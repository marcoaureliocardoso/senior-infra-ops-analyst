#!/usr/bin/env bash
set -euo pipefail

PATH="/usr/bin:/mingw64/bin:${PATH:-}"
export PATH
umask 077

blocked() {
  printf 'BLOCKED: %s\n' "$*" >&2
  exit 2
}

failed() {
  printf 'FAILED: %s\n' "$*" >&2
  exit 1
}

MODE=""
KEEP_ARTIFACTS=0
for option in "$@"; do
  case "$option" in
    --self-test|--run-live)
      [[ -z "$MODE" ]] || blocked "select exactly one execution mode"
      MODE="$option"
      ;;
    --keep-artifacts) KEEP_ARTIFACTS=1 ;;
    *) blocked "usage: $0 --self-test|--run-live [--keep-artifacts]" ;;
  esac
done
[[ -n "$MODE" ]] || MODE="--self-test"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
SOURCE_CLAUDE_SETTINGS="${CLAUDE_SETTINGS_SOURCE:-${CLAUDE_CONFIG_DIR:-$HOME/.claude}/settings.json}"
ALLOWED_CLAUDE_ENV=(
  ANTHROPIC_AUTH_TOKEN ANTHROPIC_API_KEY ANTHROPIC_BASE_URL ANTHROPIC_MODEL
  ANTHROPIC_DEFAULT_HAIKU_MODEL ANTHROPIC_DEFAULT_OPUS_MODEL
  ANTHROPIC_DEFAULT_SONNET_MODEL CLAUDE_CODE_SUBAGENT_MODEL
  CLAUDE_CODE_EFFORT_LEVEL
)
LIVE_ACK='I_ACCEPT_PROVIDER_CREDENTIAL_EGRESS_RISK'
if [[ "$MODE" == "--run-live" ]]; then
  [[ "${P0_04A_LIVE_NORMAL_CREDENTIALS_ACK:-}" == "$LIVE_ACK" ]] || \
    blocked "set P0_04A_LIVE_NORMAL_CREDENTIALS_ACK=$LIVE_ACK for the isolated live provider test"
  printf '%s\n' 'WARNING: normal provider credentials enter Claude Code; Bubblewrap reduces but cannot eliminate provider-egress risk.' >&2
fi

TMP_PARENT="${TMPDIR:-/tmp}"
WORK="$(mktemp -d "$TMP_PARENT/p0-04a-context.XXXXXX")"
WORK_REAL="$(readlink -f "$WORK")"
case "$WORK_REAL" in
  "$(readlink -f "$TMP_PARENT")"/p0-04a-context.*) ;;
  *) blocked "temporary directory escaped the verified runner prefix" ;;
esac
PROBES="$WORK_REAL/probes"
EVIDENCE="$PROBES/context-continuity-evidence.json"

delete_content_captures() {
  find "$PROBES" -type f \( \
    -name '*.jsonl' -o -name '*.pty' -o -name '*.transcript' -o -name '*.requests' \
  \) -delete 2>/dev/null || true
}

cleanup() {
  if [[ -n "${ENV_LOADER_PID:-}" ]]; then kill "$ENV_LOADER_PID" 2>/dev/null || true; fi
  if [[ -n "${SERVER_PID:-}" ]]; then kill "$SERVER_PID" 2>/dev/null || true; fi
  if [[ $KEEP_ARTIFACTS -eq 1 ]]; then
    printf 'Artifacts retained at %s; warning: this directory contains model content.\n' "$WORK_REAL" >&2
  else
    delete_content_captures
    rm -rf -- "$WORK_REAL"
  fi
}
trap cleanup EXIT

