#!/usr/bin/env python3
"""Behavioral tests for the confirmed-window diagnostic gate."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "tests" / "confirmed-window-diagnostic.py"


class ConfirmedWindowDiagnosticTests(unittest.TestCase):
    def run_gate(self, events: list[dict[str, object]], confirmed: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as directory:
            event_path = Path(directory) / "status-context.jsonl"
            event_path.write_text(
                "".join(json.dumps(event) + "\n" for event in events),
                encoding="utf-8",
            )
            return subprocess.run(
                [sys.executable, str(GATE), "--events", str(event_path), "--confirmed", confirmed],
                check=False,
                capture_output=True,
                text=True,
            )

    def test_accepts_only_an_exact_native_window_match(self) -> None:
        result = self.run_gate([{
            "kind": "status-context", "percent": 8, "windowTokens": 1_000_000,
        }], "1000000")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "1000000\n")
        self.assertEqual(result.stderr, "")

    def test_rejects_a_confirmed_value_that_differs_from_the_native_window(self) -> None:
        result = self.run_gate([{
            "kind": "status-context", "percent": 8, "windowTokens": 1_000_000,
        }], "999999")

        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("does not equal native context capacity", result.stderr)

    def test_rejects_a_missing_native_window_label(self) -> None:
        result = self.run_gate([{
            "kind": "status-context", "percent": 8,
        }], "1000000")

        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("native context capacity unavailable", result.stderr)

    def test_rejects_zero_non_numeric_and_fractional_confirmations(self) -> None:
        for value in ("0", "one-million", "1000000.0", "-1000000"):
            with self.subTest(value=value):
                result = self.run_gate([{
                    "kind": "status-context", "percent": 8, "windowTokens": 1_000_000,
                }], value)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, "")

    def test_rejects_a_model_label_without_structural_context_capacity(self) -> None:
        result = self.run_gate([{
            "kind": "pty-driver", "stage": "context_inspected", "outcome": "passed",
            "percent": 8,
            "modelLabel": "deepseek-v4-pro[1m]",
        }], "1000000")

        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")

    def test_accepts_repeated_consistent_native_status_events(self) -> None:
        event: dict[str, object] = {
            "kind": "status-context", "percent": 8, "windowTokens": 1_000_000,
        }
        result = self.run_gate([event, event], "1000000")

        self.assertEqual(result.returncode, 0)

    def test_rejects_conflicting_native_status_capacities(self) -> None:
        result = self.run_gate([{
            "kind": "status-context", "percent": 8, "windowTokens": 1_000_000,
        }, {
            "kind": "status-context", "percent": 9, "windowTokens": 200_000,
        }], "1000000")

        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")

    def test_rejects_boolean_or_unbounded_structural_capacity(self) -> None:
        for value, confirmed in ((True, "1"), (10_000_001, "10000001")):
            with self.subTest(value=value):
                result = self.run_gate([{
                    "kind": "status-context", "percent": 8, "windowTokens": value,
                }], confirmed)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
