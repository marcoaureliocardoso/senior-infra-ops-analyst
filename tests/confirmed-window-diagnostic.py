#!/usr/bin/env python3
"""Require an operator-confirmed capacity to equal structural /context evidence."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


POSITIVE_INTEGER = re.compile(r"^[1-9][0-9]*$")
def fail(message: str) -> int:
    print(f"BLOCKED: {message}", file=sys.stderr)
    return 2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", required=True)
    parser.add_argument("--confirmed", required=True)
    args = parser.parse_args()

    if not POSITIVE_INTEGER.fullmatch(args.confirmed):
        return fail("confirmed capacity requires a positive integer")
    try:
        path = Path(args.events)
        if not path.is_file() or path.stat().st_size > 64 * 1024:
            return fail("native context capacity unavailable")
        events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    except (OSError, UnicodeError, json.JSONDecodeError):
        return fail("native context capacity unavailable")
    matches = [
        event.get("windowTokens") for event in events
        if isinstance(event, dict)
        and event.get("kind") == "status-context"
        and type(event.get("percent")) is int
        and 0 <= event["percent"] <= 100
    ]
    if (not matches or any(type(value) is not int or not 0 < value <= 10_000_000 for value in matches)
            or len(set(matches)) != 1):
        return fail("native context capacity unavailable")
    native = matches[-1]
    confirmed = int(args.confirmed)
    if confirmed != native:
        return fail("confirmed capacity does not equal native context capacity")
    print(native)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
