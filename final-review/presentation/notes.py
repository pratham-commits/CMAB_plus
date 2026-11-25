"""Speaker notes for final-review.pptx, one entry per slide.

`say` is the timed script (about 140-150 words per minute). `point` tells the
presenter where to look on a graph. `detail` is backup material for questions.
Numbers are from report/paper.tex and the CSVs named in make_slide_figures.py.
"""

SLIDES = [
    dict(title="Title", speaker="Ved", sec=20,
         say="""Good morning. We are Ved, Vidhu and Pratham, Track A7. We reproduced the MMSys '24 Starlink live-streaming paper, extended it to BBR, and ended with a fix to its bitrate controller, CMAB+. Today covers Review II through the final results.""",
         detail="""Paper: Zhao and Pan, MMSys '24. Artifact commit dc120de. Our fork: github.com/pratham-commits/CMAB_plus, commit d60f163."""),

    dict(title="Starlink reschedules satellites every 15 s", speaker="Ved", sec=35,
         say="""Starlink reassigns terminals to satellites every 15 seconds, at seconds 12, 27, 42 and 57 of each minute, and RTT and loss jump at those instants. A low-latency live player at a 3-second target holds only one or two 2-second segments, so it has little room to absorb that. Zhao and Pan's CMAB treats each of the eight bitrate rungs, 300 to 6000 kbps, as an arm of a contextual bandit and resets it at every slot. We call it old CMAB.""",
         point="""The orange marks on the minute bar are the handover seconds.""",
         detail="""Schedule from Tanveer et al. and Pan et al. CMAB learns with Linear Thompson Sampling (LinTS). Context: measured latency, playback speed, estimated throughput. Reward: ITU-T P.1203 O.46 score times target/measured latency times a bitrate ratio, minus the share of rebuffering time at the chosen bitrate. Ladder: 300, 450, 900, 1200, 1500, 4900, 5100, 6000 kbps, 2 s segments, served by livesim2."""),

    dict(title="Review I: we reproduced the paper's emulation", speaker="Ved", sec=25,
         say="""In Review I we ran the authors' artifact: four ABRs, four targets, ten rounds, 160 five-minute sessions under CUBIC on the default clock shaper. CMAB at a 3-second target ran at 3.19 seconds with no rebuffering. One claim did not reproduce: the paper says every ABR misses 3 seconds by at least 1.5; our worst miss was 0.19.""",
         detail="""GCP e2-standard-4, asia-south1-c. Clock shaper: 100 Mbit/s, 40 ms, 0.1% loss; 50 Mbit/s, 100 ms, 1% loss in each handover second. Our metric drops the first 20% of each session; the paper's pipeline may differ. Cause of the gap is unexplained. One CMAB round at 5 s had 13.38 s and 25.24% rebuffer; kept in the mean (cell: 6.05 s, 2.52%)."""),

    dict(title="Review II: the first BBR run looked like a failure", speaker="Ved", sec=25,
         say="""Review II switched the server to BBR and reran the same 160 sessions. The first run put CMAB at 7.19 seconds and 28 percent rebuffering at a 3-second target. Before blaming BBR, we checked CUBIC on the same stack, and CMAB failed there too. A CUBIC failure is not a BBR effect, so we audited the testbed.""",
         detail="""BBR set on the nginx container with sysctl; ABRs and batch file unchanged. Prefix 1010-0432: CMAB 7.19 s / 28.32% / 5795 kbps at 3 s. CUBIC validation: about 16.6 s, 86% rebuffer, all 28 logged decisions on the top arm (Review II notes)."""),

    dict(title="Two testbed faults explained the first run", speaker="Ved", sec=35,
         say="""We found two faults. First, the run used the trace shaper, a Starlink inter-satellite-link trace with about 130 ms RTT and full loss at handovers, while Review I used the clock shaper. Different experiments. Second, nginx restarts before every session, and the trace shaper crashed on restart because old queueing state survived, which could leave the link at 100 percent loss. We fixed the setup, checked the shaper before each batch, and reran on the clock shaper.""",
         detail="""Docker restart keeps the network namespace and qdiscs; tc-trace.py init only added classes. Fix: delete and rebuild the HTB root. The wrong shaper explains D2: in Review III the corrected trace shaper gave old CMAB 7.16 s and 28.98% under BBR at 3 s, almost the same as D2. Rerun prefix 1017-0606."""),

    dict(title="On the clock shaper, BBR changes little", speaker="Ved", sec=30,
         say="""That gives three datasets: D1, Review I on the clock shaper; D3, BBR on the clock shaper; D2, the first BBR run on the trace. On the clock shaper BBR changes little: CMAB goes from 3.19 to 3.29 seconds, with zero rebuffering in both. D2 supports no transport claim. The lesson: separate testbed faults from transport effects first.""",
         point="""Blue and green lines sit on the target; orange (D2) is far above. The D1 spike at 5 s is one outlier round.""",
         detail="""Mean of 10 sessions, 95% t intervals. CMAB bitrate 4955 (CUBIC) vs 5223 kbps (BBR). Other ABRs stayed within 0.12 s of their CUBIC latency."""),

    dict(title="On D2, only CMAB kept requesting ~5800 kbps", speaker="Ved", sec=30,
         say="""This chart puts all four ABRs side by side at a 3-second target. On the clock runs, blue and green, everyone sits near 3 seconds with no rebuffering. On D2, in orange, the other three adapted down: Dynamic to 619 kbps, LoL+ to 861. CMAB kept about 5800 kbps and rebuffered 28 percent. That pointed at the controller.""",
         point="""Middle panel: the tall orange CMAB bar. Right panel: orange bars for Dynamic, L2A-LL and LoL+ are short; CMAB's is near 6000.""",
         detail="""D2 at 3 s: Dynamic 4.13 s / 1.10% / 619 kbps; L2A-LL 3.81 s / 0.59% / 359 kbps; LoL+ 4.64 s / 5.40% / 861 kbps; CMAB 7.19 s / 28.32% / 5795 kbps. D1 and D3 rebuffering is 0.00% everywhere except LoL+ under D3 (0.01%). Data: report/results/review12-aggregate.csv."""),

    dict(title="Diagnosis: forced-rung collapse", speaker="Ved", sec=45,
         say="""So we read the controller code. For the first seven decisions after each slot boundary, it skips LinTS and requests 6000 kbps without checking throughput, at a priority that overrides dash.js's throughput rule. A slot holds only seven or eight decisions. A 6000 kbps segment is 12 megabits: at least 3 seconds to fetch on a 4 Mbit/s link for 2 seconds of video, so every forced decision drains the buffer. On the paper's 100 Mbit/s shaper the top rung fits, which is why it never showed up there. Vidhu will show the collapse in one session and then the fix.""",
         point="""Top row (orange): seven forced 6000 boxes. Bottom row (blue) is CMAB+, covered next.""",
         detail="""Files: CMABAbrController.js and CMABRule.js. Window length |A|-1 = 7. Priority: dash.js STRONG. Neither is in the paper's LinTS formulation. A stalled player makes even fewer decisions, so LinTS may never get a turn before the next reset."""),

    dict(title="On 4 Mbit/s, old CMAB never leaves 6000 kbps", speaker="Vidhu", sec=25,
         say="""Thanks Ved. Here is the collapse in one real session on a fixed 4 Mbit/s link. Old CMAB, orange, requests 6000 kbps for the whole minute and its buffer sits at the floor. CMAB+, blue, holds 1500 kbps and keeps the buffer between about half a second and 2.5 seconds.""",
         point="""Top: the orange line above the 4 Mbit/s bottleneck line. Bottom: orange flat at zero, blue oscillating 0.5–2.5 s.""",
         detail="""One session per player, CUBIC, 3 s target, round 0, first full minute after 120 s of playback. Grey bands: handover seconds. Source: report Fig. 2."""),

    dict(title="CMAB+: same LinTS bandit, five rules around it", speaker="Vidhu", sec=40,
         say="""CMAB+ keeps the paper's learner unchanged and adds five rules around its choice. T-hat is the dash.js throughput estimate. One: probe the highest rung that fits T-hat, not the top rung. Two: clamp later LinTS choices to that rung. Three: if the rung playing is above T-hat, step down one. Four: a clamped up-switch uses default priority, so dash.js can veto it. Five, the stall guard: after the buffer empties, cap the rung by recent worst-case throughput until the buffer recovers.""",
         detail="""Unchanged: LinTS, context, reward, 15 s reset, catch-up. T-hat = getSafeAverageThroughput (includes 0.9 factor). i-star = max{i : r_i <= T-hat}, 0 if missing. Rule 3: if r_q > T-hat the arm cannot rise and is at most q-1. Rule 4: only an upward switch that rule 2 reduced uses DEFAULT; others STRONG. Rule 5: buffer <= 0.05 s with a real quality playing; cap at 0.9 x min of last 8 segment throughputs; off after 12 consecutive decisions with >= 1 s buffer. Flag cmabHardened=true, abrCMAB only; cmabPlusPolicy.js with unit tests. A repair of one implementation, not a new bandit."""),

    dict(title="Eight trials before the final rules", speaker="Vidhu", sec=25,
         say="""We got there through eight trials. With no probe at all, CMAB stayed at 900 kbps. Latency as the step-down trigger failed, because a healthy player runs a little above its target: it walked down to 300 kbps. Throughput as the trigger worked, and the stall guard came last, from trace runs.""",
         point="""The verdict column: orange rejected, green kept.""",
         detail="""Trial 2 (probe + clamp only): 4.99 s at 3 s under BBR. Trial 4 under BBR: 3.32 s, 4894 kbps; trial 7 under CUBIC: 4.02 s, 3009 kbps against 4955 for old CMAB. Trials 5 and 6 (one-rung and graded climbs) were worse. Guard variants with a spare rung or forced bottom rung were flat or worse."""),

    dict(title="Method: three shapers, two transports, 450 runs", speaker="Vidhu", sec=30,
         say="""Each batch ran old CMAB and CMAB+ side by side, with L2A-LL as a reference, under CUBIC and BBR. Three shapers: the paper's clock; a capacity clock fixed at 8, 4 or 1 Mbit/s; and the Starlink trace. Five 300-second rounds per cell, 450 sessions. We drop the first 20 percent and report latency, rebuffer ratio and bitrate with 95 percent confidence intervals.""",
         detail="""Same VM and stack as Review I; CUBIC and BBR runs sequential. 37.5 hours of video. 4 Mbit/s sits between the 1500 and 4900 kbps rungs. Trace: one-hour Seychelles ISL RTT trace, median ~130 ms; handover rows emulated as 100 ms, 100% loss, 20 Mbit/s cap; other rows trace RTT, 1% loss, 50 Mbit/s cap. Rebuffer ratio = share of buffer samples <= 0.05 s. Student-t, t = 2.776, n = 5. L2A-LL kept as reference: tight targets in Review I, least rebuffering in D2. Pass gates fixed in advance: same class as old CMAB on the paper clock, no collapse at 4 Mbit/s, less rebuffering than old CMAB on the trace without living on the bottom rung."""),

    dict(title="Results at a glance: CMAB+ against old CMAB", speaker="Vidhu", sec=25,
         say="""The headline numbers first, all against old CMAB. On the paper's shaper, no regression. At 4 Mbit/s, rebuffering goes from 62–82 percent to zero at every target. At 1 Mbit/s, from 99 percent to zero under BBR. On the Starlink trace, 71 to 86 percent less. The next slides walk through each.""",
         point="""The four big numbers, left to right, top to bottom.""",
         detail="""1 Mbit/s CUBIC: 98.79% -> 16.54%. 1 Mbit/s BBR: 99.13% -> 0%. Trace latency falls 1.1-13.5 s. Clock and 4 Mbit/s numbers use rules 1-4; trace uses rules 1-5."""),

    dict(title="Paper clock: CMAB+ latency tracks old CMAB", speaker="Vidhu", sec=25,
         say="""How to read these: one panel per transport, target on the x-axis, measured latency on the y-axis, and the dash-dot line is the target. Orange is old CMAB, blue CMAB+, grey L2A-LL as a reference. Blue sits on orange in every cell, at most 0.15 seconds apart and inside the confidence intervals.""",
         point="""The blue and orange lines overlapping in both panels; the one wide orange interval is BBR at 5 s.""",
         detail="""CMAB+ is 0.28 s faster under BBR at 5 s. CUBIC latencies here are ~0.9 s higher than Review I for both old CMAB (4.09 vs 3.19 s) and the reference (4.02 vs 3.00 s): testbed drift between September and November, not isolated. We compare players only within a batch. Rules 1-4."""),

    dict(title="Paper clock: CMAB+ keeps old CMAB's bitrate", speaker="Vidhu", sec=20,
         say="""Same runs, bitrate. The orange and blue bars match at every target: CMAB+ plays between 11 kbps less and 141 kbps more than old CMAB, with zero rebuffering in every CUBIC cell.""",
         point="""Pairs of orange and blue bars at equal height around 5200-5500 kbps.""",
         detail="""Seven of eight cells +3 to +141 kbps, one cell -11 kbps. BBR rebuffer: old CMAB 0.26% at 5 s; CMAB+ 0.08% at 5 s and 0.38% at 6 s; all intervals include zero. Stall guard spot-checked only on this path; spot sessions are not archived, so no numbers."""),

    dict(title="4 Mbit/s: rebuffering 62–82% → 0% at every target", speaker="Vidhu", sec=25,
         say="""Now a fixed 4 Mbit/s link, where the top rung cannot fit. The orange bars are old CMAB: 62 to 82 percent rebuffering at every target, under both transports. The blue bars are at zero: CMAB+ did not rebuffer in any of its 40 sessions, and it plays about 1470 kbps.""",
         point="""Tall orange bars with the percentages on top; blue labelled 0% next to each.""",
         detail="""Old CMAB: 71.70-80.59% (CUBIC), 62.05-69.23% (BBR), always 6000 kbps. CMAB+: 1457-1477 kbps. Rules 1-4."""),

    dict(title="4 Mbit/s: CMAB+ cuts latency by 46.5–58.7%", speaker="Vidhu", sec=25,
         say="""Latency on the same runs. Old CMAB, orange, sits 5.6 to 5.9 seconds above the target line. CMAB+ follows the target: about 0.2 seconds above it at 4 to 6 seconds, and about 0.6 above at 3. That is a 46.5 to 58.7 percent latency cut. Pratham takes the capacity sweep, the Starlink trace and the demo.""",
         point="""The gap between the orange line and the dash-dot target line; blue hugging the target.""",
         detail="""CMAB+ 0.20-0.23 s above the 4-6 s targets and 0.54-0.62 s above 3 s. CMAB+ latency intervals are at most +/-0.05 s."""),

    dict(title="Capacity: rebuffering drops where 6000 kbps cannot fit", speaker="Pratham", sec=30,
         say="""Thanks Vidhu. The capacity sweep at a 3-second target: 8, 4 and 1 Mbit/s on the x-axis. At 8 the top rung fits, so the two CMABs behave alike, as expected. At 4, CMAB+ goes to zero. At 1 Mbit/s old CMAB rebuffers 99 percent; CMAB+ reaches zero under BBR and 17 percent under CUBIC, which is our next item to fix.""",
         point="""Left group (8): small bars for both. Middle and right groups: tall orange, short or zero blue.""",
         detail="""8 Mbit/s: both CMABs 1.8-3.5% rebuffer, 6.2-6.7 s. 4 Mbit/s: 82.25% -> 0 (CUBIC), 65.69% -> 0 (BBR). 1 Mbit/s: 98.79% -> 16.54% (CUBIC), 99.13% -> 0 (BBR). At 1 Mbit/s CUBIC CMAB+ plays mostly 900 kbps, which fits T-hat but not the sustained rate; the clamp has no spare margin. Old CMAB BBR 1 Mbit/s latency mean (47.04 s) includes one 131.26 s session."""),

    dict(title="Capacity: CMAB+ picks a rung below the link rate", speaker="Pratham", sec=25,
         say="""Bitrate on the same runs. The dash-dot line in each group is the link rate. Old CMAB's orange bars stay at 6000 kbps even when the link carries 4 or 1 Mbit/s. CMAB+'s blue bars sit under the line in every cell: about 1475 kbps at 4, and 450 to 888 at 1.""",
         point="""Orange bars crossing above the dash-dot line at 4 and 1 Mbit/s; blue bars below it.""",
         detail="""CMAB+: 5721 / 5804 kbps at 8 Mbit/s; 1473 / 1477 at 4; 888 / 450 at 1 (CUBIC / BBR)."""),

    dict(title="Starlink trace: rebuffering cut by 71–86% at every target", speaker="Pratham", sec=30,
         say="""Back to the Starlink trace, now with the final player. Orange, old CMAB: about 80 percent rebuffering under CUBIC and about 30 under BBR at every target. Blue, CMAB+: at a 3-second target, 81 down to 15 percent under CUBIC, and 29 down to 8 under BBR. Across all eight cells, a 71 to 86 percent cut. Grey is the L2A-LL reference.""",
         point="""Orange bars versus blue bars at each target; read the labels on top.""",
         detail="""Old CMAB: 78.55-84.61% (CUBIC), 28.98-32.88% (BBR). CMAB+: 11.52-14.67% (CUBIC), 4.75-8.29% (BBR). Rules 1-5."""),

    dict(title="Starlink trace: CMAB+ leaves the 6000 kbps lock", speaker="Pratham", sec=20,
         say="""Bitrate on the trace. Old CMAB stays near 6000 kbps, which this link cannot sustain. CMAB+ moves to rungs the trace can carry: about 830 to 935 kbps under CUBIC and 2500 to 2900 under BBR. Latency also falls by 1.1 to 13.5 seconds.""",
         point="""Orange near the top in every group; blue lower, and higher under BBR than under CUBIC.""",
         detail="""CMAB+: 832-935 kbps (CUBIC), 2499-2917 kbps (BBR). Old CMAB: 6000 (CUBIC), 5882-5913 (BBR). Old CMAB latency 18.5-20.9 s (CUBIC) and 7.16-10.19 s (BBR); CMAB+ 6.46-8.84 s (CUBIC) and 6.05-7.93 s (BBR)."""),

    dict(title="Stall guard more than halves CUBIC rebuffering", speaker="Pratham", sec=30,
         say="""This isolates the fifth rule. Light bars are CMAB+ with rules one to four, dark bars with the stall guard added, on the same trace. Under CUBIC, rebuffering falls from 31–35 percent to 12–15; under BBR, from 9–12 to 5–8. The bottom row shows the price: the guard holds lower rungs, so bitrate drops.""",
         point="""Top row: light versus dark bars. Bottom row: the bitrate cost.""",
         detail="""Pre-guard run 2026-11-08 (report/results/trace-pre-stallguard-aggregate.csv), a separate batch; old CMAB in that batch rebuffered 79.6-80.7% (CUBIC). CUBIC bitrate 1578-1776 -> 832-935 kbps; BBR 3062-3783 -> 2499-2917 kbps."""),

    dict(title="Trace session: after a stall, CMAB+ holds a low rung", speaker="Pratham", sec=30,
         say="""Here is that behaviour in one real session, CUBIC at a 3-second target. At about 105 seconds CMAB+'s buffer empties. In the shaded band it stays at 450 kbps for about 21 seconds while the buffer refills, then steps back up to 900. Old CMAB, orange, stays at 6000 kbps with its buffer at the floor.""",
         point="""The shaded band in both panels: flat blue bitrate on top, refilling blue buffer below.""",
         detail="""Sessions abrCMABPlus-1107-1442 and abrCMAB-1107-1442, round 0, from the demo catalog (~2 Hz). The logs do not record the guard state; the hold matches the guard's 12-decision release rule (about 24 s of 2 s segments). Session time on the x-axis; the two sessions ran at different wall-clock times."""),

    dict(title="Demo: side-by-side replay of logged sessions", speaker="Pratham", sec=25,
         say="""The demo replays logged sessions; it does not run a live player. Here, old CMAB, CMAB+ and the L2A-LL reference on the 4 Mbit/s link, with a countdown to the next handover. In this session old CMAB spends 81 percent of the time rebuffering and CMAB+ none.""",
         detail="""Run: cd review-3/demo-ui; npm install; npm run dev; open http://localhost:5173. Screenshot: Phase 3, "4 Mbit latency targets", 3 s CUBIC, round 0; header values are per session, not 5-round means. Other tabs: Review I and II, trace with stall guard, capacity sweep, Algorithm, Problems we faced. The UI summary line says "four hardened rules" while listing five."""),

    dict(title="Scope and next steps", speaker="Pratham", sec=25,
         say="""On scope. Everything is emulation from one hour of trace at one site, so a dish measurement comes next. Five rounds per cell; ten would narrow the wider intervals. The stall guard should be rerun on the clock and 4 Mbit/s matrices, and the clamp needs a safety margin for the 1 Mbit/s CUBIC case.""",
         detail="""Handover rows are modeled as 100% loss; real handovers vary with location, time and load. Rebuffer metric counts buffer samples at the floor, not wall-clock stall time. Dynamic and LoL+ were not rerun in Review III. The artifact passes P.1203 an empty stalling list, so stalls reach the reward only through the share-of-rebuffering term."""),

    dict(title="Conclusion", speaker="Pratham", sec=20,
         say="""To close: the BBR failure was a testbed mistake, and following it into the code found a forced top-rung window after every handover. Bounding exploration by measured throughput removes the collapse without changing the bandit. Code and data are on GitHub. Thank you.""",
         detail="""Repository: github.com/pratham-commits/CMAB_plus (branch main, commit d60f163)."""),
]


