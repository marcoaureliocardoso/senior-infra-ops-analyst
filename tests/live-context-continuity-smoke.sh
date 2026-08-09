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

last_driver_stage() {
  python3 - "$1" <<'PY'
import json, sys
from pathlib import Path
path = Path(sys.argv[1])
stage = "no-event"
if path.is_file():
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict) and isinstance(event.get("stage"), str):
            stage = event["stage"]
print(stage)
PY
}

driver_stage_percent() {
  python3 - "$1" "$2" <<'PY'
import json, sys
from pathlib import Path
value = "unavailable"
path = Path(sys.argv[1])
if path.is_file():
    for line in path.read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        if event.get("stage") == sys.argv[2] and isinstance(event.get("percent"), int):
            value = str(event["percent"])
print(value)
PY
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
    -o -name '*.prompt' \
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

seed_isolated_onboarding() {
  python3 - "$HOME/.claude.json" "$CLAUDE_CONFIG_DIR/settings.json" "$WORK/project" "$1" <<'PY'
import json, sys
from pathlib import Path
target, settings_path, project = map(Path, sys.argv[1:4])
version = sys.argv[4]
target.write_text(json.dumps({
    "hasCompletedOnboarding": True,
    "lastOnboardingVersion": version,
    "projects": {str(project.resolve()): {
        "hasCompletedProjectOnboarding": True,
        "hasTrustDialogAccepted": True,
        "projectOnboardingSeenCount": 1,
    }},
}) + "\n", encoding="utf-8")
settings = json.loads(settings_path.read_text(encoding="utf-8")) if settings_path.exists() else {}
settings["theme"] = "dark"
settings_path.write_text(json.dumps(settings) + "\n", encoding="utf-8")
PY
}

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
if runtime["context"]["compactionCount"] != 3:
    raise SystemExit("expected focused manual, unfocused manual, and automatic compaction")
if not runtime["tasks"]["survivedCompaction"]:
    raise SystemExit("native task identifiers did not survive compaction")
if runtime["context"]["roleCount"] != 13:
    raise SystemExit("main plus all 12 subagent context probes were not observed")
if runtime["context"]["skillUseCount"] != 2:
    raise SystemExit("repeated skill context impact was not observed")
if runtime["mcp"]["connectedCount"] != 1 or runtime["mcp"]["visibleToolCount"] != 1:
    raise SystemExit("disposable MCP connection or visible tool count is missing")
if runtime["mcp"]["beforePercent"] is None or runtime["mcp"]["afterPercent"] is None:
    raise SystemExit("MCP before/after context measurements are missing")
if not runtime["window"]["absoluteOverrideEvidenceGated"]:
    raise SystemExit("mock window override was not gated by observed divergence")
if not all(runtime["session"].values()):
    raise SystemExit("resume rewind or isolated clear evidence is missing")
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
    '{"kind":"compact","phase":"PreCompact","trigger":"auto"}' \
    '{"kind":"compact","phase":"PostCompact","trigger":"auto"}' \
    '{"kind":"compact","phase":"PreCompact","trigger":"manual"}' \
    '{"kind":"compact","phase":"PostCompact","trigger":"manual"}' \
    '{"kind":"task","action":"observed-after","family":"TaskCreate","identifier":"P004A_TASK_A"}' \
    '{"kind":"task","action":"observed-after","family":"TodoWrite","identifier":"P004A_TASK_B"}' \
    '{"kind":"tool-snapshot","stage":"before","visibleCount":18}' \
    '{"kind":"tool-search","available":true}' \
    '{"kind":"tool-snapshot","stage":"after","visibleCount":7}' \
    '{"kind":"context","stage":"after","percent":19,"response":"tool output"}' \
    '{"kind":"session","action":"resume-tasks"}' \
    '{"kind":"session","action":"rewind-tasks"}' \
    '{"kind":"session","action":"rewind-context"}' \
    '{"kind":"session","action":"rewind-authorization-invalid"}' \
    '{"kind":"session","action":"clear-isolated"}' \
    '{"kind":"skill-use","percent":17}' \
    '{"kind":"skill-use","percent":21}' \
    '{"kind":"mcp","connectedCount":1,"visibleToolCount":1,"beforePercent":2,"afterPercent":3}' \
    '{"kind":"window","reportedWindow":128000,"observedWindow":64000,"absoluteOverrideApplied":true}' \
    >"$events"
  for percent in 3 4 5 6 7 8 9 10 11 12 13 14 15; do
    printf '%s\n' "{\"kind\":\"context-role\",\"percent\":$percent}" >>"$events"
  done
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
  printf '%s' 'runtime-model[1m] ctx 3%' >"$PROBES/manual.pty"
  build_automatic_filler
  python3 - "$PROBES/automatic.prompt" <<'PY'
import sys
from pathlib import Path
p = Path(sys.argv[1])
assert p.stat().st_size == 420_000
assert p.read_text(encoding="utf-8").startswith(" probe probe")
PY
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
    "cleanupPeriodDays": 30,
    "env": {"OPERATOR_PREFERENCE_BEFORE": "keep"},
    "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "/operator/stop"}]}]},
}) + "\n", encoding="utf-8")
PY
  CONFIGURATOR="$INSTALLED_SKILLS_DIR/context-continuity/scripts/configure-context-continuity.mjs"
  node "$CONFIGURATOR" --apply --scope project --root "$WORK/project" \
    --claude-config-dir "$CLAUDE_CONFIG_DIR" >/dev/null
  if python3 - "$CLAUDE_CONFIG_DIR/settings.json" <<'PY'
