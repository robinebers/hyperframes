import { afterEach, expect, it, onTestFinished, vi } from "vitest";
import { registerFrameSource } from "./frameSources";
import { initSandboxRuntimeModular } from "./init";
import { installPausedVideoCallbacks } from "./pausedVideoCallbacks";
import { getPausedVideoFrame } from "./pausedVideoFrames";
import { createMockTimeline, resetRuntimeFixtureDom } from "./runtimeSeekFixture.test-helpers";

const disposers: Array<() => void> = [];

/**
 * A ten-second film whose video #cam has a frame source and no src of its own, played on a hand-driven clock. The
 * source can play while `canPlay.value` is true; `videoAttrs` replaces the video's timing attributes.
 */
function playWithFrameSource({
  videoAttrs = 'data-start="0" data-duration="4"',
  length,
  received,
  picture,
}: {
  videoAttrs?: string;
  length?: () => number | undefined;
  received?: () => number;
  picture?: () => { canvas: HTMLCanvasElement; time: number } | null;
} = {}) {
  resetRuntimeFixtureDom();
  document.body.innerHTML =
    '<div data-composition-id="main" data-root="true" data-duration="10">' +
    `<video id="cam" data-track-index="0" ${videoAttrs}></video>` +
    "</div>";
  const cam = document.getElementById("cam") as HTMLVideoElement;
  vi.spyOn(HTMLMediaElement.prototype, "play").mockResolvedValue(undefined);
  vi.spyOn(HTMLMediaElement.prototype, "load").mockImplementation(() => {});
  const canPlay = { value: false };
  const asked: number[] = [];
  disposers.push(
    registerFrameSource({
      element: cam,
      render: (sourceTime) => void asked.push(sourceTime),
      canPlayAt: () => canPlay.value,
      length,
      received,
      picture,
    }),
  );
  window.__timelines = { main: createMockTimeline(10) };

  let now = 0;
  const frames = new Map<number, FrameRequestCallback>();
  let nextFrame = 0;
  vi.spyOn(performance, "now").mockImplementation(() => now);
  window.requestAnimationFrame = (cb) => (frames.set(++nextFrame, cb), nextFrame);
  window.cancelAnimationFrame = (id) => void frames.delete(id);
  const states: Array<{ isPlaying: boolean; buffering: boolean }> = [];
  vi.spyOn(window.parent, "postMessage").mockImplementation((message: unknown) => {
    const m = message as { type?: string; isPlaying: boolean; buffering: boolean };
    if (m?.type === "state") states.push({ isPlaying: m.isPlaying, buffering: m.buffering });
  });

  initSandboxRuntimeModular();
  const playFor = (seconds: number) => {
    for (let ms = 0; ms < seconds * 1000; ms += 1000 / 60) {
      now += 1000 / 60;
      const due = [...frames.values()];
      frames.clear();
      for (const cb of due) cb(now);
    }
  };
  return { cam, canPlay, asked, states, playFor };
}

afterEach(() => {
  for (const dispose of disposers.splice(0)) dispose();
  window.__hfRuntimeTeardown?.();
  vi.restoreAllMocks();
  resetRuntimeFixtureDom();
});

it("a video whose frame source cannot play yet holds the film with Buffering, and resumes once it can", () => {
  const { canPlay, states, playFor } = playWithFrameSource();
  window.__player!.play();

  playFor(1);
  expect(window.__player!.getTime()).toBeLessThan(0.1);
  expect(states.at(-1)).toEqual({ isPlaying: true, buffering: true });

  canPlay.value = true;
  playFor(1);
  expect(window.__player!.getTime()).toBeGreaterThan(0.9);
  expect(states.at(-1)).toEqual({ isPlaying: true, buffering: false });
});

it("a frame source that never can play stops holding the film after 8 s, as a clip without data does", () => {
  const { states, playFor } = playWithFrameSource();
  window.__player!.play();

  playFor(7);
  expect(window.__player!.getTime()).toBeLessThan(0.1);
  expect(states.at(-1)).toEqual({ isPlaying: true, buffering: true });

  playFor(2);
  expect(window.__player!.getTime()).toBeGreaterThan(0.5);
  expect(states.at(-1)).toEqual({ isPlaying: true, buffering: false });
});

