#!/usr/bin/env python3
"""Tests for the disposable, content-free status-line capacity observer."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RECORDER = ROOT / "tests" / "live-context-window-recorder.py"


class LiveContextWindowRecorderTests(unittest.TestCase):
    def run_recorder(self, payload: str) -> tuple[subprocess.CompletedProcess[str], Path, tempfile.TemporaryDirectory[str]]:
        directory = tempfile.TemporaryDirectory()
        destination = Path(directory.name) / "events.jsonl"
        result = subprocess.run(
            [sys.executable, str(RECORDER), str(destination)], input=payload,
            text=True, capture_output=True, check=False,
        )
        return result, destination, directory

    def test_records_only_official_numeric_context_fields(self) -> None:
        result, destination, directory = self.run_recorder(json.dumps({
            "context_window": {"context_window_size": 1_000_000, "used_percentage": 8},
            "model": {"display_name": "SECRET_MODEL_LABEL"},
            "transcript_path": "/SECRET/transcript.jsonl",
        }))
        self.addCleanup(directory.cleanup)

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "ctx 8%\n")
        self.assertEqual(json.loads(destination.read_text(encoding="utf-8")), {
            "kind": "status-context", "percent": 8, "windowTokens": 1_000_000,
        })
        self.assertNotIn("SECRET", destination.read_text(encoding="utf-8"))

    def test_invalid_or_missing_capacity_remains_non_blocking_and_writes_nothing(self) -> None:
        for payload in ("not-json", json.dumps({"context_window": {"used_percentage": 8}})):
            with self.subTest(payload=payload):
                result, destination, directory = self.run_recorder(payload)
                self.addCleanup(directory.cleanup)
                self.assertEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "ctx --\n")
                self.assertFalse(destination.exists())


if __name__ == "__main__":
    unittest.main()
