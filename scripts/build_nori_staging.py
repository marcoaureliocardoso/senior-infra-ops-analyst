#!/usr/bin/env python3
"""Build or verify deterministic Nori upload staging."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.nori_package import build_staging, validate_staging  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--destination", required=True, type=Path)
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    if args.check and args.replace:
        parser.error("--check and --replace cannot be combined")
    return args


def main() -> int:
    args = parse_args()
    try:
        if args.check:
            errors, inventory = validate_staging(args.source, args.destination)
            if errors:
                raise ValueError("\n".join(errors))
        else:
            inventory = build_staging(
                args.source, args.destination, replace=args.replace
            )
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.as_json:
        print(
            json.dumps(
                [entry.to_dict() for entry in inventory],
                ensure_ascii=True,
                indent=2,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
