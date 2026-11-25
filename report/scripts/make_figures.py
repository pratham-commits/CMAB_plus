#!/usr/bin/env python3
"""Build the report's vector figures from committed results.

Inputs (read-only):
  review-3/results/*-aggregate-metrics.csv
  report/results/review12-aggregate.csv   (from review12_tables.py)
  review-3/data/capacity-cubic/emulation-capacity-cubic-4mbit/  (raw JSON)
Outputs: report/figures/*.pdf
"""

from __future__ import annotations

import csv
import json
import os
from datetime import datetime
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/mplconfig")
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
RES = REPO / "review-3" / "results"
OUT = REPO / "report" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "font.family": "serif",
    "font.size": 7.5,
    "axes.titlesize": 7.5,
    "axes.labelsize": 7.5,
    "legend.fontsize": 6.8,
    "xtick.labelsize": 6.8,
    "ytick.labelsize": 6.8,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "grid.linewidth": 0.4,
    "lines.linewidth": 1.1,
    "lines.markersize": 3.6,
})

# Okabe-Ito colours; markers and dashes keep series apart in grayscale.
STYLE = {
    "old CMAB": dict(color="#D55E00", marker="x", linestyle="--"),
    "CMAB+": dict(color="#0072B2", marker="o", linestyle="-"),
    "L2A": dict(color="#000000", marker="s", linestyle=":", markerfacecolor="none"),
}
PLAYERS = ["old CMAB", "CMAB+", "L2A"]


def read(path: Path) -> list[dict]:
    with path.open() as f:
        return list(csv.DictReader(f))


def metric_grid(rows, xkey, xs, fname, xlabel, xticklabels=None, logy_rebuffer=False):
    metrics = [("latency_s", "Live latency (s)"), ("rebuffer_pct", "Rebuffer ratio (%)"),
               ("bitrate_kbps", "Bitrate (kbps)")]
    fig, axes = plt.subplots(2, 3, figsize=(7.0, 3.5), sharex=True)
    for r, tcp in enumerate(["CUBIC", "BBR"]):
        for c, (m, label) in enumerate(metrics):
            ax = axes[r][c]
            for k, p in enumerate(PLAYERS):
                sel = {float(row[xkey]): row for row in rows if row["transport"] == tcp and row["algorithm"] == p}
                ys = [float(sel[x][m]) for x in xs]
                es = [float(sel[x][m + "_ci95"]) for x in xs]
                pos = [i + (k - 1) * 0.06 for i in range(len(xs))]
                ax.errorbar(pos, ys, yerr=es, capsize=1.8, elinewidth=0.6, label=p, **STYLE[p])
            ax.set_xticks(range(len(xs)))
            ax.set_xticklabels(xticklabels or [str(x) for x in xs])
            if r == 1:
                ax.set_xlabel(xlabel)
            ax.set_ylabel(label)
            ax.set_title(f"{tcp}: {label.split(' (')[0].lower()}")
            if m == "rebuffer_pct":
                ax.set_ylim(-3, 103)
            if m == "bitrate_kbps":
                ax.set_ylim(0, 6500)
    handles, labels = axes[0][0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=3, frameon=False,
               bbox_to_anchor=(0.5, 1.0))
    fig.tight_layout(pad=0.4, h_pad=0.6, w_pad=0.8, rect=(0, 0, 1, 0.94))
    fig.savefig(OUT / fname)
    plt.close(fig)


def capacity():
    rows = read(RES / "capacity-aggregate-metrics.csv")
    metric_grid(rows, "rate_mbit", [1.0, 4.0, 8.0], "capacity.pdf", "Bottleneck capacity (Mbit/s)",
                ["1", "4", "8"])


def trace():
    rows = read(RES / "trace-targets-aggregate-metrics.csv")
    metric_grid(rows, "target_s", [3.0, 4.0, 5.0, 6.0], "trace.pdf", "Target latency (s)",
                ["3", "4", "5", "6"])