command -v node >/dev/null 2>&1 || blocked "Node.js not found"
command -v python3 >/dev/null 2>&1 || blocked "python3 not found"
export HOME="$WORK/home"
export CLAUDE_CONFIG_DIR="$HOME/.claude"
export HISTFILE=/dev/null
unset AWS_PROFILE AZURE_CONFIG_DIR CLOUDSDK_CONFIG KUBECONFIG
unset GOOGLE_APPLICATION_CREDENTIALS AZURE_CLIENT_SECRET AWS_SECRET_ACCESS_KEY
unset CLAUDE_CODE_AUTO_COMPACT_WINDOW
mkdir -p "$CLAUDE_CONFIG_DIR" "$PROBES" "$WORK/project/.claude"

find_forbidden_evidence() {
  python3 - "$1" <<'PY'
import json
import sys
from pathlib import Path

forbidden = {
    "content", "prompt", "response", "summary", "transcript", "tool_input",
    "tool_result", "command", "header", "credential", "secret", "token",
}
try:
    value = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
except (OSError, UnicodeError, json.JSONDecodeError):
    raise SystemExit(1)

def walk(item):
    if isinstance(item, dict):
        for key, child in item.items():
            if key.lower() in forbidden:
                raise SystemExit(1)
            walk(child)
    elif isinstance(item, list):
        for child in item:
            walk(child)

walk(value)
serialized = json.dumps(value, sort_keys=True)
if any(marker.lower() in serialized.lower() for marker in (
    "SYNTH_SECRET", "synthetic prompt", "tool output", "compact summary"
)):
    raise SystemExit(1)
PY
}

assert_evidence() {
  find_forbidden_evidence "$EVIDENCE" || failed "retained evidence contains a forbidden field or marker"
  python3 - "$EVIDENCE" <<'PY'
import json
import sys
from pathlib import Path
report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
runtime = report["runtime"]
if runtime["context"]["compactionCount"] != 1:
    raise SystemExit("expected one normalized compaction")
if not runtime["tasks"]["survivedCompaction"]:
    raise SystemExit("native task identifiers did not survive compaction")
if runtime["tools"]["reasonCode"] not in {
    "TOOL_SEARCH_AVAILABLE", "TOOL_SEARCH_UNAVAILABLE_GATEWAY", "TOOL_SEARCH_NOT_OBSERVED"
}:
    raise SystemExit("invalid tool-search capability result")
PY
}

run_self_test() {
  local events="$PROBES/self-test.jsonl" unavailable="$PROBES/unavailable.jsonl"
  local consistent="$PROBES/consistent.jsonl" consistent_report="$PROBES/consistent-evidence.json"
  printf '%s\n' \
    '{"kind":"context","stage":"before","percent":73,"prompt":"synthetic prompt SYNTH_SECRET"}' \
    '{"kind":"task","action":"created","family":"TaskCreate","identifier":"P004A_TASK_A","tool_input":"SYNTH_SECRET"}' \
    '{"kind":"task","action":"created","family":"TodoWrite","identifier":"P004A_TASK_B"}' \
    '{"kind":"task","action":"completed","family":"TaskUpdate","identifier":"P004A_TASK_A"}' \
    '{"kind":"compact","phase":"PreCompact","custom_instructions":"SYNTH_SECRET"}' \
    '{"kind":"compact","phase":"PostCompact","compact_summary":"SYNTH_SECRET compact summary"}' \
    '{"kind":"task","action":"observed-after","family":"TaskCreate","identifier":"P004A_TASK_A"}' \
    '{"kind":"task","action":"observed-after","family":"TodoWrite","identifier":"P004A_TASK_B"}' \
    '{"kind":"tool-snapshot","stage":"before","visibleCount":18}' \
    '{"kind":"tool-search","available":true}' \
    '{"kind":"tool-snapshot","stage":"after","visibleCount":7}' \
    '{"kind":"context","stage":"after","percent":19,"response":"tool output"}' \
    '{"kind":"window","reportedWindow":128000,"observedWindow":64000,"absoluteOverrideApplied":true}' \
    >"$events"
  node "$ROOT/skills/context-continuity/scripts/context-inventory.mjs" \
    --root "$ROOT" --runtime-jsonl "$events" >"$EVIDENCE"
  assert_evidence
  python3 - "$EVIDENCE" <<'PY'
import json, sys
from pathlib import Path
r = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))["runtime"]
assert r["tasks"]["toolFamily"] == "MixedNativeTasks"
assert r["tasks"]["createdCount"] == 2 and r["tasks"]["completedCount"] == 1
assert r["tools"]["reasonCode"] == "TOOL_SEARCH_AVAILABLE"
assert r["window"]["reasonCode"] == "WINDOW_REPORTING_DIVERGENCE"
assert r["window"]["absoluteOverrideEvidenceGated"] is True
PY

  printf '%s\n' '{"kind":"tool-search","available":false,"gatewayUnavailable":true}' >"$unavailable"
  node "$ROOT/skills/context-continuity/scripts/context-inventory.mjs" \
    --root "$ROOT" --runtime-jsonl "$unavailable" >"$PROBES/unavailable-evidence.json"
  python3 - "$PROBES/unavailable-evidence.json" <<'PY'
