#!/usr/bin/env python3
"""Recompute Review III capacity metrics and generate paper-ready figures.

Metric definitions match Review II:
  * latency: mean playback latency after dropping the first 20% of samples
  * rebuffer: fraction of post-trim buffer samples <= 0.05 seconds
  * bitrate: mean positive bitrate after dropping the first 20%
"""

from __future__ import annotations

import csv
import json
import math
import os
import re
import statistics
from collections import defaultdict
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/cmab-plus-matplotlib")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp/cmab-plus-cache")
os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parent
DATA_ROOTS = {
    "CUBIC": ROOT / "data" / "capacity-cubic",
    "BBR": ROOT / "data" / "capacity-bbr",
}
OUTPUT = ROOT / "results"
FIGURES = ROOT / "figures"
RATES = (8, 4, 1)
ALGORITHMS = ("old CMAB", "CMAB+", "L2A")
COLORS = {
    "old CMAB": "#7f7f7f",
    "CMAB+": "#2878b5",
    "L2A": "#d47a20",
}
SESSION_RE = re.compile(
    r"^(abrCMABPlus|abrCMAB|abrL2A)-.*-target-latency-(\d+)s-"
    r"duration-(\d+)-bitrate-variable-(\d+)$"
)
RATE_RE = re.compile(r"-(\d+)mbit$")
T_95_DF4 = 2.776


