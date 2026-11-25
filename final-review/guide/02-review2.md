# Part 2. Review II: BBR, a scary result, and a shaper confound

[Back to the index](../GROUND_UP_GUIDE.md) · Previous: [Part 1](01-paper-and-review1.md) · Next: [Part 3, Review III and CMAB+](03-review3-cmabplus.md)

---

## 2.1 The question and why BBR

Review II asked whether a Starlink handover is mainly an ABR problem or a transport problem.

The reasoning for trying BBR:

- A handover second brings 1% loss and a jump in RTT.
- CUBIC treats loss as congestion and cuts its window, so throughput dips after each handover.
- BBR paces at its estimate of bottleneck bandwidth and does not cut on every loss, so it might recover from a lossy second faster.
- The MMSys '24 paper itself suggests BBR as a possible improvement over CUBIC on Starlink.

If BBR made CMAB much better, the transport was the main problem. If it changed little, the ABR was.

## 2.2 What we changed and what we kept

We changed exactly one setting: the congestion control of the nginx container (the video sender), set to BBR with `sysctl net.ipv4.tcp_congestion_control=bbr`. Everything else stayed the same: the four ABRs, the batch file, the ladder, 300-second sessions, ten rounds, four targets, 160 sessions.

Changing one variable at a time is the basic rule of a fair experiment. If two things change at once, you cannot tell which one caused the result. Keep this rule in mind, because the first run broke it without our noticing.

## 2.3 The first run and the scary result (dataset D2)

The first complete BBR matrix (session prefix `1010-0432`) finished all 160 sessions; an audit found 160 of 160 production sessions and excluded three 60-second smoke tests. At the 3 s target it gave:

| ABR | Live latency (s) | Rebuffer ratio (%) | Bitrate (kbps) |
| --- | ---: | ---: | ---: |
| Dynamic | 4.13 | 1.10 | 619 |
| L2A-LL | 3.81 | 0.59 | 359 |
| LoL+ | 4.64 | 5.40 | 861 |
| CMAB | 7.19 | 28.32 | 5795 |

CMAB was more than 4 s off its target and stalled more than a quarter of the time. Under CUBIC in Review I it had been 3.19 s with no stalls. The easy headline was "BBR breaks CMAB".

Two things in this table should have raised doubts at once:

- Every ABR dropped to a much lower bitrate (Dynamic 619 kbps, L2A-LL 359 kbps) on a link that, in Review I, carried 6000 kbps easily. A change of congestion control alone should not cut the usable rate by a factor of ten on a 100 Mbit/s link.
- Only CMAB stayed near the top rung (5795 kbps) while the others adapted down.

## 2.4 How we found the real cause

We did not publish the headline. Instead we ran a check.

Step 1: a control run. Before blaming BBR, we ran a small validation on the same patched stack with CUBIC, the transport that had worked in Review I. CMAB failed there too. Our Review II notes record about 16.6 s latency, about 86% rebuffering, and all 28 logged decisions on the top arm, while Dynamic on the same stack was about 4.3 s with little rebuffering. (These validation numbers exist only in the Review II notes, `review-2/docs/SHAPER_ROOT_CAUSE.md`, not in the report tables.)

Step 2: the logic. A BBR effect cannot explain a failure under CUBIC. So something else in the testbed had changed between Review I and Review II.

Step 3: a red flag in the logs. In Review I, a CMAB session logged hundreds of bandit decisions (our notes say about 800 or more). In the failed sessions it logged only a few dozen. A player that is stalled most of the time downloads few segments, so it makes few decisions.

Step 4: the audit found two faults.

### Fault 1: the wrong shaper

The run had used the trace shaper (`SHAPER=trace`) instead of the clock shaper (`SHAPER=clock`) that Review I used. The trace shaper replays the Seychelles ISL latency trace, with a median RTT of about 130 ms and 100% loss on handover rows. It is a different and much harsher experiment. So the first BBR run changed two things at once: the congestion control and the network.

### Fault 2: a restart bug in the trace shaper

The batch runner restarts the nginx container before every session. A Docker restart keeps the container's network namespace, including the old `tc` queueing disciplines. The trace shaper's start-up code only added traffic classes and never deleted or rebuilt the root qdisc. On restart, the classes already existed, the Python script crashed, and the supervisor restarted it in a loop. The link could be left frozen in whatever state the trace was in, sometimes a 100%-loss handover row.

### Which fault explains the D2 numbers?

