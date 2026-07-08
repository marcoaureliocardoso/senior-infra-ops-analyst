#!/usr/bin/env bash
# SAFE_READ_ONLY + SENSITIVE_OUTPUT: collect a narrow Linux baseline.
# Review output before sharing. Redact hostnames, IPs, users, paths, and logs when needed.
set -uo pipefail

usage() {
  cat <<'EOF'
linux-baseline-readonly.sh - collect a narrow read-only Linux baseline

Usage:
  ./linux-baseline-readonly.sh [--log-lines N]
  ./linux-baseline-readonly.sh -h|--help

Options:
  --log-lines N   Number of recent warning+ journal lines to show. Default: 50.
  -h, --help      Show this help.

Risk classification:
  SAFE_READ_ONLY + SENSITIVE_OUTPUT

What it checks:
  identity, OS/kernel, uptime/load, IP addresses/routes, listening sockets,
  disk usage, memory, failed systemd units, limited warning/error logs.

Operational notes:
  - Run only on authorized systems.
  - Output may contain hostnames, users, IPs, paths, service names, and logs.
  - Redact before sharing outside the operations context.
EOF
}

LOG_LINES="${LOG_LINES:-50}"
while [ "$#" -gt 0 ]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --log-lines)
      shift
      if [ "$#" -eq 0 ] || ! [[ "$1" =~ ^[0-9]+$ ]] || [ "$1" -gt 1000 ]; then
        echo "Invalid --log-lines. Use an integer from 0 to 1000." >&2
        exit 2
      fi
      LOG_LINES="$1"
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

echo "## identity"
id 2>/dev/null || true
hostnamectl 2>/dev/null || hostname
uname -a

echo "## uptime/load"
uptime

echo "## network"
ip -brief addr 2>/dev/null || true
ip route 2>/dev/null || true

echo "## listening sockets"
ss -tulpn 2>/dev/null | head -100 || true

echo "## storage"
df -hT 2>/dev/null || df -h

echo "## memory"
free -h 2>/dev/null || true

echo "## failed systemd units"
systemctl --failed --no-pager 2>/dev/null || true

echo "## recent warning+ logs, limited"
journalctl -p warning..alert -n "${LOG_LINES}" --no-pager 2>/dev/null || true