def trim(values: list) -> list:
    return values[len(values) // 5 :] if len(values) >= 10 else values


def mean_latency(session: Path) -> float:
    values = [float(v) for v in json.loads((session / "playback_latency.json").read_text()).values()]
    return statistics.mean(trim(values))


def rebuffer_pct(session: Path) -> float:
    values = trim(list(json.loads((session / "buffer.json").read_text()).values()))
    return 100.0 * sum(float(v) <= 0.05 for v in values) / len(values) if values else 0.0


def mean_bitrate(session: Path) -> float:
    values = [
        float(v)
        for v in json.loads((session / "bitrates.json").read_text()).values()
        if float(v) > 0
    ]
    values = trim(values)
    return statistics.mean(values) if values else 0.0


def algorithm_name(raw: str) -> str:
    return {
        "abrCMAB": "old CMAB",
        "abrCMABPlus": "CMAB+",
        "abrL2A": "L2A",
    }[raw]


def collect_sessions() -> list[dict]:
    rows = []
    for transport, root in DATA_ROOTS.items():
        for latency_file in sorted(root.glob("**/playback_latency.json")):
            session = latency_file.parent
            match = SESSION_RE.match(session.name)
            rate_match = RATE_RE.search(session.parent.parent.name)
            if not match or not rate_match:
                continue
            raw_algorithm, target, duration, round_id = match.groups()
            rows.append(
                {
                    "transport": transport,
                    "rate_mbit": int(rate_match.group(1)),
                    "algorithm": algorithm_name(raw_algorithm),
                    "round": int(round_id),
                    "target_s": int(target),
                    "duration_s": int(duration),
                    "latency_s": mean_latency(session),
                    "rebuffer_pct": rebuffer_pct(session),
                    "bitrate_kbps": mean_bitrate(session),
                    "session": session.name,
                }
            )
    return rows


def aggregate(rows: list[dict]) -> list[dict]:
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for row in rows:
        groups[(row["transport"], row["rate_mbit"], row["algorithm"])].append(row)

    output = []
    for (transport, rate, algorithm), sessions in groups.items():
        result = {
            "transport": transport,
            "rate_mbit": rate,
            "algorithm": algorithm,
            "n": len(sessions),
        }
        for source, label in (
            ("latency_s", "latency_s"),
            ("rebuffer_pct", "rebuffer_pct"),
            ("bitrate_kbps", "bitrate_kbps"),
        ):
            values = [row[source] for row in sessions]
            mean = statistics.mean(values)
            sd = statistics.stdev(values) if len(values) > 1 else 0.0
            ci = T_95_DF4 * sd / math.sqrt(len(values)) if len(values) > 1 else 0.0
            result[label] = mean
            result[f"{label}_sd"] = sd
            result[f"{label}_ci95"] = ci
        output.append(result)
    return sorted(
        output,
        key=lambda row: (
            ("CUBIC", "BBR").index(row["transport"]),
            RATES.index(row["rate_mbit"]),
            ALGORITHMS.index(row["algorithm"]),
        ),
    )


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def index_aggregates(rows: list[dict]) -> dict[tuple, dict]:
    return {
        (row["transport"], row["rate_mbit"], row["algorithm"]): row
        for row in rows
    }


def plot_metric(
    aggregates: list[dict],
    field: str,
    error_field: str,
    ylabel: str,
    title: str,
    filename: str,
) -> None:
    lookup = index_aggregates(aggregates)
    fig, axes = plt.subplots(1, 2, figsize=(11, 5), sharey=False)
    x = list(range(len(RATES)))
    width = 0.23
    offsets = (-width, 0, width)

    for ax, transport in zip(axes, ("CUBIC", "BBR")):
        for algorithm, offset in zip(ALGORITHMS, offsets):
            values = [lookup[(transport, rate, algorithm)][field] for rate in RATES]
            errors = [lookup[(transport, rate, algorithm)][error_field] for rate in RATES]
            ax.bar(
                [point + offset for point in x],
                values,
                width,
                yerr=errors,
                capsize=3,
                color=COLORS[algorithm],
                label=algorithm,
            )
        ax.set_title(transport)
        ax.set_xlabel("Configured bottleneck capacity (Mbit/s)")
        ax.set_xticks(x, [str(rate) for rate in RATES])
        ax.grid(axis="y", alpha=0.25)
    axes[0].set_ylabel(ylabel)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.925),
        ncols=3,
        frameon=False,
    )
    fig.suptitle(title, y=0.995, fontweight="bold")
    fig.text(
        0.5,
        -0.01,
        "Mean of 5 sessions; error bars are 95% t confidence intervals. "
        "Target latency 3 s; 300 s/session; mild clock handovers.",
        ha="center",
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.04, 1, 0.84))
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES / filename, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_improvement(aggregates: list[dict]) -> None:
    lookup = index_aggregates(aggregates)
    fig, axes = plt.subplots(1, 2, figsize=(11, 5))
    x = list(range(len(RATES)))
    width = 0.34
    for ax, transport in zip(axes, ("CUBIC", "BBR")):
        latency_reduction = []
        rebuffer_reduction = []
        for rate in RATES:
            old = lookup[(transport, rate, "old CMAB")]
            plus = lookup[(transport, rate, "CMAB+")]
            latency_reduction.append(100 * (old["latency_s"] - plus["latency_s"]) / old["latency_s"])
            if old["rebuffer_pct"] > 0:
                rebuffer_reduction.append(
                    100 * (old["rebuffer_pct"] - plus["rebuffer_pct"]) / old["rebuffer_pct"]
                )
            else:
                rebuffer_reduction.append(0)
        ax.bar(
            [point - width / 2 for point in x],
            latency_reduction,
            width,
            color=COLORS["CMAB+"],
            label="Latency reduction",
        )
        ax.bar(
            [point + width / 2 for point in x],
            rebuffer_reduction,
            width,
            color=COLORS["L2A"],
            label="Rebuffer reduction",
        )
        ax.axhline(0, color="black", linewidth=0.8)
        ax.set_title(transport)
        ax.set_xlabel("Configured bottleneck capacity (Mbit/s)")
        ax.set_xticks(x, [str(rate) for rate in RATES])
        ax.grid(axis="y", alpha=0.25)
    axes[0].set_ylabel("Reduction versus old CMAB (%)")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.925),
        ncols=2,
        frameon=False,
    )
    fig.suptitle("CMAB+ improvement over old CMAB", y=0.995, fontweight="bold")
    fig.text(
        0.5,
        -0.01,
        "Positive values favor CMAB+. Source: Review III capacity runs, 4 Nov 2026.",
        ha="center",
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.04, 1, 0.84))
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES / "cmab-plus-improvement.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


