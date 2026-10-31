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

Code, not yet run: a downward step while late stays. When latency is not late, the applied rung may rise by at most one from the current quality, still capped by safe throughput. Cubic nginx is also started privileged, matching the BBR file, so `sysctl` can set `cubic`.

Check on CUBIC at a 3 s target before leaving a full matrix: latency near 3.2 s and bitrate near 5000 kbps. The aggressive trace case is still untested.
