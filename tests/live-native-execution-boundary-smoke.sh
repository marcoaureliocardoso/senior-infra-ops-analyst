#!/usr/bin/env bash
set -euo pipefail

blocked() {
  printf 'BLOCKED: %s\n' "$*" >&2
  exit 2
}

MODE="${1:---self-test}"
[[ "$MODE" == "--self-test" || "$MODE" == "--run-live" ]] || {
  printf 'Usage: %s [--self-test|--run-live]\n' "$0" >&2
  exit 2
}
MODE="${MODE#--}"

LIVE_ACK='I_AUTHORIZE_BOUNDED_PROVIDER_USE'
if [[ "$MODE" == "run-live" ]]; then
  [[ "${P0_05_LIVE_PROVIDER_ACK:-}" == "$LIVE_ACK" ]] || \
    blocked "set P0_05_LIVE_PROVIDER_ACK=$LIVE_ACK to authorize bounded provider use"
  printf '%s\n' \
    'WARNING: provider credentials enter the disposable Claude process; the harness never records their values.' >&2
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_CLAUDE_SETTINGS="${CLAUDE_SETTINGS_SOURCE:-${CLAUDE_CONFIG_DIR:-$HOME/.claude}/settings.json}"
TMP_PARENT="${TMPDIR:-/tmp}"
WORK="$(mktemp -d "$TMP_PARENT/p0-05-native-boundary.XXXXXX")"
WORK_REAL="$(readlink -f "$WORK")"
case "$WORK_REAL" in
  "$(readlink -f "$TMP_PARENT")"/p0-05-native-boundary.*) ;;
  *) blocked 'temporary directory escaped the verified runner prefix' ;;
esac
cleanup() {
  if [[ -n "${ENV_LOADER_PID:-}" ]]; then kill "$ENV_LOADER_PID" 2>/dev/null || true; fi
  rm -rf -- "$WORK_REAL"
}
trap cleanup EXIT
umask 077

command -v node >/dev/null 2>&1 || blocked 'Node.js not found'
command -v python3 >/dev/null 2>&1 || blocked 'python3 not found'
command -v timeout >/dev/null 2>&1 || blocked 'timeout not found'

HOME="$WORK/home"
CLAUDE_CONFIG_DIR="$HOME/.claude"
PROJECT="$WORK/project"
AUDIT_DIR="$WORK/audit"
SYNTHETIC_TARGET="$WORK/synthetic-target"
RESULT_DIR="$WORK/results"
export HOME CLAUDE_CONFIG_DIR
export HISTFILE=/dev/null CLAUDE_CODE_SKIP_PROMPT_HISTORY=1
export CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1
mkdir -p "$CLAUDE_CONFIG_DIR" "$PROJECT/.claude" "$AUDIT_DIR" \
  "$SYNTHETIC_TARGET" "$RESULT_DIR"
printf 'synthetic-only\n' >"$SYNTHETIC_TARGET/README"

PROBE='printf P005_GUARD_PROBE'
EXPECTED_REASON='DENY_UNKNOWN_COMMAND'
DRIVER="$ROOT/tests/native-execution-boundary-pty.py"
LIFECYCLE_RECORDER="$WORK/native-execution-boundary-lifecycle.py"
cp "$ROOT/tests/native-execution-boundary-lifecycle.py" "$LIFECYCLE_RECORDER"
chmod 700 "$LIFECYCLE_RECORDER"
ALLOWED_CLAUDE_ENV=(
  ANTHROPIC_AUTH_TOKEN ANTHROPIC_API_KEY ANTHROPIC_BASE_URL ANTHROPIC_MODEL
  ANTHROPIC_DEFAULT_HAIKU_MODEL ANTHROPIC_DEFAULT_OPUS_MODEL
  ANTHROPIC_DEFAULT_SONNET_MODEL CLAUDE_CODE_SUBAGENT_MODEL
  CLAUDE_CODE_EFFORT_LEVEL
)

