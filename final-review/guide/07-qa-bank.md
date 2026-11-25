# Part 7. Question and answer bank

[Back to the index](../GROUND_UP_GUIDE.md) · Previous: [Part 6](06-demo-artifact.md) · Next: [Part 8, glossary and cheat sheet](08-glossary-cheatsheet.md)

Answers are short enough to say aloud. Numbers match the report. Where a number exists only in our notes, the answer says so.

---

## A. Basics

#### Q1. What is your project in one sentence?
We reproduced the MMSys '24 Starlink live-streaming emulation, tested it under BBR, found that a testbed mistake caused the first BBR failure, traced the remaining failure to a forced top-rung window in the paper's CMAB code, and fixed it with five rules (CMAB+) that cut rebuffering at 4 Mbit/s from 62–82% to 0% at every target.

#### Q2. What problem does the original paper address?
Low-latency live video over Starlink. Starlink reassigns satellites every 15 s, at seconds 12, 27, 42 and 57, and each reassignment raises latency and loss. A live player keeps only one or two 2-second segments in its buffer, so it has little room to absorb those disturbances.

#### Q3. Why is live video harder than Netflix-style video?
A VoD player can buffer tens of seconds because the whole video exists. A live player cannot download what has not been recorded yet, so with a 3 s target it holds only a couple of seconds. A short slowdown empties that buffer.

#### Q4. What is an ABR algorithm?
The logic in the player that picks the bitrate (the rung) for each next segment, trading picture quality against the risk of a stall and against staying near the latency target.

#### Q5. What are the three metrics you report?
Mean live latency (seconds behind the live edge), rebuffer ratio (share of buffer samples at or below 0.05 s), and mean bitrate (kbps). All are computed after dropping the first 20% of each session.

#### Q6. What are the bitrate ladder rungs?
300, 450, 900, 1200, 1500, 4900, 5100 and 6000 kbps, with 2-second segments. The gap between 1500 and 4900 kbps is why we chose a 4 Mbit/s test link.

## B. Starlink and the network

