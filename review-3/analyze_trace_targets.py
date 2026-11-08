#!/usr/bin/env python3
"""Score Starlink-trace target runs and plot CMAB vs CMAB+.

SHAPER=trace (isl-trace.csv). Targets 3/4/5/6 s.
Metrics match Review II / capacity analysis.
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
    "CUBIC": ROOT / "data" / "trace-targets-cubic",
    "BBR": ROOT / "data" / "trace-targets-bbr",
}
OUTPUT = ROOT / "results"
FIGURES = ROOT / "figures" / "trace-targets"
TARGETS = (3, 4, 5, 6)
ALGORITHMS = ("old CMAB", "CMAB+", "L2A")
PLAYER_STYLES = {
    "old CMAB": {
        "color": "#c0392b",
        "marker": "o",
        "linestyle": "--",
        "label": "CMAB",
        "offset": -0.06,
        "zorder": 2,
    },
    "CMAB+": {
        "color": "#1f77b4",
        "marker": "s",
        "linestyle": "-",
        "label": "CMAB+",
        "offset": 0.06,
        "zorder": 3,
    },
}
SESSION_RE = re.compile(
    r"^(abrCMABPlus|abrCMAB|abrL2A)-.*-target-latency-(\d+)s-"
    r"duration-(\d+)-bitrate-variable-(\d+)$"
)
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
        if not root.exists():
            continue
        for latency_file in sorted(root.glob("**/playback_latency.json")):
            session = latency_file.parent
            match = SESSION_RE.match(session.name)
            if not match:
                continue
            raw_algorithm, target, duration, round_id = match.groups()
            rows.append(
                {
                    "transport": transport,
                    "target_s": int(target),
                    "algorithm": algorithm_name(raw_algorithm),
                    "round": int(round_id),
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
        groups[(row["transport"], row["target_s"], row["algorithm"])].append(row)

    output = []
    for (transport, target, algorithm), sessions in groups.items():
        result = {
            "transport": transport,
            "target_s": target,
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
            row["target_s"],
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
    return {(row["transport"], row["target_s"], row["algorithm"]): row for row in rows}


def plot_cmab_vs_cmabplus(
    aggregates: list[dict],
    field: str,
    error_field: str,
    ylabel: str,
    title: str,
    filename: str,
    *,
    zoom: bool,
) -> None:
    lookup = index_aggregates(aggregates)
    transports = sorted({row["transport"] for row in aggregates}, key=["CUBIC", "BBR"].index)
    if not transports:
        return
    fig, axes = plt.subplots(1, len(transports), figsize=(6 * len(transports), 5), sharex=True)
    if len(transports) == 1:
        axes = [axes]
    fig.suptitle(
        f"{title} · {'zoomed Y' if zoom else 'full scale'}",
        fontsize=14,
        fontweight="bold",
    )
    xs = [float(t) for t in TARGETS]
    for ax, transport in zip(axes, transports):
        all_means = []
        for algorithm in ("old CMAB", "CMAB+"):
            style = PLAYER_STYLES[algorithm]
            means = [lookup[(transport, target, algorithm)][field] for target in TARGETS]
            errors = [lookup[(transport, target, algorithm)][error_field] for target in TARGETS]
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
        ax.set_xticks(TARGETS)
        ax.set_xlabel("Target live latency (s)")
        ax.grid(True, alpha=0.35)
        ax.legend(loc="best", fontsize=8)
        if zoom and all_means:
            # Zoom around CMAB+ only so old CMAB collapse does not flatten the win.
            plus_means = [lookup[(transport, target, "CMAB+")][field] for target in TARGETS]
            low, high = min(plus_means), max(plus_means)
            span = high - low
            if field == "latency_s":
                pad = max(0.08 * span, 0.15)
            elif field == "bitrate_kbps":
                pad = max(0.08 * span, 50)
            else:
                pad = max(0.08 * span, 0.5)
            ax.set_ylim(max(0, low - pad), high + pad)
    axes[0].set_ylabel(ylabel)
    fig.text(
        0.5,
        0.01,
        "Starlink ISL trace (SHAPER=trace). Mean ± sample SD over five 300 s sessions.",
        ha="center",
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.04, 1, 0.94))
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES / filename, dpi=200, bbox_inches="tight")
    plt.close(fig)


def write_summary(aggregates: list[dict]) -> None:
    lookup = index_aggregates(aggregates)
    lines = [
        "# Trace target results",
        "",
        "Real Starlink ISL trace (SHAPER=trace, handover loss 100%). "
        "Means of five 300 s sessions. Latency and bitrate drop the first 20% of samples. "
        "Rebuffer is the post-trim fraction of buffer samples at or below 0.05 s.",
        "",
        "| TCP | Target | Player | Latency (s) | Rebuffer (%) | Bitrate (kbps) |",
        "| --- | ---: | --- | ---: | ---: | ---: |",
    ]
    for row in aggregates:
        lines.append(
            f"| {row['transport']} | {row['target_s']} s | {row['algorithm']} | "
            f"{row['latency_s']:.2f} | {row['rebuffer_pct']:.2f} | "
            f"{row['bitrate_kbps']:.0f} |"
        )

    lines += [
        "",
        "## CMAB+ versus old CMAB",
        "",
        "| TCP | Target | Δ latency (s) | Latency change | Rebuffer change | Bitrate change |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for transport in sorted({row["transport"] for row in aggregates}, key=["CUBIC", "BBR"].index):
        for target in TARGETS:
            old = lookup[(transport, target, "old CMAB")]
            plus = lookup[(transport, target, "CMAB+")]
            dlat = plus["latency_s"] - old["latency_s"]
            lat_pct = 100 * dlat / old["latency_s"] if old["latency_s"] else 0
            if old["rebuffer_pct"] > 0:
                rebuf_pct = 100 * (plus["rebuffer_pct"] - old["rebuffer_pct"]) / old["rebuffer_pct"]
            else:
                rebuf_pct = plus["rebuffer_pct"] - old["rebuffer_pct"]
            dbr = plus["bitrate_kbps"] - old["bitrate_kbps"]
            lines.append(
                f"| {transport} | {target} s | {dlat:+.2f} | {lat_pct:+.1f}% | "
                f"{rebuf_pct:+.1f}% | {dbr:+.0f} kbps |"
            )

    lines += [
        "",
        "## Reading",
        "",
        "- Pass vs old CMAB if rebuffer and latency drop without locking at 6000 kbps.",
        "- Not a pass vs L2A unless CMAB+ is near the target with near-zero rebuffer.",
        "- Fail if CMAB+ collapses to a few hundred kbps the way a latency-only step-down did.",
    ]
    (OUTPUT / "trace-targets-summary.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    session_rows = collect_sessions()
    if not session_rows:
        raise SystemExit("No trace target sessions found under review-3/data/")
    by_transport = defaultdict(int)
    for row in session_rows:
        by_transport[row["transport"]] += 1
    for transport, count in by_transport.items():
        if count != 60:
            raise SystemExit(f"Expected 60 sessions for {transport}, found {count}")

    aggregates = aggregate(session_rows)
    write_csv(OUTPUT / "trace-targets-session-metrics.csv", session_rows)
    write_csv(OUTPUT / "trace-targets-aggregate-metrics.csv", aggregates)
    write_summary(aggregates)

    for field, error_field, ylabel, title, stem in (
        ("latency_s", "latency_s_sd", "Mean live latency (s)", "Live latency · CMAB vs CMAB+", "latency"),
        ("rebuffer_pct", "rebuffer_pct_sd", "Rebuffer sample ratio (%)", "Rebuffering · CMAB vs CMAB+", "rebuffer"),
        ("bitrate_kbps", "bitrate_kbps_sd", "Mean bitrate (kbps)", "Bitrate · CMAB vs CMAB+", "bitrate"),
    ):
        plot_cmab_vs_cmabplus(
            aggregates, field, error_field, ylabel, title, f"{stem}_cmab_vs_cmabplus_full.png", zoom=False
        )
        plot_cmab_vs_cmabplus(
            aggregates, field, error_field, ylabel, title, f"{stem}_cmab_vs_cmabplus_zoom.png", zoom=True
        )

    print(f"Wrote {len(session_rows)} session rows and {len(aggregates)} aggregate rows")
    print(f"Transports: {dict(by_transport)}")
    print(f"Results: {OUTPUT}")
    print(f"Figures: {FIGURES}")


if __name__ == "__main__":
    main()
