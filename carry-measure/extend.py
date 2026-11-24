#!/usr/bin/env python3
"""Walk a newer head of the patch back through the stored versions, reusing every hand resolution made so far.

usage: extend.py <versions-dir> <new-head> <out-dir> [--drop <sha>,...]
  versions-dir  NNN-<base>.patch: the old patch as written on each older upstream commit; 000 sits on the
                new head's upstream base
  new-head      the new patch head (same upstream base as version 000)
  --drop        commits of new-head to leave out
Version 000 of the new patch is new-head squashed. Each later one is a three-way merge: base the old
version N-1, ours the old version N, theirs the new version N-1, so only the lines the new head adds move,
one stored step at a time. A clean merge is written to <out-dir>. A conflict stops the walk and leaves the
files with markers in <out-dir>/conflicts/NNN/; edit them there, run extend-save.py <out-dir> NNN, rerun.
"""
import argparse, glob, os, re, subprocess, sys, tempfile
def git(*a, input=None, env=None, ok=(0,)):
    r = subprocess.run(["git", *a], input=input, capture_output=True, env=env)
    if r.returncode not in ok: sys.exit(f"git {a}: {r.stderr.decode()}")
    return r
def out(*a, **k): return git(*a, **k).stdout.decode().strip()
def commit_of(path):
    base = out("rev-parse", re.match(r"\d+-([0-9a-f]+)\.patch", os.path.basename(path)).group(1))
    with tempfile.TemporaryDirectory() as d:
        env = dict(os.environ, GIT_INDEX_FILE=os.path.join(d, "i"))
        git("read-tree", base, env=env); git("apply", "--cached", path, env=env)
        return base, out("commit-tree", out("write-tree", env=env), "-p", base, "-m", "version")
ap = argparse.ArgumentParser()
ap.add_argument("versions"); ap.add_argument("new"); ap.add_argument("outdir"); ap.add_argument("--drop", default="")
ap.add_argument("--stop-at", default="", help="NNN,... stop there even when the merge is clean (a silent break to fix)")
a = ap.parse_args()
olds = sorted(glob.glob(os.path.join(a.versions, "*.patch")))
os.makedirs(a.outdir, exist_ok=True)
first = os.path.join(a.outdir, os.path.basename(olds[0]))
if not os.path.exists(first):
    base0, _ = commit_of(olds[0])
    new = out("rev-parse", a.new)
    for d in [x for x in a.drop.split(",") if x]:
        r = git("merge-tree", "--write-tree", f"--merge-base={d}", new, f"{d}^", ok=(0, 1))
        if r.returncode: sys.exit(f"cannot drop {d}")
        new = out("commit-tree", r.stdout.decode().split("\n")[0], "-p", new, "-m", "drop")
    assert git("merge-base", "--is-ancestor", base0, new, ok=(0, 1)).returncode == 0
    open(first, "w").write(git("diff", "--binary", base0, new).stdout.decode())
for prev, cur in zip(olds, olds[1:]):
    target = os.path.join(a.outdir, os.path.basename(cur))
    if os.path.exists(target): continue
    _, old_prev = commit_of(prev)
    base, old_cur = commit_of(cur)
    _, new_prev = commit_of(os.path.join(a.outdir, os.path.basename(prev)))
    r = git("-c", "merge.conflictStyle=diff3", "merge-tree", "--write-tree", f"--merge-base={old_prev}", old_cur, new_prev, ok=(0, 1))
    lines = r.stdout.decode().split("\n")
    forced = os.path.basename(cur)[:3] in a.stop_at.split(",") and not os.path.exists(os.path.join(a.outdir, "conflicts", os.path.basename(cur)[:3], "DONE"))
    if r.returncode == 0 and not forced:
        open(target, "w").write(git("diff", "--binary", base, lines[0]).stdout.decode()); continue
    files = sorted({l.split("\t", 1)[1] for l in lines[1:] if "\t" in l})
    if r.returncode == 0:
        files = out("diff", "--name-only", f"{old_cur}^", lines[0], "--", "*.ts").split()
    cd = os.path.join(a.outdir, "conflicts", os.path.basename(cur)[:3])
    os.makedirs(cd, exist_ok=True)
    for f in files:
        open(os.path.join(cd, os.path.basename(f)), "wb").write(git("cat-file", "blob", f"{lines[0]}:{f}", ok=(0, 128)).stdout)
    open(os.path.join(cd, "META"), "w").write(f"{lines[0]} {base} {os.path.basename(cur)}\n" + "\n".join(files) + "\n")
    sys.exit(f"CONFLICT at {os.path.basename(cur)} (upstream {base[:10]}): {' '.join(files)}; markers in {cd}")
print(f"done: {len(olds)} versions written to {a.outdir}")