import json, sys
from pathlib import Path
value = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
raise SystemExit(0 if "statusLine" in value else 1)
PY
  then
    set +e
    node "$CONFIGURATOR" --apply --scope project --root "$WORK/project" \
      --claude-config-dir "$CLAUDE_CONFIG_DIR" --status-line \
      >"$PROBES/status-line-conflict.json"
    status_line_status=$?
    set -e
    [[ $status_line_status -eq 2 ]] || failed "inherited Nori status line was not preserved"
  else
    node "$CONFIGURATOR" --apply --scope project --root "$WORK/project" \
      --claude-config-dir "$CLAUDE_CONFIG_DIR" --status-line >/dev/null
  fi
  python3 - "$WORK/project/.claude/settings.local.json" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1]); value = json.loads(p.read_text(encoding="utf-8"))
assert value["cleanupPeriodDays"] == 30
assert value["env"]["OPERATOR_PREFERENCE_BEFORE"] == "keep"
assert value["env"]["CLAUDE_AUTOCOMPACT_PCT_OVERRIDE"] == "72"
assert "CLAUDE_CODE_AUTO_COMPACT_WINDOW" not in value["env"]
assert len(value["hooks"]["PreCompact"]) == 1 and len(value["hooks"]["PostCompact"]) == 1
if "statusLine" in value:
    assert value["statusLine"]["type"] == "command"
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

install_live_compact_observer() {
  local recorder="$WORK/project/.claude/live-compact-event-recorder.py"
  local destination="$PROBES/live-compact-hook-events.jsonl"
  cp "$ROOT/tests/live-compact-event-recorder.py" "$recorder"
  chmod 0500 "$recorder"
  python3 - "$WORK/project/.claude/settings.local.json" "$recorder" "$destination" <<'PY'
import json, sys
from pathlib import Path

settings_path, recorder_path, destination_path = map(Path, sys.argv[1:4])
settings = json.loads(settings_path.read_text(encoding="utf-8"))
observer = {
    "hooks": [{
        "type": "command",
        "command": "/usr/bin/python3",
        "args": [str(recorder_path.resolve()), str(destination_path.resolve())],
        "timeout": 5,
    }],
}

for event in ("PreCompact", "PostCompact"):
    settings.setdefault("hooks", {}).setdefault(event, []).append(observer)
settings_path.write_text(json.dumps(settings) + "\n", encoding="utf-8")
PY
}

set_live_compact_observer_destination() {
  python3 - "$WORK/project/.claude/settings.local.json" \
    "$WORK/project/.claude/live-compact-event-recorder.py" "$1" <<'PY'
import json, sys
from pathlib import Path
settings_path, recorder_path, destination_path = map(Path, sys.argv[1:4])
settings = json.loads(settings_path.read_text(encoding="utf-8"))
changed = 0
for phase in ("PreCompact", "PostCompact"):
    for group in settings.get("hooks", {}).get(phase, []):
        for hook in group.get("hooks", []):
            args = hook.get("args")
            if hook.get("command") == "/usr/bin/python3" and isinstance(args, list) and args and args[0] == str(recorder_path.resolve()):
                hook["args"] = [str(recorder_path.resolve()), str(destination_path.resolve())]
                changed += 1
if changed != 2:
    raise SystemExit("live compact observer could not be retargeted exactly")
settings_path.write_text(json.dumps(settings) + "\n", encoding="utf-8")
PY
}

verify_real_manual_compact_pairs() {
  python3 - "$PROBES/live-compact-hook-events.jsonl" <<'PY'
import json, sys
from pathlib import Path
path = Path(sys.argv[1])
events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
pairs = [(event.get("phase"), event.get("trigger")) for event in events]
expected = [
    ("PreCompact", "manual"), ("PostCompact", "manual"),
    ("PreCompact", "manual"), ("PostCompact", "manual"),
]
if pairs != expected:
    raise SystemExit(f"unexpected structural real manual compaction sequence: {pairs}")
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
    [[ "$key" =~ ^[A-Z][A-Z0-9_]*$ ]] || blocked "allowlisted Claude environment key is invalid"
  done <"$CLAUDE_ENV_PIPE"
  set +e
  wait "$ENV_LOADER_PID"
  status=$?
  set -e
  unset ENV_LOADER_PID
  rm -f -- "$CLAUDE_ENV_PIPE"
  [[ $status -eq 0 ]] || blocked "allowlisted Claude environment import failed"
}

emit_synthetic_credential_event() {
  local session_id="$1" tool_use_id="$2"
  python3 -c 'import json,sys
secret=sys.stdin.read()
q=chr(34)
command=f"OPS_CREDENTIAL_IDENTITY=operator curl -q -H {q}Authorization: Bearer {secret}{q} http://127.0.0.1:43119/health"
print(json.dumps({"session_id":sys.argv[1],"tool_use_id":sys.argv[2],"hook_event_name":"PreToolUse","agent_type":"diagnostic-operator","permission_mode":"bypassPermissions","tool_name":"Bash","tool_input":{"command":command}}))' "$session_id" "$tool_use_id"
}

