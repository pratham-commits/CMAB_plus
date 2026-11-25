#!/usr/bin/env python3
"""Slide-sized result figures, drawn from committed results.

Inputs (read-only):
  review-3/results/*-aggregate-metrics.csv          (Review III, n = 5 per cell)
  report/results/review12-aggregate.csv              (Review I/II, n = 10 per cell)
  report/results/trace-pre-stallguard-aggregate.csv  (trace, CMAB+ rules 1-4)
  review-3/demo-ui/public/sessions/*.json            (one logged session per player, ~2 Hz)
Outputs: final-review/presentation/assets/fig-*.png
Error bars are two-sided 95% Student-t intervals, as in the report.
"""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/mplconfig")
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
RES = REPO / "review-3" / "results"
SESS = REPO / "review-3" / "demo-ui" / "public" / "sessions"
OUT = HERE / "assets"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 15,
    "axes.titlesize": 17,
    "axes.labelsize": 16,
    "legend.fontsize": 15,
    "xtick.labelsize": 15,
    "ytick.labelsize": 14,
    "axes.grid": True,
    "axes.axisbelow": True,
    "grid.alpha": 0.3,
    "lines.linewidth": 2.6,
    "lines.markersize": 9,
    "axes.spines.top": False,
    "axes.spines.right": False,
})

ORANGE, BLUE, GREY, GREEN = "#D55E00", "#0072B2", "#8C8C8C", "#009E73"
PLAYERS = ["old CMAB", "CMAB+", "L2A"]
LABEL = {"old CMAB": "old CMAB", "CMAB+": "CMAB+", "L2A": "L2A-LL (reference)"}
COLOR = {"old CMAB": ORANGE, "CMAB+": BLUE, "L2A": GREY}
LINE = {
    "old CMAB": dict(color=ORANGE, marker="x", linestyle="--", markeredgewidth=2.5),
    "CMAB+": dict(color=BLUE, marker="o", linestyle="-"),
    "L2A": dict(color=GREY, marker="s", linestyle=":", markerfacecolor="none", markeredgewidth=2),
}
HATCH = {"old CMAB": "//", "CMAB+": "", "L2A": ".."}
UNIT = {"latency_s": "Live latency (s)", "rebuffer_pct": "Rebuffer ratio (%)",
        "bitrate_kbps": "Bitrate (kbps)"}


def read(path: Path) -> list[dict]:
    with path.open() as f:
        return list(csv.DictReader(f))


def cell(rows, tcp, xkey, x, alg):
    for r in rows:
        if r["transport"] == tcp and float(r[xkey]) == x and r["algorithm"] == alg:
            return r
    raise KeyError((tcp, x, alg))


def fmt_val(v, metric):
    if metric == "rebuffer_pct":
        return f"{v:.0f}%" if v >= 1 or v == 0 else f"{v:.1f}%"
    if metric == "bitrate_kbps":
        return f"{v:.0f}"
    return f"{v:.1f}"


def save(fig, name):
    fig.savefig(OUT / name, dpi=200)
    plt.close(fig)


def legend_top(fig, handles, labels, ncol=3):
    fig.legend(handles, labels, loc="upper center", ncol=ncol, frameon=False,
               bbox_to_anchor=(0.5, 1.0))


