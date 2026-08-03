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
    codeql_matrix_stats=$(awk '
      function indentation(line, stripped) {
        stripped = line
        sub(/^[[:space:]]*/, "", stripped)
        return length(line) - length(stripped)
      }
      function content(line) {
        sub(/^[[:space:]]*/, "", line)
        return line
      }
      {
        level = indentation($0)
        text = content($0)
        if (text == "" || text ~ /^#/) next
        if (level == 0) {
          in_jobs = (text == "jobs:")
          in_codeql = in_strategy = in_matrix = 0
          next
        }
        if (!in_jobs) next
        if (level == 2 && text ~ /^[A-Za-z0-9_-]+:[[:space:]]*$/) {
          in_codeql = (text == "codeql:")
          if (in_codeql) codeql_jobs += 1
          in_strategy = in_matrix = 0
          next
        }
        if (!in_codeql) next
        if (level == 4 && text ~ /^[A-Za-z0-9_-]+:/) {
          in_strategy = (text == "strategy:")
          if (in_strategy) strategy_blocks += 1
          in_matrix = 0
          next
        }
        if (!in_strategy) next
        if (level == 6 && text ~ /^[A-Za-z0-9_-]+:/) {
          in_matrix = (text == "matrix:")
          if (in_matrix) matrix_blocks += 1
          next
        }
        if (in_matrix && level == 8 && text ~ /^[A-Za-z0-9_-]+:/) {
          matrix_keys += 1
          if (text == "language: [python, javascript-typescript]") canonical_languages += 1
        }
      }
      END {
        print (codeql_jobs + 0) ":" (strategy_blocks + 0) ":" (matrix_blocks + 0) ":" (matrix_keys + 0) ":" (canonical_languages + 0)
      }
    ' "$workflow")
    if [ "$codeql_matrix_stats" != "1:1:1:1:1" ]; then
      echo "FAIL: security.yml CodeQL languages must be exactly python and javascript-typescript"
      errors=$((errors + 1))
    fi
    codeql_init_steps=$(grep -Ec 'github/codeql-action/init@' "$workflow" || true)
    codeql_analyze_steps=$(grep -Ec 'github/codeql-action/analyze@' "$workflow" || true)
    matrix_wiring=$(grep -Fc 'languages: ${{ matrix.language }}' "$workflow" || true)
    init_wiring_stats=$(awk '
      function indentation(line, stripped) {
        stripped = line
        sub(/^[[:space:]]*/, "", stripped)
        return length(line) - length(stripped)
      }
      function content(line) {
        sub(/^[[:space:]]*/, "", line)
        return line
      }
      {
        level = indentation($0)
        text = content($0)
        if (text == "" || text ~ /^#/) next
        if (level == 2 && text ~ /^[A-Za-z0-9_-]+:[[:space:]]*$/) {
          in_codeql = (text == "codeql:")
          in_steps = in_init = in_with = 0
          next
        }
        if (!in_codeql) next
        if (level == 4 && text ~ /^[A-Za-z0-9_-]+:/) {
          if (text ~ /^(if|continue-on-error):/) forbidden_controls += 1
          in_steps = (text == "steps:")
          if (in_steps) {
            steps_indent = level
            steps_count += 1
          }
          in_init = in_with = 0
          next
        }
        if (!in_steps) next
        if (level == steps_indent + 2 && text ~ /^- /) {
          in_init = 0
          in_with = 0
          security_step = ""
          if (text ~ /^- uses:[[:space:]]*github\/codeql-action\/init@/) {
            in_init = 1
            init_indent = level
            init_count += 1
            security_step = "init"
          } else if (text ~ /^- uses:[[:space:]]*github\/codeql-action\/analyze@/) {
            analyze_count += 1
            security_step = "analyze"
          }
          next
        }
        if (security_step != "" && level == steps_indent + 4 && text ~ /^(if|continue-on-error):/) {
          forbidden_controls += 1
        }
        if (in_init && level == init_indent + 2 && text == "with:") {
          in_with = 1
          with_indent = level
          with_count += 1
          next
        }
        if (in_with && level <= with_indent) in_with = 0
        if (in_with && level == with_indent + 2 && text ~ /^languages:/) language_count += 1
        if (in_with && level == with_indent + 2 && text == "languages: ${{ matrix.language }}") matrix_count += 1
      }
      END {
        print (steps_count + 0) ":" (init_count + 0) ":" (analyze_count + 0) ":" (matrix_count + 0) ":" (with_count + 0) ":" (language_count + 0) ":" (forbidden_controls + 0)
      }
    ' "$workflow")
    if [ "$codeql_init_steps" -ne 1 ] || [ "$codeql_analyze_steps" -ne 1 ] || [ "$matrix_wiring" -ne 1 ] || [ "$init_wiring_stats" != "1:1:1:1:1:1:0" ]; then
      echo 'FAIL: security.yml CodeQL init wiring must use direct with.languages: ${{ matrix.language }} exactly once'
      echo 'FAIL: security.yml CodeQL steps must contain direct unconditional init and analyze actions with fail-closed matrix wiring'
      errors=$((errors + 1))
    fi
  fi
done

if [ "$errors" -gt 0 ]; then
  echo "CI workflow validation failed with $errors error(s)"
  exit 1
fi

echo "CI workflow validation passed"
