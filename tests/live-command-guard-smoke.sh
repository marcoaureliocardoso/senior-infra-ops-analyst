#!/usr/bin/env bash
set -euo pipefail

blocked() {
  echo "BLOCKED: $*" >&2
  exit 2
}

MODE="${1:---self-test}"
[[ "$MODE" == "--self-test" || "$MODE" == "--run-live" ]] || {
  echo "Usage: $0 [--self-test|--run-live]" >&2
  exit 2
}
MODE="${MODE#--}"

LIVE_CREDENTIAL_ACK='I_ACCEPT_PROVIDER_CREDENTIAL_EGRESS_RISK'
if [[ "$MODE" == "run-live" ]]; then
  [[ "${P0_04_LIVE_NORMAL_CREDENTIALS_ACK:-}" == "$LIVE_CREDENTIAL_ACK" ]] || \
    blocked "set P0_04_LIVE_NORMAL_CREDENTIALS_ACK=$LIVE_CREDENTIAL_ACK to acknowledge normal provider credential exposure"
  printf '%s\n' \
    'WARNING: normal provider credentials enter the live Claude process and provider egress remains open; isolation reduces but does not eliminate exfiltration risk.' >&2
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_CLAUDE_SETTINGS="${CLAUDE_SETTINGS_SOURCE:-${CLAUDE_CONFIG_DIR:-$HOME/.claude}/settings.json}"
ALLOWED_CLAUDE_ENV=(
  ANTHROPIC_AUTH_TOKEN ANTHROPIC_API_KEY ANTHROPIC_BASE_URL ANTHROPIC_MODEL
  ANTHROPIC_DEFAULT_HAIKU_MODEL ANTHROPIC_DEFAULT_OPUS_MODEL
  ANTHROPIC_DEFAULT_SONNET_MODEL CLAUDE_CODE_SUBAGENT_MODEL
  CLAUDE_CODE_EFFORT_LEVEL
)
TMP_PARENT="${TMPDIR:-/tmp}"
WORK="$(mktemp -d "$TMP_PARENT/p0-04-command-guard.XXXXXX")"
WORK_REAL="$(readlink -f "$WORK")"
case "$WORK_REAL" in
  "$(readlink -f "$TMP_PARENT")"/p0-04-command-guard.*) ;;
  *) blocked "temporary directory escaped the verified runner prefix" ;;
esac
cleanup() {
  if [[ -n "${ENV_LOADER_PID:-}" ]]; then kill "$ENV_LOADER_PID" 2>/dev/null || true; fi
  if [[ -n "${SERVER_PID:-}" ]]; then kill "$SERVER_PID" 2>/dev/null || true; fi
  rm -rf -- "$WORK_REAL"
}
trap cleanup EXIT
umask 077

command -v node >/dev/null 2>&1 || blocked "Node.js not found"
command -v python3 >/dev/null 2>&1 || blocked "python3 not found"
export HOME="$WORK/home"
export CLAUDE_CONFIG_DIR="$HOME/.claude"
export HISTFILE=/dev/null
unset AWS_PROFILE AZURE_CONFIG_DIR CLOUDSDK_CONFIG KUBECONFIG
unset GOOGLE_APPLICATION_CREDENTIALS AZURE_CLIENT_SECRET AWS_SECRET_ACCESS_KEY
mkdir -p "$CLAUDE_CONFIG_DIR/agents" "$CLAUDE_CONFIG_DIR/skills" "$WORK/probes"

INSTALLED_AGENTS_DIR="$CLAUDE_CONFIG_DIR/agents"
INSTALLED_SKILLS_DIR="$CLAUDE_CONFIG_DIR/skills"
AUDIT_PATH="$WORK/probes/audit.jsonl"
REPORT_PATH="$WORK/probes/report.txt"
SECRET="SYNTH_SECRET_$$_p004"

