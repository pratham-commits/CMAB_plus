# Paper framing

## Working title

**Preventing Forced-Rung Collapse in Contextual Bandit Live Streaming over
Capacity-Constrained LEO Links**

## Problem

The MMSys '24 CMAB implementation forces the absolute top video rung during
the first `|A|-1` decisions after every 15 s satellite slot boundary. That
bootstrap ignores whether recent safe throughput can carry the rung. When a
6000 kbps representation is forced onto a slower link, the controller can
rebuffer continuously while continuing to request the same representation.

## Proposed improvement

CMAB+ preserves the original LinTS controller but adds five safety rules:

1. Bootstrap to the highest rung at or below measured safe throughput, not the
   absolute top rung.
2. Clamp later LinTS selections to that feasible rung.
3. If the quality already playing is above measured safe throughput, step down
   one rung and do not rise on that decision.
4. DEFAULT switch priority only when an upward switch was reduced by the clamp.
5. Stall guard: after a real empty-buffer stall, hold quality down using the
   worst of the last 8 throughputs until the buffer recovers.

The final rule does not use live latency alone as a downswitch trigger. Earlier
trials showed that a latency threshold can cut bitrate even when the link can
still carry the current rung.

## Supported claim

**Capacity (4 Mbit, mild handovers).** Old CMAB stays at 6000 kbps and
rebuffers ~66–82%. CMAB+ selects ~1470 kbps with 0% rebuffer and ~3.5–3.6 s
latency, next to L2A (~1500 kbps). The same pattern holds at targets 3/4/5/6 s
under CUBIC and BBR.

**Non-regression (paper clock, 100 Mbit / 50 Mbit handover).** CMAB+ tracks
old CMAB (~5 Mbps, ~0% rebuffer) at targets 3/4/5/6 s under CUBIC and BBR.
Stall-guard spots confirm the guard does not fire on this healthy path.

**Starlink ISL trace (final player with stall guard).** CMAB+ cuts rebuffer
versus old CMAB at every target (CUBIC 3 s: ~81% → ~15%; BBR 3 s: ~29% →
~8%) and leaves the 6000 kbps lock. L2A still has lower rebuffer at a much
lower bitrate (~300–450 kbps).

Therefore CMAB+ prevents forced-rung collapse on constrained links, preserves
the paper-clock case, and improves the real-trace case relative to old CMAB
without claiming to beat L2A.

## Why this is an improvement over CMAB

The comparison is not “CMAB+ always has lower latency.” It is:

> When old CMAB's forced exploration is unsafe, CMAB+ preserves playback and
> brings latency back near the target instead of repeatedly forcing an
> infeasible representation.

At 4 Mbit, CMAB+ reduces mean latency by ~58% under both CUBIC and BBR and
removes observed rebuffer samples.

## What the evidence does not support

- CMAB+ does not generally beat L2A. It nearly matches L2A at 4 Mbit and at
  1 Mbit BBR; L2A is better at 8 Mbit, at 1 Mbit CUBIC, and on the Starlink
  trace for rebuffer.
- The 1 Mbit CUBIC capacity cell remains weak: ~7.2 s latency and ~16.5%
  rebuffer at about 888 kbps, while L2A selects 450 kbps with no rebuffer.
- Main conference matrices use five rounds per cell. That is enough for a
  conference claim; a journal rewrite would raise central cells to ten rounds.
- Clock and 4 Mbit multi-target matrices were measured under rules 1–3; the
  final player adds stall guard, which spots show stays off on those paths.
  Trace multi-target matrices use the final player (rules 1–5).

## Conference decision

Proceed. The three gates hold: no material clock regression, 4 Mbit win at
every target, and trace rebuffer below old CMAB without collapsing to the
bottom rung alone as the only operating point.