def bars(csvname, xkey, xs, metric, fname, xlabel, xticks=None, ylim=None,
         labels=True, link_rate=False, players=PLAYERS, rows=None):
    """CUBIC and BBR side by side; grouped bars per x with 95% CI."""
    rows = rows if rows is not None else read(RES / csvname)
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.3), sharey=True)
    w = 0.8 / len(players)
    for ax, tcp in zip(axes, ["CUBIC", "BBR"]):
        for k, p in enumerate(players):
            vals = [float(cell(rows, tcp, xkey, x, p)[metric]) for x in xs]
            errs = [float(cell(rows, tcp, xkey, x, p)[metric + "_ci95"]) for x in xs]
            pos = [i + (k - (len(players) - 1) / 2) * w for i in range(len(xs))]
            ax.bar(pos, vals, w * 0.92, yerr=errs, capsize=4, color=COLOR[p],
                   hatch=HATCH[p], edgecolor="white", linewidth=0.5,
                   error_kw=dict(elinewidth=1.6, ecolor="#333333"), label=LABEL[p])
            if labels:
                top = ylim[1] if ylim else max(vals) * 1.15
                for x0, v, e in zip(pos, vals, errs):
                    ax.text(x0, min(v + e, top * 0.93) + top * 0.015, fmt_val(v, metric),
                            ha="center", va="bottom", fontsize=11.5, color="#222222")
        if link_rate:
            for i, x in enumerate(xs):
                ax.plot([i - 0.45, i + 0.45], [x * 1000] * 2, color="#222222",
                        linestyle="-.", linewidth=1.8)
        ax.set_xticks(range(len(xs)))
        ax.set_xticklabels(xticks or [f"{x:g}" for x in xs])
        ax.set_xlabel(xlabel)
        ax.set_title(tcp, fontweight="bold")
        ax.grid(axis="x", visible=False)
        if ylim:
            ax.set_ylim(*ylim)
    axes[0].set_ylabel(UNIT[metric])
    h, lab = axes[0].get_legend_handles_labels()
    if link_rate:
        h.append(plt.Line2D([], [], color="#222222", linestyle="-.", linewidth=1.8))
        lab.append("link rate")
    legend_top(fig, h, lab, ncol=len(h))
    fig.tight_layout(rect=(0, 0, 1, 0.9), w_pad=2.0)
    save(fig, fname)


def lines(csvname, xkey, xs, metric, fname, xlabel, target_line=False, ylim=None):
    rows = read(RES / csvname)
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.3), sharey=True)
    for ax, tcp in zip(axes, ["CUBIC", "BBR"]):
        if target_line:
            ax.plot(xs, xs, color="#222222", linestyle="-.", linewidth=1.6, label="target")
        for k, p in enumerate(PLAYERS):
            vals = [float(cell(rows, tcp, xkey, x, p)[metric]) for x in xs]
            errs = [float(cell(rows, tcp, xkey, x, p)[metric + "_ci95"]) for x in xs]
            pos = [x + (k - 1) * 0.05 for x in xs]
            ax.errorbar(pos, vals, yerr=errs, capsize=5, elinewidth=1.6, label=LABEL[p], **LINE[p])
        ax.set_xticks(xs)
        ax.set_xticklabels([f"{x:g}" for x in xs])
        ax.set_xlabel(xlabel)
        ax.set_title(tcp, fontweight="bold")
        if ylim:
            ax.set_ylim(*ylim)
    axes[0].set_ylabel(UNIT[metric])
    h, lab = axes[0].get_legend_handles_labels()
    legend_top(fig, h, lab, ncol=len(h))
    fig.tight_layout(rect=(0, 0, 1, 0.9), w_pad=2.0)
    save(fig, fname)


