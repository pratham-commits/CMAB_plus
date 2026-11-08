# CMAB+ trials

Same LinTS player as the paper. `cmabHardened=true` only on abrCMAB. Matrices are 4 ABR × targets 3/4/5/6 s × 10 rounds × 300 s, `SHAPER=clock`.

The comparison for a normal link is the unhardened BBR clock run, prefix `1017-0606`: CMAB at a 3 s target was 3.29 s, 0% rebuffer, 5223 kbps. L2A on these clock runs holds the target at about 6000 kbps.

## Trial 1 — no upward probe

Code: disable the paper's post-handover jump to the top rung. No replacement probe.

Run: BBR clock, prefix `1027-0300`, 160 sessions. Saved in `review-3/bbr-cmab-plus-stuck900/`.

Result: CMAB stayed at 900 kbps at every target. Latency was on target and rebuffer was about 0%. Dynamic, L2A, and LoLP were about 5000–6000 kbps. LinTS never left arm 0 once the forced top rung was removed.

## Trial 2 — probe the highest feasible rung

Code: in that same post-handover window, request the highest rung at or below safe throughput. LinTS after the window is clamped the same way. A clamped switch, or a buffer under 0.5 s, uses normal priority instead of strong.

Run: BBR clock, prefix `1027-2225`, 160 sessions. Saved in `review-3/bbr-cmab-plus-rerun/`.

Result: bitrate recovered (about 5200–5400 kbps). Latency did not. At 3 s, CMAB+ was 4.99 s with 1.0% rebuffer, against L2A at 3.12 s and 6000 kbps on the same run. Samples already at 6000 kbps still averaged 5.08 s, so the top rung fits this link. Arm 7 was the common choice, with drops to the bottom rungs (about 147 switches per session). Buffer was under 0.5 s for 16% of samples at the 3 s target, which is when this trial refused a strong switch.

## Trial 3 — step down while late, strong downswitch

Code: while live latency was strictly above the target, the applied rung could not rise and stepped one rung down per decision. A downward switch stayed strong.

Run: BBR clock, started 2026-10-30, stopped after 26 sessions. CMAB only.

Result: latency was on target (3.17 s at a 3 s target, 4.19 s at 4 s) with 0% rebuffer, and bitrate was **300 kbps**. The bottom rung. A normal player sits slightly above the target (L2A is 3.12 s at a 3 s target), so `latency > target` stayed true even after the step-down had done its job. The ladder walked to arm 0 and was not allowed back up.

## Trial 4 — step down only when clearly late

Code: the step-down waits until latency is more than 1 s above the target. The strong-downswitch rule from trial 3 stays.

Run: BBR clock, prefix `1030-0137`, 160 sessions. Saved in `review-3/bbr-cmab-plus-1030-0137/`.

| Target | CMAB+ latency | L2A latency | CMAB+ rebuffer | CMAB+ kbps | L2A kbps |
| --- | ---: | ---: | ---: | ---: | ---: |
| 3 s | 3.32 s | 3.11 s | 0% | 4894 | 6000 |
| 4 s | 4.21 s | 4.00 s | 0% | 5220 | 5550 |
| 5 s | 5.21 s | 5.06 s | 0% | 5244 | 6000 |
| 6 s | 6.23 s | 6.00 s | 0% | 5185 | 6000 |

CMAB+ session-mean latency spread at 3 s is 0.06 s. Dynamic and LoLP sit with L2A. Unhardened CMAB on the earlier clock run was 3.29 s, 0% rebuffer, 5223 kbps at a 3 s target.

This is the normal-link BBR result. Latency is about 0.2 s above the other algorithms and about the same as unhardened CMAB. Rebuffer is 0. Bitrate is in the 4900–5200 kbps range, below L2A at 6000 and below the 300/900 kbps failures.

## Trial 4 on CUBIC — partial, prefix 1031-0032

Same player as the BBR trial 4 run. Stopped after 7 CMAB sessions at a 3 s target: latency 3.98 s, 0% rebuffer, 3035 kbps. Old unhardened CUBIC CMAB was about 3.19 s and 4955 kbps. The 1 s step-down line for a 3 s target is 4.0 s. This run sat on that line. Under the line the probe still jumped to the highest feasible rung, which pushed latency back over the line.

## Trial 5 — climb one rung when not late

Code: a downward step while late stays. When latency is not late, the applied
rung may rise by at most one from the current quality, still capped by safe
throughput. CUBIC nginx is also started privileged, matching BBR, so `sysctl`
can set `cubic`.

Run: CUBIC clock, prefix `1031-2231`, 160 sessions.

| Target | CMAB+ latency | Rebuffer | CMAB+ kbps |
| --- | ---: | ---: | ---: |
| 3 s | 3.85 s | 0.04% | 2626 |
| 4 s | 4.36 s | 0% | 4224 |
| 5 s | 5.27 s | 0% | 4732 |
| 6 s | 6.24 s | 0% | 5081 |

Result: worse than old CUBIC CMAB at 3 s (3.19 s, 4955 kbps). The one-rung
climb was too slow to leave the lower rungs while latency stayed between 3 and
4 s.

