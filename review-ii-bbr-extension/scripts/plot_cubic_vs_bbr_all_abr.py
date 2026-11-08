#!/usr/bin/env python3
"""CUBIC (Review I) vs BBR (clock 160-run): all four ABR algos × targets 3–6 s.

Produces 3 metrics × (full + zoom) = 6 PNGs.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ABRS = [
    ("abrCMAB", "CMAB"),
    ("abrL2A", "L2A"),
    ("abrLoLP", "LoLP"),
    ("abrDynamic", "Dynamic"),
]
TARGETS = [3, 4, 5, 6]
SESSION_OK = re.compile(r"-duration-300-")
CUBIC_COLOR = "#c0392b"
BBR_COLOR = "#1f77b4"
LINEWIDTH = 2.5
MARKERSIZE = 8


def metric_per_session(session_dir: Path, kind: str) -> float:
    if kind == "latency":
        data = json.loads(session_dir.joinpath("playback_latency.json").read_text())
        vals = [float(v) for v in data.values()]
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
        return 100.0 * stall / len(items)
    raise ValueError(kind)


def series_for_abr(root: Path, abr_key: str, kind: str) -> tuple[list[float], list[float]]:
    """Returns (means, stds) per target, n=10 rounds."""
    means, stds = [], []
    for target in TARGETS:
        tdir = root / f"target-{target}s"
        vals: list[float] = []
        if tdir.is_dir():
            for d in sorted(tdir.iterdir()):
                if (
                    d.is_dir()
                    and abr_key in d.name
                    and SESSION_OK.search(d.name)
                    and "variable" in d.name
                ):
                    try:
                        vals.append(metric_per_session(d, kind))
                    except FileNotFoundError:
                        pass
        if vals:
            means.append(float(np.mean(vals)))
            stds.append(float(np.std(vals, ddof=1)) if len(vals) > 1 else 0.0)
        else:
            means.append(float("nan"))
            stds.append(0.0)
    return means, stds


def plot_metric(
    cubic_root: Path,
    bbr_root: Path,
    kind: str,
    ylabel: str,
    title: str,
    out_path: Path,
    *,
    zoom: bool,
    bbr_legend: str,
):
    fig, axes = plt.subplots(2, 2, figsize=(12, 9), sharex=True)
    fig.suptitle(title, fontsize=14, fontweight="bold")

    for ax, (abr_key, abr_label) in zip(axes.flat, ABRS):
        cm, cs = series_for_abr(cubic_root, abr_key, kind)
        bm, bs = series_for_abr(bbr_root, abr_key, kind)
        xs = np.array(TARGETS, dtype=float)
        # Slight X offset so CUBIC and BBR both show when means coincide (e.g. L2A @ 6000 kbps).
        x_off = 0.07
        xs_c = xs - x_off
        xs_b = xs + x_off

        ax.errorbar(
            xs_c,
            cm,
            yerr=cs,
            color=CUBIC_COLOR,
            marker="o",
            markersize=MARKERSIZE,
            linewidth=LINEWIDTH,
            capsize=4,
            linestyle="--",
            zorder=3,
            label="TCP CUBIC (Review I)",
        )
        ax.errorbar(
            xs_b,
            bm,
            yerr=bs,
            color=BBR_COLOR,
            marker="s",
            markersize=MARKERSIZE,
            linewidth=LINEWIDTH,
            capsize=4,
            linestyle="-",
            zorder=2,
            label=bbr_legend,
        )
        ax.set_title(abr_label, fontsize=12)
        ax.set_xticks(TARGETS)
        ax.grid(True, alpha=0.35)
        ax.legend(loc="best", fontsize=8)

        if np.allclose(cm, bm, rtol=0, atol=1e-9, equal_nan=True) and not any(
            np.isnan(v) for v in cm + bm
        ):
            ax.text(
                0.5,
                0.04,
                "CUBIC ≈ BBR (overlapping means)",
                transform=ax.transAxes,
                ha="center",
                fontsize=7,
                color="dimgray",
            )

        if zoom:
            all_y = [v for v in cm + bm if not np.isnan(v)]
            if all_y:
                lo, hi = min(all_y), max(all_y)
                span = hi - lo
                if kind == "latency":
                    pad = max(0.08 * span, 0.05)
                elif kind == "bitrate":
                    pad = max(0.08 * span, 80.0)
                else:
                    pad = max(0.08 * span, 0.15)
                if span < 1e-12:
                    pad = {"latency": 0.15, "bitrate": 120.0, "rebuffer": 0.2}[kind]
                ax.set_ylim(lo - pad, hi + pad)

    for ax in axes[1, :]:
        ax.set_xlabel("Target live latency (s)")
    axes[0, 0].set_ylabel(ylabel)
    axes[1, 0].set_ylabel(ylabel)

    fig.tight_layout(rect=[0, 0, 1, 0.96])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=160)
    plt.close(fig)
    print(f"Wrote {out_path}")


def plot_target3_bars(
    cubic_root: Path,
    bbr_root: Path,
    kind: str,
    ylabel: str,
    title: str,
    out_path: Path,
):
    """Extra clarity: all ABR at target 3 s only (paired bars)."""
    labels = [a[1] for a in ABRS]
    x = np.arange(len(labels))
    width = 0.35
    cubic_vals, cubic_err, bbr_vals, bbr_err = [], [], [], []
    for abr_key, _ in ABRS:
        cm, cs = series_for_abr(cubic_root, abr_key, kind)
        bm, bs = series_for_abr(bbr_root, abr_key, kind)
        cubic_vals.append(cm[0])
        cubic_err.append(cs[0])
        bbr_vals.append(bm[0])
        bbr_err.append(bs[0])

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(x - width / 2, cubic_vals, width, yerr=cubic_err, color=CUBIC_COLOR, label="CUBIC", capsize=4)
    ax.bar(x + width / 2, bbr_vals, width, yerr=bbr_err, color=BBR_COLOR, label="BBR", capsize=4)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend()
    ax.grid(True, axis="y", alpha=0.35)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=160)
    plt.close(fig)
    print(f"Wrote {out_path}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--cubic-root",
        type=Path,
        default=Path(
            "/Users/prathamshah/BITS/ACN/Project/review 1/mmsys24-starlink-livestreaming/figures/emulation"
        ),
    )
    ap.add_argument(
        "--bbr-root",
        type=Path,
        default=Path(
            "review-ii-bbr-extension/deliverables/bbr-clock-160-deliverable-20261018-0535/figures/emulation-bbr-clock"
        ),
    )
    ap.add_argument(
        "--out-dir",
        type=Path,
        default=Path("review-ii-bbr-extension/figures/comparison-cubic-vs-bbr-clock"),
    )
    ap.add_argument(
        "--bbr-legend",
        default="TCP BBR (clock 160-run)",
        help="Legend label for BBR series",
    )
    ap.add_argument(
        "--title-suffix",
        default="",
        help="Appended to each figure suptitle (e.g. run type)",
    )
    args = ap.parse_args()
    args.cubic_root = args.cubic_root.resolve()
    args.bbr_root = args.bbr_root.resolve()
    args.out_dir = args.out_dir.resolve()

    specs = [
        ("latency", "Mean live latency (s)", "Live latency · CUBIC vs BBR (all ABR)"),
        ("bitrate", "Mean bitrate (kbps)", "Bitrate · CUBIC vs BBR (all ABR)"),
        ("rebuffer", "Rebuffer sample ratio (%)", "Rebuffering · CUBIC vs BBR (all ABR)"),
    ]
    suffix = args.title_suffix or ""
    for kind, ylabel, title in specs:
        plot_metric(
            args.cubic_root,
            args.bbr_root,
            kind,
            ylabel,
            title + suffix + " · full scale",
            args.out_dir / f"{kind}_all_abr_full.png",
            zoom=False,
            bbr_legend=args.bbr_legend,
        )
        plot_metric(
            args.cubic_root,
            args.bbr_root,
            kind,
            ylabel,
            title + suffix + " · zoomed Y",
            args.out_dir / f"{kind}_all_abr_zoom.png",
            zoom=True,
            bbr_legend=args.bbr_legend,
        )
        plot_target3_bars(
            args.cubic_root,
            args.bbr_root,
            kind,
            ylabel,
            title + " · target 3 s only",
            args.out_dir / f"{kind}_target3s_bars.png",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