run_installed_credential_compaction_probe() {
  local guard="$INSTALLED_SKILLS_DIR/command-driven-operations/scripts/validate-ops-command.mjs"
  local recorder="$INSTALLED_SKILLS_DIR/command-driven-operations/scripts/record-command-approval.mjs"
  local compact="$INSTALLED_SKILLS_DIR/context-continuity/scripts/compact-hook.mjs"
  local secret="SYNTH_SECRET_$$_p004a"
  local post="$PROBES/credential-post.jsonl" compact_event="$PROBES/compact.jsonl"
  output="$(printf '%s' "$secret" | emit_synthetic_credential_event p004a-live-session p004a-first | \
    OPS_COMMAND_GUARD_STATE_DIR="$PROBES/bindings" node "$guard")"
  python3 - "$output" <<'PY'
import json, sys
if json.loads(sys.argv[1])["hookSpecificOutput"]["permissionDecision"] != "ask":
    raise SystemExit("synthetic credential did not require initial approval")
PY
  printf '%s\n' '{"session_id":"p004a-live-session","tool_use_id":"p004a-first","hook_event_name":"PostToolUse","tool_name":"Bash"}' >"$post"
  OPS_COMMAND_GUARD_STATE_DIR="$PROBES/bindings" node "$recorder" <"$post"
  printf '%s\n' '{"session_id":"p004a-live-session","hook_event_name":"PreCompact","trigger":"manual"}' >"$compact_event"
  OPS_COMMAND_GUARD_STATE_DIR="$PROBES/bindings" node "$compact" pre <"$compact_event"
  output="$(printf '%s' "$secret" | emit_synthetic_credential_event p004a-live-session p004a-second | \
    OPS_COMMAND_GUARD_STATE_DIR="$PROBES/bindings" node "$guard")"
  python3 - "$output" <<'PY'
import json, sys
if json.loads(sys.argv[1])["hookSpecificOutput"]["permissionDecision"] != "ask":
    raise SystemExit("synthetic credential reuse survived compaction")
PY
}

activate_actual_session_credential_binding() {
  local session_id="$1"
  local guard="$INSTALLED_SKILLS_DIR/command-driven-operations/scripts/validate-ops-command.mjs"
  local recorder="$INSTALLED_SKILLS_DIR/command-driven-operations/scripts/record-command-approval.mjs"
  local secret="SYNTH_SESSION_${session_id}_p004a" output post
  output="$(printf '%s' "$secret" | emit_synthetic_credential_event "$session_id" p004a-session-first | \
    OPS_COMMAND_GUARD_STATE_DIR="$PROBES/bindings" node "$guard")"
  python3 - "$output" <<'PY'
import json, sys
if json.loads(sys.argv[1])["hookSpecificOutput"]["permissionDecision"] != "ask":
    raise SystemExit("actual session credential did not require initial approval")
PY
  post="$(python3 -c 'import json,sys; print(json.dumps({"session_id":sys.argv[1],"tool_use_id":"p004a-session-first","hook_event_name":"PostToolUse","tool_name":"Bash"}))' "$session_id")"
  printf '%s\n' "$post" | OPS_COMMAND_GUARD_STATE_DIR="$PROBES/bindings" node "$recorder"
  output="$(printf '%s' "$secret" | emit_synthetic_credential_event "$session_id" p004a-session-active | \
    OPS_COMMAND_GUARD_STATE_DIR="$PROBES/bindings" node "$guard")"
  python3 - "$output" <<'PY'
import json, sys
if json.loads(sys.argv[1])["hookSpecificOutput"]["permissionDecision"] != "allow":
    raise SystemExit("actual session credential binding did not activate")
PY
}

run_post_rewind_authorization_probe() {
  local session_id="$1"
  local guard="$INSTALLED_SKILLS_DIR/command-driven-operations/scripts/validate-ops-command.mjs"
  local secret="SYNTH_SESSION_${session_id}_p004a" output
  output="$(printf '%s' "$secret" | emit_synthetic_credential_event "$session_id" p004a-after-rewind | \
    OPS_COMMAND_GUARD_STATE_DIR="$PROBES/bindings" node "$guard")"
  python3 - "$output" "$PROBES/rewind-authorization.json" <<'PY'
import json, sys
result = json.loads(sys.argv[1])
if result["hookSpecificOutput"]["permissionDecision"] != "ask":
    raise SystemExit("actual session credential binding was restored by rewind")
with open(sys.argv[2], "w", encoding="utf-8") as stream:
    json.dump({"authorizationInvalidated": True}, stream)
    stream.write("\n")
PY
}

