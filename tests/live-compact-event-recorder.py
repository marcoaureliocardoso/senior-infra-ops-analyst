#!/usr/bin/env python3
"""Record only structural compact-hook evidence for the disposable live test."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


MAX_INPUT_BYTES = 64 * 1024


def strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate JSON key")
        value[key] = item
    return value


def record(raw: bytes, destination: Path) -> None:
    if len(raw) > MAX_INPUT_BYTES or not destination.is_absolute():
        return
    try:
        event = json.loads(raw.decode("utf-8"), object_pairs_hook=strict_object)
    except (UnicodeError, ValueError, json.JSONDecodeError):
        return
    if not isinstance(event, dict):
        return
    phase = event.get("hook_event_name")
    trigger = event.get("trigger")
    if phase not in {"PreCompact", "PostCompact"} or trigger not in {"manual", "auto"}:
        return
    evidence = json.dumps(
        {"kind": "compact", "phase": phase, "trigger": trigger},
        separators=(",", ":"),
    ).encode("ascii") + b"\n"
    flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(destination, flags, 0o600)
    try:
        os.write(descriptor, evidence)
    finally:
        os.close(descriptor)


def main() -> int:
    try:
        if len(sys.argv) != 2:
            return 0
        raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
        record(raw, Path(sys.argv[1]))
    except (OSError, RuntimeError):
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
