# Part 6. The demo UI, the artifact, and how to present them

[Back to the index](../GROUND_UP_GUIDE.md) · Previous: [Part 5](05-comparison-limitations.md) · Next: [Part 7, Q&A bank](07-qa-bank.md)

---

## 6.1 What the demo is

`review-3/demo-ui` is a small web app (React and Vite) that replays logged sessions from our experiments. It does not stream over a network and it does not run dash.js. It reads the recorded timelines of real sessions (bitrate, buffer, latency over time) and drives three video panes side by side from those timelines, so the audience can see what each player did.

Each pane shows:

- A cricket clip whose visible quality follows the recorded bitrate. The app maps the logged bitrate onto four encoded files: Low (about 300 kbps, 240p), Medium (about 900 kbps, 360p), High (about 1500 kbps, 480p) and Ultra (labeled as the 6000 kbps rung; the file is encoded at about 2500 kbps, 720p, because the source footage limits it).
- A large label: "Video quality: N kbps (Low / Medium / High / Ultra)".
- A freeze with the text "Rebuffering…" whenever the recorded buffer is at or below 0.05 s, the same threshold as our metric.
- A 15-second handover clock that marks the slot seconds 12, 27, 42 and 57.

The footage is a real club cricket match, "Nambour v USC – 2021-22 Sunshine Coast Cricket Association Division 3 Round 15" by PattmanSport, under the CC BY 3.0 licence from Wikimedia Commons. Credit the author if you show it.

## 6.2 Pages and families

| Top tab | Families (chips) | What it shows |
| --- | --- | --- |
| Phase 1 / Review I | CUBIC clock | The reproduction: the four ABRs under the paper clock |
| Phase 2 / Review II | BBR clock (canonical), BBR faulty versus fixed | D3, and the D2 trace run against the fixed run |
| Phase 3 / Review III | capacity, clock-nonreg, capacity-4mbit-targets, trace-targets, stall-guard-spots | old CMAB, CMAB+ and L2A-LL in each Review III experiment |
| Algorithm | (none) | A textbook page for CMAB+: notation, rules 1–5, formulas, pseudocode, matching `review-3/ALGORITHM.md` |
| Problems we faced | (none) | The failure ledger from `review-3/PROBLEMS.md` |

In Phase 3, each family has a short explainer panel: "What is this?", "Real-life scenario" and "What should you observe?".

How sessions are picked: `scripts/build-catalog.mjs` walks the Review I–III session trees, picks round 0 (or the lowest round present), computes the same metrics as the report (20% trim, buffer at or below 0.05 s), downsamples timelines to about 2 samples per second, and writes `public/sessions/*.json` and `public/catalog.json`.

One caution about the stall-guard family: the README says that the trace sessions there use stall-guard-on data, while the clock and 4 Mbit/s entries use representative sessions where the guard stays inactive. Since the clock and 4 Mbit/s spot trees are not in the archives, do not present those panes as the spot runs themselves.

## 6.3 How to run it

```bash
cd review-3/demo-ui
npm install
bash scripts/fetch-video.sh   # only if public/video/cricket-*.mp4 are missing (about 1.1 GB)
npm run dev                   # http://localhost:5173 ; also rebuilds the catalog
```

For a static build: `npm run build`, then `npm run preview`.

Controls: the app starts paused. Play starts demo time, the videos and the handover clock. Pause freezes everything, and Play resumes from the same point. Only Reset returns to t = 0.

Before the review, do one dry run on the presentation laptop, with the videos already downloaded and the dev server already started. A network fetch of 1.1 GB during a viva is a risk.

## 6.4 A suggested five-minute demo script

1. Phase 1, CUBIC clock. "This is the paper's emulator. All four players stay near the 3 s target and almost never freeze. CMAB sits a little above the others." Point at the handover clock as it passes 12 and 27.
2. Phase 2, BBR faulty versus fixed. "This is the run that scared us: CMAB freezing about a quarter of the time. It used the trace shaper. The fixed run on the clock shaper looks like Review I." Use the line: "the 7-second number is D2, the 3.3-second number is D3".
3. Phase 3, capacity at 4 Mbit/s. Play the three panes. "Old CMAB keeps asking for 6000 kbps on a 4 Mbit/s link and is frozen most of the time. CMAB+ asks for 1500 kbps and never freezes. L2A-LL does the same as CMAB+, a little closer to the target." Wait for a handover second and point out that old CMAB's label stays at the top rung.
4. Phase 3, trace targets. "On the Starlink ISL trace, CMAB+ freezes much less than old CMAB, but L2A-LL freezes even less, at a much lower quality. We do not beat L2A-LL here."
5. Algorithm tab. Walk through the five rules in one sentence each (Part 3.6).
6. Problems tab, if time allows: the eight trials and the shaper bug.

