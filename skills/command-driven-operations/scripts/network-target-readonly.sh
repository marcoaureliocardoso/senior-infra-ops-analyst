#!/usr/bin/env bash
# SAFE_READ_ONLY + ACTIVE_PROBE: narrow connectivity check for one target.
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

Operational notes:
  - This sends packets to the target; use only when authorized.
  - Keep scope to one target and one port unless approved.
  - If no reliable TCP probe tool is present, the script says the probe was not run; it does not interpret missing tooling as a closed port.
EOF
}

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then usage; exit 0; fi
TARGET="${1:-}"
PORT="${2:-443}"
if [ -z "$TARGET" ]; then echo "Missing target." >&2; usage >&2; exit 2; fi
if [ "$#" -gt 2 ]; then echo "Too many arguments." >&2; usage >&2; exit 2; fi
if [[ ! "$TARGET" =~ ^[A-Za-z0-9._:-]+$ ]]; then echo "Invalid target. Use a hostname, IPv4, or simple IPv6 literal only." >&2; exit 2; fi
if [[ ! "$PORT" =~ ^[0-9]+$ ]] || [ "$PORT" -lt 1 ] || [ "$PORT" -gt 65535 ]; then echo "Invalid port. Use 1-65535." >&2; exit 2; fi

have() { command -v "$1" >/dev/null 2>&1; }
section() { printf '\n## %s\n' "$1"; }

section "name resolution"
getent hosts "$TARGET" 2>/dev/null || nslookup "$TARGET" 2>/dev/null || true

section "ping"
ping -c 4 -W 2 "$TARGET" || true

section "route"
if have ip; then ip route get "$TARGET" 2>/dev/null || true; else route -n 2>/dev/null || true; fi

section "tcp port"
if have nc; then
  timeout 5 nc -vz -- "$TARGET" "$PORT" && echo "TCP open" || echo "TCP probe completed: not open or not reachable"
elif have python3; then
  python3 - "$TARGET" "$PORT" <<'PY'
import socket, sys
host, port = sys.argv[1], int(sys.argv[2])
s = socket.socket(socket.AF_INET if ':' not in host else socket.AF_INET6, socket.SOCK_STREAM)
s.settimeout(5)
try:
    s.connect((host, port))
    print('TCP open')
except socket.timeout:
    print('TCP timeout')
except OSError as e:
    print(f'TCP probe completed: {e}')
finally:
    s.close()
PY
else
  echo "TCP probe not run: install nc or python3 for reliable status."
fi

section "traceroute if available"
if have traceroute; then traceroute -m 15 -- "$TARGET" || true; else echo "traceroute not available; skipped."; fi
