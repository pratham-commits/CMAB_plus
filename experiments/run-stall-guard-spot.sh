#!/usr/bin/env bash
# 3 s spot check for the stall guard. Old CMAB, CMAB+, L2A. Five rounds.
# 15 sessions (~90 min wall). One congestion control at a time.
#
# Order:
#   ./experiments/run-stall-guard-spot.sh clock cubic
#   ./experiments/run-stall-guard-spot.sh clock bbr
#   ./experiments/run-stall-guard-spot.sh 4mbit cubic
#   ./experiments/run-stall-guard-spot.sh 4mbit bbr
#   ./experiments/run-stall-guard-spot.sh trace cubic
#
# Pass clock: CMAB+ still ~5 Mbps, ~0% rebuffer.
# Pass 4mbit: CMAB+ still ~1.5 Mbps, 0% rebuffer, latency ~3.5 s.
# Pass trace: CMAB+ rebuffer near L2A, bitrate near a few hundred kbps.
# Reject the rule if clock or 4mbit bitrate falls to a few hundred kbps.
set -euo pipefail

MODE="${1:-}"
CC="${2:-}"
if [[ "${MODE}" != "clock" && "${MODE}" != "4mbit" && "${MODE}" != "trace" ]]; then
  echo "Usage: $0 {clock|4mbit|trace} {bbr|cubic}" >&2
  exit 2
fi
if [[ "${CC}" != "bbr" && "${CC}" != "cubic" ]]; then
  echo "Usage: $0 {clock|4mbit|trace} {bbr|cubic}" >&2
  exit 2
fi

REPO_ROOT="${REPO_ROOT:-${HOME}/mmsys24-starlink-livestreaming}"
cd "${REPO_ROOT}"

if [[ "${CC}" == "bbr" ]]; then
  COMPOSE="docker-compose-emulation-bbr.yaml"
else
  COMPOSE="docker-compose-emulation.yaml"
fi

if [[ "${MODE}" == "trace" ]]; then
  OVERRIDE_SHAPER="experiments/compose-shaper-trace.override.yaml"
else
  OVERRIDE_SHAPER="experiments/compose-shaper-clock.override.yaml"
fi

OVERRIDE_PROD="experiments/compose-stall-spot-${MODE}-${CC}.override.yaml"
BATCH="experiments/batch-stall-guard-spot.json"
FIG_SUBDIR="emulation-stall-spot-${MODE}-${CC}"
NGINX="dashjs-nginx"
RUNNER="dashjs-runner"
EXPECT=15
TRACE_CSV="runner/trace/isl-trace.csv"

log() { printf '==> %s\n' "$*"; }

if docker info >/dev/null 2>&1; then DOCKER=(docker); else DOCKER=(sudo docker); fi
compose() { "${DOCKER[@]}" compose "$@"; }
compose_files() {
  compose -f "${COMPOSE}" -f "${OVERRIDE_SHAPER}" -f "${OVERRIDE_PROD}" "$@"
}

