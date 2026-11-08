# MASTER TECHNICAL REPORT & PRESENTATION GUIDE — REVIEW II

## TCP BBR extension on the MMSys ’24 Starlink live-streaming artifact

**Course:** CS G525 Advanced Computer Networks — First Semester 2026–27  
**Department of Computer Science & Information Systems, BITS Pilani**  
**Instructor-in-Charge:** Dr. Yash Sinha  
**Track:** Track A (Reproduction, Validation & Systems Extension) — Menu Item **A7**  
**Reference Paper:** Jinwei Zhao & Jianping Pan, *Low-Latency Live Video Streaming over a Low-Earth-Orbit Satellite Network with DASH*, ACM MMSys ’24 ([DOI: 10.1145/3625468.3647616](https://doi.org/10.1145/3625468.3647616))

**Team:** Ved Pahune (2026H1030056P), Vidhu Kant Sharma (2026H1030053P), Pratham Shah (2026H1030063P)

**Review I master doc (prerequisite):** `~/BITS/ACN/Project/review 1/details.md`  
**This package root:** `csg525-a7-leo-live/review-2/` (figures, scripts, meta, presentation)

---

# TLDR — read this first (60 seconds)

1. **Review I ended with:** 160 emulation runs, **TCP CUBIC**, paper-scale validation (Figs 6a/7a/8a), forensic 5 s target outlier, and a **planned extension**: rerun the **same matrix** with **TCP BBR** on the HTTPS sender to study **cross-layer** (transport × ABR × LEO handover).

2. **Review II delivered:** A complete **160 × 300 s BBR matrix** on GCP, plus deep forensics when **CMAB looked “catastrophic” on BBR** in an **early run**.

3. **The surprise was not “BBR fixes CMAB.”** Under a **fair shaper (`SHAPER=clock`)**, CMAB @ 3 s target is **healthy on both CUBIC and BBR** (~3.2 s latency, ~0% rebuffer). **BBR vs CUBIC delta is small** (~0.1 s latency, modest bitrate shift).

4. **The disaster (~7.2 s, ~28% rebuffer)** came from **`SHAPER=trace` + nginx/tc restart bugs + CMAB control path** (STRONG switches, max-arm bootstrap) — documented as **RC1–RC3**, not as proof that bandits fail.

5. **Canonical BBR data for claims:** prefix **`1017-0606`**, output **`emulation-bbr-clock`**, **`SHAPER=clock`**, **`tcp_cc=bbr`**, **160/160** sessions.

6. **Next step (planned, not yet coded):** **CMAB+** — same LinTS CMAB with **throughput-feasible clamp**, **fixed handover bootstrap**, **conditional STRONG priority** (see §12).

---

# TABLE OF CONTENTS

1. [Where Review I stopped and what Review II had to do](#1-where-review-i-stopped-and-what-review-ii-had-to-do)
2. [Concepts you must know (Review II additions only)](#2-concepts-you-must-know-review-ii-additions-only)
3. [Chronology: what we did, what failed, how we fixed it](#3-chronology-what-we-did-what-failed-how-we-fixed-it)
4. [Three datasets — never mix them in one claim](#4-three-datasets--never-mix-them-in-one-claim)
5. [Testbed: what changed vs Review I](#5-testbed-what-changed-vs-review-i)
6. [Metric definitions and proof numbers are reproducible](#6-metric-definitions-and-proof-numbers-are-reproducible)
7. [Verified results tables (full matrix)](#7-verified-results-tables-full-matrix)
8. [Interpretation: what the results mean logically](#8-interpretation-what-the-results-mean-logically)
9. [Root-cause analysis RC1–RC7 (faculty-grade)](#9-root-cause-analysis-rc1rc7-faculty-grade)
10. [Claims we are allowed to make vs claims we must not make](#10-claims-we-are-allowed-to-make-vs-claims-we-must-not-make)
11. [Evidence checklist (audit trail)](#11-evidence-checklist-audit-trail)
12. [CMAB+ planned improvements (exact changes)](#12-cmab-planned-improvements-exact-changes)
13. [Presentation flow and division of speaking](#13-presentation-flow-and-division-of-speaking)
14. [File index and reproduction commands](#14-file-index-and-reproduction-commands)
15. [Glossary (Review II terms)](#15-glossary-review-ii-terms)

---

# 1. Where Review I stopped and what Review II had to do

## 1.1 Review I outcome (accepted baseline)

Review I reproduced the MMSys ’24 **emulation campaign**:

- **160 runs** = 4 ABR algorithms × 4 target live latencies (3, 4, 5, 6 s) × 10 random seeds × **300 s** each.
- **TCP congestion control on sender:** Linux default **CUBIC** (loss-based).
- **Traffic shaper:** clock-based **`tc.py`** emulating ~40 ms baseline RTT and handover pulses at **12, 27, 42, 57 s** each minute (15 s cadence).
- **Key validated headline (CMAB, target 3 s, n=10):** mean live latency **≈ 3.19 s**, rebuffer sample ratio **≈ 0%**, mean bitrate **≈ 4955 kbps**, **hundreds to thousands** of CMAB arm decisions per session (`arms.json`).

Review I also documented a **5 s target outlier** (one bad round driving mean rebuffer on CMAB) — headless Chrome / catch-up interaction — and reported it honestly.

## 1.2 The Review II question (what faculty expected)

**Cross-layer extension hypothesis (initial):**

> If the sender uses **TCP BBR** (delay/model-based pacing and probing) instead of **CUBIC**, do the **same four ABR algorithms** — especially **CMAB**, which targets high bitrate and models handover context — behave differently under the **same LEO handover schedule**?

**Operational requirement:** Same `batch-emulation.json`, same durations, same figure style — store under a **new figures subtree** (`emulation-bbr`), prove **`bbr`** active, compare to Review I CUBIC.

## 1.3 What we actually learned (mature conclusion)

The extension turned into **two sub-questions**:

1. **Transport effect under fair emulation:** With **`SHAPER=clock`**, does BBR materially change live QoE vs Review I CUBIC?  
   **Answer:** For **CMAB @ 3 s**, **no large effect** — both are good.

2. **Why did the first BBR matrix show CMAB “death”?**  
   **Answer:** **Wrong shaper mode for Review I parity (`trace`)**, **tc restart bug**, plus **CMAB implementation control path** that ignores throughput feasibility — **especially punishing under BBR + harsh trace handovers**.

Review II is therefore **both** a transport comparison **and** a **systems forensics** contribution.

---

# 2. Concepts you must know (Review II additions only)

If you read Review I §2, skip to **2.3**.

## 2.1 TCP CUBIC (Review I default)

**Loss-based.** Increases sending rate until packet loss signals congestion, then multiplicative decrease. Segment download times under handover loss/spikes can drop sharply; ABR \(\hat{T}\) (throughput estimate) reacts.

## 2.2 TCP BBR (Review II sender change)

**Model-based (delay/bandwidth).** Maintains a model of bottleneck bandwidth and min RTT; **paces** packets and **probes** periodically. Per-segment throughput seen by the player can be **inflated during probes** or **depressed during drain phases** — different **autocorrelation** than CUBIC.

**Important:** BBR is **not “faster” or “slower”** universally; it interacts with **ABR’s estimate \(\hat{T}\)** and **how aggressively** an algorithm picks bitrate.

## 2.3 Two shaper modes (critical for Review II)

| Env `SHAPER` | Process | Typical baseline delay | Handover behavior | Review I parity? |
|--------------|---------|------------------------|-------------------|------------------|
| **`clock`** | `runner/tc.py` | ~**40 ms** | Pulses at 12/27/42/57 s (~1% loss in clock mode) | **Yes — match this** |
| **`trace`** | `runner/tc-trace.py` | ~**180 ms** from CSV | **100% loss** on trace zero RTT rows | **Stress test / not Sept baseline** |

Using **`trace`** for “compare to Review I CUBIC” **without saying so** is a **methodological error** we corrected.

## 2.4 Why CMAB is special among the four ABRs

- Targets **high ladder rungs** (up to ~6000 kbps) when context looks favorable.
- Uses **`SwitchRequest.PRIORITY.STRONG`** — overrides conservative throughput rules.
- On each **15 s Starlink timeslot**, **forces max arm** for first \(|A|-1\) decisions before LinTS runs (**bootstrap**).

**Dynamic / LoLP / L2A** generally **respect buffer and/or throughput** more directly → **less CC-sensitive** in our data (L2A often **pins max ladder** on both CCs).

---

# 3. Chronology: what we did, what failed, how we fixed it

| Phase | When (approx) | What we ran | What we saw | Verdict |
|-------|---------------|-------------|-------------|---------|
| **R2-A** | Oct 10–11 | **160 BBR**, `figures/emulation-bbr`, prefix **1010-0432**, **`SHAPER=trace`** (default trace path) | CMAB @ 3 s: **~7.19 s**, **~28% rebuffer**, **~5795 kbps**; Dynamic @ 3 s: **~4.13 s**, **~619 kbps** | Matrix complete but **not fair vs Review I**; CMAB looks broken |
| **R2-B** | Oct 16–17 | Validation on **patched** stack, still trace at first | **CUBIC** CMAB also bad (~16 s, ~28 arms, all arm 7) while Dynamic OK | **Not a BBR-only story** — shaper/nginx broken |
| **Fix-1** | Oct 17 | Patch `tc-trace.py`: HTB root, `tc_del()`, recovery on restart | Shaper survives **`docker restart nginx`** between batch jobs | Stops stuck 100% loss / crash loop |
| **Fix-2** | Oct 17 | Set **`SHAPER=clock`**, rebuild nginx, RC7 validation runs | CMAB @ CUBIC & BBR **~3–4 s** class, **many arm logs** | **Review I parity path found** |
| **R2-C** | Oct 17–18 | **160 BBR clock**, `emulation-bbr-clock`, prefix **1017-0606** | CMAB @ 3 s BBR: **~3.29 s**, **0% rebuffer**, **~5223 kbps**, **~599 arm logs/run** | **Canonical Review II BBR dataset** |
| **Plots** | Oct 18 | `plot_cubic_vs_bbr_all_abr.py` | CMAB shows CC spread; L2A overlap at 6000 kbps | Fixed overlap plotting (dodge + dashed CUBIC) |

**GCP VM:** `instance-20260929-210923` (asia-south1-c), repo clone `~/mmsys24-starlink-livestreaming`, long runs in **tmux**.

---

# 4. Three datasets — never mix them in one claim

| ID | TCP CC | Shaper | Path (this repo) | Session prefix | Use |
|----|--------|--------|------------------|----------------|-----|
| **D1** | CUBIC | clock | Review I: `review 1/.../figures/emulation` | 0929-1424 | **CUBIC baseline** |
| **D2** | BBR | trace | `review-ii-bbr-extension/figures/emulation-bbr` | 1010-0432 | **Failure analysis / appendix** |
| **D3** | BBR | clock | `review-ii-bbr-extension/deliverables/.../figures/emulation-bbr-clock` | 1017-0606 | **Primary BBR results** |

**Faculty one-liner:** “The 7 second CMAB number is **D2**; the 3.3 second BBR number is **D3**; Review I is **D1**.”

---

# 5. Testbed: what changed vs Review I

## 5.1 Intentional changes (BBR extension)

- `shaper/set-tcp-cc.sh` + `entrypoint.sh` → `net.ipv4.tcp_congestion_control=bbr` in nginx container.
- Compose override: `docker-compose-emulation-bbr.yaml`, env **`EMULATION_FIGURES_SUBDIR=emulation-bbr-clock`** (final rerun).
- **`TCP_CONGESTION_CONTROL=bbr`** recorded in deliverable meta.

## 5.2 Unintentional / environmental differences (documented)

- **Docker image rebuild** after BBR patches vs Review I possible Hub pull — **RC7**.
- **`SHAPER` env** differed between early BBR (trace) and Review I (clock) until we fixed it.

## 5.3 Unchanged

- `dash.js` v4.7.4 fork with **CMAB** Pyodide LinTS, same ladder, same batch JSON structure, Selenium Chromium player, stats JSON pipeline, 300 s duration, variable bitrate ladder.

---

# 6. Metric definitions and proof numbers are reproducible

All aggregated numbers in this document come from **`review-2/scripts/verify_cmab_claims.py`** (same logic as audit/plot scripts):

| Metric | Source file | Rule |
|--------|-------------|------|
| **Mean live latency (s)** | `playback_latency.json` | Mean of values; **drop first 20%** of time-ordered samples (`_trim`) |
| **Rebuffer sample ratio (%)** | `buffer.json` | Fraction of samples (after trim) with buffer level **≤ 0.05 s** × 100 |
| **Mean bitrate (kbps)** | `bitrates.json` | Mean of **positive** bitrates after trim |
| **Arm histogram** | `arms.json` | Count of selected arm indices per session, summed over n=10 |

**Session filter:** regex requires **`duration-300`**; 60 s smoke runs excluded.

**Recompute yourself:**

```bash
python3 review-2/scripts/verify_cmab_claims.py \
  --label "Review I CUBIC" \
  --root "/Users/prathamshah/BITS/ACN/Project/review 1/mmsys24-starlink-livestreaming/figures/emulation" \
  --label "BBR clock" \
  --root "review-ii-bbr-extension/deliverables/bbr-clock-160-deliverable-20261018-0535/figures/emulation-bbr-clock"
```

**Logical sanity checks:**

- Latency should track target loosely (3 s target → ~3 s mean if algorithm succeeds).
- L2A often **saturates ladder** → ~6000 kbps both CCs.
- If `arms.json` has **tens** of entries while Review I has **hundreds**, the player was **stall-bound** (CMAB not invoked) — red flag we used in forensics.

---

# 7. Verified results tables (full matrix)

**D1 — Review I CUBIC vs D3 — BBR clock** (n=10 per cell, duration 300 s).  
Generated Oct 18, 2026 from raw JSON.

## 7.1 CMAB

| Target (s) | CUBIC latency | BBR latency | CUBIC rebuf % | BBR rebuf % | CUBIC kbps | BBR kbps |
|------------|---------------|-------------|---------------|-------------|------------|----------|
| 3 | 3.187 | 3.293 | 0.00 | 0.00 | 4955 | 5223 |
| 4 | 4.203 | 4.207 | 0.00 | 0.00 | 4989 | 5167 |
| 5 | 6.048 | 5.211 | **2.52** | 0.00 | 4951 | 5165 |
| 6 | 6.244 | 6.227 | 0.00 | 0.00 | 5021 | 5205 |

**Note on 5 s CUBIC rebuffer:** one round with heavy stall samples; see Review I 5 s outlier culture — here it appears on **CUBIC**, not BBR clock.

## 7.2 L2A

| Target | CUBIC lat | BBR lat | CUBIC kbps | BBR kbps |
|--------|-----------|---------|------------|----------|
| 3–6 | ~3.0–6.0 | ~3.1–6.0 | **6000** | **6000** |

## 7.3 LoLP

| Target | CUBIC lat | BBR lat | CUBIC kbps | BBR kbps |
|--------|-----------|---------|------------|----------|
| 3 | 3.083 | 3.137 | 4938 | 5454 |
| 4 | 4.067 | 4.075 | 4902 | 4974 |
| 5 | 5.079 | 5.087 | 4900 | 4906 |
| 6 | 6.105 | 6.105 | 4900 | 4900 |

## 7.4 Dynamic

| Target | CUBIC lat | BBR lat | CUBIC kbps | BBR kbps |
|--------|-----------|---------|------------|----------|
| 3 | 3.002 | 3.124 | 5909 | 5123 |
| 4 | 4.004 | 4.012 | 5910 | 5679 |
| 5 | 5.001 | 5.000 | 5640 | 5824 |
| 6 | 6.009 | 6.002 | 5600 | 5744 |

## 7.5 D2 appendix — BBR trace CMAB @ 3 s (why we reran)

| Metric | D2 BBR trace | D3 BBR clock | D1 CUBIC |
|--------|--------------|--------------|----------|
| Mean latency | **7.186 s** | 3.293 s | 3.187 s |
| Rebuffer % | **28.32** | 0.00 | 0.00 |
| Mean kbps | 5795 | 5223 | 4955 |
| Arm hist (0–7) | heavy **7** (1018 counts) | mixed, 2283 on arm 7 | mixed, 3272 on arm 7 |

**Figures:** `review-2/figures/comparison-cubic-vs-bbr-clock/*.png` (D1 vs D3 only).

---

# 8. Interpretation: what the results mean logically

## 8.1 Under fair clock emulation (D1 vs D3)

- **CMAB live QoE is in the same ballpark** for CUBIC and BBR at tight targets — **transport is not the dominant knob** once emulation matches Review I.
- **Bitrate:** BBR clock runs **slightly higher** kbps on CMAB/LoLP at some targets — consistent with BBR probing/pacing, not necessarily better QoE (latency within ~0.1–0.2 s at 3 s).
- **Dynamic** bitrates **differ** more visibly — Dynamic **uses \(\hat{T}\)**; CC changes \(\hat{T}\) statistics.

## 8.2 Why only CMAB “cared” in the first BBR narrative

On **D2 (trace + BBR)**:

- **Trace** starves high-bitrate flows (180 ms + loss).
- **CMAB** keeps requesting **high rungs** (STRONG + bootstrap) → buffer drain → stalls → **few LinTS calls**.
- **Dynamic** collapses to **~619 kbps** → survives.

So the **first** story “BBR breaks CMAB but not Dynamic” is **true for D2** but **misleading** if presented as universal — **D3** shows CMAB healthy on BBR when shaper matches Review I class.

## 8.3 L2A and overlapping plots

Both CCs max the ladder → **identical means** → plots looked like “missing CUBIC line”; fixed by x-offset + dashed red series + footnote.

## 8.4 What Review II adds to the paper

The paper’s emulation figures are **CUBIC-era**. We provide:

1. **First BBR rerun** of the same matrix (canonical D3).
2. **Explanation** of when BBR **would** hurt this **specific CMAB implementation** (trace stress + RC1–RC3).
3. A **concrete patch plan (CMAB+)** aligned with code-level root causes.

---

# 9. Root-cause analysis RC1–RC7 (faculty-grade)

Full math and code line citations: **`review-2/docs/FACULTY_VERIFICATION_CMAB_BBR.md`**.

| ID | Mechanism | Status |
|----|-----------|--------|
| **RC1** | CMAB **STRONG** switch, **no** clamp against \(\hat{T}\) | **Proven** — explains high BBR bitrate vs Dynamic |
| **RC2** | **Max-arm bootstrap** each 15 s timeslot | **Proven** — arm 7 spikes |
| **RC3** | Reward: empty P.1203 stalling; weak rebuffer term | **Proven** — learning decoupled from stalls |
| **RC4** | BBR inflates segment throughput vs sustainable rate | **Hypothesis (strong)** — amplifier |
| **RC5** | Catch-up speeds playback when late | **Proven** — stability amplifier |
| **RC6** | (Reserved / batch confounds) | Documented in faculty doc |
| **RC7** | Sept CUBIC vs Oct BBR different stack dates | **Mitigated** via clock shaper + RC7 validation + D3 |

**Verdict for examiner:** Measured D2 catastrophe is **expected** from **control analysis + shaper class**, not refutation of contextual bandits.

---

# 10. Claims we are allowed to make vs claims we must not make

## Allowed

- Completed **160-run BBR** matrix with verified **`bbr`** and (**for D3**) **`SHAPER=clock`**.
- Under **clock**, **CMAB @ 3 s** on BBR is **operationally similar** to Review I CUBIC (latency/rebuffer).
- **CMAB implementation** has identifiable bugs/design hazards (RC1–RC3) that **interact with BBR and trace shaper**.
- **Dynamic** down-shifts on harsh paths; **CMAB** does not — **same code, same logs**.

## Not allowed (without qualification)

- “BBR improves live streaming for Starlink.”
- “CMAB is theoretically wrong.”
- Equating **D2** to Review I baseline without **trace vs clock** disclaimer.
- “We reproduced paper Fig 6 with BBR” — paper plots are **CUBIC**; we **extend**, not replicate identically.

---

# 11. Evidence checklist (audit trail)

- [ ] **160/160** counts — `review-2/meta/summary_stats.txt`
- [ ] **SHAPER=clock** — `review-2/meta/nginx-SHAPER.txt`
- [ ] **tcp_cc=bbr** — `review-2/meta/nginx-tcp_cc.txt`
- [ ] **Git commit** at run — `review-2/meta/git-commit.txt`
- [ ] **Independent recompute** — `verify_cmab_claims.py`
- [ ] **Comparison plots** — `review-2/figures/comparison-cubic-vs-bbr-clock/`
- [ ] **Trace run audit** — `review-2/audit/AUDIT_REPORT_BBR_TRACE_1010.md`
- [ ] **Shaper fix narrative** — `review-2/docs/SHAPER_ROOT_CAUSE.md`
- [ ] **Deep mechanism** — `review-2/docs/FACULTY_VERIFICATION_CMAB_BBR.md`
- [ ] **Deliverable tarball** — `~/Downloads/bbr-clock-160-deliverable-20261018-0535.tar.gz`

---

# 12. CMAB+ planned improvements (exact changes)

**CMAB+** = **same algorithm** (LinTS, contexts, timeslots, reward structure) + **safety layer** so live control respects network reality — especially under **BBR** and **trace stress**.

We are **not** proposing a fifth ABR name for the paper competition; we **harden abrCMAB**.

## 12.1 Design principles

1. **Feasibility before learning** — no bandit arm above what \(\hat{T}\) can sustain.
2. **Do not force max bitrate on handover** — exploration should not mean “always arm 7.”
3. **Do not override safety with STRONG** when clamped or buffer-critical.
4. **Optional later:** fix reward stall signal (RC3) and add latency to features — only after Tier 1 works.

## 12.2 P1 — Throughput feasibility clamp (RC1 / experiment E5)

**Problem:** `CMABRule` sets quality from LinTS/bootstrap then **`PRIORITY.STRONG`**. `ABRRulesCollection` picks STRONG without `min(quality, throughputQuality)`.

**Change:**

1. Compute **`safeThroughputKbps = getSafeAverageThroughput(...)`** (already available in rule).
2. Map to **`maxFeasibleArm`** = largest arm with `bitrateList[i].bandwidth/1000 <= kappa * safeThroughputKbps` (kappa = **0.9**, matching `bandwidthSafetyFactor`).
3. **`selectedArm = min(linTSArm, maxFeasibleArm)`** before returning quality.

**Why it makes sense:** Every other sane ABR implicitly solves **admission control**; CMAB currently **skips** it. Under BBR, \(\hat{T}\) jitter makes **uncapped STRONG** dangerous — Dynamic’s 619 kbps vs CMAB 5795 kbps on D2 is the smoking gun.

**Files:** `dash.js/src/streaming/rules/abr/cmab/CMABAbrController.js` (return path), possibly `CMABRule.js`.

## 12.3 P2 — Fix max-arm bootstrap (RC2 / experiment E2)

**Problem (current code):**

```javascript
if (_selectedArmsArray.length < cmabArms.length - 1) {
    selectedArm = cmabArms.length - 1  // ALWAYS max arm
} else {
    selectedArm = pyodide.runPython(_py_mabwiser_select_arm);
}
```

**Change options (pick one for v1):**

- **A (recommended):** Always run LinTS (remove if-block).
- **B:** Bootstrap **lowest** arm or **throughput-matched** arm once per slot.
- **C:** Round-robin one sample per arm without biasing to max.

**Why it makes sense:** Paper motivation for timeslot reset is **non-stationarity across handovers**, not “always request 6 Mbps for 105 seconds.” Forcing max mimics **worst-case cross-layer coupling** with BBR probe/handover loss.

**File:** `CMABAbrController.js` lines 414–419.

## 12.4 P3 — Conditional STRONG priority (RC1 / experiment E3)

**Problem:** STRONG always wins over throughput rules.

**Change:**

- If **`selectedArm` was clamped** in P1 **or** buffer level \< **B_min** (e.g. 0.3 s) **or** within **T_handover** seconds after timeslot reset → set **`PRIORITY.DEFAULT`**.
- Else keep STRONG for parity with original behavior when safe.

**Why it makes sense:** STRONG is an **implementation choice**, not part of LinTS math. Softening it when unsafe preserves learning when healthy, allows **throughput rules to veto** suicide switches.

**File:** `CMABRule.js` ~195.

## 12.5 P4 — Catch-up gating (RC5, Tier 2)

**Problem:** `_calculateNewPlaybackRateCMAB` increases playback speed when \(L > L_{\mathrm{target}}\), draining buffer while download is weak.

**Change:** Disable or cap catch-up multiplier when buffer \< threshold, after handover window, or when current media bitrate \> \(\kappa \hat{T}\).

**File:** `CatchupController.js` CMAB path.

## 12.6 P5 — Reward / P.1203 stalling (RC3, Tier 2)

**Problem:** ITU JSON uses `'stalling': []` while stalls happen — learning signal weak.

**Change:** Populate stalling intervals from `rebufferingEvents`; optional extra penalty term in `calculateReward`.

**File:** `CMABAbrController.js` reward + ITU builder.

## 12.7 P6 — Add live latency to LinTS context (Tier 2 / research)

**Problem:** \(L_{\mathrm{current}}\) logged but **excluded** from LinTS feature vector.

**Change:** Extend Pyodide feature scaler to include normalized \((L - L_{\mathrm{target}})\).

**Note:** Document as **extension beyond paper-identical code**.

## 12.8 CMAB+ v1 bundle (what we will implement first)

**Ship:** **P1 + P2 + P3** behind env flag `CMAB_HARDENED=1` or dash.js setting.

## 12.9 Evaluation plan (before another 160-run)

| Step | Runs | Pass criteria |
|------|------|---------------|
| Ablation baseline | Original CMAB, BBR, trace, 3 s, n=3 | Reproduce high rebuffer OR confirm clock OK |
| CMAB+ v1 | Same | Trace BBR: mean latency **↓ >30%**, rebuffer **↓ >50%** vs baseline; clock: within **~0.2 s** of D3 CMAB |
| Factorial spot | CUBIC/BBR × CMAB/CMAB+ × clock, 3 s, n=5 | Shows which patch matters (E2/E5 style) |
| Optional full matrix | 160 CMAB+ BBR clock | Only if faculty requires figure parity |

---

# 13. Presentation flow and division of speaking

See **`presentation/PRESENTATION_GUIDE.md`** (slide-by-slide) and **`presentation/FACULTY_QA.md`** (examiner questions).

**Suggested split:**

- **Ved:** Slides 1–5 (motivation, one-knob change, three datasets).
- **Vidhu:** Slides 6–10 (TCP BBR vs CUBIC theory, mechanism RC1–RC3, trace vs clock).
- **Pratham:** Slides 11–14 (results tables, plots, CMAB+, evidence checklist).

---

# 14. File index and reproduction commands

| Item | Location |
|------|----------|
| This master doc | `review-2/details.md` |
| Package README | `review-2/README.md` |
| Plots | `review-2/figures/comparison-cubic-vs-bbr-clock/` |
| Scripts | `review-2/scripts/` |
| Full BBR JSON | `review-ii-bbr-extension/deliverables/bbr-clock-160-deliverable-20261018-0535/figures/emulation-bbr-clock/` |
| Review I JSON | `~/BITS/ACN/Project/review 1/mmsys24-starlink-livestreaming/figures/emulation/` |
| Code vendor tree | `csg525-a7-leo-live/vendor/mmsys24-starlink-livestreaming/` |
| VM run script | `review-ii-bbr-extension/experiments/run-bbr-160-clock-gcp.sh` |

**Regenerate plots:**

```bash
python3 review-2/scripts/plot_cubic_vs_bbr_all_abr.py \
  --out-dir review-2/figures/comparison-cubic-vs-bbr-clock
```

---

# 15. Glossary (Review II terms)

| Term | Meaning |
|------|---------|
| **BBR** | Bottleneck Bandwidth and RTT — TCP congestion control used on sender in Review II |
| **CUBIC** | Default Linux loss-based CC — Review I sender |
| **D1 / D2 / D3** | Our three dataset IDs (CUBIC clock, BBR trace, BBR clock) |
| **\(\hat{T}\)** | Player throughput estimate (`getSafeAverageThroughput`) |
| **STRONG** | dash.js switch priority — CMAB overrides other ABR rules |
| **Bootstrap (RC2)** | Forced max arm before LinTS runs each timeslot |
| **CMAB+** | Hardened CMAB (P1–P3) — same LinTS, added guards |
| **RC1–RC7** | Root-cause IDs in faculty verification doc |
| **SHAPER=clock / trace** | Which tc emulator runs in nginx container |

---

**End of Review II master document.** For slide timing and hostile Q&A, open **`presentation/`** next. For code-level proofs, open **`docs/FACULTY_VERIFICATION_CMAB_BBR.md`**.
