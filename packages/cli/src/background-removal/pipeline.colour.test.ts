import { spawnSync } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterAll, describe, expect, it } from "vitest";
import { findFFmpeg, findFFprobe } from "../browser/ffmpeg.js";
import { buildDecoderArgs, buildEncoderArgs } from "./pipeline.js";

const ffmpeg = findFFmpeg();
const ffprobe = findFFprobe();
const SIZE = 64;
const dir = mkdtempSync(join(tmpdir(), "hf-cutout-colour-"));
afterAll(() => rmSync(dir, { recursive: true, force: true }));

function run(bin: string, args: string[], input?: Buffer): Buffer {
  const result = spawnSync(bin, args, { input, maxBuffer: 64 * 1024 * 1024 });
  if (result.status !== 0) throw new Error(result.stderr.toString());
  return result.stdout;
}

function recording(name: string, colour: string): string {
  const path = join(dir, `${name}.mkv`);
  const bt709 = ["-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709"];
  run(ffmpeg!, [
    ...[
      "-y",
      "-loglevel",
      "error",
      "-f",
      "lavfi",
      "-i",
      `color=c=${colour}:s=${SIZE}x${SIZE}:d=0.2`,
    ],
    ...["-vf", "format=yuv420p", "-c:v", "ffv1", ...bt709, "-color_range", "tv", path],
  ]);
  return path;
}

const decode = (path: string) => run(ffmpeg!, buildDecoderArgs(path));

function cutOut(source: string, name: string): string {
  const rgb = decode(source);
  const rgba = Buffer.alloc(SIZE * SIZE * 4, 255);
  for (let i = 0; i < SIZE * SIZE; i++) rgb.copy(rgba, i * 4, i * 3, i * 3 + 3);
  const output = join(dir, `${name}.webm`);
  run(ffmpeg!, buildEncoderArgs("webm", SIZE, SIZE, 10, output, "best"), rgba);
  return output;
}

const channelMeans = (rgb: Buffer) =>
  [0, 1, 2].map((c) => {
    let sum = 0;
    for (let i = c; i < rgb.length; i += 3) sum += rgb[i]!;
    return sum / (rgb.length / 3);
  });

describe.skipIf(!ffmpeg || !ffprobe)("background-removal cut-out colour", () => {
  it.each([
    ["shadow", "0x3a2621"],
    ["skin", "0xb4766e"],
    ["highlight", "0xe8c8b8"],
  ])("keeps a BT.709 recording's %s level in the cut-out", (name, colour) => {
    const source = recording(name, colour);
    const cutout = channelMeans(decode(cutOut(source, name)));
    channelMeans(decode(source)).forEach((level, channel) => {
      expect(Math.abs(cutout[channel]! - level)).toBeLessThan(0.5);
    });
  });

  it("labels the cut-out BT.709 like the recording under it", () => {
    const cutout = cutOut(recording("tags", "0xb4766e"), "tags");
    const entries = "stream=color_range,color_space,color_transfer,color_primaries";
    const tags = run(ffprobe!, [
      "-v",
      "error",
      "-select_streams",
      "v:0",
      "-of",
      "csv=p=0",
      "-show_entries",
      entries,
      "--",
      cutout,
    ]);
    expect(tags.toString().trim()).toBe("tv,bt709,bt709,bt709");
  });
});
