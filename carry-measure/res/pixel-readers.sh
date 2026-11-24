#!/usr/bin/env bash
# Hand resolutions for the pixel-readers commit (0bbcdd66c) when it is walked back.
set -euo pipefail
N=$1; C=$2; R=$(cd "$(dirname "$0")/.." && pwd)/resolve.py
PIX=0bbcdd66cf9b0fb2dafc2d95884f74250b80b62c
RT=packages/core/src/runtime
case $N in
  037) # upstream added the nativeVideoLook import, the line next to the patch's frameSources import
    [ -f $C/pausedVideoFrames.ts ] || exit 3
    grep -q '^<<<<<<<' $C/pausedVideoFrames.ts || exit 3
    $R $C/pausedVideoFrames.ts 'import { frameSourcePicture } from "./frameSources";' ;;
  048) # MISSING FOUNDATION: b7157bda (#7379) created pausedVideoFrames.ts and pausedVideoCallbacks.ts, the
       # paused-frame readers (drawImage, WebGL upload, colour grade, rVFC shim) the commit hands its picture to.
       # Before it there is nothing to hand it to; carrying it means building those readers (a redesign), so the
       # pixel-readers part leaves the patch here: its hunks are taken out of frameSources.ts and the test file.
    tree=$(head -1 $C/META | cut -d' ' -f1)
    grep -qx "$RT/pausedVideoFrames.ts" $C/META || exit 3
    for f in frameSources.ts init.frameSourceMedia.test.ts; do
      git show $tree:$RT/$f > $C/$f.cur; git show $PIX:$RT/$f > $C/$f.base; git show $PIX^:$RT/$f > $C/$f.other
      git merge-file -p --ours $C/$f.cur $C/$f.base $C/$f.other > $C/$f
      rm $C/$f.cur $C/$f.base $C/$f.other
      echo "$RT/$f" >> $C/META
    done
    sed -i "s#^$RT/pausedVideoFrames.ts\$#DELETE $RT/pausedVideoFrames.ts#" $C/META ;;
  *) exit 3 ;;
esac
