# Part 1. The original paper and Review I

[Back to the index](../GROUND_UP_GUIDE.md) · Previous: [Part 0](00-foundations.md) · Next: [Part 2, Review II](02-review2.md)

---

## 1.1 The paper in one page

Jinwei Zhao and Jianping Pan, "Low-Latency Live Video Streaming over a Low-Earth-Orbit Satellite Network with DASH", ACM MMSys '24, DOI 10.1145/3625468.3647616.

What they did:

1. Measured Starlink. They ran latency and TCP throughput measurements from two installations: one in the Pacific Northwest (no ISLs, served through the Seattle point of presence) and one in the Seychelles (traffic crosses ISLs to Lagos). Median RTT to the gateway was 42.8 ms without ISLs and 109.0 ms with them. RTT spiked at seconds 12, 27, 42 and 57 of each minute, matching the 15-second schedule found by Tanveer et al. They also saw TCP fall back into slow start around handovers. The data is public as the LENS dataset.
2. Proposed CMAB, a contextual-bandit ABR for dash.js (Part 0.7). It picks a rung with LinTS, uses a P.1203-based reward, keeps history only for the current 15-second slot, and uses a catch-up policy that slows playback around handover seconds.
3. Evaluated CMAB against Dynamic, L2A-LL and LoL+ in three settings: a Docker emulator (handover modeled as 100 ms delay and 1% loss at the four seconds; 40 ms and 0.1% otherwise), a real Starlink dish (the installation without ISLs only), and a terrestrial network as a control group. Targets were 3, 4, 5 and 6 s.

What they claimed (from the paper text):

- The proposed algorithm gives low live latency, high average bitrate, little rebuffering and fewer visible quality swings.
- In emulation at a 3 s target, every ABR missed the target by at least 1.5 s.
- On the real dish, only CMAB reached a live latency below the target when the target was above 4 s, and its rebuffering was close to L2A-LL's for targets above 4 s.
- CMAB made more bitrate switches than the others but had a lower bitrate standard deviation.
- The paper itself notes a weakness: because history restarts at every handover, "it has to restart the exploration phase from scratch after every handover event", which makes it hard for the learner to converge in a short slot with 2-second segments.
- In its discussion, it suggests that BBR, HyStart++ or satellite-aware congestion control such as SaTCP may do better than CUBIC over Starlink.

Implementation details from the paper: dash.js v4.7.1; MABWiser LinTS run in the browser through Pyodide, costing under 100 ms per decision; exploration rate 1.0; maximum catch-up playback-rate change 0.17; maximum drift 5 s; FastSwitching disabled.

## 1.2 What Track A7 asked of us

Track A is "reproduction, validation and systems extension". For menu item A7 the plan had three phases, one per review:

| Review | Goal | Outcome in one line |
| --- | --- | --- |
| Review I | Reproduce the paper's emulation results | Done: 160 sessions under CUBIC; qualitative match, one claim not reproduced |
| Review II | Extend: does the transport (BBR instead of CUBIC) matter? | Under a fair shaper, BBR changes little; the scary first result came from the wrong shaper |
| Review III | Fix what Review II exposed | CMAB+: five rules that stop forced-rung collapse |

## 1.3 Review I: the reproduction

### Setup

- Machine: one Google Cloud `e2-standard-4` virtual machine (4 vCPU, 16 GB RAM) in zone `asia-south1-c` (Mumbai).
- Code: the authors' artifact at commit `dc120de` (full hash `dc120dec12e89e884268eccca43c53b0e2192e20`).
- Containers (Docker Compose): livesim2 (a live DASH source that loops a video and stamps it with wall-clock time), an nginx front end that also hosts the traffic shaper, a stats server with MongoDB that collects player logs, and a Chromium browser driven by Selenium that runs the modified dash.js.
- Network: the clock shaper. 100 Mbit/s, 40 ms, 0.1% loss normally; 50 Mbit/s, 100 ms, 1% loss in each handover second.
- Transport: CUBIC, the Linux default.
- Matrix: 4 ABRs × 4 targets (3, 4, 5, 6 s) × 10 rounds × 300 s = 160 sessions, 48,000 seconds or 13.33 hours of video.

A simple picture of the testbed:

```
 livesim2  --->  nginx (+ tc shaper on its outgoing traffic)  --->  Chromium + dash.js
 (live source)       sender; TCP CUBIC or BBR set here              (ABR runs here)
                                                                          |
                                                                          v
                                                         stats server + MongoDB (logs)
```

### Results at the 3 s target (dataset D1)

From the final report, Table 1 (mean of 10 sessions):

