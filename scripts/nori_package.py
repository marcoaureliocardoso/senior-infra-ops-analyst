#!/usr/bin/env python3
"""Shared validation and discovery for the canonical Nori package."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


CANONICAL_MANIFEST_FIELDS = frozenset(
    {
        "name",
        "version",
        "description",
        "author",
        "license",
        "repository",
        "keywords",
        "dependencies",
    }
)
SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
PACKAGE_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
REQUIRED_SKILL_DEPENDENCIES = {"read-the-damn-docs": "latest"}


def load_json(path: Path) -> object:
    """Load one UTF-8 JSON document."""
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def discover_skill_ids(root: Path) -> tuple[str, ...]:
    """Return sorted skill directory IDs backed by a regular SKILL.md."""
    skills_dir = root / "skills"
    if not skills_dir.is_dir():
        return ()
    return tuple(
        sorted(
            entry.name
            for entry in skills_dir.iterdir()
            if entry.is_dir() and (entry / "SKILL.md").is_file()
        )
    )


def discover_reference_paths(root: Path) -> tuple[str, ...]:
    """Return sorted root-relative packaged Markdown references."""
    references_dir = root / "references"
    if not references_dir.is_dir():
        return ()
    return tuple(
        sorted(
            path.relative_to(root).as_posix()
            for path in references_dir.glob("*.md")
            if path.is_file()
        )
    )


def discover_subagent_ids(root: Path) -> tuple[str, ...]:
    """Return sorted flat Markdown subagent IDs."""
    subagents_dir = root / "subagents"
    if not subagents_dir.is_dir():
        return ()
    return tuple(
        sorted(path.stem for path in subagents_dir.glob("*.md") if path.is_file())
    )


def _read_object(path: Path, label: str, errors: list[str]) -> dict[str, Any] | None:
    try:
        value = load_json(path)
    except FileNotFoundError:
        errors.append(f"{label} not found")
        return None
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{label} is not valid JSON: {exc}")
        return None
    if not isinstance(value, dict):
        errors.append(f"{label} must be a JSON object")
        return None
    return value


def validate_manifest(root: Path) -> list[str]:
    """Validate the canonical root Nori manifest and instruction source."""
    errors: list[str] = []
    manifest = _read_object(root / "nori.json", "nori.json", errors)
    if manifest is None:
        return errors

    if "tags" in manifest:
        errors.append("nori.json legacy field is not allowed: tags")
    for field in sorted(CANONICAL_MANIFEST_FIELDS - set(manifest)):
        errors.append(f"nori.json missing required field: {field}")
    for field in sorted(set(manifest) - CANONICAL_MANIFEST_FIELDS - {"tags"}):
        errors.append(f"nori.json unexpected field: {field}")

    for field in ("name", "description", "author", "license", "repository"):
        value = manifest.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"nori.json {field} must be a non-empty string")
        elif value.startswith("TBD"):
            errors.append(f"nori.json {field} is still a TBD placeholder: '{value}'")

    name = manifest.get("name")
    if isinstance(name, str) and not PACKAGE_ID_PATTERN.fullmatch(name):
        errors.append(f"nori.json name is not a canonical package id: '{name}'")

    version = manifest.get("version")
    if not isinstance(version, str) or not SEMVER_PATTERN.fullmatch(version):
        errors.append(
            f"nori.json version '{version}' is not valid semver (X.Y.Z)"
        )

    keywords = manifest.get("keywords")
    if not isinstance(keywords, list):
        errors.append("nori.json keywords must be an array")
    else:
        invalid_keywords = [
            value for value in keywords if not isinstance(value, str) or not value
        ]
        if invalid_keywords:
            errors.append("nori.json keywords must contain non-empty strings")
        string_keywords = [value for value in keywords if isinstance(value, str)]
        if len(string_keywords) != len(set(string_keywords)):
            errors.append("nori.json keywords contains duplicates")

    dependencies = manifest.get("dependencies")
    if not isinstance(dependencies, dict):
        errors.append("nori.json dependencies must be an object")
    else:
        skill_dependencies = dependencies.get("skills")
        if not isinstance(skill_dependencies, dict):
            errors.append("nori.json dependencies.skills must be an object")
        elif skill_dependencies != REQUIRED_SKILL_DEPENDENCIES:
            errors.append(
                "nori.json read-the-damn-docs dependency must be 'latest' "
                "and the only skill dependency"
            )
        unexpected_dependency_groups = set(dependencies) - {"skills"}
        for group in sorted(unexpected_dependency_groups):
            errors.append(f"nori.json unexpected dependency group: {group}")

    agents_path = root / "AGENTS.md"
    if not agents_path.is_file():
        errors.append("AGENTS.md is required at the package root")
    else:
        try:
            if not agents_path.read_text(encoding="utf-8").strip():
                errors.append("AGENTS.md must not be empty")
        except OSError as exc:
            errors.append(f"AGENTS.md could not be read: {exc}")

    if (root / "CLAUDE.md").exists():
        errors.append("root CLAUDE.md is not allowed; AGENTS.md is canonical")

    return errors


def validate_repository_inventory(root: Path) -> list[str]:
    """Validate filesystem-discovered package assets and metadata."""
    errors: list[str] = []
    skills_dir = root / "skills"
    if not skills_dir.is_dir():
        errors.append("skills directory not found")
        skill_ids: tuple[str, ...] = ()
    else:
        for entry in sorted(skills_dir.iterdir(), key=lambda path: path.name):
            if entry.is_dir() and not (entry / "SKILL.md").is_file():
                errors.append(f"packaged skill '{entry.name}' missing SKILL.md")
        skill_ids = discover_skill_ids(root)

    skills_catalog = _read_object(root / "skills.json", "skills.json", errors)
    if skills_catalog is not None:
        discovered = set(skill_ids)
        catalogued = set(skills_catalog)
        for skill_id in sorted(discovered - catalogued):
            errors.append(
                f"packaged skill '{skill_id}' not found in skills.json"
            )
        for skill_id in sorted(catalogued - discovered):
            errors.append(
                f"skills.json entry '{skill_id}' has no packaged skill directory"
            )
        for skill_id, version in sorted(skills_catalog.items()):
            if not isinstance(version, str) or not version:
                errors.append(
                    f"skills.json version for '{skill_id}' must be a non-empty string"
                )

    for skill_id in skill_ids:
        if not PACKAGE_ID_PATTERN.fullmatch(skill_id):
            errors.append(f"packaged skill id is invalid: '{skill_id}'")
        metadata_path = root / "skills" / skill_id / "nori.json"
        metadata = _read_object(
            metadata_path, f"skills/{skill_id}/nori.json", errors
        )
        if metadata is None:
            continue
        for field in ("name", "version", "type", "description"):
            if field not in metadata:
                errors.append(
                    f"skills/{skill_id}/nori.json missing required field: {field}"
                )
        if metadata.get("name") != skill_id:
            errors.append(
                f"skills/{skill_id}/nori.json name must match directory id"
            )
        if metadata.get("type") != "skill":
            errors.append(
                f"skills/{skill_id}/nori.json type must be 'skill', "
                f"got '{metadata.get('type')}'"
            )
        skill_version = metadata.get("version")
        if not isinstance(skill_version, str) or not SEMVER_PATTERN.fullmatch(
            skill_version
        ):
            errors.append(
                f"skills/{skill_id}/nori.json version '{skill_version}' "
                "is not valid semver (X.Y.Z)"
            )

    if not discover_reference_paths(root):
        errors.append("no packaged references discovered")
    if not discover_subagent_ids(root):
        errors.append("no packaged subagents discovered")

    return errors
