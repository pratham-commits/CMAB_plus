# Part 8. Glossary and cheat sheet

[Back to the index](../GROUND_UP_GUIDE.md) · Previous: [Part 7](07-qa-bank.md)

## 8.1 Glossary

Terms are in alphabetical order. "See" points to the part of the guide that explains each one in full.

| Term | Meaning |
|---|---|
| ABR (adaptive bitrate) | The player logic that picks the bitrate rung for each next segment. See Part 0. |
| Arm | One option a bandit can choose. In CMAB, each of the 8 ladder rungs is an arm. |
| Artifact | The code and scripts the paper's authors released (`clarkzjw/mmsys24-starlink-livestreaming`, commit `dc120de`). |
| BBR | Bottleneck Bandwidth and Round-trip propagation time. A model-based TCP congestion control that paces at its bandwidth estimate and does not cut its rate on every loss. |
| BOLA | A buffer-based ABR rule inside dash.js that the Dynamic player uses when the buffer is healthy. |
| Bitrate | Bits of video per second of playback, in kbps. Higher means a sharper picture and a bigger download. |
| Bitrate ladder | The list of bitrates the server offers: 300, 450, 900, 1200, 1500, 4900, 5100, 6000 kbps. |
| Buffer | Downloaded video not yet played, measured in seconds. |
| Capacity shaper | Our flat-rate shaper (`tc-capacity.sh`) that fixes the link at 8, 4 or 1 Mbit/s. |
| Catch-up | Speeding playback up or slowing it down (by up to 0.17, so 0.83x to 1.17x) to stay near the latency target. |
| Clock shaper | The artifact's `tc.py`, which changes delay, loss and, on the paper clock, rate for one second at 12, 27, 42 and 57 s of every minute. |
| CMAB | The paper's contextual multi-armed bandit ABR, using LinTS. In our tables, "old CMAB" means the paper's code unchanged. |
| CMAB+ | Our version: the same LinTS learner with five safety rules around its choice. Enabled with `cmabHardened=true`. |
| `cmabHardened` | The player setting that turns on CMAB+ for `abrCMAB`. |
| Confidence interval (95%) | A range around a mean that shows its uncertainty. We use t × sd / √n over session means. |
| Congestion control | The TCP logic that decides how fast a sender transmits. Examples: CUBIC, BBR. |
| Context | The measured numbers a contextual bandit sees before choosing. CMAB uses throughput, playback rate and network latency. |
| CUBIC | The default Linux TCP congestion control. Loss-based: it grows its window until a loss, then cuts. |
| D1, D2, D3 | Review I and II datasets. D1 is CUBIC on the clock shaper, D2 is BBR on the trace shaper (superseded), D3 is BBR on the clock shaper. |
| DASH | Dynamic Adaptive Streaming over HTTP. Video is cut into short segments, each offered at several bitrates. |
| dash.js | The reference DASH player in JavaScript. The artifact uses a modified 4.7.1. |
| DEFAULT / STRONG / WEAK priority | dash.js rule priorities. The player takes the highest priority present and, within it, the lowest proposed rung. |
| Docker Compose | A tool that starts several containers together from one file. Our testbed is one Compose stack. |
| Dynamic | The dash.js default ABR, switching between a throughput rule and BOLA. |
| Emulation | Running real software over imposed network conditions. Different from simulation, which models the software too. |
| EWMA | Exponentially weighted moving average. Recent samples count more than old ones. dash.js uses two (fast and slow) for throughput. |
| Exploration / exploitation | Trying uncertain options to learn versus using the best-known one. |
| Feasible probe | CMAB+ rule 1: in the forced window, request the highest rung at or below the safe throughput estimate. |
| Forced window | In old CMAB, the first 7 decisions of each slot (the number of arms minus one), which skip LinTS and request the top rung at STRONG priority. |
| Forced-rung collapse | Our name for the failure in which the forced window drains the buffer on a slow link and the player never recovers before the next reset. |
| GCP | Google Cloud Platform. Our VM is an `e2-standard-4` in `asia-south1-c`. |
| Handover | Starlink reassigning a terminal to a different satellite, every 15 s at seconds 12, 27, 42 and 57. |
| HTB | Hierarchical Token Bucket, a Linux `tc` queueing discipline used to cap rate in the trace shaper. |
| i* | The highest rung whose bitrate is at or below the safe throughput estimate. Rules 1 and 2 use it. |
| ISL | Inter-satellite link. A laser link between satellites. |
| L2A-LL | Learn2Adapt-LowLatency, an ABR based on online convex optimization. Our strongest baseline. |
| Latency target | The live latency the player aims for: 3, 4, 5 or 6 s in our runs. |
| LEO | Low Earth orbit. Starlink satellites orbit at about 550 km. |
| LinTS | Linear Thompson Sampling. A bandit method that samples reward weights from a distribution and picks the arm with the highest sampled reward. |
| Live latency | How far behind the real-time edge the viewer is, in seconds. |
| livesim2 | The live DASH source in the testbed. It produces a live stream from stored content. |
| LoL+ | A low-latency ABR in dash.js based on a self-organizing map. |
| MABWiser | The Python bandit library that CMAB uses, run in the browser through Pyodide. |
| netem | A Linux tool that adds delay and loss to a network interface. |
| nginx | The web server that delivers segments to the player. The shaper and the congestion control both sit on nginx. |
| Non-regression | A check that a change does not make things worse where the old version already worked. Our gate is the paper's 100 Mbit/s clock. |
| P.1203 | An ITU-T model that estimates viewer quality. CMAB uses its O.46 score in the reward. |
| Paper clock | The clock shaper with the paper's rate schedule: 100 Mbit/s, dropping to 50 Mbit/s for one second at each handover. |
| Playback rate | Playback speed. 1.0 is normal; catch-up moves it between 0.83 and 1.17. |
| Pyodide | Python compiled to run inside a web browser. |
| Qdisc | Queueing discipline: Linux's per-interface packet scheduler. Shapers install qdiscs. |
| Rebuffer ratio | Our metric: share of buffer samples at or below 0.05 s, after the 20% trim. |
| Reward | The number a bandit gets back after a choice. CMAB's combines P.1203 quality, latency ratio, bitrate ratio and a rebuffer penalty. |
| RTT | Round-trip time, how long a packet takes to go and an answer to come back. |
| Rung | One entry in the bitrate ladder. |
| Safe throughput estimate (T̂) | dash.js's `getSafeAverageThroughput`: the smoothed throughput times 0.9. |
| Segment | A short piece of video, 2 s in our stream. |
| Selenium | A tool that drives a browser automatically. Each session is one Selenium-controlled Chromium. |
| Session | One automated playback run of one ABR at one target. |
| Slot | The 15 s between two handovers. CMAB resets its history at the start of each slot. |
| Stall | Playback stops because the buffer is empty. |
| Stall guard | CMAB+ rule 5: after the buffer hits 0.05 s, cap at 0.9 times the worst of the last 8 throughputs and do not rise until 12 consecutive decisions have at least 1 s of buffer. |
| Step-down | CMAB+ rule 3: if the rung now playing exceeds T̂, go at most one rung down and do not rise. |
| `sysctl` | A Linux command to read or set kernel settings, such as the TCP congestion control. |
| `tc` | Linux traffic control, the command used to install shapers. |
| Throughput | Data delivered per second, as measured by the player. |
| Throughput clamp | CMAB+ rule 2: after the forced window, cap LinTS's choice at i*. |
| Trace shaper | The artifact's `tc-trace.py`, which replays a measured ISL RTT trace; handover rows become 100% loss under a 20 Mbit/s ceiling. |
| Trim (20%) | Dropping the first 20% of each session's samples before computing metrics. |
| Trial | One of our eight design iterations before the final CMAB+ rules. |

