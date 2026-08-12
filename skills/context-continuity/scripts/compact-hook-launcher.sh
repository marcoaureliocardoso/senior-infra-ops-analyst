#!/usr/bin/env bash

set +e
PATH="/usr/bin:/bin:${PATH:-}"
export PATH
umask 077

phase="${1:-invalid}"
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" 2>/dev/null && pwd -P)"
NODE_BIN="$(command -v node 2>/dev/null)"
timeout_bin="$(command -v timeout 2>/dev/null)"
status=1

if [[ "$phase" =~ ^(pre|post)$ ]] && [[ -n "$script_dir" ]] && [[ -n "$NODE_BIN" ]] && \
  [[ -n "$timeout_bin" ]] && [[ -f "$script_dir/compact-hook.mjs" ]] && [[ ! -L "$script_dir/compact-hook.mjs" ]]; then
  "$timeout_bin" --signal=TERM --kill-after=1s 3s "$NODE_BIN" "$script_dir/compact-hook.mjs" "$phase"
  status=$?
fi

if [[ $status -ne 0 ]]; then
  state_dir=""
  if [[ -n "${OPS_COMMAND_GUARD_STATE_DIR:-}" ]]; then
    state_dir="$OPS_COMMAND_GUARD_STATE_DIR"
  elif [[ -n "${HOME:-}" ]]; then
    state_dir="$HOME/.claude/senior-infra-ops-analyst/command-guard-state"
  fi

  if [[ -n "$state_dir" ]] && [[ -d "$state_dir" ]] && [[ ! -L "$state_dir" ]]; then
    for target in "$state_dir"/*.json; do
      [[ -e "$target" ]] || continue
      name="${target##*/}"
      [[ "$name" =~ ^[a-f0-9]{64}\.json$ ]] || continue
      [[ -f "$target" ]] && [[ ! -L "$target" ]] || continue
      temporary="$target.$$.$RANDOM.tmp"
      if printf '%s\n' '{"version":1,"pending":[],"active":[]}' >"$temporary"; then
        chmod 600 "$temporary" 2>/dev/null
        mv -f -- "$temporary" "$target" 2>/dev/null
      fi
      rm -f -- "$temporary" 2>/dev/null
    done
  fi
  printf '%s\n' 'Context continuity degraded. Credential reuse requires fresh approval.' >&2
fi

exit 0
