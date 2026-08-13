#!/usr/bin/env python3
"""Behavior tests for source and installed command-guard hook policy."""
from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "tests" / "command_guard_install_policy.py"
EXECUTOR = ROOT / "subagents" / "diagnostic-operator" / "SUBAGENT.md"
ANALYST = ROOT / "subagents" / "change-manager" / "SUBAGENT.md"


def load_policy() -> ModuleType:
    """Load the production policy only after the test can report its absence."""
    if not POLICY_PATH.is_file():
        raise AssertionError("command guard install policy module is missing")
    spec = importlib.util.spec_from_file_location(
        "command_guard_install_policy", POLICY_PATH
    )
    if spec is None or spec.loader is None:
        raise AssertionError("command guard install policy cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CommandGuardInstallPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        if not POLICY_PATH.is_file():
            if self._testMethodName == "test_policy_module_exists":
                return
            self.skipTest("policy module not available for behavior cases")
        self.policy = load_policy()
        self.assertTrue(
            callable(getattr(self.policy, "source_hook_errors", None)),
            "source_hook_errors is missing",
        )
        self.executor_text = EXECUTOR.read_text(encoding="utf-8")
        self.analyst_text = ANALYST.read_text(encoding="utf-8")

    def test_policy_module_exists(self) -> None:
        self.assertTrue(POLICY_PATH.is_file(), "install policy must exist")

    def assert_source_error(
        self, agent_id: str, text: str, expected: str
    ) -> None:
        errors = self.policy.source_hook_errors(agent_id, text)
        self.assertTrue(
            any(expected in error for error in errors),
            f"expected {expected!r} in {errors!r}",
        )

    def test_valid_executor_hook_is_accepted(self) -> None:
        self.assertEqual(
            self.policy.source_hook_errors(
                "diagnostic-operator", self.executor_text
            ),
            [],
        )

    def test_executor_without_hook_is_rejected(self) -> None:
        changed = self.policy.remove_command_guard_hook(self.executor_text)
        self.assert_source_error(
            "diagnostic-operator", changed, "missing command guard hook"
        )

    def test_analytical_agent_with_bash_hook_is_rejected(self) -> None:
        changed = self.policy.insert_command_guard_hook(self.analyst_text)
        self.assert_source_error(
            "change-manager", changed, "analytical agent declares Bash hook"
        )

    def test_broadened_matcher_is_rejected(self) -> None:
        changed = self.executor_text.replace("matcher: Bash", "matcher: *", 1)
        self.assert_source_error(
            "diagnostic-operator", changed, "matcher must be exactly Bash"
        )

    def test_shell_string_hook_is_rejected(self) -> None:
        changed = self.executor_text.replace(
            'command: "{{skills_dir}}/command-driven-operations/scripts/command-guard-launcher.sh"',
            "command: node command-guard",
            1,
        )
        self.assert_source_error(
            "diagnostic-operator", changed, "canonical exec form"
        )

    def test_hook_timeout_drift_is_rejected(self) -> None:
        changed = self.executor_text.replace("timeout: 7", "timeout: 30", 1)
        self.assert_source_error(
            "diagnostic-operator", changed, "timeout must be 7 seconds"
        )

    def test_duplicate_pretooluse_is_rejected(self) -> None:
        block = self.policy.CANONICAL_HOOK_BLOCK
        changed = self.executor_text.replace(block, block + block, 1)
        self.assert_source_error(
            "diagnostic-operator", changed, "exactly one command guard hook"
        )

    def test_unexpected_hook_argument_is_rejected(self) -> None:
        changed = self.executor_text.replace(
            "            - pre\n          timeout: 7",
            "            - pre\n            - --unsafe\n          timeout: 7",
            1,
        )
        self.assert_source_error(
            "diagnostic-operator", changed, "canonical exec form"
        )

    def test_package_content_validation_rejects_missing_hook(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            sandbox = Path(temporary) / "package"
            shutil.copytree(
                ROOT,
                sandbox,
                ignore=shutil.ignore_patterns(
                    ".git", ".worktrees", ".tmp", "__pycache__"
                ),
            )
            agent = (
                sandbox
                / "subagents"
                / "diagnostic-operator"
                / "SUBAGENT.md"
            )
            agent.write_text(
                self.policy.remove_command_guard_hook(
                    agent.read_text(encoding="utf-8")
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, str(sandbox / "tests" / "validate-content.py")],
                cwd=sandbox,
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing command guard hook", result.stdout)

    def test_initial_validator_entrypoint_fails_closed(self) -> None:
        validator = (
            ROOT
            / "skills"
            / "command-driven-operations"
            / "scripts"
            / "validate-ops-command.mjs"
        )
        result = subprocess.run(
            ["node", str(validator)],
            input="{}",
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertNotIn('"permissionDecision":"allow"', result.stdout)


if __name__ == "__main__":
    unittest.main()
