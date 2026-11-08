# Review II — TCP BBR extension (complete package)

**Course:** CS G525 — Track A7 (MMSys ’24 Starlink live streaming)  
**Extension:** Same 160-run emulation matrix as Review I, with **TCP BBR** on the sender; **fair comparison** to Review I **TCP CUBIC** after shaper parity (`SHAPER=clock`).

---

## Start here

| Document | Purpose |
|----------|---------|
| **[`details.md`](details.md)** | **Master guide** — TLDR, timeline, failures/fixes, verified results, proofs, claims, CMAB+, presentation script, faculty Q&A |
| [`docs/FACULTY_VERIFICATION_CMAB_BBR.md`](docs/FACULTY_VERIFICATION_CMAB_BBR.md) | Deep RC1–RC7 mechanism + code citations |
| [`docs/SHAPER_ROOT_CAUSE.md`](docs/SHAPER_ROOT_CAUSE.md) | Shaper/nginx bugs and `clock` vs `trace` |
| [`presentation/PRESENTATION_GUIDE.md`](presentation/PRESENTATION_GUIDE.md) | Slide-by-slide Review II only |
| [`presentation/FACULTY_QA.md`](presentation/FACULTY_QA.md) | Hard questions + short answers |

---

## Directory layout

```text
review-2/
├── README.md                 ← you are here
├── details.md                ← read this for defense / presentation
├── figures/
│   ├── safe-run/          # Canonical: CUBIC vs BBR clock (1017-0606) + BBR-only figs
│   └── faulty-run/        # First BBR trace run (1010-0432) — explain failure only
├── docs/                     # technical appendices (copied from repo)
├── scripts/                  # verify_cmab_claims.py, plot_cubic_vs_bbr_all_abr.py, …
├── meta/                     # nginx SHAPER=bbr, git commit, matrix counts (clock 160-run)
├── deliverables/             # README for canonical tarball
├── audit/                    # audit report for **superseded** trace BBR run (1010-0432)
├── data/                     # pointers to full per-run JSON (not duplicated — too large)
└── presentation/
```

---

## Canonical data locations (full JSON)

| Dataset | Role | Path |
|---------|------|------|
| **Review I CUBIC baseline** | Faculty-accepted reproduction | `~/BITS/ACN/Project/review 1/mmsys24-starlink-livestreaming/figures/emulation` |
| **Review II BBR (canonical)** | **Use for all CUBIC vs BBR claims** | `csg525-a7-leo-live/review-ii-bbr-extension/deliverables/bbr-clock-160-deliverable-20261018-0535/figures/emulation-bbr-clock` |
| **Review II BBR (superseded)** | Trace shaper; CMAB collapse — **appendix only** | `csg525-a7-leo-live/review-ii-bbr-extension/figures/emulation-bbr` |

Session ID prefix: **1017-0606** (clock), **1010-0432** (trace, old).

Tarball (Mac): `~/Downloads/bbr-clock-160-deliverable-20261018-0535.tar.gz`

---

## Reproduce headline numbers in 30 seconds

```bash
cd /Users/prathamshah/Projects/csg525-a7-leo-live
python3 review-2/scripts/verify_cmab_claims.py \
  --label "Review I CUBIC" \
  --root "/Users/prathamshah/BITS/ACN/Project/review 1/mmsys24-starlink-livestreaming/figures/emulation" \
  --label "BBR clock" \
  --root "review-ii-bbr-extension/deliverables/bbr-clock-160-deliverable-20261018-0535/figures/emulation-bbr-clock"
```

Regenerate plots: see `figures/safe-run/README.md` and `figures/faulty-run/README.md`.

---

## Review I pointer

Foundations, 160-run CUBIC reproduction, 5 s outlier forensics, and Review II *motivation* live in:

`~/BITS/ACN/Project/review 1/details.md`

This package assumes that work is accepted and focuses on **everything new in Review II**.
