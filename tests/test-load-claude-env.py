#!/usr/bin/env python3
"""Behavioral tests for the live probe's allowlisted Claude environment loader."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOADER = ROOT / "tests" / "load-claude-env.py"


class LoadClaudeEnvTests(unittest.TestCase):
    def run_loader(self, payload: object, *allowed: str) -> subprocess.CompletedProcess[bytes]:
        with tempfile.TemporaryDirectory() as directory:
            settings = Path(directory) / "settings.json"
            settings.write_text(json.dumps(payload), encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(LOADER), str(settings), *allowed],
                check=False,
                capture_output=True,
            )

    def test_emits_only_allowlisted_string_values_as_nul_records(self) -> None:
        result = self.run_loader(
            {
                "env": {
                    "ANTHROPIC_AUTH_TOKEN": "secret-value",
                    "ANTHROPIC_MODEL": "future-model",
                    "UNRELATED_SECRET": "must-not-cross-boundary",
                    "NON_STRING": 42,
                }
            },
            "ANTHROPIC_AUTH_TOKEN",
            "ANTHROPIC_MODEL",
            "NON_STRING",
        )

        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertEqual(
            result.stdout.split(b"\0"),
            [
                b"ANTHROPIC_AUTH_TOKEN=secret-value",
                b"ANTHROPIC_MODEL=future-model",
                b"",
            ],
        )
        self.assertNotIn(b"UNRELATED_SECRET", result.stdout)
        self.assertNotIn(b"NON_STRING", result.stdout)

    def test_missing_settings_is_an_empty_success(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing.json"
            result = subprocess.run(
                [sys.executable, str(LOADER), str(missing), "ANTHROPIC_AUTH_TOKEN"],
                check=False,
                capture_output=True,
            )

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, b"")

    def test_rejects_invalid_key_names_and_nul_values(self) -> None:
        invalid_key = self.run_loader(
            {"env": {"BAD-KEY": "value"}},
            "BAD-KEY",
        )
        nul_value = self.run_loader(
            {"env": {"ANTHROPIC_AUTH_TOKEN": "bad\0value"}},
            "ANTHROPIC_AUTH_TOKEN",
        )

        self.assertNotEqual(invalid_key.returncode, 0)
        self.assertNotEqual(nul_value.returncode, 0)
        self.assertNotIn(b"value", invalid_key.stderr)
        self.assertNotIn(b"bad", nul_value.stderr)


if __name__ == "__main__":
    unittest.main()
