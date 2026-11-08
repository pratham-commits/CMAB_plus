# Review II — professor discussion guide (not a slide deck)

**Your plan:** (1) show **final, correct results** → (2) explain **what failed**, **why**, and **why the final numbers are trustworthy**.

Use this as a **talk track**. Keep **`details.md`** and **`FACULTY_QA.md`** open for deep dives.

---

## Part A — Final results (show this first, ~10 minutes)

### A.0 One-sentence framing (say this before opening anything)

> “Review II reran the same **160 × 300 s** emulation matrix with **TCP BBR** on the sender. After we fixed the testbed, the **fair comparison** to Review I is **BBR with `SHAPER=clock`** versus **Review I CUBIC** — same handover class as our September baseline. Under that, **CMAB is healthy on BBR**, not collapsed; the scary **~7 s / ~28% rebuffer** numbers were from an **earlier misconfigured run** I’ll explain in Part B.”

That sets honesty upfront so he doesn’t think you’re hiding the bad run.

---

### A.1 What you actually delivered (facts only)

| Item | Value | Proof on laptop |
|------|--------|-----------------|
| Matrix | **160 / 160** production runs (300 s) | `review-2/meta/summary_stats.txt` |
| Session prefix | **1017-0606** | Any folder under `emulation-bbr-clock` |
| TCP on sender | **bbr** | `review-2/meta/nginx-tcp_cc.txt` |
| Shaper | **clock** (`tc.py`) | `review-2/meta/nginx-SHAPER.txt` |
| CUBIC baseline | Review I, unchanged | `review 1/.../figures/emulation` |

**Optional live check (30 s):**

```bash
python3 review-2/scripts/verify_cmab_claims.py \
  --label "Review I CUBIC" \
  --root "/Users/prathamshah/BITS/ACN/Project/review 1/mmsys24-starlink-livestreaming/figures/emulation" \
  --label "BBR clock FINAL" \
  --root "review-ii-bbr-extension/deliverables/bbr-clock-160-deliverable-20261018-0535/figures/emulation-bbr-clock"
```

Say: “These numbers are **recomputed from raw JSON**, not from matplotlib — same trim rules as Review I.”

---

### A.2 Headline numbers he will care about (CMAB @ target 3 s, n=10)

| Metric | Review I CUBIC | BBR clock (final) |
|--------|----------------|-------------------|
| Mean live latency | **3.19 s** | **3.29 s** |
| Rebuffer sample ratio | **0%** | **0%** |
| Mean bitrate | **4955 kbps** | **5223 kbps** |
| CMAB arm activity | ~800+ decisions/run (mixed arms) | ~599/run, mixed arms |

**How to interpret in plain language:**

- Switching **CUBIC → BBR** under **fair emulation** does **not** blow up CMAB live latency.
- Difference at 3 s is **~0.1 s** — same QoE class, not a transport catastrophe.
- BBR runs **slightly higher bitrate** on CMAB; that’s plausible (pacing/probing), not automatically “better.”

**Dynamic @ 3 s (shows CC can matter for throughput-based ABR):**

| | CUBIC | BBR clock |
|--|-------|-----------|
| Latency | 3.00 s | 3.12 s |
| Bitrate | 5909 kbps | 5123 kbps |

Say: “**Dynamic** moves more with CC because it **obeys throughput estimates**; **CMAB** under clock is **stable on both**.”

---

### A.3 Show the figures (in this order)

Open folder: **`review-2/figures/safe-run/`** (final results). For the bad run later: **`review-2/figures/faulty-run/`**.

1. **`safe-run/latency_all_abr_zoom.png`** — “All four ABRs, targets 3–6; CUBIC vs BBR **clock**.”
2. **`bitrate_all_abr_zoom.png`** — “**CMAB** and **LoLP** show the most CC spread; **L2A** sits at **6000 kbps** both sides (lines overlap — we fixed plotting so both series show).”
3. **`rebuffer_all_abr_zoom.png`** — “Mostly zero; CUBIC CMAB @ **5 s target** has a **2.5% mean** from **one bad round** (same culture as Review I 5 s outlier), not BBR-specific.”

