#!/usr/bin/env bash
# Full 160×300 s matrix with CMAB+ on abrCMAB only.
# Other ABRs in batch-emulation.json are unchanged.
#
# Always uses SHAPER=clock (tc.py). Do not compare a trace-shaper run to Review I.
#
# Usage (on the GCP VM, repo root, inside tmux):
#   ./experiments/run-cmab-plus-160-clock.sh bbr
#   ./experiments/run-cmab-plus-160-clock.sh cubic
#   ./experiments/run-cmab-plus-160-clock.sh bbr count
#
# Outputs:
#   figures/emulation-cmab-plus-bbr/
#   figures/emulation-cmab-plus-cubic/
set -euo pipefail

CC="${1:-}"
ACTION="${2:-run}"
if [[ "${CC}" != "bbr" && "${CC}" != "cubic" ]]; then
  echo "Usage: $0 {bbr|cubic} [preflight|stack|run|count]" >&2
  exit 2
fi
if [[ "${ACTION}" == "count" || "${ACTION}" == "preflight" || "${ACTION}" == "stack" || "${ACTION}" == "run" ]]; then
  :
else
  # allow `$0 count` only when cc was passed: already handled
  echo "Usage: $0 {bbr|cubic} [preflight|stack|run|count]" >&2
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
OVERRIDE_CMAB="experiments/compose-cmab-plus.override.yaml"
OVERRIDE_PROD="experiments/compose-cmab-plus-${CC}.override.yaml"
BATCH="experiments/batch-emulation.json"
FIG_SUBDIR="emulation-cmab-plus-${CC}"
NGINX="dashjs-nginx"
RUNNER="dashjs-runner"

log() { printf '==> %s\n' "$*"; }

if docker info >/dev/null 2>&1; then DOCKER=(docker); else DOCKER=(sudo docker); fi
compose() { "${DOCKER[@]}" compose "$@"; }
compose_files() {
  compose -f "${COMPOSE}" -f "${OVERRIDE_SHAPER}" -f "${OVERRIDE_CMAB}" -f "${OVERRIDE_PROD}" "$@"
}

write_prod_override() {
  cat >"${OVERRIDE_PROD}" <<EOF
# CMAB+ 160-run (${CC}) → figures/${FIG_SUBDIR}/
# Set both here. A later compose environment list replaces the earlier one,
# which previously dropped TCP_CONGESTION_CONTROL and left the sender on cubic.
services:
  nginx:
    privileged: true
    cap_add:
      - NET_ADMIN
      - SYS_ADMIN
    environment:
      SHAPER: "clock"
      TCP_CONGESTION_CONTROL: "${CC}"
  runner:
    volumes:
      - ./experiments/batch-emulation.json:/batch.json
    environment:
      - WORKDIR=\${PWD}
      - VIDEO=0
      - EMULATION_FIGURES_SUBDIR=${FIG_SUBDIR}
      - CMAB_HARDENED=1
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
  local cc
  cc="$("${DOCKER[@]}" exec "${NGINX}" cat /proc/sys/net/ipv4/tcp_congestion_control 2>/dev/null || true)"
  local sh
  sh="$("${DOCKER[@]}" exec "${NGINX}" printenv SHAPER 2>/dev/null || true)"
  local tc
  tc="$("${DOCKER[@]}" exec "${NGINX}" tc qdisc show dev eth0 2>/dev/null | head -1 || true)"
  local requested
  requested="$("${DOCKER[@]}" exec "${NGINX}" printenv TCP_CONGESTION_CONTROL 2>/dev/null || true)"
  log "SHAPER=${sh} requested=${requested} CC=${cc} tc=${tc}"
  [[ "${requested}" == "${CC}" ]] || { echo "FAIL: container env TCP_CONGESTION_CONTROL=${requested}, want ${CC}"; return 1; }
  [[ "${sh}" == "clock" ]] || { echo "FAIL: SHAPER must be clock (got '${sh}')"; return 1; }
  [[ "${cc}" == "${CC}" ]] || { echo "FAIL: expected tcp_congestion_control=${CC}, got '${cc}'"; return 1; }
  echo "${tc}" | grep -q tbf || { echo "FAIL: expected tbf qdisc from tc.py (clock), got: ${tc}"; return 1; }
}

preflight() {
  [[ -f "${BATCH}" ]] || { echo "Missing ${BATCH}"; exit 1; }
  [[ -f "${OVERRIDE_SHAPER}" ]] || { echo "Missing ${OVERRIDE_SHAPER}"; exit 1; }
  [[ -f "${OVERRIDE_CMAB}" ]] || { echo "Missing ${OVERRIDE_CMAB}"; exit 1; }
  [[ -f Dockerfile-dashjs-local ]] || { echo "Missing Dockerfile-dashjs-local"; exit 1; }
  grep -q 'cmabPlusPolicy' dash.js/src/streaming/rules/abr/cmab/CMABAbrController.js \
    || { echo "FAIL: CMAB+ source is not in this checkout"; exit 1; }
  write_prod_override
  log "Building dashjs (local CMAB+), runner, and nginx..."
  compose_files build dashjs runner nginx
  if [[ "${CC}" == "bbr" ]]; then
    sudo /sbin/modprobe tcp_bbr 2>/dev/null || sudo /usr/sbin/modprobe tcp_bbr 2>/dev/null || sudo modprobe tcp_bbr 2>/dev/null || true
  fi
}

start_stack() {
  compose_files up -d stat-server mongo dashjs pyodide livesim2 chrome mongo-express
  # The previous nginx container stays up across retries and keeps CUBIC.
  compose_files up -d --force-recreate --no-deps nginx
  log "Waiting for Selenium grid..."
  local i
  for i in $(seq 1 60); do
    if curl -sf http://127.0.0.1:4444/status | grep -q '"ready":true'; then
      log "Grid ready (${i})"
      break
    fi
    sleep 5
  done
  log "Waiting for dash.js dev server..."
  for i in $(seq 1 60); do
    if "${DOCKER[@]}" exec dashjs-runner true 2>/dev/null; then
      :
    fi
    if curl -sf -o /dev/null "http://127.0.0.1:$(${DOCKER[@]} port dashjs 3000 2>/dev/null | head -1 | awk -F: '{print $NF}')/" 2>/dev/null; then
      log "dash.js responded"
      break
    fi
    sleep 5
  done
  shaper_check
}

start_runner() {
  compose_files up -d --force-recreate runner
  log "Follow logs: docker logs -f ${RUNNER}"
  log "Figures: figures/${FIG_SUBDIR}/"
  log "abrCMAB sessions must be opened with cmabHardened=true (runner sets this)."
}

count_done() {
  local root="figures/${FIG_SUBDIR}"
  if [[ ! -d "${root}" ]]; then
    echo 0
    return
  fi
  find "${root}" -type f -name playback_latency.json 2>/dev/null | wc -l | tr -d ' '
}

case "${ACTION}" in
  preflight) preflight ;;
  stack) preflight; start_stack ;;
  run)
    preflight
    start_stack
    start_runner
    ;;
  count)
    n="$(count_done)"
    log "playback_latency.json count in figures/${FIG_SUBDIR}: ${n} (expect 160 when done)"
    ;;
esac
