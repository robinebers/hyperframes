#!/usr/bin/env bash
# Type-check packages/core and run the patch's own test files (every *.test.ts the HEAD commit touches in
# packages/core) plus the neighbours it could break. HEAD must be the patch commit on its upstream parent.
# Prints one line: typecheck=<pass|fail> tests=<pass|fail> [summary] (details in .carry-check.log)
set -uo pipefail
ROOT=$(git rev-parse --show-toplevel); cd "$ROOT"
LOGF="$ROOT/.carry-check.log"; : >"$LOGF"
export LEFTHOOK=0
lock=$(git hash-object bun.lock 2>/dev/null || echo none)
if [ "$(cat .carry-lock 2>/dev/null)" != "$lock" ]; then
  bun install >>"$LOGF" 2>&1 && echo "$lock" >.carry-lock
fi
bun run --cwd packages/parsers build >>"$LOGF" 2>&1
( cd packages/core && bun run build:hyperframes-runtime && bun run build:audio-fx-runtime ) >>"$LOGF" 2>&1
tc=pass
( cd packages/core && npx tsc --noEmit && npx tsc --noEmit -p tsconfig.runtime.json ) >>"$LOGF" 2>&1 || tc=fail
files=()
for f in init.buffering.test.ts frameSources.test.ts media.test.ts preloadMedia.test.ts; do
  [ -f packages/core/src/runtime/$f ] && files+=("src/runtime/$f")
done
while read -r f; do
  [ -f "$f" ] && files+=("${f#packages/core/}")
done < <(git diff --name-only HEAD^ HEAD -- 'packages/core/*.test.ts')
out=$( cd packages/core && npx vitest run "${files[@]}" 2>&1 ); rc=$?
echo "$out" >>"$LOGF"
summary=$(echo "$out" | grep -E '^ +Tests ' | sed 's/  */ /g' | sed 's/^ //')
[ $rc -eq 0 ] && t=pass || t=fail
fails=$(echo "$out" | grep -E '^ +(×|✗|FAIL) ' | sed 's/^ *//' | sort -u | tr '\n' ';' | cut -c1-400)
echo "typecheck=$tc tests=$t [$summary] files=${#files[@]} $fails"
