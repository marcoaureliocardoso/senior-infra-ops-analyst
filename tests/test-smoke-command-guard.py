#!/usr/bin/env python3
"""Behavior tests for the test-only live-smoke command guard."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / "tests" / "smoke-command-guard.py"


class SmokeCommandGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.work = Path(self.tempdir.name)
        self.log = self.work / "hook-events.jsonl"

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def run_guard(self, event: dict[str, object]) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["P0_03_HOOK_LOG"] = str(self.log)
        return subprocess.run(
            [sys.executable, str(GUARD)],
            input=json.dumps(event),
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )

    def test_allows_exact_diagnostic_command(self) -> None:
        result = self.run_guard(
            {
                "hook_event_name": "PreToolUse",
                "agent_type": "diagnostic-operator",
                "tool_name": "Bash",
                "tool_input": {"command": "printf 'p0-03-smoke\\n'"},
            }
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        self.assertEqual(
            output["hookSpecificOutput"]["permissionDecision"], "allow"
        )

    def test_denies_any_other_command(self) -> None:
        result = self.run_guard(
            {
                "hook_event_name": "PreToolUse",
                "agent_type": "diagnostic-operator",
                "tool_name": "Bash",
                "tool_input": {"command": "env"},
            }
        )
        output = json.loads(result.stdout)
        self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_denies_background_execution(self) -> None:
        result = self.run_guard(
            {
                "hook_event_name": "PreToolUse",
                "agent_type": "turn-cutoff-probe",
                "tool_name": "Bash",
                "tool_input": {
                    "command": "printf 'turn-cutoff\\n'",
                    "run_in_background": True,
                },
            }
        )
        output = json.loads(result.stdout)
        self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_lifecycle_log_is_sanitized_and_counts_assistant_turns(self) -> None:
        transcript = self.work / "agent.jsonl"
        transcript.write_text(
            "\n".join(
                [
                    '{"type":"assistant","message":{"content":[]}}',
                    '{"type":"user","message":{"content":[]}}',
                    '{"type":"assistant","message":{"content":[]}}',
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        event = {
            "hook_event_name": "SubagentStop",
            "agent_type": "turn-cutoff-probe",
            "agent_transcript_path": str(transcript),
            "ANTHROPIC_AUTH_TOKEN": "must-not-be-logged",
        }
        result = self.run_guard(event)
        self.assertEqual(result.returncode, 0, result.stderr)
        logged = json.loads(self.log.read_text(encoding="utf-8"))
        self.assertEqual(logged["assistant_turns"], 2)
        self.assertNotIn("agent_transcript_path", logged)
        self.assertNotIn("must-not-be-logged", self.log.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