it("a frame source still receiving data keeps holding the film past 8 s", () => {
  let bytes = 0;
  const { states, playFor } = playWithFrameSource({ received: () => bytes });
  window.__player!.play();

  for (let s = 0; s < 12; s++) {
    bytes += 1000;
    playFor(1);
  }
  expect(window.__player!.getTime()).toBeLessThan(0.1);
  expect(states.at(-1)).toEqual({ isPlaying: true, buffering: true });

  playFor(9);
  expect(window.__player!.getTime()).toBeGreaterThan(0.5);
  expect(states.at(-1)).toEqual({ isPlaying: true, buffering: false });
});

it("scripts reading a video's pixels get its frame source's picture, and its frame callbacks fire", async () => {
  const proto = HTMLVideoElement.prototype;
  const descriptors = Object.getOwnPropertyDescriptors(proto);
  onTestFinished(() => {
    for (const name of ["requestVideoFrameCallback", "cancelVideoFrameCallback"] as const) {
      if (descriptors[name]) Object.defineProperty(proto, name, descriptors[name]);
      else Reflect.deleteProperty(proto, name);
    }
  });
  Object.assign(proto, { requestVideoFrameCallback: () => 1, cancelVideoFrameCallback: () => {} });
  installPausedVideoCallbacks();
  const shown = document.createElement("canvas");
  const { cam, canPlay, playFor } = playWithFrameSource({
    picture: () => ({ canvas: shown, time: 0 }),
  });
  const frames: number[] = [];
  cam.requestVideoFrameCallback((_now, metadata) => void frames.push(metadata.mediaTime));
  canPlay.value = true;
  window.__player!.play();
  playFor(0.5);

  expect(getPausedVideoFrame(cam)).toBe(shown);
  await vi.waitFor(() => expect(frames).toEqual([0]));
});

it("the runtime never loads, seeks or plays a video its frame source supplies, even one with a src", () => {
  const { cam, canPlay, playFor } = playWithFrameSource({
    videoAttrs: 'data-start="0" data-duration="4" src="/cam.mp4"',
  });
  const load = vi.spyOn(cam, "load").mockImplementation(() => {});
  const play = vi.spyOn(cam, "play").mockImplementation(() => Promise.resolve());
  const seek = vi.fn();
  Object.defineProperty(cam, "currentTime", { get: () => 0, set: seek, configurable: true });
  canPlay.value = true;

  window.__player!.play();
  playFor(1);
  window.__player!.seek(2);
  window.__player!.pause();
  window.__player!.play();
  playFor(1);

  expect(load).not.toHaveBeenCalled();
  expect(play).not.toHaveBeenCalled();
  expect(seek).not.toHaveBeenCalled();
});

it("a frame source gives the source time it is asked for, trims and speed included, to the page", async () => {
  const { cam, canPlay, asked, playFor } = playWithFrameSource({
    videoAttrs: 'data-start="2" data-duration="4" data-media-start="5" data-playback-rate="2"',
  });
  canPlay.value = true;
  window.__player!.seek(3);
  playFor(0.1);

  expect(window.__hf!.sourceTimeAt!(cam, 3)).toBeCloseTo(7);
  await vi.waitFor(() => expect(asked.at(-1)).toBeCloseTo(7));
});

it("a looping video's frame source is asked for source times that wrap at its length", () => {
  const { cam, playFor } = playWithFrameSource({
    videoAttrs: 'data-start="0" data-duration="8" data-media-start="1" loop',
    length: () => 4,
  });
  playFor(0.1);

  expect(window.__hf!.sourceTimeAt!(cam, 2)).toBeCloseTo(3);
  expect(window.__hf!.sourceTimeAt!(cam, 4)).toBeCloseTo(2);
});

it("a video the page gives no length lasts as long as its frame source says its source is", () => {
  let length: number | undefined;
  const { cam, playFor } = playWithFrameSource({
    videoAttrs: 'data-start="1" data-media-start="2"',
    length: () => length,
  });
  playFor(0.1);

  length = 6;
  cam.dispatchEvent(new Event("durationchange"));
  playFor(0.1);

  expect(window.__hf!.clipWindow!(cam)).toEqual({ start: 1, end: 5 });
});
