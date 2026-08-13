#!/usr/bin/env python3
"""Build a fresh, verified ZIP from canonical Nori staging."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(ROOT))

from scripts.nori_package import InventoryEntry, validate_staging  # noqa: E402


def build_archive(
    source: Path, staging: Path, output: Path
) -> tuple[InventoryEntry, ...]:
    source = Path(os.path.abspath(source))
    staging = Path(os.path.abspath(staging))
    output = Path(os.path.abspath(output))
    output_resolved = output.resolve(strict=False)
    if output_resolved == staging or staging in output_resolved.parents:
        raise ValueError("archive output must be outside staging")

    errors, inventory = validate_staging(source, staging)
    if errors:
        raise ValueError("\n".join(errors))

    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output.name}.tmp-", dir=output.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        with zipfile.ZipFile(
            temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as archive:
            for entry in inventory:
                data = (staging / entry.path).read_bytes()
                info = zipfile.ZipInfo(entry.path, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, data, compresslevel=9)

        with zipfile.ZipFile(temporary) as archive:
            if archive.namelist() != [entry.path for entry in inventory]:
                raise ValueError("archive inventory differs from staging")
            for entry in inventory:
                digest = hashlib.sha256(archive.read(entry.path)).hexdigest()
                if digest != entry.sha256:
                    raise ValueError(f"archive content differs from staging: {entry.path}")

        os.replace(temporary, output)
        return inventory
    finally:
        if temporary.exists():
            temporary.unlink()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--staging", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        inventory = build_archive(args.source, args.staging, args.output)
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
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
