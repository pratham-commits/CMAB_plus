#!/usr/bin/env python3
"""Aggregate per-session JSON; production runs only (duration-300)."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

L2A = "abrL2A"
Dynamic = "abrDynamic"
LoLP = "abrLoLP"
CMAB = "abrCMAB"

LINEWIDTH = 3
MARKERSIZE = 10
FIGSIZE = (10, 7)

SESSION_OK = re.compile(r"-duration-300-")


def is_production_session(name: str) -> bool:
    return "variable" in name and SESSION_OK.search(name)


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


def rebuffering_ratio_pct(session_dir: Path, round_duration: int = 300) -> float:
    """Share of post-startup buffer samples at or near empty (0–100%)."""
    del round_duration  # kept for call-site compatibility
    data = json.loads(session_dir.joinpath("buffer.json").read_text())
    items = list(data.items())
    if len(items) < 10:
        return 0.0
    items = items[len(items) // 5 :]
    stall = sum(1 for _, v in items if float(v) <= 0.05)
    return (stall / len(items)) * 100.0


def walk_sessions(figures_root: Path, metric_fn):
    result = {L2A: [], Dynamic: [], LoLP: [], CMAB: [], "expected": []}
    xs = list(range(3, 7))
    for target in xs:
        target_dir = figures_root / f"target-{target}s"
        buckets = {L2A: [], Dynamic: [], LoLP: [], CMAB: []}
        if target_dir.is_dir():
            for session_dir in sorted(target_dir.iterdir()):
                if not session_dir.is_dir() or not is_production_session(session_dir.name):
                    continue
                name = session_dir.name
                try:
                    val = metric_fn(session_dir)
                except FileNotFoundError:
                    continue
                if L2A in name:
                    buckets[L2A].append(val)
                elif Dynamic in name:
                    buckets[Dynamic].append(val)
                elif LoLP in name:
                    buckets[LoLP].append(val)
                elif CMAB in name:
                    buckets[CMAB].append(val)
        for k in (L2A, Dynamic, LoLP, CMAB):
            result[k].append(float(np.mean(buckets[k])) if buckets[k] else float("nan"))
        result["expected"].append(float(target))
    return xs, result


def plot_lines(xs, result, ylabel: str, title: str, out_path: Path, ylim=None):
    fig, ax = plt.subplots(figsize=FIGSIZE)
    ax.plot(result[L2A], marker="o", markersize=MARKERSIZE, color="tab:blue", linewidth=LINEWIDTH, label="L2A-LL")
    ax.plot(result[Dynamic], marker="o", markersize=MARKERSIZE, color="tab:orange", linewidth=LINEWIDTH, label="Dynamic")
    ax.plot(result[LoLP], marker="o", markersize=MARKERSIZE, color="tab:green", linewidth=LINEWIDTH, label="LoL+")
    ax.plot(result[CMAB], marker="o", markersize=MARKERSIZE, color="tab:brown", linewidth=LINEWIDTH, label="CMAB")
    if "expected" in result:
        ax.plot(result["expected"], marker="o", markersize=MARKERSIZE, color="tab:red", linewidth=LINEWIDTH, label="Expected")
    ax.set_xticks(range(4))
    ax.set_xticklabels([3, 4, 5, 6])
    ax.set_xlabel("Latency Target (seconds)")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    if ylim:
        ax.set_ylim(*ylim)
    ax.legend(loc="best")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"Wrote {out_path}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--figures-root", type=Path, required=True)
    p.add_argument("--label", default="Emulation")
    p.add_argument("--out-dir", type=Path, required=True)
    args = p.parse_args()

    root = args.figures_root.resolve()
    if not root.is_dir():
        raise SystemExit(f"Missing figures root: {root}")

    xs, lat = walk_sessions(root, avg_live_latency)
    lat_vals = [v for vals in lat.values() for v in vals if not np.isnan(v)]
    lat_ylim = (2.5, max(7.0, max(lat_vals, default=7.0) * 1.08 + 0.1))
    plot_lines(
        xs,
        lat,
        "Average Live Latency (seconds)",
        f"Average Live Latency — {args.label} (Fig 6a style)",
        args.out_dir / "average_live_latency_Emulation.png",
        ylim=lat_ylim,
    )

    _, bit = walk_sessions(root, avg_bitrate_kbps)
    plot_lines(
        xs,
        bit,
        "Average Bitrate (Kbps)",
        f"Average Bitrate — {args.label} (Fig 7a style)",
        args.out_dir / "average_bitrate_Emulation.png",
    )

    _, reb = walk_sessions(root, rebuffering_ratio_pct)
    reb.pop("expected", None)
    flat = [v for vals in reb.values() for v in vals if not np.isnan(v)]
    yhi = max(1.0, (max(flat) if flat else 1.0) * 1.2 + 0.01)
    plot_lines(
        xs,
        reb,
        "Rebuffering Time Ratio (%)",
        f"Rebuffering Ratio — {args.label} (Fig 8a style)",
        args.out_dir / "average_rebuffering_time_percentage_Emulation.png",
        ylim=(0, yhi),
    )


if __name__ == "__main__":
    main()
