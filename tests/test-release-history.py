#!/usr/bin/env python3
"""Mutation tests for the README release-history contract."""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RELEASE_HEADING = "## Release history"
RELEASE_LINK = (
    "See [CHANGELOG.md](CHANGELOG.md) for version history and release notes."
)


class ReleaseHistoryTests(unittest.TestCase):
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
        cls.readme = cls.sandbox / "README.md"
        cls.original = cls.readme.read_text(encoding="utf-8")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tempdir.cleanup()

    def tearDown(self) -> None:
        self.readme.write_text(self.original, encoding="utf-8")

    def run_validator(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "tests/validate-content.py"],
            cwd=self.sandbox,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_current_package_accepts_release_history_contract(self) -> None:
        result = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_legacy_version_heading_is_rejected(self) -> None:
        mutated = self.original.replace(
            RELEASE_HEADING,
            "## What changed in v9.9.9\n\n- Regression.\n\n" + RELEASE_HEADING,
            1,
        )
        self.readme.write_text(mutated, encoding="utf-8")
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("README.md duplicates release history", result.stdout)

    def test_missing_release_history_heading_is_rejected(self) -> None:
        self.readme.write_text(
            self.original.replace(RELEASE_HEADING, "## Releases", 1),
            encoding="utf-8",
        )
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("README.md missing release history heading", result.stdout)

    def test_missing_or_incorrect_changelog_link_is_rejected(self) -> None:
        self.readme.write_text(
            self.original.replace(
                RELEASE_LINK,
                "See [release notes](docs/releases.md) for version history.",
                1,
            ),
            encoding="utf-8",
        )
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("README.md missing canonical changelog link", result.stdout)


if __name__ == "__main__":
    unittest.main()
