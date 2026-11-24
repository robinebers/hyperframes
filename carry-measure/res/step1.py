
import re,sys
R="/workspace/wt-walk/packages/core/src/runtime/"
def sub(f, old, new, count=1):
    p=R+f; s=open(p).read()
    n=s.count(old)
    assert n==count, (f, old, n)
    s=s.replace(old,new); open(p,"w").write(s)
# media.ts conflict: keep the hasFrameSource import, no runtimeAttributes import (does not exist yet)
p=R+"media.ts"; s=open(p).read()
s=re.sub(r"<<<<<<< HEAD\n\|\|\|\|\|\|\| [^\n]*\nimport \{ setRuntimePreload \} from \"./runtimeAttributes\";\n=======\nimport \{ hasFrameSource \} from \"./frameSources\";\nimport \{ setRuntimePreload \} from \"./runtimeAttributes\";\n>>>>>>> [^\n]*\n", 'import { hasFrameSource } from "./frameSources";\n', s)
assert "<<<<<<<" not in s; open(p,"w").write(s)
# init.ts call sites
sub("init.ts", "  const armLength = (el: HTMLMediaElement) => {\n    if (\n", "  const armLength = (el: HTMLMediaElement) => {\n    if (hasFrameSource(el)) return;\n    if (\n")
sub("init.ts", "      return;\n    el.preload = \"none\";\n    withoutOwnTimingRecords(el, () => releaseMedia(el, true));", "      return;\n    if (!hasFrameSource(el)) el.preload = \"none\";\n    withoutOwnTimingRecords(el, () => releaseMedia(el, true));")
sub("init.ts", "      const wasPreloading = el.preload !== \"none\";\n      el.preload = \"none\";", "      const wasPreloading = el.preload !== \"none\";\n      if (!hasFrameSource(el)) el.preload = \"none\";")
sub("init.ts", "          if (!isVideoElement(el) || el.videoWidth > 0) continue;\n          if (el.preload === \"none\") el.preload = \"metadata\";", "          if (!isVideoElement(el) || el.videoWidth > 0 || hasFrameSource(el)) continue;\n          if (el.preload === \"none\") el.preload = \"metadata\";")
sub("init.ts", "        if (el.preload !== \"auto\") el.preload = \"auto\";\n        if (el.readyState === 1 && !el.seeking)", "        if (el.preload !== \"auto\" && !hasFrameSource(el)) el.preload = \"auto\";\n        if (el.readyState === 1 && !el.seeking)")
sub("init.ts", "        const { el } = clip;\n        el.preload = \"metadata\";\n        withoutOwnTimingRecords(el, () => releaseMedia(el));", "        const { el } = clip;\n        if (!hasFrameSource(el)) el.preload = \"metadata\";\n        withoutOwnTimingRecords(el, () => releaseMedia(el));")
# mediaProxy.ts
sub("mediaProxy.ts", "    el.setAttribute(\"src\", original);\n  }\n  el.load();\n", "    el.setAttribute(\"src\", original);\n  }\n  if (!hasFrameSource(el)) el.load();\n")
sub("mediaProxy.ts", "  el.src = href;\n  el.load();\n", "  el.src = href;\n  if (!hasFrameSource(el)) el.load();\n")
# preloadMedia.ts
sub("preloadMedia.ts", "export function preloadMedia(media: PreloadableMedia): void {\n  if (isRenderFrameVideo(media)) return;", "export function preloadMedia(media: PreloadableMedia): void {\n  if (isRenderFrameVideo(media) || hasFrameSource(media)) return;")
sub("preloadMedia.ts", "  if (!isChromium()) return preloadMedia(media);\n  if (isRenderFrameVideo(media)) return;", "  if (!isChromium()) return preloadMedia(media);\n  if (isRenderFrameVideo(media) || hasFrameSource(media)) return;")
sub("preloadMedia.ts", "  media.removeAttribute(\"src\");\n  media.load();\n}", "  media.removeAttribute(\"src\");\n  if (!hasFrameSource(media)) media.load();\n}")
sub("preloadMedia.ts", "    if (later) media.preload = \"none\";\n    const restore = () => (media.preload = authoredPreload);", "    if (later && !hasFrameSource(media)) media.preload = \"none\";\n    const restore = () => void (hasFrameSource(media) || (media.preload = authoredPreload));")
print("ok")