create_fake_nori() {
  local fake="$WORK/fake-nori"
  python3 - "$fake" <<'PY'
import os
import sys
from pathlib import Path

target = Path(sys.argv[1])
target.write_text(r'''#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == '--version' ]]; then
  printf 'nori-skillsets test-double\n'
  exit 0
fi
install_dir=''
agent=''
positionals=()
while (($#)); do
  case "$1" in
    --install-dir|-d) install_dir="$2"; shift 2 ;;
    --agent|-a) agent="$2"; shift 2 ;;
    --non-interactive|-n) shift ;;
    *) positionals+=("$1"); shift ;;
  esac
done
case "${positionals[0]:-}" in
  link)
    printf '%s' "${positionals[1]}" >"$HOME/.p005-source"
    [[ "${positionals[2]:-}" == '--name' ]]
    case "${P005_TEST_NORI_PROFILE_PREFIX:-}" in
      ''|'personal/') ;;
      *) exit 64 ;;
    esac
    printf '%s%s' "${P005_TEST_NORI_PROFILE_PREFIX:-}" "${positionals[3]}" \
      >"$HOME/.p005-profile"
    ;;
  list)
    cat "$HOME/.p005-profile"
    printf ' (linked)\n'
    ;;
  switch)
    source_path="$(<"$HOME/.p005-source")"
    [[ "${positionals[1]:-}" == "$(<"$HOME/.p005-profile")" ]]
    [[ "$agent" == 'claude-code' ]]
    mkdir -p "$install_dir/.claude/skills" "$install_dir/.claude/agents"
    cp -R "$source_path/skills/." "$install_dir/.claude/skills/"
    for source in "$source_path"/subagents/*/SUBAGENT.md; do
      name="$(basename "$(dirname "$source")")"
      cp "$source" "$install_dir/.claude/agents/$name.md"
    done
    ;;
  *) exit 64 ;;
esac
''', encoding="utf-8")
os.chmod(target, 0o700)
PY
  NORI_BIN="$fake"
}

create_fake_claude() {
  local fake="$WORK/fake-claude"
  python3 - "$fake" <<'PY'
import os
import sys
from pathlib import Path

target = Path(sys.argv[1])
target.write_text(r'''#!/usr/bin/env python3
import json
import os
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

if '--version' in sys.argv:
    print('Claude Code test-double')
    raise SystemExit(0)
args = sys.argv[1:]
prompt = args[args.index('-p') + 1]
if 'printf P005_GUARD_PROBE' not in prompt:
    raise SystemExit(64)
mode = args[args.index('--permission-mode') + 1]
executor = 'executor-fallback' in os.environ['OPS_COMMAND_GUARD_AUDIT_PATH']
agent = 'diagnostic-operator' if executor else None
if executor:
    if ('--tools' in args or args[args.index('--agent') + 1] != 'p005-probe-coordinator'
            or 'delegate' not in prompt.lower()):
        raise SystemExit(64)
    coordinator = (
        Path.cwd() / '.claude' / 'agents' / 'p005-probe-coordinator.md'
    ).read_text(encoding='utf-8')
    if ('tools: Agent(diagnostic-operator)' not in coordinator
            or 'Delegate the supplied task exactly once' not in coordinator):
        raise SystemExit(64)
    settings = json.loads(
        (Path.cwd() / '.claude' / 'settings.local.json').read_text(encoding='utf-8')
    )
    groups = settings['hooks']['SubagentStart']
    matches = [group for group in groups if group.get('matcher') == 'diagnostic-operator']
    if len(matches) != 1 or len(matches[0].get('hooks', [])) != 1:
        raise SystemExit(64)
    handler = matches[0]['hooks'][0]
    if handler.get('type') != 'command':
        raise SystemExit(64)
    event = {
        'hook_event_name': 'SubagentStart',
        'agent_type': 'diagnostic-operator',
        'agent_id': 'test-double-agent',
        'session_id': 'test-double-session',
    }
    subprocess.run(
        shlex.split(handler['command']), input=json.dumps(event), text=True,
        timeout=handler['timeout'], check=True, env=os.environ,
    )
record = {
    'timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
    'sessionId': 'test-double-current-session', 'agent': agent, 'mode': mode,
    'risk': None, 'modifiers': [], 'policyId': None, 'target': None,
    'environment': None, 'scope': None, 'credential': None,
    'actionId': 'a' * 64, 'decision': 'deny',
    'reason': 'DENY_UNKNOWN_COMMAND', 'stage': 1, 'findings': [],
    'probeNonce': os.environ['P005_LIVE_STAGE_NONCE'],
}
with open(os.environ['OPS_COMMAND_GUARD_AUDIT_PATH'], 'w', encoding='utf-8') as stream:
    stream.write(json.dumps(record) + '\n')
print('synthetic model output is ignored')
time.sleep(0.3)
''', encoding="utf-8")
os.chmod(target, 0o700)
PY
  CLAUDE_BIN="$fake"
}

