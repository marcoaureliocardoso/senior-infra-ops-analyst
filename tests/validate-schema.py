#!/usr/bin/env python3
"""Validate nori.json schema beyond JSON parse — structural and semantic checks."""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "nori.json"
errors = []


def err(msg: str) -> None:
    errors.append(msg)


def main() -> None:
    if not MANIFEST_PATH.exists():
        err("nori.json not found")
        _report()

    with open(MANIFEST_PATH, encoding="utf-8") as fh:
        manifest = json.load(fh)

    # Required top-level fields
    for field in ["name", "version", "description", "author", "license", "skills", "references"]:
        if field not in manifest:
            err(f"nori.json missing required field: {field}")

    # Version must be valid semver
    version = manifest.get("version", "")
    if not re.match(r"^\d+\.\d+\.\d+$", str(version)):
        err(f"nori.json version '{version}' is not valid semver (X.Y.Z)")

    # Repository/homepage/bugs should not be TBD placeholders
    for field in ["repository", "homepage"]:
        value = manifest.get(field, "")
        if isinstance(value, str) and value.startswith("TBD"):
            err(f"nori.json {field} is still a TBD placeholder: '{value}'")

    bugs = manifest.get("bugs", {})
    if isinstance(bugs, dict):
        bugs_url = bugs.get("url", "")
        if isinstance(bugs_url, str) and bugs_url.startswith("TBD"):
            err(f"nori.json bugs.url is still a TBD placeholder: '{bugs_url}'")

    # Skills must be unique
    skills = manifest.get("skills", [])
    if len(skills) != len(set(skills)):
        seen: dict[str, int] = {}
        for s in skills:
            seen[s] = seen.get(s, 0) + 1
        dups = [f"{s} (x{c})" for s, c in seen.items() if c > 1]
        err(f"nori.json skills contains duplicates: {dups}")

    # References must be unique
    refs = manifest.get("references", [])
    if len(refs) != len(set(refs)):
        seen_refs: dict[str, int] = {}
        for r in refs:
            seen_refs[r] = seen_refs.get(r, 0) + 1
        dups = [f"{r} (x{c})" for r, c in seen_refs.items() if c > 1]
        err(f"nori.json references contains duplicates: {dups}")

    # Every skill must have a directory
    for skill in skills:
        skill_dir = ROOT / "skills" / skill
        if not skill_dir.is_dir():
            err(f"skill '{skill}' listed in nori.json but directory missing: {skill_dir}")
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            err(f"skill '{skill}' missing SKILL.md: {skill_md}")

    # Every reference must exist on disk
    for ref in refs:
        ref_path = ROOT / ref
        if not ref_path.exists():
            err(f"reference '{ref}' listed in nori.json but file missing: {ref_path}")

    # Tags should be unique
    tags = manifest.get("tags", [])
    if len(tags) != len(set(tags)):
        seen_tags: dict[str, int] = {}
        for t in tags:
            seen_tags[t] = seen_tags.get(t, 0) + 1
        dups = [f"{t} (x{c})" for t, c in seen_tags.items() if c > 1]
        err(f"nori.json tags contains duplicates: {dups}")

    _report()


def _report() -> None:
    if errors:
        print("Schema validation failed:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    print("schema validation passed")


if __name__ == "__main__":
    main()
