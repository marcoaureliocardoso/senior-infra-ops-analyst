#!/usr/bin/env python3
"""Mutation tests for Nori manifest schema validation."""
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

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tempdir.cleanup()

    def tearDown(self) -> None:
        self.manifest_path.write_text(self.original_manifest, encoding="utf-8")
        self.nori_version_path.write_text(
            self.original_nori_version, encoding="utf-8"
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

    def test_skillset_manifest_type_is_accepted(self) -> None:
        manifest = json.loads(self.original_manifest)
        manifest["type"] = "skillset"
        self.write_manifest(manifest)
        result = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_missing_manifest_type_is_rejected(self) -> None:
        manifest = json.loads(self.original_manifest)
        manifest.pop("type", None)
        self.write_manifest(manifest)
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("type must be 'skillset'", result.stdout + result.stderr)

    def test_non_skillset_manifest_type_is_rejected(self) -> None:
        manifest = json.loads(self.original_manifest)
        manifest["type"] = "skill"
        self.write_manifest(manifest)
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("type must be 'skillset'", result.stdout + result.stderr)

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


if __name__ == "__main__":
    unittest.main()
