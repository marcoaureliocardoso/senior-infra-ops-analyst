#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

errors=0

if [ ! -f .github/workflows/security.yml ]; then
  echo "FAIL: security.yml is required"
  errors=$((errors + 1))
fi

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

  if [ "$name" = "security.yml" ]; then
    language_lines=$(grep -Ec '^[[:space:]]+language:[[:space:]]*\[[^]]+\][[:space:]]*$' "$workflow" || true)
    codeql_languages=$(sed -nE 's/^[[:space:]]+language:[[:space:]]*\[([^]]+)\][[:space:]]*$/\1/p' "$workflow" \
      | tr ',' '\n' \
      | sed -E 's/^[[:space:]]+|[[:space:]]+$//g' \
      | sort \
      | paste -sd, -)
    if [ "$language_lines" -ne 1 ] || [ "$codeql_languages" != "javascript-typescript,python" ]; then
      echo "FAIL: security.yml CodeQL languages must be exactly python and javascript-typescript"
      errors=$((errors + 1))
    fi
    codeql_init_steps=$(grep -Ec 'github/codeql-action/init@' "$workflow" || true)
    matrix_wiring=$(grep -Fc 'languages: ${{ matrix.language }}' "$workflow" || true)
    init_wiring_stats=$(awk '
      function indentation(line, stripped) {
        stripped = line
        sub(/^[[:space:]]*/, "", stripped)
        return length(line) - length(stripped)
      }
      /^[[:space:]]*- uses:[[:space:]]*github\/codeql-action\/init@/ {
        in_init = 1
        in_with = 0
        init_indent = indentation($0)
        next
      }
      in_init && /^[[:space:]]*- / && indentation($0) <= init_indent {
        in_init = 0
        in_with = 0
      }
      in_init && indentation($0) == init_indent + 2 && /^[[:space:]]+with:[[:space:]]*$/ {
        in_with = 1
        with_indent = indentation($0)
        with_count += 1
        next
      }
      in_with && /^[[:space:]]*[^[:space:]]/ && indentation($0) <= with_indent {
        in_with = 0
      }
      in_with && indentation($0) == with_indent + 2 && /^[[:space:]]+languages:[[:space:]]*/ {
        language_count += 1
      }
      in_with && indentation($0) == with_indent + 2 && /^[[:space:]]+languages:[[:space:]]*\$\{\{[[:space:]]*matrix\.language[[:space:]]*\}\}[[:space:]]*$/ {
        matrix_count += 1
      }
      END { print (matrix_count + 0) ":" (with_count + 0) ":" (language_count + 0) }
    ' "$workflow")
    if [ "$codeql_init_steps" -ne 1 ] || [ "$matrix_wiring" -ne 1 ] || [ "$init_wiring_stats" != "1:1:1" ]; then
      echo 'FAIL: security.yml CodeQL init wiring must use languages: ${{ matrix.language }} exactly once'
      errors=$((errors + 1))
    fi
  fi
done

if [ "$errors" -gt 0 ]; then
  echo "CI workflow validation failed with $errors error(s)"
  exit 1
fi

echo "CI workflow validation passed"
