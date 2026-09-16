#!/usr/bin/env python3
"""Protocol and privacy tests for the disposable context MCP fixture."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "tests" / "mcp-context-fixture.py"


class McpContextFixtureTests(unittest.TestCase):
    def test_stdio_server_exposes_one_tool_and_persists_only_connection_signal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            signal = Path(directory) / "connected.json"
            process = subprocess.Popen(
                [sys.executable, str(SERVER), str(signal), "p004b-run-001"],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True,
            )
            assert process.stdin is not None and process.stdout is not None
            request = {
                "jsonrpc": "2.0", "id": 1, "method": "initialize",
                "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                           "clientInfo": {"name": "SYNTH_SECRET", "version": "1"}},
            }
            process.stdin.write(json.dumps(request) + "\n")
            process.stdin.flush()
            initialized = json.loads(process.stdout.readline())
            self.assertEqual(initialized["id"], 1)
            self.assertEqual(initialized["result"]["capabilities"], {"tools": {}})

            process.stdin.write(json.dumps({
                "jsonrpc": "2.0", "method": "notifications/initialized", "params": {},
            }) + "\n")
            process.stdin.write(json.dumps({
                "jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {},
            }) + "\n")
            process.stdin.flush()
            listed = json.loads(process.stdout.readline())
            self.assertEqual(len(listed["result"]["tools"]), 1)
            self.assertEqual(listed["result"]["tools"][0]["name"], "context_fixture_ping")
            self.assertEqual(
                listed["result"]["tools"][0]["inputSchema"]["properties"]["nonce"]["const"],
                "p004b-run-001",
            )
            process.stdin.write(json.dumps({
                "jsonrpc": "2.0", "id": 3, "method": "tools/call",
                "params": {"name": "context_fixture_ping", "arguments": {
                    "nonce": "p004b-run-001",
                }},
            }) + "\n")
            process.stdin.flush()
            called = json.loads(process.stdout.readline())
            self.assertEqual(called["id"], 3)
            process.stdin.write(json.dumps({
                "jsonrpc": "2.0", "id": 4, "method": "initialize", "params": {},
            }) + "\n")
            process.stdin.write(json.dumps({
                "jsonrpc": "2.0", "id": 5, "method": "tools/list", "params": {},
            }) + "\n")
            process.stdin.flush()
            self.assertEqual(json.loads(process.stdout.readline())["id"], 4)
            self.assertEqual(json.loads(process.stdout.readline())["id"], 5)
            process.stdin.close()
            process.wait(timeout=5)
            process.stdout.close()
            assert process.stderr is not None
            process.stderr.close()
            self.assertEqual(process.returncode, 0)
            evidence = json.loads(signal.read_text(encoding="utf-8"))
            self.assertEqual(evidence, {
                "connected": True, "toolsListed": True, "visibleToolCount": 1,
                "called": True, "callCount": 1, "runNonce": "p004b-run-001",
            })
            self.assertNotIn("SYNTH_SECRET", signal.read_text(encoding="utf-8"))

    def test_list_or_call_without_prior_lifecycle_stays_incomplete(self) -> None:
        requests = (
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
            {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {
                "name": "context_fixture_ping", "arguments": {"nonce": "p004b-run-001"},
            }},
        )
        with tempfile.TemporaryDirectory() as directory:
            for index, request in enumerate(requests):
                signal = Path(directory) / f"signal-{index}.json"
                completed = subprocess.run(
                    [sys.executable, str(SERVER), str(signal), "p004b-run-001"],
                    input=json.dumps(request) + "\n", text=True,
                    capture_output=True, check=False,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertFalse(signal.exists())


if __name__ == "__main__":
    unittest.main()
