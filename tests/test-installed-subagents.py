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


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "tests" / "validate-installed-subagents.py"


class InstalledSubagentValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.installed = Path(self.tempdir.name) / "agents"
        shutil.copytree(ROOT / "subagents", self.installed)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def run_validator(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(VALIDATOR),
                "--installed-agents-dir",
                str(self.installed),
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


if __name__ == "__main__":
    unittest.main()
