#!/usr/bin/env python3
"""Mutation tests for repository packaging metadata validation."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SchemaValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tempdir = tempfile.TemporaryDirectory()
        cls.sandbox = Path(cls.tempdir.name) / "package"
        shutil.copytree(
            ROOT,
            cls.sandbox,
            ignore=shutil.ignore_patterns(
                ".git", ".worktrees", ".tmp", "__pycache__"
            ),
        )
        cls.manifest_path = cls.sandbox / "nori.json"
        cls.original_manifest = cls.manifest_path.read_text(encoding="utf-8")
        cls.nori_version_path = cls.sandbox / ".nori-version"
        cls.original_nori_version = cls.nori_version_path.read_text(
            encoding="utf-8"
        )
        cls.skills_json_path = cls.sandbox / "skills.json"
        cls.original_skills_json = cls.skills_json_path.read_text(
            encoding="utf-8"
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tempdir.cleanup()

    def tearDown(self) -> None:
        self.manifest_path.write_text(self.original_manifest, encoding="utf-8")
        self.nori_version_path.write_text(
            self.original_nori_version, encoding="utf-8"
        )
        self.skills_json_path.write_text(
            self.original_skills_json, encoding="utf-8"
        )

    def run_validator(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "tests/validate-schema.py"],
            cwd=self.sandbox,
            capture_output=True,
            text=True,
            check=False,
        )

    def write_manifest(self, manifest: dict[str, object]) -> None:
        self.manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def test_canonical_manifest_is_accepted(self) -> None:
        result = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_current_package_version_is_0_13_0(self) -> None:
        manifest = json.loads(self.original_manifest)
        metadata = json.loads(self.original_nori_version)
        self.assertEqual(manifest["version"], "0.13.0")
        self.assertEqual(metadata["version"], "0.13.0")

    def test_legacy_manifest_type_is_rejected(self) -> None:
        manifest = json.loads(self.original_manifest)
        manifest["type"] = "skillset"
        self.write_manifest(manifest)
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unexpected field: type", result.stdout)

    def test_removed_reference_inventory_is_rejected(self) -> None:
        manifest = json.loads(self.original_manifest)
        manifest["references"] = ["references/risk-levels.md"]
        self.write_manifest(manifest)
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unexpected field: references", result.stdout)

    def test_nori_version_must_match_manifest(self) -> None:
        metadata = json.loads(self.original_nori_version)
        metadata["version"] = "9.9.9"
        self.nori_version_path.write_text(
            json.dumps(metadata) + "\n", encoding="utf-8"
        )
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            ".nori-version version must match nori.json",
            result.stdout + result.stderr,
        )

    def test_context_continuity_is_discovered_and_catalogued(self) -> None:
        skills = json.loads(self.original_skills_json)
        self.assertTrue(
            (self.sandbox / "skills" / "context-continuity" / "SKILL.md").is_file()
        )
        self.assertEqual(skills["context-continuity"], "*")
        result = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_missing_context_continuity_catalog_entry_is_rejected(self) -> None:
        skills = json.loads(self.original_skills_json)
        skills.pop("context-continuity")
        self.skills_json_path.write_text(
            json.dumps(skills, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "packaged skill 'context-continuity' not found in skills.json",
            result.stdout + result.stderr,
        )


if __name__ == "__main__":
    unittest.main()
