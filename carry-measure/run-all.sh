#!/usr/bin/env bash
# Forward replay in modes b, c and a, with type-check and tests at every step. Output: $RESULTS/mode-*.tsv
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
START=${START:-refs/carry/start}
TO=${TO:-efef865}
WT=${WT:-/workspace/wt-check}
VERSIONS=${VERSIONS:-$HERE/versions}
RESULTS=${RESULTS:-$HERE/results}
TAGS=${TAGS:-v0.9.6,v0.9.27,v0.9.58,v0.9.79,v0.9.86}
mkdir -p "$RESULTS"
for mode in ${MODES:-b c a}; do
  : > "$RESULTS/mode-$mode.tsv"
  python3 "$HERE/carry.py" "$START" "$TO" $mode --tags "$TAGS" --versions "$VERSIONS" \
    --check-worktree "$WT" --out "$RESULTS/mode-$mode.tsv"
done
