#!/usr/bin/env python3
"""CUBIC (Review I) vs BBR — abrDynamic only, production duration-300 sessions."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

Dynamic = "abrDynamic"
FIGSIZE = (10, 7)
LINEWIDTH = 3
MARKERSIZE = 10
SESSION_OK = re.compile(r"-duration-300-")


def metric_per_round(session_dir: Path, kind: str) -> float:
    if kind == "latency":
        data = json.loads(session_dir.joinpath("playback_latency.json").read_text())
        vals = list(data.values())
        trim = vals[len(vals) // 5 :]
        return float(np.mean(trim))
    if kind == "bitrate":
        data = json.loads(session_dir.joinpath("bitrates.json").read_text())
        vals = [float(v) for v in data.values() if float(v) > 0]
        trim = vals[len(vals) // 5 :]
        return float(np.mean(trim))
    if kind == "rebuffer":
        data = json.loads(session_dir.joinpath("buffer.json").read_text())
        items = list(data.items())[len(data) // 5 :]
        if not items:
            return 0.0
        stall = sum(1 for _, v in items if float(v) <= 0.05)
        return (stall / len(items)) * 100.0
    raise ValueError(kind)


def dynamic_series(root: Path, kind: str) -> list[float]:
    out = []
    for target in range(3, 7):
        tdir = root / f"target-{target}s"
        vals = []
        if tdir.is_dir():
            for d in sorted(tdir.iterdir()):
                if (
                    d.is_dir()
                    and Dynamic in d.name
                    and SESSION_OK.search(d.name)
                ):
                    try:
                        vals.append(metric_per_round(d, kind))
                    except FileNotFoundError:
                        pass
        out.append(float(np.mean(vals)) if vals else float("nan"))
    return out


def plot_pair(cubic, bbr, ylabel: str, title: str, path: Path):
    fig, ax = plt.subplots(figsize=FIGSIZE)
    xs = np.arange(4)
    ax.plot(cubic, marker="o", markersize=MARKERSIZE, color="tab:red", linewidth=LINEWIDTH, label="TCP CUBIC (Review I)")
    ax.plot(bbr, marker="o", markersize=MARKERSIZE, color="tab:green", linewidth=LINEWIDTH, label="TCP BBR (Review II)")
    ax.set_xticks(xs)
    ax.set_xticklabels([3, 4, 5, 6])
    ax.set_xlabel("Latency Target (seconds)")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"Wrote {path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cubic-root", type=Path, required=True)
    ap.add_argument("--bbr-root", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    args = ap.parse_args()

    for kind, ylabel, fname in [
        ("latency", "Average Live Latency (s)", "dynamic_latency_cubic_vs_bbr.png"),
        ("bitrate", "Average Bitrate (Kbps)", "dynamic_bitrate_cubic_vs_bbr.png"),
        ("rebuffer", "Rebuffering Ratio (%)", "dynamic_rebuffer_cubic_vs_bbr.png"),
    ]:
        cubic = dynamic_series(args.cubic_root, kind)
        bbr = dynamic_series(args.bbr_root, kind)
        plot_pair(
            cubic,
            bbr,
            ylabel,
            f"Dynamic ABR · {ylabel.split('(')[0].strip()} · CUBIC vs BBR",
            args.out_dir / fname,
        )


if __name__ == "__main__":
    main()