import json, sys
from pathlib import Path
r = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))["runtime"]
assert r["tools"]["reasonCode"] == "TOOL_SEARCH_UNAVAILABLE_GATEWAY"
PY

  printf '%s\n' '{"kind":"window","reportedWindow":64000,"observedWindow":64000}' >"$consistent"
  node "$ROOT/skills/context-continuity/scripts/context-inventory.mjs" \
    --root "$ROOT" --runtime-jsonl "$consistent" >"$consistent_report"
  python3 - "$consistent_report" <<'PY'
import json, sys
from pathlib import Path
r = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))["runtime"]["window"]
assert r["reasonCode"] == "WINDOW_REPORTING_CONSISTENT"
assert r["absoluteOverrideEvidenceGated"] is False
PY

  printf '%s\n' '{"summary":"SYNTH_SECRET deliberately unsafe"}' >"$PROBES/unsafe-evidence.json"
  if find_forbidden_evidence "$PROBES/unsafe-evidence.json"; then
    failed "forbidden-content scanner accepted an unsafe retained fixture"
  fi
  rm -f -- "$PROBES/unsafe-evidence.json" "$PROBES/unavailable-evidence.json" "$consistent_report"
  delete_content_captures
  printf '%s\n' 'live context continuity parser self-test passed'
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
  INSTALLED_AGENTS_DIR="$CLAUDE_CONFIG_DIR/agents"
  INSTALLED_SKILLS_DIR="$CLAUDE_CONFIG_DIR/skills"
  if [[ ! -f "$INSTALLED_AGENTS_DIR/diagnostic-operator.md" ]]; then
    local agent
    agent="$(find "$CLAUDE_CONFIG_DIR" -type f -name diagnostic-operator.md -print -quit)"
    [[ -n "$agent" ]] || blocked "installed agents directory not found"
    INSTALLED_AGENTS_DIR="$(dirname "$agent")"
  fi
  if [[ ! -f "$INSTALLED_SKILLS_DIR/context-continuity/SKILL.md" ]]; then
    local skill
    skill="$(find "$CLAUDE_CONFIG_DIR" -type f -path '*/context-continuity/SKILL.md' -print -quit)"
    [[ -n "$skill" ]] || blocked "installed continuity skill not found"
    INSTALLED_SKILLS_DIR="$(dirname "$(dirname "$skill")")"
  fi
}

configure_and_verify_preservation() {
  python3 - "$WORK/project/.claude/settings.local.json" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
p.write_text(json.dumps({
    "model": "operator-model",
    "env": {"OPERATOR_PREFERENCE_BEFORE": "keep"},
    "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "/operator/stop"}]}]},
}) + "\n", encoding="utf-8")
PY
  CONFIGURATOR="$INSTALLED_SKILLS_DIR/context-continuity/scripts/configure-context-continuity.mjs"
  node "$CONFIGURATOR" --apply --scope project --root "$WORK/project" \
    --claude-config-dir "$CLAUDE_CONFIG_DIR" --status-line >/dev/null
  python3 - "$WORK/project/.claude/settings.local.json" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1]); value = json.loads(p.read_text(encoding="utf-8"))