#### Q7. Why do handovers happen every 15 seconds?
Measurements by Tanveer et al. (CoNEXT '23) and by the paper's authors show that a global Starlink controller reassigns satellites to terminals on a 15-second schedule. Starlink has not published the reason, and we did not study it; we use the measured schedule.

#### Q8. What is an ISL, and why does it matter here?
An inter-satellite link is a laser link between satellites. Where no ground station is nearby, traffic hops between satellites before landing. The paper's Seychelles terminal used ISLs and had a median gateway RTT of 109.0 ms against 42.8 ms without ISLs. Our trace shaper replays an ISL RTT trace from that terminal.

#### Q9. How does your emulator model a handover?
Clock shaper: for one second at 12, 27, 42 and 57, delay goes from 40 ms to 100 ms, loss from 0.1% to 1%, and on the paper clock the rate drops from 100 to 50 Mbit/s. Trace shaper: trace rows with RTT 0 or −1 become 100 ms delay, 100% loss and a 20 Mbit/s ceiling.

#### Q10. What is the difference between bandwidth, throughput and latency?
Bandwidth is the most the path can carry; throughput is what you get; latency is the delay. A pipe's width versus how much water flows versus its length.

#### Q11. Why emulation and not simulation?
Emulation runs the real browser, the real dash.js code and the real Linux TCP stack; only the network conditions are imposed with `tc` and netem. A simulation would model all of that with equations and could miss behaviour like TCP loss recovery or browser timing.

#### Q12. Why not test on a real dish?
We had no Starlink dish. That is the first limitation in our report; we make no claims about real Starlink links.

## C. TCP: CUBIC and BBR

#### Q13. What is the difference between CUBIC and BBR?
CUBIC is loss-based: it grows its window until a loss and then cuts it. BBR is model-based: it estimates bottleneck bandwidth and minimum RTT, paces at that rate and probes periodically, and does not cut on every loss.

#### Q14. Why did you expect BBR to help?
Handovers bring loss, and CUBIC treats loss as congestion. The paper also notes slow-start behaviour after handovers and suggests BBR as future work.

#### Q15. So did BBR help?
On the fair clock shaper, very little: CMAB at a 3 s target went from 3.19 s (CUBIC) to 3.29 s (BBR), both with no rebuffering. On constrained links BBR reduced old CMAB's rebuffering (65.69% against 82.25% at 4 Mbit/s) but did not stop the collapse. The ABR's request policy mattered more.

#### Q16. How did you switch to BBR?
With `sysctl net.ipv4.tcp_congestion_control=bbr` inside the nginx container, which is the video sender. We recorded the value from inside the running container.

#### Q17. Why set BBR on the server and not on the client?
Congestion control governs the sender. Video flows from nginx to the player, so the nginx side decides the sending rate.

## D. Bandits and CMAB

#### Q18. What is a multi-armed bandit?
A repeated choice among options (arms) with unknown payoffs, where each try reveals the payoff of the chosen arm only. The challenge is balancing exploration (trying uncertain arms) and exploitation (using the best-known arm).

#### Q19. What makes it contextual?
Before each choice the learner sees some measured numbers, the context, and the best arm may depend on them.

#### Q20. How does Linear Thompson Sampling choose?
It keeps a probability distribution over each arm's reward weights, draws one sample per arm, and plays the arm with the highest sampled reward for the current context. Uncertain arms sometimes draw high, which gives exploration.

#### Q21. In CMAB, what are the arms, context and reward?
Arms: the 8 rungs. Context: network latency to the stats server, playback speed and estimated throughput. Reward: the P.1203 O.46 score times target/current latency times chosen/top bitrate, minus the share of rebuffering time spent at the chosen bitrate.

#### Q22. Why does CMAB reset its history every 15 s?
The paper argues that each satellite slot has its own latency pattern, so data from an old slot may mislead. It keeps only the current slot's history.

#### Q23. What is the forced exploration after each handover?
In the code, during the first |A| − 1 = 7 decisions of each slot, CMAB skips LinTS and requests the top rung (6000 kbps), and sends it at STRONG priority. This is not in the paper's equations.

#### Q24. Does CMAB's context include the buffer level or the time since handover?
No. The LinTS features are throughput, playback rate and network latency. The handover awareness comes from the slot reset and the catch-up policy. Some early slides said otherwise; the code is clear.

## E. Testbed and method

#### Q25. Describe the testbed.
One GCP `e2-standard-4` VM (4 vCPU, 16 GB) in `asia-south1-c`. Docker Compose runs livesim2 (live DASH source), nginx with the traffic shaper on its egress, a stats server with MongoDB, and Selenium-driven Chromium running the authors' modified dash.js 4.7.1. Artifact commit `dc120de`.

#### Q26. Why drop the first 20% of each session?
Start-up is always unusual: the buffer is empty and the player is choosing its first rungs. Trimming keeps start-up effects out of the steady-state numbers. The same trim is applied everywhere.

#### Q27. Why 0.05 s as the stall threshold?
A buffer that low means the player has nothing left to play. We use the same threshold for the metric and for turning on the stall guard, so the two agree. The demo uses it too.

#### Q28. Is your rebuffer ratio the same as the paper's?
No. Ours is a sampled buffer-floor ratio; the paper reports a rebuffering-time ratio. They are related but not equal, so direct comparison with the paper's Figure 8 is limited.

#### Q29. What is a 95% confidence interval and how did you compute it?
A range around the mean that shows how uncertain it is. We use a two-sided Student-t interval over session means: t × standard deviation / √n, with t = 2.776 for 5 sessions and 2.262 for 10.

#### Q30. Why only five rounds in Review III when Review I had ten?
Time and machine budget: Review III ran 450 sessions plus the trial matrices. Five rounds give tight intervals where the effect is large (CMAB+ latency at 4 Mbit/s is within ± 0.05 s), but wide ones on some trace and 1 Mbit/s cells. We list ten rounds as future work.

#### Q31. What is "one variable at a time", and where did you violate it?
Change one setting per comparison so you know what caused the difference. The first BBR run changed both the congestion control and the shaper. That is why we discarded it as a transport result.

## F. Review I

#### Q32. Did you reproduce the paper?
Qualitatively yes: all four ABRs tracked the targets, CMAB sat a little above the others (3.19 s against 3.00–3.08 s at 3 s) and L2A-LL played 6000 kbps throughout. One claim did not reproduce: the paper says every ABR missed a 3 s target by at least 1.5 s; our worst miss was 0.19 s.

#### Q33. Why didn't that claim reproduce?
We do not know. Our 20% trim removes start-up, and the paper's metric pipeline may differ. We report it as unexplained.

#### Q34. What about the 5 s outlier?
One CMAB session at the 5 s target had 13.38 s latency and 25.24% rebuffering; the other nine were 5.21–5.38 s with none. It lifts the cell to 6.05 s and 2.52%. We kept it in every aggregate. We have no proven cause for it.

#### Q35. Your Review I slides gave 20.74% for that round and blamed a Chromium desync. Which is right?
The final report: 25.24% and 13.38 s, recomputed from the session files with the fixed metric. The desync explanation was a hypothesis in our Review I notes; the report does not claim a cause.

## G. Review II

#### Q36. What was the scary first result?
In the first BBR matrix, CMAB at a 3 s target had 7.19 s latency and 28.32% rebuffering, while Dynamic dropped to 619 kbps and stayed near 4.13 s.

#### Q37. How did you find out it was not BBR's fault?
We ran a small validation under CUBIC on the same stack and CMAB failed there too (notes record about 16.6 s, about 86% rebuffering, all 28 logged decisions on the top arm). A BBR effect cannot explain a CUBIC failure, so we audited the testbed.

#### Q38. What were the two faults?
First, the run used the trace shaper instead of the clock shaper used in Review I. Second, the trace shaper crashed when nginx was restarted between sessions, because its start-up only added `tc` classes and the old qdiscs survived the restart; this could leave the link stuck at 100% loss.

#### Q39. Which fault explains the 7.19 s number?
The shaper choice. On the corrected trace shaper in Review III, old CMAB under BBR gave 7.16 s and 28.98% at 3 s, almost the same as D2. The restart bug was a reliability problem that we fixed anyway.

#### Q40. What are D1, D2 and D3?
D1: CUBIC, clock (Review I). D2: BBR, trace (first BBR run, superseded). D3: BBR, clock (the fair rerun, prefix `1017-0606`).

#### Q41. What did D2 still teach you?
On the same trace, Dynamic adapted to 619 kbps and survived while CMAB kept requesting about 5800 kbps. Same network, same transport, different controller, which pointed at CMAB's code.

#### Q42. How do we know the BBR rerun used BBR and the clock shaper?
We read both settings from inside the running nginx container before the batch and saved them (`review-2/meta/nginx-tcp_cc.txt` and `nginx-SHAPER.txt`). The runners for Review III check these automatically.

## H. Review III and CMAB+ design

#### Q43. What is forced-rung collapse?
On a link slower than 6000 kbps, the 7 forced top-rung decisions after each handover each download slower than they play, so the buffer drains. A stalled player makes fewer decisions per slot, may never reach decision 8 where LinTS takes over, and the next handover restarts the forced window.

#### Q44. Why didn't the paper see it?
Its emulator runs at 100 Mbit/s (50 Mbit/s during handovers), far above 6000 kbps, so forcing the top rung costs nothing. Its dish runs used a terminal without ISLs; we cannot say how often a real dish stays below 6 Mbit/s for a slot.

#### Q45. Why not just delete the forced window?
We tried (trial 1). CMAB then stayed at 900 kbps at every target, because after each reset the learner never tried the high rungs. The bandit needs a probe; it needs a safe one.

#### Q46. Why not step down when latency is too high?
We tried that in trials 3 to 7. With no margin, the ladder walked to 300 kbps because a healthy player always runs slightly above target. With a 1 s margin, the CUBIC run sat on the line (4.02 s at a 3 s target) and cut bitrate to 3009 kbps on a link that carried 4955 kbps for old CMAB. Latency is the wrong trigger.

#### Q47. State the five rules.
1. Feasible probe: in the 7-decision window, request the highest rung at or below the safe throughput estimate. 2. Throughput clamp: cap later LinTS choices at that rung. 3. Step-down: if the rung now playing exceeds the estimate, go at most one rung down and do not rise. 4. Priority: an upward switch that the clamp reduced uses DEFAULT priority; others stay STRONG. 5. Stall guard: after the buffer hits 0.05 s, cap at the worst of the last 8 throughputs × 0.9 and do not rise until 12 consecutive decisions with at least 1 s of buffer.

#### Q48. What is the "safe throughput estimate"?
dash.js's `getSafeAverageThroughput`: a smoothed throughput (the lower of a fast and a slow moving average) multiplied by a 0.9 safety factor. CMAB+ uses it as is and does not scale it again.

#### Q49. Why rule 4? What does priority have to do with it?
dash.js picks the lowest rung among proposals at the highest priority present. STRONG wins over the throughput rule. For an upward switch that our clamp already had to trim, we drop to DEFAULT so other rules may still veto it. Downward switches stay STRONG so a player in trouble leaves a high rung fast.

#### Q50. Why was the stall guard needed?
On the trace, rules 1–4 still left CMAB+ at 30.84–35.22% rebuffering under CUBIC. The smoothed estimate recovered between loss spikes and let the player climb right before the next spike. Using the worst recent sample and a long healthy run holds it down through the bad stretch.

#### Q51. Does the stall guard hurt healthy links?
It should never turn on there, since CMAB+ with rules 1–4 does not empty its buffer on the paper clock or at a flat 4 Mbit/s. Spot runs were recorded as unchanged in our ledger, but those session trees are not archived, so we do not report numbers.

#### Q52. Is CMAB+ a new algorithm?
No. LinTS, the context, the reward, the slot reset and the catch-up policy are unchanged. CMAB+ is a safety layer around the learner's choice.

#### Q53. Which rule matters most?
Rules 1 and 2 together. They replace "ask for 6000 kbps" with "ask for the best rung the link has shown it can carry". At 4 Mbit/s that alone turns 6000 kbps requests into 1500 kbps requests. Rule 3 adds recovery when the estimate falls; rule 5 matters on the trace.

## I. Results

#### Q54. Give the headline result.
At 4 Mbit/s, old CMAB rebuffers 62.05–80.59% across targets at 6000 kbps; CMAB+ has 0% in all 40 sessions at 1457–1477 kbps, with latency 46.5–58.7% lower. On the paper clock, CMAB+ matches old CMAB. On the ISL trace, CMAB+ cuts rebuffering by 71.4–86.0%, but L2A-LL still rebuffers less.

#### Q55. Does CMAB+ beat L2A-LL?
No. It is close at 4 Mbit/s (0.18–0.23 s behind, same rung, no rebuffering) and at 1 Mbit/s under BBR. L2A-LL is better at 8 Mbit/s, at 1 Mbit/s under CUBIC, and on the trace; on the paper clock it has lower latency and higher bitrate.

#### Q56. What happens at 1 Mbit/s under CUBIC?
CMAB+ plays mostly the 900 kbps rung (mean 888 kbps), which fits the estimate but not the sustained rate, and rebuffers 16.54%. L2A-LL stays at 450 kbps with none. Rules 1 and 2 have no spare margin below the estimate; this is a known weakness.

#### Q57. Why is old CMAB's BBR latency at 1 Mbit/s 47 s?
One session reached 131.26 s. The other four were 25.61–26.37 s, and all five rebuffered 98.7–100%. The conclusion does not depend on that session, but the interval is very wide.

#### Q58. Why is 8 Mbit/s not improved?
8 Mbit/s is only 1.33 times the top rung, so the top rung fits on paper and CMAB+'s clamp rarely binds. Both CMAB versions run at 6.2–6.7 s with 1.8–3.5% rebuffering, and L2A-LL is better.

#### Q59. Why are the non-regression CUBIC latencies higher than in Review I?
At 3 s, old CMAB is 4.09 s against 3.19 s in Review I, and L2A-LL moved from 3.00 to 4.02 s on the same runs. Both moved together, so the cause is in the testbed between September and November. We have not isolated it, and we compare players only within a batch.

#### Q60. What does the stall guard cost?
Bitrate. On the trace under CUBIC, CMAB+ went from 1578–1776 kbps without the guard to 832–935 kbps with it, while rebuffering fell from 30.84–35.22% to 11.52–14.67%.

## J. Tricky faculty questions

#### Q61. Isn't CMAB+ just "Dynamic's throughput rule bolted onto CMAB"?
In spirit, partly, and the report says so: CMAB+ is closer to the throughput rule in Dynamic than to a new learner. The contribution is the diagnosis of why the published controller collapses, the evidence for which guard works and which do not (eight trials), and a fix that keeps the learner intact and passes the non-regression gate.

#### Q62. If L2A-LL is safer, why not just use L2A-LL?
Where stalls dominate the cost, that is the right choice, and we say so. Our goal was to repair the published bandit controller so that research on it can continue on slow links. On the trace, CMAB+ also gives a different trade-off: 2.5–7 times L2A-LL's bitrate for 4–14 points more rebuffering.

#### Q63. Your rebuffer reduction "71–86%" sounds large, but CMAB+ still stalls 15% on the trace. Isn't that bad?
Yes, 14.67% at a 3 s target under CUBIC is still high, and the report states it. The 71.4–86.0% is a relative cut from old CMAB, which rebuffers 78.55–84.61% under CUBIC and 28.98–32.88% under BBR on the trace. In absolute terms CMAB+ is 4–14 points worse than L2A-LL there.

#### Q64. Did you tune CMAB+ on the same data you evaluate on?
Partly, and we report it. The trials used the clock shaper and the capacity shaper; rule 5 was motivated by trace runs. The final trace matrix is a fresh run with the final player, but it is the same trace. We fixed pass criteria before the final matrices and did not tune after seeing them.

#### Q65. Are five sessions enough to claim anything?
For the 4 Mbit/s result, yes: old CMAB rebuffers 62–81% and CMAB+ 0% in every one of 40 sessions, and CMAB+'s latency interval is at most ± 0.05 s. For close comparisons, such as CUBIC 3 s on the paper clock where the intervals overlap, no, and we say the difference is not settled.

#### Q66. How do you know your fix doesn't simply pick low bitrates everywhere?
The paper-clock result: CMAB+ plays 5255–5462 kbps, 3 to 141 kbps more than old CMAB in seven of eight cells. It only lowers the bitrate where the link cannot carry the top rung.

#### Q67. What if the throughput estimate is wrong?
Then the clamp is wrong too. If it is too high (as at 1 Mbit/s CUBIC), CMAB+ picks a rung the link cannot sustain; rule 3 and rule 5 then pull it down after the fact. If it is too low, CMAB+ plays below what the link could carry. A margin or variance-aware cap is listed as future work.

#### Q68. Why did the paper use STRONG priority at all?
We can only read the code, not the authors' intent. STRONG makes CMAB's choice final over the other dash.js rules, which is natural if you want the learner to be in control. On a fast link it is harmless; on a slow one it removes the only safety net.

#### Q69. Doesn't removing the top-rung probe bias the bandit's learning?
It changes what the bandit observes: it never sees rewards from rungs above i* on a slow link. Those rungs would stall anyway, so their reward would be poor. On fast links i* is the top rung and nothing changes. LinTS's own updates are untouched.

#### Q70. The reward ignores stalls because P.1203 gets an empty stall list. Why didn't you fix that?
It would change the learner, and we wanted a fix that leaves the paper's learner and reward intact, so that every difference comes from the guard rules. Feeding stalls to the reward is the first item in our open problems.

#### Q71. Your trace has 100% loss at handover rows. Isn't that unrealistic?
It is the artifact's own trace shaper, which the authors ship; it is harsher than the clock shaper. Real handovers vary. We treat the trace as a stress test from one installation, not a model of all of Starlink.

#### Q72. Could the September-to-November drift also affect your CMAB+ conclusions?
It would affect any cross-batch comparison, which is why every Review III batch runs old CMAB, CMAB+ and L2A-LL side by side on the same stack and we compare only within a batch.

#### Q73. How did you avoid mixing CUBIC and BBR runs?
They ran sequentially, never at the same time, and the runners check the congestion control inside the nginx container before each batch.

#### Q74. What would you do with one more month?
Ten rounds per cell with the final player on every shaper; a margin under the throughput estimate; feeding stalls into the reward; rerunning Dynamic and LoL+; and, ideally, a dish measurement.

## K. Artifact, demo and team

#### Q75. Where is the code?
`github.com/pratham-commits/CMAB_plus`, branch `main`, commit `d60f163`, forked from the authors' repository at `dc120de`. The rules are in `cmabPlusPolicy.js`, unit-tested by `experiments/test_cmab_plus_policy.mjs`.

#### Q76. How is CMAB+ switched on?
The player setting `cmabHardened=true`, which applies to `abrCMAB` only.

#### Q77. Is the demo live streaming?
No. It replays recorded session timelines. The pane's quality and freezes follow the logged bitrate and buffer. That makes it repeatable and safe to show.

#### Q78. How can someone verify your data?
The archives have SHA-256 digests listed in the report and in `review-3/DATA_MANIFEST.md`, and each analysis script rebuilds the tables and stops if the session count is wrong.

#### Q79. How did the team divide the work?
Answer from your actual contributions. The final speaker script (`final-review/presentation/SPEAKER_SCRIPT.md`) splits the talk into three contiguous blocks of about 4 minutes each. Ved opens with the problem, Review I, the Review II BBR runs, the testbed faults and the diagnosis. Vidhu covers the collapse session, the CMAB+ design, the trials, the evaluation method, the headline numbers, the paper-clock non-regression result and the 4 Mbit/s results. Pratham covers the capacity sweep, the trace results, the stall guard, the demo, the limitations and the conclusion. Keep the answer consistent with that split.

---

[Back to the index](../GROUND_UP_GUIDE.md) · Previous: [Part 6](06-demo-artifact.md) · Next: [Part 8, glossary and cheat sheet](08-glossary-cheatsheet.md)
