#!/usr/bin/env python3
"""Save a hand resolution made in <out-dir>/conflicts/NNN/ as the version patch, and print its size.
usage: extend-save.py <out-dir> NNN"""
import os, subprocess, sys, tempfile
def git(*a, input=None, env=None):
    r = subprocess.run(["git", *a], input=input, capture_output=True, env=env)
    if r.returncode: sys.exit(f"git {a}: {r.stderr.decode()}")
    return r.stdout.decode().strip()
outdir, n = sys.argv[1], sys.argv[2]
cd = os.path.join(outdir, "conflicts", n)
head, *files = [l for l in open(os.path.join(cd, "META")).read().split("\n") if l]
tree, base, name = head.split()
with tempfile.TemporaryDirectory() as d:
    env = dict(os.environ, GIT_INDEX_FILE=os.path.join(d, "i"))
    git("read-tree", tree, env=env)
    for f in files:
        if f.startswith("DELETE "):
            git("update-index", "--force-remove", f[7:], env=env); continue
        text = open(os.path.join(cd, os.path.basename(f)), "rb").read()
        assert b"<<<<<<<" not in text and b">>>>>>>" not in text, f"markers left in {f}"
        blob = git("hash-object", "-w", "--stdin", input=text)
        git("update-index", "--cacheinfo", f"100644,{blob},{f}", env=env)
    t = git("write-tree", env=env)
open(os.path.join(outdir, name), "w").write(subprocess.run(["git", "diff", "--binary", base, t], capture_output=True).stdout.decode())
print(git("diff", "--numstat", tree, t))