write_prod_override() {
  local shaper_env
  if [[ "${MODE}" == "trace" ]]; then
    shaper_env=$(cat <<EOF
      SHAPER: "trace"
      TCP_CONGESTION_CONTROL: "${CC}"
      HANDOVER_LOSS_PERCENT: "100"
EOF
)
  elif [[ "${MODE}" == "4mbit" ]]; then
    shaper_env=$(cat <<EOF
      SHAPER: "clock"
      TCP_CONGESTION_CONTROL: "${CC}"
      CLOCK_RATE_MBIT: "4"
      CLOCK_HANDOVER_RATE_MBIT: "4"
      CLOCK_LOSS_PERCENT: "0.1"
      CLOCK_HANDOVER_LOSS_PERCENT: "1"
      CLOCK_HANDOVER_DURATION: "0"
EOF
)
  else
    shaper_env=$(cat <<EOF
      SHAPER: "clock"
      TCP_CONGESTION_CONTROL: "${CC}"
      CLOCK_RATE_MBIT: "100"
      CLOCK_HANDOVER_RATE_MBIT: "50"
      CLOCK_LOSS_PERCENT: "0.1"
      CLOCK_HANDOVER_LOSS_PERCENT: "1"
      CLOCK_DELAY_MS: "40"
      CLOCK_HANDOVER_DELAY_MS: "100"
      CLOCK_HANDOVER_DURATION: "0"
EOF
)
  fi
  local trace_volume=""
  if [[ "${MODE}" == "trace" ]]; then
    trace_volume="    volumes:
      - ./${TRACE_CSV}:/trace/trace.csv:ro"
  fi
  cat >"${OVERRIDE_PROD}" <<EOF
# Stall-guard spot (${MODE}, ${CC}) → figures/${FIG_SUBDIR}/
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
${trace_volume}
    environment:
${shaper_env}
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
  local cc sh tc requested
  cc="$("${DOCKER[@]}" exec "${NGINX}" cat /proc/sys/net/ipv4/tcp_congestion_control 2>/dev/null || true)"
  sh="$("${DOCKER[@]}" exec "${NGINX}" printenv SHAPER 2>/dev/null || true)"
  tc="$("${DOCKER[@]}" exec "${NGINX}" tc qdisc show dev eth0 2>/dev/null | head -3 || true)"
  requested="$("${DOCKER[@]}" exec "${NGINX}" printenv TCP_CONGESTION_CONTROL 2>/dev/null || true)"
  log "SHAPER=${sh} requested=${requested} CC=${cc} tc=${tc}"
  [[ "${requested}" == "${CC}" ]] || { echo "FAIL: TCP_CONGESTION_CONTROL=${requested}, want ${CC}"; return 1; }
  [[ "${cc}" == "${CC}" ]] || { echo "FAIL: tcp_congestion_control=${cc}, want ${CC}"; return 1; }
  if [[ "${MODE}" == "trace" ]]; then
    [[ "${sh}" == "trace" ]] || { echo "FAIL: SHAPER=${sh}, want trace"; return 1; }
    echo "${tc}" | grep -qi htb || { echo "FAIL: expected HTB, got: ${tc}"; return 1; }
    echo "${tc}" | grep -qi tbf && { echo "FAIL: clock tbf leaked into trace: ${tc}"; return 1; }
    "${DOCKER[@]}" exec "${NGINX}" test -s /trace/trace.csv \
      || { echo "FAIL: /trace/trace.csv missing or empty inside nginx"; return 1; }
    # The trace loop prints every 10 ms, so the startup line can be late in docker logs.
    local i
    for i in $(seq 1 15); do
      if "${DOCKER[@]}" logs --tail 4000 "${NGINX}" 2>&1 | grep -q 'trace loaded:'; then
        log "trace loaded"
        break
      fi
      sleep 1
    done
    "${DOCKER[@]}" logs --tail 4000 "${NGINX}" 2>&1 | grep -q 'trace loaded:' \
      || log "trace loaded line not visible yet; HTB is up and trace.csv is present"
  else
    [[ "${sh}" == "clock" ]] || { echo "FAIL: SHAPER=${sh}, want clock"; return 1; }
    echo "${tc}" | grep -q tbf || { echo "FAIL: expected tbf, got: ${tc}"; return 1; }
    if [[ "${MODE}" == "4mbit" ]]; then
      echo "${tc}" | grep -Eq "rate 4[Mm]bit" || { echo "FAIL: tc rate is not 4 mbit: ${tc}"; return 1; }
    else
      echo "${tc}" | grep -Eq "rate 100[Mm]bit" || { echo "FAIL: tc rate is not 100 mbit: ${tc}"; return 1; }
    fi
  fi
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
  grep -q 'applyStallGuard' dash.js/src/streaming/rules/abr/cmab/CMABAbrController.js \
    || { echo "FAIL: stall guard is not in this checkout"; exit 1; }
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
  log "Stall-guard spot ${MODE} ${CC} → figures/${FIG_SUBDIR}/ (${EXPECT} sessions)"
  write_prod_override
  compose_files up -d --force-recreate --no-deps nginx
  sleep 3
  shaper_check
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
  log "runner CMAB_HARDENED=${hardened} (want 0)"
  [[ "${hardened}" == "0" ]] || { echo "FAIL: runner CMAB_HARDENED=${hardened}, want 0"; return 1; }
  local rc
  rc="$("${DOCKER[@]}" wait "${RUNNER}")"
  [[ "${rc}" == "0" ]] || { echo "FAIL: runner exited ${rc}" >&2; return 1; }
  "${DOCKER[@]}" logs "${RUNNER}" 2>&1 | grep -q 'Video Streaming completed' \
    || { echo "FAIL: runner exited without Video Streaming completed"; return 1; }
  local n
  n="$(count_done "figures/${FIG_SUBDIR}")"
  log "playback_latency.json count: ${n} (expect ${EXPECT})"
  [[ "${n}" == "${EXPECT}" ]] || { echo "FAIL: produced ${n}, want ${EXPECT}"; return 1; }
}

preflight
run_batch
log "Stall-guard spot finished for ${MODE} ${CC}"
