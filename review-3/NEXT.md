# Next checklist

Conference experiment matrices are complete. Final player = CMAB+ rules 1–5
(including stall guard). Remaining work is paper + demo UI, not more runs.

## Done

- [x] Capacity decision 8/4/1 Mbit (CUBIC+BBR), figures under `figures/` and
  `figures/review2-style/`.
- [x] Clock non-regression, targets 3/4/5/6, CUBIC+BBR (5 rounds).
- [x] 4 Mbit target robustness, targets 3/4/5/6, CUBIC+BBR (5 rounds).
- [x] Stall-guard spots: clock / 4 Mbit / trace × CUBIC+BBR. Clock and 4 Mbit
  hold; trace CUBIC ~13%, BBR ~7% at 3 s.
- [x] Trace validity with **final** player (stall guard on), targets 3/4/5/6,
  CUBIC+BBR (5 rounds, 120 sessions). Archive
  `data/archives/cmab-plus-trace-stallguard-cubic-bbr-20261108.tar.gz`.
  Regenerated `figures/trace-targets/` and `results/trace-targets-*`.
  Headline 3 s: CUBIC CMAB+ ~14.7% rebuffer / 851 kbps; BBR ~8.3% / 2658 kbps.
  Old CMAB still ~81% / ~29%. L2A still best on rebuffer.

## Now (non-experiment)

- [ ] Stop the GCP VM if it is still running.
- [ ] Conference paper draft from locked figures (clock / 4 Mbit / capacity /
  trace) + algorithm 1–5 + limitations.
- [ ] Comprehensive demo UI: Phase 1 (Review I) + Phase 2 (Review II) +
  Phase 3 (Review III, including stall-guard tab).
- [ ] Dry-run demo once before evaluation.

## Explicitly skipped for conference

- Ten-round rematrix of every cell.
- Full ablations / Dynamic rematrix.
- Re-running clock and 4 Mbit multi-target under stall guard (spots suffice).