def review2_abrs():
    rows = read(REPO / "report" / "results" / "review12-aggregate.csv")
    abrs = [("abrDynamic", "Dynamic"), ("abrL2A", "L2A-LL"), ("abrLoLP", "LoL+"), ("abrCMAB", "CMAB")]
    sets = [("D1-CUBIC-clock", "D1: CUBIC, clock", BLUE, ""),
            ("D3-BBR-clock", "D3: BBR, clock", GREEN, "//"),
            ("D2-BBR-trace", "D2: BBR, trace (wrong shaper)", ORANGE, "..")]
    metrics = [("latency_s", "latency_ci95", "Live latency (s)", (0, 8.5)),
               ("rebuffer_pct", "rebuffer_ci95", "Rebuffer ratio (%)", (0, 34)),
               ("bitrate_kbps", "bitrate_ci95", "Bitrate (kbps)", (0, 7000))]
    fig, axes = plt.subplots(1, 3, figsize=(14, 5.2))
    w = 0.27
    for ax, (m, ci, label, ylim) in zip(axes, metrics):
        for k, (key, lab, col, hatch) in enumerate(sets):
            sel = {r["abr"]: r for r in rows if r["dataset"] == key and r["target_s"] == "3"}
            vals = [float(sel[a][m]) for a, _ in abrs]
            errs = [float(sel[a][ci]) for a, _ in abrs]
            pos = [i + (k - 1) * w for i in range(len(abrs))]
            ax.bar(pos, vals, w * 0.92, yerr=errs, capsize=3, color=col, hatch=hatch,
                   edgecolor="white", error_kw=dict(elinewidth=1.4, ecolor="#333333"), label=lab)
        ax.set_xticks(range(len(abrs)))
        ax.set_xticklabels([n for _, n in abrs])
        ax.set_ylabel(label)
        ax.set_ylim(*ylim)
        ax.grid(axis="x", visible=False)
    h, lab = axes[0].get_legend_handles_labels()
    legend_top(fig, h, lab)
    fig.tight_layout(rect=(0, 0, 1, 0.9), w_pad=2.0)
    save(fig, "fig-review2-abrs.png")


def stall_guard():
    pre = read(REPO / "report" / "results" / "trace-pre-stallguard-aggregate.csv")
    post = read(RES / "trace-targets-aggregate-metrics.csv")
    xs = [3.0, 4.0, 5.0, 6.0]
    variants = [("CMAB+ rules 1–4 (before guard)", pre, "#9CC3E0", "//"),
                ("CMAB+ rules 1–5 (with guard)", post, BLUE, "")]
    fig, axes = plt.subplots(2, 2, figsize=(13, 6.6), sharex=True)
    for c, tcp in enumerate(["CUBIC", "BBR"]):
        for r, (m, ylim) in enumerate([("rebuffer_pct", (0, 48)), ("bitrate_kbps", (0, 4800))]):
            ax = axes[r][c]
            for k, (lab, rows, col, hatch) in enumerate(variants):
                vals = [float(cell(rows, tcp, "target_s", x, "CMAB+")[m]) for x in xs]
                errs = [float(cell(rows, tcp, "target_s", x, "CMAB+")[m + "_ci95"]) for x in xs]
                pos = [i + (k - 0.5) * 0.38 for i in range(len(xs))]
                ax.bar(pos, vals, 0.35, yerr=errs, capsize=4, color=col, hatch=hatch,
                       edgecolor="white", error_kw=dict(elinewidth=1.4, ecolor="#333333"), label=lab)
                for x0, v, e in zip(pos, vals, errs):
                    ax.text(x0, min(v + e, ylim[1] * 0.9) + ylim[1] * 0.02, fmt_val(v, m),
                            ha="center", va="bottom", fontsize=11.5)
            ax.set_ylim(*ylim)
            ax.set_xticks(range(len(xs)))
            ax.set_xticklabels([f"{x:g}" for x in xs])
            ax.grid(axis="x", visible=False)
            if r == 0:
                ax.set_title(tcp, fontweight="bold")
            else:
                ax.set_xlabel("Target latency (s)")
            if c == 0:
                ax.set_ylabel(UNIT[m])
    h, lab = axes[0][0].get_legend_handles_labels()
    legend_top(fig, h, lab, ncol=2)
    fig.tight_layout(rect=(0, 0, 1, 0.92), h_pad=1.2, w_pad=2.0)
    save(fig, "fig-stallguard.png")


def session(name):
    d = json.loads((SESS / name).read_text())
    return d, d["samples"]