install_source_fixture() {
  cp "$ROOT"/subagents/*.md "$INSTALLED_AGENTS_DIR/"
  cp -R "$ROOT"/skills/. "$INSTALLED_SKILLS_DIR/"
  python3 - "$INSTALLED_AGENTS_DIR" "$INSTALLED_SKILLS_DIR" <<'PY'
import sys
from pathlib import Path
agents, skills = map(Path, sys.argv[1:])
for path in agents.glob("*.md"):
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace("{{skills_dir}}", str(skills)), encoding="utf-8")
PY
}

install_with_nori() {
  NORI_BIN="${NORI_BIN:-$(command -v sks || command -v nori-skillsets || true)}"
  [[ -n "$NORI_BIN" ]] || blocked "Nori CLI not found"
  "$NORI_BIN" --install-dir "$CLAUDE_CONFIG_DIR" --agent claude-code \
    link "$ROOT" --name senior-infra-ops-analyst
  "$NORI_BIN" --install-dir "$CLAUDE_CONFIG_DIR" --agent claude-code \
    switch senior-infra-ops-analyst --agent claude-code
}

locate_installed_roots() {
  if [[ ! -f "$INSTALLED_AGENTS_DIR/diagnostic-operator.md" ]]; then
    local agent
    agent="$(find "$CLAUDE_CONFIG_DIR" -type f -name diagnostic-operator.md -print -quit)"
    [[ -n "$agent" ]] || blocked "installed agents directory not found"
    INSTALLED_AGENTS_DIR="$(dirname "$agent")"
  fi
  if [[ ! -f "$INSTALLED_SKILLS_DIR/command-driven-operations/SKILL.md" ]]; then
    local skill
    skill="$(find "$CLAUDE_CONFIG_DIR" -type f -path '*/command-driven-operations/SKILL.md' -print -quit)"
    [[ -n "$skill" ]] || blocked "installed skills directory not found"
    INSTALLED_SKILLS_DIR="$(dirname "$(dirname "$skill")")"
  fi
}

emit_event() {
  python3 - "$1" "$2" <<'PY'
import json
import sys
print(json.dumps({
    "session_id": "p0-04-live-synthetic-session",
    "hook_event_name": "PreToolUse",
    "agent_type": "diagnostic-operator",
    "permission_mode": sys.argv[1],
    "tool_name": "Bash",
    "tool_input": {"command": sys.argv[2], "run_in_background": False},
}))
PY
}

assert_decision() {
  local mode="$1" command="$2" expected="$3" output status
  set +e
  output="$(emit_event "$mode" "$command" | \
    OPS_COMMAND_GUARD_AUDIT_PATH="$AUDIT_PATH" node "$GUARD" 2>"$WORK/probes/stderr")"
  status=$?
  set -e
  [[ $status -eq 0 ]] || blocked "direct guard probe failed: expected $expected, exit $status"
  python3 - "$expected" "$output" <<'PY'
import json
import sys
expected, raw = sys.argv[1:]
value = json.loads(raw)
actual = value["hookSpecificOutput"]["permissionDecision"]
if actual != expected:
    raise SystemExit(f"expected {expected}, observed {actual}")
if actual == "deny" and not value.get("systemMessage"):
    raise SystemExit("deny did not include an operator-visible systemMessage")
PY
}

assert_failure() {
  local input="$1" audit="$2" status
  set +e
  printf '%s' "$input" | OPS_COMMAND_GUARD_AUDIT_PATH="$audit" \
    node "$GUARD" >"$WORK/probes/failure.stdout" 2>"$WORK/probes/failure.stderr"
  status=$?
  set -e
  [[ $status -eq 2 ]] || blocked "fail-closed probe returned $status instead of 2"
  [[ ! -s "$WORK/probes/failure.stdout" ]] || blocked "fail-closed probe emitted a decision"
}

run_direct_probes() {
  GUARD="$INSTALLED_SKILLS_DIR/command-driven-operations/scripts/validate-ops-command.mjs"
  [[ -f "$GUARD" ]] || blocked "installed guard entrypoint not found"
  assert_decision default 'uname -a' allow
  assert_decision default 'systemctl restart nginx' ask
  assert_decision bypassPermissions 'systemctl restart nginx' allow
  assert_decision bypassPermissions 'kubectl --context lab --namespace demo delete pod demo-0' ask
  assert_decision default 'unknown-command synthetic' deny
  assert_decision default 'journalctl -u nginx -n 20 | grep error | head -n 5' allow
  assert_decision default "pwsh -NoProfile -Command \"Get-Service | Where-Object Status -eq 'Running'\"" allow
  assert_decision bypassPermissions "curl -H \"Authorization: Bearer $SECRET\" http://127.0.0.1:43119/health" ask
  # shellcheck disable=SC2016 # Literal provider variable must reach the guard unchanged.
  assert_decision bypassPermissions 'curl -H "Authorization: Bearer $ANTHROPIC_AUTH_TOKEN" http://127.0.0.1:43119/health' deny
  assert_decision bypassPermissions "TOKEN=$SECRET echo \$TOKEN" deny
  assert_failure '{' "$AUDIT_PATH"
  assert_failure "$(emit_event default 'uname -a')" "$WORK/probes"
}

