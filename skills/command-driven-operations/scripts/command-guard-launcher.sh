#!/usr/bin/env bash
set -euo pipefail

PATH="/usr/bin:/bin:${PATH:-}"
export PATH
umask 077

block_hook() {
  printf '%s\n' 'Command guard blocked execution because its launcher failed.' >&2
  exit 2
}

[[ $# -eq 1 ]] || block_hook

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)" || block_hook
case "$1" in
  pre) VALIDATOR="$SCRIPT_DIR/validate-ops-command.mjs" ;;
  post) VALIDATOR="$SCRIPT_DIR/record-command-approval.mjs" ;;
  *) block_hook ;;
esac
[[ -f "$VALIDATOR" && ! -L "$VALIDATOR" ]] || block_hook

NODE_BIN="$(command -v node || true)"
TIMEOUT_BIN="$(command -v timeout || true)"
[[ -n "$NODE_BIN" && -x "$NODE_BIN" && -n "$TIMEOUT_BIN" && -x "$TIMEOUT_BIN" ]] || block_hook

TEMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/ops-command-guard.XXXXXX")" || block_hook
cleanup() {
  rm -rf -- "$TEMP_ROOT"
}
trap cleanup EXIT HUP INT TERM
STDOUT_FILE="$TEMP_ROOT/stdout"
STDERR_FILE="$TEMP_ROOT/stderr"

if ! "$TIMEOUT_BIN" --signal=TERM --kill-after=1s 5s \
  "$NODE_BIN" "$VALIDATOR" >"$STDOUT_FILE" 2>"$STDERR_FILE"; then
  block_hook
fi
[[ ! -s "$STDERR_FILE" ]] || block_hook

if [[ "$1" == "post" ]]; then
  [[ ! -s "$STDOUT_FILE" ]] || block_hook
  exit 0
fi

if ! "$NODE_BIN" -e '
  const fs = require("node:fs");
  const text = fs.readFileSync(process.argv[1], "utf8");
  if (!text.endsWith("\n") || text.trim().split(/\r?\n/u).length !== 1) process.exit(2);
  let value;
  try { value = JSON.parse(text); } catch { process.exit(2); }
  const hook = value?.hookSpecificOutput;
  if (hook?.hookEventName !== "PreToolUse" || !["allow", "ask", "deny"].includes(hook.permissionDecision)) process.exit(2);
' "$STDOUT_FILE"; then
  block_hook
fi

cat -- "$STDOUT_FILE"
