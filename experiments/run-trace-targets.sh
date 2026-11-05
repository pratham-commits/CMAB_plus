#!/usr/bin/env bash
# Trace validity: real Starlink ISL trace (SHAPER=trace, isl-trace.csv).
# Old CMAB, CMAB+, L2A. Targets 3/4/5/6 s, five rounds.
# 60 sessions per congestion control (~5 h video, ~6 h wall).
#
# Uses the fixed tc-trace.py (tc_del + HTB reinit). Handover rows keep the
# paper default HANDOVER_LOSS_PERCENT=100 unless overridden in the environment.
#
# Usage, on the GCP VM, repo root, inside tmux:
#   ./experiments/run-trace-targets.sh cubic
#   ./experiments/run-trace-targets.sh bbr
#
# Figures:
#   figures/emulation-trace-targets-cubic/
#   figures/emulation-trace-targets-bbr/
#
# Do not reuse earlier misconfigured trace folders as a baseline; old CMAB must
# be in this same batch.
set -euo pipefail

CC="${1:-}"
if [[ "${CC}" != "bbr" && "${CC}" != "cubic" ]]; then
  echo "Usage: $0 {bbr|cubic}" >&2
  exit 2
fi

REPO_ROOT="${REPO_ROOT:-${HOME}/mmsys24-starlink-livestreaming}"
cd "${REPO_ROOT}"

if [[ "${CC}" == "bbr" ]]; then
  COMPOSE="docker-compose-emulation-bbr.yaml"
else
  COMPOSE="docker-compose-emulation.yaml"
fi

OVERRIDE_SHAPER="experiments/compose-shaper-trace.override.yaml"
OVERRIDE_PROD="experiments/compose-trace-targets-${CC}.override.yaml"
BATCH="experiments/batch-trace-targets.json"
FIG_SUBDIR="emulation-trace-targets-${CC}"
NGINX="dashjs-nginx"
RUNNER="dashjs-runner"
EXPECT=60
TRACE_CSV="runner/trace/isl-trace.csv"

log() { printf '==> %s\n' "$*"; }

if docker info >/dev/null 2>&1; then DOCKER=(docker); else DOCKER=(sudo docker); fi
compose() { "${DOCKER[@]}" compose "$@"; }
compose_files() {
  # Do not include compose-cmab-plus.override.yaml. That file sets CMAB_HARDENED=1
  # on every abrCMAB session, which would erase old CMAB from this batch.
  # Do not include compose-shaper-clock.override.yaml — this run is SHAPER=trace.
  compose -f "${COMPOSE}" -f "${OVERRIDE_SHAPER}" -f "${OVERRIDE_PROD}" "$@"
}

write_prod_override() {
  cat >"${OVERRIDE_PROD}" <<EOF
# Trace targets (${CC}) → figures/${FIG_SUBDIR}/
# SHAPER=trace drives isl-trace.csv via tc-trace.py.
# Runner CMAB_HARDENED must stay 0. The batch JSON turns it on only for CMAB+.
services:
  dashjs:
    image: dashjs-cmab-plus:local
    build:
      context: .
      dockerfile: Dockerfile-dashjs-local
  runner:
    image: dashjs-runner-cmab-plus:local
    build:
      context: .
      dockerfile: Dockerfile-runner
    volumes:
      - ./${BATCH}:/batch.json
      - ./figures:/figures
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      - WORKDIR=\${PWD}
      - VIDEO=0
      - EMULATION_FIGURES_SUBDIR=${FIG_SUBDIR}
      - CMAB_HARDENED=0
  nginx:
    privileged: true
    cap_add:
      - NET_ADMIN
      - SYS_ADMIN
    volumes:
      - ./${TRACE_CSV}:/trace/trace.csv:ro
    environment:
      SHAPER: "trace"
      TCP_CONGESTION_CONTROL: "${CC}"
      HANDOVER_LOSS_PERCENT: "\${HANDOVER_LOSS_PERCENT:-100}"
EOF
}

load_tcp_bbr() {
  if [[ "${CC}" != "bbr" ]]; then
    return 0
  fi
  sudo /sbin/modprobe tcp_bbr 2>/dev/null || sudo /usr/sbin/modprobe tcp_bbr 2>/dev/null || sudo modprobe tcp_bbr 2>/dev/null || true
  "${DOCKER[@]}" exec "${NGINX}" /usr/sbin/sysctl -w net.ipv4.tcp_congestion_control=bbr >/dev/null
}

