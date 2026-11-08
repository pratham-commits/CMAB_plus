#!/usr/bin/env bash
# 4-run validation on GCP VM: CUBIC vs BBR × (abrCMAB + abrDynamic) @ target 3s, 300s.
# Run from the patched mmsys24-starlink-livestreaming repo root (Linux / Cloud SSH).
#
# Default repo: ~/mmsys24-starlink-livestreaming
# If you only have this script from the course repo, paste it on the VM and run;
# the batch JSON is embedded below when experiments/batch-validation-cubic-bbr.json is missing.
#
# Optional: copy verify_cmab_claims.py from review-ii-bbr-extension/scripts/ to
#   ~/mmsys24-starlink-livestreaming/scripts/verify_cmab_claims.py
#
# On GCP VM SSH (no scp): paste this entire file with:
#   cd ~/mmsys24-starlink-livestreaming
#   nano run-validation-gcp.sh   # paste, save
#   chmod +x run-validation-gcp.sh && bash run-validation-gcp.sh

set -euo pipefail

REPO_ROOT="${REPO_ROOT:-${HOME}/mmsys24-starlink-livestreaming}"
BATCH_REL="experiments/batch-validation-cubic-bbr.json"
COMPOSE_CUBIC="docker-compose-emulation.yaml"
COMPOSE_BBR="docker-compose-emulation-bbr.yaml"
OVERRIDE_CUBIC="experiments/compose-validation-cubic.override.yaml"
OVERRIDE_BBR="experiments/compose-validation-bbr.override.yaml"
NGINX_CONTAINER="${NGINX_CONTAINER:-dashjs-nginx}"
RUNNER_CONTAINER="${RUNNER_CONTAINER:-dashjs-runner}"

# Use sudo when the current user cannot talk to the Docker daemon.
if docker info >/dev/null 2>&1; then
  DOCKER=(docker)
else
  DOCKER=(sudo docker)
fi

compose() {
  "${DOCKER[@]}" compose "$@"
}

log() {
  printf '==> %s\n' "$*"
}

ensure_repo() {
  if [[ ! -d "${REPO_ROOT}" ]]; then
    echo "Repo not found at ${REPO_ROOT}. Clone patched stack first, e.g.:" >&2
    echo "  git clone <your-patched-mmsys24-starlink-livestreaming> ~/mmsys24-starlink-livestreaming" >&2
    exit 1
  fi
  cd "${REPO_ROOT}"
  log "Working directory: $(pwd)"
  for f in "${COMPOSE_CUBIC}" "${COMPOSE_BBR}"; do
    if [[ ! -f "${f}" ]]; then
      echo "Missing ${f} under ${REPO_ROOT} (need BBR-patched vendor clone)." >&2
      exit 1
    fi
  done
}

ensure_tcp_bbr_on_host() {
  log "Ensuring tcp_bbr is available on the VM host (for BBR nginx namespace)"
  if [[ -f /proc/modules ]] && grep -q '^tcp_bbr ' /proc/modules 2>/dev/null; then
    log "tcp_bbr already loaded on host"
    return 0
  fi
  if command -v modprobe >/dev/null 2>&1; then
    sudo modprobe tcp_bbr 2>/dev/null || true
  fi
  if grep -q tcp_bbr /proc/modules 2>/dev/null || lsmod 2>/dev/null | grep -q tcp_bbr; then
    log "tcp_bbr loaded"
  else
    echo "WARNING: tcp_bbr not loaded on host; BBR run may fail inside nginx container." >&2
  fi
  if command -v sysctl >/dev/null 2>&1; then
    sudo sysctl -w net.core.default_qdisc=fq >/dev/null 2>&1 || true
  fi
}

