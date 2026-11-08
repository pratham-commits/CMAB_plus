# Capacity experiment methodology

## Research question

Does a throughput-feasible CMAB bootstrap prevent the original CMAB player from
collapsing when the network cannot carry the top video rung, while preserving
reasonable latency and quality?

## Compared players

- **old CMAB**: original LinTS controller. During the first `|A|-1` decisions
  after each 15 s slot boundary, it forces the absolute top rung.
- **CMAB+**: same LinTS controller, with a feasible probe, a throughput clamp,
  and a one-rung step-down when the quality already playing exceeds measured
  safe throughput.
- **L2A**: included as a conservative low-latency reference, not as the claimed
  algorithm being replaced.

Old CMAB and CMAB+ use the same `abrCMAB` player. The batch enables
`cmabHardened=true` only for CMAB+ and gives its result folders the
`abrCMABPlus` prefix.

## Code

- Policy change: `c9af3e6` — throughput-triggered step-down and configurable
  clock shaper.
- Runner corrections: `1e77ba6`, `0e5f08d`, `c2a8db2`.
- Final tested code: `c2a8db2`.
- Batch: `experiments/batch-capacity-decision.json`.
- Runner: `experiments/run-capacity-decision.sh`.

## Network

The clock shaper uses `tc` TBF plus netem.

- Bottleneck: 8, 4, or 1 Mbit in separate blocks.
- Normal delay: 40 ms.
- Normal loss: 0.1%.
- Handover seconds: 12, 27, 42, and 57 of every wall-clock minute.
- Handover rate: unchanged from the configured bottleneck.
- Handover delay: 100 ms.
- Handover loss: 1%.
- Handover duration setting: 0, meaning the listed wall-clock second.
- TCP: CUBIC and BBR, run sequentially.

This is a controlled capacity experiment, not the trace shaper. It isolates
whether the video ladder fits the bottleneck while retaining the paper's mild
periodic handover disturbance.

## Matrix

- 3 capacities.
- 2 congestion controls.
- 3 players.
- 5 independent 300 s sessions per cell.
- 3 s target latency.
- Total: 90 sessions and 7.5 hours of streamed video.

The approximate video ladder is 300, 450, 900, 1200, 1500, 4900, 5100, and
6000 kbps. The 4 Mbit bottleneck deliberately falls in the large gap between
1500 and 4900 kbps.

## Metrics

The analysis is implemented in `analyze_capacity.py`.

- **Mean live latency**: values from `playback_latency.json`, after dropping
  the first 20% in time order.
- **Rebuffer sample ratio**: post-trim values in `buffer.json` at or below
  0.05 s, divided by all post-trim buffer samples.
- **Mean bitrate**: positive values in `bitrates.json`, after dropping the
  first 20%.
- Aggregate values are means of five session-level values.
- Figure error bars are two-sided 95% t intervals over the five session means
  (`t=2.776`, four degrees of freedom).

## Reproduction

From the course repository root:

```bash
python3 review-3/analyze_capacity.py
```

The script requires exactly 90 sessions and exits if the extracted data are
incomplete. It rewrites:

- `results/capacity-session-metrics.csv`
- `results/capacity-aggregate-metrics.csv`
- `results/capacity-summary.md`
- all four PNGs under `figures/`

## Important controls and limitations

- The three players share the same shaper, target, media ladder, duration, and
  congestion control within each capacity block.
- CUBIC and BBR are not simultaneous; they use the same nginx and Chrome stack.
- Five rounds are enough for the conference matrices; a journal rewrite would
  raise central cells to ten rounds.
- Paper-clock non-regression, 4 Mbit targets 3/4/5/6 s, and Starlink trace
  targets 3/4/5/6 s are complete (CUBIC and BBR). Trace tables use the final
  player with stall guard; see `results/trace-targets-summary.md`.
- The 8 Mbit setting is only 1.33 times the nominal 6000 kbps media rate. It is
  not equivalent to the earlier 100 Mbit normal-link matrix.
- Rebuffer is a sampled buffer-floor ratio, not wall-clock stall duration.