scan_retained_artifacts() {
  if grep -R -F "$SECRET" "$WORK/probes" --exclude='input.json' >/dev/null 2>&1; then
    blocked "synthetic credential retained in command guard artifacts"
  fi
  if grep -R -E 'ANTHROPIC_AUTH_TOKEN|ANTHROPIC_API_KEY' "$WORK/probes" >/dev/null 2>&1; then
    blocked "provider credential variable name retained in command guard artifacts"
  fi
}

record_versions() {
  {
    printf 'Observed Node.js: %s\n' "$(node --version)"
    printf 'Observed Nori: %s\n' "${NORI_VERSION:-not-run-self-test}"
    printf 'Observed Claude Code: %s\n' "${CLAUDE_VERSION:-not-run-self-test}"
    printf 'Observed model: %s\n' "${ANTHROPIC_MODEL:-operator-configured}"
    printf 'Observed platform: %s\n' "$(uname -s 2>/dev/null || printf unknown)"
    printf 'Observed permission modes: default,bypassPermissions\n'
  } >"$REPORT_PATH"
  cat "$REPORT_PATH"
}

if [[ "$MODE" == "run-live" ]]; then
  CLAUDE_BIN="${CLAUDE_BIN:-$(command -v claude || true)}"
  BWRAP_BIN="${BWRAP_BIN:-$(command -v bwrap || true)}"
  [[ -n "$CLAUDE_BIN" ]] || blocked "Claude Code CLI not found"
  [[ -n "$BWRAP_BIN" ]] || blocked "Bubblewrap is required for --run-live"
  NORI_BIN="${NORI_BIN:-$(command -v sks || command -v nori-skillsets || true)}"
  [[ -n "$NORI_BIN" ]] || blocked "Nori CLI not found"
  CLAUDE_REAL="$(readlink -f "$CLAUDE_BIN")"
  [[ -f "$CLAUDE_REAL" && -x "$CLAUDE_REAL" ]] || blocked "Claude Code executable cannot be resolved"
  CLAUDE_VERSION="$("$CLAUDE_BIN" --version | head -n 1)"
  NORI_VERSION="$("$NORI_BIN" --version | head -n 1)"
  install_with_nori
else
  install_source_fixture
fi

locate_installed_roots
python3 "$ROOT/tests/validate-installed-subagents.py" \
  --installed-agents-dir "$INSTALLED_AGENTS_DIR" \
  --installed-skills-dir "$INSTALLED_SKILLS_DIR"
run_direct_probes