assert value["model"] == "operator-model"
assert value["env"]["OPERATOR_PREFERENCE_BEFORE"] == "keep"
assert value["env"]["CLAUDE_AUTOCOMPACT_PCT_OVERRIDE"] == "72"
assert "CLAUDE_CODE_AUTO_COMPACT_WINDOW" not in value["env"]
assert len(value["hooks"]["PreCompact"]) == 1 and len(value["hooks"]["PostCompact"]) == 1
value["env"]["OPERATOR_PREFERENCE_AFTER"] = "keep"
p.write_text(json.dumps(value) + "\n", encoding="utf-8")
PY
  "$NORI_BIN" --install-dir "$CLAUDE_CONFIG_DIR" --agent claude-code \
    switch senior-infra-ops-analyst --agent claude-code
  python3 - "$WORK/project/.claude/settings.local.json" <<'PY'
import json, sys
from pathlib import Path
v = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert v["env"]["OPERATOR_PREFERENCE_BEFORE"] == "keep"
assert v["env"]["OPERATOR_PREFERENCE_AFTER"] == "keep"
assert v["hooks"]["Stop"][0]["hooks"][0]["command"] == "/operator/stop"
PY
}

load_provider_environment() {
  CLAUDE_ENV_PIPE="$PROBES/claude-env.pipe"
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
  status=$?
  set -e
  unset ENV_LOADER_PID
  rm -f -- "$CLAUDE_ENV_PIPE"
  [[ $status -eq 0 ]] || blocked "allowlisted Claude environment import failed"
}

run_installed_credential_compaction_probe() {
  local guard="$INSTALLED_SKILLS_DIR/command-driven-operations/scripts/validate-ops-command.mjs"
  local recorder="$INSTALLED_SKILLS_DIR/command-driven-operations/scripts/record-command-approval.mjs"
  local compact="$INSTALLED_SKILLS_DIR/context-continuity/scripts/compact-hook.mjs"
  local secret="SYNTH_SECRET_$$_p004a" first="$PROBES/credential-first.jsonl"
  local post="$PROBES/credential-post.jsonl" compact_event="$PROBES/compact.jsonl"
  python3 - "$secret" >"$first" <<'PY'
import json, sys
print(json.dumps({"session_id":"p004a-live-session","tool_use_id":"p004a-first","hook_event_name":"PreToolUse","agent_type":"diagnostic-operator","permission_mode":"bypassPermissions","tool_name":"Bash","tool_input":{"command":f'OPS_CREDENTIAL_IDENTITY=operator curl -q -H "Authorization: Bearer {sys.argv[1]}" http://127.0.0.1:43119/health'}}))
PY
  output="$(OPS_COMMAND_GUARD_STATE_DIR="$PROBES/bindings" node "$guard" <"$first")"
  python3 - "$output" <<'PY'
import json, sys
assert json.loads(sys.argv[1])["hookSpecificOutput"]["permissionDecision"] == "ask"
PY
  printf '%s\n' '{"session_id":"p004a-live-session","tool_use_id":"p004a-first","hook_event_name":"PostToolUse","tool_name":"Bash"}' >"$post"
  OPS_COMMAND_GUARD_STATE_DIR="$PROBES/bindings" node "$recorder" <"$post"
  printf '%s\n' '{"session_id":"p004a-live-session","hook_event_name":"PreCompact","trigger":"manual"}' >"$compact_event"
  OPS_COMMAND_GUARD_STATE_DIR="$PROBES/bindings" node "$compact" pre <"$compact_event"
  python3 - "$secret" >"$first" <<'PY'
import json, sys
print(json.dumps({"session_id":"p004a-live-session","tool_use_id":"p004a-second","hook_event_name":"PreToolUse","agent_type":"diagnostic-operator","permission_mode":"bypassPermissions","tool_name":"Bash","tool_input":{"command":f'OPS_CREDENTIAL_IDENTITY=operator curl -q -H "Authorization: Bearer {sys.argv[1]}" http://127.0.0.1:43119/health'}}))
PY
  output="$(OPS_COMMAND_GUARD_STATE_DIR="$PROBES/bindings" node "$guard" <"$first")"
  python3 - "$output" <<'PY'
import json, sys
assert json.loads(sys.argv[1])["hookSpecificOutput"]["permissionDecision"] == "ask"
PY
}