install_package() {
  local link_name='senior-infra-ops-analyst-p005' list_output profile
  local -a profiles=()
  "$NORI_BIN" --install-dir "$HOME" --agent claude-code \
    link "$ROOT" --name "$link_name"
  list_output="$("$NORI_BIN" --install-dir "$HOME" --agent claude-code list)" || \
    blocked 'Nori linked-profile discovery failed'
  while IFS= read -r profile; do
    case "$profile" in
      *' (linked)') profile="${profile% (linked)}" ;;
    esac
    [[ -n "$profile" ]] && profiles+=("$profile")
  done <<<"$list_output"
  [[ ${#profiles[@]} -eq 1 ]] || blocked 'Nori linked-profile discovery was ambiguous'
  profile="${profiles[0]}"
  case "$profile" in
    "$link_name"|"personal/$link_name") ;;
    *) blocked 'Nori linked-profile identity was unexpected' ;;
  esac
  "$NORI_BIN" --install-dir "$HOME" --agent claude-code \
    switch "$profile" --agent claude-code
  INSTALLED_SKILL="$CLAUDE_CONFIG_DIR/skills/command-driven-operations"
  CONFIGURATOR="$INSTALLED_SKILL/scripts/configure-native-execution-boundary.mjs"
  [[ -f "$CONFIGURATOR" ]] || blocked 'installed main-session configurator not found'
  [[ -f "$CLAUDE_CONFIG_DIR/agents/diagnostic-operator.md" ]] || \
    blocked 'installed protected executor not found'
}

if [[ "$MODE" == "self-test" ]]; then
  create_fake_nori
  create_fake_claude
else
  CLAUDE_BIN="${CLAUDE_BIN:-$(command -v claude || true)}"
  NORI_BIN="${NORI_BIN:-$(command -v sks || command -v nori-skillsets || true)}"
  BWRAP_BIN="${BWRAP_BIN:-$(command -v bwrap || true)}"
  [[ -n "$CLAUDE_BIN" ]] || blocked 'Claude Code CLI not found'
  [[ -n "$NORI_BIN" ]] || blocked 'Nori CLI not found'
  [[ -n "$BWRAP_BIN" ]] || blocked 'Bubblewrap is required for --run-live'
  CLAUDE_BIN="$(readlink -f "$CLAUDE_BIN")"
  NORI_BIN="$(readlink -f "$NORI_BIN")"
  CLAUDE_ENV_PIPE="$WORK/claude-env.pipe"
  mkfifo "$CLAUDE_ENV_PIPE"
  python3 "$ROOT/tests/load-claude-env.py" "$SOURCE_CLAUDE_SETTINGS" \
    "${ALLOWED_CLAUDE_ENV[@]}" >"$CLAUDE_ENV_PIPE" &
  ENV_LOADER_PID=$!
  while IFS= read -r -d '' entry; do
    key="${entry%%=*}"
    if [[ ! -v "$key" ]]; then export "${entry?}"; fi
  done <"$CLAUDE_ENV_PIPE"
  set +e
  wait "$ENV_LOADER_PID"
  loader_status=$?
  set -e
  unset ENV_LOADER_PID
  rm -f "$CLAUDE_ENV_PIPE"
  [[ $loader_status -eq 0 ]] || blocked 'Claude provider environment import failed'