def fmt(sec: int) -> str:
    return f"{sec // 60}:{sec % 60:02d}"


def notes_text(i: int) -> str:
    s = SLIDES[i]
    out = f"{s['speaker'].upper()} ({fmt(s['sec'])})\n\nSAY:\n{s['say']}\n\n"
    if s.get("point"):
        out += f"POINT AT:\n{s['point']}\n\n"
    return out + f"DETAIL IF ASKED:\n{s['detail']}"


HEADER = """# Final review: speaker script

CS G525 Advanced Computer Networks, Track A7. Deck: `final-review.pptx` (26 slides).
Team: Pratham Shah (2026H1030063P), Vidhu Kant Sharma (2026H1030053P), Ved Pahune (2026H1030056P). Tutor: Dr. Yash Sinha.

Each speaker presents one contiguous block of about 4 minutes, with a handoff only at slides 9 and 18. Ved (slides 1-8) opens and covers Starlink, Review I, the Review II BBR runs, the testbed faults and the diagnosis of the forced window. Vidhu (slides 9-17) shows the collapse in one session, then the CMAB+ design, the trials, the method, the headline numbers, the paper-clock results and the 4 Mbit/s results. Pratham (slides 18-26) covers the capacity sweep, the Starlink trace, the stall guard, the demo, scope and the conclusion. "Say" is sized at about 140-150 words per minute. "Point at" says where to look on the graph. "Detail if asked" is backup; do not read it out. The same text is in each slide's notes field.

Every graph uses the same colours: orange for old CMAB, blue for CMAB+, grey for L2A-LL as a reference. Error bars are 95% Student-t intervals. Numbers come from `report/paper.tex` and the CSVs listed in `make_slide_figures.py`; if a number here disagrees with the report, the report wins.
"""

