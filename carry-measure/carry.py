#!/usr/bin/env python3
"""Replay a one-commit patch forward over upstream and count what it costs.

usage: carry.py <patch-commit> <to> <mode> [--tags t1,t2,...] [--check-worktree DIR] [--out FILE]
  patch-commit  the patch as one commit; its parent is the upstream commit it starts from
  to            the upstream commit to carry it to
  mode          a = one step per upstream commit that touches a file any version of the patch touches
                b = one step per week (main as of each --week-anchor + 7k days), then <to>
                c = one step per tag given with --tags, then <to>
Resolutions come from versions/*.patch (NNN-<base>.patch: the patch as written by hand on <base>).
At each step the target is the nearest stored version at or after that upstream commit, moved back onto it
(clean by construction when no touching commit lies between; otherwise it must move back cleanly). With no
such version a conflicting step stops the run.
rerere is never used: every merge is a fresh git merge-tree.
"""
import argparse, datetime, glob, os, re, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))

def git(*a, input=None, env=None, ok=(0,)):
    r = subprocess.run(["git", *a], input=input, capture_output=True, env=env)
    if r.returncode not in ok:
        sys.exit(f"git {' '.join(a)}: {r.stderr.decode()}")
    return r

def out(*a, **k): return git(*a, **k).stdout.decode().strip()
def is_ancestor(a, b): return git("merge-base", "--is-ancestor", a, b, ok=(0, 1)).returncode == 0
def tree(c): return out("rev-parse", f"{c}^{{tree}}")
def files_of(c): return out("diff", "--name-only", f"{c}^", c).split()

def commit_tree(t, parent, msg="carry"):
    return out("commit-tree", t, "-p", parent, "-m", msg)

def merge(onto, patch):
    """Mechanical cherry-pick of <patch> onto <onto>: (clean, merged tree, {path: stages})."""
    r = git("-c", "merge.conflictStyle=diff3", "merge-tree", "--write-tree",
            f"--merge-base={patch}^", onto, patch, ok=(0, 1))
    lines = r.stdout.decode().split("\n")
    stages = {}
    for l in lines[1:]:
        if not l: break
        meta, path = l.split("\t", 1)
        stages.setdefault(path, set()).add(meta.split()[2])
    return r.returncode == 0, lines[0], stages

def strip_ours(text):
    kept, mode, hunks = [], None, 0
    for line in text.split("\n"):
        if line.startswith("<<<<<<< "): mode = "ours"; hunks += 1; continue
        if mode and line.startswith("||||||| "): mode = "base"; continue
        if mode and line == "=======": mode = "theirs"; continue
        if mode and line.startswith(">>>>>>> "): mode = None; continue
        if mode in (None, "ours"): kept.append(line)
    return "\n".join(kept), hunks

def ours_stripped(onto, t, stages):
    """The merged tree with every conflict reduced to the upstream side, plus per-file hunk counts."""
    files, hunks = [], 0
    with tempfile.TemporaryDirectory() as d:
        env = dict(os.environ, GIT_INDEX_FILE=os.path.join(d, "index"))
        git("read-tree", t, env=env)
        for path, st in sorted(stages.items()):
            name = os.path.basename(path)
            if "2" not in st:
                git("update-index", "--force-remove", path, env=env)
                files.append(f"{name}(modify/delete):1"); hunks += 1; continue
            if "3" not in st:
                blob = out("rev-parse", f"{onto}:{path}")
                git("update-index", "--add", "--cacheinfo", f"100644,{blob},{path}", env=env)
                files.append(f"{name}(delete/modify):1"); hunks += 1; continue
            text, h = strip_ours(out("cat-file", "blob", f"{t}:{path}") + "\n")
            blob = out("hash-object", "-w", "--stdin", input=text.encode())
            git("update-index", "--add", "--cacheinfo", f"100644,{blob},{path}", env=env)
            files.append(f"{name}:{h}"); hunks += h
        return out("write-tree", env=env), files, hunks

def numstat(a, b):
    add = rem = tadd = trem = 0
    for l in out("diff", "--numstat", a, b).splitlines():
        x, y, p = l.split("\t")
        if p.endswith(".test.ts"): tadd += int(x); trem += int(y)
        else: add += int(x); rem += int(y)
    return add, rem, tadd, trem

class Versions:
    def __init__(self, d):
        self.items = []
        for p in sorted(glob.glob(os.path.join(d, "*.patch"))):
            base = out("rev-parse", re.match(r"\d+-([0-9a-f]+)\.patch", os.path.basename(p)).group(1))
            text = open(p, "rb").read()
            files = sorted(set(re.findall(rb"^diff --git a/(\S+) b/", text, re.M)))
            self.items.append({"base": base, "path": p, "files": [f.decode() for f in files], "commit": None})
    def commit(self, v):
        if v["commit"] is None:
            with tempfile.TemporaryDirectory() as d:
                env = dict(os.environ, GIT_INDEX_FILE=os.path.join(d, "index"))
                git("read-tree", v["base"], env=env)
                git("apply", "--cached", v["path"], env=env)
                v["commit"] = commit_tree(out("write-tree", env=env), v["base"], "carry version")
        return v["commit"]
    def files(self):
        return sorted({f for v in self.items for f in v["files"]})
    def target(self, onto):
        """The stored version for <onto>: its base descends from <onto> with no touching commit between."""
        best = None
        for v in self.items:
            if not is_ancestor(onto, v["base"]): continue
            n = int(out("rev-list", "--count", f"{onto}..{v['base']}"))
            if best is None or n < best[0]: best = (n, v)
        if best is None: return None
        exact = out("rev-list", "--count", f"{onto}..{best[1]['base']}", "--", *best[1]["files"]) == "0"
        clean, t, _ = merge(onto, self.commit(best[1]))
        if not clean:
            assert not exact, f"stored version {best[1]['path']} does not apply cleanly to {onto}"
            return None
        return commit_tree(t, onto, f"carry: patch on {onto[:10]}")

