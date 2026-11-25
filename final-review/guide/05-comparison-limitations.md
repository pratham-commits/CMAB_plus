# Part 5. Comparison with L2A-LL, paper versus findings, limitations

[Back to the index](../GROUND_UP_GUIDE.md) · Previous: [Part 4](04-experiments.md) · Next: [Part 6, demo and artifact](06-demo-artifact.md)

---

## 5.1 CMAB+ against L2A-LL, cell by cell

The report's own summary (its "Comparison with L2A-LL" subsection) is narrow, and you should repeat it in the same words: when the forced window asks for a rung the link cannot carry, CMAB+ keeps playback going; at 4 Mbit/s it also brings latency to within 0.62 s of the target. On links that carry the top rung it behaves like old CMAB.

| Condition | Who is better | Evidence |
| --- | --- | --- |
| Paper clock (100 Mbit/s) | L2A-LL: lower latency and higher bitrate | L2A-LL 6000 kbps and 0.15–0.38 s closer to target; both near 0% rebuffer |
| 8 Mbit/s | L2A-LL: lower latency and rebuffering | CUBIC 5.15 s / 0.45% against 6.48 s / 2.85%; BBR 4.32 s / 0% against 6.63 s / 3.49% |
| 4 Mbit/s, all targets | Close. L2A-LL slightly ahead on latency | Same rung (about 1500 kbps), both 0% rebuffer, CMAB+ 0.18–0.23 s behind |
| 1 Mbit/s, BBR | Close | Both 450 kbps and 0%; 3.85 s against 3.69 s |
| 1 Mbit/s, CUBIC | L2A-LL | 3.47 s / 0% / 450 against 7.23 s / 16.54% / 888 |
| ISL trace | L2A-LL on rebuffering and latency; CMAB+ on bitrate | L2A-LL 0.49–1.43% at 301–482 kbps; CMAB+ 4.75–14.67% at 832–2917 kbps |

CMAB+ plays a higher bitrate than L2A-LL on the trace and at 8 and 1 Mbit/s under CUBIC, each time with more rebuffering.

So CMAB+ does not beat L2A-LL in general, and we never claim it does.

## 5.2 Then why does CMAB+ matter?

A faculty member may ask: "If L2A-LL is better or equal everywhere, why should anyone care about CMAB+?" Four answers, in order of strength:

1. It repairs a published system. The MMSys '24 artifact is the public implementation of a peer-reviewed algorithm. Anyone who deploys or builds on it inherits forced-rung collapse on any link slower than 6 Mbit/s. At 4 Mbit/s, CMAB+ turns 62–82% rebuffering into 0% at every target, and that is the concrete repair.
2. It keeps the learner. CMAB+ does not throw away the bandit. LinTS, the reward and the slot reset are unchanged, so any later research on the bandit (a better reward, a stall-aware P.1203 input, more context features) can start from a player that no longer collapses.
3. It does no harm on the healthy path. On the paper clock it is in the same operating range as old CMAB, so there is no reason not to apply the fix.
4. It gives a general lesson for learning-based ABRs: exploration in live streaming should be bounded by what the link has delivered. Our design ledger shows two specific ways to get this wrong (no probe at all, and a latency trigger).

The trade-off on the trace is a service choice. CMAB+ plays 2.5–7 times the bitrate of L2A-LL for 4–14 percentage points more rebuffering. A service that hates stalls should prefer L2A-LL there. The report says so in plain words.

## 5.3 The paper's claims against what we found