| ABR | Live latency (s) | Bitrate (kbps) | Rebuffer ratio |
| --- | ---: | ---: | ---: |
| Dynamic | 3.00 | 5909 | 0.00% |
| L2A-LL | 3.00 | 6000 | 0.00% |
| LoL+ | 3.08 | 4938 | 0.00% |
| CMAB | 3.19 | 4955 | 0.00% |

All targets (report Appendix B, latency s / bitrate kbps):

| ABR | 3 s | 4 s | 5 s | 6 s |
| --- | --- | --- | --- | --- |
| Dynamic | 3.00 / 5909 | 4.00 / 5910 | 5.00 / 5640 | 6.01 / 5600 |
| L2A-LL | 3.00 / 6000 | 4.02 / 6000 | 5.00 / 6000 | 6.02 / 6000 |
| LoL+ | 3.08 / 4938 | 4.07 / 4902 | 5.08 / 4900 | 6.11 / 4900 |
| CMAB | 3.19 / 4955 | 4.20 / 4989 | 6.05 / 4951 | 6.24 / 5021 |

What matched the paper: all four ABRs track the target, CMAB sits a little above the others, and L2A-LL plays the top rung all the time.

What did not match: the paper says that at a 3 s target every algorithm misses by at least 1.5 s. Our worst miss at 3 s was 0.19 s (CMAB, 3.19 s). We do not know why. Two possible contributors: our metric drops the first 20% of each session, which removes start-up; and the paper's own metric pipeline may differ. The report states this as an open question and does not claim a cause.

### The 5 s outlier

Under our metric, every D1 cell has a 0.00% mean rebuffer ratio except one: CMAB at the 5 s target, 2.52%. The per-session file `report/results/d1-cmab-5s-sessions.csv` shows why. Nine sessions sat at 5.21–5.38 s with no rebuffering. One session (round index 2) had 13.38 s mean latency and 25.24% rebuffering. That one session lifts the cell mean to 6.05 s and 2.52%. We kept it in every aggregate and reported it instead of dropping it.

Why keep it? Dropping data you dislike is a form of cherry-picking. Reporting it, with the per-session breakdown, lets a reader judge for themselves.

## 1.4 Where the earlier Review I guide differs from the final report

The Review I guide (`~/BITS/ACN/Project/review 1/details.md`) was written before the final metric pipeline was fixed and before the code was read closely. Some of its statements differ from the final report. If a faculty member quotes the old slides, these are the corrections. The final report and its result files win in every case.

| Topic | Review I guide said | Final report and data say |
| --- | --- | --- |
| The 5 s outlier session | 20.74% rebuffering, 62.71 s latency, caused by a headless Chromium desynchronization | 25.24% rebuffering, 13.38 s latency (round index 2). The report gives no proven cause. |
| Rebuffering in D1 | CMAB 0.50–0.69%, others 0.11–0.17% | 0.00% in every cell except CMAB at 5 s (2.52%), under the fixed sampled metric |
| CMAB bitrate in D1 | About 4810–4855 kbps | 4951–5021 kbps |
| Shaper capacity | A 10 Mbit/s ceiling | 100 Mbit/s normally, 50 Mbit/s in handover seconds |
| Ladder | "500 to 6000 kbps" | 300, 450, 900, 1200, 1500, 4900, 5100, 6000 kbps |
| dash.js version | 4.7.4 | 4.7.1 (paper and report) |
| L2A-LL method | A PID controller | Online convex optimization |
| CMAB context | Includes buffer level and time since the last handover | Network latency, playback speed and throughput only. Handover awareness comes from the slot reset and the catch-up policy. |
| CMAB behaviour near handovers | "Lowers bitrate before a handover" | The code does the opposite: it requests the top rung for the first 7 decisions after each slot boundary (Part 3) |
| CUBIC vs BBR recovery times | CUBIC about 7.2 s, BBR about 1.8 s | No such measurement exists in the final results; these were illustrative numbers in a planning slide |

Being able to state these corrections calmly is useful in a viva. It shows that the team checked its own earlier work.

## 1.5 What Review I left open

At the end of Review I we had a working testbed, a reproduced baseline, and two open questions:

1. The paper's discussion suggests BBR might help on Starlink. Does it?
2. Is the handover problem mainly an ABR problem (the player picks the wrong rung) or a transport problem (TCP slows down after loss)?

Review II was planned to answer both by changing one thing, the congestion control, and rerunning the same matrix.

---

[Back to the index](../GROUND_UP_GUIDE.md) · Previous: [Part 0](00-foundations.md) · Next: [Part 2, Review II](02-review2.md)
