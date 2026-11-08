# Problems we faced (Review I → III)

Ledger of failures, false starts, and how we recovered. The interactive demo
**Problems we faced** tab mirrors this file.

## Review I — CUBIC paper reproduction

| Problem | What happened | What we did |
| --- | --- | --- |
| Reproduce MMSys ’24 under course constraints | Needed a faithful 160-run clock matrix, not a slide paraphrase | Cloned the artifact, ran the full CUBIC `SHAPER=clock` matrix, archived figures and JSON |
| 5 s target CMAB outlier culture | Occasional bad rounds inflate means if undocumented | Forensic notes: report outlier rounds explicitly; keep trim/rebuffer definitions fixed |
| Cross-layer question left open | Paper is CUBIC-centric; faculty asked what BBR does | Planned Review II as same matrix, BBR on the sender |

## Review II — BBR extension

| Problem | What happened | What we did |
| --- | --- | --- |
| First BBR 160-run looked catastrophic | CMAB ~7.2 s latency, ~28% rebuffer at 3 s | Finished the matrix, then investigated instead of claiming “BBR breaks CMAB” |
| Wrong shaper for Review I parity | Run used `SHAPER=trace` (harsh ISL handovers) while Review I used `SHAPER=clock` | Documented as D2 (appendix only); reran with `SHAPER=clock` as D3 |
| nginx / `tc-trace.py` restart bugs | Between sessions, HTB/qdisc state could stick at 100% loss | Patched `tc_del()` / HTB reinit so restarts survive; validation runs on both CCs |
| Confounding “BBR vs CUBIC” with testbed drift | Early read mixed transport effect with shaper/nginx faults | Separated datasets D1/D2/D3; faculty line: 7 s is D2, 3.3 s BBR is D3 |
| Plotting overlap | CUBIC vs BBR markers stacked | Dodged series in comparison plots |

Canonical fair result: BBR clock prefix `1017-0606` — CMAB ~3.29 s, 0% rebuffer, ~5223 kbps at 3 s.

## Review III — CMAB+ design search

| Trial / problem | What happened | What we did |
| --- | --- | --- |
| Trial 1 — remove top-rung probe | Bitrate stuck ~900 kbps; LinTS never left arm 0 | Rejected. Need a feasible upward probe, not “no probe” |
| Trial 2 — feasible probe only | Bitrate recovered (~5 Mbps) but latency ~5 s at 3 s target | Kept probe+clamp; still needed a safe step-down story |
| Trial 3 — step down while `latency > target` | Walked to **300 kbps** bottom rung and stayed there | Rejected. Normal players sit slightly above target, so the predicate never clears |
| Trial 4 — step down only if `latency > target+1s` (BBR) | Looked OK on BBR clock (~3.3 s, ~5 Mbps) | Candidate briefly; CUBIC check required |
| Trial 4 CUBIC / Trials 5–7 | One-second latency cut sat on the 4.0 s line and cut bitrate on a link that could still carry a high rung (`1102-1304`: 4.02 s, 3009 kbps vs old CMAB ~4955) | **Rejected latency as the downswitch trigger** |
| Trial 8 — throughput-triggered step-down | At 4 Mbit: old CMAB ~70–80% rebuffer @ 6000; CMAB+ ~0% @ ~1470 kbps | **Kept** as core of CMAB+ (rules 1–3) |
| 1 Mbit CUBIC still weak | ~16% rebuffer @ ~888 kbps vs L2A 450 kbps / 0% | Documented limitation; not claimed as solved |
| Clock / 4 Mbit / TRACE matrices (5 rounds) | Needed non-reg + target robustness + real ISL validity | Ran full targets 3/4/5/6 on both CCs; TRACE without stall guard still ~33% CUBIC rebuffer |
| Stall-guard design loop | Spares/bottom-rung variants flat or worse; spots hit ~13% CUBIC TRACE | Restored worst-of-8 / 12-decision hold (`8d0596c`); gated on clock+4 Mbit spots first |
| TRACE final matrix with stall guard | Needed paper tables under final player | Reran TRACE CUBIC+BBR; 3 s CUBIC ~15% / 851 kbps, BBR ~8% / 2658 kbps; still behind L2A on rebuffer |
| Demo UX polish | Fake cricket loop; cryptic labels; rules-only Algorithm page | Real CC BY cricket ladder, quality switching, textbook Algorithm boxes, Problems tab |

## What we still do not claim

- CMAB+ does not generally beat L2A (especially on Starlink TRACE rebuffer).
- Five rounds are conference-grade, not a ten-round journal sweep.
- Clock / 4 Mbit multi-target archives were measured under rules 1–3; spots show stall guard stays off there. TRACE multi-target tables use rules 1–5.