normalize_live_capture() {
  python3 - "$PROBES/manual.pty" "$PROBES/manual-driver.jsonl" \
    "$PROBES/automatic-driver.jsonl" "$PROBES/live-events.jsonl" "$PROBES" <<'PY'
import json, re, sys
from pathlib import Path
manual_path, driver_path, automatic_path, output_path = map(Path, sys.argv[1:5])
probes_path = Path(sys.argv[5])
text = manual_path.read_text(encoding="utf-8", errors="replace")
driver_events = [json.loads(line) for line in driver_path.read_text(encoding="utf-8").splitlines() if line]
passed = {event["stage"] for event in driver_events if event.get("outcome") == "passed"}
events = []
percentages = [int(v) for v in re.findall(r"(?<!\d)(\d{1,3})%", text) if 0 <= int(v) <= 100]
if "context_inspected" in passed and percentages:
    events.append({"kind":"context","stage":"before","percent":percentages[0]})
    events.append({"kind":"context","stage":"after","percent":percentages[-1]})
if "tasks_created" in passed:
    for identifier in ("P004A_TASK_A", "P004A_TASK_B"):
        events.append({"kind":"task","action":"created","family":"TaskCreate","identifier":identifier})
compact_path = probes_path / "live-compact-hook-events.jsonl"
compact_events = [json.loads(line) for line in compact_path.read_text(encoding="utf-8").splitlines() if line]
manual_pairs = [event for event in compact_events if event.get("trigger") == "manual"]
auto_pairs = [event for event in compact_events if event.get("trigger") == "auto"]
expected_pair = ["PreCompact", "PostCompact"]
if [event.get("phase") for event in manual_pairs] != expected_pair * 2:
    raise SystemExit("expected two ordered real manual PreCompact/PostCompact pairs")
if [event.get("phase") for event in auto_pairs] != expected_pair:
    raise SystemExit("expected one ordered real automatic PreCompact/PostCompact pair")
events.extend({"kind":"compact","phase":event["phase"]} for event in manual_pairs[:2])
if "post_compaction_tasks" in passed:
    for identifier in ("P004A_TASK_A", "P004A_TASK_B"):
        events.append({"kind":"task","action":"observed-after","family":"TaskCreate","identifier":identifier})
events.extend({"kind":"compact","phase":event["phase"]} for event in manual_pairs[2:])
automatic_events = [
    json.loads(line) for line in automatic_path.read_text(encoding="utf-8").splitlines()
    if line
]
automatic_passed = {
    event["stage"] for event in automatic_events if event.get("outcome") == "passed"
}
if "automatic_compaction" in automatic_passed:
    events.append({"kind":"task","action":"created","family":"TaskCreate","identifier":"P004A_AUTO"})
    events.extend({"kind":"compact","phase":event["phase"]} for event in auto_pairs)
    events.append({"kind":"task","action":"observed-after","family":"TaskCreate","identifier":"P004A_AUTO"})
tool_search_path = probes_path / "tool-search-capability.jsonl"
if tool_search_path.is_file():
    events.extend(json.loads(line) for line in tool_search_path.read_text(encoding="utf-8").splitlines() if line)
mcp_path = probes_path / "mcp-capability.jsonl"
if mcp_path.is_file():
    events.extend(json.loads(line) for line in mcp_path.read_text(encoding="utf-8").splitlines() if line)
window_path = probes_path / "window-capability.jsonl"
if window_path.is_file():
    events.extend(json.loads(line) for line in window_path.read_text(encoding="utf-8").splitlines() if line)
role_percentages = []
for role_path in sorted(probes_path.glob("context-role-*.driver.jsonl")):
    for line in role_path.read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        if event.get("stage") == "context_inspected" and event.get("outcome") == "passed":
            percent = event.get("percent")
            if isinstance(percent, int) and 0 <= percent <= 100:
                role_percentages.append(percent)
if len(role_percentages) != 13:
    raise SystemExit("expected 13 native context role observations")
events.extend({"kind":"context-role","percent":percent} for percent in role_percentages)
resume_events = [
    json.loads(line) for line in (probes_path / "resume-driver.jsonl").read_text(encoding="utf-8").splitlines()
    if line
]
resume_passed = {event.get("stage") for event in resume_events if event.get("outcome") == "passed"}
if "resume_tasks" in resume_passed:
    events.append({"kind":"session","action":"resume-tasks"})
rewind_authorization_path = probes_path / "rewind-authorization.json"
rewind_authorization_invalid = False
if rewind_authorization_path.is_file():
    rewind_authorization_invalid = json.loads(
        rewind_authorization_path.read_text(encoding="utf-8")
    ).get("authorizationInvalidated") is True
if {"post_rewind_tasks", "post_rewind_context"}.issubset(resume_passed) and rewind_authorization_invalid:
    events.append({"kind":"session","action":"rewind-tasks"})
    events.append({"kind":"session","action":"rewind-context"})
    events.append({"kind":"session","action":"rewind-authorization-invalid"})
clear_events = [
    json.loads(line) for line in (probes_path / "clear-driver.jsonl").read_text(encoding="utf-8").splitlines()
    if line
]
if any(event.get("stage") == "clear_observed" and event.get("outcome") == "passed" for event in clear_events):
    events.append({"kind":"session","action":"clear-isolated"})
skill_events = [
    json.loads(line) for line in (probes_path / "skill-driver.jsonl").read_text(encoding="utf-8").splitlines()
    if line
]
for stage in ("skill_one_context", "skill_two_context"):
    matches = [event for event in skill_events if event.get("stage") == stage and event.get("outcome") == "passed"]
    if len(matches) != 1 or not isinstance(matches[0].get("percent"), int):
        raise SystemExit(f"missing structural repeated-skill measurement: {stage}")
    events.append({"kind":"skill-use","percent":matches[0]["percent"]})
large = [event for event in skill_events if event.get("stage") == "skill_two_invoked" and event.get("outcome") == "passed"]
if len(large) != 1 or not isinstance(large[0].get("outputBytes"), int) or large[0]["outputBytes"] < 1024:
    raise SystemExit("bounded large skill output was not structurally observed")
with output_path.open("w", encoding="utf-8") as stream:
    for event in events:
        stream.write(json.dumps(event) + "\n")
PY
  node "$INSTALLED_SKILLS_DIR/context-continuity/scripts/context-inventory.mjs" \
    --root "$ROOT" --runtime-jsonl "$PROBES/live-events.jsonl" >"$EVIDENCE"
}

run_context_role_probes() {
  local roles=(
    main audit-evidence-collector change-manager cloud-platform-operator
    database-operator diagnostic-operator incident-commander kubernetes-operator
    network-edge-operator observability-sre rca-facilitator release-cicd-operator
    security-operations-reviewer
  )
  local index role role_args status attempt
  for index in "${!roles[@]}"; do
    role="${roles[$index]}"
    role_args=()
    if [[ "$role" != "main" ]]; then role_args=(--agent "$role"); fi
    status=2
    for attempt in 1 2; do
      set +e
      timeout 120 "${PROVIDER_EXEC[@]}" \
        python3 "$ROOT/tests/claude-pty-driver.py" \
        --capture "$PROBES/context-role-$index.pty" \
        --events "$PROBES/context-role-$index.driver.jsonl" \
        --dialogue context --timeout 115 -- \
        "$BWRAP_BIN" "${BWRAP_ARGS[@]}" /opt/claude \
        "${CLAUDE_RUNTIME_ARGS[@]}" "${role_args[@]}" \
        >"$PROBES/context-role-$index.transcript" 2>&1
      status=$?
      set -e
      [[ $status -eq 0 ]] && break
    done
    [[ $status -eq 0 ]] || blocked \
      "native context role probe $index unavailable or failed at $(last_driver_stage "$PROBES/context-role-$index.driver.jsonl")"
  done
}

