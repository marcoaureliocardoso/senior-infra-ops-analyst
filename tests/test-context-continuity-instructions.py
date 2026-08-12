#!/usr/bin/env python3
"""Regression tests for the distributed context-continuity contract."""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "## Context continuity and compaction",
    "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE",
    "TaskCreate`/`TaskGet`/`TaskList`/`TaskUpdate",
    "`TodoWrite`",
    "authorization or credential reuse",
    "transcript, prompt, compact summary, or secret",
    "Immediate next action",
)


class ContextContinuityInstructionTests(unittest.TestCase):
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
        cls.agents = cls.sandbox / "AGENTS.md"
        cls.original = cls.agents.read_text(encoding="utf-8")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tempdir.cleanup()

    def tearDown(self) -> None:
        self.agents.write_text(self.original, encoding="utf-8")

    def run_validator(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "tests/validate-content.py"],
            cwd=self.sandbox,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_current_package_accepts_continuity_contract(self) -> None:
        result = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_each_continuity_clause_is_required(self) -> None:
        for clause in REQUIRED:
            with self.subTest(clause=clause):
                self.assertIn(clause, self.original)
                self.agents.write_text(
                    self.original.replace(clause, f"omitted-{len(clause)}", 1),
                    encoding="utf-8",
                )
                result = self.run_validator()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(
                    "missing context continuity clause",
                    result.stdout + result.stderr,
                )
                self.agents.write_text(self.original, encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