If he wants one summary slide worth of content: **`latency_target3s_bars.png`** + **`bitrate_target3s_bars.png`**.

---

### A.4 What conclusion you are asking him to accept (Part A)

Use this wording:

1. **Review II extension is complete** for BBR: full matrix, verified CC and shaper, auditable JSON.
2. **Primary scientific result:** Under **Review I–class shaper (`clock`)**, **TCP CC has a small effect on CMAB live QoE** at tight targets; the extension does **not** show “BBR breaks live CMAB” in the fair setup.
3. **Secondary result:** **CMAB is the ABR that interacts most with transport and shaper stress**; L2A/Dynamic/LoLP are mostly flat or self-limiting in this matrix.
4. **Forward work:** **CMAB+** (feasibility clamp + fix handover bootstrap) — see Part C if he asks “so what next?”

---

## Part B — What failed, why, and why the final result is still correct (~15 minutes)

### B.0 Transition sentence

> “The **first** BBR 160-run **did** finish, and it **looked** like BBR destroyed CMAB. We investigated; that matrix is **not** comparable to Review I. I’ll walk through **three layered causes** — shaper mode, nginx/tc bug, and CMAB control path — then show why the **1017-0606 clock rerun** fixes the comparison question.”

---

### B.1 Failure #1 — Wrong shaper for “same as Review I” (biggest confound)

**What happened:** First BBR batch **`emulation-bbr`**, prefix **1010-0432**, default **`SHAPER=trace`** (`tc-trace.py`).

**Symptoms (CMAB @ 3 s, n=10):**

| | BBR trace (failed comparison) | BBR clock (final) |
|--|-------------------------------|-------------------|
| Latency | **7.19 s** | **3.29 s** |
| Rebuffer | **28.3%** | **0%** |
| Bitrate | **5795 kbps** | **5223 kbps** |

**Why it failed logically:**

- Review I used **`clock`**: ~**40 ms** baseline, handover pulses at 12/27/42/57 s.
- **Trace** uses CSV RTT ~**180 ms** + **100% loss** on handover rows — much harsher.
- **CMAB** tries to hold **~5–6 Mbps**; **Dynamic** drops to **~619 kbps** on the same BBR trace run → **same stack, same CC**, only ABR differs → starvation is **not** “BBR alone.”

**Why final result is correct:** We explicitly reran with **`SHAPER=clock`** and recorded it in deliverable meta. **D1 vs D3** is the defensible transport comparison; **D2** is **stress-test / appendix**, not Review I parity.

**Doc:** `review-2/docs/SHAPER_ROOT_CAUSE.md`

---

### B.2 Failure #2 — `docker restart nginx` + broken `tc-trace` init

**What happened:** Batch runner **restarts nginx before every 300 s run**. Old `tc-trace.py` did not tear down/recreate HTB cleanly → **tc crash / stuck qdisc** (sometimes stuck in harsh loss).

**Symptoms:** Even **CUBIC + CMAB** on validation looked dead (~**16 s** latency, ~**28** arm logs, all arm 7) while **Dynamic** still ~4 s — proves **not** “BBR broke CMAB” exclusively.

**Fix:** `tc_del()` + proper HTB root in `runner/tc-trace.py`.

**Why final result is correct:** After fix + **`SHAPER=clock`**, RC7 validation and the **160-run clock** batch show **hundreds of arm logs** and **~3–4 s** CMAB class behavior on **both** CUBIC and BBR in spot checks.

---

### B.3 Failure #3 — CMAB *implementation* amplifies bad paths (not LinTS “theory”)

When path is harsh (trace + BBR), this **code** makes CMAB worse than Dynamic:

