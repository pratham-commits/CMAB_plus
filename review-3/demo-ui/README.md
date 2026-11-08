# CMAB+ demo UI

Interactive side-by-side ABR replay for Review I–III. Real session timelines drive
buffer stalls and bitrate rungs; a 15 s LEO handover clock matches paper slots
`{12, 27, 42, 57}`.

## Run

```bash
cd review-3/demo-ui
npm install
# If public/video/cricket-*.mp4 are missing (~1.1 GB total):
bash scripts/fetch-video.sh
npm run catalog   # scan session trees → public/catalog.json + public/sessions/
npm run dev       # http://localhost:5173
```

`npm run dev` / `npm run build` also regenerate the catalog via `predev` /
`prebuild`.

Production static build:

```bash
npm run build
npm run preview
```

## Top navigation

- **Phase 1 / Review I**, **Phase 2 / Review II**, **Phase 3 / Review III** — experiment
  replay (family chips, play/pause, handover timer, three player panes).
- **Algorithm** — dedicated textbook page for CMAB+ (rules 1–5, notation, KaTeX
  formulas, pseudocode). Hides the experiment player controls. Content mirrors
  `review-3/ALGORITHM.md`.

### Phase 3 explainers

Under Phase 3, each family chip shows a short panel: *What is this?*, *Real-life
scenario*, and *What should you observe?* (old CMAB / CMAB+ / L2A). Families:
capacity, clock-nonreg, capacity-4mbit-targets, trace-targets, stall-guard-spots.

## Play / pause / reset

- The app **starts paused**. Demo time, videos, and the handover countdown do
  not advance until you press **Play**.
- **Pause** freezes everything at the current demo time (videos hold the current
  frame; timer freezes). Pressing **Play** again **resumes from the same
  position** — it does not restart.
- **Reset** is the only control that jumps back to `t = 0` (and stops playback).

## Quality / resolution shifting

Each pane maps the timeline sample bitrate onto a ladder file:

| Rung | File | Encode target |
| --- | --- | --- |
| Low | `video/cricket-300.mp4` | ~300 kbps · 240p |
| Medium | `video/cricket-900.mp4` | ~900 kbps · 360p |
| High | `video/cricket-1500.mp4` | ~1500 kbps · 480p |
| Ultra | `video/cricket-6000.mp4` | ~2500 kbps · 720p (source-limited; labeled as the 6000 kbps rung) |

A large on-video label shows `Video quality: N kbps (Low|Medium|High|Ultra)`.
When `buffer ≤ 0.05 s` the pane freezes and shows **Rebuffering…** (unchanged).

## Cricket video (license)

Real cricket match footage (not a synthetic pitch loop):

- **Title:** Nambour v USC – 2021-22 Sunshine Coast Cricket Association Division 3 Round 15
- **Author:** PattmanSport
- **License:** [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/)
- **Commons:** https://commons.wikimedia.org/wiki/File:Nambour_v_USC_%E2%80%93_2021-22_Sunshine_Coast_Cricket_Association_Division_3_Round_15.webm
- **Source duration:** 46 min 40 s (360p Commons transcode · 130 MB)
- **Demo encodes:** first **30 minutes** cut into the ladder above (see `public/video/SOURCE.txt`)

Attribution on reuse: *PattmanSport* (CC BY 3.0).

## Catalog regeneration

`scripts/build-catalog.mjs` walks Review I–III session trees, picks round 0 (else
lowest), computes paper metrics (trim first 20%, rebuffer = buffer ≤ 0.05 s),
downsamples timelines to ~2 Hz, and writes `public/sessions/*.json`.

## Old CMAB vs CMAB+

The section under the players summarizes the paper baseline vs the four hardened
rules (feasible probe, throughput clamp, step-down, switch priority) plus stall
guard — wording aligned with `review-3/ALGORITHM.md`. Highlighted lines are the
CMAB+ additions/changes.

## Stall-guard spots

The **Stall-guard spot checks** family covers clock / 4 Mbit / trace × CUBIC+BBR.
Trace uses stall-guard-on data; clock and 4 Mbit use representative sessions
where the guard stays inactive.
