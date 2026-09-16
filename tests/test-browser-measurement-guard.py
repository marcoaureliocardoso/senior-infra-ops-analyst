#!/usr/bin/env python3
"""Tests for the disposable one-call Agent measurement guard."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / "tests" / "browser-measurement-guard.py"
SESSION = "p004b-session-001"


def event(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "session_id": SESSION,
        "tool_use_id": "agent-call-001",
        "hook_event_name": "PreToolUse",
        "tool_name": "Agent",
        "permission_mode": "default",
        "tool_input": {
            "description": "P004B_SUBAGENT_ACK",
            "prompt": "P004B_SUBAGENT_ACK",
            "subagent_type": "diagnostic-operator",
        },
    }
    value.update(overrides)
    return value


class BrowserMeasurementGuardTests(unittest.TestCase):
    def invoke(self, claim: Path, value: object) -> tuple[str, Path]:
        result = subprocess.run(
            [sys.executable, str(GUARD), str(claim), SESSION],
            input=json.dumps(value), text=True, capture_output=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"], claim

    @unittest.skipIf(os.name == "nt", "POSIX O_NOFOLLOW claim semantics required")
    def test_exact_first_call_is_allowed_and_second_is_denied(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            claim = Path(directory) / "agent.claim"
            self.assertEqual(self.invoke(claim, event())[0], "allow")
            self.assertEqual(self.invoke(claim, event())[0], "deny")
            self.assertEqual(claim.read_text(encoding="utf-8"), "claimed\n")
            self.assertEqual(claim.stat().st_mode & 0o777, 0o600)

    def test_wrong_session_role_or_payload_is_denied_without_claim(self) -> None:
        mutations = (
            event(session_id="different"),
            event(tool_name="Bash"),
            event(tool_input={"subagent_type": "diagnostic-operator"}),
            event(tool_input={
                "description": "P004B_SUBAGENT_ACK", "prompt": "other",
                "subagent_type": "diagnostic-operator",
            }),
        )
        with tempfile.TemporaryDirectory() as directory:
            for index, value in enumerate(mutations):
                claim = Path(directory) / f"claim-{index}"
                self.assertEqual(self.invoke(claim, value)[0], "deny")
                self.assertFalse(claim.exists())

    @unittest.skipIf(os.name == "nt", "POSIX O_EXCL concurrency semantics required")
    def test_concurrent_exact_calls_allow_only_one(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            claim = Path(directory) / "agent.claim"
            with ThreadPoolExecutor(max_workers=8) as pool:
                decisions = list(pool.map(lambda _: self.invoke(claim, event())[0], range(8)))
            self.assertEqual(decisions.count("allow"), 1)
            self.assertEqual(decisions.count("deny"), 7)


if __name__ == "__main__":
    unittest.main()
