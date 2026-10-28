#!/usr/bin/env python3
"""Behavior tests for staged P0-04B installed-policy safety."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.nori_package import build_staging  # noqa: E402
from tests.browser_operation_install_policy import installed_browser_errors  # noqa: E402


class BrowserOperationInstallPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        base = Path(self.temporary.name)
        staging = base / "staging"
        self.install = base / "installed"
        build_staging(ROOT, staging)
        self.install.mkdir()
        shutil.copy2(staging / "AGENTS.md", self.install / "CLAUDE.md")
        shutil.copytree(staging / "skills", self.install / "skills")
        shutil.copytree(staging / "references", self.install / "references")
        agents = self.install / "agents"
        agents.mkdir()
        for component in (staging / "subagents").iterdir():
            if component.is_dir():
                shutil.copy2(component / "SUBAGENT.md", agents / f"{component.name}.md")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_staged_install_is_complete_and_side_effect_free(self) -> None:
        self.assertEqual(installed_browser_errors(self.install), [])

    def test_missing_artifact_and_generic_subagent_grant_are_rejected(self) -> None:
        (self.install / "skills/browser-operations/scripts/browser-hook.mjs").unlink()
        agent = self.install / "agents/diagnostic-operator.md"
        text = agent.read_text(encoding="utf-8")
        agent.write_text(text.replace("tools:", "tools:\n  - mcp__unknown__*", 1), encoding="utf-8")
        errors = installed_browser_errors(self.install)
        self.assertTrue(any("artifact missing" in error for error in errors))
        self.assertTrue(any("generic MCP grant" in error for error in errors))

    def test_configurator_preserves_operator_settings_on_installed_tree(self) -> None:
        project = Path(self.temporary.name) / "project"
        claude = project / ".claude"
        claude.mkdir(parents=True)
        settings = claude / "settings.local.json"
        original = {"model": "operator", "mcpServers": {"keep": {"command": "keep"}}}
        settings.write_text(json.dumps(original) + "\n", encoding="utf-8")
        cli = self.install / "skills/browser-operations/scripts/configure-browser-operations.mjs"
        check = subprocess.run(
            ["node", str(cli), "--check", "--root", str(project)],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(check.returncode, 2, check.stdout + check.stderr)
        self.assertEqual(json.loads(check.stdout)["changed"], False)
        self.assertEqual(json.loads(settings.read_text(encoding="utf-8")), original)
        apply = subprocess.run(
            ["node", str(cli), "--apply", "--root", str(project)],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(apply.returncode, 2, apply.stdout + apply.stderr)
        remove = subprocess.run(
            ["node", str(cli), "--remove-owned", "--root", str(project)],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(remove.returncode, 0, remove.stdout + remove.stderr)
        self.assertEqual(json.loads(settings.read_text(encoding="utf-8")), original)


if __name__ == "__main__":
    unittest.main()