| Paper claim or suggestion | What we found | Status |
| --- | --- | --- |
| Starlink hands over every 15 s at seconds 12, 27, 42, 57 | We used this schedule in every shaper; we did not measure it ourselves (no dish) | Taken from the paper and Tanveer et al. |
| In emulation, all ABRs track the targets; CMAB a little above the others; L2A-LL at the top rung | Reproduced (D1) | Reproduced |
| In emulation at a 3 s target, every ABR misses by at least 1.5 s | Worst miss 0.19 s in our CUBIC run | Not reproduced; cause unknown |
| CMAB gives low latency, high bitrate and little rebuffering | True on the paper's 100 Mbit/s emulator. False for the shipped implementation on links slower than the top rung, where the forced window collapses it | Holds only where the top rung fits |
| BBR may help TCP over Starlink | Under the clock shaper, BBR moved CMAB latency by 0.1 s at a 3 s target. Under capacity and trace shapers BBR helped old CMAB (65.69% against 82.25% rebuffering at 4 Mbit/s) but did not remove the collapse | Transport effect small next to the ABR request policy |
| CMAB restarts exploration after every handover and struggles to converge | Confirmed in a sharper form: the restart is implemented as 7 forced top-rung decisions, which covers almost the whole slot | Confirmed, and explained in code |
| Real-dish results (CMAB below target for targets above 4 s; rebuffering close to L2A-LL) | Not tested | Out of scope (no dish) |
| Bitrate switches and bitrate standard deviation | Not measured in our final tables | Not tested |

Why the bug survived the paper's evaluation: the emulator runs at 100 Mbit/s with 50 Mbit/s during handovers, far above 6000 kbps. A forced top-rung window costs nothing there. The paper's dish runs used a terminal without ISLs, and we cannot say how often a real dish falls below 6 Mbit/s for a whole slot. Our capacity shaper forces that condition on purpose.

## 5.4 Limitations

State these plainly when asked. Each one is also in the report.

1. No live dish. Every result is emulation. We cannot claim anything about a real Starlink link.
2. One trace. The trace shaper replays one hour of RTT samples from one installation (Seychelles). Handover loss is modeled as 100% for the zero-RTT rows. Real handovers vary by place, time and load.
3. Five rounds per cell in Review III. The CMAB+ intervals are tight at 4 Mbit/s and wide for some trace and 1 Mbit/s cells. Ten rounds would narrow them.
4. The stall guard was not run on the full clock and 4 Mbit/s matrices. Those matrices used rules 1–4. Rule 5 was checked there only by spot runs, whose session trees are not archived.
5. Dynamic and LoL+ were not rerun in Review III. Only L2A-LL was kept as the reference.
6. Our rebuffer metric differs from the paper's. We count buffer samples at or below 0.05 s; the paper reports a rebuffering-time ratio. This limits direct comparison with the paper's Figure 8.
7. Testbed drift. The November CUBIC clock runs sit about 0.9 s above the September Review I runs for both old CMAB and L2A-LL. We did not isolate the cause, so we compare players only within a batch.
8. The 3 s-target gap to the paper (0.19 s against at least 1.5 s) is unexplained.
9. No spare margin. Rules 1 and 2 accept any rung at or below T̂. The 1 Mbit/s CUBIC cell (16.54% rebuffering at 888 kbps) shows this is too aggressive when the estimate is noisy. A margin or a variance-aware cap may help; we did not test one.
10. The reward still does not see stalls. The artifact passes P.1203 an empty stall list, so stalls reach the reward only through the bounded share-of-rebuffering term, and the bandit learns little from them. Changing that would change the learner, which we deliberately did not do.
11. One machine and one cloud zone. All runs used one GCP `e2-standard-4` VM.
12. QoE beyond three metrics was not measured: no P.1203 session score, no switch counts, no VMAF.

## 5.5 What we did not claim

- We do not claim CMAB+ beats L2A-LL in general.
- We do not claim BBR improves live streaming over Starlink.
- We do not claim contextual bandits are a bad idea for ABR, or that the paper's theory is wrong. The flaw is in one implementation detail (the forced window plus STRONG priority), not in LinTS.
- We do not claim CMAB+ is a new bandit algorithm. It is a systems repair around an unchanged learner.
- We do not claim any result on a real Starlink dish.
- We do not claim to have explained the 0.19 s versus 1.5 s gap, the 5 s outlier round, or the September-to-November drift.
- We do not report numbers for the stall-guard spot runs.

## 5.6 Open problems the report lists

- A spare margin or a variance-aware cap for rules 1 and 2.
- A stall signal the bandit can learn from (populate the P.1203 stall list, or add a stall term to the reward).
- A dish measurement.
- Ten-round matrices with the final player on every shaper.
- An explanation for the latency gap to the paper's 3 s result.

---

[Back to the index](../GROUND_UP_GUIDE.md) · Previous: [Part 4](04-experiments.md) · Next: [Part 6, demo and artifact](06-demo-artifact.md)
