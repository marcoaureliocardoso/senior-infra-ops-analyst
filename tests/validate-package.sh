#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:-$(cd "$(dirname "$0")/.." && pwd)}"
cd "$ROOT"

echo "## JSON"
python3 -m json.tool nori.json >/dev/null

echo "## Bash syntax"
bash -n skills/command-driven-operations/scripts/linux-baseline-readonly.sh
bash -n skills/command-driven-operations/scripts/network-target-readonly.sh

echo "## PowerShell syntax"
if command -v pwsh >/dev/null 2>&1; then
  pwsh -NoProfile -ExecutionPolicy Bypass -File tests/validate-powershell-syntax.ps1
elif command -v powershell >/dev/null 2>&1; then
  powershell -NoProfile -ExecutionPolicy Bypass -File tests/validate-powershell-syntax.ps1
else
  echo "pwsh/powershell not found; PowerShell syntax not parsed in this environment." >&2
  echo "Run tests/validate-powershell-syntax.ps1 on a host with PowerShell before release." >&2
fi

echo "## Help smoke tests"
./skills/command-driven-operations/scripts/linux-baseline-readonly.sh --help >/dev/null
./skills/command-driven-operations/scripts/network-target-readonly.sh --help >/dev/null

echo "OK"
