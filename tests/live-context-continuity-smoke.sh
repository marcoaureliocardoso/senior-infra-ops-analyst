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
if runtime["context"]["compactionCount"] != 2:
    raise SystemExit("expected one manual and one automatic normalized compaction")
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
    '{"kind":"compact","phase":"PostCompact","trigger":"auto"}' \
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
  printf '%s' 'runtime-model[1m] ctx 3%' >"$PROBES/manual.pty"
  build_automatic_filler
  python3 - "$PROBES/automatic.prompt" <<'PY'
import sys
from pathlib import Path
p = Path(sys.argv[1])
assert p.stat().st_size == 420_000
assert p.read_text(encoding="utf-8").startswith(" probe probe")
PY
  printf '%s' 'P004A_READY_DONE P004A_SECOND_TURN P004A_AUTO_CHECK_OK ctx 3%' \
    >"$PROBES/automatic.pty"
  printf '%s\n' \
    '{"kind":"pty-driver","outcome":"passed","stage":"automatic_task_created"}' \
    '{"kind":"pty-driver","outcome":"failed","stage":"automatic_compaction"}' \
    >"$PROBES/automatic-driver.jsonl"
  read -r diagnostic_reported diagnostic_observed <<<"$(derive_diagnostic_window_override)"
  [[ "$diagnostic_reported" == "1000000" && "$diagnostic_observed" == "100000" ]] || \
    failed "diagnostic window derivation is not runtime-relative"
  printf '%s\n' '{"kind":"compact","phase":"PreCompact","trigger":"auto"}' \
    >"$PROBES/live-compact-hook-events.jsonl"
  if derive_diagnostic_window_override >/dev/null; then
    failed "diagnostic window override accepted an observed automatic compaction"
  fi
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
    --claude-config-dir "$CLAUDE_CONFIG_DIR" --status-line >/dev/null
  python3 - "$WORK/project/.claude/settings.local.json" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1]); value = json.loads(p.read_text(encoding="utf-8"))
assert value["cleanupPeriodDays"] == 30
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
    "matcher": "auto",
    "hooks": [{
        "type": "command",
        "command": "/usr/bin/python3",
        "args": [str(recorder_path.resolve()), str(destination_path.resolve())],
        "timeout": 5,
    }],
}
settings.setdefault("hooks", {}).setdefault("PreCompact", []).append(observer)
settings_path.write_text(json.dumps(settings) + "\n", encoding="utf-8")
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
  python3 - "$PROBES/manual.pty" "$PROBES/manual-driver.jsonl" \
    "$PROBES/automatic-driver.jsonl" "$PROBES/live-events.jsonl" \
    "${DIAGNOSTIC_REPORTED_WINDOW:-}" "${DIAGNOSTIC_OBSERVED_WINDOW:-}" <<'PY'
import json, re, sys
from pathlib import Path
manual_path, driver_path, automatic_path, output_path = map(Path, sys.argv[1:5])
reported_window, observed_window = sys.argv[5:7]
text = manual_path.read_text(encoding="utf-8", errors="replace")
driver_events = [json.loads(line) for line in driver_path.read_text(encoding="utf-8").splitlines() if line]
passed = {event["stage"] for event in driver_events if event.get("outcome") == "passed"}
events = []
percentages = [int(v) for v in re.findall(r"(?<!\d)(\d{1,3})%", text) if 0 <= int(v) <= 100]
if "context_inspected" in passed and percentages:
    events.append({"kind":"context","stage":"before","percent":percentages[0]})
    events.append({"kind":"context","stage":"after","percent":percentages[-1]})
if {"tasks_created", "post_compaction_tasks"} <= passed:
    for identifier in ("P004A_TASK_A", "P004A_TASK_B"):
        events.extend([
            {"kind":"task","action":"created","family":"TaskCreate","identifier":identifier},
            {"kind":"task","action":"observed-after","family":"TaskCreate","identifier":identifier},
        ])
if "manual_compaction" in passed:
    events.append({"kind":"compact","phase":"PostCompact"})
automatic_events = [
    json.loads(line) for line in automatic_path.read_text(encoding="utf-8").splitlines()
    if line
]
automatic_passed = {
    event["stage"] for event in automatic_events if event.get("outcome") == "passed"
}
if "automatic_compaction" in automatic_passed:
    events.append({"kind":"compact","phase":"PostCompact"})
    events.extend([
        {"kind":"task","action":"created","family":"TaskCreate","identifier":"P004A_AUTO"},
        {"kind":"task","action":"observed-after","family":"TaskCreate","identifier":"P004A_AUTO"},
    ])
if re.search(r"tool[_ -]?search|tool_reference", text, re.I):
    events.append({"kind":"tool-search","available":True})
else:
    events.append({"kind":"tool-search","available":False,"gatewayUnavailable":True})
if reported_window and observed_window:
    events.append({
        "kind":"window",
        "reportedWindow":int(reported_window),
        "observedWindow":int(observed_window),
        "absoluteOverrideApplied":True,
    })
with output_path.open("w", encoding="utf-8") as stream:
    for event in events:
        stream.write(json.dumps(event) + "\n")
PY
  node "$INSTALLED_SKILLS_DIR/context-continuity/scripts/context-inventory.mjs" \
    --root "$ROOT" --runtime-jsonl "$PROBES/live-events.jsonl" >"$EVIDENCE"
}

