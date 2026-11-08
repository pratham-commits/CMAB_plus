/** Ladder rungs aligned with the livesim / paper ABR ladder. */
export type QualityTier = {
  kbps: number;
  label: "Low" | "Medium" | "High" | "Ultra";
  file: string;
  /** CSS filter applied on top of the encode for an obvious visual step. */
  filter: string;
};

export const QUALITY_LADDER: QualityTier[] = [
  {
    kbps: 300,
    label: "Low",
    file: "video/cricket-300.mp4",
    filter: "contrast(0.88) saturate(0.8) blur(0.6px)",
  },
  {
    kbps: 900,
    label: "Medium",
    file: "video/cricket-900.mp4",
    filter: "contrast(0.95) saturate(0.92)",
  },
  {
    kbps: 1500,
    label: "High",
    file: "video/cricket-1500.mp4",
    filter: "saturate(1.05) contrast(1.05)",
  },
  {
    kbps: 6000,
    label: "Ultra",
    file: "video/cricket-6000.mp4",
    filter: "saturate(1.08) contrast(1.08) brightness(1.02)",
  },
];

/** Map a timeline sample bitrate (kbps) onto the nearest ladder rung. */
export function tierForBitrate(kbps: number | null | undefined): QualityTier {
  if (kbps == null || !Number.isFinite(kbps) || kbps <= 0) {
    return QUALITY_LADDER[0];
  }
  let best = QUALITY_LADDER[0];
  let bestDist = Math.abs(kbps - best.kbps);
  for (const tier of QUALITY_LADDER) {
    const dist = Math.abs(kbps - tier.kbps);
    if (dist < bestDist) {
      best = tier;
      bestDist = dist;
    }
  }
  return best;
}

export function qualityCaption(tier: QualityTier, sampleKbps: number | null): string {
  const live =
    sampleKbps != null && Number.isFinite(sampleKbps) && sampleKbps > 0
      ? Math.round(sampleKbps)
      : tier.kbps;
  return `Video quality: ${live} kbps (${tier.label})`;
}
