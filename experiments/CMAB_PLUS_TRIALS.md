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

Code, not yet run:

- While live latency is above the target, the applied rung cannot rise. It steps one rung down from the current quality. The next decision can step down again until latency is back at or under the target.
- Normal priority only when an upward switch was cut down to safe throughput. A downward switch stays strong, including when the buffer is thin.

What would count as better than trial 2: at a 3 s target, latency near 3.3 s rather than 5 s, rebuffer near 0%, bitrate still in the 5000 kbps range rather than 900 kbps. Do not start the CUBIC matrix until a BBR run shows that.
