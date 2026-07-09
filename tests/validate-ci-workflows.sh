#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

errors=0

for workflow in .github/workflows/*.yml .github/workflows/*.yaml; do
  [ -f "$workflow" ] || continue
  name=$(basename "$workflow")

  # Every workflow MUST set top-level permissions
  if ! grep -q '^permissions:' "$workflow"; then
    echo "FAIL: $name missing top-level permissions block"
    errors=$((errors + 1))
  fi

  # Every workflow MUST pin the OS version (no ubuntu-latest)
  if grep -q 'ubuntu-latest' "$workflow"; then
    echo "FAIL: $name uses ubuntu-latest (must pin to ubuntu-24.04)"
    errors=$((errors + 1))
  fi

  # CI workflows on push/PR MUST have concurrency control
  if grep -qE '^on:' "$workflow" && grep -qE 'pull_request|push' "$workflow"; then
    if ! grep -q 'concurrency:' "$workflow"; then
      echo "FAIL: $name triggers on push/PR but lacks concurrency group"
      errors=$((errors + 1))
    fi
  fi

  # Every job SHOULD have a timeout (warn only)
  if grep -q 'timeout-minutes' "$workflow"; then
    :
  else
    echo "WARN: $name has no timeout-minutes set on any job"
  fi

  # Checkout action MUST be pinned by commit hash, not just tag
  if grep -qE 'uses: *actions/checkout@v[0-9]+[[:space:]]*$' "$workflow"; then
    echo "FAIL: $name pins checkout by tag only, not commit hash"
    errors=$((errors + 1))
  fi
done

if [ "$errors" -gt 0 ]; then
  echo "CI workflow validation failed with $errors error(s)"
  exit 1
fi

echo "CI workflow validation passed"
