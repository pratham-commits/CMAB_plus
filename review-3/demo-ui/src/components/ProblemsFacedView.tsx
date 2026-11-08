/**
 * Interactive mirror of review-3/PROBLEMS.md — failures across Reviews I–III
 * and how we responded. Keep copy plain for visitors.
 */

type Entry = {
  problem: string;
  happened: string;
  response: string;
};

type PhaseBlock = {
  id: string;
  title: string;
  blurb: string;
  entries: Entry[];
  closing?: string;
};

const PHASES: PhaseBlock[] = [
  {
    id: "r1",
    title: "Review I — CUBIC paper reproduction",
    blurb:
      "Goal: reproduce the MMSys ’24 live LEO streaming artifact under TCP CUBIC with the paper clock shaper, and leave a clean baseline the later reviews can trust.",
    entries: [
      {
        problem: "Need a faithful reproduction, not a slide paraphrase",
        happened:
          "Course work required the same 160-run class of matrix (targets, duration, ABR set) that the paper used — anything less would not convince faculty.",
        response:
          "Cloned the MMSys artifact, ran the full CUBIC SHAPER=clock matrix, and archived session JSON plus figures with fixed metric rules (trim first 20%, rebuffer = buffer ≤ 0.05 s).",
      },
      {
        problem: "Occasional bad rounds at some targets",
        happened:
          "A single ugly round (especially around a 5 s target) can drag a mean if you hide it.",
        response:
          "Documented outlier culture explicitly: report which rounds are bad, keep the same trim/rebuffer definitions everywhere, and never silently drop sessions.",
      },
      {
        problem: "Open cross-layer question",
        happened:
          "The accepted baseline is CUBIC-centric. Faculty asked what changes when the sender uses BBR instead.",
        response:
          "Scoped Review II as the same matrix with BBR on nginx — not a new ABR paper yet, a transport extension with shaper parity.",
      },
    ],
  },
  {
    id: "r2",
    title: "Review II — BBR extension and the “7 second” scare",
    blurb:
      "Goal: same live matrix as Review I, but TCP BBR on the sender. The first finished run looked like CMAB collapsed; the fair rerun showed that was mostly a testbed story.",
    entries: [
      {
        problem: "First BBR 160-run looked catastrophic",
        happened:
          "At a 3 s target, CMAB showed roughly 7.2 s live latency and about 28% rebuffer while still requesting high bitrate. Easy (wrong) headline: “BBR breaks CMAB.”",
        response:
          "Kept the finished matrix as evidence, then forensics instead of publishing the scare number as the BBR result.",
      },
      {
        problem: "Wrong shaper for Review I parity (biggest confound)",
        happened:
          "That first run used SHAPER=trace (harsh ISL-style handovers). Review I used SHAPER=clock (mild periodic pulses). The comparison was unfair.",
        response:
          "Labeled the TRACE run as dataset D2 (appendix / failure analysis only). Reran the full matrix with SHAPER=clock as dataset D3 — the canonical Review II BBR result (~3.29 s, 0% rebuffer, ~5223 kbps at 3 s).",
      },
      {
        problem: "nginx / tc-trace restart bugs",
        happened:
          "Between Selenium sessions, qdisc state could stick (including near-100% loss), so even CUBIC looked broken on the patched stack until the shaper was fixed.",
        response:
          "Patched tc-trace.py (tc_del / HTB reinit) so docker restart nginx between jobs recovers cleanly; validated on both CUBIC and BBR.",
      },
      {
        problem: "Mixing transport effect with testbed drift",
        happened:
          "Early slides risked comparing Review I CUBIC clock to BBR TRACE as if only TCP CC changed.",
        response:
          "Hard rule in the notes: never mix D1/D2/D3 in one claim. Faculty one-liner: “7 s is D2; 3.3 s BBR is D3; Review I is D1.”",
      },
    ],
    closing:
      "Takeaway: under a fair clock shaper, CMAB stays healthy on BBR. The disaster number taught us shaper parity and control-path stress — it is not the fair BBR result.",
  },
  {
    id: "r3",
    title: "Review III — CMAB+ design search and stall guard",
    blurb:
      "Goal: stop old CMAB’s forced-6000 collapse when the link cannot carry the top rung, without wrecking the paper-clock case. Many designs failed before the final rules.",
    entries: [
      {
        problem: "Trial 1 — remove the upward probe entirely",
        happened:
          "Bitrate froze near 900 kbps. LinTS never left the bottom arm once forced exploration was deleted.",
        response:
          "Rejected. CMAB+ needs a feasible upward probe, not “no probe.”",
      },
      {
        problem: "Trial 2 — probe the highest feasible rung only",
        happened:
          "Bitrate recovered (~5 Mbps) but latency stayed high (~5 s at a 3 s target) with lots of thrashing.",
        response:
          "Kept feasible probe + throughput clamp as rules 1–2; still needed a safer step-down policy.",
      },
      {
        problem: "Trial 3 — step down whenever latency > target",
        happened:
          "Player walked to the 300 kbps bottom rung and stayed there with “perfect” latency — unusable quality.",
        response:
          "Rejected. Healthy players sit slightly above the target, so latency > target never clears.",
      },
      {
        problem: "Trials 4–7 — latency+1 s as the downswitch trigger",
        happened:
          "Looked tolerable on BBR clock, but on CUBIC the 3 s cell sat on the 4.0 s line and cut bitrate on a link that could still carry a high rung (final bad clock matrix ~4.02 s / ~3009 kbps vs old CMAB ~4955 kbps).",
        response:
          "Rejected live latency as the step-down trigger. Final rule steps down only when current quality exceeds measured safe throughput.",
      },
      {
        problem: "Capacity collapse of old CMAB",
        happened:
          "At a sustained 4 Mbit bottleneck, old CMAB stays at 6000 kbps and rebuffers ~66–82%.",
        response:
          "Trial 8 / final CMAB+ (rules 1–3): ~1470 kbps, 0% rebuffer, ~3.5–3.6 s — next to L2A. Kept as the main capacity claim.",
      },
      {
        problem: "Starlink TRACE still harsh after rules 1–3",
        happened:
          "Full TRACE matrices beat old CMAB (~80% → ~33% CUBIC rebuffer) but stayed far from L2A (~0–2% at a few hundred kbps).",
        response:
          "Added stall guard (rule 5): after a real empty buffer, hold quality using the worst of the last 8 throughputs until recovery. Spots first (do not break clock / 4 Mbit), then full TRACE rematrix with the final player (~15% CUBIC / ~8% BBR at 3 s). Still do not claim to beat L2A.",
      },
      {
        problem: "Stall-guard variants that looked clever",
        happened:
          "Spare-rung / force-bottom-rung experiments were flat or worse than the ~13% spot.",
        response:
          "Restored the simpler worst-of-8 / 12 healthy-decision hold on main and treated that as the keeper after clock and 4 Mbit gates passed.",
      },
      {
        problem: "Demo had to match the science",
        happened:
          "Early UI used a fake cricket loop, cryptic metric labels, and an Algorithm page that only restated rules in prose.",
        response:
          "Switched to a real CC BY cricket ladder with visible quality tiers, plain-language HUD, textbook Algorithm boxes, Phase 3 scenario explainers, and this Problems tab.",
      },
    ],
    closing:
      "What we still refuse to claim: CMAB+ generally beats L2A; 1 Mbit CUBIC is “solved”; or that five rounds equal a journal ten-round sweep.",
  },
];

