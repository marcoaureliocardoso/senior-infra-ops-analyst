#!/usr/bin/env python3
"""Behavior tests for fresh, verified Nori package archives."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARCHIVER = ROOT / "scripts" / "build_nori_archive.py"
sys.path.insert(0, str(ROOT))

from scripts.nori_package import build_staging  # noqa: E402


class NoriArchiveTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.temp_root = Path(self.tempdir.name)
        self.staging = self.temp_root / "staging"
        self.output = self.temp_root / "package.zip"
        build_staging(ROOT, self.staging)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def run_archiver(self, *extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(ARCHIVER),
                "--source",
                str(ROOT),
                "--staging",
                str(self.staging),
                "--output",
                str(self.output),
                *extra,
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_existing_archive_is_rebuilt_without_stale_entries(self) -> None:
        with zipfile.ZipFile(self.output, "w") as archive:
            archive.writestr("operator-stale.txt", "must disappear")
        result = self.run_archiver("--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        inventory = json.loads(result.stdout)
        expected = [entry["path"] for entry in inventory]
        with zipfile.ZipFile(self.output) as archive:
            self.assertEqual(archive.namelist(), expected)
            self.assertNotIn("operator-stale.txt", archive.namelist())
        self.assertEqual(len(expected), 199)

    def test_drifted_staging_is_rejected_without_replacing_archive(self) -> None:
        self.output.write_bytes(b"operator archive")
        (self.staging / "AGENTS.md").write_text("drift\n", encoding="utf-8")
        result = self.run_archiver()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("content differs from source", result.stderr)
        self.assertEqual(self.output.read_bytes(), b"operator archive")

    def test_output_inside_staging_is_rejected(self) -> None:
        self.output = self.staging / "package.zip"
        result = self.run_archiver()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("archive output must be outside staging", result.stderr)
        self.assertFalse(self.output.exists())

    def test_linked_staging_argument_is_rejected(self) -> None:
        linked = self.temp_root / "linked-staging"
        try:
            linked.symlink_to(self.staging, target_is_directory=True)
        except OSError:
            self.skipTest("directory symlink creation is unavailable")
        self.staging = linked
        result = self.run_archiver()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("destination is a symlink or reparse point", result.stderr)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
