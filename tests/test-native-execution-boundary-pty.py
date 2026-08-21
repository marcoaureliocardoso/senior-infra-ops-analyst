#!/usr/bin/env python3
"""Behavior contract for the bounded P0-05 PTY evidence driver."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "tests" / "native-execution-boundary-pty.py"
EXPECTED = [
    "main-default:PreToolUse:deny",
    "main-bypass:PreToolUse:deny",
    "executor-fallback:PreToolUse:deny",
]


def load_driver():
    if not DRIVER.is_file():
        raise AssertionError("native execution boundary PTY driver is missing")
    spec = importlib.util.spec_from_file_location("native_execution_boundary_pty", DRIVER)
    if spec is None or spec.loader is None:
        raise AssertionError("native execution boundary PTY driver cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def audit_record(*, session="session-current", agent=None, mode="default",
                 decision="deny", reason="DENY_UNKNOWN_COMMAND", timestamp=None,
                 probe_nonce="0123456789abcdef0123456789abcdef"):
    return {
        "timestamp": timestamp or "2026-08-21T12:00:01.000Z",
        "sessionId": session,
        "agent": agent,
        "mode": mode,
        "risk": None,
        "modifiers": [],
        "policyId": None,
        "target": None,
        "environment": None,
        "scope": None,
        "credential": None,
        "actionId": "a" * 64,
        "decision": decision,
        "reason": reason,
        "stage": 1,
        "findings": [],
        "probeNonce": probe_nonce,
    }


class NativeExecutionBoundaryPtyTests(unittest.TestCase):
    def test_driver_exists(self) -> None:
        self.assertTrue(DRIVER.is_file())

    def test_exact_sequence_rejects_missing_repeated_or_reordered_markers(self) -> None:
        driver = load_driver()
        self.assertTrue(driver.exact_sequence(EXPECTED))
        for observed in (
            EXPECTED[:-1],
            EXPECTED + [EXPECTED[-1]],
            [EXPECTED[1], EXPECTED[0], EXPECTED[2]],
            ["main-default:PostToolUse:deny", *EXPECTED],
            [*EXPECTED, "orphan:PreToolUse:deny"],
        ):
            self.assertFalse(driver.exact_sequence(observed), observed)

    def test_audit_parser_requires_exact_current_stage_record(self) -> None:
        driver = load_driver()
        with tempfile.TemporaryDirectory() as directory:
            audit = Path(directory) / "audit-stage-nonce.jsonl"
            audit.write_text(json.dumps(audit_record()) + "\n", encoding="utf-8")
            result = driver.observe_audit(
                audit,
                stage="main-default",
                expected_mode="default",
                expected_agent=None,
                started_at=1787313600.0,
                expected_nonce="0123456789abcdef0123456789abcdef",
            )
            self.assertEqual(result.marker, EXPECTED[0])
            self.assertEqual(result.reason_code, "DENY_UNKNOWN_COMMAND")
            self.assertTrue(result.session_matched)

    def test_audit_parser_rejects_stale_wrong_session_shape_and_wrong_actor(self) -> None:
        driver = load_driver()
        mutations = [
            [audit_record(timestamp="2026-08-21T11:59:59.000Z")],
            [audit_record(session="")],
            [audit_record(agent="diagnostic-operator")],
            [audit_record(mode="bypassPermissions")],
            [audit_record(decision="allow")],
            [audit_record(reason="ALLOW_NARROW_READ")],
            [audit_record(probe_nonce="fedcba9876543210fedcba9876543210")],
            [{key: value for key, value in audit_record().items() if key != "probeNonce"}],
            [{**audit_record(), "stage": None}],
            [audit_record(), audit_record(session="second-session")],
        ]
        with tempfile.TemporaryDirectory() as directory:
            audit = Path(directory) / "audit-stage-nonce.jsonl"
            for records in mutations:
                audit.write_text(
                    "".join(json.dumps(item) + "\n" for item in records),
                    encoding="utf-8",
                )
                with self.assertRaises(driver.EvidenceError):
                    driver.observe_audit(
                        audit,
                        stage="main-default",
                        expected_mode="default",
                        expected_agent=None,
                        started_at=1787313600.0,
                        expected_nonce="0123456789abcdef0123456789abcdef",
                    )

    def test_audit_parser_rejects_malformed_oversized_and_unknown_fields(self) -> None:
        driver = load_driver()
        with tempfile.TemporaryDirectory() as directory:
            audit = Path(directory) / "audit-stage-nonce.jsonl"
            for payload in (
                "{\n",
                "x" * (driver.MAX_AUDIT_BYTES + 1),
                json.dumps({**audit_record(), "command": "printf P005_GUARD_PROBE"}) + "\n",
            ):
                audit.write_text(payload, encoding="utf-8")
                with self.assertRaises(driver.EvidenceError):
                    driver.observe_audit(
                        audit,
                        stage="main-default",
                        expected_mode="default",
                        expected_agent=None,
                        started_at=1787313600.0,
                        expected_nonce="0123456789abcdef0123456789abcdef",
                    )

    def test_prompt_or_terminal_echo_cannot_create_evidence(self) -> None:
        driver = load_driver()
        echoed = "main-default:PreToolUse:deny DENY_UNKNOWN_COMMAND P005_GUARD_PROBE"
        self.assertFalse(driver.terminal_text_is_evidence(echoed.encode("utf-8")))
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "audit-stage-nonce.jsonl"
            with self.assertRaises(driver.EvidenceError):
                driver.observe_audit(
                    missing,
                    stage="main-default",
                    expected_mode="default",
                    expected_agent=None,
                    started_at=time.time(),
                    expected_nonce="0123456789abcdef0123456789abcdef",
                )

    @unittest.skipUnless(os.name == "posix", "PTY behavior requires POSIX")
    def test_driver_accepts_fresh_structural_audit_and_discards_large_terminal_output(self) -> None:
        driver = load_driver()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fake = root / "fake-claude.py"
            audit = root / "audit-0123456789abcdef0123456789abcdef.jsonl"
            fake.write_text(textwrap.dedent(r'''
                import json, os, sys, time
                from datetime import datetime, timezone
                audit = os.environ["OPS_COMMAND_GUARD_AUDIT_PATH"]
                os.write(sys.stdout.fileno(), b"echo main-default:PreToolUse:deny " + b"x" * 65536)
                record = {
                    "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    "sessionId": "fresh-session", "agent": None, "mode": "default",
                    "risk": None, "modifiers": [], "policyId": None, "target": None,
                    "environment": None, "scope": None, "credential": None,
                    "actionId": "a" * 64, "decision": "deny",
                    "reason": "DENY_UNKNOWN_COMMAND", "stage": 1, "findings": [],
                    "probeNonce": os.environ["P005_LIVE_STAGE_NONCE"],
                }
                with open(audit, "w", encoding="utf-8") as stream:
                    stream.write(json.dumps(record) + "\n")
                time.sleep(0.1)
            '''), encoding="utf-8")
            result = driver.drive_stage(
                [sys.executable, str(fake)],
                audit_path=audit,
                stage="main-default",
                expected_mode="default",
                expected_agent=None,
                timeout_seconds=5,
            )
            self.assertEqual(result.marker, EXPECTED[0])
            self.assertLessEqual(result.output_bytes, driver.MAX_TERMINAL_BYTES)
            self.assertEqual(list(root.glob("*.pty")), [])

    @unittest.skipUnless(os.name == "posix", "PTY behavior requires POSIX")
    def test_driver_timeout_is_inconclusive_and_never_active(self) -> None:
        driver = load_driver()
        with tempfile.TemporaryDirectory() as directory:
            result = driver.drive_stage(
                [sys.executable, "-c", "import time; time.sleep(30)"],
                audit_path=Path(directory) / "audit-nonce.jsonl",
                stage="main-default",
                expected_mode="default",
                expected_agent=None,
                timeout_seconds=1,
            )
            self.assertEqual(result.outcome, "INCONCLUSIVE")
            self.assertFalse(result.active)
            self.assertIsNone(result.marker)

    def test_public_evidence_contains_only_bounded_content_free_fields(self) -> None:
        driver = load_driver()
        evidence = driver.public_evidence([
            driver.StageResult("OBSERVED", EXPECTED[0], "DENY_UNKNOWN_COMMAND", True, False, 12),
            driver.StageResult("OBSERVED", EXPECTED[1], "DENY_UNKNOWN_COMMAND", True, False, 13),
            driver.StageResult("OBSERVED", EXPECTED[2], "DENY_UNKNOWN_COMMAND", True, False, 14),
        ], runtime={"claude": "2.1.x", "nori": "0.31.x", "platform": "Linux"})
        self.assertTrue(evidence["complete"])
        self.assertEqual(evidence["observationCount"], 3)
        serialized = json.dumps(evidence, sort_keys=True).lower()
        for forbidden in ("prompt", "transcript", "sessionid", "credential", "token"):
            self.assertNotIn(forbidden, serialized)
        self.assertNotIn("p005_guard_probe", serialized)

    def test_clean_child_environment_uses_a_fixed_allowlist(self) -> None:
        driver = load_driver()
        source = {
            "PATH": "/usr/bin:/bin",
            "HOME": "/tmp/home",
            "CLAUDE_CONFIG_DIR": "/tmp/home/.claude",
            "ANTHROPIC_API_KEY": "synthetic-provider-value",
            "UNRELATED_OPERATOR_SECRET": "must-not-cross",
        }
        child = driver.child_environment(
            source,
            audit_path=Path("/tmp/audit.jsonl"),
            nonce="bounded-nonce",
            clean=True,
        )
        self.assertEqual(child["ANTHROPIC_API_KEY"], "synthetic-provider-value")
        self.assertNotIn("UNRELATED_OPERATOR_SECRET", child)
        self.assertEqual(child["OPS_COMMAND_GUARD_AUDIT_PATH"], str(Path("/tmp/audit.jsonl")))


if __name__ == "__main__":
    unittest.main()
