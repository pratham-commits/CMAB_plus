"""Aggregate the pre-stall-guard trace trees (CMAB+ rules 1-4) with the
same metric code as review-3/analyze_trace_targets.py."""
import csv
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "review-3"))
import analyze_trace_targets as a  # noqa: E402

a.DATA_ROOTS = {
    "CUBIC": REPO / "review-3/data/trace-targets-cubic.pre-stallguard-20261108",
    "BBR": REPO / "review-3/data/trace-targets-bbr.pre-stallguard-20261108",
}
rows = a.aggregate(a.collect_sessions())
out = REPO / "report/results/trace-pre-stallguard-aggregate.csv"
with out.open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
print(f"wrote {out} ({len(rows)} cells)")