## 6.5 The artifact

### Code

- Public repository: `github.com/pratham-commits/CMAB_plus`, branch `main`, commit `d60f163`. It is a fork of the authors' repository (`github.com/clarkzjw/mmsys24-starlink-livestreaming`) at commit `dc120de`.
- CMAB+ rules: `dash.js/src/streaming/rules/abr/cmab/cmabPlusPolicy.js`, wired into `CMABAbrController.js` and `CMABRule.js`.
- Unit tests that run without Docker: `experiments/test_cmab_plus_policy.mjs`.
- Each matrix has a batch file (`experiments/batch-*.json`, for example `batch-capacity-decision.json`, `batch-clock-nonregression.json`, `batch-capacity-4mbit-targets.json`, `batch-trace-targets.json`, `batch-stall-guard-spot.json`) and a runner script (`experiments/run-*.sh`).
- The capacity runners check the congestion control, the `tc` qdisc and the rate inside the nginx container before every batch. This is the Review II lesson turned into code.
- In our workspace the fork is at `vendor/mmsys24-starlink-livestreaming`, with a git remote named `pratham` pointing to the public repository.

### Course repository

- `review-2/`: the Review II package (details, shaper root cause, code-level verification notes, audit of the D2 run, figures, scripts, presentation notes).
- `review-ii-bbr-extension/`: the Review II datasets, including D3 (prefix `1017-0606`) and the superseded D2 trace run (prefix `1010-0432`).
- `review-3/`: the Review III record: `ALGORITHM.md`, `TRIALS.md`, `METHOD.md`, `PAPER_CLAIM.md`, `PROBLEMS.md`, `DATA_MANIFEST.md`, `NEXT.md`, the four `analyze_*.py` scripts, results CSVs, figures, retained trial trees, and the demo.
- `report/`: the final report (`paper.tex`, `paper.pdf`), its figures, its result CSVs and the three report scripts.

### Data archives (`review-3/data/archives/`)

From the report's Table 8. The SHA-256 digests were re-checked against `review-3/DATA_MANIFEST.md` before the report was written.

| Archive | Sessions | SHA-256 (first 16 hex digits) |
| --- | ---: | --- |
| `cmab-plus-clock-nonreg-cubic.tar.gz` | 60 | `55716f33b860b4ba` |
| `cmab-plus-clock-nonreg-bbr.tar.gz` | 60 | `1b29c2ac41bde0f3` |
| `cmab-plus-capacity-cubic.tar.gz` | 45 | `0040b3d46a0b202c` |
| `cmab-plus-capacity-bbr.tar.gz` | 45 | `c62c01d2bdf15222` |
| `cmab-plus-capacity-4mbit-targets-cubic.tar.gz` | 60 | `21b29deccba1f3f2` |
| `cmab-plus-capacity-4mbit-targets-bbr.tar.gz` | 60 | `0141ed96b2a28219` |
| `cmab-plus-trace-stallguard-cubic-bbr-20261108.tar.gz` | 120 | `27cdf2a5493e126a` |
| `cmab-plus-cubic-1102-1304.tar.gz` (trial 7) | 160 | `0652cda3862b6759` |

The full digests are in `report/paper.tex` (Table 8) and `review-3/DATA_MANIFEST.md`. To check one: `shasum -a 256 review-3/data/archives/*.tar.gz`.

What a SHA-256 digest is, in plain words: a 64-character fingerprint computed from every byte of a file. Change one byte and the fingerprint changes completely. Publishing it lets anyone confirm that the archive they downloaded is the one we analysed.

### How to rebuild any table

```bash
python3 review-3/analyze_capacity.py               # capacity, needs 90 sessions
python3 review-3/analyze_clock_nonreg.py           # non-regression
python3 review-3/analyze_capacity_4mbit_targets.py # 4 Mbit/s targets
python3 review-3/analyze_trace_targets.py          # trace
python3 report/scripts/review12_tables.py          # Review I/II tables
python3 report/scripts/make_figures.py             # all four report figures
```

## 6.6 How to present the artifact in one minute

"Everything in the report can be rebuilt. The CMAB+ rules are about 300 lines of pure functions with unit tests, switched on by one flag, so the other ABRs are untouched. Each experiment has a batch file, a runner that checks the shaper and congestion control inside the container before it starts, and an analysis script that refuses to run if a session is missing. The raw data are archived with SHA-256 fingerprints. The demo replays those same sessions."

---

[Back to the index](../GROUND_UP_GUIDE.md) · Previous: [Part 5](05-comparison-limitations.md) · Next: [Part 7, Q&A bank](07-qa-bank.md)
