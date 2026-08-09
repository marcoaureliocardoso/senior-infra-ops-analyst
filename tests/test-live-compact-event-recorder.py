#!/usr/bin/env python3
"""Safety tests for the structural-only live compact event recorder."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RECORDER = ROOT / "tests" / "live-compact-event-recorder.py"


class LiveCompactEventRecorderTests(unittest.TestCase):
    def run_recorder(self, raw: bytes, destination: Path) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            [sys.executable, str(RECORDER), str(destination)],
            input=raw,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_records_only_structural_fields(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "events.jsonl"
            raw = json.dumps({
                "session_id": "session-secret",
                "hook_event_name": "PreCompact",
                "trigger": "auto",
                "custom_instructions": "do not persist this prompt",
                "transcript_path": "/secret/transcript",
            }).encode()
            result = self.run_recorder(raw, destination)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout, b"")
            self.assertEqual(result.stderr, b"")
            self.assertEqual(
                json.loads(destination.read_text(encoding="utf-8")),
                {"kind": "compact", "phase": "PreCompact", "trigger": "auto"},
            )
            evidence = destination.read_text(encoding="utf-8")
            self.assertNotIn("secret", evidence)
            self.assertNotIn("prompt", evidence)
            self.assertNotIn("transcript", evidence)

    def test_invalid_or_oversized_input_never_blocks_or_writes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "events.jsonl"
            for raw in (
                b'{"hook_event_name":"PreCompact","hook_event_name":"PostCompact","trigger":"auto"}',
                b'{"hook_event_name":"PreCompact","trigger":"unknown"}',
                b"x" * (64 * 1024 + 1),
            ):
                with self.subTest(size=len(raw)):
                    result = self.run_recorder(raw, destination)
                    self.assertEqual(result.returncode, 0)
                    self.assertEqual(result.stdout, b"")
                    self.assertEqual(result.stderr, b"")
            self.assertFalse(destination.exists())


if __name__ == "__main__":
    unittest.main()
