#!/usr/bin/env bash
# Quick checks on GCP after rebuilding dashjs-nginx. Run from mmsys24 repo root.
set -euo pipefail

NGINX="${NGINX_CONTAINER:-dashjs-nginx}"

echo "==> TCP CC"
docker exec "$NGINX" cat /proc/sys/net/ipv4/tcp_congestion_control

echo "==> tc qdisc (expect htb root + netem child)"
docker exec "$NGINX" tc qdisc show dev eth0

echo "==> tc-trace process"
docker exec "$NGINX" pgrep -af tc-trace || echo "WARNING: tc-trace not running"

echo "==> last tc-trace lines"
docker logs "$NGINX" 2>&1 | grep -E "tc init OK|tc-trace|trace loaded" | tail -5

echo "==> simulate batch restart (same as runner restart_nginx)"
docker restart "$NGINX" >/dev/null
sleep 8
docker exec "$NGINX" tc qdisc show dev eth0
docker exec "$NGINX" pgrep -af tc-trace || { echo "FAIL: tc-trace dead after restart"; exit 1; }
docker logs "$NGINX" 2>&1 | grep "tc init OK" | tail -1

echo "OK: shaper survived docker restart"
