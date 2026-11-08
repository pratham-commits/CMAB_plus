import type { TimelineSample } from "./types";

export const STALL_THRESH = 0.05;

/** Binary-search nearest sample at or before playback time t. */
export function sampleAt(samples: TimelineSample[], t: number): TimelineSample | null {
  if (!samples.length) return null;
  if (t <= samples[0].t) return samples[0];
  if (t >= samples[samples.length - 1].t) return samples[samples.length - 1];
  let lo = 0;
  let hi = samples.length - 1;
  while (lo < hi) {
    const mid = (lo + hi + 1) >> 1;
    if (samples[mid].t <= t) lo = mid;
    else hi = mid - 1;
  }
  return samples[lo];
}

export function isStalling(sample: TimelineSample | null): boolean {
  return sample != null && sample.buffer <= STALL_THRESH;
}
