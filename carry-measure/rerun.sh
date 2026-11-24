#!/usr/bin/env bash
# One command for a new head of the patch.
# usage: rerun.sh <new-head> [name]      e.g. rerun.sh origin/spike/host-media final
# Env: DROP=<sha>         a commit of the head to leave out of the whole measurement (dropped before the walk)
#      DROP_FOR_PR=<sha>  a commit of the head that pull request #8636 already contains (dropped for that rebase only)
# Needs: the upstream remote, a worktree $WT (default /workspace/wt-check) with bun available.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
WT=${WT:-/workspace/wt-check}
NEW=$(git rev-parse "$1"); NAME=${2:-$(git rev-parse --short=7 "$NEW")}
OUT=$HERE/versions-$NAME; RES=$HERE/results-$NAME; mkdir -p "$RES"
git merge-base --is-ancestor efef865 "$NEW" || { echo "new head is not on efef865; the stored versions start there"; exit 2; }
if [ -n "${DROP:-}" ]; then
  r=$(git merge-tree --write-tree --merge-base="$DROP" "$NEW" "$DROP^") || { echo "cannot drop $DROP cleanly"; exit 2; }
  NEW=$(git commit-tree "$(echo "$r" | head -1)" -p efef865 -m "$1 without $DROP")
fi
echo "measuring $1 as $NEW ($(git diff --shortstat efef865 "$NEW"))"
# 1. walk the new head back, replaying stored hand resolutions (stops on an unknown conflict)
"$HERE/extend-all.sh" "$NEW" "$OUT"
mk(){ d=$(mktemp -d); GIT_INDEX_FILE=$d/i git read-tree "$1" && GIT_INDEX_FILE=$d/i git apply --cached "$2" \
  && t=$(GIT_INDEX_FILE=$d/i git write-tree) && git commit-tree "$t" -p "$1" -m "$3"; rm -rf "$d"; }
last=$(ls "$OUT"/*.patch | tail -1); sb=$(basename "$last" .patch); sb=${sb#*-}
git update-ref refs/carry/$NAME/start "$(mk "$sb" "$last" "carry $NAME at start")"
# 2. forward replay, three modes, checks at every step
START=refs/carry/$NAME/start VERSIONS=$OUT RESULTS=$RES WT=$WT "$HERE/run-all.sh"
# 3. forward of today: upstream main now and pull request #8636's head
GIT_LFS_SKIP_SMUDGE=1 git fetch -q --filter=blob:none upstream main "+refs/pull/8636/head:refs/carry/pr8636"
SQ=$(git commit-tree "$(git rev-parse "$NEW^{tree}")" -p efef865 -m "squash $NAME")
row(){ # label ref patch
  local m chk=- c
  m=$(python3 "$HERE/measure.py" "$2" "$3")
  if [ "$(echo "$m" | cut -f1)" = clean ]; then
    c=$(git commit-tree "$(echo "$m" | cut -f6)" -p "$2" -m "carry $NAME on $1")
    git -C "$WT" checkout -q -f --detach "$c"
    chk=$(cd "$WT" && "$HERE/check.sh")
  fi
  printf '%s\t%s\t%s\t%s\n' "$1" "$(git rev-parse --short=10 "$2")" "$m" "$chk"
}
{
  printf 'target\tsha\tresult\tfiles\thunks\tlines\ttest_lines\tmerged_tree\tcheck\n'
  row main upstream/main "$SQ"
  row pr8636 refs/carry/pr8636 "$SQ"
  if [ -n "${DROP_FOR_PR:-}" ]; then
    D=$(git merge-tree --write-tree --merge-base="$DROP_FOR_PR" "$NEW" "$DROP_FOR_PR^" | head -1)
    row "pr8636-minus-${DROP_FOR_PR:0:7}" refs/carry/pr8636 "$(git commit-tree "$D" -p efef865 -m "minus drop")"
  fi
} > "$RES/today.tsv"
python3 "$HERE/totals.py" "$RES" | tee "$RES/totals.tsv"
