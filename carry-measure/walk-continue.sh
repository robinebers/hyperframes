#!/usr/bin/env bash
# Finish a hand-resolved walk-back step: commit, tag, measure, append the note, and walk on.
# usage: walk-continue.sh "<note line>"
set -euo pipefail
export LEFTHOOK=0
W=~/.capy/work/carry
git add -A packages
git -c core.editor=true cherry-pick --continue >/dev/null
N=$(( $(wc -l < $W/walkback.tsv) - 1 ))
git update-ref refs/carry/walk/$(printf %03d $N) HEAD
m=$($W/measure.py HEAD^ refs/carry/walk/$(printf %03d $((N-1))) HEAD)
echo "step $N: $m"
printf '%s\t%s\n' "$N" "$m" >> $W/walk-measure.tsv
printf '%s. %s\n' "$N" "$1" >> $W/walk-notes.md
$W/walkback.sh 443ded42 $W/walkback.tsv && echo WALK-DONE || true
tail -n 4 $W/walkback.tsv | cut -f1,2,3,7,8
