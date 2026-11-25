# Final review: likely faculty questions

Short answers for the Q&A after the talk. The slides compare CMAB+ with old CMAB and show L2A-LL only as a reference; the L2A-LL answers below are here in case faculty ask. Numbers are from `report/paper.tex`; section and table references point there. The suggested answerer is the person who presented that part. Anyone can answer, but one person should speak per question.

## Scope and contribution

**1. Is CMAB+ a new algorithm or new theory?** (Vidhu)
No. LinTS, the context, the reward, the 15 s reset and the catch-up policy are the paper's. CMAB+ is five rules around the bandit's choice that bound it by measured throughput and hold a low rung after a stall. It is a systems repair of one implementation (report Section 6).

**2. Why not just use L2A-LL?** (Pratham)
Our goal was to repair the paper's controller, so the comparison that matters is CMAB+ against old CMAB. L2A-LL is in every batch as a reference. The two make different trade-offs. On the trace, L2A-LL holds rebuffering at 0.49–1.43% by staying at 301–482 kbps. CMAB+ keeps 2.5–3 times that bitrate under CUBIC and 5–7 times under BBR, and rebuffers 4.75–14.67%. If stalls are the main cost for a service, L2A-LL's choice is safer. At 4 Mbit/s and at 1 Mbit/s under BBR the two pick the same rung with no rebuffering. We do not claim CMAB+ beats L2A-LL.

**3. What exactly is your claim?** (Pratham)
When old CMAB's forced window asks for a rung the link cannot carry, CMAB+ keeps playback going: at 4 Mbit/s rebuffering drops from 62–82% to 0% at every target. On the paper's 100 Mbit/s shaper it behaves like old CMAB. On the Starlink trace it cuts rebuffering by 71–86% relative to old CMAB.

**4. Why does the forced top-rung window exist in the first place?** (Ved)
The paper does not describe it. Our reading is that it gathers samples for the top arm after each reset. It is in `CMABAbrController.js`, not in the paper's LinTS formulation, and neither is the STRONG switch priority.

**5. Why did the authors not see this bug?** (Ved)
Their emulator runs at 100 Mbit/s, or 50 Mbit/s during handovers, which is far above the 6000 kbps top rung, so the forced window costs nothing there. Their dish runs used a terminal without inter-satellite links. We cannot say how often a real dish stays below 6 Mbit/s for a full slot.

## Review II and transport

**6. What is your conclusion on BBR versus CUBIC?** (Ved)
On the clock shaper BBR changes little: CMAB at 3 s goes from 3.19 s to 3.29 s, with no rebuffering in either case. Under the capacity and trace shapers BBR helped old CMAB (65.69% against 82.25% rebuffering at 4 Mbit/s) but did not remove the collapse. In our setup the ABR's request policy mattered more than the congestion controller. We do not claim BBR is better for live streaming in general.

**7. How do you know D2 was the shaper and not BBR?** (Ved)
There are two checks. CMAB also failed under CUBIC on the same patched stack (about 16.6 s and 86% rebuffering), so BBR cannot be the cause. And in Review III the corrected trace shaper gave old CMAB 7.16 s and 28.98% under BBR at 3 s, almost the same as D2's 7.19 s and 28.32%.

**8. What was the restart bug?** (Ved)
The runner restarts nginx before each session. A Docker restart keeps the network namespace and its qdiscs, and the trace shaper's init only added classes, so it crashed and could leave the link at 100% loss. We now delete and rebuild the HTB root, and check the shaper mode inside the container before every batch.

**9. Why is BBR the only transport you tried?** (Ved)
The paper suggests BBR or satellite-aware control such as SaTCP for Starlink. BBR ships with Linux and changes only one sysctl on the server. We did not try SaTCP.

## Design

**10. What does the stall guard do?** (Pratham)
When a real quality is playing and the buffer is at or below 0.05 s, the rung cannot go up and is capped by 0.9 times the worst of the last eight segment throughputs. It turns off after 12 consecutive decisions with at least 1 s of buffer. On the trace it brought CUBIC rebuffering from 30.84–35.22% down to 11.52–14.67%, at a cost in bitrate.

**11. Why did you reject live latency as the step-down trigger?** (Vidhu)
A healthy player runs slightly above its target, so "step down when latency is above target" never clears and walked the ladder to 300 kbps (trial 3). A 1 s margin looked fine under BBR, but under CUBIC it sat on the margin line (4.02 s at a 3 s target) and cut bitrate to 3009 kbps on a link that carried 4955 kbps for old CMAB (trial 7). Throughput says whether the rung fits; latency does not.

**12. Why not delete the forced window?** (Vidhu)
We tried that in trial 1. CMAB stayed at 900 kbps at every target, because the bandit needs a probe after each reset. So rule 1 keeps the window and its length and changes only what it requests.

**13. Do hard-coded rules defeat the point of a learning controller?** (Vidhu)
The rules limit which arms are allowed. LinTS still chooses among the feasible arms. This is close to the throughput rule in dash.js Dynamic, which also bounds the choice by measured throughput.

**14. What is T-hat and why 0.9?** (Vidhu)
T-hat is dash.js `getSafeAverageThroughput`, which already applies a 0.9 safety factor. The stall guard uses the same 0.9 factor on the worst recent segment throughput.

