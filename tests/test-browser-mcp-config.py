#!/usr/bin/env python3
"""Tests for phase-isolated P0-04B MCP configuration generation."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "tests" / "browser-mcp-config.py"
HANDLER = ROOT / "tests" / "browser-permission-mcp.py"
VERIFIER = ROOT / "tests" / "browser-permission-verifier.mjs"
RUNNER = ROOT / "skills" / "browser-operations" / "scripts" / "browser-runner.mjs"
FIXTURE = ROOT / "tests" / "mcp-context-fixture.py"
NODE = Path(shutil.which("node") or "node")
NONCE = "p004b-run-001"
ORIGIN = "http://127.0.0.1:43111"
ALLOW_SESSION = "11111111-1111-4111-8111-111111111111"
DENY_SESSION = "22222222-2222-4222-8222-222222222222"


@unittest.skipIf(os.name == "nt", "private output requires POSIX O_NOFOLLOW")
class BrowserMcpConfigTests(unittest.TestCase):
    def invoke(self, output: Path, *overrides: object) -> subprocess.CompletedProcess[str]:
        values: list[object] = [
            HANDLER, VERIFIER, NODE, RUNNER, FIXTURE, output,
            output / "fixture.signal.json", NONCE, ORIGIN, ALLOW_SESSION, DENY_SESSION,
        ]
        for index in range(0, len(overrides), 2):
            values[int(overrides[index])] = overrides[index + 1]
        return subprocess.run(
            [sys.executable, str(BUILDER), *(str(value) for value in values)],
            capture_output=True, text=True, check=False,
        )

    def test_emits_four_private_phase_isolated_configs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            result = self.invoke(output)
            self.assertEqual(result.returncode, 0, result.stderr)
            values = {
                name: json.loads((output / f"{name}-mcp.json").read_text(encoding="utf-8"))
                for name in ("empty", "measurement", "allow", "deny")
            }
            self.assertEqual(values["empty"]["mcpServers"], {})
            self.assertEqual(set(values["measurement"]["mcpServers"]), {"p004b-context"})
            self.assertEqual(set(values["allow"]["mcpServers"]), {"p004b-permission"})
            self.assertEqual(set(values["deny"]["mcpServers"]), {"p004b-permission"})
            allow = values["allow"]["mcpServers"]["p004b-permission"]
            deny = values["deny"]["mcpServers"]["p004b-permission"]
            self.assertEqual(allow["command"], sys.executable)
            self.assertEqual(allow["args"][4:6], ["allow", "allow"])
            self.assertEqual(deny["args"][4:6], ["deny", "deny"])
            self.assertNotEqual(allow["args"][6], deny["args"][6])
            self.assertEqual(allow["args"][7], ALLOW_SESSION)
            self.assertEqual(deny["args"][7], DENY_SESSION)
            self.assertNotEqual(allow["args"][-2:], deny["args"][-2:])
            for name in values:
                self.assertEqual((output / f"{name}-mcp.json").stat().st_mode & 0o777, 0o600)
            serialized = json.dumps(values, separators=(",", ":"))
            self.assertNotIn('"env"', serialized)
            self.assertNotIn("TOKEN", serialized)
            self.assertNotIn("secret", serialized.lower())
            self.assertNotIn("external", serialized.lower())

    def test_rejects_unsafe_inputs_without_partial_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cases: list[tuple[str, int, object]] = [
                ("relative-handler", 0, Path("relative.py")),
                ("duplicate-session", 10, ALLOW_SESSION),
                ("invalid-origin", 8, "https://example.com"),
                ("invalid-nonce", 7, "bad nonce"),
                ("long-nonce", 7, "x" * 257),
            ]
            link = root / "handler-link.py"
            link.symlink_to(HANDLER)
            cases.append(("linked-handler", 0, link))
            for name, index, value in cases:
                with self.subTest(name=name):
                    output = root / name
                    output.mkdir(mode=0o700)
                    result = self.invoke(output, index, value)
                    self.assertEqual(result.returncode, 2)
                    self.assertEqual(list(output.iterdir()), [])

    def test_rejects_public_directory_and_preexisting_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            public = root / "public"
            public.mkdir(mode=0o755)
            os.chmod(public, 0o755)
            result = self.invoke(public)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(list(public.iterdir()), [])

            output = root / "existing"
            output.mkdir(mode=0o700)
            existing = output / "allow-mcp.json"
            existing.write_text("sentinel", encoding="utf-8")
            result = self.invoke(output)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(existing.read_text(encoding="utf-8"), "sentinel")
            self.assertEqual([path.name for path in output.iterdir()], ["allow-mcp.json"])


if __name__ == "__main__":
    unittest.main()