normalize_live_capture() {
  python3 - "$PROBES/manual.pty" "$PROBES/live-events.jsonl" <<'PY'
import json, re, sys
from pathlib import Path
text = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
events = []
percentages = [int(v) for v in re.findall(r"(?<!\d)(\d{1,3})%", text) if 0 <= int(v) <= 100]
if percentages:
    events.append({"kind":"context","stage":"before","percent":percentages[0]})
    events.append({"kind":"context","stage":"after","percent":percentages[-1]})
for identifier in ("P004A_TASK_A", "P004A_TASK_B"):
    if text.count(identifier) >= 2:
        events.extend([
            {"kind":"task","action":"created","family":"TaskCreate","identifier":identifier},
            {"kind":"task","action":"observed-after","family":"TaskCreate","identifier":identifier},
        ])
if re.search(r"compact(?:ed|ion|ing)|context compact", text, re.I):
    events.append({"kind":"compact","phase":"PostCompact"})
if re.search(r"tool[_ -]?search|tool_reference", text, re.I):
    events.append({"kind":"tool-search","available":True})
else:
    events.append({"kind":"tool-search","available":False,"gatewayUnavailable":True})
with Path(sys.argv[2]).open("w", encoding="utf-8") as stream:
    for event in events:
        stream.write(json.dumps(event) + "\n")
PY
  node "$INSTALLED_SKILLS_DIR/context-continuity/scripts/context-inventory.mjs" \
    --root "$ROOT" --runtime-jsonl "$PROBES/live-events.jsonl" >"$EVIDENCE"
}