## 8.2 One-page cheat sheet

### The setup

```
Video ladder      300 450 900 1200 1500 | 4900 5100 6000 kbps, 2 s segments
Handovers         every 15 s at :12 :27 :42 :57
Paper clock       100 Mbit/s, 40 ms, 0.1% loss; 50 Mbit/s, 100 ms, 1% at handovers
Capacity shaper   8 / 4 / 1 Mbit/s flat
Trace shaper      ISL RTT trace, median about 130 ms; handover rows 100% loss, 20 Mbit/s cap
Machine           GCP e2-standard-4, asia-south1-c; dash.js 4.7.1; artifact dc120de
Metrics           20% trim; rebuffer = buffer <= 0.05 s; 95% t interval (t = 2.776 n=5, 2.262 n=10)
Sessions          Review I: 160 (D1).  Review III: 450 (90 + 120 + 120 + 120)
```

### Review I (D1, CUBIC, clock, 10 rounds)

```
Target  CMAB          L2A-LL
3 s     3.19 s, 0%    3.00 s, 0%, 6000 kbps
5 s     6.05 s, 2.52% (one round 13.38 s / 25.24%; other nine 5.21-5.38 s)
Paper claim "every ABR misses 3 s by >= 1.5 s": not reproduced (worst miss 0.19 s)
```

