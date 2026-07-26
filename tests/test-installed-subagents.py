#!/usr/bin/env python3
"""Regression tests for semantic validation of Nori-installed subagents."""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from command_guard_install_policy import CANONICAL_HOOK_BLOCK, EXECUTOR_AGENTS


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "tests" / "validate-installed-subagents.py"


class InstalledSubagentValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.installed = Path(self.tempdir.name) / "agents"
        self.skills = Path(self.tempdir.name) / "skills"
        shutil.copytree(ROOT / "subagents", self.installed)
        shutil.copytree(ROOT / "skills", self.skills)
        installed_skills = self.skills.as_posix()
        for agent_id in EXECUTOR_AGENTS:
            path = self.installed / f"{agent_id}.md"
            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    "{{skills_dir}}", installed_skills
                ),
                encoding="utf-8",
            )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def run_validator(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(VALIDATOR),
                "--installed-agents-dir",
                str(self.installed),
                "--installed-skills-dir",
                str(self.skills),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_identical_installed_agents_pass(self) -> None:
        result = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_missing_installed_agent_fails(self) -> None:
        (self.installed / "change-manager.md").unlink()
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing installed subagent", result.stdout + result.stderr)

    def test_broadened_installed_tools_fail(self) -> None:
        path = self.installed / "change-manager.md"
        text = path.read_text(encoding="utf-8").replace(
            "tools: Read, Grep, Glob, WebFetch, WebSearch, Skill",
            "tools: Read, Grep, Glob, Bash, WebFetch, WebSearch, Skill",
            1,
        )
        path.write_text(text, encoding="utf-8")
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("installed tools differ", result.stdout + result.stderr)

    def test_changed_installed_skills_fail(self) -> None:
        path = self.installed / "diagnostic-operator.md"
        text = path.read_text(encoding="utf-8").replace(
            "  - infrastructure-troubleshooting\n",
            "  - change-management\n",
            1,
        )
        path.write_text(text, encoding="utf-8")
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("installed skills differ", result.stdout + result.stderr)

    def test_missing_installed_runtime_section_fails(self) -> None:
        path = self.installed / "diagnostic-operator.md"
        text = path.read_text(encoding="utf-8")
        text = re.sub(
            r"^## Runtime controls\n.*?(?=^## )",
            "",
            text,
            count=1,
            flags=re.MULTILINE | re.DOTALL,
        )
        path.write_text(text, encoding="utf-8")
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "installed runtime controls differ", result.stdout + result.stderr
        )

    def test_missing_installed_runtime_precedence_fails(self) -> None:
        path = self.installed / "diagnostic-operator.md"
        text = path.read_text(encoding="utf-8")
        text = re.sub(
            r"^## Runtime control precedence\n.*\Z",
            "",
            text,
            count=1,
            flags=re.MULTILINE | re.DOTALL,
        )
        path.write_text(text, encoding="utf-8")
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "installed runtime precedence differs",
            result.stdout + result.stderr,
        )

    def test_missing_installed_launcher_fails(self) -> None:
        launcher = (
            self.skills
            / "command-driven-operations"
            / "scripts"
            / "command-guard-launcher.sh"
        )
        if launcher.exists():
            launcher.unlink()
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("installed launcher missing", result.stdout + result.stderr)

    def test_unresolved_installed_hook_placeholder_fails(self) -> None:
        path = self.installed / "diagnostic-operator.md"
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                self.skills.as_posix(), "{{skills_dir}}", 1
            ),
            encoding="utf-8",
        )
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("installed hook differs", result.stdout + result.stderr)

    def test_changed_installed_hook_matcher_fails(self) -> None:
        path = self.installed / "diagnostic-operator.md"
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "matcher: Bash", "matcher: *", 1
            ),
            encoding="utf-8",
        )
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("installed hook differs", result.stdout + result.stderr)

    def test_changed_installed_guard_module_fails(self) -> None:
        path = (
            self.skills / "command-driven-operations" / "scripts" /
            "command-guard" / "policy.mjs"
        )
        path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("installed command guard artifact differs", result.stdout + result.stderr)

    def test_analytical_agent_cannot_gain_installed_hook(self) -> None:
        path = self.installed / "change-manager.md"
        text = path.read_text(encoding="utf-8")
        end = text.find("\n---\n", 4)
        resolved = CANONICAL_HOOK_BLOCK.replace(
            "{{skills_dir}}", self.skills.as_posix()
        )
        path.write_text(text[: end + 1] + resolved + text[end + 1 :], encoding="utf-8")
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("analytical agent declares Bash hook", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
