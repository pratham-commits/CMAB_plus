#!/usr/bin/env bash
# 160×300 s BBR matrix on GCP with SHAPER=clock (Review I–comparable emulation).
# Run from ~/mmsys24-starlink-livestreaming in tmux. ~13–14 h wall time.
#
# Output: figures/emulation-bbr-clock/  (does NOT overwrite figures/emulation-bbr/)
#
# Prerequisites on VM:
#   - Fixed runner/tc-trace.py, shaper/run-shaper.sh, supervisord → run-shaper.sh
#   - experiments/batch-emulation.json (160 jobs, MPD_URL uses https://nginx/...)
#   - experiments/compose-shaper-clock.override.yaml
#   - experiments/compose-bbr-160-clock.override.yaml (this script can create it)

set -euo pipefail

REPO_ROOT="${REPO_ROOT:-${HOME}/mmsys24-starlink-livestreaming}"
cd "${REPO_ROOT}"

COMPOSE_BBR="docker-compose-emulation-bbr.yaml"
OVERRIDE_SHAPER="experiments/compose-shaper-clock.override.yaml"
OVERRIDE_PROD="experiments/compose-bbr-160-clock.override.yaml"
BATCH="experiments/batch-emulation.json"
FIG_SUBDIR="emulation-bbr-clock"
NGINX="dashjs-nginx"
RUNNER="dashjs-runner"

log() { printf '==> %s\n' "$*"; }

if docker info >/dev/null 2>&1; then DOCKER=(docker); else DOCKER=(sudo docker); fi
compose() { "${DOCKER[@]}" compose "$@"; }

write_prod_override() {
  cat >"${OVERRIDE_PROD}" <<EOF
# 160-run BBR production matrix → figures/${FIG_SUBDIR}/
services:
  runner:
    volumes:
      - ./experiments/batch-emulation.json:/batch.json
    environment:
      - WORKDIR=\${PWD}
      - VIDEO=0
      - EMULATION_FIGURES_SUBDIR=${FIG_SUBDIR}
EOF
}

shaper_check() {
  local cc expect_cc="${1:-bbr}"
  cc="$("${DOCKER[@]}" exec "${NGINX}" cat /proc/sys/net/ipv4/tcp_congestion_control 2>/dev/null || true)"
  local sh="${SHAPER:-}$("${DOCKER[@]}" exec "${NGINX}" printenv SHAPER 2>/dev/null || true)"
  local tc="$("${DOCKER[@]}" exec "${NGINX}" tc qdisc show dev eth0 2>/dev/null | head -1 || true)"
  log "SHAPER=${sh} CC=${cc} tc=${tc}"
  [[ "${sh}" == "clock" ]] || { echo "FAIL: SHAPER must be clock"; return 1; }
  [[ "${cc}" == "${expect_cc}" ]] || echo "WARNING: expected CC ${expect_cc}, got ${cc}"
  echo "${tc}" | grep -q tbf || { echo "FAIL: expected tbf (tc.py), not trace htb"; return 1; }
}

preflight() {
  [[ -f "${BATCH}" ]] || { echo "Missing ${BATCH}"; exit 1; }
  [[ -f "${OVERRIDE_SHAPER}" ]] || { echo "Missing ${OVERRIDE_SHAPER}"; exit 1; }
  grep -q 'https://nginx/' "${BATCH}" || echo "WARNING: batch may not use https://nginx/ MPD_URL"
  write_prod_override
  log "Building nginx (embeds tc-trace fix + run-shaper)..."
  compose -f "${COMPOSE_BBR}" -f "${OVERRIDE_SHAPER}" -f "${OVERRIDE_PROD}" build nginx
  if command -v modprobe >/dev/null 2>&1; then
    sudo modprobe tcp_bbr 2>/dev/null || true
  fi
}

start_stack() {
  compose -f "${COMPOSE_BBR}" -f "${OVERRIDE_SHAPER}" -f "${OVERRIDE_PROD}" \
    up -d stat-server mongo dashjs pyodide livesim2 chrome nginx mongo-express
  log "Waiting for Selenium grid..."
  local i
  for i in $(seq 1 60); do
    if curl -sf http://127.0.0.1:4444/status | grep -q '"ready":true'; then
      log "Grid ready (${i})"
      break
    fi
    sleep 5
  done
  shaper_check bbr
}

start_runner() {
  compose -f "${COMPOSE_BBR}" -f "${OVERRIDE_SHAPER}" -f "${OVERRIDE_PROD}" \
    up -d --force-recreate runner
  log "Follow logs: docker logs -f ${RUNNER}"
}

count_done() {
  local root="figures/${FIG_SUBDIR}"
  if [[ ! -d "${root}/target-3s" ]]; then
    echo 0
    return
  fi
  find "${root}" -type f -name playback_latency.json 2>/dev/null | wc -l | tr -d ' '
}

case "${1:-run}" in
  preflight) preflight ;;
  stack) preflight; start_stack ;;
  run)
    preflight
    start_stack
    start_runner
    ;;
  count)
    n="$(count_done)"
    log "playback_latency.json count: ${n} (expect 160 when done)"
    ;;
  *)
    echo "Usage: $0 {preflight|stack|run|count}"
    exit 1
    ;;
esac
