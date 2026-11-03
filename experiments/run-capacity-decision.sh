#!/usr/bin/env bash
# Decision batch: old CMAB, CMAB+, L2A. 3 s target, 5 rounds, one link speed.
# 15 sessions per speed. Default speeds are 8, then 4, then 1 Mbit.
#
# The handover stays the paper's mild bump (100 ms, 1% loss) but the rate does
# not jump back up to 50 Mbit. One congestion control at a time.
#
# Usage, on the GCP VM, repo root, inside tmux:
#   ./experiments/run-capacity-decision.sh cubic
#   ./experiments/run-capacity-decision.sh bbr
#   ./experiments/run-capacity-decision.sh cubic 4
#
# Figures:
#   figures/emulation-capacity-cubic-8mbit/
#   figures/emulation-capacity-cubic-4mbit/
#   figures/emulation-capacity-cubic-1mbit/
#   and the same names with bbr.
set -euo pipefail

CC="${1:-}"
RATE_ARG="${2:-all}"
if [[ "${CC}" != "bbr" && "${CC}" != "cubic" ]]; then
  echo "Usage: $0 {bbr|cubic} [8|4|1|all]" >&2
  exit 2
fi
if [[ "${RATE_ARG}" == "all" ]]; then
  RATES=(8 4 1)
elif [[ "${RATE_ARG}" == "8" || "${RATE_ARG}" == "4" || "${RATE_ARG}" == "1" ]]; then
  RATES=("${RATE_ARG}")
else
  echo "Usage: $0 {bbr|cubic} [8|4|1|all]" >&2
  exit 2
fi

REPO_ROOT="${REPO_ROOT:-${HOME}/mmsys24-starlink-livestreaming}"
cd "${REPO_ROOT}"

if [[ "${CC}" == "bbr" ]]; then
  COMPOSE="docker-compose-emulation-bbr.yaml"
else
  COMPOSE="docker-compose-emulation.yaml"
fi

OVERRIDE_SHAPER="experiments/compose-shaper-clock.override.yaml"
OVERRIDE_PROD="experiments/compose-capacity-${CC}.override.yaml"
BATCH="experiments/batch-capacity-decision.json"
NGINX="dashjs-nginx"
RUNNER="dashjs-runner"
EXPECT=15

log() { printf '==> %s\n' "$*"; }

if docker info >/dev/null 2>&1; then DOCKER=(docker); else DOCKER=(sudo docker); fi
compose() { "${DOCKER[@]}" compose "$@"; }
compose_files() {
  # Do not include compose-cmab-plus.override.yaml. That file sets CMAB_HARDENED=1
  # on every abrCMAB session, which would erase old CMAB from this batch.
  compose -f "${COMPOSE}" -f "${OVERRIDE_SHAPER}" -f "${OVERRIDE_PROD}" "$@"
}