FOOTER = """
## Running the demo

Before the review, on the presenting laptop:

```bash
cd review-3/demo-ui
npm install
npm run dev        # http://localhost:5173
```

The videos live in `public/video/`; if they are missing, run `bash scripts/fetch-video.sh` (about 1.1 GB) before the day. Open Phase 3, family "4 Mbit latency targets", cell "3 s CUBIC". The app starts paused; press Play. If the laptop, browser or projector fails, stay on the demo slide and describe the screenshot. Stop the dev server afterwards.

## If time runs short or long

Each speaker keeps to their own block, so a cut or an addition stays inside it and the handoff times (4:05 and 8:05) hold.

- Ved over time: shorten slide 7 to the CMAB bar and one sentence ("the other three ABRs adapted down; CMAB stayed near 5800 kbps"). That saves about 15 s.
- Vidhu over time: skip the trials table (slide 11) with one sentence ("we rejected latency as the step-down trigger"), and give the paper-clock bitrate slide (slide 15) one sentence. Together that saves about 30 s.
- Pratham over time: give the capacity bitrate and trace bitrate slides (slides 19 and 21) one sentence each. That saves about 30 s.
- Pratham under time: on the demo slide press Play for 20 s, then switch to the trace tab.
- Keep slide 13 (headline numbers), the 4 Mbit/s rebuffer slide (16) and the trace rebuffer slide (20) in every version.
"""


