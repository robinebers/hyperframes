#!/usr/bin/env bash
# Walk a new patch head back through the stored versions, replaying the stored hand resolutions in res/*.sh.
# usage: extend-all.sh <new-head> <out-dir> [--drop sha,...]
# Stops at a conflict no resolution script covers: edit <out-dir>/conflicts/NNN/*, run extend-save.py, rerun.
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
NEW=$1; OUT=$2; shift 2
while :; do
  stops=$(cat "$HERE"/res/*.stops 2>/dev/null | tr '\n' ',')
  msg=$(python3 "$HERE/extend.py" "$HERE/versions" "$NEW" "$OUT" --stop-at "$stops" "$@" 2>&1); rc=$?
  echo "$msg" | tail -1
  [ $rc -eq 0 ] && exit 0
  n=$(echo "$msg" | sed -n 's/^CONFLICT at \([0-9]*\)-.*/\1/p' | tail -1)
  [ -n "$n" ] || exit $rc
  ok=0
  for r in "$HERE"/res/*.sh; do
    if bash "$r" "$n" "$OUT/conflicts/$n" >/dev/null 2>&1; then ok=1; echo "  step $n resolved by $(basename "$r")"; break; fi
  done
  [ $ok -eq 1 ] || { echo "  step $n: no stored resolution; resolve by hand"; exit 3; }
  python3 "$HERE/extend-save.py" "$OUT" "$n" >/dev/null && rm -rf "$OUT/conflicts/$n" && mkdir -p "$OUT/conflicts/$n" && touch "$OUT/conflicts/$n/DONE"
done