**15. What does the switch-priority rule change?** (Vidhu)
Old CMAB issues every switch at STRONG priority, which overrides the dash.js throughput rule. CMAB+ issues an upward switch that the clamp reduced at DEFAULT priority, so other dash.js rules can veto it. Downward switches stay STRONG.

## Method and statistics

**16. Why only five rounds per cell?** (Vidhu)
Time on one VM. The 450 sessions are 37.5 hours of streaming, run one after another. We report 95% Student-t intervals with n = 5. They are tight at 4 Mbit/s (CMAB+ latency within ±0.05 s) and wide for some trace and 1 Mbit/s cells. Ten rounds would narrow them.

**17. Are the differences statistically significant?** (Vidhu)
We report intervals, not formal tests. At 4 Mbit/s and on the trace, the gaps between old CMAB and CMAB+ are far larger than the intervals. On the paper clock the differences fall inside the intervals, which is the non-regression result we wanted.

**18. Is the trace realistic?** (Pratham)
It is the artifact's one-hour Seychelles inter-satellite-link RTT trace, from one installation, sampled about every 10 ms, with a median RTT of about 130 ms. It carries RTT only, not capacity. Rows marking a handover are emulated as 100 ms, 100% loss and a 20 Mbit/s cap; other rows use the trace RTT, 1% loss and a 50 Mbit/s cap. Real handovers vary with location, time and load, and this is the harsher of the artifact's two shapers.

**19. Why not a live Starlink dish?** (Pratham)
We had no dish. All results are emulation through `tc` and netem. A dish measurement is the first item in our next steps.

**20. Is 4 Mbit/s a realistic Starlink rate?** (Vidhu)
We chose it to put the link between the 1500 and 4900 kbps rungs, so the top rung cannot fit. It is a controlled stress test, not a measured Starlink rate. We do not claim to know how often real links fall there.

**21. How is rebuffering measured, and does it match the paper?** (Vidhu)
It is the share of buffer samples at or below 0.05 s, after dropping the first 20% of each session. It is a sampled buffer-floor ratio, not wall-clock stall time, so it is not the paper's rebuffering-time ratio. The same function is used for all three reviews, so our tables compare with each other.

**22. Why are Review III CUBIC latencies about 0.9 s higher than Review I?** (Vidhu)
Both players moved: old CMAB went from 3.19 s to 4.09 s and L2A-LL from 3.00 s to 4.02 s at a 3 s target. So the cause is in the testbed between September and November, not in CMAB+. We have not isolated it and compare players only within a batch.

**23. Did you check the stall guard on the clock and 4 Mbit/s paths?** (Pratham)
Only with spot batches at a 3 s target. The project ledger records both as unchanged, but those session trees are not in the archives, so we report no numbers. The full clock and 4 Mbit/s matrices used rules 1–4.

**24. Why not rerun Dynamic and LoL+ in Review III?** (Pratham)
Time. We kept L2A-LL as the reference because it held targets as tightly as Dynamic in Review I, played the top rung throughout, and rebuffered least in D2.

## Results

**25. How does CMAB+ latency at 4 Mbit/s compare with the L2A-LL reference?** (Vidhu)
Both pick the 1500 kbps rung with no rebuffering, and CMAB+ is 0.19–0.23 s further from the target in every cell. CMAB+ lands 0.20–0.23 s above the 4–6 s targets and 0.54–0.62 s above 3 s, while L2A-LL sits on the target. We kept the paper's catch-up policy and have not isolated the cause of the gap.

**26. Why does CMAB+ rebuffer at 1 Mbit/s under CUBIC?** (Pratham)
It plays mostly the 900 kbps rung (mean 888 kbps), which fits T-hat but not the sustained rate, and rebuffers 16.54%. L2A-LL stays at 450 kbps with none. Rules 1 and 2 accept any rung at or below T-hat with no spare margin. A margin or a variance-aware cap is the obvious next change.

**27. At 8 Mbit/s CMAB+ does no better. Why?** (Pratham)
At 8 Mbit/s the top rung nominally fits (1.33 times 6000 kbps), so the clamp rarely binds. Both CMABs sit at 6.2–6.7 s with 1.8–3.5% rebuffering, and L2A-LL is better under both transports. The fix only matters when the requested rung does not fit.

**28. Did you not reproduce one of the paper's claims?** (Ved)
Yes. The paper says every ABR misses a 3 s target by at least 1.5 s. In our CUBIC reproduction the worst miss was 0.19 s. Our 20% trim removes start-up, and the paper's metric pipeline may differ. The cause is unexplained.

## Artifact

**29. Can someone reproduce this?** (Pratham)
The fork is at github.com/pratham-commits/CMAB_plus (commit d60f163). The rules are in `cmabPlusPolicy.js` with unit tests that run without Docker. Each matrix has a batch file and a runner script that checks the congestion control and qdisc inside nginx first. The archives have SHA-256 digests in `review-3/DATA_MANIFEST.md`, and the analysis scripts stop if the session count is wrong.

**30. What would you do next?** (Pratham)
Measure on a dish, run ten-round matrices with the final player on every shaper, add a margin to the clamp, and give the bandit a stall signal it can learn from. The artifact passes P.1203 an empty stalling list, so today stalls reach the reward only through the share-of-rebuffering term.