derive_diagnostic_window_override() {
  python3 - "$PROBES/manual.pty" "$PROBES/automatic.pty" \
    "$PROBES/automatic-driver.jsonl" "$PROBES/live-compact-hook-events.jsonl" <<'PY'
import json, math, re, sys
from pathlib import Path

manual_path, automatic_path, driver_path, hook_path = map(Path, sys.argv[1:5])
driver_events = [
    json.loads(line) for line in driver_path.read_text(encoding="utf-8").splitlines()
    if line
]
passed = {event.get("stage") for event in driver_events if event.get("outcome") == "passed"}
failed = {event.get("stage") for event in driver_events if event.get("outcome") == "failed"}
if "automatic_task_created" not in passed or "automatic_compaction" not in failed:
    raise SystemExit(1)
capture = automatic_path.read_bytes().upper()
for marker in (b"P004A_READY_DONE", b"P004A_SECOND_TURN", b"P004A_AUTO_CHECK_OK"):
    if marker not in capture:
        raise SystemExit(1)
if hook_path.exists():
    for line in hook_path.read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        if event.get("phase") == "PreCompact" and event.get("trigger") == "auto":
            raise SystemExit(1)
percentages = [
    int(value) for value in re.findall(rb"(?<!\d)(\d{1,3})%", capture)
    if 0 <= int(value) <= 100
]
if not percentages or max(percentages) <= 1:
    raise SystemExit(1)
manual = manual_path.read_text(encoding="utf-8", errors="replace")
windows = re.findall(r"\[(\d+(?:\.\d+)?)([kKmM])\]", manual)
if not windows:
    raise SystemExit(1)
amount, unit = windows[-1]
reported = int(float(amount) * ({"k": 1_000, "m": 1_000_000}[unit.lower()]))
observed = math.ceil(reported / 10)
if reported <= 0 or observed <= 0 or observed >= reported:
    raise SystemExit(1)
print(f"{reported} {observed}")
PY
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
if threshold not in {1, 72}:
    raise SystemExit("unsupported isolated diagnostic threshold")
value = json.loads(path.read_text(encoding="utf-8"))
current = int(value["env"]["CLAUDE_AUTOCOMPACT_PCT_OVERRIDE"])
if current not in {1, 72}:
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
    "CLAUDE_CODE_SKIP_PROMPT_HISTORY=1" "CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1"
  )
  for key in "${ALLOWED_CLAUDE_ENV[@]}"; do
    if [[ -v "$key" ]]; then PROBE_ENV+=("$key=${!key}"); fi
  done
  load_provider_environment

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

  set +e
  timeout "$MANUAL_TIMEOUT" env -i "${PROBE_ENV[@]}" \
    python3 "$ROOT/tests/claude-pty-driver.py" \
    --capture "$PROBES/manual.pty" --events "$PROBES/manual-driver.jsonl" \
    --timeout "$DRIVER_TIMEOUT" -- \
    "$BWRAP_BIN" "${BWRAP_ARGS[@]}" /opt/claude "${CLAUDE_RUNTIME_ARGS[@]}" \
    >"$PROBES/manual.transcript" 2>&1
  manual_status=$?
  set -e
  [[ $manual_status -eq 0 ]] || blocked "manual compact PTY capability unavailable or failed"

  # The automatic probe lowers only the disposable project's percentage and restores it.
  build_automatic_filler
  set_isolated_diagnostic_threshold 1
  DIAGNOSTIC_REPORTED_WINDOW=""
  DIAGNOSTIC_OBSERVED_WINDOW=""
  set +e
  timeout "$AUTOMATIC_TIMEOUT" env -i "${PROBE_ENV[@]}" \
    CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=1 CLAUDE_CODE_EFFORT_LEVEL=low \
    python3 "$ROOT/tests/claude-pty-driver.py" \
    --capture "$PROBES/automatic.pty" --events "$PROBES/automatic-driver.jsonl" \
    --dialogue automatic --filler "$PROBES/automatic.prompt" \
    --compact-events "$PROBES/live-compact-hook-events.jsonl" \
    --timeout "$DRIVER_TIMEOUT" -- \
    "$BWRAP_BIN" "${BWRAP_ARGS[@]}" /opt/claude "${CLAUDE_RUNTIME_ARGS[@]}" \
    >"$PROBES/automatic.transcript" 2>&1
  automatic_status=$?
  set -e
  if [[ $automatic_status -ne 0 ]]; then
    set +e
    diagnostic_windows="$(derive_diagnostic_window_override)"
    diagnostic_status=$?
    set -e
    if [[ $diagnostic_status -eq 0 ]]; then
      read -r DIAGNOSTIC_REPORTED_WINDOW DIAGNOSTIC_OBSERVED_WINDOW <<<"$diagnostic_windows"
      rm -f -- "$PROBES/automatic.pty" "$PROBES/automatic-driver.jsonl" \
        "$PROBES/automatic.transcript" "$PROBES/live-compact-hook-events.jsonl"
      set +e
      timeout "$AUTOMATIC_TIMEOUT" env -i "${PROBE_ENV[@]}" \
        CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=1 \
        CLAUDE_CODE_AUTO_COMPACT_WINDOW="$DIAGNOSTIC_OBSERVED_WINDOW" \
        CLAUDE_CODE_EFFORT_LEVEL=low \
        python3 "$ROOT/tests/claude-pty-driver.py" \
        --capture "$PROBES/automatic.pty" --events "$PROBES/automatic-driver.jsonl" \
        --dialogue automatic --filler "$PROBES/automatic.prompt" \
        --compact-events "$PROBES/live-compact-hook-events.jsonl" \
        --timeout "$DRIVER_TIMEOUT" -- \
        "$BWRAP_BIN" "${BWRAP_ARGS[@]}" /opt/claude "${CLAUDE_RUNTIME_ARGS[@]}" \
        >"$PROBES/automatic.transcript" 2>&1
      automatic_status=$?
      set -e
    fi
  fi
  set_isolated_diagnostic_threshold 72
  [[ $automatic_status -eq 0 ]] || blocked "automatic compact capability unavailable or failed"

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
