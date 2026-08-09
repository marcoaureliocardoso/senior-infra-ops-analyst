#!/usr/bin/env python3
"""Tests for clean, argv-safe Claude environment execution."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "tests" / "exec-claude-env.py"


class ExecClaudeEnvTests(unittest.TestCase):
    @unittest.skipUnless(os.name == "posix", "execve behavior requires POSIX")
    def test_allowlisted_value_reaches_environment_but_never_command_arguments(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            settings = Path(directory) / "settings.json"
            settings.write_text(json.dumps({"env": {
                "P004A_ALLOWED": "SYNTH_SECRET", "P004A_BLOCKED": "do-not-copy",
            }}), encoding="utf-8")
            code = "import json,os,sys; print(json.dumps({'allowed':os.getenv('P004A_ALLOWED'),'blocked':os.getenv('P004A_BLOCKED'),'argv':sys.argv}))"
            command = [
                sys.executable, str(HELPER), str(settings), "P004A_ALLOWED", "--",
                sys.executable, "-c", code, "safe-argument",
            ]
            result = subprocess.run(command, check=True, text=True, capture_output=True)
            value = json.loads(result.stdout)
            self.assertEqual(value["allowed"], "SYNTH_SECRET")
            self.assertIsNone(value["blocked"])
            self.assertNotIn("SYNTH_SECRET", " ".join(value["argv"]))


if __name__ == "__main__":
    unittest.main()