run_live() {
  CLAUDE_BIN="${CLAUDE_BIN:-$(command -v claude || true)}"
  BWRAP_BIN="${BWRAP_BIN:-$(command -v bwrap || true)}"
  [[ -n "$CLAUDE_BIN" ]] || blocked "Claude Code CLI not found"
  [[ -n "$BWRAP_BIN" ]] || blocked "Bubblewrap is required for --run-live"
  command -v timeout >/dev/null 2>&1 || blocked "timeout not found"
  command -v script >/dev/null 2>&1 || blocked "pseudo-terminal script utility not found"
  install_with_nori
  locate_installed_roots
  python3 "$ROOT/tests/validate-installed-subagents.py" \
    --installed-agents-dir "$INSTALLED_AGENTS_DIR" \
    --installed-skills-dir "$INSTALLED_SKILLS_DIR"
  configure_and_verify_preservation
  run_installed_credential_compaction_probe

  CLAUDE_REAL="$(readlink -f "$CLAUDE_BIN")"
  [[ -f "$CLAUDE_REAL" && -x "$CLAUDE_REAL" ]] || blocked "Claude Code executable cannot be resolved"
  BWRAP_ARGS=(
    --die-with-parent --new-session --unshare-user --unshare-pid --unshare-ipc --unshare-uts
    --ro-bind /usr /usr --dev /dev --proc /proc --tmpfs /tmp
    --bind "$WORK_REAL" "$WORK_REAL" --dir /opt --ro-bind "$CLAUDE_REAL" /opt/claude
    --chdir "$WORK_REAL/project"
  )
  for runtime_path in /bin /lib /lib64; do
    [[ -e "$runtime_path" || -L "$runtime_path" ]] || continue
    if [[ -L "$runtime_path" ]]; then
      BWRAP_ARGS+=(--symlink "$(readlink "$runtime_path")" "$runtime_path")
    else
      BWRAP_ARGS+=(--ro-bind "$runtime_path" "$runtime_path")
    fi
  done
  BWRAP_ARGS+=(--dir /etc)
  for etc_path in /etc/resolv.conf /etc/hosts /etc/nsswitch.conf /etc/ssl /etc/ca-certificates.conf; do
    [[ -e "$etc_path" || -L "$etc_path" ]] || continue
    BWRAP_ARGS+=(--ro-bind "$(readlink -f "$etc_path")" "$etc_path")
  done
  "$BWRAP_BIN" "${BWRAP_ARGS[@]}" /usr/bin/true || blocked "Bubblewrap isolation preflight failed"
  isolated_uid="$("$BWRAP_BIN" "${BWRAP_ARGS[@]}" /usr/bin/id -u)"
  [[ "$isolated_uid" != "0" ]] || blocked "Bubblewrap live process resolved to root"

  PROBE_ENV=(
    "HOME=$WORK_REAL/home" "CLAUDE_CONFIG_DIR=$WORK_REAL/home/.claude"
    "HISTFILE=/dev/null" "PATH=/usr/bin:/bin" "TMPDIR=/tmp"
    "CLAUDE_CODE_SKIP_PROMPT_HISTORY=1" "CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1"
  )
  for key in "${ALLOWED_CLAUDE_ENV[@]}"; do
    if [[ -v "$key" ]]; then PROBE_ENV+=("$key=${!key}"); fi
  done
  load_provider_environment

  printf '%s\n' \
    'Create native tasks named P004A_TASK_A and P004A_TASK_B. Complete only P004A_TASK_A.' \
    '/context' \
    '/compact Preserve task identifiers and immediate next action' \
    'Read the native task list and report both task identifiers only.' \
    '/exit' >"$PROBES/manual.input"
  set +e
  timeout 600 env -i "${PROBE_ENV[@]}" "$BWRAP_BIN" "${BWRAP_ARGS[@]}" \
    /usr/bin/script --quiet --return --command "/opt/claude --agent diagnostic-operator" \
    "$PROBES/manual.pty" <"$PROBES/manual.input" >"$PROBES/manual.transcript" 2>&1
  manual_status=$?
  set -e
  [[ $manual_status -eq 0 ]] || blocked "manual compact PTY capability unavailable or failed"

  # The automatic probe deliberately lowers only its process-scoped percentage.
  set +e
  timeout 600 env -i "${PROBE_ENV[@]}" CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=5 \
    "$BWRAP_BIN" "${BWRAP_ARGS[@]}" /opt/claude -p \
    'Create one native task P004A_AUTO, then emit bounded repetitive synthetic text until automatic compaction occurs; read the task list afterward.' \
    --output-format stream-json >"$PROBES/automatic.jsonl" 2>"$PROBES/automatic.transcript"
  automatic_status=$?
  set -e
  [[ $automatic_status -eq 0 ]] || blocked "automatic compact capability unavailable or failed"

  normalize_live_capture
  assert_evidence

  # An absolute override is diagnostic-only and can be enabled only after numeric divergence evidence.
  if python3 - "$EVIDENCE" <<'PY'
import json, sys
from pathlib import Path
w = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))["runtime"]["window"]
raise SystemExit(0 if w["reasonCode"] == "WINDOW_REPORTING_DIVERGENCE" else 1)
PY
  then
    CLAUDE_CODE_AUTO_COMPACT_WINDOW="${P0_04A_MOCK_WINDOW_OVERRIDE:-64000}"
    export CLAUDE_CODE_AUTO_COMPACT_WINDOW
  else
    unset CLAUDE_CODE_AUTO_COMPACT_WINDOW
  fi

  find_forbidden_evidence "$EVIDENCE" || failed "live evidence failed forbidden-content scan"
  python3 - "$EVIDENCE" <<'PY'
import json, sys
from pathlib import Path
print(json.dumps(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")), sort_keys=True))
PY
  delete_content_captures
  printf '%s\n' 'live context continuity run-live passed'
}

if [[ "$MODE" == "--self-test" ]]; then
  run_self_test
else
  run_live
fi