Fault 1. The evidence: in Review III we reran the old CMAB player on the corrected trace shaper under BBR and got almost the same result, 7.16 s and 28.98% at 3 s, against 7.19 s and 28.32% in D2. So D2 is what CMAB does on that trace, not a crash artifact. Fault 2 is a reliability problem that could have corrupted runs, so we fixed it anyway.

### The fixes

1. Rewrote the trace shaper's start-up to delete and rebuild the HTB root qdisc, so it survives a restart.
2. Set `SHAPER=clock` for the BBR rerun.
3. Checked the shaper mode and the congestion control inside the running nginx container before each batch, and saved the values (`review-2/meta/nginx-SHAPER.txt`, `nginx-tcp_cc.txt`).
4. Reran the full 160-session BBR matrix on the clock shaper (prefix `1017-0606`).

## 2.5 The three datasets

To avoid ever mixing them again, we named the datasets.

| Name | Transport | Shaper | Session prefix | What it may be used for |
| --- | --- | --- | --- | --- |
| D1 | CUBIC | clock | `0929-1424` | Review I baseline |
| D2 | BBR | trace | `1010-0432` | Superseded first run; shows controller behaviour on the trace, supports no transport claim |
| D3 | BBR | clock | `1017-0606` | The fair BBR comparison with D1 |

The one-line answer for a faculty member: "The 7-second CMAB number is D2, which used the trace shaper. The 3.3-second BBR number is D3, which used the same clock shaper as Review I."

## 2.6 The fair result: D1 versus D3

Report Table 1 and Appendix B (mean of 10 sessions):

| ABR | Target | D1 CUBIC clock: latency / kbps | D3 BBR clock: latency / kbps |
| --- | --- | --- | --- |
| Dynamic | 3 s | 3.00 / 5909 | 3.12 / 5123 |
| L2A-LL | 3 s | 3.00 / 6000 | 3.11 / 6000 |
| LoL+ | 3 s | 3.08 / 4938 | 3.14 / 5454 |
| CMAB | 3 s | 3.19 / 4955 | 3.29 / 5223 |
| CMAB | 4 s | 4.20 / 4989 | 4.21 / 5167 |
| CMAB | 5 s | 6.05 / 4951 | 5.21 / 5165 |
| CMAB | 6 s | 6.24 / 5021 | 6.23 / 5205 |

Rebuffering is 0.00% in every D1 and D3 cell except D1 CMAB at 5 s (2.52%, the outlier round) and D3 LoL+ at 3 s (0.01%).

What this means:

- Under the clock shaper, BBR changes little. CMAB at 3 s moves from 3.19 to 3.29 s, with no stalls, and its bitrate rises from 4955 to 5223 kbps.
- The other ABRs stay within 0.12 s of their CUBIC latency.
- On this path, with 100 Mbit/s of capacity, the transport has a small effect. The handover problem in this emulator is not mainly a TCP problem.

## 2.7 What D2 still taught us

D2 supports no claim about BBR, because it changed the network too. But it held one useful comparison: on the same trace, in the same batch, Dynamic adapted down to 619 kbps and survived, while CMAB kept requesting about 5800 kbps and stalled. Same network, same transport, different controller. That pointed at CMAB's control logic, which is where Review III started.

Our Review II notes list the code-level suspects (named RC1 to RC7 in `review-2/docs/FACULTY_VERIFICATION_CMAB_BBR.md`). The three that were proven from the code:

| Note ID | Mechanism |
| --- | --- |
| RC1 | CMAB's switch uses STRONG priority and has no cap against the throughput estimate |
| RC2 | After each slot boundary, the code forces the top arm for the first 7 decisions (the number of arms minus one) |
| RC3 | The P.1203 input has an empty stall list, so the quality score does not see stalls |

The notes also recorded supporting evidence from the arm logs: in D2, CMAB's choices were dominated by arm 7 (1018 counts summed over ten sessions at 3 s). Treat these arm counts as notes-only numbers.

## 2.8 Lessons from Review II

1. Verify the configuration inside the running system, not in the config file. The `SHAPER` variable was set differently from what we assumed.
2. Change one variable at a time, and check that you did.
3. Run a control. A failure that also appears under the old, known-good condition points at the testbed.
4. Name and separate datasets. Mixing D2 into a CUBIC-versus-BBR comparison would have produced a false conclusion.
5. A strange result can still carry information. The Dynamic-versus-CMAB contrast in D2 led to the bug Review III fixed.

---

[Back to the index](../GROUND_UP_GUIDE.md) · Previous: [Part 1](01-paper-and-review1.md) · Next: [Part 3, Review III and CMAB+](03-review3-cmabplus.md)