write_batch_json_if_missing() {
  local dest="${REPO_ROOT}/${BATCH_REL}"
  if [[ -f "${dest}" ]]; then
    log "Using existing ${BATCH_REL}"
    return 0
  fi
  log "Writing ${BATCH_REL} (embedded 2-job validation matrix)"
  mkdir -p "$(dirname "${dest}")"
  cat >"${dest}" <<'EOF'
[
    {
        "EMULATION": true,
        "ROUND_DURATION": 300,
        "CMAB_ALPHA": 1.0,
        "TARGET_LATENCY": 3,
        "CONSTANT_VIDEO_BITRATE": -1,
        "TOTAL_ROUNDS": 1,
        "MPD_URL": "https://nginx/livesim2/vectors/switching_sets/12.5_25_50/ss1/2023-04-28/stream.mpd",
        "ABR_ALGORITHM": "abrCMAB",
        "CATCH_UP": "liveCatchupModeCMAB"
    },
    {
        "EMULATION": true,
        "ROUND_DURATION": 300,
        "CMAB_ALPHA": 1.0,
        "TARGET_LATENCY": 3,
        "CONSTANT_VIDEO_BITRATE": -1,
        "TOTAL_ROUNDS": 1,
        "MPD_URL": "https://nginx/livesim2/vectors/switching_sets/12.5_25_50/ss1/2023-04-28/stream.mpd",
        "ABR_ALGORITHM": "abrDynamic"
    }
]
EOF
}

write_compose_overrides() {
  log "Writing compose override files"
  cat >"${OVERRIDE_CUBIC}" <<'EOF'
# Validation: CUBIC sender, 2×300s jobs → figures/validation-cubic/
services:
  runner:
    volumes:
      - ./experiments/batch-validation-cubic-bbr.json:/batch.json
    environment:
      - WORKDIR=${PWD}
      - VIDEO=0
      - EMULATION_FIGURES_SUBDIR=validation-cubic
  nginx:
    environment:
      - TCP_CONGESTION_CONTROL=cubic
EOF

  cat >"${OVERRIDE_BBR}" <<'EOF'
# Validation: BBR sender (base file sets TCP_CONGESTION_CONTROL=bbr), 2×300s → figures/validation-bbr/
services:
  runner:
    volumes:
      - ./experiments/batch-validation-cubic-bbr.json:/batch.json
    environment:
      - WORKDIR=${PWD}
      - VIDEO=0
      - EMULATION_FIGURES_SUBDIR=validation-bbr
EOF
}

wait_for_nginx_cc() {
  local expect="${1:?expected cc}"
  local i cc=""
  for i in $(seq 1 90); do
    cc="$("${DOCKER[@]}" exec "${NGINX_CONTAINER}" cat /proc/sys/net/ipv4/tcp_congestion_control 2>/dev/null || true)"
    if [[ -n "${cc}" ]]; then
      log "nginx tcp_congestion_control=${cc} (expect ${expect})"
      if [[ "${cc}" != "${expect}" ]]; then
        echo "WARNING: expected ${expect}, got ${cc}" >&2
      fi
      return 0
    fi
    sleep 2
  done
  echo "ERROR: ${NGINX_CONTAINER} did not report tcp_congestion_control in time" >&2
  return 1
}

wait_for_runner() {
  local i status
  for i in $(seq 1 360); do
    status="$("${DOCKER[@]}" inspect -f '{{.State.Status}}' "${RUNNER_CONTAINER}" 2>/dev/null || echo missing)"
    case "${status}" in
      running) sleep 15 ;;
      exited)
        local code
        code="$("${DOCKER[@]}" inspect -f '{{.State.ExitCode}}' "${RUNNER_CONTAINER}")"
        if [[ "${code}" -eq 0 ]]; then
          log "${RUNNER_CONTAINER} exited 0"
          return 0
        fi
        echo "ERROR: ${RUNNER_CONTAINER} exited with code ${code}" >&2
        "${DOCKER[@]}" logs "${RUNNER_CONTAINER}" 2>&1 | tail -80 >&2 || true
        return 1
        ;;
      *)
        sleep 5
        ;;
    esac
  done
  echo "ERROR: timed out waiting for ${RUNNER_CONTAINER}" >&2
  return 1
}

count_sessions() {
  local subdir="${1:?figures subdir}"
  local root="figures/${subdir}/target-3s"
  if [[ ! -d "${root}" ]]; then
    echo "0"
    return 0
  fi
  find "${root}" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' '
}