install_mcp_fixture() {
  local fixture="$WORK/project/.claude/mcp-context-fixture.py"
  cp "$ROOT/tests/mcp-context-fixture.py" "$fixture"
  chmod 0500 "$fixture"
  (
    cd "$WORK/project"
    "${PROVIDER_EXEC[@]}" "$CLAUDE_BIN" mcp add --scope project p004a-context -- \
      /usr/bin/python3 "$fixture" "$PROBES/mcp-connected.json"
  ) >"$PROBES/mcp-add.transcript" 2>&1 || blocked "disposable MCP registration failed"
  python3 - "$WORK/project/.claude/settings.local.json" <<'PY'
import json, sys
from pathlib import Path
path = Path(sys.argv[1])
value = json.loads(path.read_text(encoding="utf-8"))
approved = value.setdefault("enabledMcpjsonServers", [])
if not isinstance(approved, list) or any(not isinstance(item, str) for item in approved):
    raise SystemExit("invalid inherited MCP approval setting")
if "p004a-context" not in approved:
    approved.append("p004a-context")
path.write_text(json.dumps(value) + "\n", encoding="utf-8")
PY
}

verify_mcp_fixture_connection() {
  python3 - "$PROBES/mcp-connected.json" "$PROBES/mcp-before.driver.jsonl" \
    "$PROBES/mcp-after.driver.jsonl" "$PROBES/mcp-capability.jsonl" <<'PY'
import json, sys
from pathlib import Path
signal, before_path, after_path, output = map(Path, sys.argv[1:5])
if not signal.is_file():
    raise SystemExit("disposable MCP was not connected by Claude Code")
value = json.loads(signal.read_text(encoding="utf-8"))
if value != {"connected": True, "toolsListed": True, "visibleToolCount": 1}:
    raise SystemExit("unexpected MCP structural signal")
def percent(path):
    values = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    matches = [event.get("percent") for event in values if event.get("stage") == "context_inspected" and event.get("outcome") == "passed"]
    if len(matches) != 1 or not isinstance(matches[0], int):
        raise SystemExit("MCP context percentage missing")
    return matches[0]
output.write_text(json.dumps({
    "kind":"mcp", "connectedCount":1, "visibleToolCount":1,
    "beforePercent":percent(before_path), "afterPercent":percent(after_path),
}) + "\n", encoding="utf-8")
PY
}

run_mcp_context_probe() {
  local label="$1"
  timeout 120 "${PROVIDER_EXEC[@]}" \
    python3 "$ROOT/tests/claude-pty-driver.py" \
    --capture "$PROBES/mcp-$label.pty" --events "$PROBES/mcp-$label.driver.jsonl" \
    --dialogue context --timeout 115 -- \
    "$BWRAP_BIN" "${BWRAP_ARGS[@]}" /opt/claude "${CLAUDE_RUNTIME_ARGS[@]}" \
    >"$PROBES/mcp-$label.transcript" 2>&1 || \
    blocked "MCP $label context probe failed at $(last_driver_stage "$PROBES/mcp-$label.driver.jsonl")"
}

probe_tool_search() {
  set +e
  timeout 120 "${PROVIDER_EXEC[@]}" \
    "$BWRAP_BIN" "${BWRAP_ARGS[@]}" /opt/claude "${CLAUDE_RUNTIME_ARGS[@]}" \
    --print --output-format stream-json --verbose \
    "If ToolSearch is available, call it once to search for context_fixture_ping. Otherwise reply unavailable." \
    >"$PROBES/tool-search.raw.jsonl" 2>"$PROBES/tool-search.transcript"
  local status=$?
  set -e
  [[ $status -eq 0 ]] || blocked "explicit tool-search capability probe failed"
  python3 - "$PROBES/tool-search.raw.jsonl" "$PROBES/tool-search-capability.jsonl" <<'PY'
import json, sys
from pathlib import Path
source, output = map(Path, sys.argv[1:3])
observed = False
def walk(value):
    global observed
    if isinstance(value, dict):
        if value.get("name") == "ToolSearch" or value.get("tool_name") == "ToolSearch":
            observed = True
        if value.get("type") == "tool_reference" and value.get("tool_name") == "ToolSearch":
            observed = True
        for child in value.values(): walk(child)
    elif isinstance(value, list):
        for child in value: walk(child)
for line in source.read_text(encoding="utf-8", errors="replace").splitlines():
    try: walk(json.loads(line))
    except json.JSONDecodeError: pass
output.write_text(json.dumps({"kind":"tool-search","available":observed}) + "\n", encoding="utf-8")
PY
}

run_skill_probe() {
  set +e
  timeout 240 "${PROVIDER_EXEC[@]}" \
    python3 "$ROOT/tests/claude-pty-driver.py" \
    --capture "$PROBES/skill.pty" --events "$PROBES/skill-driver.jsonl" \
    --dialogue skill --timeout 235 -- \
    "$BWRAP_BIN" "${BWRAP_ARGS[@]}" /opt/claude "${CLAUDE_RUNTIME_ARGS[@]}" \
    >"$PROBES/skill.transcript" 2>&1
  local status=$?
  set -e
  [[ $status -eq 0 ]] || \
    blocked "repeated skill or bounded large-output probe failed at $(last_driver_stage "$PROBES/skill-driver.jsonl")"
}