## Trial 6 — full climb only when at or below target

Code: take the full feasible rung only while live latency is at or below the
target. Between target and target+1 s, climb half the gap. Above target+1 s,
step down.

Run: CUBIC clock, prefix `1101-2306`, stopped after the early CMAB block.

Result: at 3 s, 5.18 s latency, 0.56% rebuffer, and 708 kbps. At 4 s (four
sessions), 5.86 s, 0.19%, and 1174 kbps. Because latency started around 5 s,
the full-climb condition never fired. This design was rejected.

## Trial 7 — one-second step-down, final clock matrix

Code: revert to Trial 4. Above target+1 s, step down one and do not rise on
that decision. Otherwise take the throughput-clamped suggestion.

Run: CUBIC clock, prefix `1102-1304`, 160 sessions. Original tar:
`data/archives/cmab-plus-cubic-1102-1304.tar.gz`.

| Target | CMAB+ latency | Rebuffer | CMAB+ kbps | Old CUBIC CMAB |
| --- | ---: | ---: | ---: | --- |
| 3 s | 4.02 s | 0% | 3009 | 3.19 s, 0%, 4955 kbps |
| 4 s | 4.41 s | 0% | 4842 | 4.20 s, 0%, 4989 kbps |
| 5 s | 5.23 s | 0% | 5316 | 6.05 s, 2.52%, 4951 kbps |
| 6 s | 6.26 s | 0% | 5323 | 6.24 s, 0%, 5021 kbps |

Result: the 3 s line is 4.0 s, and the measured mean is 4.02 s. The latency
cut therefore reduced bitrate on a link that could still carry a high rung.
The same-run L2A player reached 5550 kbps at 4.06 s. The one-second latency
cut was rejected as the trigger for the final rule.

## Trial 8 — throughput-triggered step-down and capacity decision

Code, commit `c9af3e6` plus runner fixes through `c2a8db2`: keep the feasible
probe and throughput clamp. Step down only when the quality already playing is
faster than measured safe throughput. Latency by itself no longer triggers the
cut. The clock shaper accepts configurable rate and loss values. Old CMAB,
CMAB+, and L2A run in the same batch.

Matrix: 3 s target, 300 s/session, five rounds, 8/4/1 Mbit bottlenecks, mild
clock handovers, CUBIC and BBR. Ninety sessions total.

| TCP | Capacity | old CMAB | CMAB+ | L2A |
| --- | ---: | --- | --- | --- |
| CUBIC | 8 Mbit | 6.73 s, 3.31%, 5854 | 6.48 s, 2.85%, 5721 | 5.15 s, 0.45%, 5075 |
| CUBIC | 4 Mbit | 8.58 s, 82.25%, 6000 | 3.54 s, 0%, 1473 | 3.36 s, 0%, 1500 |
| CUBIC | 1 Mbit | 23.96 s, 98.79%, 6000 | 7.23 s, 16.54%, 888 | 3.47 s, 0%, 450 |
| BBR | 8 Mbit | 6.22 s, 1.77%, 5828 | 6.63 s, 3.49%, 5804 | 4.32 s, 0%, 6000 |
| BBR | 4 Mbit | 8.66 s, 65.69%, 6000 | 3.62 s, 0%, 1477 | 3.40 s, 0%, 1500 |
| BBR | 1 Mbit | 47.04 s, 99.13%, 6000 | 3.85 s, 0%, 450 | 3.69 s, 0%, 450 |

Each cell is latency, rebuffer, bitrate kbps. This is the first result that
supports the intended claim. At 4 Mbit under both transports, old CMAB's forced
6000 kbps choice collapses; CMAB+ selects the 1500 kbps rung, eliminates
rebuffer, and lands within 0.18–0.22 s of L2A. At 1 Mbit CUBIC, CMAB+ remains
too aggressive, proving the guard is not universally sufficient.

## After Trial 8 — clock / 4 Mbit / TRACE matrices (rules 1–3)

Full targets 3/4/5/6 s, five rounds, old CMAB / CMAB+ / L2A, CUBIC and BBR:

- Paper clock: CMAB+ ≈ old CMAB (non-regression).
- 4 Mbit: CMAB+ wins every target (0% rebuffer, ~1470 kbps).
- TRACE without stall guard: CUBIC rebuffer ~80% → ~33%; BBR ~9–12%. Still
  far from L2A. See `PROBLEMS.md` and `results/trace-targets-summary.md`
  history notes for the pre–stall-guard trees.

## Stall guard (rule 5) — spots then TRACE rematrix

Code tip `8d0596c`: after buffer ≤ 0.05 s, hold quality using the worst of the
last 8 throughputs until 12 decisions with buffer ≥ 1 s.

- Spots (3 s only): clock and 4 Mbit hold; TRACE CUBIC ~13%, BBR ~7%.
- Spare-rung / force-bottom variants rejected (flat or worse).
- Final TRACE rematrix with stall guard on: CUBIC 3 s CMAB+ ~14.7% / 851 kbps;
  BBR ~8.3% / 2658 kbps. Archive
  `data/archives/cmab-plus-trace-stallguard-cubic-bbr-20261108.tar.gz`.
