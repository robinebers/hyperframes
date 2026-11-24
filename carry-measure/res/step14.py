
R="/workspace/wt-walk/packages/core/src/runtime/"
def sub(f, old, new):
    p=R+f; s=open(p).read(); assert s.count(old)==1,(f,old,s.count(old)); open(p,"w").write(s.replace(old,new))
open(R+"sourceLength.ts","w").write('''const supplied = new WeakMap<object, () => number | undefined>();

/** A frame source's answer for the element's length; undefined removes it. */
export function supplySourceLength(
  media: object,
  length: (() => number | undefined) | undefined,
): void {
  if (length) supplied.set(media, length);
  else supplied.delete(media);
}

/** The source length: the element's own, else its frame source's; NaN. */
export function sourceLengthOf(media: { duration: number }): number {
  if (Number.isFinite(media.duration)) return media.duration;
  return supplied.get(media)?.() ?? Number.NaN;
}
''')
sub("clipTree.ts", 'import type { RuntimeTimelineLike } from "./types";\n', 'import { sourceLengthOf } from "./sourceLength";\nimport type { RuntimeTimelineLike } from "./types";\n')
sub("clipTree.ts", "    return Number.isFinite(el.duration)\n      ? resolveNaturalMediaTimelineDuration(el, el.duration)", "    return Number.isFinite(sourceLengthOf(el))\n      ? resolveNaturalMediaTimelineDuration(el, sourceLengthOf(el))")
sub("init.ts", "// fallow-ignore-file code-duplication complexity\n", "// fallow-ignore-file code-duplication complexity\nimport { sourceLengthOf } from \"./sourceLength\";\n")
sub("init.ts", "        const sourceDuration = Number.isFinite(element.duration)\n          ? resolveNaturalMediaTimelineDuration(element, element.duration)", "        const sourceDuration = Number.isFinite(sourceLengthOf(element))\n          ? resolveNaturalMediaTimelineDuration(element, sourceLengthOf(element))")
sub("media.ts", 'import { wallClearTimeout, wallSetTimeout } from "./wallClock";\n', 'import { sourceLengthOf } from "./sourceLength";\nimport { wallClearTimeout, wallSetTimeout } from "./wallClock";\n')
sub("media.ts", "    const sourceDuration = Number.isFinite(el.duration) && el.duration > 0 ? el.duration : null;", "    const length = sourceLengthOf(el);\n    const sourceDuration = Number.isFinite(length) && length > 0 ? length : null;")
p=R+"playbackRate.ts"; s=open(p).read(); s='import { sourceLengthOf } from "./sourceLength";\n'+s; open(p,"w").write(s)
sub("playbackRate.ts", "    sourceDurationSeconds: Number.isFinite(el.duration) ? el.duration : null,", "    sourceDurationSeconds: Number.isFinite(sourceLengthOf(el)) ? sourceLengthOf(el) : null,")
sub("playbackRate.ts", "    ? resolveNaturalMediaTimelineDuration(el, el.duration)\n    : resolved.seconds;", "    ? resolveNaturalMediaTimelineDuration(el, sourceLengthOf(el))\n    : resolved.seconds;")
p=R+"startResolver.ts"; s=open(p).read(); s='import { sourceLengthOf } from "./sourceLength";\n'+s; open(p,"w").write(s)
sub("startResolver.ts", "          ? resolveNaturalMediaTimelineDuration(element, element.duration)", "          ? resolveNaturalMediaTimelineDuration(element, sourceLengthOf(element))")
p=R+"timeline.ts"; s=open(p).read(); s='import { sourceLengthOf } from "./sourceLength";\n'+s; open(p,"w").write(s)
sub("timeline.ts", "      if (Number.isFinite(node.duration)) {\n        duration = resolveNaturalMediaTimelineDuration(node, node.duration);", "      if (Number.isFinite(sourceLengthOf(node))) {\n        duration = resolveNaturalMediaTimelineDuration(node, sourceLengthOf(node));")
print("ok")