PLAYER_STYLES = {
    "old CMAB": {
        "color": "#c0392b",
        "marker": "o",
        "linestyle": "--",
        "label": "CMAB",
        "zorder": 2,
        "offset": -0.08,
    },
    "CMAB+": {
        "color": "#1f77b4",
        "marker": "s",
        "linestyle": "-",
        "label": "CMAB+",
        "zorder": 3,
        "offset": 0.08,
    },
}


def plot_review2_style_metric(
    aggregates: list[dict],
    field: str,
    error_field: str,
    ylabel: str,
    title: str,
    filename: str,
    *,
    zoom: bool,
) -> None:
    """Review II format: CUBIC panel and BBR panel, CMAB vs CMAB+ lines."""
    lookup = index_aggregates(aggregates)
    capacities = (1, 4, 8)
    xs = [float(value) for value in capacities]
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharex=True)
    fig.suptitle(
        f"{title} · {'zoomed Y' if zoom else 'full scale'}",
        fontsize=14,
        fontweight="bold",
    )

    for ax, transport in zip(axes, ("CUBIC", "BBR")):
        all_means = []
        for algorithm in ("old CMAB", "CMAB+"):
            style = PLAYER_STYLES[algorithm]
            means = [lookup[(transport, rate, algorithm)][field] for rate in capacities]
            errors = [
                lookup[(transport, rate, algorithm)][error_field]
                for rate in capacities
            ]
            all_means.extend(means)
            ax.errorbar(
                [x + style["offset"] for x in xs],
                means,
                yerr=errors,
                color=style["color"],
                marker=style["marker"],
                markersize=8,
                linewidth=2.5,
                capsize=4,
                linestyle=style["linestyle"],
                zorder=style["zorder"],
                label=style["label"],
            )

        ax.set_title(f"TCP {transport}", fontsize=12)
        ax.set_xticks(capacities)
        ax.set_xlabel("Bottleneck capacity (Mbit/s)")
        ax.grid(True, alpha=0.35)
        ax.legend(loc="best", fontsize=8)
        if zoom and all_means:
            low, high = min(all_means), max(all_means)
            span = high - low
            if field == "latency_s":
                pad = max(0.08 * span, 0.1)
            elif field == "bitrate_kbps":
                pad = max(0.08 * span, 100)
            else:
                pad = max(0.08 * span, 0.2)
            ax.set_ylim(max(0, low - pad), high + pad)

    axes[0].set_ylabel(ylabel)
    fig.text(
        0.5,
        0.01,
        "Mean ± sample SD over five 300 s sessions; 3 s target; mild clock handovers.",
        ha="center",
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.04, 1, 0.94))
    out_dir = FIGURES / "review2-style"
    out_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_dir / filename, dpi=200, bbox_inches="tight")
    plt.close(fig)