def write_script(path) -> None:
    lines = [HEADER, "## Timing", "",
             "| # | Slide | Speaker | Time | Ends at |", "|---|---|---|---|---|"]
    total, per = 0, {}
    for i, s in enumerate(SLIDES, 1):
        total += s["sec"]
        per[s["speaker"]] = per.get(s["speaker"], 0) + s["sec"]
        lines.append(f"| {i} | {s['title']} | {s['speaker']} | {fmt(s['sec'])} | {fmt(total)} |")
    lines += ["", f"Total {fmt(total)}. " + ", ".join(f"{k} {fmt(v)}" for k, v in per.items()) + ".", ""]
    for i, s in enumerate(SLIDES, 1):
        lines += [f"## Slide {i}: {s['title']}", "",
                  f"**{s['speaker']}, {fmt(s['sec'])}**", "", s["say"], ""]
        if s.get("point"):
            lines += [f"Point at: {s['point']}", ""]
        lines += [f"Detail if asked: {s['detail']}", ""]
        if i < len(SLIDES) and SLIDES[i]["speaker"] != s["speaker"]:
            lines += [f"Handoff to {SLIDES[i]['speaker']}.", ""]
    lines.append(FOOTER)
    path.write_text("\n".join(lines))


if __name__ == "__main__":
    from pathlib import Path
    out = Path(__file__).resolve().parent / "SPEAKER_SCRIPT.md"
    write_script(out)
    print("wrote", out)
