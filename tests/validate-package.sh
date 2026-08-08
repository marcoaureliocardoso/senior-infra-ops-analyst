#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
node tests/run-command-guard-tests.mjs
node --test tests/context-continuity/settings.test.mjs
node --test tests/context-continuity/statusline.test.mjs
node --test tests/context-continuity/compact-hook.test.mjs
python3 tests/test-command-guard-install-policy.py
python3 tests/test-context-continuity-install-policy.py
python3 -m json.tool nori.json >/dev/null
python3 tests/validate-content.py
python3 tests/test-risk-taxonomy.py
python3 tests/test-subagent-frontmatter.py
python3 tests/test-installed-subagents.py
python3 tests/test-schema-validation.py
python3 tests/test-architecture-docs.py
python3 tests/test-live-smoke-safety.py
python3 tests/test-load-claude-env.py
python3 tests/test-loopback-http-fixture.py
python3 tests/test-live-command-guard-safety.py
python3 tests/test-smoke-command-guard.py
python3 tests/test-ci-workflows.py
bash -n skills/command-driven-operations/scripts/linux-baseline-readonly.sh
bash -n skills/command-driven-operations/scripts/network-target-readonly.sh
bash -n skills/context-continuity/scripts/compact-hook-launcher.sh
bash -n tests/live-subagent-runtime-smoke.sh
bash -n tests/live-command-guard-smoke.sh
bash -n tests/validate-package.sh
bash tests/live-subagent-runtime-smoke.sh --self-test
bash tests/live-command-guard-smoke.sh --self-test
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
python3 tests/validate-schema.py
bash tests/validate-ci-workflows.sh
echo "package validation passed"