def write_summary(aggregates: list[dict]) -> None:
    lookup = index_aggregates(aggregates)
    lines = [
        "# Capacity experiment results",
        "",
        "All values are means of five 300 s sessions at a 3 s target. Latency and bitrate "
        "drop the first 20% of samples. Rebuffer is the post-trim fraction of buffer "
        "samples at or below 0.05 s.",
        "",
        "| TCP | Capacity | Player | Latency (s) | Rebuffer (%) | Bitrate (kbps) |",
        "| --- | ---: | --- | ---: | ---: | ---: |",
    ]
    for row in aggregates:
        lines.append(
            f"| {row['transport']} | {row['rate_mbit']} Mbit | {row['algorithm']} | "
            f"{row['latency_s']:.2f} | {row['rebuffer_pct']:.2f} | "
            f"{row['bitrate_kbps']:.0f} |"
        )

    lines += [
        "",
        "## Direct CMAB+ versus old CMAB",
        "",
        "| TCP | Capacity | Latency reduction | Rebuffer reduction |",
        "| --- | ---: | ---: | ---: |",
    ]
    for transport in ("CUBIC", "BBR"):
        for rate in RATES:
            old = lookup[(transport, rate, "old CMAB")]
            plus = lookup[(transport, rate, "CMAB+")]
            latency = 100 * (old["latency_s"] - plus["latency_s"]) / old["latency_s"]
            rebuffer = (
                100 * (old["rebuffer_pct"] - plus["rebuffer_pct"]) / old["rebuffer_pct"]
                if old["rebuffer_pct"] > 0
                else 0
            )
            lines.append(f"| {transport} | {rate} Mbit | {latency:.1f}% | {rebuffer:.1f}% |")

    lines += [
        "",
        "## Reading",
        "",
        "- **4 Mbit is the central result.** Under both CUBIC and BBR, old CMAB keeps "
        "requesting 6000 kbps and rebuffers 65.69–82.25%. CMAB+ selects about "
        "1475 kbps, reaches 3.54–3.62 s, and has 0% rebuffer. L2A is 3.36–3.40 s "
        "at 1500 kbps.",
        "- **1 Mbit shows a transport-dependent limit.** BBR CMAB+ matches L2A at "
        "450 kbps with 0% rebuffer. CUBIC CMAB+ chooses about 888 kbps and still "
        "rebuffers 16.54%; it remains much better than old CMAB but not competitive "
        "with L2A.",
        "- **8 Mbit is not an improvement.** The top rung nominally fits. CMAB+ is "
        "close to old CMAB, but both have multi-second latency and some rebuffer; "
        "L2A is better.",
        "- The result supports a narrow claim: throughput feasibility prevents old "
        "CMAB's forced-top-rung collapse when capacity lies below the top video rung. "
        "It does not establish that CMAB+ generally beats L2A.",
    ]
    (OUTPUT / "capacity-summary.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    session_rows = collect_sessions()
    if len(session_rows) != 90:
        raise SystemExit(f"Expected 90 sessions, found {len(session_rows)}")
    aggregates = aggregate(session_rows)
    if len(aggregates) != 18:
        raise SystemExit(f"Expected 18 aggregate rows, found {len(aggregates)}")

    write_csv(OUTPUT / "capacity-session-metrics.csv", session_rows)
    write_csv(OUTPUT / "capacity-aggregate-metrics.csv", aggregates)
    write_summary(aggregates)
    plot_metric(
        aggregates,
        "latency_s",
        "latency_s_ci95",
        "Mean live latency (s)",
        "Live latency under fixed link capacities",
        "capacity-latency.png",
    )
    plot_metric(
        aggregates,
        "rebuffer_pct",
        "rebuffer_pct_ci95",
        "Rebuffer samples (%)",
        "Rebuffering under fixed link capacities",
        "capacity-rebuffer.png",
    )
    plot_metric(
        aggregates,
        "bitrate_kbps",
        "bitrate_kbps_ci95",
        "Mean video bitrate (kbps)",
        "Video bitrate under fixed link capacities",
        "capacity-bitrate.png",
    )
    plot_improvement(aggregates)
    for field, error_field, ylabel, title, stem in (
        (
            "latency_s",
            "latency_s_sd",
            "Mean live latency (s)",
            "Live latency · CMAB vs CMAB+",
            "latency",
        ),
        (
            "bitrate_kbps",
            "bitrate_kbps_sd",
            "Mean bitrate (kbps)",
            "Bitrate · CMAB vs CMAB+",
            "bitrate",
        ),
        (
            "rebuffer_pct",
            "rebuffer_pct_sd",
            "Rebuffer sample ratio (%)",
            "Rebuffering · CMAB vs CMAB+",
            "rebuffer",
        ),
    ):
        plot_review2_style_metric(
            aggregates,
            field,
            error_field,
            ylabel,
            title,
            f"{stem}_cmab_vs_cmabplus_full.png",
            zoom=False,
        )
        plot_review2_style_metric(
            aggregates,
            field,
            error_field,
            ylabel,
            title,
            f"{stem}_cmab_vs_cmabplus_zoom.png",
            zoom=True,
        )
    print(f"Wrote {len(session_rows)} session rows and {len(aggregates)} aggregate rows")
    print(f"Results: {OUTPUT}")
    print(f"Figures: {FIGURES}")


if __name__ == "__main__":
    main()
