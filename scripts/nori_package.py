#!/usr/bin/env python3
"""Shared validation and discovery for the canonical Nori package."""
from __future__ import annotations

import json
import hashlib
import os
import re
import shutil
import tempfile
import uuid
from dataclasses import asdict, dataclass
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
STAGING_ROOT_FILES = ("AGENTS.md", "LICENSE", "nori.json", "skills.json")
STAGING_ROOT_DIRS = ("references", "skills", "slashcommands", "subagents")
REPARSE_POINT_FLAG = 0x400
SENSITIVE_SUFFIXES = (
    ".pem",
    ".key",
    ".crt",
    ".p12",
    ".pfx",
    ".kubeconfig",
    ".token",
    ".ovpn",
    ".pgpass",
)
SENSITIVE_NAMES = frozenset(
    {".env", ".netrc", ".my.cnf", "credentials", "credentials.json"}
)


@dataclass(frozen=True, order=True)
class InventoryEntry:
    """One deterministic staged-file inventory record."""

    path: str
    size: int
    sha256: str

    def to_dict(self) -> dict[str, str | int]:
        return asdict(self)


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


def _is_link_or_reparse(path: Path) -> bool:
    if path.is_symlink():
        return True
    try:
        attributes = getattr(path.stat(follow_symlinks=False), "st_file_attributes", 0)
    except OSError:
        return False
    return bool(attributes & REPARSE_POINT_FLAG)


def _is_sensitive_path(relative: Path) -> bool:
    for part in relative.parts:
        lowered = part.lower()
        if lowered in SENSITIVE_NAMES or lowered.startswith(".env."):
            return True
        if lowered.endswith(SENSITIVE_SUFFIXES):
            return True
        if "service-account" in lowered:
            return True
    return False


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _inventory_entry(root: Path, path: Path) -> InventoryEntry:
    relative = path.relative_to(root).as_posix()
    stat_result = path.stat(follow_symlinks=False)
    return InventoryEntry(relative, stat_result.st_size, _sha256(path))


def _source_files(root: Path) -> tuple[list[str], tuple[Path, ...]]:
    if _is_link_or_reparse(root):
        return ["source root is a symlink or reparse point"], ()
    errors = [*validate_manifest(root), *validate_repository_inventory(root)]
    files: list[Path] = []

    for name in STAGING_ROOT_FILES:
        path = root / name
        if not path.is_file():
            errors.append(f"required staging file is missing: {name}")
        elif _is_link_or_reparse(path):
            errors.append(f"symlink or reparse point is not allowed: {name}")
        else:
            files.append(path)

    for name in STAGING_ROOT_DIRS:
        directory = root / name
        if not directory.is_dir():
            errors.append(f"required staging directory is missing: {name}")
            continue
        if _is_link_or_reparse(directory):
            errors.append(f"symlink or reparse point is not allowed: {name}")
            continue
        for current, directories, filenames in os.walk(
            directory, topdown=True, followlinks=False
        ):
            current_path = Path(current)
            for child_name in list(directories):
                child = current_path / child_name
                relative = child.relative_to(root)
                if _is_link_or_reparse(child):
                    errors.append(
                        "symlink or reparse point is not allowed: "
                        f"{relative.as_posix()}"
                    )
                    directories.remove(child_name)
                elif _is_sensitive_path(relative):
                    errors.append(
                        f"sensitive path is not allowed: {relative.as_posix()}"
                    )
                    directories.remove(child_name)
            for filename in filenames:
                path = current_path / filename
                relative = path.relative_to(root)
                if _is_link_or_reparse(path):
                    errors.append(
                        "symlink or reparse point is not allowed: "
                        f"{relative.as_posix()}"
                    )
                elif _is_sensitive_path(relative):
                    errors.append(
                        f"sensitive path is not allowed: {relative.as_posix()}"
                    )
                elif not path.is_file():
                    errors.append(
                        f"non-regular package entry is not allowed: {relative.as_posix()}"
                    )
                else:
                    files.append(path)

    unique_files = tuple(sorted(set(files), key=lambda path: path.relative_to(root).as_posix()))
    return errors, unique_files


def validate_source(
    source: Path,
) -> tuple[list[str], tuple[InventoryEntry, ...]]:
    """Validate and inventory the current source package without staging it."""
    source = Path(os.path.abspath(source))
    errors, source_files = _source_files(source)
    if errors:
        return errors, ()
    return errors, tuple(_inventory_entry(source, path) for path in source_files)


def validate_destination(source: Path, destination: Path) -> list[str]:
    """Reject destinations that could erase source, home, or a broad root."""
    errors: list[str] = []
    source_resolved = source.resolve()
    destination_absolute = Path(os.path.abspath(destination))
    if _is_link_or_reparse(destination_absolute):
        errors.append("destination is a symlink or reparse point")
    for ancestor in destination_absolute.parents:
        if ancestor == Path(destination_absolute.anchor):
            break
        if ancestor.exists() and _is_link_or_reparse(ancestor):
            errors.append("destination ancestor is a symlink or reparse point")
            break
    destination_resolved = destination_absolute.resolve(strict=False)
    home_resolved = Path.home().resolve()
    drive_root = Path(destination_resolved.anchor).resolve()

    overlaps_source = (
        destination_resolved == source_resolved
        or destination_resolved in source_resolved.parents
        or source_resolved in destination_resolved.parents
    )
    if overlaps_source:
        errors.append("unsafe staging destination overlaps the source")
    if destination_resolved in {home_resolved, drive_root}:
        errors.append("unsafe staging destination is a protected root")
    if destination_resolved.name in {"", ".", ".."}:
        errors.append("unsafe staging destination is not a named directory")
    return errors


