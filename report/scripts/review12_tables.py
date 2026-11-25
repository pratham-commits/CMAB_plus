#!/usr/bin/env python3
"""Recompute Review I (D1) / Review II (D2, D3) aggregates for the report.

Uses the same metric functions as review-2/scripts/verify_cmab_claims.py:
20% time-order trim, rebuffer = buffer samples <= 0.05 s, positive bitrates.
Writes report/results/review12-aggregate.csv and prints a table.
"""

from __future__ import annotations

import csv
import statistics
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "review-2" / "scripts"))
import verify_cmab_claims as v  # noqa: E402

ROOTS = {
    "D1-CUBIC-clock": Path.home()
    / "BITS/ACN/Project/review 1/mmsys24-starlink-livestreaming/figures/emulation",
    "D2-BBR-trace": REPO / "review-ii-bbr-extension/figures/emulation-bbr",
    "D3-BBR-clock": REPO
    / "review-ii-bbr-extension/deliverables/bbr-clock-160-deliverable-20261018-0535/figures/emulation-bbr-clock",
}
ABRS = ["abrDynamic", "abrL2A", "abrLoLP", "abrCMAB"]
T95 = {2: 12.706, 3: 4.303, 4: 3.182, 5: 2.776, 6: 2.571, 7: 2.447, 8: 2.365, 9: 2.306, 10: 2.262}


def ci(vals):
    n = len(vals)
    if n < 2:
        return 0.0
    return T95[n] * statistics.stdev(vals) / n**0.5


def main() -> int:
    out = REPO / "report" / "results" / "review12-aggregate.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for label, root in ROOTS.items():
        if not root.is_dir():
            print(f"missing {label}: {root}", file=sys.stderr)
            continue
        for abr in ABRS:
            for target in (3, 4, 5, 6):
                tdir = root / f"target-{target}s"
                lat, reb, br = [], [], []
                if tdir.is_dir():
                    for s in sorted(tdir.iterdir()):
                        m = v.SESSION_RE.match(s.name)
                        if not m or m.group(1) != abr or int(m.group(4)) != 300:
                            continue
                        lat.append(v.mean_live_latency(s))
                        reb.append(v.rebuffer_sample_ratio_pct(s))
                        br.append(v.mean_bitrate_kbps(s))
                if not lat:
                    continue
                rows.append(
                    dict(
                        dataset=label, abr=abr, target_s=target, n=len(lat),
                        latency_s=round(statistics.mean(lat), 3), latency_ci95=round(ci(lat), 3),
                        rebuffer_pct=round(statistics.mean(reb), 2), rebuffer_ci95=round(ci(reb), 2),
                        bitrate_kbps=round(statistics.mean(br)), bitrate_ci95=round(ci(br)),
                    )
                )
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        print(r)

    # Per-session view of the Review I CMAB 5 s cell (one outlier round).
    tdir = ROOTS["D1-CUBIC-clock"] / "target-5s"
    per = []
    for s in sorted(tdir.iterdir()) if tdir.is_dir() else []:
        m = v.SESSION_RE.match(s.name)
        if m and m.group(1) == "abrCMAB" and int(m.group(4)) == 300:
            per.append(dict(session=s.name, latency_s=round(v.mean_live_latency(s), 2),
                            rebuffer_pct=round(v.rebuffer_sample_ratio_pct(s), 2),
                            bitrate_kbps=round(v.mean_bitrate_kbps(s))))
    if per:
        with (out.parent / "d1-cmab-5s-sessions.csv").open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(per[0].keys()))
            w.writeheader()
            w.writerows(per)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