fi

install_package
CLAUDE_VERSION="$($CLAUDE_BIN --version | head -n 1)"
NORI_VERSION="$($NORI_BIN --version | head -n 1)"
CLAUDE_COMMAND=("$CLAUDE_BIN")

if [[ "$MODE" == "run-live" ]]; then
  BWRAP_ARGS=(
    --die-with-parent --new-session --unshare-user --unshare-pid --unshare-ipc --unshare-uts
    --ro-bind /usr /usr
    --dev /dev --proc /proc --tmpfs /tmp
    --bind "$WORK_REAL" "$WORK_REAL"
    --dir /opt --ro-bind "$CLAUDE_BIN" /opt/claude
    --chdir "$PROJECT"
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
  add_readonly_etc /etc/passwd
  add_readonly_etc /etc/group
  add_readonly_etc /etc/ssl
  add_readonly_etc /etc/ca-certificates.conf
  "$BWRAP_BIN" "${BWRAP_ARGS[@]}" /usr/bin/true || \
    blocked 'Bubblewrap isolation preflight failed'
  CLAUDE_COMMAND=("$BWRAP_BIN" "${BWRAP_ARGS[@]}" /opt/claude)
fi

set +e
node "$CONFIGURATOR" --apply --root "$PROJECT" >"$RESULT_DIR/apply.json"
apply_status=$?
set -e
if [[ $apply_status -ne 2 ]]; then
  apply_reason="$(python3 - "$RESULT_DIR/apply.json" <<'PY'
import json
import sys
try:
    value = json.load(open(sys.argv[1], encoding="utf-8"))
    print(value.get("reasonCode", "CONFIGURATION_FAILED"))
except (OSError, ValueError):
    print("CONFIGURATION_FAILED")
PY
)"
  blocked "main hook configuration failed: $apply_reason"
fi
grep -q '"state":"CONFIGURED_UNPROVEN"' "$RESULT_DIR/apply.json" || \
  blocked 'main hooks were not configured in the disposable project'

run_stage() {
  local stage="$1" mode="$2" result prompt
  result="$RESULT_DIR/$stage.json"
  shift 2
  prompt="Use Bash exactly once to run exactly this harmless coverage probe: $PROBE. Stop after the guard response."
  if [[ "$stage" == "executor-fallback" ]]; then
    prompt="Use the Agent tool exactly once to delegate to diagnostic-operator this exact task: use Bash exactly once to run exactly this harmless coverage probe: $PROBE. Stop after the guard response."
  fi
  set +e
  (
    cd "$PROJECT"
    timeout 300 python3 "$DRIVER" --stage "$stage" --audit-dir "$AUDIT_DIR" \
      --timeout 180 --clean-environment -- "${CLAUDE_COMMAND[@]}" -p \
      "$prompt" \
      --permission-mode "$mode" --no-session-persistence "$@"
  ) >"$result"
  local status=$?
  set -e
  [[ $status -eq 0 || $status -eq 3 ]] || blocked "$stage driver failed with exit $status"
}

run_stage main-default default
run_stage main-bypass bypassPermissions

node "$CONFIGURATOR" --remove-owned --root "$PROJECT" >"$RESULT_DIR/remove.json"
grep -q '"state":"ABSENT"' "$RESULT_DIR/remove.json" || \
  blocked 'owned main hooks were not removed before fallback'