def trace_timeline():
    """Trace, CUBIC, 3 s target, round 0: CMAB+ stalls, then holds a low rung."""
    lo, hi = 95, 150
    dp, sp = session("p3-trace-cubic-t3__cmab.json")
    do, so = session("p3-trace-cubic-t3__old-cmab.json")
    fig, axes = plt.subplots(2, 1, figsize=(13, 6.4), sharex=True)
    for name, smp, st in [("old CMAB", so, LINE["old CMAB"]), ("CMAB+", sp, LINE["CMAB+"])]:
        pts = [x for x in smp if lo <= x["t"] <= hi]
        ts = [x["t"] for x in pts]
        axes[0].step(ts, [x["bitrate"] for x in pts], where="post", color=st["color"],
                     linestyle=st["linestyle"], label=name)
        axes[1].step(ts, [x["buffer"] for x in pts], where="post", color=st["color"],
                     linestyle=st["linestyle"], label=name)
    axes[0].axvspan(106, 127, color=BLUE, alpha=0.10, linewidth=0)
    axes[0].annotate("CMAB+ holds 450 kbps for ~21 s\nafter its buffer empties",
                     xy=(116, 450), xytext=(109, 2600), fontsize=14, color=BLUE,
                     arrowprops=dict(arrowstyle="->", color=BLUE, lw=1.8))
    axes[1].axvspan(106, 127, color=BLUE, alpha=0.10, linewidth=0)
    axes[1].axhline(0.05, color="#222222", linestyle="-.", linewidth=1.4)
    axes[0].set_ylabel("Bitrate (kbps)")
    axes[0].set_ylim(0, 6600)
    axes[1].set_ylabel("Buffer (s)")
    axes[1].set_xlabel("Session time (s)")
    axes[1].set_xlim(lo, hi)
    h, lab = axes[0].get_legend_handles_labels()
    legend_top(fig, h, lab, ncol=2)
    fig.tight_layout(rect=(0, 0, 1, 0.93), h_pad=0.8)
    save(fig, "fig-trace-timeline.png")
    return dp["session"], do["session"]


if __name__ == "__main__":
    t = [3.0, 4.0, 5.0, 6.0]
    review2_abrs()
    lines("clock-nonreg-aggregate-metrics.csv", "target_s", t, "latency_s",
          "fig-clock-latency.png", "Target latency (s)", target_line=True)
    bars("clock-nonreg-aggregate-metrics.csv", "target_s", t, "bitrate_kbps",
         "fig-clock-bitrate.png", "Target latency (s)", ylim=(0, 7000), labels=False)
    bars("capacity-4mbit-targets-aggregate-metrics.csv", "target_s", t, "rebuffer_pct",
         "fig-4mbit-rebuffer.png", "Target latency (s)", ylim=(0, 100))
    lines("capacity-4mbit-targets-aggregate-metrics.csv", "target_s", t, "latency_s",
          "fig-4mbit-latency.png", "Target latency (s)", target_line=True, ylim=(2, 12.5))
    bars("capacity-aggregate-metrics.csv", "rate_mbit", [8.0, 4.0, 1.0], "rebuffer_pct",
         "fig-capacity-rebuffer.png", "Bottleneck capacity (Mbit/s)", ylim=(0, 110))
    bars("capacity-aggregate-metrics.csv", "rate_mbit", [8.0, 4.0, 1.0], "bitrate_kbps",
         "fig-capacity-bitrate.png", "Bottleneck capacity (Mbit/s)", ylim=(0, 9000),
         link_rate=True)
    bars("trace-targets-aggregate-metrics.csv", "target_s", t, "rebuffer_pct",
         "fig-trace-rebuffer.png", "Target latency (s)", ylim=(0, 100))
    bars("trace-targets-aggregate-metrics.csv", "target_s", t, "bitrate_kbps",
         "fig-trace-bitrate.png", "Target latency (s)", ylim=(0, 7000))
    stall_guard()
    print(trace_timeline())
    print(sorted(p.name for p in OUT.glob("fig-*.png")))