if [[ "$MODE" == "run-live" ]]; then
  "$CLAUDE_BIN" --help | grep -q -- '--permission-mode' || blocked "Claude Code does not advertise --permission-mode"
  "$CLAUDE_BIN" --help | grep -q -- '--dangerously-skip-permissions' || blocked "Claude Code does not advertise --dangerously-skip-permissions"
  # The live model probes are constrained to the generated home and loopback fixture.
  # Bubblewrap availability is mandatory before either permissive form is invoked.
  BWRAP_ARGS=(
    --die-with-parent --new-session --unshare-user --unshare-pid --unshare-ipc --unshare-uts
    --ro-bind /usr /usr
    --dev /dev --proc /proc --tmpfs /tmp
    --bind "$WORK_REAL" "$WORK_REAL"
    --dir /opt --ro-bind "$CLAUDE_REAL" /opt/claude
    --chdir "$WORK_REAL/probes"
  )
  add_runtime_path() {
    local path="$1" target
    [[ -e "$path" || -L "$path" ]] || return 0
    if [[ -L "$path" ]]; then
      target="$(readlink "$path")"
      BWRAP_ARGS+=(--symlink "$target" "$path")
    else
      BWRAP_ARGS+=(--ro-bind "$path" "$path")
    fi
  }
  add_runtime_path /bin
  add_runtime_path /lib
  add_runtime_path /lib64
  BWRAP_ARGS+=(--dir /etc)
  add_readonly_etc() {
    local path="$1" source
    [[ -e "$path" || -L "$path" ]] || return 0
    source="$(readlink -f "$path")"
    BWRAP_ARGS+=(--ro-bind "$source" "$path")
  }
  add_readonly_etc /etc/resolv.conf
  add_readonly_etc /etc/hosts
  add_readonly_etc /etc/nsswitch.conf
  add_readonly_etc /etc/ssl
  add_readonly_etc /etc/ca-certificates.conf
  "$BWRAP_BIN" "${BWRAP_ARGS[@]}" /usr/bin/true || blocked "Bubblewrap isolation preflight failed"
  PROBE_ENV=(
    "HOME=$WORK_REAL/home"
    "CLAUDE_CONFIG_DIR=$WORK_REAL/home/.claude"
    "HISTFILE=/dev/null"
    "PATH=/usr/bin:/bin"
    "TMPDIR=/tmp"
    "CLAUDE_CODE_SKIP_PROMPT_HISTORY=1"
    "CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1"
  )
  for key in "${ALLOWED_CLAUDE_ENV[@]}"; do
    if [[ -v "$key" ]]; then PROBE_ENV+=("$key=${!key}"); fi
  done
  CLAUDE_ENV_PIPE="$WORK/probes/claude-env.pipe"
  mkfifo "$CLAUDE_ENV_PIPE"
  python3 "$ROOT/tests/load-claude-env.py" "$SOURCE_CLAUDE_SETTINGS" \
    "${ALLOWED_CLAUDE_ENV[@]}" >"$CLAUDE_ENV_PIPE" &
  ENV_LOADER_PID=$!
  while IFS= read -r -d '' entry; do
    key="${entry%%=*}"
    if [[ ! -v "$key" ]]; then PROBE_ENV+=("$entry"); fi
  done <"$CLAUDE_ENV_PIPE"
  set +e
  wait "$ENV_LOADER_PID"
  ENV_LOADER_STATUS=$?
  set -e
  unset ENV_LOADER_PID
  rm -f "$CLAUDE_ENV_PIPE"
  [[ $ENV_LOADER_STATUS -eq 0 ]] || blocked "Claude environment import failed"
  READY_FILE="$WORK/probes/http.ready"
  REQUEST_LOG="$WORK/probes/http.requests"
  python3 "$ROOT/tests/loopback-http-fixture.py" \
    --port 0 --ready-file "$READY_FILE" --request-log "$REQUEST_LOG" \
    >"$WORK/probes/http.stderr" 2>&1 &
  SERVER_PID=$!
  for _ in {1..100}; do
    [[ -f "$READY_FILE" ]] && break
    kill -0 "$SERVER_PID" 2>/dev/null || blocked "loopback HTTP fixture exited before readiness"
    sleep 0.05
  done
  [[ -f "$READY_FILE" ]] || blocked "loopback HTTP fixture readiness timed out"
  LOOPBACK_PORT="$(<"$READY_FILE")"
  [[ "$LOOPBACK_PORT" =~ ^[0-9]+$ ]] || blocked "loopback HTTP fixture returned an invalid port"
  timeout 180 env -i "${PROBE_ENV[@]}" "$BWRAP_BIN" "${BWRAP_ARGS[@]}" \
    /opt/claude -p 'Run exactly one Bash command: uname -a. Stop after reporting its result.' \
      --agent diagnostic-operator --permission-mode bypassPermissions \
      --no-session-persistence >"$WORK/probes/claude-mode.jsonl"
  timeout 180 env -i "${PROBE_ENV[@]}" "$BWRAP_BIN" "${BWRAP_ARGS[@]}" \
    /opt/claude -p "Run exactly one Bash command: curl -X POST http://127.0.0.1:$LOOPBACK_PORT/reload. Stop after reporting its result." \
      --agent diagnostic-operator --dangerously-skip-permissions \
      --no-session-persistence >"$WORK/probes/claude-dangerous.jsonl"
  grep -Fxq 'POST /reload' "$REQUEST_LOG" || blocked "dangerous-mode probe did not reach the loopback fixture"
  rm -f "$WORK/probes/claude-mode.jsonl" "$WORK/probes/claude-dangerous.jsonl" \
    "$READY_FILE" "$REQUEST_LOG" "$WORK/probes/http.stderr"
fi

scan_retained_artifacts
record_versions
echo "live command guard $MODE passed"
