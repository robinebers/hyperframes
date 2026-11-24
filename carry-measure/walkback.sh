#!/usr/bin/env bash
# Walk a one-commit patch backwards over every upstream commit that touches the files it touches.
# Run inside a worktree whose HEAD is the patch commit on top of its upstream tree.
# usage: walkback.sh <stop-sha> [log.tsv]
# Stops on a conflict (resolve by hand, git add, git -c core.editor=true cherry-pick --continue, then
# record with record-resolution.sh) or when the next touching commit is <stop-sha> or older.
set -euo pipefail
STOP=$(git rev-parse "$1")
LOG=${2:-walkback.tsv}
[ -f "$LOG" ] || printf 'step\tstepped_over\tdate\tauthor\ttitle\tnew_base\tresult\tconflicted_files\n' >"$LOG"
step=$(( $(wc -l <"$LOG") ))
while :; do
  BASE=$(git rev-parse HEAD^)
  mapfile -t FILES < <(git diff --name-only HEAD^ HEAD)
  C=$(git log --first-parent -1 --format=%H "$BASE" -- "${FILES[@]}")
  if git merge-base --is-ancestor "$C" "$STOP"; then
    echo "next touching commit $C is at or before stop; done at base $BASE"; exit 0
  fi
  P=$(git rev-parse HEAD)
  git checkout -q --detach "$C^"
  meta=$(git log -1 --format='%h%x09%cI%x09%an%x09%s' "$C")
  # call sites that exist only in the older code: the patch may need a guard there
  git diff "$C^" "$C" -- 'packages/core/src/runtime/*.ts' ':!*.test.ts' | grep -E '^-[^-].*(\.load\(\)|\.preload = |\.play\(\)|\.currentTime = )' | sed "s/^/$(git rev-parse --short "$C") /" >>"${LOG%.tsv}-sites.txt" || true
  if git cherry-pick --no-rerere-autoupdate -x "$P" >/dev/null 2>&1; then
    printf '%s\t%s\t%s\tclean\t\n' "$step" "$meta" "$(git rev-parse --short "$C^")" >>"$LOG"
    git update-ref "refs/carry/walk/$(printf %03d "$step")" HEAD
    step=$((step+1))
  else
    files=$(git diff --name-only --diff-filter=U | tr '\n' ' ')
    printf '%s\t%s\t%s\tconflict\t%s\n' "$step" "$meta" "$(git rev-parse --short "$C^")" "$files" >>"$LOG"
    echo "CONFLICT at step $step stepping over $meta: $files"; exit 3
  fi
done
