#!/usr/bin/env bash
# SAFE_READ_ONLY + ACTIVE_PROBE: narrow connectivity check for one target.
# Input is validated before use to avoid shell injection when probing /dev/tcp.
set -uo pipefail
TARGET="${1:-}"
PORT="${2:-443}"
if [ -z "$TARGET" ]; then
  echo "Usage: $0 <target-host-or-ip> [port]" >&2
  exit 2
fi
if [[ ! "$TARGET" =~ ^[A-Za-z0-9._:-]+$ ]]; then
  echo "Invalid target. Use a hostname, IPv4, or simple IPv6 literal only." >&2
  exit 2
fi
if [[ ! "$PORT" =~ ^[0-9]+$ ]] || [ "$PORT" -lt 1 ] || [ "$PORT" -gt 65535 ]; then
  echo "Invalid port. Use 1-65535." >&2
  exit 2
fi

echo "## name resolution"
getent hosts "$TARGET" || true

echo "## ping"
ping -c 4 -W 2 "$TARGET" || true

echo "## route"
ip route get "$TARGET" 2>/dev/null || true

echo "## tcp port"
if command -v nc >/dev/null 2>&1; then
  timeout 5 nc -vz -- "$TARGET" "$PORT" && echo "TCP open" || echo "TCP closed/filtered/refused"
else
  timeout 5 bash -c 'cat < /dev/null > "/dev/tcp/$1/$2"' _ "$TARGET" "$PORT" \
    && echo "TCP open" || echo "TCP closed/filtered/refused or shell lacks /dev/tcp"
fi

echo "## traceroute if available"
command -v traceroute >/dev/null && traceroute -m 15 -- "$TARGET" || true