shaper_check() {
  load_tcp_bbr || true
  local cc sh tc requested loss
  cc="$("${DOCKER[@]}" exec "${NGINX}" cat /proc/sys/net/ipv4/tcp_congestion_control 2>/dev/null || true)"
  sh="$("${DOCKER[@]}" exec "${NGINX}" printenv SHAPER 2>/dev/null || true)"
  tc="$("${DOCKER[@]}" exec "${NGINX}" tc qdisc show dev eth0 2>/dev/null | head -3 || true)"
  requested="$("${DOCKER[@]}" exec "${NGINX}" printenv TCP_CONGESTION_CONTROL 2>/dev/null || true)"
  loss="$("${DOCKER[@]}" exec "${NGINX}" printenv HANDOVER_LOSS_PERCENT 2>/dev/null || true)"
  log "SHAPER=${sh} requested=${requested} CC=${cc} HANDOVER_LOSS_PERCENT=${loss} tc=${tc}"
  [[ "${requested}" == "${CC}" ]] || { echo "FAIL: container env TCP_CONGESTION_CONTROL=${requested}, want ${CC}"; return 1; }
  [[ "${sh}" == "trace" ]] || { echo "FAIL: SHAPER must be trace (got '${sh}')"; return 1; }
  [[ "${cc}" == "${CC}" ]] || { echo "FAIL: expected tcp_congestion_control=${CC}, got '${cc}'"; return 1; }
  echo "${tc}" | grep -qi htb || { echo "FAIL: expected HTB qdisc from tc-trace.py, got: ${tc}"; return 1; }
  echo "${tc}" | grep -qi tbf && { echo "FAIL: tbf present — clock shaper leaked into a trace run: ${tc}"; return 1; }
  "${DOCKER[@]}" logs "${NGINX}" 2>&1 | grep -q 'trace loaded:' \
    || { echo "FAIL: nginx logs missing 'trace loaded:' from tc-trace.py"; return 1; }
  "${DOCKER[@]}" exec "${NGINX}" test -s /trace/trace.csv \
    || { echo "FAIL: /trace/trace.csv missing or empty inside nginx"; return 1; }
}

wait_for_grid() {
  log "Waiting for Selenium grid..."
  local i body
  for i in $(seq 1 60); do
    body="$(curl -sf -m 3 http://127.0.0.1:4444/status || true)"
    if echo "${body}" | grep -Eq '"ready"[[:space:]]*:[[:space:]]*true'; then
      log "Grid ready (${i})"
      return 0
    fi
    sleep 5
  done
  echo "FAIL: Selenium grid did not become ready" >&2
  echo "Last /status: ${body:-<no response>}" >&2
  docker ps -a --filter name=chrome --format '{{.Names}} {{.Status}}' >&2 || true
  return 1
}

count_done() {
  local root="$1"
  if [[ ! -d "${root}" ]]; then
    echo 0
    return
  fi
  find "${root}" -type f -name playback_latency.json 2>/dev/null | wc -l | tr -d ' '
}

preflight() {
  [[ -f "${BATCH}" ]] || { echo "Missing ${BATCH}"; exit 1; }
  [[ -f "${OVERRIDE_SHAPER}" ]] || { echo "Missing ${OVERRIDE_SHAPER}"; exit 1; }
  [[ -f "${TRACE_CSV}" ]] || { echo "Missing ${TRACE_CSV}"; exit 1; }
  [[ -f Dockerfile-dashjs-local ]] || { echo "Missing Dockerfile-dashjs-local"; exit 1; }
  grep -q 'isCurrentAboveThroughput' dash.js/src/streaming/rules/abr/cmab/CMABAbrController.js \
    || { echo "FAIL: throughput step-down is not in this checkout"; exit 1; }
  grep -q 'def tc_del' runner/tc-trace.py \
    || { echo "FAIL: tc-trace.py missing tc_del (old broken init)"; exit 1; }
  write_prod_override
  log "Building dashjs (local CMAB+), runner, and nginx..."
  compose_files build dashjs runner nginx
  if [[ "${CC}" == "bbr" ]]; then
    sudo /sbin/modprobe tcp_bbr 2>/dev/null || sudo /usr/sbin/modprobe tcp_bbr 2>/dev/null || sudo modprobe tcp_bbr 2>/dev/null || true
  fi
  compose_files up -d stat-server mongo dashjs pyodide livesim2 chrome mongo-express
  wait_for_grid
}

run_batch() {
  log "Starting ${CC} SHAPER=trace, targets 3/4/5/6 → figures/${FIG_SUBDIR}/ (${EXPECT} sessions)"
  write_prod_override
  compose_files up -d --force-recreate --no-deps nginx
  sleep 3
  shaper_check
  "${DOCKER[@]}" logs "${NGINX}" 2>&1 | grep 'trace loaded:' | tail -n 1 || true
  compose_files restart chrome
  wait_for_grid
  compose_files up -d --force-recreate runner
  local hardened i
  hardened=""
  for i in $(seq 1 20); do
    hardened="$("${DOCKER[@]}" exec "${RUNNER}" printenv CMAB_HARDENED 2>/dev/null || true)"
    if [[ -n "${hardened}" ]]; then
      break
    fi
    sleep 1
  done
  log "runner CMAB_HARDENED=${hardened} (want 0; CMAB+ is selected by the batch JSON)"
  [[ "${hardened}" == "0" ]] || { echo "FAIL: runner CMAB_HARDENED=${hardened}, want 0 so old CMAB stays in the batch"; return 1; }
  log "Waiting for ${RUNNER} to finish (${EXPECT} sessions)..."
  local rc
  rc="$("${DOCKER[@]}" wait "${RUNNER}")"
  [[ "${rc}" == "0" ]] || {
    echo "FAIL: ${RUNNER} exited ${rc}" >&2
    "${DOCKER[@]}" logs --tail 40 "${RUNNER}" >&2 || true
    return 1
  }
  "${DOCKER[@]}" logs "${RUNNER}" 2>&1 | grep -q 'Video Streaming completed' \
    || { echo "FAIL: runner exited without Video Streaming completed"; return 1; }
  local n
  n="$(count_done "figures/${FIG_SUBDIR}")"
  log "playback_latency.json count in figures/${FIG_SUBDIR}: ${n} (expect ${EXPECT})"
  [[ "${n}" == "${EXPECT}" ]] || { echo "FAIL: produced ${n} sessions, want ${EXPECT}"; return 1; }
}

preflight
run_batch
log "Trace targets finished for ${CC}"
