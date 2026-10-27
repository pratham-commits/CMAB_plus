#!/usr/bin/env bash
# SHAPER=trace (default): isl-trace.csv via tc-trace.py — paper trace-driven path.
# SHAPER=clock: wall-clock handover at 12/27/42/57 via tc.py — matches many Review I pulls.
set -euo pipefail
mode="${SHAPER:-trace}"
case "$mode" in
  trace) exec python3 /tc-trace.py ;;
  clock) exec python3 /tc.py ;;
  *)
    echo "Unknown SHAPER=${mode}; use trace or clock" >&2
    exit 1
    ;;
esac
