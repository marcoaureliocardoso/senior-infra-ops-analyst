#!/usr/bin/env python3
"""Behavioral tests for the confirmed-window diagnostic gate."""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "tests" / "confirmed-window-diagnostic.py"


class ConfirmedWindowDiagnosticTests(unittest.TestCase):
    def run_gate(self, capture_text: str, confirmed: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as directory:
            capture = Path(directory) / "context.pty"
            capture.write_text(capture_text, encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(GATE), "--capture", str(capture), "--confirmed", confirmed],
                check=False,
                capture_output=True,
                text=True,
            )

    def test_accepts_only_an_exact_native_window_match(self) -> None:
        result = self.run_gate("header [200k]\nlatest native window [1m] ctx 8%\n", "1000000")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "1000000\n")
        self.assertEqual(result.stderr, "")

    def test_rejects_a_confirmed_value_that_differs_from_the_native_window(self) -> None:
        result = self.run_gate("native window [1m] ctx 8%\n", "999999")

        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("does not equal native context capacity", result.stderr)

    def test_rejects_a_missing_native_window_label(self) -> None:
        result = self.run_gate("native context ctx 8%\n", "1000000")

        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("native context capacity unavailable", result.stderr)

    def test_rejects_zero_non_numeric_and_fractional_confirmations(self) -> None:
        for value in ("0", "one-million", "1000000.0", "-1000000"):
            with self.subTest(value=value):
                result = self.run_gate("native window [1m] ctx 8%\n", value)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, "")

    def test_rejects_an_unsupported_native_window_unit(self) -> None:
        result = self.run_gate("native window [1g] ctx 8%\n", "1000000000")

        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
