#!/usr/bin/env bash
# SAFE_READ_ONLY + SENSITIVE_OUTPUT: collect a narrow Linux baseline.
# Review output before sharing. Redact hostnames, IPs, users, paths, and logs when needed.
set -uo pipefail

usage() {
  cat <<'EOF'
linux-baseline-readonly.sh - collect a narrow read-only Linux baseline

Usage:
  ./linux-baseline-readonly.sh [--log-lines N] [--processes]
  ./linux-baseline-readonly.sh -h|--help

Options:
  --log-lines N   Number of recent warning+ log lines to show. Default: 50.
  --processes     Include process names on listening sockets when permitted.
  -h, --help      Show this help.

Risk classification:
  SAFE_READ_ONLY + SENSITIVE_OUTPUT

Operational notes:
  - Run only on authorized systems.
  - Output may contain hostnames, users, IPs, paths, service names, and logs.
  - Uses systemd commands when present and falls back to generic checks when absent.
EOF
}

LOG_LINES="${LOG_LINES:-50}"
SHOW_PROCESSES=0
while [ "$#" -gt 0 ]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --processes) SHOW_PROCESSES=1 ;;
    --log-lines)
      shift
      if [ "$#" -eq 0 ] || ! [[ "$1" =~ ^[0-9]+$ ]] || [ "$1" -gt 1000 ]; then
        echo "Invalid --log-lines. Use an integer from 0 to 1000." >&2
        exit 2
      fi
      LOG_LINES="$1"
      ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

section() { printf '\n## %s\n' "$1"; }
have() { command -v "$1" >/dev/null 2>&1; }

section "identity"
id 2>/dev/null || true
if have hostnamectl; then hostnamectl 2>/dev/null || hostname; else hostname; fi
uname -a

section "uptime/load"
uptime 2>/dev/null || true

section "network"
if have ip; then ip -brief addr 2>/dev/null || true; ip route 2>/dev/null || true; else ifconfig 2>/dev/null || true; netstat -rn 2>/dev/null || true; fi

section "listening sockets"
if have ss; then
  if [ "$SHOW_PROCESSES" -eq 1 ]; then
    if [ "$(id -u 2>/dev/null || echo 1)" -eq 0 ]; then ss -tulpn 2>/dev/null | head -100 || true; else echo "Not root: using ss -tuln. Re-run with approved privileges for process names."; ss -tuln 2>/dev/null | head -100 || true; fi
  else
    ss -tuln 2>/dev/null | head -100 || true
  fi
elif have netstat; then
  netstat -tuln 2>/dev/null | head -100 || true
else
  echo "No ss/netstat available; socket check not run."
fi

section "storage"
df -hT 2>/dev/null || df -h 2>/dev/null || true

section "memory"
free -h 2>/dev/null || vm_stat 2>/dev/null || true

section "service manager status"
if have systemctl; then
  systemctl --failed --no-pager 2>/dev/null || true
elif have service; then
  service --status-all 2>/dev/null | head -100 || true
else
  echo "No systemctl/service command available."
fi

section "recent warning+ logs, limited"
if have journalctl; then
  journalctl -p warning..alert -n "${LOG_LINES}" --no-pager 2>/dev/null || true
elif [ -r /var/log/syslog ]; then
  tail -n "${LOG_LINES}" /var/log/syslog 2>/dev/null || true
elif [ -r /var/log/messages ]; then
  tail -n "${LOG_LINES}" /var/log/messages 2>/dev/null || true
else
  echo "No readable journal/syslog/messages log source found."
fi
