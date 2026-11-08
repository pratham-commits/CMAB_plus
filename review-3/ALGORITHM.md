# CMAB+ algorithm

This is the player that produced the 4 Mbit result. Source:
`dash.js/src/streaming/rules/abr/cmab/cmabPlusPolicy.js` and
`CMABAbrController.js`. Flag: `cmabHardened=true` on `abrCMAB` only.
LinTS, the reward, the 15 s slot, and the catch-up controller are unchanged
from Zhao & Pan, MMSys '24.

## Notation

- Ladder \(A = \{0,\ldots,|A|-1\}\). Higher index is higher bitrate.
  The livesim ladder is about 300, 450, 900, 1200, 1500, 4900, 5100, 6000 kbps.
- \(r_i\): bitrate of arm \(i\), in kbps.
- \(\hat{T}\): dash.js `getSafeAverageThroughput`, already in kbps and already
  multiplied by the 0.9 safety factor. Do not scale it again.
- \(q\): quality already playing, an index in \(A\).
- \(r_q\): bitrate of that quality.
- \(n\): number of ABR decisions already taken in the current 15 s slot.
  Slots follow wall-clock seconds \(\{12, 27, 42, 57\}\), same as the paper.

## Old CMAB (paper)

After each slot starts, for the first \(|A|-1\) decisions, force the
**top rung** \(|A|-1\) and apply the switch at STRONG priority. After that
window, LinTS picks the arm. There is no throughput cap.

That is why a 4 Mbit link still requests 6000 kbps.

## CMAB+ (four rules)

**1. Feasible probe.** In the same first \(|A|-1\) decisions of a slot, request
the highest rung that still fits \(\hat{T}\), not the top of the ladder.

\[
i^\star = \max\{ i \in A : r_i \le \hat{T} \}
\]

If \(\hat{T}\) is missing or \(\le 0\), use arm 0. Skip LinTS during this
window so the bandit state stays aligned with the paper bootstrap.

**2. Throughput clamp.** After the window, LinTS still cannot exceed \(i^\star\).

**3. Step-down only when the current quality is above \(\hat{T}\).** If
\(r_q > \hat{T}\), the applied arm cannot rise on that decision, and it is at
most \(q-1\). If \(r_q \le \hat{T}\), keep the clamped suggestion, including a
jump up to \(i^\star\). Live latency by itself does **not** trigger this cut.

**4. Switch priority.** DEFAULT only for an upward switch that rule 2 reduced.
A downward switch stays STRONG.

**5. Stall guard.** This does not use live latency. It stays off while the
playback buffer is above 0.05 s, which is the paper-clock and flat 4 Mbit
case, so those sessions keep rules 1–3. Once a real quality is playing and
the buffer is at or below 0.05 s, the applied rung cannot rise, and it is
capped at the highest rung that fits the worst of the last 8 segment
throughputs. The guard turns off only after 12 decisions with the buffer at
or above 1 s. This is part of the final CMAB+ player. Clock and 4 Mbit
spots confirm the guard stays inactive there; the Starlink trace matrices
under `data/trace-targets-*` were run with this rule on.

## One decision

```
input: ladder A, throughput T_hat, current quality q, slot decision count n,
       LinTS, hardened flag

if T_hat is missing or T_hat <= 0:
    i_star = 0
else:
    i_star = highest i in A with r_i <= T_hat

# suggestion
if n < |A| - 1:
    if hardened:                 # CMAB+
        suggested = i_star
    else:                        # old CMAB
        suggested = |A| - 1
else:
    suggested = LinTS.select()

# CMAB+ only from here
arm = min(suggested, i_star)     # rule 2
clamped = (arm != suggested)

if r_q > T_hat and q is a real quality:
    arm = min(arm, max(0, q - 1))   # rule 3: no rise, one rung down
else:
    keep arm                        # including a climb to i_star

# rule 5: stall guard. Off when the buffer stays above 0.05 s.
if q is a real quality and buffer <= 0.05:
    stall = true
if stall:
    arm = min(arm, q, highest i with r_i <= worst of the last 8 throughputs)
    # stays on until 12 decisions with buffer >= 1 s

if clamped and arm > q:
    priority = DEFAULT              # rule 4
else:
    priority = STRONG

play arm, record reward, n = n + 1
```

At a slot boundary, reset \(n\) and the LinTS history for that slot, same as
the paper.

## What this is not

- It is not a new bandit. LinTS and the QoE reward are the paper's.
- It does not step down because live latency is 1 s over the target. That rule
  was tried (trials 3–7) and it cut bitrate on a link that could still carry
  the current quality.
- It does not keep a spare gap under \(\hat{T}\). A rung that is only just
  below the measurement is still allowed. That is why 1 Mbit CUBIC still
  chose about 888 kbps.

## Mapping to the 4 Mbit result

On a 4 Mbit link, \(i^\star\) is the 1500 kbps rung. Old CMAB still forces
6000 kbps in the post-handover window and rebuffers. CMAB+ probes 1500 kbps,
clamps later LinTS choices there, and lands at 3.54–3.62 s with 0% rebuffer.
