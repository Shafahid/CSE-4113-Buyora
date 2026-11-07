export const LOOP_PAUSE_MS = 2000;
export type Playback = { tick: number; playing: boolean; speed: number };
export function advancePlayback(
  playback: Playback,
  finalTick: number,
  loop: boolean,
): Playback {
  if (!playback.playing) return playback;
  if (playback.tick >= finalTick)
    return { ...playback, tick: loop ? 0 : finalTick, playing: loop };
  const tick = Math.min(finalTick, playback.tick + 1);
  return { ...playback, tick, playing: loop || tick < finalTick };
}
export function playbackDelay(
  playback: Playback,
  finalTick: number,
  loop: boolean,
) {
  return loop && playback.tick >= finalTick
    ? LOOP_PAUSE_MS
    : 280 / playback.speed;
}