def review12():
    rows = read(REPO / "report" / "results" / "review12-aggregate.csv")
    series = [
        ("D1-CUBIC-clock", "D1: CUBIC, clock", dict(color="#0072B2", marker="o", linestyle="-")),
        ("D3-BBR-clock", "D3: BBR, clock", dict(color="#009E73", marker="^", linestyle="--")),
        ("D2-BBR-trace", "D2: BBR, trace", dict(color="#D55E00", marker="x", linestyle=":")),
    ]
    targets = [3, 4, 5, 6]
    fig, axes = plt.subplots(1, 2, figsize=(3.4, 1.65))
    for k, (key, label, st) in enumerate(series):
        sel = {int(r["target_s"]): r for r in rows if r["dataset"] == key and r["abr"] == "abrCMAB"}
        pos = [t + (k - 1) * 0.08 for t in targets]
        for ax, m in zip(axes, ["latency_s", "rebuffer_pct"]):
            ys = [float(sel[t][m]) for t in targets]
            es = [float(sel[t][m.replace("_s", "_ci95").replace("_pct", "_ci95")]) for t in targets]
            ax.errorbar(pos, ys, yerr=es, capsize=1.6, elinewidth=0.6, label=label, **st)
    axes[0].plot([3, 6], [3, 6], color="0.5", linewidth=0.6, linestyle="-.", label="target")
    axes[0].set_ylabel("Live latency (s)")
    axes[1].set_ylabel("Rebuffer ratio (%)")
    for ax in axes:
        ax.set_xlabel("Target latency (s)")
        ax.set_xticks(targets)
    axes[1].set_ylim(-1.5, 37)
    axes[0].set_ylim(2, 10.5)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=4, frameon=False, fontsize=6.0,
               bbox_to_anchor=(0.5, 1.02), handlelength=1.6, columnspacing=0.8)
    fig.tight_layout(pad=0.3, w_pad=0.6, rect=(0, 0, 1, 0.88))
    fig.savefig(OUT / "review2-cmab.pdf")
    plt.close(fig)


def _series(path: Path):
    data = json.loads(path.read_text())
    pts = sorted((datetime.fromisoformat(k), float(v)) for k, v in data.items())
    return pts


def timeline():
    """4 Mbit CUBIC, round 0: bitrate and buffer for old CMAB vs CMAB+ over 60 s."""
    base = REPO / "review-3/data/capacity-cubic/emulation-capacity-cubic-4mbit/target-3s"
    runs = {
        "old CMAB": next(base.glob("abrCMAB-*-variable-0")),
        "CMAB+": next(base.glob("abrCMABPlus-*-variable-0")),
    }
    fig, axes = plt.subplots(2, 1, figsize=(3.4, 2.3), sharex=True)
    t0s = {}
    for name, d in runs.items():
        br = _series(d / "bitrates.json")
        bu = _series(d / "buffer.json")
        start = br[0][0]
        # Window: 120-180 s after session start, aligned to the next minute boundary.
        w0 = start.timestamp() + 120
        w0 = w0 - (datetime.fromtimestamp(w0).second) + 60
        t0s[name] = w0
        st = STYLE[name]
        for ax, pts in zip(axes, [br, bu]):
            xs = [p[0].timestamp() - w0 for p in pts if 0 <= p[0].timestamp() - w0 <= 60]
            ys = [p[1] for p in pts if 0 <= p[0].timestamp() - w0 <= 60]
            ax.plot(xs, ys, color=st["color"], linestyle=st["linestyle"], linewidth=0.9, label=name,
                    drawstyle="steps-post")
    for ax in axes:
        for s in (12, 27, 42, 57):
            ax.axvspan(s, s + 1, color="0.6", alpha=0.35, linewidth=0)
    axes[0].axhline(4000, color="0.3", linewidth=0.6, linestyle="-.")
    axes[0].text(0.5, 4150, "4 Mbit/s bottleneck", fontsize=6.0, color="0.3")
    axes[0].set_ylabel("Bitrate (kbps)")
    axes[0].set_ylim(0, 6600)
    axes[1].set_ylabel("Buffer (s)")
    axes[1].axhline(0.05, color="0.3", linewidth=0.6, linestyle="-.")
    axes[1].set_xlabel("Second of the wall-clock minute (shaded: handover)")
    axes[1].set_xlim(0, 60)
    axes[1].set_xticks([0, 12, 27, 42, 57])
    axes[0].legend(loc="center right", frameon=True, framealpha=0.9, edgecolor="none")
    fig.tight_layout(pad=0.3, h_pad=0.4)
    fig.savefig(OUT / "timeline-4mbit.pdf")
    plt.close(fig)
    return {k: str(v.name) for k, v in runs.items()}


if __name__ == "__main__":
    capacity()
    trace()
    review12()
    print(timeline())
    print("wrote", sorted(p.name for p in OUT.glob("*.pdf")))
