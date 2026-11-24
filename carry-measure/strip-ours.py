#!/usr/bin/env python3
# Strip git conflict markers from a file, keeping the "ours" side (the upstream tree during a cherry-pick).
import sys
out, mode = [], None
for line in open(sys.argv[1], encoding="utf-8").read().split("\n"):
    if line.startswith("<<<<<<< "): mode = "ours"; continue
    if mode and line.startswith("||||||| "): mode = "base"; continue
    if mode and line == "=======": mode = "theirs"; continue
    if mode and line.startswith(">>>>>>> "): mode = None; continue
    if mode in (None, "ours"): out.append(line)
sys.stdout.write("\n".join(out))