def check(wt, commit):
    if not wt: return "-", "-"
    git("-C", wt, "checkout", "-q", "-f", "--detach", commit)
    r = subprocess.run([os.path.join(HERE, "check.sh")], cwd=wt, capture_output=True, text=True)
    line = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "typecheck=? tests=?"
    tc = re.search(r"typecheck=(\w+)", line).group(1)
    ts = re.search(r"tests=(\w+) \[([^\]]*)\]", line)
    return tc, (f"{ts.group(1)} ({ts.group(2)})" if ts else line)

def steps_for(mode, frm, to, versions, tags, anchor):
    if mode == "a":
        return out("rev-list", "--reverse", "--first-parent", f"{frm}..{to}", "--", *versions.files()).split()
    if mode == "b":
        start = datetime.datetime.fromisoformat(out("log", "-1", "--format=%cI", frm)).astimezone(datetime.timezone.utc)
        end = datetime.datetime.fromisoformat(out("log", "-1", "--format=%cI", to)).astimezone(datetime.timezone.utc)
        monday = datetime.datetime.fromisoformat(anchor)
        while monday <= start: monday += datetime.timedelta(days=7)
        res = []
        while monday < end:
            c = out("rev-list", "-1", "--first-parent", f"--before={monday.isoformat()}", to)
            if c and c != frm and is_ancestor(frm, c) and c not in res: res.append(c)
            monday += datetime.timedelta(days=7)
        return res + [out("rev-parse", to)]
    if mode == "c":
        return [out("rev-parse", f"{t}^{{commit}}") for t in tags] + [out("rev-parse", to)]
    sys.exit(f"unknown mode {mode}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("patch"); ap.add_argument("to"); ap.add_argument("mode")
    ap.add_argument("--tags", default=""); ap.add_argument("--versions", default=os.path.join(HERE, "versions"))
    ap.add_argument("--check-worktree", default=""); ap.add_argument("--check", default="all", help="all|end|none")
    ap.add_argument("--out", default="")
    ap.add_argument("--week-anchor", default="2026-10-27T00:00:00+00:00", help="mode b: weeks start at this instant, every 7 days")
    a = ap.parse_args()
    versions = Versions(a.versions)
    cur = out("rev-parse", a.patch); frm = out("rev-parse", f"{cur}^")
    steps = steps_for(a.mode, frm, a.to, versions, [t for t in a.tags.split(",") if t], a.week_anchor)
    head = "mode\tstep\tupstream\tdate\ttag\ttitle\tresult\tfiles\thunks\tlines\ttest_lines\tclean_but_differs\ttypecheck\ttests\tsilent_break\n"
    sink = open(a.out, "a") if a.out else sys.stdout
    if a.out and os.path.getsize(a.out) == 0: sink.write(head)
    if not a.out: sink.write(head)
    for i, s in enumerate(steps, 1):
        meta = out("log", "-1", "--format=%h%x09%cI%x09%s", s).split("\t")
        tag = out("tag", "--points-at", s).replace("\n", ",") or "-"
        clean, t, stages = merge(s, cur)
        target = versions.target(s)
        mech = commit_tree(t, s, "mechanical") if clean else None
        do_check = a.check == "all" or (a.check == "end" and i == len(steps))
        if target is None:
            if not clean:
                st, files, hunks = ours_stripped(s, t, stages)
                sink.write(f"{a.mode}\t{i}\t{meta[0]}\t{meta[1]}\t{tag}\t{meta[2][:90]}\tconflict\t{' '.join(files)}\t{hunks}\tNEEDS HAND RESOLUTION\t-\t-\t-\t-\t-\n")
                sink.flush(); print(f"stop: no stored version for {s}; resolve by hand, store versions/NNN-{s[:10]}.patch, rerun", file=sys.stderr)
                sys.exit(3)
            target = mech
        diff_lines = "-"
        if clean:
            files, hunks, lines, tlines = "-", 0, "+0/-0", "+0/-0"
            if tree(mech) != tree(target):
                x, y, tx, ty = numstat(mech, target)
                diff_lines = f"+{x}/-{y} test +{tx}/-{ty}"
        else:
            st, fl, hunks = ours_stripped(s, t, stages)
            files = " ".join(fl)
            x, y, tx, ty = numstat(st, target)
            lines, tlines = f"+{x}/-{y}", f"+{tx}/-{ty}"
        tc, ts, silent = "-", "-", "-"
        if do_check and a.check_worktree:
            if clean and tree(mech) != tree(target):
                mtc, mts = check(a.check_worktree, mech)
                silent = "yes" if (mtc != "pass" or not mts.startswith("pass")) else "no"
                tc, ts = check(a.check_worktree, target)
                ts = f"{ts}; mechanical: typecheck={mtc} tests={mts}"
            else:
                tc, ts = check(a.check_worktree, target)
                if clean: silent = "yes" if (tc != "pass" or not ts.startswith("pass")) else "no"
        sink.write(f"{a.mode}\t{i}\t{meta[0]}\t{meta[1]}\t{tag}\t{meta[2][:90]}\t{'clean' if clean else 'conflict'}\t{files}\t{hunks}\t{lines}\t{tlines}\t{diff_lines}\t{tc}\t{ts}\t{silent}\n")
        sink.flush()
        cur = target

main()