run_mock_window_probe() {
  local limits port mock_status override_status
  limits="$(python3 - "$PROBES/mcp-before.pty" <<'PY'
import re, sys
from pathlib import Path
text = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
matches = re.findall(r"\[(\d+(?:\.\d+)?)([kKmM])\]", text)
if not matches:
    raise SystemExit("reported runtime context window unavailable")
amount, unit = matches[-1]
reported = int(float(amount) * ({"k":1_000,"m":1_000_000}[unit.lower()]))
observed = max(4, reported // 10)
if observed >= reported:
    raise SystemExit("mock divergence cannot be established")
print(reported, observed)
PY
)" || blocked "reported runtime window could not be parsed"
  read -r MOCK_REPORTED_WINDOW MOCK_OBSERVED_WINDOW <<<"$limits"
  python3 "$ROOT/tests/mock-anthropic-gateway.py" \
    "$PROBES/mock-port.json" "$PROBES/mock-gateway.jsonl" \
    "$MOCK_REPORTED_WINDOW" "$MOCK_OBSERVED_WINDOW" &
  SERVER_PID=$!
  for _ in $(seq 1 100); do
    [[ -f "$PROBES/mock-port.json" ]] && break
    sleep 0.02
  done
  [[ -f "$PROBES/mock-port.json" ]] || blocked "loopback mock gateway did not start"
  port="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["port"])' "$PROBES/mock-port.json")"
  [[ "$port" =~ ^[0-9]+$ ]] || blocked "loopback mock gateway returned an invalid port"

  python3 - "$port" "$MOCK_OBSERVED_WINDOW" <<'PY'
import json, sys, urllib.error, urllib.request
port, observed = map(int, sys.argv[1:3])
def post(words):
    body = json.dumps({"model":"mock-model","max_tokens":8,"messages":[{"role":"user","content":" probe" * words}]}).encode()
    return urllib.request.urlopen(urllib.request.Request(
        f"http://127.0.0.1:{port}/v1/messages", data=body,
        headers={"Content-Type":"application/json"}), timeout=10).status
assert post(observed) == 200
try:
    post(observed + 1)
except urllib.error.HTTPError as error:
    assert error.code == 400
else:
    raise SystemExit("mock did not enforce its observed window")
PY

  MOCK_ENV=()
  for entry in "${PROBE_ENV[@]}"; do
    case "$entry" in
      ANTHROPIC_AUTH_TOKEN=*|ANTHROPIC_API_KEY=*|ANTHROPIC_BASE_URL=*|ANTHROPIC_MODEL=*|ANTHROPIC_DEFAULT_*_MODEL=*) ;;
      *) MOCK_ENV+=("$entry") ;;
    esac
  done
  MOCK_ENV+=(
    "ANTHROPIC_AUTH_TOKEN=p004a_mock_token" "ANTHROPIC_BASE_URL=http://127.0.0.1:$port"
    "ANTHROPIC_MODEL=mock-model[1m]" "ANTHROPIC_DEFAULT_HAIKU_MODEL=mock-model[1m]"
    "ANTHROPIC_DEFAULT_OPUS_MODEL=mock-model[1m]" "ANTHROPIC_DEFAULT_SONNET_MODEL=mock-model[1m]"
    "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=5"
  )
  python3 - "$PROBES/mock-pressure.prompt" "$MOCK_OBSERVED_WINDOW" <<'PY'
import math, sys
from pathlib import Path
path = Path(sys.argv[1]); observed = int(sys.argv[2])
words = max(1, math.ceil(observed * 0.07))
if words > 100_000:
    raise SystemExit("mock pressure prompt exceeds safety bound")
path.write_text(" probe" * words, encoding="utf-8")
PY
  set_isolated_diagnostic_threshold 5
  set_live_compact_observer_destination "$PROBES/mock-compact-events.jsonl"
  set +e
  timeout 90 env -i "${MOCK_ENV[@]}" \
    python3 "$ROOT/tests/claude-pty-driver.py" \
    --capture "$PROBES/mock-before.pty" --events "$PROBES/mock-before.driver.jsonl" \
    --dialogue mock-window --filler "$PROBES/mock-pressure.prompt" \
    --compact-events "$PROBES/mock-compact-events.jsonl" --timeout 85 -- \
    "$BWRAP_BIN" "${BWRAP_ARGS[@]}" /opt/claude "${CLAUDE_RUNTIME_ARGS[@]}" \
    >"$PROBES/mock-before.transcript" 2>&1
  mock_status=$?
  set -e
  [[ $mock_status -eq 0 ]] || blocked "Claude Code could not use the loopback mock before override"
  [[ ! -s "$PROBES/mock-compact-events.jsonl" ]] || \
    blocked "mock compacted before the evidence-gated absolute override"
  printf '%s\n' "{\"kind\":\"window\",\"reportedWindow\":$MOCK_REPORTED_WINDOW,\"observedWindow\":$MOCK_OBSERVED_WINDOW}" \
    >"$PROBES/window-pre-override.jsonl"
  node "$INSTALLED_SKILLS_DIR/context-continuity/scripts/context-inventory.mjs" \
    --root "$ROOT" --runtime-jsonl "$PROBES/window-pre-override.jsonl" >"$PROBES/window-pre-override.json"
  python3 - "$PROBES/window-pre-override.json" <<'PY'
import json, sys
value = json.load(open(sys.argv[1], encoding="utf-8"))["runtime"]["window"]
assert value["reasonCode"] == "WINDOW_REPORTING_DIVERGENCE"
assert value["absoluteOverrideEvidenceGated"] is False
PY
  set +e
  timeout 90 env -i "${MOCK_ENV[@]}" \
    CLAUDE_CODE_AUTO_COMPACT_WINDOW="$MOCK_OBSERVED_WINDOW" \
    python3 "$ROOT/tests/claude-pty-driver.py" \
    --capture "$PROBES/mock-after.pty" --events "$PROBES/mock-after.driver.jsonl" \
    --dialogue mock-window --filler "$PROBES/mock-pressure.prompt" \
    --compact-events "$PROBES/mock-compact-events.jsonl" --timeout 85 -- \
    "$BWRAP_BIN" "${BWRAP_ARGS[@]}" /opt/claude "${CLAUDE_RUNTIME_ARGS[@]}" \
    >"$PROBES/mock-after.transcript" 2>&1
  override_status=$?
  set -e
  [[ $override_status -eq 0 ]] || blocked "evidence-gated mock override probe failed"
  [[ -s "$PROBES/mock-compact-events.jsonl" ]] || \
    blocked "evidence-gated mock override did not emit automatic compact hooks"
  python3 - "$PROBES/mock-before.pty" "$PROBES/mock-after.pty" \
    "$PROBES/mock-compact-events.jsonl" "$MOCK_REPORTED_WINDOW" <<'PY'
