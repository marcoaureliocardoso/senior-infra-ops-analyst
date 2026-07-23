#!/usr/bin/env python3
"""Regression tests for strict subagent frontmatter validation."""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AGENT_REL = Path("subagents/diagnostic-operator.md")


class SubagentFrontmatterValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tempdir = tempfile.TemporaryDirectory()
        cls.sandbox = Path(cls.tempdir.name) / "package"
        shutil.copytree(
            ROOT,
            cls.sandbox,
            ignore=shutil.ignore_patterns(".git", ".worktrees", "__pycache__"),
        )
        cls.agent_path = cls.sandbox / AGENT_REL
        cls.original_agent = cls.agent_path.read_text(encoding="utf-8")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tempdir.cleanup()

    def tearDown(self) -> None:
        self.agent_path.write_text(self.original_agent, encoding="utf-8")

    def run_validator(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "tests/validate-content.py"],
            cwd=self.sandbox,
            capture_output=True,
            text=True,
            check=False,
        )

    def assert_rejected(self, content: str, expected_message: str) -> None:
        self.agent_path.write_text(content, encoding="utf-8")
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(expected_message, result.stdout + result.stderr)

    def test_valid_frontmatter_is_accepted(self) -> None:
        result = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_trailing_malformed_skill_is_rejected(self) -> None:
        content = self.original_agent.replace(
            "  - infrastructure-troubleshooting\n---",
            "  - infrastructure-troubleshooting\n  - INVALID_SKILL\n---",
            1,
        )
        self.assert_rejected(content, "malformed skills preload")

    def test_quoted_unknown_skill_is_rejected(self) -> None:
        content = self.original_agent.replace(
            "  - infrastructure-troubleshooting\n---",
            '  - infrastructure-troubleshooting\n  - "unknown-skill"\n---',
            1,
        )
        self.assert_rejected(content, "malformed skills preload")

    def test_duplicate_skill_is_rejected(self) -> None:
        content = self.original_agent.replace(
            "  - infrastructure-troubleshooting\n---",
            "  - infrastructure-troubleshooting\n  - infrastructure-troubleshooting\n---",
            1,
        )
        self.assert_rejected(content, "duplicate preloaded skills")

    def test_empty_skill_list_is_rejected(self) -> None:
        content = self.original_agent.replace(
            "skills:\n"
            "  - command-driven-operations\n"
            "  - infrastructure-troubleshooting\n",
            "skills:\n",
            1,
        )
        self.assert_rejected(content, "malformed or empty skills preload")

    def test_unterminated_frontmatter_is_rejected(self) -> None:
        content = self.original_agent.replace(
            "---\n\n# Diagnostic Operator",
            "\n# Diagnostic Operator",
            1,
        )
        self.assert_rejected(content, "missing closing frontmatter delimiter")


if __name__ == "__main__":
    unittest.main()
