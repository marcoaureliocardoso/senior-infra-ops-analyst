#!/usr/bin/env python3
"""Tests for strict minimization of the P0-04B MCP configuration."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "tests" / "browser-mcp-config.py"
FIXTURE = ROOT / "tests" / "mcp-context-fixture.py"


@unittest.skipIf(os.name == "nt", "private output requires POSIX O_NOFOLLOW")
class BrowserMcpConfigTests(unittest.TestCase):
    def test_only_exact_approval_server_and_fixture_are_retained(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "operator.json"
            approval = root / "approval.json"
            measurement = root / "measurement.json"
            signal = root / "signal.json"
            source.write_text(json.dumps({
                "mcpServers": {
                    "approval": {"command": "approval", "env": {"TOKEN": "secret"}},
                    "unrelated": {"command": "must-not-start"},
                },
                "other": "ignored",
            }), encoding="utf-8")
            result = subprocess.run([
                sys.executable, str(BUILDER), str(source), "mcp__approval__ask",
                str(approval), str(measurement), str(FIXTURE), str(signal),
                "p004b-run-001",
            ], capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            approval_value = json.loads(approval.read_text(encoding="utf-8"))
            measurement_value = json.loads(measurement.read_text(encoding="utf-8"))
            self.assertEqual(set(approval_value["mcpServers"]), {"approval"})
            self.assertEqual(
                set(measurement_value["mcpServers"]), {"approval", "p004b-context"},
            )
            self.assertNotIn("unrelated", json.dumps(measurement_value))
            self.assertEqual(approval.stat().st_mode & 0o777, 0o600)
            self.assertEqual(measurement.stat().st_mode & 0o777, 0o600)

    def test_ambiguous_or_missing_tool_binding_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "operator.json"
            source.write_text(json.dumps({"mcpServers": {
                "approval": {"command": "approval"},
            }}), encoding="utf-8")
            for index, tool in enumerate(("mcp__missing__ask", "bad tool")):
                result = subprocess.run([
                    sys.executable, str(BUILDER), str(source), tool,
                    str(root / f"a-{index}.json"), str(root / f"m-{index}.json"),
                    str(FIXTURE), str(root / f"signal-{index}.json"), "p004b-run-001",
                ], capture_output=True, text=True, check=False)
                self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
