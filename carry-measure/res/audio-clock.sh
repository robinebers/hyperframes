#!/usr/bin/env bash
# Hand resolutions for the audio-clock commit (4d15018) when it is walked back; called by extend-all.sh with
# the step number and the conflicts directory. Each case is what a person decided once; the script replays it.
set -euo pipefail
N=$1; C=$2; R=$(cd "$(dirname "$0")/.." && pwd)/resolve.py
case $N in
  026) # a56fa2ca (#8082) added "scrub-audio" and the time field the audio-clock handler reads
    $R $C/types.ts '  | "flash-elements"
  | "audio-clock";'
    python3 - "$C/types.ts" <<'EOF'
import sys; p=sys.argv[1]; s=open(p).read()
old='  seekMode?: "drag" | "commit";\n  rate?: number;'
assert s.count(old)==1; open(p,"w").write(s.replace(old,'  seekMode?: "drag" | "commit";\n  time?: number | null;\n  rate?: number;'))
EOF
    ;;
  028) # 925a64db (#8243) added the ANOTHER_SITE_DRIVES allowlist; before it there is nothing to list
    $R $C/bridge.ts @ours ;;
  031) # the commit before f667111d17 added isFiniteNumber/readNumber; the handler checks inline
    $R $C/bridge.ts '      deps.onSetWebAudioMediaDisabled(Boolean(data.disabled)),
    "audio-clock": (data, deps) => {
      if (data.time === null) return deps.onAudioClock?.(null);
      const { time, rate, at } = data;
      if (typeof time !== "number" || typeof rate !== "number" || typeof at !== "number") return;
      if (!Number.isFinite(time) || !Number.isFinite(rate) || !Number.isFinite(at) || rate <= 0) return;
      deps.onAudioClock?.({ time: Math.max(0, time), rate, at });
    },
    "set-playback-rate": (data, deps) => deps.onSetPlaybackRate(Number(data.playbackRate ?? 1)),
    "set-idle-heartbeat": (data, deps) => deps.onSetIdleHeartbeat(Boolean(data.slow)),
    "set-display-scale": (data, deps) => deps.onSetDisplayScale?.(Number(data.scale)),
    "set-preview-quality": (data, deps) => deps.onSetPreviewQuality?.(Number(data.level)),
    "set-copies-ahead": (data, deps) => deps.onSetCopiesAhead?.(Boolean(data.on)),' ;;
  079) # silent break: bba3676a (#6906) added the webAudio flag to AudioClockSource; before it the source has none
    sed -i '/^        webAudio: true,$/d' "$C/init.ts" ;;
  *) echo "no stored resolution for step $N"; exit 3 ;;
esac
