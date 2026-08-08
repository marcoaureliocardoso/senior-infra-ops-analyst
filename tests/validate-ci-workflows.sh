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

  if [ "$name" != "security.yml" ] && {
    grep -Eq '^[[:space:]]*(-[[:space:]]+)?"[^"]+"[[:space:]]*:' "$workflow" ||
      grep -Eq "^[[:space:]]*(-[[:space:]]+)?'[^']+'[[:space:]]*:" "$workflow" ||
      grep -Eq '^[[:space:]]*(-[[:space:]]+)?[?:][[:space:]]+' "$workflow" ||
      grep -Eq '^[[:space:]]*(-[[:space:]]+)?\*[A-Za-z0-9_-]+[[:space:]]*:|:[[:space:]]*&[A-Za-z0-9_-]+([[:space:]]|$)|^[[:space:]]*(-[[:space:]]+)?!!' "$workflow"
  }; then
    echo "FAIL: $name requires canonical YAML mapping keys"
    errors=$((errors + 1))
  fi

  bad_action_refs=$(awk '
    {
      text = $0
      sub(/^[[:space:]]*/, "", text)
      sub(/^-[[:space:]]*/, "", text)
      if (text !~ /^uses:[[:space:]]+/) next
      sub(/^uses:[[:space:]]+/, "", text)
      if (text ~ /^\.\//) next
      count = split(text, fields, /[[:space:]]+#[[:space:]]+/)
      target = fields[1]
      ref = target
      sub(/^.*@/, "", ref)
      base = target
      sub(/@[^@]*$/, "", base)
      if (count != 2 || base == target || length(ref) != 40 || ref !~ /^[0-9a-f]+$/ || fields[2] !~ /^v[^[:space:]]+$/) {
        print NR ":" $0
      }
    }
  ' "$workflow")
  if [ -n "$bad_action_refs" ]; then
    echo "FAIL: $name external action must use a full commit SHA with a release comment"
    echo "$bad_action_refs"
    errors=$((errors + 1))
  fi

  if [ "$name" = "ci.yml" ]; then
    python_matrix_stats=$(awk '
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
          in_nori = in_strategy = in_matrix = in_steps = in_setup = in_with = 0
          next
        }
        if (!in_jobs) next
        if (level == 2 && text ~ /^[A-Za-z0-9_-]+:[[:space:]]*$/) {
          in_nori = (text == "nori-schema:")
          if (in_nori) nori_jobs += 1
          in_strategy = in_matrix = in_steps = in_setup = in_with = 0
          next
        }
        if (!in_nori) next
        if (level == 4 && text ~ /^[A-Za-z0-9_-]+:/) {
          if (text ~ /^(if|continue-on-error):/) forbidden_controls += 1
          in_strategy = (text == "strategy:")
          if (in_strategy) strategy_blocks += 1
          in_steps = (text == "steps:")
          if (in_steps) steps_blocks += 1
          in_matrix = in_setup = in_with = 0
          next
        }
        if (in_strategy && level == 6 && text ~ /^[A-Za-z0-9_-]+:/) {
          in_matrix = (text == "matrix:")
          if (in_matrix) matrix_blocks += 1
          next
        }
        if (in_matrix && level == 8 && text ~ /^[A-Za-z0-9_-]+:/) {
          matrix_keys += 1
          if (text == "python-version: ['\''3.12'\'', '\''3.14'\'']") canonical_matrix += 1
          next
        }
        if (in_steps && level == 6 && text ~ /^- /) {
          in_setup = (text ~ /^- uses:[[:space:]]*actions\/setup-python@/)
          if (in_setup) setup_steps += 1
          in_with = 0
          next
        }
        if (in_setup && level == 8 && text ~ /^(if|continue-on-error):/) forbidden_controls += 1
        if (in_setup && level == 8 && text == "with:") {
          in_with = 1
          with_blocks += 1
          next
        }
        if (in_with && level <= 8) in_with = 0
        if (in_with && level == 10 && text ~ /^python-version:/) {
          python_inputs += 1
          if (text == "python-version: ${{ matrix.python-version }}") matrix_wiring += 1
        }
      }
      END {
        print (nori_jobs + 0) ":" (strategy_blocks + 0) ":" (matrix_blocks + 0) ":" (matrix_keys + 0) ":" (canonical_matrix + 0) ":" (steps_blocks + 0) ":" (setup_steps + 0) ":" (with_blocks + 0) ":" (python_inputs + 0) ":" (matrix_wiring + 0) ":" (forbidden_controls + 0)
      }
    ' "$workflow")
    if [ "$python_matrix_stats" != "1:1:1:1:1:1:1:1:1:1:0" ]; then
      echo "FAIL: ci.yml nori-schema Python matrix must be exactly 3.12 and 3.14"
      echo "FAIL: ci.yml Python setup wiring must be direct, unconditional, and fail closed"
      errors=$((errors + 1))
    fi
  fi

  if [ "$name" = "security.yml" ]; then
    if grep -Eq '^[[:space:]]*(-[[:space:]]+)?"[^"]+"[[:space:]]*:' "$workflow" ||
      grep -Eq "^[[:space:]]*(-[[:space:]]+)?'[^']+'[[:space:]]*:" "$workflow" ||
      grep -Eq '^[[:space:]]*(-[[:space:]]+)?[?:][[:space:]]+' "$workflow" ||
      grep -Eq '^[[:space:]]*(-[[:space:]]+)?\*[A-Za-z0-9_-]+[[:space:]]*:|:[[:space:]]*&[A-Za-z0-9_-]+([[:space:]]|$)|^[[:space:]]*(-[[:space:]]+)?!!' "$workflow"; then
      echo "FAIL: security.yml CodeQL steps require canonical YAML mapping keys"
      errors=$((errors + 1))
    fi

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
    matrix_wiring=$(grep -Fc "languages: \${{ matrix.language }}" "$workflow" || true)
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
      echo "FAIL: security.yml CodeQL init wiring must use direct with.languages: \${{ matrix.language }} exactly once"
      echo 'FAIL: security.yml CodeQL steps must contain direct unconditional init and analyze actions with fail-closed matrix wiring'
      errors=$((errors + 1))
    fi

    shellcheck_url='https://github.com/koalaman/shellcheck/releases/download/v0.11.0/shellcheck-v0.11.0.linux.x86_64.tar.xz'
    shellcheck_digest='8c3be12b05d5c177a04c29e3c78ce89ac86f1595681cab149b65b97c4e227198'
    shellcheck_url_count=$(grep -Fc "$shellcheck_url" "$workflow" || true)
    shellcheck_digest_count=$(grep -Fc "$shellcheck_digest" "$workflow" || true)
    shellcheck_verify_count=$(grep -Fc 'sha256sum --check --strict' "$workflow" || true)
    shellcheck_path_count=$(grep -Fc "echo \"\$RUNNER_TEMP/shellcheck-v0.11.0\" >> \"\$GITHUB_PATH\"" "$workflow" || true)
    shellcheck_version_count=$(grep -Fc "version: 0.11.0" "$workflow" || true)
    shellcheck_url_line=$(grep -nF "$shellcheck_url" "$workflow" | cut -d: -f1 || true)
    shellcheck_use_count=$(grep -Fc 'shellcheck -x' "$workflow" || true)
    shellcheck_use_line=$(grep -nF 'shellcheck -x' "$workflow" | head -n 1 | cut -d: -f1 || true)
    if [ "$shellcheck_url_count" -ne 1 ] || [ "$shellcheck_digest_count" -ne 1 ] ||
      [ "$shellcheck_verify_count" -ne 1 ] || [ "$shellcheck_path_count" -ne 1 ] ||
      [ "$shellcheck_version_count" -ne 1 ] || [ "$shellcheck_use_count" -ne 1 ] ||
      [ -z "$shellcheck_url_line" ] ||
      [ -z "$shellcheck_use_line" ] || [ "$shellcheck_url_line" -ge "$shellcheck_use_line" ]; then
      echo "FAIL: security.yml ShellCheck 0.11.0 provisioning must verify the official archive before use"
      errors=$((errors + 1))
    fi
  fi
done

if [ "$errors" -gt 0 ]; then
  echo "CI workflow validation failed with $errors error(s)"
  exit 1
fi

echo "CI workflow validation passed"