export function ProblemsFacedView() {
  return (
    <article className="problems" aria-labelledby="problems-heading">
      <header className="problems__header">
        <p className="problems__eyebrow">Failure ledger · Reviews I → III</p>
        <h1 id="problems-heading">Problems we faced</h1>
        <p className="problems__lede">
          Every serious result in this project sits on top of false starts. This page lists
          what broke, what we mistakenly believed, and what we changed — across the CUBIC
          reproduction, the BBR extension, and the CMAB+ design search. Full write-up:{" "}
          <code>review-3/PROBLEMS.md</code>.
        </p>
      </header>

      {PHASES.map((phase) => (
        <section key={phase.id} className="problems__phase" aria-labelledby={`prob-${phase.id}`}>
          <h2 id={`prob-${phase.id}`}>{phase.title}</h2>
          <p className="problems__blurb">{phase.blurb}</p>
          <div className="problems__list">
            {phase.entries.map((entry) => (
              <article key={entry.problem} className="problems__card">
                <h3>{entry.problem}</h3>
                <dl>
                  <div>
                    <dt>What happened</dt>
                    <dd>{entry.happened}</dd>
                  </div>
                  <div>
                    <dt>What we did</dt>
                    <dd>{entry.response}</dd>
                  </div>
                </dl>
              </article>
            ))}
          </div>
          {phase.closing ? <p className="problems__closing">{phase.closing}</p> : null}
        </section>
      ))}
    </article>
  );
}