import json, re, sys
from pathlib import Path
before, after, compact_events = map(Path, sys.argv[1:4])
reported = int(sys.argv[4])
def window(path):
    matches = re.findall(r"\[(\d+(?:\.\d+)?)([kKmM])\]", path.read_text(encoding="utf-8", errors="replace"))
    if not matches: raise SystemExit("mock runtime window label missing")
    amount, unit = matches[-1]
    return int(float(amount) * ({"k":1000,"m":1000000}[unit.lower()]))
if window(before) != reported or window(after) != reported:
    raise SystemExit("mock status line did not remain bound to the reported full window")
events = [json.loads(line) for line in compact_events.read_text(encoding="utf-8").splitlines() if line]
pairs = [(event.get("phase"), event.get("trigger")) for event in events]
if not pairs or ("PreCompact", "auto") not in pairs or any(trigger != "auto" for _, trigger in pairs):
    raise SystemExit(f"unexpected structural mock auto-compaction sequence: {pairs}")
PY
  set_live_compact_observer_destination "$PROBES/live-compact-hook-events.jsonl"
  set_isolated_diagnostic_threshold 72
  printf '%s\n' "{\"kind\":\"window\",\"reportedWindow\":$MOCK_REPORTED_WINDOW,\"observedWindow\":$MOCK_OBSERVED_WINDOW,\"absoluteOverrideApplied\":true}" \
    >"$PROBES/window-capability.jsonl"
  kill "$SERVER_PID" 2>/dev/null || true
  wait "$SERVER_PID" 2>/dev/null || true
  unset SERVER_PID
}

build_automatic_filler() {
  python3 - "$PROBES/manual.pty" "$PROBES/automatic.prompt" <<'PY'
import math, re, sys
from pathlib import Path
manual_path, output_path = map(Path, sys.argv[1:3])
manual = manual_path.read_text(encoding="utf-8", errors="replace")
percentages = [
    int(value) for value in re.findall(
        r"(?<!\d)(\d{1,3})%",
        manual,
    ) if 0 <= int(value) <= 100
]
if not percentages:
    raise SystemExit("manual context percentage unavailable")
baseline_percent = max(percentages)
windows = re.findall(r"\[(\d+(?:\.\d+)?)([kKmM])\]", manual)
if not windows:
    raise SystemExit("runtime context window label unavailable")
amount, unit = windows[-1]
window_tokens = int(float(amount) * ({"k": 1_000, "m": 1_000_000}[unit.lower()]))
target_percent = 5
margin_percent = 2
required_percent = margin_percent if baseline_percent >= target_percent else target_percent + margin_percent
target_tokens = max(1, math.ceil(
    window_tokens * required_percent / 100
))
if target_tokens > 100_000:
    raise SystemExit("adaptive filler exceeds diagnostic safety bound")
output_path.write_text(" probe" * target_tokens, encoding="utf-8")
PY
}

set_isolated_diagnostic_threshold() {
  python3 - "$WORK/project/.claude/settings.local.json" "$1" <<'PY'
import json, sys
from pathlib import Path
path = Path(sys.argv[1])
threshold = int(sys.argv[2])
if threshold not in {5, 72}:
    raise SystemExit("unsupported isolated diagnostic threshold")
value = json.loads(path.read_text(encoding="utf-8"))
current = int(value["env"]["CLAUDE_AUTOCOMPACT_PCT_OVERRIDE"])
if current not in {5, 72}:
    raise SystemExit("unexpected prior isolated threshold")
value["env"]["CLAUDE_AUTOCOMPACT_PCT_OVERRIDE"] = str(threshold)
path.write_text(json.dumps(value) + "\n", encoding="utf-8")
PY
}

