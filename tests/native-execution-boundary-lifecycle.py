#!/usr/bin/env python3
"""Record one bounded, content-free P0-05 SubagentStart marker."""
from __future__ import annotations

import json
import os
import re
import stat
import sys
from pathlib import Path


MAX_INPUT_BYTES = 64 * 1024
MAX_IDENTITY_CHARS = 256
NONCE = re.compile(r"^[a-f0-9]{32}$")


class InvalidEvent(ValueError):
    """The lifecycle event cannot establish the expected delegation."""


def unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    output: dict[str, object] = {}
    for key, value in pairs:
        if key in output:
            raise InvalidEvent("duplicate key")
        output[key] = value
    return output


def bounded_string(value: object) -> str:
    if not isinstance(value, str) or not value or len(value) > MAX_IDENTITY_CHARS:
        raise InvalidEvent("invalid identity")
    if any(character in value for character in "\r\n\0"):
        raise InvalidEvent("invalid identity")
    return value


def record() -> None:
    raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise InvalidEvent("input too large")
    try:
        event = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise InvalidEvent("invalid JSON") from error
    if not isinstance(event, dict):
        raise InvalidEvent("event must be an object")
    if event.get("hook_event_name") != "SubagentStart":
        raise InvalidEvent("unexpected event")
    if bounded_string(event.get("agent_type")) != "diagnostic-operator":
        raise InvalidEvent("unexpected agent")
    bounded_string(event.get("agent_id"))
    bounded_string(event.get("session_id"))

    nonce = os.environ.get("P005_LIVE_STAGE_NONCE", "")
    if NONCE.fullmatch(nonce) is None:
        raise InvalidEvent("invalid nonce")
    output = Path(os.environ.get("P005_LIFECYCLE_EVENT_PATH", ""))
    if not output.is_absolute() or output.name != f"lifecycle-executor-fallback-{nonce}.json":
        raise InvalidEvent("invalid output path")
    parent_mode = output.parent.lstat().st_mode
    if not stat.S_ISDIR(parent_mode) or stat.S_ISLNK(parent_mode):
        raise InvalidEvent("invalid output parent")

    marker = json.dumps({
        "agentIdPresent": True,
        "agentTypeMatched": True,
        "event": "SubagentStart",
        "probeNonce": nonce,
        "schemaVersion": 1,
    }, sort_keys=True, separators=(",", ":")).encode("utf-8")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(output, flags, 0o600)
    try:
        offset = 0
        while offset < len(marker):
            written = os.write(descriptor, marker[offset:])
            if written <= 0:
                raise OSError("short lifecycle write")
            offset += written
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def main() -> int:
    try:
        record()
    except (InvalidEvent, OSError, ValueError):
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
