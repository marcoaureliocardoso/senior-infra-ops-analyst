#!/usr/bin/env python3
"""Mutation tests for required architecture decision records."""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ArchitectureDocumentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tempdir = tempfile.TemporaryDirectory()
        cls.sandbox = Path(cls.tempdir.name) / "package"
        shutil.copytree(
            ROOT,
            cls.sandbox,
            ignore=shutil.ignore_patterns(".git", ".worktrees", "__pycache__"),
        )
        cls.index_path = cls.sandbox / "docs" / "architecture" / "README.md"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tempdir.cleanup()

    def setUp(self) -> None:
        if not self.index_path.exists():
            self.fail("architecture fixture missing from package")
        self.original_index = self.index_path.read_text(encoding="utf-8")

    def tearDown(self) -> None:
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.index_path.write_text(self.original_index, encoding="utf-8")
        source_dir = ROOT / "docs" / "architecture"
        for source in source_dir.glob("ADR-*.md"):
            target = self.index_path.parent / source.name
            if not target.exists():
                shutil.copy2(source, target)

    def run_validator(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "tests/validate-content.py"],
            cwd=self.sandbox,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_architecture_docs_are_accepted(self) -> None:
        result = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_missing_architecture_index_is_rejected(self) -> None:
        self.index_path.unlink()
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing architecture decision index", result.stdout)

    def test_missing_index_entry_is_rejected(self) -> None:
        text = self.original_index.replace(
            "ADR-002-subagent-skill-preload.md", "ADR-002-omitted.md", 1
        )
        self.index_path.write_text(text, encoding="utf-8")
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("architecture index missing ADR", result.stdout)

    def test_missing_adr_file_is_rejected(self) -> None:
        (self.index_path.parent / "ADR-003-subagent-runtime-controls.md").unlink()
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing architecture decision record", result.stdout)


if __name__ == "__main__":
    unittest.main()
