# Faulty run — figures (do **not** use for Review I comparison)

**What this is:** First BBR 160×300 s batch — **`SHAPER=trace`**, session prefix **`1010-0432`**.

**Why “faulty”:** Not broken data (160/160 real runs), but **wrong emulation class** vs Review I (`SHAPER=clock`) + CMAB collapse under harsh trace. Use this folder when explaining **what went wrong** to faculty.

## Main comparison (CUBIC Review I vs BBR trace)

| File | Content |
|------|---------|
| `latency_all_abr_*.png` | Live latency, 4 ABRs |
| `bitrate_all_abr_*.png` | Mean bitrate |
| `rebuffer_all_abr_*.png` | Rebuffer sample % |
| `*_target3s_bars.png` | Target 3 s only |

Legend: **TCP CUBIC (Review I)** vs **TCP BBR (trace · 1010-0432)**.

**Headline (CMAB @ 3 s):** ~**7.2 s** latency, ~**28%** rebuffer — see `verify_cmab_claims.py` on `review-ii-bbr-extension/figures/emulation-bbr`.

## Extra (trace BBR only / Dynamic overlay)

| File | Content |
|------|---------|
| `average_*_Emulation.png` | Paper-style Fig 6a/7a/8a for **trace BBR only** |
| `dynamic_*_cubic_vs_bbr.png` | Dynamic only: CUBIC vs BBR trace |

**Raw JSON:** `review-ii-bbr-extension/figures/emulation-bbr/` or `BBR-Review-II-Deliverable/data/emulation-bbr/`.

**Regenerate comparison PNGs:**

```bash
python3 review-2/scripts/plot_cubic_vs_bbr_all_abr.py \
  --bbr-root review-ii-bbr-extension/figures/emulation-bbr \
  --out-dir review-2/figures/faulty-run \
  --bbr-legend "TCP BBR (trace · 1010-0432)" \
  --title-suffix " · FAULTY (SHAPER=trace)"
```