grep -q 'PreToolUse' "$CLAUDE_CONFIG_DIR/agents/diagnostic-operator.md" || \
  blocked 'executor fallback lacks a native PreToolUse hook'
python3 - "$PROJECT/.claude/settings.local.json" "$LIFECYCLE_RECORDER" \
  "$PROJECT/.claude/agents/p005-probe-coordinator.md" <<'PY'
import json
import os
import shlex
import stat
import sys
from pathlib import Path

settings_path = Path(sys.argv[1])
recorder = Path(sys.argv[2])
coordinator = Path(sys.argv[3])
payload = json.loads(settings_path.read_text(encoding="utf-8"))
hooks = payload.setdefault("hooks", {})
if "SubagentStart" in hooks:
    raise SystemExit("unexpected existing SubagentStart hook")
hooks["SubagentStart"] = [{
    "matcher": "diagnostic-operator",
    "hooks": [{
        "type": "command",
        "command": f"python3 {shlex.quote(str(recorder))}",
        "timeout": 5,
    }],
}]
temporary = settings_path.with_suffix(".p005-lifecycle.tmp")
temporary.write_text(json.dumps(payload, separators=(",", ":")) + "\n", encoding="utf-8")
os.chmod(temporary, 0o600)
os.replace(temporary, settings_path)

coordinator.parent.mkdir(mode=0o700)
content = b"""---
name: p005-probe-coordinator
description: Coordinate only the bounded P0-05 delegated executor probe.
tools: Agent(diagnostic-operator)
maxTurns: 3
model: inherit
---

Delegate the supplied task exactly once to diagnostic-operator. Do not perform
the task yourself. Stop after returning the delegated result.
"""
flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
descriptor = os.open(coordinator, flags, 0o600)
try:
    if not stat.S_ISREG(os.fstat(descriptor).st_mode):
        raise SystemExit("coordinator target is not regular")
    offset = 0
    while offset < len(content):
        written = os.write(descriptor, content[offset:])
        if written <= 0:
            raise OSError("short coordinator write")
        offset += written
    os.fsync(descriptor)
finally:
    os.close(descriptor)
PY
run_stage executor-fallback default --agent p005-probe-coordinator

python3 - "$DRIVER" "$RESULT_DIR" "$MODE" "$CLAUDE_VERSION" "$NORI_VERSION" \
  "${ANTHROPIC_MODEL:-operator-configured}" "$EXPECTED_REASON" <<'PY'
import importlib.util
import json
import sys
from pathlib import Path

driver_path, result_dir, mode, claude, nori, provider, expected_reason = sys.argv[1:]
spec = importlib.util.spec_from_file_location("p005_driver", driver_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
results = []
for stage in module.STAGES:
    value = json.loads((Path(result_dir) / f"{stage}.json").read_text(encoding="utf-8"))
    reason = value.get("reasonCode")
    if reason not in {
        expected_reason, "TIMEOUT_OR_NO_AUDIT", "AUDIT_SEQUENCE_INVALID",
        "AUDIT_LIMIT", "TERMINAL_OUTPUT_LIMIT", "DELEGATION_NOT_OBSERVED",
        "EXECUTOR_GUARD_NOT_OBSERVED", "LIFECYCLE_SEQUENCE_INVALID",
    }:
        raise SystemExit("unexpected bounded reason code")
    results.append(module.StageResult(
        value.get("outcome"), value.get("marker"), reason,
        value.get("sessionMatched") is True, value.get("active") is True,
        value.get("outputBytes", 0), value.get("delegationObserved") is True,
    ))
evidence = module.public_evidence(results, runtime={
    "claude": claude,
    "nori": nori,
    "provider": provider,
    "platform": sys.platform,
})
evidence["validationMode"] = mode
print(json.dumps(evidence, sort_keys=True))
if not evidence["complete"]:
    raise SystemExit(3)
PY

printf 'live native execution boundary %s passed\n' "$MODE"
