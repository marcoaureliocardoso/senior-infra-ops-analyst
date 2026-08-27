#!/usr/bin/env python3
"""Behavior tests for the P0-06 content-free deny-all test hook."""
from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "tests" / "prompt-injection-deny-tool.py"
SECRET = "SYNTH_SECRET_P006_NEVER_REPORT"


class PromptInjectionDenyToolTests(unittest.TestCase):
    def setUp(self) -> None:
        if not HOOK.is_file():
            if self._testMethodName == "test_hook_exists":
                return
            self.skipTest("deny-all hook is not implemented yet")
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.audit = self.root / "audit.jsonl"

    def tearDown(self) -> None:
        temporary = getattr(self, "temporary", None)
        if temporary is not None:
            temporary.cleanup()

    def run_hook(self, raw: bytes, *, audit: Path | None = None) -> subprocess.CompletedProcess[bytes]:
        environment = os.environ.copy()
        environment["P006_DENY_AUDIT_PATH"] = str(audit or self.audit)
        return subprocess.run(
            [sys.executable, str(HOOK)],
            input=raw,
            capture_output=True,
            check=False,
            timeout=5,
            env=environment,
        )

    def valid_event(self) -> dict[str, object]:
        return {
            "session_id": "synthetic-session",
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {
                "command": SECRET,
                "description": SECRET,
                "nested": {"credential": SECRET},
            },
        }

    def test_hook_exists(self) -> None:
        self.assertTrue(HOOK.is_file(), "P0-06 deny-all hook is missing")

    def test_valid_event_is_denied_and_audited_without_input(self) -> None:
        result = self.run_hook(json.dumps(self.valid_event()).encode("utf-8"))
        self.assertEqual(result.returncode, 0)
        response = json.loads(result.stdout)
        self.assertEqual(
            response,
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": "P006_DENY_ALL_TEST_HOOK",
                }
            },
        )
        self.assertNotIn(SECRET.encode(), result.stdout + result.stderr)
        lines = self.audit.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 1)
        self.assertEqual(
            json.loads(lines[0]),
            {
                "schemaVersion": 1,
                "hookEventName": "PreToolUse",
                "toolName": "Bash",
                "disposition": "deny",
            },
        )
        self.assertNotIn(SECRET, lines[0])
        self.assertEqual(stat.S_IMODE(self.audit.stat().st_mode), 0o600)

    def test_tool_input_values_do_not_affect_denial_or_bounded_audit(self) -> None:
        expected_stdout: bytes | None = None
        expected_record: str | None = None
        payloads: tuple[object, ...] = (
            None,
            SECRET,
            [SECRET, {"nested": SECRET}],
            {"command": SECRET, "authorization": SECRET},
        )
        for index, payload in enumerate(payloads):
            with self.subTest(payload_type=type(payload).__name__):
                event = self.valid_event()
                event["tool_input"] = payload
                audit = self.root / f"audit-{index}.jsonl"
                result = self.run_hook(json.dumps(event).encode("utf-8"), audit=audit)
                self.assertEqual(result.returncode, 0)
                record = audit.read_text(encoding="utf-8")
                self.assertNotIn(SECRET.encode(), result.stdout + result.stderr)
                self.assertNotIn(SECRET, record)
                if expected_stdout is None:
                    expected_stdout = result.stdout
                    expected_record = record
                else:
                    self.assertEqual(result.stdout, expected_stdout)
                    self.assertEqual(record, expected_record)

    def test_malformed_inputs_fail_closed_without_echo(self) -> None:
        cases = (
            b'{"hook_event_name":"PreToolUse","hook_event_name":"PostToolUse","tool_name":"Bash"}',
            b'"not-an-object"',
            b'{"hook_event_name":"PostToolUse","tool_name":"Bash"}',
            b'{"hook_event_name":"PreToolUse"}',
            b'{"hook_event_name":"PreToolUse","tool_name":""}',
            b"{not-json}",
            b"\xff",
            b"x" * 65_537,
        )
        for raw in cases:
            with self.subTest(size=len(raw)):
                result = self.run_hook(raw)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, b"")
                self.assertNotIn(SECRET.encode(), result.stderr)

    def test_missing_linked_or_relative_audit_target_fails_closed(self) -> None:
        outside = self.root / "outside.jsonl"
        outside.write_text("", encoding="utf-8")
        linked = self.root / "linked.jsonl"
        try:
            linked.symlink_to(outside)
        except OSError as error:
            self.skipTest(f"symlink unavailable: {error}")
        for audit in (linked, Path("relative-audit.jsonl"), self.root / "missing" / "audit.jsonl"):
            with self.subTest(audit=audit.name):
                result = self.run_hook(json.dumps(self.valid_event()).encode(), audit=audit)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, b"")
        self.assertEqual(outside.read_text(encoding="utf-8"), "")


if __name__ == "__main__":
    unittest.main()
