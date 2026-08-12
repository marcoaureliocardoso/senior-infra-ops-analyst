#!/usr/bin/env python3
"""Require an operator-confirmed capacity to equal the native PTY label."""
from __future__ import annotations

import argparse
import re
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path


POSITIVE_INTEGER = re.compile(r"^[1-9][0-9]*$")
WINDOW_LABEL = re.compile(r"\[(\d+(?:\.\d+)?)([kKmM])\]")
MULTIPLIER = {"k": 1_000, "m": 1_000_000}


def fail(message: str) -> int:
    print(f"BLOCKED: {message}", file=sys.stderr)
    return 2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture", required=True)
    parser.add_argument("--confirmed", required=True)
    args = parser.parse_args()

    if not POSITIVE_INTEGER.fullmatch(args.confirmed):
        return fail("confirmed capacity requires a positive integer")
    try:
        text = Path(args.capture).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return fail("native context capacity unavailable")
    labels = WINDOW_LABEL.findall(text)
    if not labels:
        return fail("native context capacity unavailable")
    amount, unit = labels[-1]
    try:
        native_decimal = Decimal(amount) * MULTIPLIER[unit.lower()]
    except (InvalidOperation, KeyError):
        return fail("native context capacity unavailable")
    if native_decimal <= 0 or native_decimal != native_decimal.to_integral_value():
        return fail("native context capacity unavailable")
    native = int(native_decimal)
    confirmed = int(args.confirmed)
    if confirmed != native:
        return fail("confirmed capacity does not equal native context capacity")
    print(native)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
