#!/usr/bin/env python3
"""Totals per mode from <results-dir>/mode-*.tsv. usage: totals.py <results-dir>"""
import csv, glob, os, re, sys
d = sys.argv[1]
print("mode\tsteps\tconflict_steps\thunks\tlines_resolution(+/-)\tclean_steps_needing_a_change\tsilent_breaks\ttest_upkeep(+/-)\tfailed_checks\tconflicted_files(hunks)")
for p in sorted(glob.glob(os.path.join(d, "mode-*.tsv"))):
    rows = list(csv.DictReader(open(p), delimiter="\t"))
    if not rows: continue
    add = rem = tadd = trem = hunks = conf = differs = silent = failed = 0
    files = {}
    for r in rows:
        if r["result"] == "conflict":
            conf += 1; hunks += int(r["hunks"])
            for f in r["files"].split():
                n, h = f.rsplit(":", 1); files[n] = files.get(n, 0) + int(h)
        m = re.match(r"\+(\d+)/-(\d+)", r["lines"] or "")
        if m: add += int(m.group(1)); rem += int(m.group(2))
        m = re.match(r"\+(\d+)/-(\d+)", r["test_lines"] or "")
        if m: tadd += int(m.group(1)); trem += int(m.group(2))
        m = re.match(r"\+(\d+)/-(\d+) test \+(\d+)/-(\d+)", r["clean_but_differs"] or "")
        if m:
            differs += 1; add += int(m.group(1)); rem += int(m.group(2)); tadd += int(m.group(3)); trem += int(m.group(4))
        if r["silent_break"] == "yes": silent += 1
        if r["typecheck"] not in ("pass", "-") or not (r["tests"].startswith("pass") or r["tests"] == "-"): failed += 1
    fl = " ".join(f"{k}:{v}" for k, v in sorted(files.items(), key=lambda x: -x[1]))
    print(f"{rows[0]['mode']}\t{len(rows)}\t{conf}\t{hunks}\t+{add}/-{rem}\t{differs}\t{silent}\t+{tadd}/-{trem}\t{failed}\t{fl}")
