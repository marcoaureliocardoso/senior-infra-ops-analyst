#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m json.tool nori.json >/dev/null
python3 tests/validate-content.py
bash -n skills/command-driven-operations/scripts/linux-baseline-readonly.sh
bash -n skills/command-driven-operations/scripts/network-target-readonly.sh
bash -n tests/validate-package.sh
skills/command-driven-operations/scripts/linux-baseline-readonly.sh --help >/dev/null
skills/command-driven-operations/scripts/network-target-readonly.sh --help >/dev/null
if command -v pwsh >/dev/null 2>&1; then
  pwsh -NoProfile -File tests/validate-powershell-syntax.ps1
  pwsh -NoProfile -File skills/command-driven-operations/scripts/windows-baseline-readonly.ps1 -Help >/dev/null
elif command -v powershell >/dev/null 2>&1; then
  powershell -NoProfile -File tests/validate-powershell-syntax.ps1
  powershell -NoProfile -File skills/command-driven-operations/scripts/windows-baseline-readonly.ps1 -Help >/dev/null
else
  echo "PowerShell not available; syntax validation for .ps1 skipped. See tests/validation-notes.md."
fi
if find . -type f ! -path './.git/*' -perm -0002 | grep -q .; then
  echo "World-writable files found" >&2
  find . -type f ! -path './.git/*' -perm -0002 >&2
  exit 1
fi
if find . -type f \( -name '*.md' -o -name '*.json' -o -name 'LICENSE' -o -name '.gitattributes' -o -name '.gitignore' \) -perm -0100 | grep -q .; then
  echo "Non-script text files are executable" >&2
  find . -type f \( -name '*.md' -o -name '*.json' -o -name 'LICENSE' -o -name '.gitattributes' -o -name '.gitignore' \) -perm -0100 >&2
  exit 1
fi
echo "package validation passed"
