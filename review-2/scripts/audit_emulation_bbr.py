#!/usr/bin/env python3
"""Audit BBR emulation results (160×300s matrix + optional smoke dirs)."""

from __future__ import annotations

import csv
import json
import re
import statistics
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

SESSION_RE = re.compile(
    r"^(abr\w+)-\d+-(\d+)-target-latency-(\d+)s-duration-(\d+)-bitrate-variable-(\d+)$"
)
ABRS = ["abrCMAB", "abrL2A", "abrLoLP", "abrDynamic"]
TARGETS = [3, 4, 5, 6]
ROUNDS = list(range(10))
REQUIRED_JSON = [
    "buffer.json",
    "playback_latency.json",
    "bitrates.json",
    "bitrate_by_second.json",
    "qoe.json",
    "currentLiveLatency.json",
]


def avg_live_latency(session_dir: Path) -> float:
    data = json.loads(session_dir.joinpath("playback_latency.json").read_text())
    vals = list(data.values())
    if len(vals) < 10:
        return float(np.mean(vals))
    trim = vals[len(vals) // 5 :]
    return float(np.mean(trim))


def avg_bitrate_kbps(session_dir: Path) -> float:
    data = json.loads(session_dir.joinpath("bitrates.json").read_text())
    vals = [float(v) for v in data.values() if float(v) > 0]
    if not vals:
        return 0.0
    trim = vals[len(vals) // 5 :]
    return float(np.mean(trim))


def rebuffering_ratio_pct(session_dir: Path, round_duration: int) -> float:
    """Same formula as plot_emulation_figures.py (stall sample count / 300 × 100)."""
    data = json.loads(session_dir.joinpath("buffer.json").read_text())
    items = list(data.items())
    if len(items) < 10:
        return 0.0
    items = items[len(items) // 5 :]
    stall_seconds = sum(1 for _, v in items if float(v) <= 0.05)
    return (stall_seconds / round_duration) * 100.0


def rebuffering_sample_ratio_pct(session_dir: Path) -> float:
    data = json.loads(session_dir.joinpath("buffer.json").read_text())
    items = list(data.items())
    if len(items) < 10:
        return 0.0
    items = items[len(items) // 5 :]
    stall = sum(1 for _, v in items if float(v) <= 0.05)
    return (stall / len(items)) * 100.0


def _parse_ts(key: str) -> datetime:
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(key, fmt)
        except ValueError:
            continue
    raise ValueError(f"unparseable timestamp: {key!r}")


def sample_span_seconds(session_dir: Path) -> float:
    data = json.loads(session_dir.joinpath("playback_latency.json").read_text())
    if len(data) < 2:
        return 0.0
    times = sorted(_parse_ts(k) for k in data.keys())
    return (times[-1] - times[0]).total_seconds()


@dataclass
class RunRecord:
    session_id: str
    abr: str
    target_s: int
    duration_s: int
    round_idx: int
    path: str
    mean_latency_s: float | None = None
    rebuffer_pct: float | None = None
    mean_bitrate_kbps: float | None = None
    sample_span_s: float | None = None
    issues: list[str] = field(default_factory=list)


def parse_session(name: str) -> tuple[str, int, int, int] | None:
    m = SESSION_RE.match(name)
    if not m:
        return None
    abr, _, target, duration, rnd = m.groups()
    return abr, int(target), int(duration), int(rnd)


def iqr_outliers(values: list[tuple[str, float]]) -> set[str]:
    if len(values) < 4:
        return set()
    xs = [v for _, v in values]
    q1, q3 = np.percentile(xs, [25, 75])
    iqr = q3 - q1
    lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    return {sid for sid, v in values if v < lo or v > hi}


def audit(figures_root: Path) -> dict:
    figures_root = figures_root.resolve()
    records: list[RunRecord] = []
    unparsed: list[str] = []

    for target_dir in sorted(figures_root.glob("target-*s")):
        if not target_dir.is_dir():
            continue
        for session_dir in sorted(target_dir.iterdir()):
            if not session_dir.is_dir():
                continue
            parsed = parse_session(session_dir.name)
            if not parsed:
                unparsed.append(session_dir.name)
                continue
            abr, target, duration, rnd = parsed
            rec = RunRecord(
                session_id=session_dir.name,
                abr=abr,
                target_s=target,
                duration_s=duration,
                round_idx=rnd,
                path=str(session_dir.relative_to(figures_root)),
            )
            for fn in REQUIRED_JSON:
                if not session_dir.joinpath(fn).is_file():
                    rec.issues.append(f"missing:{fn}")
            if rec.issues:
                records.append(rec)
                continue
            try:
                rec.mean_latency_s = avg_live_latency(session_dir)
                rec.rebuffer_pct = rebuffering_ratio_pct(session_dir, duration)
                rec.mean_bitrate_kbps = avg_bitrate_kbps(session_dir)
                rec.sample_span_s = sample_span_seconds(session_dir)
            except (json.JSONDecodeError, OSError) as e:
                rec.issues.append(f"read_error:{e}")
                records.append(rec)
                continue

            if duration != 300:
                rec.issues.append("smoke:duration_not_300")
            elif rec.sample_span_s is not None and rec.sample_span_s < 240:
                rec.issues.append(f"short_span:{rec.sample_span_s:.0f}s")
            if rec.mean_latency_s is not None and rec.mean_latency_s <= 0:
                rec.issues.append(f"latency_nonpositive:{rec.mean_latency_s:.3f}")
            reb_sample = rebuffering_sample_ratio_pct(session_dir)
            if reb_sample > 45:
                rec.issues.append(f"high_stall_sample_ratio:{reb_sample:.1f}%")
            records.append(rec)

    prod = [r for r in records if r.duration_s == 300 and not any(i.startswith("missing:") for i in r.issues)]
    smokes = [r for r in records if r.duration_s == 60]

    matrix_ok = True
    matrix_gaps = []
    for abr in ABRS:
        for t in TARGETS:
            for rnd in ROUNDS:
                matches = [r for r in prod if r.abr == abr and r.target_s == t and r.round_idx == rnd]
                if len(matches) != 1:
                    matrix_ok = False
                    matrix_gaps.append({"abr": abr, "target": t, "round": rnd, "count": len(matches)})

    anomalies: list[dict] = []
    for metric, attr in [("latency", "mean_latency_s"), ("rebuffer", "rebuffer_pct"), ("bitrate", "mean_bitrate_kbps")]:
        by_cell: dict[tuple[str, int], list[tuple[str, float]]] = defaultdict(list)
        for r in prod:
            val = getattr(r, attr)
            if val is None:
                continue
            by_cell[(r.abr, r.target_s)].append((r.session_id, val))
        for cell, pairs in by_cell.items():
            for sid in iqr_outliers(pairs):
                anomalies.append({"type": f"iqr_{metric}", "cell": cell, "session_id": sid})

    for r in records:
        for issue in r.issues:
            if issue.startswith("smoke:"):
                continue
            if issue.startswith("missing:") or issue.startswith("short_span") or issue.startswith("latency_nonpositive"):
                anomalies.append({"type": "issue", "session_id": r.session_id, "detail": issue})

    prod_issues = [r for r in prod if any(not i.startswith("smoke:") for i in r.issues)]
    summary = {
        "figures_root": str(figures_root),
        "audited_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "total_session_dirs": len(records),
        "production_300s_runs": len(prod),
        "smoke_60s_runs": len(smokes),
        "matrix_160_complete": matrix_ok and len(prod) == 160,
        "matrix_gaps": matrix_gaps,
        "production_runs_with_issues": len(prod_issues),
        "iqr_anomaly_count": len([a for a in anomalies if a["type"].startswith("iqr_")]),
        "unparsed_dir_names": unparsed,
        "smoke_session_ids": [r.session_id for r in smokes],
        "recommendation": (
            "exclude duration-60 smoke dirs from aggregation plots"
            if smokes
            else "ok"
        ),
    }
    return {"summary": summary, "records": [asdict(r) for r in records], "anomalies": anomalies}


def write_report(audit_data: dict, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "audit_summary.json").write_text(json.dumps(audit_data["summary"], indent=2))
    (out_dir / "anomalies.json").write_text(json.dumps(audit_data["anomalies"], indent=2))
    (out_dir / "run_metrics.json").write_text(json.dumps(audit_data["records"], indent=2))

    smokes = audit_data["summary"]["smoke_session_ids"]
    (out_dir / "excluded_smoke_sessions.txt").write_text("\n".join(smokes) + ("\n" if smokes else ""))

    fields = [
        "session_id",
        "abr",
        "target_s",
        "duration_s",
        "round_idx",
        "mean_latency_s",
        "rebuffer_pct",
        "mean_bitrate_kbps",
        "sample_span_s",
        "issues",
    ]
    with out_dir.joinpath("run_metrics.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for row in audit_data["records"]:
            row = dict(row)
            row["issues"] = ";".join(row.get("issues") or [])
            w.writerow(row)

    s = audit_data["summary"]
    lines = [
        "# BBR emulation audit report",
        "",
        f"- **Audited at (UTC):** {s['audited_at_utc']}",
        f"- **Production runs (300 s):** {s['production_300s_runs']} (expected 160)",
        f"- **Smoke runs (60 s):** {s['smoke_60s_runs']} — excluded from paper plots",
        f"- **160 matrix complete:** {s['matrix_160_complete']}",
        f"- **Production runs with hard issues:** {s['production_runs_with_issues']}",
        f"- **IQR statistical outliers (informational):** {s['iqr_anomaly_count']}",
        "",
        "## Smoke sessions (do not aggregate)",
        "",
    ]
    for sid in smokes:
        lines.append(f"- `{sid}`")
    lines.extend(["", "## Matrix gaps", ""])
    if s["matrix_gaps"]:
        for g in s["matrix_gaps"]:
            lines.append(f"- {g}")
    else:
        lines.append("- None")
    lines.extend(["", "## Anomalies (actionable)", ""])
    actionable = [a for a in audit_data["anomalies"] if a["type"] == "issue"]
    if actionable:
        for a in actionable[:50]:
            lines.append(f"- `{a['session_id']}`: {a['detail']}")
    else:
        lines.append("- None — production set looks consistent.")
    lines.extend(["", "## IQR outliers (review only)", ""])
    iqr = [a for a in audit_data["anomalies"] if a["type"].startswith("iqr_")]
    if not iqr:
        lines.append("- None flagged.")
    else:
        for a in iqr[:30]:
            lines.append(f"- {a['type']} {a['cell']}: `{a['session_id']}`")
        if len(iqr) > 30:
            lines.append(f"- … and {len(iqr) - 30} more (see anomalies.json)")
    (out_dir / "AUDIT_REPORT.md").write_text("\n".join(lines) + "\n")


def main():
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--figures-root",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "figures/emulation-bbr",
    )
    ap.add_argument(
        "--out-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "BBR-Review-II-Deliverable/audit",
    )
    args = ap.parse_args()
    data = audit(args.figures_root)
    write_report(data, args.out_dir)
    s = data["summary"]
    print(json.dumps(s, indent=2))
    if not s["matrix_160_complete"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
