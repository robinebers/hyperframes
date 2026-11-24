#!/usr/bin/env bash
# Hand resolutions for the hold-progress commit (0a77abf42) when it is walked back.
set -euo pipefail
N=$1; C=$2; R=$(cd "$(dirname "$0")/.." && pwd)/resolve.py
case $N in
  024) # 01331014 (#8138) created stoppedReceivingData, the 8 s cut-off received() feeds; before it there is no
       # cut-off, so the hold-progress use, its import and its test (with the 8 s test) go with it
    $R $C/init.ts @ours
    $R $C/init.frameSourceMedia.test.ts @ours
    sed -i '/^  frameSourceReceived,$/d' $C/init.ts ;;
  *) exit 3 ;;
esac
