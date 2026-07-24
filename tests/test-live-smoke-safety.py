#!/usr/bin/env python3
"""Static safety contract for the opt-in live runtime smoke."""
from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / "tests" / "live-subagent-runtime-smoke.sh").read_text(
    encoding="utf-8"
)


class LiveSmokeSafetyTests(unittest.TestCase):
    def test_permission_bypass_is_not_used(self) -> None:
        self.assertNotIn("bypassPermissions", SCRIPT)

    def test_os_level_sandbox_is_required(self) -> None:
        self.assertIn("BWRAP_BIN", SCRIPT)
        self.assertIn("--ro-bind /usr /usr", SCRIPT)
        self.assertIn('--bind "$WORK" /work', SCRIPT)
        self.assertNotIn("--ro-bind / /", SCRIPT)

    def test_probe_process_uses_minimal_environment(self) -> None:
        self.assertIn("env -i", SCRIPT)

    def test_exact_command_guard_is_installed(self) -> None:
        self.assertIn('"PreToolUse"', SCRIPT)
        self.assertIn("smoke-command-guard.py", SCRIPT)

    def test_cutoff_uses_delegated_subagent(self) -> None:
        self.assertIn("Agent(turn-cutoff-probe)", SCRIPT)
        self.assertIn('"SubagentStart"', SCRIPT)
        self.assertIn('"SubagentStop"', SCRIPT)


if __name__ == "__main__":
    unittest.main()
