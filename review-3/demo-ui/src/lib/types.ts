export type PlayerMetrics = {
  latency_s: number;
  rebuffer_pct: number;
  bitrate_kbps: number;
};

export type TimelineSample = {
  t: number;
  buffer: number;
  bitrate: number;
  latency: number;
};

export type TimelinePayload = {
  session: string;
  source: string;
  round: number;
  metrics: PlayerMetrics;
  t0: string | null;
  duration_s: number;
  samples: TimelineSample[];
};

export type PlayerEntry = {
  player: string;
  status: "ok" | "missing";
  note?: string;
  round?: number;
  session?: string;
  source?: string;
  metrics: PlayerMetrics | null;
  timeline: string | null;
};

export type CatalogCell = {
  id: string;
  phase: number;
  family: string;
  label: string;
  transport: string | null;
  axis: string | null;
  axisValue: string | number | null;
  note: string | null;
  placeholder: boolean;
  players: Record<string, PlayerEntry>;
};

export type Catalog = {
  generated_at: string;
  video: string;
  handover: {
    period_s: number;
    slots_within_minute: number[];
    description: string;
  };
  metrics: Record<string, string>;
  summary: {
    cells: number;
    wired: number;
    placeholders: number;
    session_timelines: number;
  };
  phases: { id: number; name: string; families: string[] }[];
  cells: CatalogCell[];
};
