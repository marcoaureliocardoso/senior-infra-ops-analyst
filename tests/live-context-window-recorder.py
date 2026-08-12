#!/usr/bin/env python3
"""Record only native status-line context capacity and percentage metadata."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


MAX_INPUT_BYTES = 64 * 1024
MAX_WINDOW_TOKENS = 10_000_000


def main() -> int:
    rendered = "ctx --"
    try:
        if len(sys.argv) != 2:
            raise ValueError("destination required")
        payload = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
        if len(payload) > MAX_INPUT_BYTES:
            raise ValueError("input too large")
        value = json.loads(payload.decode("utf-8"))
        context = value.get("context_window") if isinstance(value, dict) else None
        window = context.get("context_window_size") if isinstance(context, dict) else None
        percent = context.get("used_percentage") if isinstance(context, dict) else None
        if (type(window) is not int or not 0 < window <= MAX_WINDOW_TOKENS
                or type(percent) not in {int, float} or isinstance(percent, bool)
                or not 0 <= percent <= 100):
            raise ValueError("context metadata unavailable")
        rounded = round(percent)
        event = json.dumps({
            "kind": "status-context", "percent": rounded, "windowTokens": window,
        }, sort_keys=True, separators=(",", ":")) + "\n"
        destination = Path(sys.argv[1])
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
        rendered = f"ctx {rounded}%"
    except Exception:
        pass
    sys.stdout.write(rendered + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