| Mechanism | One line | Evidence |
|-----------|----------|----------|
| **RC1** | CMAB uses **STRONG** priority — **no clamp** to safe throughput | CMAB ~5795 kbps vs Dynamic ~619 kbps on **same** BBR trace matrix |
| **RC2** | After each 15 s timeslot, **forces max arm** until \|A\|-1 samples | `arms.json` dominated by arm 7; few decisions when stalling |
| **RC5** | Catch-up **speeds playback** when late while download weak | Fits latency drift in bad runs |

**Why final result is still correct:** Under **clock**, those pathologies **don’t trigger catastrophe** — but they **explain D2** without claiming “contextual bandits don’t work.”

**Deep dive if he opens code:** `review-2/docs/FACULTY_VERIFICATION_CMAB_BBR.md` — lines cited for bootstrap (415–416) and STRONG (CMABRule.js).

---

### B.4 Failure #4 — RC7 (September CUBIC vs October BBR stack date)

**Concern:** Review I image/date ≠ Review II image/date.

**Your answer:**

- We **don’t** pretend a perfect single-day 4-way factorial for every claim.
- We **do** have: (1) **Review I CUBIC** as historical baseline, (2) **October BBR clock 160-run**, (3) RC7 **validation runs** on same VM with **clock** showing CMAB healthy on both CCs.
- **Mechanism claims** (RC1–RC3) come from **code + same-log comparisons** (Dynamic vs CMAB on identical traces), not only from date-matched CUBIC.

---

### B.5 What you should **not** apologize for

- Completing the **first** BBR 160-run — it was **real data**, wrongly interpreted until shaper parity.
- Reporting **7 s / 28%** — it belongs in the story as **“before we understood shaper + control path.”**

---

## Part C — If he asks “what next?” (CMAB+, 2 minutes)

**Not a new ABR** — same LinTS CMAB with three guards:

1. **Clamp** selected arm to feasible \(\hat{T}\) (like Dynamic implicitly does).
2. **Remove max-arm bootstrap** on handover (stop forcing arm 7).
3. **Soften STRONG** when clamped or buffer low.

**Validate with 4–8 runs** on trace stress before any new 160 matrix.

Details: **`details.md` §12**.

---

## Suggested order on your screen

1. Run **`verify_cmab_claims.py`** (CUBIC vs BBR clock) — terminal.
2. Open **`safe-run/latency_all_abr_zoom.png`** + **`safe-run/bitrate_all_abr_zoom.png`**, then **`faulty-run/latency_all_abr_zoom.png`** for contrast.
3. Open **`meta/nginx-SHAPER.txt`** + **`meta/nginx-tcp_cc.txt`** + **`summary_stats.txt`**.
4. **Then** show the **7.19 / 28.3** row (trace) from the same script with third `--root` pointing to `emulation-bbr`.
5. Open **`SHAPER_ROOT_CAUSE.md`** (one page) if he wants failure depth.

---

## Likely pushback — one-line replies

| He says | You say |
|---------|---------|
| “So BBR is fine?” | “Under **clock**, yes for CMAB QoE; under **trace stress**, this **implementation** still misbehaves — that’s why we propose CMAB+.” |
| “Why trust Review I CUBIC?” | “That was the **faculty-accepted** reproduction; we compare BBR **clock** to it and document shaper parity.” |
| “Is the extension a failure?” | “No — we learned **cross-layer sensitivity is conditional**: fair emulation → small CC effect; harsh shaper + CMAB control → large effect.” |
| “Prove BBR was on.” | “Deliverable meta + 160 sessions under BBR compose; re-run `sysctl` pattern from runbook if needed.” |

Full Q&A: **`FACULTY_QA.md`**.

---

## What you are **not** doing in this meeting

- Defending the **trace** matrix as equal to Review I.
- Claiming BBR **improves** Starlink live streaming in general.
- Saying CMAB **theory** is wrong.

---

**End.** Your narrative is: **here are the correct results and proof → here is what went wrong and why those wrong numbers were misleading → here is why the final comparison is methodologically sound.**