### Review II

```
D2 (BBR, trace, first run)  CMAB 3 s: 7.19 s, 28.32%, about 5800 kbps;  Dynamic 619 kbps, 4.13 s
Faults                      wrong shaper (trace, not clock); trace shaper broke on nginx restart
D3 (BBR, clock, fair rerun) CMAB 3 s: 3.29 s, 0%  (CUBIC was 3.19 s)
Corrected trace, old CMAB BBR 3 s: 7.16 s, 28.98%  (matches D2, so the shaper explains D2)
```

### Root cause

```
Old CMAB: first |A|-1 = 7 decisions per slot -> 6000 kbps at STRONG priority, no throughput check
One 6000 kbps segment = 12 Mbit = at least 3 s on a 4 Mbit/s link (plays 2 s)
About 7-8 decisions per slot, so the forced window covers almost all of them
```

### CMAB+ (five rules)

```
1 Feasible probe    forced window asks for i* (highest rung <= T-hat) instead of the top rung
2 Clamp             later LinTS choices capped at i*
3 Step-down         playing rung > T-hat -> one rung down, no rise
4 Priority          clamped upward switch -> DEFAULT; others STRONG
5 Stall guard       on at buffer <= 0.05 s; cap 0.9 x worst of last 8; off after 12 decisions >= 1 s buffer
T-hat = dash.js safe average throughput (smoothed x 0.9)
```

### Final results (5 rounds per cell, Review III)

```
Paper clock    CMAB+ tracks old CMAB: at most 0.15 s slower, +3 to +141 kbps in 7 of 8 cells
4 Mbit/s       old CMAB 62.05-80.59% rebuffer at 6000 kbps -> CMAB+ 0% in all 40 sessions,
               1457-1477 kbps, latency 46.5-58.7% lower, 0.18-0.23 s behind L2A-LL
8 Mbit/s       no improvement; both CMAB versions 6.2-6.7 s, 1.8-3.5% rebuffer
1 Mbit/s       BBR: CMAB+ = L2A-LL (450 kbps, 0%).  CUBIC: CMAB+ 888 kbps, 16.54% rebuffer
ISL trace      rebuffer cut 71.4-86.0%; CMAB+ CUBIC 11.52-14.67%, BBR 4.75-8.29%;
               L2A-LL 0.49-1.43% at 301-482 kbps; CMAB+ plays 2.5-7x L2A-LL's bitrate
Before guard   trace CUBIC 30.84-35.22% at 1578-1776 kbps; BBR 8.92-11.71%
```

### What we claim, and what we do not

```
Claimed      When the forced window asks for a rung the link cannot carry, CMAB+ keeps
             playback going; on links that carry the top rung it behaves like old CMAB.
Not claimed  CMAB+ beats L2A-LL; results on a real dish; BBR fixes Starlink streaming;
             a cause for the Review I outlier or for the Sept-to-Nov latency drift.
```

### Artifact

```
github.com/pratham-commits/CMAB_plus   commit d60f163   enable with cmabHardened=true
Rules in cmabPlusPolicy.js; tests in experiments/test_cmab_plus_policy.mjs
```

---

[Back to the index](../GROUND_UP_GUIDE.md) · Previous: [Part 7](07-qa-bank.md)
