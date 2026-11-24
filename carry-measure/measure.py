#!/usr/bin/env python3
"""Measure one carry step without touching a worktree.

usage: measure.py <ours> <patch-commit> [<resolved-commit>]
  ours            the upstream commit the patch is moved onto
  patch-commit    a one-commit patch (its parent is the tree it was written on)
  resolved-commit the patch as resolved by hand on <ours> (optional)

Prints one TSV row: result, conflicted files (kind:hunks), hunks, lines +/- to resolve
(non-test and test separately), mechanical tree. The resolution lines are the diff between
the mechanical merge with every conflict stripped to "ours" (upstream) and the resolved tree.
"""
import os, subprocess, sys, tempfile

def git(*a, input=None, env=None, check=True):
    r = subprocess.run(["git", *a], input=input, capture_output=True, env=env)
    if check and r.returncode not in (0, 1):
        raise SystemExit(f"git {' '.join(a)} failed: {r.stderr.decode()}")
    return r

def strip_ours(text):
    out, mode, hunks = [], None, 0
    for line in text.split("\n"):
        if line.startswith("<<<<<<< "): mode = "ours"; hunks += 1; continue
        if mode and line.startswith("||||||| "): mode = "base"; continue
        if mode and line == "=======": mode = "theirs"; continue
        if mode and line.startswith(">>>>>>> "): mode = None; continue
        if mode in (None, "ours"): out.append(line)
    return "\n".join(out), hunks

ours, patch = sys.argv[1], sys.argv[2]
resolved = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] != "-" else None
r = git("-c", "merge.conflictStyle=diff3", "merge-tree", "--write-tree", f"--merge-base={patch}^", ours, patch)
lines = r.stdout.decode().split("\n")
tree = lines[0]
stages = {}
for l in lines[1:]:
    if not l: break
    meta, path = l.split("\t", 1)
    stages.setdefault(path, set()).add(meta.split()[2])
clean = r.returncode == 0
with tempfile.TemporaryDirectory() as d:
    env = dict(os.environ, GIT_INDEX_FILE=os.path.join(d, "index"))
    git("read-tree", tree, env=env)
    files, hunks = [], 0
    for path, st in sorted(stages.items()):
        if "2" not in st:   # deleted on the upstream side: "ours" has no file
            git("update-index", "--force-remove", path, env=env)
            files.append(f"{os.path.basename(path)}(modify/delete):1"); hunks += 1; continue
        if "3" not in st:   # deleted by the patch, changed upstream: keep upstream's
            blob = git("rev-parse", f"{ours}:{path}").stdout.decode().strip()
            git("update-index", "--add", "--cacheinfo", f"100644,{blob},{path}", env=env)
            files.append(f"{os.path.basename(path)}(delete/modify):1"); hunks += 1; continue
        text = git("cat-file", "blob", f"{tree}:{path}").stdout.decode()
        stripped, h = strip_ours(text)
        blob = git("hash-object", "-w", "--stdin", input=stripped.encode()).stdout.decode().strip()
        git("update-index", "--add", "--cacheinfo", f"100644,{blob},{path}", env=env)
        files.append(f"{os.path.basename(path)}:{h}"); hunks += h
    stripped_tree = git("write-tree", env=env).stdout.decode().strip()
add = rem = tadd = trem = 0
if resolved:
    for l in git("diff", "--numstat", stripped_tree, f"{resolved}^{{tree}}").stdout.decode().splitlines():
        a, b, p = l.split("\t")
        if p.endswith(".test.ts"): tadd += int(a); trem += int(b)
        else: add += int(a); rem += int(b)
print("\t".join([
    "clean" if clean else "conflict",
    " ".join(files) or "-",
    str(hunks),
    f"+{add}/-{rem}" if resolved else "-",
    f"+{tadd}/-{trem}" if resolved else "-",
    tree,
]))
