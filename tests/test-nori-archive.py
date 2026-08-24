#!/usr/bin/env python3
"""Behavior tests for fresh, verified Nori package archives."""
from __future__ import annotations

import json
import shutil
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
        self.source = self.temp_root / "source"
        shutil.copytree(
            ROOT,
            self.source,
            ignore=shutil.ignore_patterns(
                ".git", ".worktrees", ".tmp", "__pycache__"
            ),
        )
        self.staging = self.temp_root / "staging"
        self.output = self.temp_root / "package.zip"
        build_staging(self.source, self.staging)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def run_archiver(self, *extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(ARCHIVER),
                "--source",
                str(self.source),
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
            self.assertEqual(
                len(
                    [
                        name for name in archive.namelist()
                        if name.startswith("subagents/")
                        and name.endswith("/nori.json")
                    ]
                ),
                12,
            )
            self.assertEqual(
                len(
                    [
                        name for name in archive.namelist()
                        if name.startswith("subagents/")
                        and name.endswith("/SUBAGENT.md")
                    ]
                ),
                12,
            )
            self.assertEqual(
                [
                    name for name in archive.namelist()
                    if name.startswith("subagents/") and name.count("/") == 1
                ],
                [],
            )
        self.assertEqual(len(expected), 214)

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

    def test_output_inside_source_is_rejected_without_changing_source(self) -> None:
        manifest = self.source / "nori.json"
        before = manifest.read_bytes()
        self.output = manifest
        result = self.run_archiver()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("archive output must be outside source", result.stderr)
        self.assertEqual(manifest.read_bytes(), before)

    def test_output_symlink_is_rejected_without_changing_target(self) -> None:
        target = self.temp_root / "operator.zip"
        target.write_bytes(b"operator archive")
        try:
            self.output.symlink_to(target)
        except OSError:
            self.skipTest("file symlink creation is unavailable")
        result = self.run_archiver()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("archive output is a symlink or reparse point", result.stderr)
        self.assertTrue(self.output.is_symlink())
        self.assertEqual(target.read_bytes(), b"operator archive")

    def test_linked_output_ancestor_is_rejected_without_changing_victim(self) -> None:
        target_dir = self.temp_root / "operator-dir"
        target_dir.mkdir()
        victim = target_dir / "package.zip"
        victim.write_bytes(b"operator archive")
        linked_parent = self.temp_root / "linked-output"
        try:
            linked_parent.symlink_to(target_dir, target_is_directory=True)
        except OSError:
            self.skipTest("directory symlink creation is unavailable")
        self.output = linked_parent / "package.zip"
        result = self.run_archiver()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("archive output ancestor is a symlink or reparse point", result.stderr)
        self.assertEqual(victim.read_bytes(), b"operator archive")


if __name__ == "__main__":
    unittest.main()
