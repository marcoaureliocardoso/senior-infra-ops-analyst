#!/usr/bin/env python3
"""Exec a command with a clean allowlisted Claude environment and no values in argv."""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path


KEY = re.compile(r"^[A-Z][A-Z0-9_]*$")
BASE_KEYS = (
    "HOME", "CLAUDE_CONFIG_DIR", "HISTFILE", "PATH", "TMPDIR", "TERM",
    "CLAUDE_CODE_DISABLE_BACKGROUND_TASKS",
    "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE", "CLAUDE_CODE_AUTO_COMPACT_WINDOW",
    "CLAUDE_CODE_EFFORT_LEVEL",
    "OPS_COMMAND_GUARD_STATE_DIR",
    "SYSTEMROOT", "WINDIR", "PATHEXT", "COMSPEC", "TEMP", "TMP",
)


def main() -> int:
    try:
        separator = sys.argv.index("--")
    except ValueError:
        return 2
    if separator < 3 or separator == len(sys.argv) - 1:
        return 2
    settings_path = Path(sys.argv[1])
    allowed = list(dict.fromkeys(sys.argv[2:separator]))
    command = sys.argv[separator + 1:]
    if any(not KEY.fullmatch(key) for key in allowed):
        return 2
    payload: object = {}
    if settings_path.is_file():
        try:
            payload = json.loads(settings_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return 2
    settings_env = payload.get("env", {}) if isinstance(payload, dict) else {}
    if not isinstance(settings_env, dict):
        return 2
    clean = {key: os.environ[key] for key in BASE_KEYS if key in os.environ}
    for key in allowed:
        value = os.environ.get(key, settings_env.get(key))
        if value is None:
            continue
        if not isinstance(value, str) or "\0" in value:
            return 2
        clean[key] = value
    os.execvpe(command[0], command, clean)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
