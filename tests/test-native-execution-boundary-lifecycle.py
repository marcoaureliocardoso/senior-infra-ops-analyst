#!/usr/bin/env python3
"""Behavior contract for the content-free P0-05 SubagentStart recorder."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RECORDER = ROOT / "tests" / "native-execution-boundary-lifecycle.py"
NONCE = "0123456789abcdef0123456789abcdef"


def run_recorder(payload: str, output: Path, nonce: str = NONCE) -> subprocess.CompletedProcess[str]:
    environment = {
        "PATH": os.environ.get("PATH", ""),
        "P005_LIVE_STAGE_NONCE": nonce,
        "P005_LIFECYCLE_EVENT_PATH": str(output),
    }
    return subprocess.run(
        [sys.executable, str(RECORDER)],
        input=payload,
        text=True,
        capture_output=True,
        env=environment,
        timeout=5,
        check=False,
    )


class NativeExecutionBoundaryLifecycleTests(unittest.TestCase):
    def test_valid_subagent_start_writes_only_fixed_content_free_marker(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / f"lifecycle-executor-fallback-{NONCE}.json"
            payload = json.dumps({
                "session_id": "session-value-must-not-persist",
                "transcript_path": "/secret/transcript-must-not-persist.jsonl",
                "cwd": "/synthetic/project",
                "hook_event_name": "SubagentStart",
                "agent_id": "agent-value-must-not-persist",
                "agent_type": "diagnostic-operator",
            })
            result = run_recorder(payload, output)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")
            self.assertEqual(result.stderr, "")
            self.assertEqual(
                json.loads(output.read_text(encoding="utf-8")),
                {
                    "agentIdPresent": True,
                    "agentTypeMatched": True,
                    "event": "SubagentStart",
                    "probeNonce": NONCE,
                    "schemaVersion": 1,
                },
            )
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            serialized = output.read_text(encoding="utf-8").lower()
            for forbidden in ("session-value", "agent-value", "transcript", "synthetic/project"):
                self.assertNotIn(forbidden, serialized)

    def test_invalid_duplicate_or_unbounded_input_is_silent_and_writes_nothing(self) -> None:
        payloads = (
            "{",
            '{"hook_event_name":"SubagentStart","agent_type":"diagnostic-operator"}',
            '{"hook_event_name":"SubagentStart","agent_type":"diagnostic-operator",'
            '"agent_type":"diagnostic-operator","agent_id":"agent-1","session_id":"session-1"}',
            json.dumps({
                "hook_event_name": "SubagentStart",
                "agent_type": "other-operator",
                "agent_id": "agent-1",
                "session_id": "session-1",
            }),
            "x" * (64 * 1024 + 1),
        )
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / f"lifecycle-executor-fallback-{NONCE}.json"
            for payload in payloads:
                result = run_recorder(payload, output)
                self.assertEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")
                self.assertEqual(result.stderr, "")
                self.assertFalse(output.exists())

    def test_invalid_nonce_or_preexisting_output_fails_closed_without_replacement(self) -> None:
        payload = json.dumps({
            "hook_event_name": "SubagentStart",
            "agent_type": "diagnostic-operator",
            "agent_id": "agent-1",
            "session_id": "session-1",
        })
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            invalid = root / "lifecycle-executor-fallback-invalid.json"
            result = run_recorder(payload, invalid, nonce="invalid")
            self.assertEqual(result.returncode, 0)
            self.assertFalse(invalid.exists())

            existing = root / f"lifecycle-executor-fallback-{NONCE}.json"
            existing.write_text("operator-content", encoding="utf-8")
            result = run_recorder(payload, existing)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(existing.read_text(encoding="utf-8"), "operator-content")


if __name__ == "__main__":
    unittest.main()
