#!/usr/bin/env python3
"""Validate canonical Nori and repository packaging metadata."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.nori_package import (  # noqa: E402
    load_json,
    validate_manifest,
    validate_repository_inventory,
)


errors: list[str] = []


def err(message: str) -> None:
    errors.append(message)


def read_object(path: Path, label: str) -> dict[str, object] | None:
    try:
        value = load_json(path)
    except FileNotFoundError:
        err(f"{label} not found")
        return None
    except (OSError, json.JSONDecodeError) as exc:
        err(f"{label} is not valid JSON: {exc}")
        return None
    if not isinstance(value, dict):
        err(f"{label} must be a JSON object")
        return None
    return value


def validate_release_metadata() -> None:
    manifest = read_object(ROOT / "nori.json", "nori.json")
    nori_version = read_object(ROOT / ".nori-version", ".nori-version")
    if nori_version is not None:
        for field in ("version", "registryUrl"):
            if field not in nori_version:
                err(f".nori-version missing required field: {field}")
        metadata_version = nori_version.get("version")
        if not isinstance(metadata_version, str) or not re.fullmatch(
            r"\d+\.\d+\.\d+", metadata_version
        ):
            err(
                ".nori-version version "
                f"'{metadata_version}' is not valid semver (X.Y.Z)"
            )
        if manifest is not None and metadata_version != manifest.get("version"):
            err(
                ".nori-version version must match nori.json: "
                f"'{metadata_version}' != '{manifest.get('version')}'"
            )

    profile = read_object(ROOT / "profile.json", "profile.json")
    if profile is not None:
        for field in ("name", "description"):
            if field not in profile:
                err(f"profile.json missing required field: {field}")


def report() -> None:
    if errors:
        print("Schema validation failed:")
        for message in errors:
            print(f"  - {message}")
        raise SystemExit(1)
    print("schema validation passed")


def main() -> None:
    errors.extend(validate_manifest(ROOT))
    errors.extend(validate_repository_inventory(ROOT))
    validate_release_metadata()
    report()


if __name__ == "__main__":
    main()
