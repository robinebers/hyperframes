#!/usr/bin/env python3
# Replace the conflict blocks of a file, in order, with the given texts ("@ours" keeps the upstream side).
# usage: resolve.py <file> <text-for-block-1> [<text-for-block-2> ...]
import re, sys
path, texts = sys.argv[1], sys.argv[2:]
s = open(path).read()
blocks = list(re.finditer(r"<<<<<<< [^\n]*\n(.*?)(?:\|\|\|\|\|\|\| [^\n]*\n.*?)?=======\n.*?>>>>>>> [^\n]*\n", s, re.S))
assert len(blocks) == len(texts), f"{len(blocks)} blocks, {len(texts)} texts"
out, pos = [], 0
for m, t in zip(blocks, texts):
    out.append(s[pos:m.start()])
    out.append(m.group(1) if t == "@ours" else (t if t.endswith("\n") or t == "" else t + "\n"))
    pos = m.end()
out.append(s[pos:])
open(path, "w").write("".join(out))
