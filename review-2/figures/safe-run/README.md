# Safe run — figures (canonical Review II results)

**What this is:** Final BBR 160×300 s batch — **`SHAPER=clock`**, **`tcp_cc=bbr`**, prefix **`1017-0606`**.

**Use this folder** when showing faculty **final, fair** results vs Review I CUBIC.

## Main comparison (CUBIC Review I vs BBR clock)

| File | Content |
|------|---------|
| `latency_all_abr_*.png` | Live latency, 4 ABRs |
| `bitrate_all_abr_*.png` | Mean bitrate |
| `rebuffer_all_abr_*.png` | Rebuffer sample % |
| `*_target3s_bars.png` | Target 3 s only |

Legend: **TCP CUBIC (Review I)** vs **TCP BBR (clock · 1017-0606)**.

**Headline (CMAB @ 3 s):** ~**3.29 s** latency, **0%** rebuffer vs CUBIC ~**3.19 s**.

## BBR-only paper-style (clock)

Subfolder **`bbr-only-paper-style/`** — Fig 6a/7a/8a style for **BBR clock matrix only**.

**Raw JSON:** `review-ii-bbr-extension/deliverables/bbr-clock-160-deliverable-20261018-0535/figures/emulation-bbr-clock/`.

**Proof meta:** `review-2/meta/nginx-SHAPER.txt` (clock), `nginx-tcp_cc.txt` (bbr).

**Regenerate:**

```bash
python3 review-2/scripts/plot_cubic_vs_bbr_all_abr.py \
  --bbr-root review-ii-bbr-extension/deliverables/bbr-clock-160-deliverable-20261018-0535/figures/emulation-bbr-clock \
  --out-dir review-2/figures/safe-run \
  --bbr-legend "TCP BBR (clock · 1017-0606)" \
  --title-suffix " · SAFE (SHAPER=clock)"
```
