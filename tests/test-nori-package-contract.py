#!/usr/bin/env python3
"""Mutation tests for the canonical Nori package contract."""
from __future__ import annotations

import importlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CANONICAL_FIELDS = {
    "name",
    "version",
    "description",
    "author",
    "license",
    "repository",
    "keywords",
    "dependencies",
}


class NoriPackageContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.sandbox = Path(self.tempdir.name) / "package"
        shutil.copytree(
            ROOT,
            self.sandbox,
            ignore=shutil.ignore_patterns(
                ".git", ".worktrees", ".tmp", "__pycache__"
            ),
        )
        self.manifest_path = self.sandbox / "nori.json"

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def read_manifest(self) -> dict[str, object]:
        return json.loads(self.manifest_path.read_text(encoding="utf-8"))

    def write_manifest(self, manifest: dict[str, object]) -> None:
        self.manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def canonicalize_manifest(self) -> dict[str, object]:
        manifest = self.read_manifest()
        manifest["keywords"] = manifest.pop("tags", manifest.get("keywords", []))
        manifest["dependencies"] = {
            "skills": {"read-the-damn-docs": "latest"}
        }
        for field in (
            "type",
            "skills",
            "references",
            "subagents",
            "homepage",
            "bugs",
        ):
            manifest.pop(field, None)
        self.write_manifest(manifest)
        return manifest

    def run_validator(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "tests/validate-schema.py"],
            cwd=self.sandbox,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_repository_manifest_uses_only_canonical_fields(self) -> None:
        manifest = json.loads((ROOT / "nori.json").read_text(encoding="utf-8"))
        self.assertEqual(set(manifest), CANONICAL_FIELDS)

    def test_canonical_manifest_is_accepted(self) -> None:
        self.canonicalize_manifest()
        result = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_legacy_tags_are_rejected(self) -> None:
        manifest = self.canonicalize_manifest()
        manifest["tags"] = manifest.pop("keywords")
        self.write_manifest(manifest)
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("legacy field is not allowed: tags", result.stdout)

    def test_array_skill_dependencies_are_rejected(self) -> None:
        manifest = self.canonicalize_manifest()
        manifest["dependencies"] = {"skills": ["read-the-damn-docs"]}
        self.write_manifest(manifest)
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("dependencies.skills must be an object", result.stdout)

    def test_wrong_dependency_version_is_rejected(self) -> None:
        manifest = self.canonicalize_manifest()
        manifest["dependencies"] = {
            "skills": {"read-the-damn-docs": "*"}
        }
        self.write_manifest(manifest)
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "read-the-damn-docs dependency must be 'latest'", result.stdout
        )

    def test_reintroduced_inventory_field_is_rejected(self) -> None:
        manifest = self.canonicalize_manifest()
        manifest["skills"] = ["context-continuity"]
        self.write_manifest(manifest)
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unexpected field: skills", result.stdout)

    def test_duplicate_keyword_is_rejected(self) -> None:
        manifest = self.canonicalize_manifest()
        keywords = manifest["keywords"]
        assert isinstance(keywords, list)
        keywords.append(keywords[0])
        self.write_manifest(manifest)
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("keywords contains duplicates", result.stdout)

    def test_missing_agents_md_is_rejected(self) -> None:
        self.canonicalize_manifest()
        (self.sandbox / "AGENTS.md").unlink()
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("AGENTS.md is required", result.stdout)

    def test_empty_agents_md_is_rejected(self) -> None:
        self.canonicalize_manifest()
        (self.sandbox / "AGENTS.md").write_text("", encoding="utf-8")
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("AGENTS.md must not be empty", result.stdout)

    def test_missing_skill_catalog_entry_is_rejected(self) -> None:
        self.canonicalize_manifest()
        skills_path = self.sandbox / "skills.json"
        skills = json.loads(skills_path.read_text(encoding="utf-8"))
        skills.pop("context-continuity")
        skills_path.write_text(
            json.dumps(skills, indent=2) + "\n", encoding="utf-8"
        )
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "packaged skill 'context-continuity' not found in skills.json",
            result.stdout,
        )

    def test_missing_per_skill_metadata_is_rejected(self) -> None:
        self.canonicalize_manifest()
        (self.sandbox / "skills" / "context-continuity" / "nori.json").unlink()
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("skills/context-continuity/nori.json not found", result.stdout)

    def test_filesystem_discovery_exposes_package_assets(self) -> None:
        try:
            module = importlib.import_module("scripts.nori_package")
        except ModuleNotFoundError as exc:
            self.fail(f"shared Nori package module is missing: {exc}")
        self.assertIn("context-continuity", module.discover_skill_ids(ROOT))
        self.assertIn(
            "references/risk-levels.md", module.discover_reference_paths(ROOT)
        )
        self.assertIn("diagnostic-operator", module.discover_subagent_ids(ROOT))


if __name__ == "__main__":
    unittest.main()
