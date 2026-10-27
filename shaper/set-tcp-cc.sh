#!/usr/bin/env bash
# Set default TCP congestion control for this container network namespace (sender = Nginx HTTPS).
# Usage: TCP_CONGESTION_CONTROL=bbr| cubic  (default: cubic)

set -euo pipefail

CC="${TCP_CONGESTION_CONTROL:-cubic}"

if [[ -x /usr/sbin/sysctl ]]; then
  SYSCTL=/usr/sbin/sysctl
elif [[ -x /sbin/sysctl ]]; then
  SYSCTL=/sbin/sysctl
else
  echo "sysctl binary not found; install procps in the nginx image" >&2
  exit 1
fi

if [[ "${CC}" != "cubic" && "${CC}" != "bbr" ]]; then
  echo "Invalid TCP_CONGESTION_CONTROL=${CC}; use cubic or bbr" >&2
  exit 1
fi

if [[ "${CC}" == "bbr" ]]; then
  modprobe tcp_bbr 2>/dev/null || true
  if ! grep -q tcp_bbr /proc/modules 2>/dev/null && ! lsmod 2>/dev/null | grep -q tcp_bbr; then
    echo "WARNING: tcp_bbr module not loaded; BBR may be unavailable on this kernel" >&2
  fi
  "$SYSCTL" -w net.core.default_qdisc=fq >/dev/null 2>&1 || true
fi

if ! "$SYSCTL" -w "net.ipv4.tcp_congestion_control=${CC}"; then
  echo "Failed to set tcp_congestion_control=${CC}" >&2
  exit 1
fi

echo "TCP congestion control set to: $("$SYSCTL" -n net.ipv4.tcp_congestion_control)"
