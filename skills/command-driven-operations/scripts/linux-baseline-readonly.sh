#!/usr/bin/env bash
# SAFE_READ_ONLY + SENSITIVE_OUTPUT: collect a narrow Linux baseline.
# Review output before sharing. Redact hostnames, IPs, users, paths, and logs when needed.
set -uo pipefail
LOG_LINES="${LOG_LINES:-50}"
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
