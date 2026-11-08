type Explainer = {
  what: string;
  scenario: string;
  observe: string;
};

/** Copy keyed by Phase 3 family ids (see FAMILY_LABELS / catalog families). */
const EXPLAINERS: Record<string, Explainer> = {
  capacity: {
    what: "A flat-capacity sweep: the link is held at a fixed bitrate — 8, 4, or 1 Mbit/s — while the three ABR players run the same live session. No Starlink handover chaos; just “how much pipe do we have?”",
    scenario:
      "Think of a phone stuck on a congested cell tower, or a café Wi‑Fi hop that tops out at a few megabits. Capacity does not swing every 15 seconds the way LEO handovers do — it is simply too small (or just enough) for the highest video rungs.",
    observe:
      "At 8 Mbit, all three players can usually sit high without drama. At 4 Mbit, old CMAB still lunges for ~6000 kbps after each slot and stalls; CMAB+ stays near the 1500 kbps rung and keeps playing. At 1 Mbit, everyone is squeezed — watch whether CMAB+ settles near a feasible rung (~900 kbps) instead of thrashing the top of the ladder. Compare rebuffer overlays and the on-video quality labels across the three panes.",
  },
  "clock-nonreg": {
    what: "Paper-clock non-regression: the network follows the original Zhao & Pan clock-style LEO schedule (healthy capacity with regular 15 s handover slots). CMAB+ should not get worse than old CMAB on this “good day” link.",
    scenario:
      "A clean LEO path with predictable satellite handovers — enough throughput for high quality most of the time. This is the environment the paper’s CMAB was designed for, so hardening must not punish it.",
    observe:
      "Old CMAB, CMAB+, and L2A should all look healthy: high rungs, little or no rebuffer. Stall guard stays inactive here (buffer stays above 0.05 s). If CMAB+ looks worse than old CMAB on clock, that is a regression — this family is the check that “fixing the 4 Mbit bug” did not break the good case.",
  },
  "capacity-4mbit-targets": {
    what: "Same flat 4 Mbit bottleneck as the capacity sweep, but across the paper’s live-latency targets (different target latency settings). Tests whether CMAB+ still protects the 4 Mbit case when the catch-up / latency goal changes.",
    scenario:
      "A fixed bottleneck backhaul (hotel Wi‑Fi, rural DSL, or a capped mobile plan) while the live stream aims for different end-to-end latency targets — tighter targets push the player harder.",
    observe:
      "Across targets, old CMAB should still overshoot into rebuffer after slot boundaries; CMAB+ should keep probing/clamping near ~1500 kbps with near-zero rebuffer. L2A is a third reference. Do not expect stall guard to fire on flat 4 Mbit — buffer usually stays above the 0.05 s tripwire.",
  },
  "trace-targets": {
    what: "Real Starlink TRACE capacity (measured LEO variability) with CMAB+ stall guard enabled, swept across latency targets. This is the harsh, realistic path — throughput dips and recovers around handovers.",
    scenario:
      "Watching a live match over Starlink: every ~15 s a satellite handover can slash throughput for a moment. The player must not keep requesting a 6000 kbps rung when the link just fell to a few megabits — and if the buffer actually empties, stall guard should stop climbing until the pipe recovers.",
    observe:
      "Look for old CMAB freezing/rebuffering after handovers while CMAB+ either stays on a feasible rung or, when the buffer hits ≤0.05 s, refuses to climb (stall guard). L2A gives a non-CMAB baseline. Quality labels and the amber rebuffer overlay tell the story faster than the numeric HUD.",
  },
  "stall-guard-spots": {
    what: "Focused spot checks for rule 5 (stall guard): clock and flat 4 Mbit sessions where the guard should stay off, plus TRACE sessions where it may engage when the buffer collapses.",
    scenario:
      "Three everyday situations side by side — (1) healthy paper-clock LEO, (2) steady 4 Mbit bottleneck, (3) choppy Starlink TRACE. Only the TRACE-like case should ever trip the “buffer almost empty” guard.",
    observe:
      "On clock and 4 Mbit cells: CMAB+ behaves like rules 1–3 only; no long stall-guard lockdown. On TRACE cells: when a pane shows Rebuffering…, CMAB+ should avoid climbing afterward until the buffer has recovered for many decisions. Contrast with old CMAB, which has no stall guard and often re-probes high after a stall.",
  },
};

type Props = {
  family: string;
};

export function PhaseExplainer({ family }: Props) {
  const copy = EXPLAINERS[family];
  if (!copy) return null;

  return (
    <section className="explainer" aria-label={`About ${family}`}>
      <div className="explainer__grid">
        <div className="explainer__block">
          <h3>What is this?</h3>
          <p>{copy.what}</p>
        </div>
        <div className="explainer__block">
          <h3>Real-life scenario</h3>
          <p>{copy.scenario}</p>
        </div>
        <div className="explainer__block explainer__block--observe">
          <h3>What should you observe?</h3>
          <p>{copy.observe}</p>
        </div>
      </div>
    </section>
  );
}