run_stack() {
  local label="${1:?label}"
  local compose_file="${2:?compose}"
  local override_file="${3:?override}"
  local expect_cc="${4:?cc}"

  log "======== ${label} (expect TCP CC: ${expect_cc}) ========"
  log "Tearing down any previous stack"
  compose -f "${compose_file}" -f "${override_file}" down --remove-orphans 2>/dev/null || true

  log "Pulling images (ignore errors if already local)"
  compose -f "${compose_file}" -f "${override_file}" pull || true

  log "Starting stack"
  compose -f "${compose_file}" -f "${override_file}" up -d --force-recreate

  wait_for_nginx_cc "${expect_cc}"
  "${DOCKER[@]}" exec "${NGINX_CONTAINER}" cat /proc/sys/net/ipv4/tcp_congestion_control

  log "Recreating runner to ensure batch mount and env are applied"
  compose -f "${compose_file}" -f "${override_file}" up -d --force-recreate runner

  log "Waiting for runner (~2×300s plus startup; may take 15–25 min)"
  wait_for_runner

  local subdir
  if [[ "${expect_cc}" == "cubic" ]]; then
    subdir="validation-cubic"
  else
    subdir="validation-bbr"
  fi
  local n
  n="$(count_sessions "${subdir}")"
  log "${label} complete: ${n} session dir(s) under figures/${subdir}/target-3s (expect 2)"
  find "figures/${subdir}" -type f -name 'qoe.json' 2>/dev/null | head -20 || true
  "${DOCKER[@]}" logs "${RUNNER_CONTAINER}" 2>&1 | tail -30 || true
}

run_verify_if_present() {
  local verify=""
  for verify in \
    "${REPO_ROOT}/scripts/verify_cmab_claims.py" \
    "${REPO_ROOT}/review-ii-bbr-extension/scripts/verify_cmab_claims.py"; do
    if [[ -f "${verify}" ]]; then
      log "Running $(basename "${verify}")"
      python3 "${verify}" \
        --label CUBIC --root "${REPO_ROOT}/figures/validation-cubic" \
        --label BBR --root "${REPO_ROOT}/figures/validation-bbr" \
        --target 3 --duration 300
      return 0
    fi
  done

  log "verify_cmab_claims.py not found; printing quick JSON sanity check"
  python3 <<'PY'
import json, statistics
from pathlib import Path

def summarize(root, abr):
    base = Path(root) / "target-3s"
    if not base.is_dir():
        print(f"  {root}: missing {base}")
        return
    dirs = [d for d in sorted(base.iterdir()) if d.is_dir() and abr in d.name]
    print(f"  {root} {abr}: n={len(dirs)}")
    for d in dirs[:3]:
        pl = json.loads((d / "playback_latency.json").read_text())
        vals = list(map(float, pl.values()))
        trim = vals[len(vals)//5:] if len(vals) >= 10 else vals
        print(f"    {d.name}: mean_latency={statistics.mean(trim):.3f}s")

for cc, sub in [("CUBIC", "validation-cubic"), ("BBR", "validation-bbr")]:
    print(f"\n=== {cc} ===")
    for abr in ("abrCMAB", "abrDynamic"):
        summarize(f"figures/{sub}", abr)
PY
}

main() {
  ensure_repo
  ensure_tcp_bbr_on_host
  write_batch_json_if_missing
  write_compose_overrides

  log "Batch jobs: $(python3 -c "import json; print(len(json.load(open('${BATCH_REL}'))))") (expect 2)"
  log "Estimated wall time: ~2×(2×300s) ≈ 20–30 minutes plus image pull"

  run_stack "Run 1/2 — CUBIC" "${COMPOSE_CUBIC}" "${OVERRIDE_CUBIC}" cubic
  run_stack "Run 2/2 — BBR" "${COMPOSE_BBR}" "${OVERRIDE_BBR}" bbr

  run_verify_if_present
  log "All validation runs finished."
  log "Artifacts: figures/validation-cubic/ and figures/validation-bbr/"
}

main "$@"