write_prod_override() {
  local rate="$1"
  local fig="$2"
  cat >"${OVERRIDE_PROD}" <<EOF
# Capacity decision (${CC}, ${rate} mbit) → figures/${fig}/
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
      - EMULATION_FIGURES_SUBDIR=${fig}
      - CMAB_HARDENED=0
  nginx:
    privileged: true
    cap_add:
      - NET_ADMIN
      - SYS_ADMIN
    environment:
      SHAPER: "clock"
      TCP_CONGESTION_CONTROL: "${CC}"
      CLOCK_RATE_MBIT: "${rate}"
      CLOCK_HANDOVER_RATE_MBIT: "${rate}"
      CLOCK_LOSS_PERCENT: "0.1"
      CLOCK_HANDOVER_LOSS_PERCENT: "1"
      CLOCK_HANDOVER_DURATION: "0"
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
  local rate="$1"
  load_tcp_bbr || true
  local cc sh tc requested clock_rate hardened
  cc="$("${DOCKER[@]}" exec "${NGINX}" cat /proc/sys/net/ipv4/tcp_congestion_control 2>/dev/null || true)"
  sh="$("${DOCKER[@]}" exec "${NGINX}" printenv SHAPER 2>/dev/null || true)"
  tc="$("${DOCKER[@]}" exec "${NGINX}" tc qdisc show dev eth0 2>/dev/null | head -1 || true)"
  requested="$("${DOCKER[@]}" exec "${NGINX}" printenv TCP_CONGESTION_CONTROL 2>/dev/null || true)"
  clock_rate="$("${DOCKER[@]}" exec "${NGINX}" printenv CLOCK_RATE_MBIT 2>/dev/null || true)"
  log "SHAPER=${sh} requested=${requested} CC=${cc} CLOCK_RATE_MBIT=${clock_rate} tc=${tc}"
  [[ "${requested}" == "${CC}" ]] || { echo "FAIL: container env TCP_CONGESTION_CONTROL=${requested}, want ${CC}"; return 1; }
  [[ "${sh}" == "clock" ]] || { echo "FAIL: SHAPER must be clock (got '${sh}')"; return 1; }
  [[ "${cc}" == "${CC}" ]] || { echo "FAIL: expected tcp_congestion_control=${CC}, got '${cc}'"; return 1; }
  [[ "${clock_rate}" == "${rate}" ]] || { echo "FAIL: CLOCK_RATE_MBIT=${clock_rate}, want ${rate}"; return 1; }
  echo "${tc}" | grep -q tbf || { echo "FAIL: expected tbf qdisc from tc.py (clock), got: ${tc}"; return 1; }
  echo "${tc}" | grep -Eq "rate ${rate}[Mm]bit" || { echo "FAIL: tc rate is not ${rate} mbit: ${tc}"; return 1; }
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

preflight() {
  [[ -f "${BATCH}" ]] || { echo "Missing ${BATCH}"; exit 1; }
  [[ -f "${OVERRIDE_SHAPER}" ]] || { echo "Missing ${OVERRIDE_SHAPER}"; exit 1; }
  [[ -f Dockerfile-dashjs-local ]] || { echo "Missing Dockerfile-dashjs-local"; exit 1; }
  grep -q 'isCurrentAboveThroughput' dash.js/src/streaming/rules/abr/cmab/CMABAbrController.js \
    || { echo "FAIL: throughput step-down is not in this checkout"; exit 1; }
  write_prod_override "${RATES[0]}" "emulation-capacity-${CC}-${RATES[0]}mbit"
  log "Building dashjs (local CMAB+), runner, and nginx..."
  compose_files build dashjs runner nginx
  if [[ "${CC}" == "bbr" ]]; then
    sudo /sbin/modprobe tcp_bbr 2>/dev/null || sudo /usr/sbin/modprobe tcp_bbr 2>/dev/null || sudo modprobe tcp_bbr 2>/dev/null || true
  fi
  compose_files up -d stat-server mongo dashjs pyodide livesim2 chrome mongo-express
  wait_for_grid
}

count_done() {
  local root="$1"
  if [[ ! -d "${root}" ]]; then
    echo 0
    return
  fi
  find "${root}" -type f -name playback_latency.json 2>/dev/null | wc -l | tr -d ' '
}

run_one_rate() {
  local rate="$1"
  local fig="emulation-capacity-${CC}-${rate}mbit"
  log "Starting ${CC} at ${rate} mbit → figures/${fig}/ (${EXPECT} sessions)"
  write_prod_override "${rate}" "${fig}"
  compose_files up -d --force-recreate --no-deps nginx
  sleep 2
  shaper_check "${rate}"
  "${DOCKER[@]}" logs "${NGINX}" 2>&1 | grep 'clock shaper:' | tail -n 1 || true
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
  log "Waiting for ${RUNNER} to finish ${rate} mbit..."
  local rc
  rc="$("${DOCKER[@]}" wait "${RUNNER}")"
  [[ "${rc}" == "0" ]] || {
    echo "FAIL: ${RUNNER} exited ${rc} during ${rate} mbit" >&2
    "${DOCKER[@]}" logs --tail 40 "${RUNNER}" >&2 || true
    return 1
  }
  "${DOCKER[@]}" logs "${RUNNER}" 2>&1 | grep -q 'Video Streaming completed' \
    || { echo "FAIL: ${rate} mbit runner exited without Video Streaming completed"; return 1; }
  local n
  n="$(count_done "figures/${fig}")"
  log "playback_latency.json count in figures/${fig}: ${n} (expect ${EXPECT})"
  [[ "${n}" == "${EXPECT}" ]] || { echo "FAIL: ${rate} mbit produced ${n} sessions, want ${EXPECT}"; return 1; }
}

preflight
for rate in "${RATES[@]}"; do
  run_one_rate "${rate}"
done
log "Capacity decision finished for ${CC}: ${RATES[*]} mbit"
