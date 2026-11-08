# Review II — presentation guide (slide-by-slide)

**Assumption:** Audience saw Review I (`review 1/details.md`) or you recap 2 minutes of context.

**Suggested length:** 12–15 slides, ~15–20 minutes + Q&A.

---

## Slide 1 — Title

**Review II: TCP BBR vs CUBIC on the MMSys ’24 LEO live-streaming testbed**

Team names, course, paper citation.

**Say:** “Review I reproduced 160 CUBIC runs. Review II asks: does **sender congestion control** change ABR behavior on the **same** handover cadence?”

---

## Slide 2 — TLDR (four bullets)

1. We ran **160 × 300 s** with **TCP BBR** (canonical: **`SHAPER=clock`**, prefix **1017-0606**).
2. **Fair comparison** to Review I CUBIC: CMAB @ 3 s **~3.2 s latency, ~0% rebuffer** on **both** CCs.
3. Early BBR run (**trace shaper**, 1010-0432) showed **CMAB collapse (~7 s, ~28%)** — diagnosed as **shaper + implementation**, not “BBR magic.”
4. **Next:** **CMAB+** — feasibility clamp + fix handover bootstrap (same LinTS, safer control).

---

## Slide 3 — Review I recap (where we ended)

- 160 runs, TCP **CUBIC**, figures 6a/7a/8a reproduced.
- CMAB wins on latency QoE in paper; we validated emulation.
- **Open question (Review II):** paper assumes classic loss-based TCP; **Starlink/LEO paths often use BBR-class CC** — cross-layer interaction?

**Figure:** One Review I Fig 6a-style panel (CUBIC only) — optional.

---

## Slide 4 — Review II experimental change (one knob)

**Only intentional change:** nginx sender `net.ipv4.tcp_congestion_control = bbr` via `set-tcp-cc.sh` + compose override.

**Unchanged:** 4 ABR × 4 targets × 10 rounds × 300 s, same `batch-emulation.json`, same dash.js CMAB code path.

**Diagram:** Review I stack with “TCP CC” box highlighted: CUBIC → BBR.

---

## Slide 5 — Three datasets (critical honesty slide)

| Label | Shaper | Use in talk |
|-------|--------|-------------|
| Review I CUBIC | clock (Sept) | Baseline |
| BBR **trace** 1010-0432 | trace | **What went wrong** — appendix |
| BBR **clock** 1017-0606 | clock | **Primary BBR results** |

**Say:** “If we only showed the first BBR matrix, we would over-claim. The clock rerun is the fair transport comparison.”

---

## Slide 6 — What broke (timeline)

1. First BBR 160-run completed but CMAB @ 3 s **~7.2 s / 28% rebuffer**.
2. Validation: even **CUBIC** CMAB looked dead on **trace** after nginx restarts → **`tc-trace.py` HTB bug**.
3. **SHAPER=clock** (`tc.py`, ~40 ms + handover pulses) restored **~800+ arm decisions** class behavior.
4. RC7: 4 short validation runs → full **160 BBR clock** rerun.

**Figure:** none — bullet timeline is enough.

---

## Slide 7 — Proof the numbers are real

- **`verify_cmab_claims.py`** — latency, rebuffer %, bitrate from raw JSON.
- **160/160** matrix counts in `meta/summary_stats.txt`.
- **`meta/nginx-SHAPER.txt`** = clock, **`nginx-tcp_cc.txt`** = bbr.
- Comparison plots in `figures/comparison-cubic-vs-bbr-clock/`.

**Live demo (optional):** run verify script in terminal on laptop.

---

## Slide 8 — Results @ target 3 s (headline)

**Table (CMAB + Dynamic):**

| | CUBIC (R1) | BBR clock |
|--|------------|-----------|
| CMAB latency | 3.19 s | 3.29 s |
| CMAB rebuffer | 0% | 0% |
| CMAB bitrate | 4955 kbps | 5223 kbps |
| Dynamic latency | 3.00 s | 3.12 s |
| Dynamic bitrate | 5909 kbps | 5123 kbps |

**Say:** “Transport shift is **small** for healthy clock emulation; **CMAB is not universally broken on BBR**.”

---

## Slide 9 — All ABR comparison figures

Show **`latency_all_abr_zoom.png`** and **`bitrate_all_abr_zoom.png`**.

**Say:** “**CMAB** shows the most CC-sensitive curves; **L2A** pinned at 6000 kbps both CCs; **Dynamic/LoLP** mostly self-limit.”

---

## Slide 10 — Why trace BBR killed CMAB (mechanism, not vibes)

Three code facts (no LinTS blame):

1. **STRONG** CMAB switch — no throughput clamp (RC1).
2. **Max-arm bootstrap** every 15 s slot (RC2).
3. **Trace shaper** ~180 ms + harsh handover loss — CMAB at 6 Mbps starves; Dynamic at ~500 kbps survives.

**Optional figure:** arm histogram — trace BBR arm 7 vs clock BBR diverse arms.

---

## Slide 11 — Claims we make vs do not make

**Make:**

- BBR vs CUBIC under **clock**: similar CMAB live QoE @ 3 s.
- CMAB implementation **interacts badly** with BBR under **trace stress**.
- Other ABRs largely **CC-invariant** in our matrix.

**Do not make:**

- “BBR is better for live streaming.”
- “CMAB theory failed.”
- Compare Review I CUBIC to **trace BBR** without disclaimer.

---

## Slide 12 — CMAB+ (forward work)

**Not a new algorithm** — same LinTS + three guards:

- P1: clamp arm to feasible \(\hat{T}\)
- P2: remove forced max arm on handover
- P3: soften STRONG when clamped / buffer low

**Evaluation:** 4–8 run ablation, then optional trace stress.

See **`details.md` §12** for code locations.

---

## Slide 13 — Team / division (Review II)

| Who | Review II focus |
|-----|-----------------|
| Ved | GCP, compose, 160-run execution, sysctl proof |
| Vidhu | TCP CUBIC vs BBR theory, cross-layer narrative |
| Pratham | Forensics, scripts, plots, CMAB+ spec, docs |

---

## Slide 14 — Q&A buffer

Keep **`FACULTY_QA.md`** open on second screen.

---

## Backup slides

- Full 16-row table (all ABR × targets) from `details.md` §7.
- Old BBR trace CMAB @ 3 s: 7.19 s / 28.3%.
- `SHAPER_ROOT_CAUSE.md` diagram.
- Code snippet: bootstrap lines 415–416.