def _destination_paths(destination: Path) -> tuple[set[str], list[str]]:
    paths: set[str] = set()
    errors: list[str] = []
    if not destination.exists():
        return paths, errors
    if not destination.is_dir() or _is_link_or_reparse(destination):
        return paths, ["destination is not a regular directory"]
    for current, directories, filenames in os.walk(
        destination, topdown=True, followlinks=False
    ):
        current_path = Path(current)
        for child_name in list(directories):
            child = current_path / child_name
            relative = child.relative_to(destination).as_posix()
            if _is_link_or_reparse(child):
                errors.append(
                    f"symlink or reparse point is not allowed: {relative}"
                )
                directories.remove(child_name)
            paths.add(relative + "/")
        for filename in filenames:
            path = current_path / filename
            relative = path.relative_to(destination).as_posix()
            if _is_link_or_reparse(path):
                errors.append(
                    f"symlink or reparse point is not allowed: {relative}"
                )
            elif not path.is_file():
                errors.append(f"non-regular destination entry: {relative}")
            paths.add(relative)
    return paths, errors


def _allowed_destination_paths(source: Path, source_files: tuple[Path, ...]) -> set[str]:
    allowed = set(STAGING_ROOT_DIRS)
    allowed.update(name + "/" for name in STAGING_ROOT_DIRS)
    allowed.update(STAGING_ROOT_FILES)
    for path in source_files:
        relative = path.relative_to(source)
        for parent in relative.parents:
            if parent != Path("."):
                allowed.add(parent.as_posix() + "/")
        allowed.add(relative.as_posix())
    return allowed


def validate_staging(
    source: Path, destination: Path
) -> tuple[list[str], tuple[InventoryEntry, ...]]:
    """Compare an existing staging tree with its canonical source."""
    errors = validate_destination(source, destination)
    source_errors, source_files = _source_files(source)
    errors.extend(source_errors)
    if _is_link_or_reparse(destination):
        return errors, ()
    if not destination.is_dir():
        errors.append("staging destination does not exist")
        return errors, ()

    actual_paths, destination_errors = _destination_paths(destination)
    errors.extend(destination_errors)
    allowed_paths = _allowed_destination_paths(source, source_files)
    for relative in sorted(actual_paths - allowed_paths):
        errors.append(f"unexpected destination entry: {relative.rstrip('/')}")

    inventory: list[InventoryEntry] = []
    expected_relative = {
        path.relative_to(source).as_posix(): path for path in source_files
    }
    actual_files = {
        value for value in actual_paths if not value.endswith("/")
    }
    for relative in sorted(set(expected_relative) - actual_files):
        errors.append(f"staging file is missing: {relative}")
    for relative, source_path in sorted(expected_relative.items()):
        staged_path = destination / relative
        if not staged_path.is_file() or _is_link_or_reparse(staged_path):
            continue
        staged_entry = _inventory_entry(destination, staged_path)
        inventory.append(staged_entry)
        source_entry = _inventory_entry(source, source_path)
        if (
            staged_entry.size != source_entry.size
            or staged_entry.sha256 != source_entry.sha256
        ):
            errors.append(f"content differs from source: {relative}")
    return errors, tuple(inventory)


def build_staging(
    source: Path, destination: Path, replace: bool = False
) -> tuple[InventoryEntry, ...]:
    """Atomically build a validated staging tree from the canonical allowlist."""
    source = Path(os.path.abspath(source))
    destination = Path(os.path.abspath(destination))
    errors = validate_destination(source, destination)
    source_errors, source_files = _source_files(source)
    errors.extend(source_errors)
    if errors:
        raise ValueError("\n".join(errors))

    if destination.exists():
        if not replace:
            raise ValueError("destination already exists; use --replace")
        destination_errors, _ = validate_staging(source, destination)
        if destination_errors:
            raise ValueError("\n".join(destination_errors))

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(
            prefix=f".{destination.name}.tmp-", dir=str(destination.parent)
        )
    )
    try:
        for source_path in source_files:
            relative = source_path.relative_to(source)
            staged_path = temporary / relative
            staged_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source_path, staged_path, follow_symlinks=False)

        staged_errors, inventory = validate_staging(source, temporary)
        if staged_errors:
            raise ValueError("\n".join(staged_errors))

        if destination.exists():
            backup = destination.with_name(
                f".{destination.name}.backup-{uuid.uuid4().hex}"
            )
            destination.replace(backup)
            try:
                destination_errors, _ = validate_staging(source, backup)
                if destination_errors:
                    backup.replace(destination)
                    raise ValueError("\n".join(destination_errors))
                temporary.replace(destination)
            except BaseException:
                if backup.exists() and not destination.exists():
                    backup.replace(destination)
                raise
            if backup.exists():
                shutil.rmtree(backup)
        else:
            temporary.replace(destination)
        return inventory
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