run_live() {
  CLAUDE_BIN="${CLAUDE_BIN:-$(command -v claude || true)}"
  BWRAP_BIN="${BWRAP_BIN:-$(command -v bwrap || true)}"
  [[ -n "$CLAUDE_BIN" ]] || blocked "Claude Code CLI not found"
  [[ -n "$BWRAP_BIN" ]] || blocked "Bubblewrap is required for --run-live"
  command -v timeout >/dev/null 2>&1 || blocked "timeout not found"
  CLAUDE_RUNTIME_ARGS=()
  if "$CLAUDE_BIN" --help 2>&1 | grep -F -- '--autocompact' >/dev/null; then
    CLAUDE_RUNTIME_ARGS+=(--autocompact auto)
  fi
  install_with_nori
  locate_installed_roots
  python3 "$ROOT/tests/validate-installed-subagents.py" \
    --installed-agents-dir "$INSTALLED_AGENTS_DIR" \
    --installed-skills-dir "$INSTALLED_SKILLS_DIR"
  configure_and_verify_preservation
  install_live_compact_observer
  run_installed_credential_compaction_probe
  observed_claude_version="$("$CLAUDE_BIN" --version | awk 'NR == 1 {print $1}')"
  [[ "$observed_claude_version" =~ ^[A-Za-z0-9._-]{1,128}$ ]] || blocked "Claude Code version label is unsafe"
  seed_isolated_onboarding "$observed_claude_version"

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
    "HISTFILE=/dev/null" "PATH=/usr/bin:/bin" "TMPDIR=/tmp" "TERM=xterm-256color"
    "CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1"
    "OPS_COMMAND_GUARD_STATE_DIR=$PROBES/bindings"
  )
  export TMPDIR=/tmp TERM=xterm-256color
  export CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1
  export OPS_COMMAND_GUARD_STATE_DIR="$PROBES/bindings"
  load_provider_environment
  PROVIDER_EXEC=(
    python3 "$ROOT/tests/exec-claude-env.py" "$SOURCE_CLAUDE_SETTINGS"
    "${ALLOWED_CLAUDE_ENV[@]}" --
  )

  run_mcp_context_probe before
  install_mcp_fixture
  run_mcp_context_probe after
  run_skill_probe
  run_mock_window_probe
  verify_mcp_fixture_connection

  MANUAL_TIMEOUT=600
  AUTOMATIC_TIMEOUT=600
  if [[ -n "${P0_04A_LIVE_TIMEOUT_SECONDS:-}" ]]; then
    [[ "$P0_04A_LIVE_TIMEOUT_SECONDS" =~ ^[0-9]+$ ]] || blocked "live timeout override must be numeric"
    (( P0_04A_LIVE_TIMEOUT_SECONDS >= 30 && P0_04A_LIVE_TIMEOUT_SECONDS <= 600 )) || \
      blocked "live timeout override must be from 30 through 600 seconds"
    MANUAL_TIMEOUT="$P0_04A_LIVE_TIMEOUT_SECONDS"
    AUTOMATIC_TIMEOUT="$P0_04A_LIVE_TIMEOUT_SECONDS"
  fi
  DRIVER_TIMEOUT=$((MANUAL_TIMEOUT - 5))
  SESSION_ID="$(python3 -c 'import uuid; print(uuid.uuid4())')"
  activate_actual_session_credential_binding "$SESSION_ID"

  set +e
  timeout "$MANUAL_TIMEOUT" "${PROVIDER_EXEC[@]}" \
    python3 "$ROOT/tests/claude-pty-driver.py" \
    --capture "$PROBES/manual.pty" --events "$PROBES/manual-driver.jsonl" \
    --timeout "$DRIVER_TIMEOUT" -- \
    "$BWRAP_BIN" "${BWRAP_ARGS[@]}" /opt/claude "${CLAUDE_RUNTIME_ARGS[@]}" \
    --session-id "$SESSION_ID" \
    >"$PROBES/manual.transcript" 2>&1
  manual_status=$?
  set -e
  [[ $manual_status -eq 0 ]] || blocked "manual compact PTY capability unavailable or failed"

  session_files="$(find "$CLAUDE_CONFIG_DIR" -type f -name "*$SESSION_ID*" | wc -l)"
  [[ "$session_files" -ge 1 ]] || blocked "interactive session was not persisted before resume"

  set +e
  timeout 240 "${PROVIDER_EXEC[@]}" \
    python3 "$ROOT/tests/claude-pty-driver.py" \
    --capture "$PROBES/resume.pty" --events "$PROBES/resume-driver.jsonl" \
    --dialogue resume --timeout 235 -- \
    "$BWRAP_BIN" "${BWRAP_ARGS[@]}" /opt/claude "${CLAUDE_RUNTIME_ARGS[@]}" \
    --resume "$SESSION_ID" >"$PROBES/resume.transcript" 2>&1
  resume_status=$?
  set -e
  [[ $resume_status -eq 0 ]] || \
    blocked "resume or rewind capability unavailable or failed at $(last_driver_stage "$PROBES/resume-driver.jsonl")"
  run_post_rewind_authorization_probe "$SESSION_ID"

  CLEAR_SESSION_ID="$(python3 -c 'import uuid; print(uuid.uuid4())')"
  set +e
  timeout 120 "${PROVIDER_EXEC[@]}" \
    python3 "$ROOT/tests/claude-pty-driver.py" \
    --capture "$PROBES/clear.pty" --events "$PROBES/clear-driver.jsonl" \
    --dialogue clear --timeout 115 -- \
    "$BWRAP_BIN" "${BWRAP_ARGS[@]}" /opt/claude "${CLAUDE_RUNTIME_ARGS[@]}" \
    --session-id "$CLEAR_SESSION_ID" >"$PROBES/clear.transcript" 2>&1
  clear_status=$?
  set -e
  [[ $clear_status -eq 0 ]] || \
    blocked "isolated clear capability unavailable or failed at $(last_driver_stage "$PROBES/clear-driver.jsonl")"
  verify_real_manual_compact_pairs

  run_context_role_probes
  probe_tool_search

  # The automatic probe lowers only the disposable project's percentage and restores it.
  build_automatic_filler
  set_isolated_diagnostic_threshold 5
  set +e
  CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=5 CLAUDE_CODE_EFFORT_LEVEL=low \
    timeout "$AUTOMATIC_TIMEOUT" "${PROVIDER_EXEC[@]}" \
    python3 "$ROOT/tests/claude-pty-driver.py" \
    --capture "$PROBES/automatic.pty" --events "$PROBES/automatic-driver.jsonl" \
    --dialogue automatic --filler "$PROBES/automatic.prompt" \
    --compact-events "$PROBES/live-compact-hook-events.jsonl" \
    --timeout "$DRIVER_TIMEOUT" -- \
    "$BWRAP_BIN" "${BWRAP_ARGS[@]}" /opt/claude "${CLAUDE_RUNTIME_ARGS[@]}" \
    >"$PROBES/automatic.transcript" 2>&1
  automatic_status=$?
  set -e
  set_isolated_diagnostic_threshold 72
  [[ $automatic_status -eq 0 ]] || blocked \
    "automatic compact capability unavailable or failed at $(last_driver_stage "$PROBES/automatic-driver.jsonl"); observed context $(driver_stage_percent "$PROBES/automatic-driver.jsonl" automatic_context_inspected)%"

  normalize_live_capture
  assert_evidence

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
