#!/usr/bin/env bash
# SAFE_READ_ONLY + ACTIVE_PROBE: narrow connectivity check for one target.
# Input is validated before use to avoid shell injection when probing /dev/tcp.
set -uo pipefail

usage() {
  cat <<'EOF'
network-target-readonly.sh - narrow read-only/active network probe for one target

Usage:
  ./network-target-readonly.sh <target-host-or-ip> [port]
  ./network-target-readonly.sh -h|--help

Arguments:
  target-host-or-ip  Hostname, IPv4 address, or simple IPv6 literal.
  port               TCP port to test. Default: 443.

Risk classification:
  SAFE_READ_ONLY + ACTIVE_PROBE

What it checks:
  name resolution, ping, route selection, one TCP port, and traceroute if available.

Operational notes:
  - This sends packets to the target; use only when authorized.
  - Keep scope to one target and one port unless approved.
  - Output may reveal internal names, IPs, and route details.
EOF
}

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  usage
  exit 0
fi

TARGET="${1:-}"
PORT="${2:-443}"
if [ -z "$TARGET" ]; then
  echo "Missing target." >&2
  usage >&2
  exit 2
fi
if [ "$#" -gt 2 ]; then
  echo "Too many arguments." >&2
  usage >&2
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
