#!/usr/bin/env python3
"""Deny every P0-06 live-probe tool request without using payload values."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any


MAX_INPUT_BYTES = 65_536
MAX_TOOL_NAME_CHARS = 128


class _DuplicateKey(ValueError):
    """Signal duplicate input keys without retaining their content."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise _DuplicateKey
        value[key] = item
    return value


def _fail() -> int:
    print("P0-06 deny hook rejected an invalid bounded event", file=sys.stderr)
    return 2


def _append_audit(path: Path, tool_name: str) -> None:
    if not path.is_absolute() or path.is_symlink():
        raise OSError("unsafe audit target")
    parent = path.parent
    if parent.is_symlink() or not parent.is_dir():
        raise OSError("unsafe audit parent")
    flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        metadata = os.fstat(descriptor)
        if metadata.st_uid != os.geteuid():
            raise OSError("audit target owner differs")
        os.fchmod(descriptor, 0o600)
        record = {
            "schemaVersion": 1,
            "hookEventName": "PreToolUse",
            "toolName": tool_name,
            "disposition": "deny",
        }
        encoded = (json.dumps(record, separators=(",", ":")) + "\n").encode("utf-8")
        os.write(descriptor, encoded)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def main() -> int:
    raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        return _fail()
    try:
        event = json.loads(raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError, _DuplicateKey, TypeError):
        return _fail()
    if not isinstance(event, dict) or event.get("hook_event_name") != "PreToolUse":
        return _fail()
    tool_name = event.get("tool_name")
    if (
        not isinstance(tool_name, str)
        or not tool_name
        or len(tool_name) > MAX_TOOL_NAME_CHARS
        or any(ord(character) < 33 or ord(character) > 126 for character in tool_name)
    ):
        return _fail()
    audit_value = os.environ.get("P006_DENY_AUDIT_PATH", "")
    if not audit_value:
        return _fail()
    try:
        _append_audit(Path(audit_value), tool_name)
    except OSError:
        return _fail()

    response = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": "P006_DENY_ALL_TEST_HOOK",
        }
    }
    print(json.dumps(response, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
