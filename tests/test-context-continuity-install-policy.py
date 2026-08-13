#!/usr/bin/env python3
"""Behavior tests for source compact-hook installation policy."""
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
POLICY_PATH = ROOT / "tests" / "context_continuity_install_policy.py"
AGENTS = tuple(
    path.parent.name
    for path in sorted((ROOT / "subagents").glob("*/SUBAGENT.md"))
)


def load_policy() -> ModuleType:
    if not POLICY_PATH.is_file():
        raise AssertionError("context continuity install policy module is missing")
    spec = importlib.util.spec_from_file_location(
        "context_continuity_install_policy", POLICY_PATH
    )
    if spec is None or spec.loader is None:
        raise AssertionError("context continuity install policy cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ContextContinuityInstallPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        if not POLICY_PATH.is_file():
            if self._testMethodName == "test_policy_module_exists":
                return
            self.skipTest("policy module not available for behavior cases")
        self.policy = load_policy()
        self.executor = (
            ROOT
            / "subagents"
            / "diagnostic-operator"
            / "SUBAGENT.md"
        ).read_text(encoding="utf-8")

    def test_policy_module_exists(self) -> None:
        self.assertTrue(POLICY_PATH.is_file(), "install policy must exist")

    def test_every_source_agent_has_exact_continuity_hooks(self) -> None:
        self.assertEqual(len(AGENTS), 12)
        for agent_id in AGENTS:
            with self.subTest(agent_id=agent_id):
                text = (
                    ROOT / "subagents" / agent_id / "SUBAGENT.md"
                ).read_text(encoding="utf-8")
                self.assertEqual(
                    self.policy.source_continuity_hook_errors(agent_id, text), []
                )

    def assert_mutation_rejected(self, changed: str, reason: str) -> None:
        errors = self.policy.source_continuity_hook_errors(
            "diagnostic-operator", changed
        )
        self.assertTrue(
            any(reason in error for error in errors),
            f"expected {reason!r} in {errors!r}",
        )

    def test_missing_or_duplicate_phase_is_rejected(self) -> None:
        block = self.policy.CANONICAL_CONTINUITY_HOOKS
        post = block[block.index("  PostCompact:") :]
        self.assert_mutation_rejected(
            self.executor.replace(post, "", 1), "continuity hook phase count"
        )
        self.assert_mutation_rejected(
            self.executor.replace(block, block + post, 1),
            "continuity hook phase count",
        )

    def test_path_timeout_and_argument_drift_are_rejected(self) -> None:
        self.assert_mutation_rejected(
            self.executor.replace("compact-hook-launcher.sh", "other.sh", 1),
            "canonical continuity hooks",
        )
        self.assert_mutation_rejected(
            self.executor.replace("timeout: 5", "timeout: 30", 1),
            "canonical continuity hooks",
        )
        self.assert_mutation_rejected(
            self.executor.replace(
                "            - pre\n          timeout: 5",
                "            - invalid\n          timeout: 5",
                1,
            ),
            "canonical continuity hooks",
        )

    def test_matcher_and_async_broadening_are_rejected(self) -> None:
        self.assert_mutation_rejected(
            self.executor.replace(
                "  PreCompact:\n    - hooks:",
                "  PreCompact:\n    - matcher: auto\n      hooks:",
                1,
            ),
            "canonical continuity hooks",
        )
        self.assert_mutation_rejected(
            self.executor.replace("          timeout: 5\n", "          timeout: 5\n          async: true\n", 1),
            "canonical continuity hooks",
        )

    def test_unknown_agent_fails_closed(self) -> None:
        self.assertIn(
            "unknown subagent continuity policy",
            " ".join(
                self.policy.source_continuity_hook_errors(
                    "unknown-agent", self.executor
                )
            ),
        )

    def test_package_validation_rejects_missing_continuity_phase(self) -> None:
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
            text = agent.read_text(encoding="utf-8")
            post = self.policy.CANONICAL_CONTINUITY_HOOKS[
                self.policy.CANONICAL_CONTINUITY_HOOKS.index("  PostCompact:") :
            ]
            agent.write_text(text.replace(post, "", 1), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(sandbox / "tests" / "validate-content.py")],
                cwd=sandbox,
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("continuity hook phase count", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
