#!/usr/bin/env python3
"""Real-process tests for the disposable P0-04B permission MCP server."""
from __future__ import annotations

import base64
from concurrent.futures import ThreadPoolExecutor
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "tests" / "browser-permission-mcp.py"
VERIFIER = ROOT / "tests" / "browser-permission-verifier.mjs"
RUNNER = ROOT / "skills" / "browser-operations" / "scripts" / "browser-runner.mjs"
NODE = shutil.which("node") or "node"
ORIGIN = "http://127.0.0.1:43111"
NONCE = "p004b-run-001"
SESSION = "11111111-1111-4111-8111-111111111111"
OPERATION = "p004b-allow-operation"


def token(value: dict[str, object]) -> str:
    encoded = json.dumps(value, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(encoded).rstrip(b"=").decode("ascii")


def authentication() -> list[dict[str, object]]:
    return [
        {"step": "navigate", "origin": ORIGIN},
        {"step": "click", "origin": ORIGIN, "locatorRole": "link", "locatorName": "Login", "effect": "INTERACTIVE_STATE"},
        {"step": "fill", "origin": ORIGIN, "locatorRole": "textbox", "locatorName": "Password", "valueRef": "env:OPS_BROWSER_VALUE_PASSWORD", "valueClass": "credential"},
        {"step": "click", "origin": ORIGIN, "locatorRole": "button", "locatorName": "Continue", "effect": "INTERACTIVE_STATE"},
        {"step": "fill", "origin": ORIGIN, "locatorRole": "textbox", "locatorName": "Code", "valueRef": "env:OPS_BROWSER_VALUE_TOTP", "valueClass": "credential"},
        {"step": "click", "origin": ORIGIN, "locatorRole": "button", "locatorName": "Verify", "effect": "INTERACTIVE_STATE"},
    ]


def command(phase: str = "allow", canary: str | None = None) -> str:
    allow = phase == "allow"
    auth = authentication()
    execution = auth + ([
        {"step": "select", "origin": ORIGIN, "locatorRole": "combobox", "locatorName": "WAN enabled", "valueRef": "env:OPS_BROWSER_VALUE_DISABLED", "valueClass": "configuration"},
        {"step": "click", "origin": ORIGIN, "locatorRole": "button", "locatorName": "Save", "effect": "LOW_RISK_CHANGE"},
    ] if allow else [
        {"step": "click", "origin": ORIGIN, "locatorRole": "button", "locatorName": "Rollback", "effect": "LOW_RISK_CHANGE"},
    ])
    validation = auth + [{
        "step": "inspect", "origin": ORIGIN, "locatorRole": "status", "locatorName": "Saved state",
        "predicate": "text-equals", "expectedRef": "env:OPS_BROWSER_VALUE_EXPECTED_FALSE" if allow else "env:OPS_BROWSER_VALUE_EXPECTED_TRUE",
        "expectRef": "interface-state",
    }]
    actions = ["navigate", "fill"] + (["select"] if allow else []) + ["click", "inspect"]
    operation = OPERATION if allow else "p004b-deny-operation"
    session = SESSION if allow else "22222222-2222-4222-8222-222222222222"
    args = [
        "--step", "workflow", "--operation-id", operation, "--session-id", session,
        "--role", "network-edge-operator", "--objective-ref", NONCE, "--target", "loopback-router",
        "--environment", "test", "--service-origin", ORIGIN, "--auth-origin", ORIGIN,
        "--identity-ref", "vault:network-admin", "--credential-transport", "vault",
        "--permission-mode", "normal",
    ]
    for action in actions:
        args.extend(["--action", action])
    args.extend([
        "--effect", "LOW_RISK_CHANGE", "--risk", "LOW_RISK_CHANGE",
        "--precondition-ref", "fixture-ready", "--validation-ref", "interface-state",
        "--compensation-ref", "fixture-rollback", "--expires-in-seconds", "600",
    ])
    for step in execution:
        args.extend(["--workflow-step", token(step)])
    for step in validation:
        args.extend(["--validation-step", token(step)])
    result = "node " + shlex.quote(str(RUNNER)) + " " + " ".join(shlex.quote(item) for item in args)
    return result if canary is None else f"{result} {canary}"


def arguments(phase: str = "allow", canary: str | None = None) -> dict[str, object]:
    return {"tool_name": "Bash", "input": {"command": command(phase, canary)}}


class Client:
    def __init__(
        self, root: Path, phase: str = "allow", decision: str | None = None,
        verifier: Path = VERIFIER, claim: Path | None = None, signal: Path | None = None,
    ) -> None:
        self.phase = phase
        self.claim = claim or root / f"{phase}.claim"
        self.signal = signal or root / f"{phase}.signal.json"
        operation = OPERATION if phase == "allow" else "p004b-deny-operation"
        session = SESSION if phase == "allow" else "22222222-2222-4222-8222-222222222222"
        self.process = subprocess.Popen([
            sys.executable, str(SERVER), str(verifier), str(NODE), str(RUNNER),
            phase, decision or phase, operation, session, NONCE, ORIGIN,
            str(self.claim), str(self.signal),
        ], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    def request(self, method: str, identifier: int, params: object | None = None) -> dict[str, object]:
        assert self.process.stdin is not None and self.process.stdout is not None
        value: dict[str, object] = {"jsonrpc": "2.0", "id": identifier, "method": method}
        if params is not None:
            value["params"] = params
        self.process.stdin.write(json.dumps(value, separators=(",", ":")) + "\n")
        self.process.stdin.flush()
        line = self.process.stdout.readline()
        if not line:
            stderr = self.process.stderr.read() if self.process.stderr else ""
            raise AssertionError(f"server closed without response: {stderr}")
        return json.loads(line)

    def initialize(self) -> None:
        response = self.request("initialize", 1, {
            "protocolVersion": "2025-06-18", "capabilities": {},
            "clientInfo": {"name": "test", "version": "1"},
        })
        assert response["result"]["serverInfo"]["name"] == "p004b-permission"
        assert self.process.stdin is not None
        self.process.stdin.write('{"jsonrpc":"2.0","method":"notifications/initialized"}\n')
        self.process.stdin.flush()

    def list_tools(self) -> dict[str, object]:
        return self.request("tools/list", 2, {})

    def call(self, payload: dict[str, object] | None = None, identifier: int = 3) -> dict[str, object]:
        return self.request("tools/call", identifier, {
            "name": "approval_prompt", "arguments": payload or arguments(self.phase),
        })

    def close(self) -> str:
        if self.process.stdin:
            self.process.stdin.close()
        self.process.wait(timeout=5)
        stderr = self.process.stderr.read() if self.process.stderr else ""
        if self.process.stdout:
            self.process.stdout.close()
        if self.process.stderr:
            self.process.stderr.close()
        return stderr


class BrowserPermissionMcpPlatformTests(unittest.TestCase):
    @unittest.skipUnless(os.name == "nt", "native Windows rejection only")
    def test_native_windows_is_rejected_explicitly(self) -> None:
        result = subprocess.run([sys.executable, str(SERVER)], capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stderr, "P004B permission MCP rejected\n")


@unittest.skipIf(os.name == "nt", "atomic owner-only handler requires POSIX")
class BrowserPermissionMcpProtocolTests(unittest.TestCase):
    def test_exact_allow_and_deny_protocol_and_signals(self) -> None:
        for phase in ("allow", "deny"):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as directory:
                client = Client(Path(directory), phase)
                client.initialize()
                listed = client.list_tools()
                self.assertEqual([tool["name"] for tool in listed["result"]["tools"]], ["approval_prompt"])
                called = client.call()
                permission = json.loads(called["result"]["content"][0]["text"])
                expected = ({"behavior": "allow", "updatedInput": arguments(phase)["input"]}
                            if phase == "allow" else {"behavior": "deny", "message": "P004B_SYNTHETIC_DENY"})
                self.assertEqual(permission, expected)
                signal = json.loads(client.signal.read_text(encoding="utf-8"))
                self.assertEqual(signal, {
                    "schemaVersion": 1, "runNonce": NONCE, "phase": phase,
                    "decision": phase, "callCount": 1,
                    "invocationFingerprint": signal["invocationFingerprint"],
                    "verified": True, "inputUnchanged": True,
                })
                self.assertRegex(signal["invocationFingerprint"], r"^[0-9a-f]{64}$")
                self.assertEqual(client.claim.read_text(encoding="ascii"), "claimed\n")
                self.assertEqual(client.claim.stat().st_mode & 0o777, 0o600)
                self.assertEqual(client.signal.stat().st_mode & 0o777, 0o600)
                self.assertEqual(client.close(), "")

    def test_lifecycle_mismatch_and_duplicate_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            early = Client(root)
            early.initialize()
            self.assertIn("error", early.call())
            self.assertFalse(early.claim.exists())
            early.close()

            client = Client(root)
            client.initialize()
            client.list_tools()
            mismatch = arguments("allow")
            mismatch["tool_name"] = "Read"
            response = client.call(mismatch)
            self.assertEqual(json.loads(response["result"]["content"][0]["text"]), {
                "behavior": "deny", "message": "P004B_PERMISSION_DENIED",
            })
            self.assertTrue(client.claim.exists())
            self.assertFalse(client.signal.exists())
            duplicate = client.call(arguments("allow"), 4)
            self.assertEqual(json.loads(duplicate["result"]["content"][0]["text"])["message"], "P004B_PERMISSION_DENIED")
            client.close()

    def test_concurrent_claim_allows_at_most_one_decision(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            claim, signal = root / "shared.claim", root / "shared.signal"
            clients = [Client(root, claim=claim, signal=signal) for _ in range(2)]
            for client in clients:
                client.initialize()
                client.list_tools()
            with ThreadPoolExecutor(max_workers=2) as pool:
                responses = list(pool.map(lambda client: client.call(), clients))
            permissions = [json.loads(item["result"]["content"][0]["text"]) for item in responses]
            self.assertEqual(sum(item["behavior"] == "allow" for item in permissions), 1)
            self.assertEqual(sum(item.get("message") == "P004B_PERMISSION_DENIED" for item in permissions), 1)
            for client in clients:
                client.close()

    def test_size_malformed_json_and_secret_canary_are_not_retained(self) -> None:
        canary = "P004B_SECRET_CANARY_DO_NOT_RETAIN"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            client = Client(root)
            client.initialize()
            client.list_tools()
            assert client.process.stdin is not None
            client.process.stdin.write("{malformed\n")
            client.process.stdin.flush()
            ping = client.request("ping", 7)
            self.assertEqual(ping["result"], {})
            oversized = arguments("allow")
            oversized["input"] = {"command": "x" * 65_537 + canary}
            response = client.call(oversized)
            text = json.dumps(response, separators=(",", ":"))
            self.assertNotIn(canary, text)
            self.assertEqual(json.loads(response["result"]["content"][0]["text"])["message"], "P004B_PERMISSION_DENIED")
            stderr = client.close()
            retained = stderr
            for path in (client.claim, client.signal):
                if path.exists() and path.is_file():
                    retained += path.read_text(encoding="utf-8")
            self.assertNotIn(canary, retained)

    def test_symlinks_and_verifier_failures_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target"
            target.write_text("sentinel", encoding="utf-8")
            for selected in ("claim", "signal"):
                claim, signal = root / f"{selected}.claim", root / f"{selected}.signal"
                (claim if selected == "claim" else signal).symlink_to(target)
                client = Client(root, claim=claim, signal=signal)
                client.initialize()
                client.list_tools()
                response = client.call()
                self.assertEqual(json.loads(response["result"]["content"][0]["text"])["message"], "P004B_PERMISSION_DENIED")
                client.close()
                self.assertEqual(target.read_text(encoding="utf-8"), "sentinel")

            for source in ("process.exit(3);", "setTimeout(() => {}, 10000);"):
                verifier = root / f"verifier-{len(source)}.mjs"
                verifier.write_text(source, encoding="utf-8")
                client = Client(root, verifier=verifier,
                                claim=root / f"failure-{len(source)}.claim",
                                signal=root / f"failure-{len(source)}.signal")
                client.initialize()
                client.list_tools()
                response = client.call()
                self.assertEqual(json.loads(response["result"]["content"][0]["text"])["message"], "P004B_PERMISSION_DENIED")
                self.assertFalse(client.signal.exists())
                client.close()


if __name__ == "__main__":
    unittest.main()
