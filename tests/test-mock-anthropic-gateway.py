#!/usr/bin/env python3
"""Behavior and privacy tests for the loopback window-divergence gateway."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "tests" / "mock-anthropic-gateway.py"


class MockAnthropicGatewayTests(unittest.TestCase):
    def test_accepts_and_rejects_real_boundaries_without_persisting_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            port_file = root / "port.json"
            log_file = root / "events.jsonl"
            process = subprocess.Popen([
                sys.executable, str(SERVER), str(port_file), str(log_file), "1000", "4",
            ])
            try:
                for _ in range(100):
                    if port_file.is_file(): break
                    time.sleep(0.02)
                port = json.loads(port_file.read_text(encoding="utf-8"))["port"]
                def post(content: str, stream: bool = False):
                    body = json.dumps({
                        "model": "mock-model", "max_tokens": 8, "stream": stream,
                        "messages": [{"role": "user", "content": content}],
                    }).encode()
                    return urllib.request.urlopen(urllib.request.Request(
                        f"http://127.0.0.1:{port}/v1/messages", data=body,
                        headers={"Content-Type": "application/json", "X-Secret": "SYNTH_SECRET"},
                    ), timeout=3).read().decode()
                self.assertIn("P004A_MOCK_OK", post("one two", stream=True))
                with self.assertRaises(urllib.error.HTTPError) as rejected:
                    post("one two three four five")
                self.assertEqual(rejected.exception.code, 400)
            finally:
                process.terminate()
                process.wait(timeout=5)
            retained = log_file.read_text(encoding="utf-8")
            self.assertNotIn("SYNTH_SECRET", retained)
            self.assertNotIn("one two", retained)
            events = [json.loads(line) for line in retained.splitlines()]
            self.assertEqual([event["status"] for event in events], [200, 400])
            self.assertTrue(all(set(event) == {
                "method", "path", "status", "reportedWindow", "observedWindow",
            } for event in events))


if __name__ == "__main__":
    unittest.main()
