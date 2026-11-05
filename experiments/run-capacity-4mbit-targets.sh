#!/usr/bin/env bash
# Target robustness at the 4 Mbit win point: old CMAB, CMAB+, L2A.
# Targets 3/4/5/6 s, five rounds. Fixed 4 Mbit clock (handover rate stays 4;
# mild 100 ms / 1% loss bump). 60 sessions per congestion control
# (~5 h video, ~6 h wall).
#
# Usage, on the GCP VM, repo root, inside tmux:
#   ./experiments/run-capacity-4mbit-targets.sh cubic
#   ./experiments/run-capacity-4mbit-targets.sh bbr
#
# Figures:
#   figures/emulation-capacity-4mbit-targets-cubic/
#   figures/emulation-capacity-4mbit-targets-bbr/
#
# Do not reuse figures/emulation-capacity-*-4mbit/ (those are the 3 s-only
# decision cells).
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

RATE=4
OVERRIDE_SHAPER="experiments/compose-shaper-clock.override.yaml"
OVERRIDE_PROD="experiments/compose-capacity-4mbit-targets-${CC}.override.yaml"
BATCH="experiments/batch-capacity-4mbit-targets.json"
FIG_SUBDIR="emulation-capacity-4mbit-targets-${CC}"
NGINX="dashjs-nginx"
RUNNER="dashjs-runner"
EXPECT=60

log() { printf '==> %s\n' "$*"; }

if docker info >/dev/null 2>&1; then DOCKER=(docker); else DOCKER=(sudo docker); fi
compose() { "${DOCKER[@]}" compose "$@"; }
compose_files() {
  # Do not include compose-cmab-plus.override.yaml. That file sets CMAB_HARDENED=1
  # on every abrCMAB session, which would erase old CMAB from this batch.
  compose -f "${COMPOSE}" -f "${OVERRIDE_SHAPER}" -f "${OVERRIDE_PROD}" "$@"
}

write_prod_override() {
  cat >"${OVERRIDE_PROD}" <<EOF
# Capacity 4 Mbit targets (${CC}) → figures/${FIG_SUBDIR}/
# Rate stays ${RATE} Mbit through the mild handover bump.
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
    environment:
      SHAPER: "clock"
      TCP_CONGESTION_CONTROL: "${CC}"
      CLOCK_RATE_MBIT: "${RATE}"
      CLOCK_HANDOVER_RATE_MBIT: "${RATE}"
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
  load_tcp_bbr || true
  local cc sh tc requested clock_rate clock_handover
  cc="$("${DOCKER[@]}" exec "${NGINX}" cat /proc/sys/net/ipv4/tcp_congestion_control 2>/dev/null || true)"
  sh="$("${DOCKER[@]}" exec "${NGINX}" printenv SHAPER 2>/dev/null || true)"
  tc="$("${DOCKER[@]}" exec "${NGINX}" tc qdisc show dev eth0 2>/dev/null | head -1 || true)"
  requested="$("${DOCKER[@]}" exec "${NGINX}" printenv TCP_CONGESTION_CONTROL 2>/dev/null || true)"
  clock_rate="$("${DOCKER[@]}" exec "${NGINX}" printenv CLOCK_RATE_MBIT 2>/dev/null || true)"
  clock_handover="$("${DOCKER[@]}" exec "${NGINX}" printenv CLOCK_HANDOVER_RATE_MBIT 2>/dev/null || true)"
  log "SHAPER=${sh} requested=${requested} CC=${cc} CLOCK_RATE_MBIT=${clock_rate} CLOCK_HANDOVER_RATE_MBIT=${clock_handover} tc=${tc}"
  [[ "${requested}" == "${CC}" ]] || { echo "FAIL: container env TCP_CONGESTION_CONTROL=${requested}, want ${CC}"; return 1; }
  [[ "${sh}" == "clock" ]] || { echo "FAIL: SHAPER must be clock (got '${sh}')"; return 1; }
  [[ "${cc}" == "${CC}" ]] || { echo "FAIL: expected tcp_congestion_control=${CC}, got '${cc}'"; return 1; }
  [[ "${clock_rate}" == "${RATE}" ]] || { echo "FAIL: CLOCK_RATE_MBIT=${clock_rate}, want ${RATE}"; return 1; }
  [[ "${clock_handover}" == "${RATE}" ]] || { echo "FAIL: CLOCK_HANDOVER_RATE_MBIT=${clock_handover}, want ${RATE}"; return 1; }
  echo "${tc}" | grep -q tbf || { echo "FAIL: expected tbf qdisc from tc.py (clock), got: ${tc}"; return 1; }
  echo "${tc}" | grep -Eq "rate ${RATE}[Mm]bit" || { echo "FAIL: tc rate is not ${RATE} mbit: ${tc}"; return 1; }
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
  [[ -f Dockerfile-dashjs-local ]] || { echo "Missing Dockerfile-dashjs-local"; exit 1; }
  grep -q 'isCurrentAboveThroughput' dash.js/src/streaming/rules/abr/cmab/CMABAbrController.js \
    || { echo "FAIL: throughput step-down is not in this checkout"; exit 1; }
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
  log "Starting ${CC} at ${RATE} Mbit, targets 3/4/5/6 → figures/${FIG_SUBDIR}/ (${EXPECT} sessions)"
  write_prod_override
  compose_files up -d --force-recreate --no-deps nginx
  sleep 2
  shaper_check
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
log "Capacity 4 Mbit targets finished for ${CC}"
