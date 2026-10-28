#!/usr/bin/env python3
"""Record only native status-line context capacity and percentage metadata."""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path


MAX_INPUT_BYTES = 64 * 1024
MAX_WINDOW_TOKENS = 10_000_000
LABEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/+@-]{0,95}$")


def append_event(destination: Path, event_value: dict[str, object]) -> None:
    event = json.dumps(event_value, sort_keys=True, separators=(",", ":")) + "\n"
    descriptor = os.open(destination, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
    try:
        remaining = memoryview(event.encode("utf-8"))
        while remaining:
            written = os.write(descriptor, remaining)
            if written <= 0:
                raise OSError("status event write made no progress")
            remaining = remaining[written:]
    finally:
        os.close(descriptor)


def main() -> int:
    rendered = "ctx --"
    destination: Path | None = None
    binding: dict[str, object] | None = None
    try:
        if len(sys.argv) not in {2, 4}:
            raise ValueError("destination required")
        destination = Path(sys.argv[1])
        if len(sys.argv) == 4:
            nonce, stage = sys.argv[2:]
            if not LABEL.fullmatch(nonce) or not LABEL.fullmatch(stage):
                raise ValueError("invalid binding")
            binding = {"runNonce": nonce, "stage": stage}
    except Exception:
        sys.stdout.write(rendered + "\n")
        return 0

    try:
        payload = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
        if len(payload) > MAX_INPUT_BYTES:
            raise ValueError("input too large")
        value = json.loads(payload.decode("utf-8"))
    except Exception:
        if destination is not None and binding is not None:
            try:
                append_event(destination, {
                    "kind": "status-context-rejected",
                    "reasonCode": "INVALID_STATUS_PAYLOAD", **binding,
                })
            except Exception:
                pass
        sys.stdout.write(rendered + "\n")
        return 0

    context = value.get("context_window") if isinstance(value, dict) else object()
    unavailable = (
        context is None
        or (isinstance(context, dict)
            and (context.get("context_window_size") is None
                 or context.get("used_percentage") is None))
    )
    if unavailable:
        if binding is not None:
            try:
                append_event(destination, {
                    "kind": "status-context-unavailable",
                    "reasonCode": "NATIVE_FIELDS_NOT_SUPPLIED", **binding,
                })
            except Exception:
                pass
        sys.stdout.write(rendered + "\n")
        return 0

    window = context.get("context_window_size") if isinstance(context, dict) else None
    percent = context.get("used_percentage") if isinstance(context, dict) else None
    if (type(window) is not int or not 0 < window <= MAX_WINDOW_TOKENS
            or type(percent) not in {int, float} or isinstance(percent, bool)
            or not 0 <= percent <= 100):
        if binding is not None:
            try:
                append_event(destination, {
                    "kind": "status-context-rejected",
                    "reasonCode": "INVALID_NATIVE_FIELDS", **binding,
                })
            except Exception:
                pass
        sys.stdout.write(rendered + "\n")
        return 0

    rounded = round(percent)
    event_value = {
        "kind": "status-context", "percent": rounded, "windowTokens": window,
    }
    if binding is not None:
        event_value.update(binding)
    try:
        append_event(destination, event_value)
        rendered = f"ctx {rounded}%"
    except Exception:
        pass
    sys.stdout.write(rendered + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
