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
CHANGE_MANAGER_REL = Path("subagents/change-manager.md")
RUNTIME_PRECEDENCE_HEADING = "## Runtime control precedence"


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
        cls.change_manager_path = cls.sandbox / CHANGE_MANAGER_REL
        cls.original_change_manager = cls.change_manager_path.read_text(
            encoding="utf-8"
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tempdir.cleanup()

    def tearDown(self) -> None:
        self.agent_path.write_text(self.original_agent, encoding="utf-8")
        self.change_manager_path.write_text(
            self.original_change_manager, encoding="utf-8"
        )

    def run_validator(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "tests/validate-content.py"],
            cwd=self.sandbox,
            capture_output=True,
            text=True,
            check=False,
        )

    def assert_rejected(self, content: str, expected_message: str) -> None:
        self.assert_agent_rejected(AGENT_REL, content, expected_message)

    def assert_agent_rejected(
        self, relative_path: Path, content: str, expected_message: str
    ) -> None:
        (self.sandbox / relative_path).write_text(content, encoding="utf-8")
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

    def test_missing_max_turns_is_rejected(self) -> None:
        content = self.original_agent.replace("maxTurns: 16\n", "", 1)
        self.assert_rejected(content, "missing maxTurns")

    def test_zero_max_turns_is_rejected(self) -> None:
        content = self.original_agent.replace("maxTurns: 16", "maxTurns: 0", 1)
        self.assert_rejected(content, "invalid maxTurns")

    def test_non_numeric_max_turns_is_rejected(self) -> None:
        content = self.original_agent.replace(
            "maxTurns: 16", "maxTurns: sixteen", 1
        )
        self.assert_rejected(content, "invalid maxTurns")

    def test_duplicate_max_turns_is_rejected(self) -> None:
        content = self.original_agent.replace(
            "maxTurns: 16", "maxTurns: 16\nmaxTurns: 16", 1
        )
        self.assert_rejected(content, "duplicate maxTurns")

    def test_out_of_role_range_is_rejected(self) -> None:
        content = self.original_agent.replace("maxTurns: 16", "maxTurns: 20", 1)
        self.assert_rejected(content, "maxTurns outside role range")

    def test_in_range_max_turns_drift_is_rejected(self) -> None:
        content = self.original_agent.replace("maxTurns: 16", "maxTurns: 15", 1)
        self.assert_rejected(content, "maxTurns differs from role policy")

    def test_unknown_tool_is_rejected(self) -> None:
        content = self.original_agent.replace(
            "tools: Read, Grep, Glob, Bash, WebFetch, WebSearch, Skill",
            "tools: Read, Grep, Glob, Bash, WebFetch, WebSearch, Skill, FutureTool",
            1,
        )
        self.assert_rejected(content, "unknown tools")

    def test_duplicate_tool_is_rejected(self) -> None:
        content = self.original_agent.replace(
            "tools: Read, Grep, Glob, Bash, WebFetch, WebSearch, Skill",
            "tools: Read, Grep, Glob, Bash, Bash, WebFetch, WebSearch, Skill",
            1,
        )
        self.assert_rejected(content, "duplicate tools")

    def test_role_tool_drift_is_rejected(self) -> None:
        content = self.original_agent.replace(", WebSearch", "", 1)
        self.assert_rejected(content, "tools differ from role policy")

    def test_missing_critical_denial_is_rejected(self) -> None:
        content = self.original_agent.replace(
            "disallowedTools: Write, Edit", "disallowedTools: Write", 1
        )
        self.assert_rejected(content, "disallowedTools differ from role policy")

    def test_missing_tool_rationale_is_rejected(self) -> None:
        content = self.original_agent.replace(
            "- `Bash`:", "- Shell evidence collection:", 1
        )
        self.assert_rejected(content, "missing tool rationale for Bash")

    def test_missing_handoff_field_is_rejected(self) -> None:
        content = self.original_agent.replace(
            "- Next safest action", "- Suggested continuation", 1
        )
        self.assert_rejected(content, "missing handoff field: Next safest action")

    def test_runtime_precedence_is_required_after_normal_output(self) -> None:
        heading = self.original_agent.rfind(RUNTIME_PRECEDENCE_HEADING)
        normal_output = self.original_agent.rfind("\n## Output\n")
        self.assertGreater(heading, normal_output)
        self.assertTrue(
            self.original_agent.rstrip().endswith(
                "`maxTurns` remains the hard backstop."
            )
        )

    def test_missing_runtime_precedence_is_rejected(self) -> None:
        content = self.original_agent.replace(
            RUNTIME_PRECEDENCE_HEADING,
            "## Normal output continuation",
            1,
        )
        self.assert_rejected(content, "lacks final runtime precedence")

    def test_analytical_role_cannot_gain_bash(self) -> None:
        content = self.original_change_manager.replace(
            "tools: Read, Grep, Glob, WebFetch, WebSearch, Skill",
            "tools: Read, Grep, Glob, Bash, WebFetch, WebSearch, Skill",
            1,
        )
        self.assert_agent_rejected(
            CHANGE_MANAGER_REL,
            content,
            "tools differ from role policy",
        )


if __name__ == "__main__":
    unittest.main()
