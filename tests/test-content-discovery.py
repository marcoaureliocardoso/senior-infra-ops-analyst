#!/usr/bin/env python3
"""Mutation tests for filesystem-backed content discovery."""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ContentDiscoveryTests(unittest.TestCase):
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

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def run_validator(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "tests/validate-content.py"],
            cwd=self.sandbox,
            capture_output=True,
            text=True,
            check=False,
        )

    def replace_once(self, relative: str, old: str, new: str) -> None:
        path = self.sandbox / relative
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text)
        path.write_text(text.replace(old, new, 1), encoding="utf-8")

    def test_canonical_content_is_accepted_without_manifest_inventories(self) -> None:
        result = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_unknown_preloaded_skill_is_rejected_from_filesystem_catalog(self) -> None:
        self.replace_once(
            "subagents/diagnostic-operator/SUBAGENT.md",
            "  - command-driven-operations",
            "  - absent-skill",
        )
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("preloads skills absent from packaged skills", result.stdout)

    def test_reference_file_not_routed_by_agents_is_rejected(self) -> None:
        (self.sandbox / "references" / "unrouted-reference.md").write_text(
            "# Unrouted Reference\n", encoding="utf-8"
        )
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "AGENTS.md missing required reference: "
            "references/unrouted-reference.md",
            result.stdout,
        )

    def test_slash_command_unknown_subagent_is_rejected(self) -> None:
        self.replace_once(
            "slashcommands/ops-diagnose.md",
            "Task(subagent_type:diagnostic-operator)",
            "Task(subagent_type:absent-operator)",
        )
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            'references unknown subagent "absent-operator"', result.stdout
        )

    def test_deleted_subagent_is_rejected_by_command_routing(self) -> None:
        (
            self.sandbox
            / "subagents"
            / "diagnostic-operator"
            / "SUBAGENT.md"
        ).unlink()
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            'references unknown subagent "diagnostic-operator"', result.stdout
        )

    def test_duplicate_subagent_frontmatter_name_is_rejected(self) -> None:
        self.replace_once(
            "subagents/change-manager/SUBAGENT.md",
            "name: change-manager",
            "name: diagnostic-operator",
        )
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("duplicate subagent frontmatter name", result.stdout)

    def test_new_malformed_skill_is_discovered_and_rejected(self) -> None:
        skill_dir = self.sandbox / "skills" / "malformed-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "# Malformed skill\n", encoding="utf-8"
        )
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("skill lacks <required>: malformed-skill", result.stdout)


if __name__ == "__main__":
    unittest.main()
