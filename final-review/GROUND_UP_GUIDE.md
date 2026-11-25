# Ground-up guide: Track A7, from Review II to the final results

CS G525 Advanced Computer Networks, BITS Pilani. Track A7: low-latency live streaming over Starlink.

Team: Pratham Shah (2026H1030063P), Vidhu Kant Sharma (2026H1030053P), Ved Pahune (2026H1030056P). Tutor: Dr. Yash Sinha.

## How to use this guide

The guide assumes no networking background. Each part defines its terms before it uses them, and the glossary in Part 8 collects them all.

- Read Parts 0 to 5 in order the first time. They build on each other.
- Before the viva, read the cheat sheet in Part 8 and go through the question bank in Part 7.
- Every number comes from the final report (`report/paper.tex`) or the result files it cites. When a number exists only in our working notes, the text says "notes only". Those numbers are also listed at the end of this page.

## The short version

The MMSys '24 paper by Zhao and Pan built CMAB, a bitrate controller for live video over Starlink that relearns after every 15-second satellite handover. In Review I we reproduced their emulation. In Review II we switched the video server to BBR, got an alarming result, and traced it to our own testbed: the wrong traffic shaper and a shaper that broke on restart. On the fair setup BBR changed very little.

The alarming run still pointed at something real. After each handover, CMAB's code asks for the top 6000 kbps rung for seven decisions without checking whether the link can carry it. On a slower link the player stalls over and over, which we call forced-rung collapse. In Review III we kept the learner and wrapped it in five rules (CMAB+) that cap each request at measured throughput and hold a low rung after a stall.

Across 450 sessions, CMAB+ matches the original on the paper's 100 Mbit/s shaper. At 4 Mbit/s it cuts rebuffering from 62–82% to 0% at every latency target. On a Starlink ISL trace it cuts rebuffering by 71.4–86.0%, though L2A-LL still rebuffers less there. CMAB+ does not beat L2A-LL overall, and we do not claim it does.

## Outline

| Part | File | What it covers |
|---|---|---|
| 0 | [Foundations](guide/00-foundations.md) | Packets, Starlink and handovers, online and live video, DASH and ABR, CUBIC and BBR, bandits, emulation and the three shapers, metrics, statistics |
| 1 | [The paper and Review I](guide/01-paper-and-review1.md) | The paper in one page, what Track A7 asked, the reproduction and its results, corrections to the earlier Review I guide |
| 2 | [Review II](guide/02-review2.md) | Why BBR, the first run (D2), how we found the testbed faults, datasets D1 to D3, the fair result, lessons |
| 3 | [Review III and CMAB+](guide/03-review3-cmabplus.md) | Diagnosis, the arithmetic, a worked collapse timeline, the eight trials, the five rules with analogies, one decision step by step, code locations |
| 4 | [Experiments](guide/04-experiments.md) | The plan, Figure A, non-regression, capacity, 4 Mbit/s at every target, the ISL trace and the stall guard, how the numbers are produced |
| 5 | [Comparison and limitations](guide/05-comparison-limitations.md) | CMAB+ against L2A-LL, why CMAB+ matters, paper claims against our findings, limitations, what we did not claim, open problems |
| 6 | [Demo and artifact](guide/06-demo-artifact.md) | The replay demo, how to run it, a five-minute demo script, the `CMAB_plus` repository, archives and checksums |
| 7 | [Question bank](guide/07-qa-bank.md) | 79 questions from basic to hard, including likely faculty questions |
| 8 | [Glossary and cheat sheet](guide/08-glossary-cheatsheet.md) | Every term in one table, and a one-page sheet of the key numbers |

A combined PDF of all parts is at [GROUND_UP_GUIDE.pdf](GROUND_UP_GUIDE.pdf) if it was built.

## Sources

- Final report: `report/paper.tex` and `report/results/*.csv`.
- Review II: `review-2/details.md`, `review-2/docs/SHAPER_ROOT_CAUSE.md`, `review-2/docs/FACULTY_VERIFICATION_CMAB_BBR.md`, `review-2/audit/AUDIT_REPORT_BBR_TRACE_1010.md`, `review-2/presentation/FACULTY_QA.md`.
- Review III: `review-3/TRIALS.md`, `ALGORITHM.md`, `PROBLEMS.md`, `PAPER_CLAIM.md`, `METHOD.md`, `DATA_MANIFEST.md`, `review-3/results/`, `review-3/demo-ui/README.md`.
- Code: `CMABAbrController.js`, `CMABRule.js`, `cmabPlusPolicy.js` and the dash.js rule collection in the artifact fork.
- The original paper: Zhao and Pan, "Low-latency live video streaming over a low-earth-orbit satellite network with DASH", MMSys '24.

## Numbers that exist only in notes

These numbers are not in the final report. They come from working notes, and their session data is either not archived or not summarized in the report. Use them as background only, and say so if you quote them.

| Number | Where it comes from |
|---|---|
| Review II CUBIC validation: CMAB about 16.6 s latency, about 86% rebuffering, all 28 logged decisions on the top arm | Review II notes; the report only says CMAB "failed there too" |
| 1018 decisions on arm 7 in D2; about 800 or more arm logs in Review I | Review II notes |
| Trial 2: about 147 switches per session, 16% of samples below 0.5 s of buffer | `review-3/TRIALS.md` |
| Stall-guard spot checks: trace about 13% (CUBIC) and 7% (BBR); clock and 4 Mbit/s "unchanged" | `review-3/TRIALS.md`; session trees not archived |
| EWMA half-lives of 3 s and 8 s in dash.js throughput smoothing | dash.js defaults noted in our code reading, not in the report |
| Trial 7 L2A-LL at 5550 kbps and 4.06 s; trial 4 L2A-LL at 3.12 s | `review-3/TRIALS.md` |

One note on conflicting sources: where the notes and the report disagree, the guide follows the report. One example is the trace median RTT (about 130 ms in the report, 180 ms in the Review II notes).
