#!/usr/bin/env python3
"""Recompute CMAB (and optional ABR) aggregates from emulation JSON trees.

Metrics match review-ii plot/audit scripts:
  - Mean live latency: playback_latency.json, drop first 20% of samples
  - Rebuffer sample ratio: buffer.json, fraction of samples with level <= 0.05 s
  - Mean bitrate: bitrates.json, positive values only, drop first 20%

Example:
  python3 verify_cmab_claims.py \\
    --label CUBIC \\
    --root "/path/to/figures/emulation" \\
    --label BBR \\
    --root "/path/to/figures/emulation-bbr"
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path

SESSION_RE = re.compile(
    r"^(abr\w+)-\d+-(\d+)-target-latency-(\d+)s-duration-(\d+)-bitrate-variable-(\d+)$"
)


def _trim(items: list) -> list:
    if len(items) < 10:
        return items
    return items[len(items) // 5 :]


def mean_live_latency(session_dir: Path) -> float:
    data = json.loads(session_dir.joinpath("playback_latency.json").read_text())
    vals = [float(v) for v in data.values()]
    t = _trim(vals)
    return statistics.mean(t) if t else float("nan")


def rebuffer_sample_ratio_pct(session_dir: Path) -> float:
    data = json.loads(session_dir.joinpath("buffer.json").read_text())
    items = _trim(list(data.items()))
    if not items:
        return 0.0
    stall = sum(1 for _, v in items if float(v) <= 0.05)
    return 100.0 * stall / len(items)


def mean_bitrate_kbps(session_dir: Path) -> float:
    data = json.loads(session_dir.joinpath("bitrates.json").read_text())
    vals = [float(v) for v in data.values() if float(v) > 0]
    t = _trim(vals)
    return statistics.mean(t) if t else 0.0


def arm_histogram(session_dir: Path) -> dict[int, int]:
    path = session_dir / "arms.json"
    if not path.is_file():
        return {}
    raw = json.loads(path.read_text())
    if isinstance(raw, dict):
        arms = [int(v) for v in raw.values()]
    else:
        arms = [int(v) for v in raw]
    hist: dict[int, int] = {}
    for a in arms:
        hist[a] = hist.get(a, 0) + 1
    return hist


def aggregate_root(
    root: Path,
    abr: str = "abrCMAB",
    target_s: int = 3,
    duration_s: int = 300,
) -> dict:
    root = root.resolve()
    target_dir = root / f"target-{target_s}s"
    if not target_dir.is_dir():
        raise FileNotFoundError(target_dir)

    latencies: list[float] = []
    rebuffers: list[float] = []
    bitrates: list[float] = []
    sessions: list[str] = []
    arm_totals: dict[int, int] = {}

    for session_dir in sorted(target_dir.iterdir()):
        if not session_dir.is_dir():
            continue
        m = SESSION_RE.match(session_dir.name)
        if not m or m.group(1) != abr:
            continue
        if int(m.group(3)) != target_s or int(m.group(4)) != duration_s:
            continue
        latencies.append(mean_live_latency(session_dir))
        rebuffers.append(rebuffer_sample_ratio_pct(session_dir))
        bitrates.append(mean_bitrate_kbps(session_dir))
        sessions.append(session_dir.name)
        for arm, cnt in arm_histogram(session_dir).items():
            arm_totals[arm] = arm_totals.get(arm, 0) + cnt

    n = len(latencies)
    return {
        "root": str(root),
        "abr": abr,
        "target_s": target_s,
        "duration_s": duration_s,
        "n_sessions": n,
        "mean_latency_s": statistics.mean(latencies) if latencies else None,
        "stdev_latency_s": statistics.pstdev(latencies) if n > 1 else 0.0,
        "mean_rebuffer_sample_pct": statistics.mean(rebuffers) if rebuffers else None,
        "mean_bitrate_kbps": statistics.mean(bitrates) if bitrates else None,
        "sessions": sessions,
        "arm_histogram": dict(sorted(arm_totals.items())),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", action="append", required=True, help="figures/emulation root")
    parser.add_argument("--label", action="append", help="label per --root (same order)")
    parser.add_argument("--abr", default="abrCMAB")
    parser.add_argument("--target", type=int, default=3)
    parser.add_argument("--duration", type=int, default=300)
    parser.add_argument("--also-abr", default="abrDynamic", help="second ABR to print")
    args = parser.parse_args()

    labels = args.label or [f"root{i}" for i in range(len(args.root))]
    if len(labels) != len(args.root):
        print("error: --label count must match --root count", file=sys.stderr)
        return 2

    for label, root_str in zip(labels, args.root):
        root = Path(root_str)
        for abr in (args.abr, args.also_abr):
            stats = aggregate_root(root, abr=abr, target_s=args.target, duration_s=args.duration)
            print(f"\n=== {label} | {abr} | target={args.target}s | n={stats['n_sessions']} ===")
            print(f"  mean live latency (s):     {stats['mean_latency_s']:.4f}" if stats["mean_latency_s"] else "  (no runs)")
            print(f"  rebuffer sample ratio (%): {stats['mean_rebuffer_sample_pct']:.4f}" if stats["mean_rebuffer_sample_pct"] is not None else "")
            print(f"  mean bitrate (kbps):       {stats['mean_bitrate_kbps']:.2f}" if stats["mean_bitrate_kbps"] else "")
            if abr == args.abr and stats.get("arm_histogram"):
                print(f"  arm histogram (index):     {stats['arm_histogram']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
