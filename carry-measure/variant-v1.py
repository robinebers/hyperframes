#!/usr/bin/env python3
"""Point 5: derive the smaller-contact variant of every stored version.

The variant leaves mediaNotReadyAt's filter as upstream wrote it and changes one line only:
  isPlayableTrack(el) &&   ->   (frameSourceWaitsAt(el, t, start) ?? isPlayableTrack(el)) &&
usage: variant-v1.py <versions-dir> <out-dir>   (run inside the repository)
"""
import glob, os, re, subprocess, sys, tempfile
INIT = "packages/core/src/runtime/init.ts"
def git(*a, input=None, env=None):
    r = subprocess.run(["git", *a], input=input, capture_output=True, env=env)
    if r.returncode: sys.exit(f"git {a}: {r.stderr.decode()}")
    return r.stdout.decode()
def block(text):
    s = text.index("const mediaNotReadyAt")
    e = text.index(".map(({ el }) => el);", s)
    return s, e
src, dst = sys.argv[1], sys.argv[2]
os.makedirs(dst, exist_ok=True)
for p in sorted(glob.glob(os.path.join(src, "*.patch"))):
    base = git("rev-parse", re.match(r"\d+-([0-9a-f]+)\.patch", os.path.basename(p)).group(1)).strip()
    with tempfile.TemporaryDirectory() as d:
        env = dict(os.environ, GIT_INDEX_FILE=os.path.join(d, "i"))
        git("read-tree", base, env=env)
        git("apply", "--cached", p, env=env)
        mine = git("show", ":" + INIT, env=env)
        up = git("show", f"{base}:{INIT}")
        us, ue = block(up)
        ms, me = block(mine)
        new_block, n = re.subn(r"^(\s*)isPlayableTrack\(el\) &&$",
                               r"\1(frameSourceWaitsAt(el, t, start) ?? isPlayableTrack(el)) &&",
                               up[us:ue], flags=re.M)
        assert n == 1, (p, n)
        out = mine[:ms] + new_block + mine[me:]
        blob = git("hash-object", "-w", "--stdin", input=out.encode()).strip()
        git("update-index", "--cacheinfo", f"100644,{blob},{INIT}", env=env)
        t = git("write-tree", env=env).strip()
    open(os.path.join(dst, os.path.basename(p)), "w").write(git("diff", "--binary", base, t))
print("ok")
