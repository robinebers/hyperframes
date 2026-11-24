#!/usr/bin/env bash
# Hand resolutions for the loop-wrap commit (d60dbefc8) when it is walked back.
set -euo pipefail
N=$1; C=$2; R=$(cd "$(dirname "$0")/.." && pwd)/resolve.py
case $N in
  059) # 5377b756 (#7238): the clipWindow import (isClipOnScreenAt -> isClipVisibleAt) sits next to the
       # sourceLength import the loop wrap widens
    [ -f $C/frameSources.ts ] && [ "$(grep -c '^<<<<<<<' $C/frameSources.ts)" = 1 ] || exit 3
    grep -q 'sourceLengthOf, supplySourceLength' $C/frameSources.ts || exit 3
    $R $C/frameSources.ts 'import { isClipVisibleAt } from "./clipWindow";
import { sourceLengthOf, supplySourceLength } from "./sourceLength";' ;;
  *) exit 3 ;;
esac
