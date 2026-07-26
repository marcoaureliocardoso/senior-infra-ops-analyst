#!/usr/bin/env python3
"""Emit selected Claude settings environment entries as NUL-delimited records."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


KEY = re.compile(r"^[A-Z][A-Z0-9_]*$")


def fail(message: str) -> int:
    print(f"Claude environment import failed: {message}", file=sys.stderr)
    return 2


def main() -> int:
    if len(sys.argv) < 3:
        return fail("settings path and allowlist are required")

    settings_path = Path(sys.argv[1])
    allowed = list(dict.fromkeys(sys.argv[2:]))
    if any(not KEY.fullmatch(key) for key in allowed):
        return fail("allowlist contains an invalid key")
    if not settings_path.is_file():
        return 0

    try:
        payload = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return fail("settings file is unreadable or invalid")

    env = payload.get("env", {}) if isinstance(payload, dict) else {}
    if not isinstance(env, dict):
        return fail("settings env must be an object")

    output = sys.stdout.buffer
    for key in allowed:
        value = env.get(key)
        if not isinstance(value, str):
            continue
        if "\0" in value:
            return fail("an allowlisted value contains a NUL byte")
        output.write(f"{key}={value}".encode("utf-8") + b"\0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
