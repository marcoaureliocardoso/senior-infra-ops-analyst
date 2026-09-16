#!/usr/bin/env python3
"""Allow exactly one nonce-bound diagnostic Agent call in a disposable run."""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path


MAX_INPUT_BYTES = 32 * 1024
LABEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/+@-]{0,95}$")
ACK = "P004B_SUBAGENT_ACK"


def response(decision: str, reason: str) -> dict[str, object]:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        }
    }


def evaluate(raw: bytes, claim: Path, expected_session: str) -> dict[str, object]:
    if len(raw) > MAX_INPUT_BYTES or not LABEL.fullmatch(expected_session):
        return response("deny", "P004B_MEASUREMENT_GUARD_INVALID")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        return response("deny", "P004B_MEASUREMENT_GUARD_INVALID")
    expected_input = {
        "description": ACK,
        "prompt": ACK,
        "subagent_type": "diagnostic-operator",
    }
    if (not isinstance(value, dict)
            or value.get("hook_event_name") != "PreToolUse"
            or value.get("session_id") != expected_session
            or value.get("tool_name") != "Agent"
            or value.get("tool_input") != expected_input):
        return response("deny", "P004B_MEASUREMENT_GUARD_MISMATCH")
    if os.name == "nt" or not claim.is_absolute() or not hasattr(os, "O_NOFOLLOW"):
        return response("deny", "P004B_MEASUREMENT_GUARD_UNSUPPORTED")
    descriptor: int | None = None
    try:
        descriptor = os.open(
            claim,
            os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW"),
            0o600,
        )
        os.write(descriptor, b"claimed\n")
        os.fsync(descriptor)
    except FileExistsError:
        return response("deny", "P004B_MEASUREMENT_GUARD_ALREADY_USED")
    except OSError:
        return response("deny", "P004B_MEASUREMENT_GUARD_INVALID")
    finally:
        if descriptor is not None:
            os.close(descriptor)
    return response("allow", "P004B_MEASUREMENT_GUARD_FIRST_CALL")


def main() -> int:
    if len(sys.argv) != 3:
        return 2
    raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    print(json.dumps(evaluate(raw, Path(sys.argv[1]), sys.argv[2]), separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
