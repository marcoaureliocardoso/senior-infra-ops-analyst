#!/usr/bin/env python3
"""Static and provider-free safety contract for the P0-04B live harness."""
from __future__ import annotations

import base64
import json
import os
import shlex
import shutil
import subprocess
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "tests" / "live-browser-operations-smoke.sh"
PARSER = ROOT / "tests" / "browser_operations_live.py"
GATE = ROOT / "tests" / "validate-package.sh"


class LiveBrowserOperationSafetyTests(unittest.TestCase):
    ROLES = (
        "audit-evidence-collector", "change-manager", "cloud-platform-operator",
        "database-operator", "diagnostic-operator", "incident-commander",
        "kubernetes-operator", "network-edge-operator", "observability-sre",
        "rca-facilitator", "release-cicd-operator", "security-operations-reviewer",
    )

    @classmethod
    def setUpClass(cls) -> None:
        cls.script = HARNESS.read_text(encoding="utf-8") if HARNESS.is_file() else ""

    def setUp(self) -> None:
        if not HARNESS.is_file() and self._testMethodName != "test_harness_files_exist":
            self.skipTest("live browser harness is not implemented yet")
        isolated_prefixes = (
            "test_local_model_dispatch_probe_",
            "test_provider_free_preflight_",
            "test_live_mode_blocks_",
        )
        if (self._testMethodName.startswith(isolated_prefixes)
                and self._testMethodName
                != "test_local_model_dispatch_probe_requires_os_network_isolation"
                and (os.name != "posix" or shutil.which("bwrap") is None)):
            self.skipTest("Linux/WSL Bubblewrap is required for this isolation test")

    def test_harness_files_exist(self) -> None:
        self.assertTrue(HARNESS.is_file())
        self.assertTrue(PARSER.is_file())

    def test_pty_failure_reason_is_stage_bound_and_content_free(self) -> None:
        import sys
        import tempfile

        sys.path.insert(0, str(ROOT / "tests"))
        import browser_operations_live  # noqa: PLC0415

        self.assertTrue(hasattr(browser_operations_live, "pty_failure_reason"))
        pty_failure_reason = browser_operations_live.pty_failure_reason

        with tempfile.TemporaryDirectory() as directory:
            events = Path(directory) / "events.jsonl"
            events.write_text(
                "\n".join(json.dumps(event) for event in (
                    {"kind": "pty-driver", "stage": "initial_screen", "outcome": "passed"},
                    {"kind": "pty-driver", "stage": "prompt_ready", "outcome": "passed"},
                    {"kind": "pty-driver", "stage": "context_inspected", "outcome": "failed"},
                )) + "\n",
                encoding="utf-8",
            )
            self.assertEqual(
                pty_failure_reason(events),
                "PTY_CONTEXT_INSPECTED_FAILED",
            )
            events.write_text(json.dumps({
                "kind": "pty-driver",
                "stage": "P004B_PROTECTED_VALUE_MUST_NOT_APPEAR",
                "outcome": "failed",
                "content": "untrusted screen text",
            }) + "\n", encoding="utf-8")
            self.assertEqual(pty_failure_reason(events), "PTY_EVIDENCE_REJECTED")

    def test_pty_context_observation_accepts_only_completed_context_dialogue(self) -> None:
        import sys
        import tempfile

        sys.path.insert(0, str(ROOT / "tests"))
        import browser_operations_live  # noqa: PLC0415

        self.assertTrue(hasattr(browser_operations_live, "pty_context_observation"))
        observe = browser_operations_live.pty_context_observation
        with tempfile.TemporaryDirectory() as directory:
            events = Path(directory) / "events.jsonl"
            events.write_text(
                "\n".join(json.dumps(event) for event in (
                    {"kind": "pty-driver", "stage": "initial_screen", "outcome": "passed"},
                    {"kind": "pty-driver", "stage": "trust_selection", "outcome": "passed"},
                    {"kind": "pty-driver", "stage": "prompt_ready", "outcome": "passed"},
                    {"kind": "pty-driver", "stage": "context_inspected", "outcome": "passed", "percent": 7},
                    {"kind": "pty-driver", "stage": "exit", "outcome": "passed"},
                )) + "\n",
                encoding="utf-8",
            )
            self.assertEqual(observe(events, "session-001", "before"), {
                "stage": "before", "sessionId": "session-001", "usedPercentage": 7,
            })
            forced = [
                {"kind": "pty-driver", "stage": "initial_screen", "outcome": "passed"},
                {"kind": "pty-driver", "stage": "prompt_ready", "outcome": "passed"},
                {"kind": "pty-driver", "stage": "context_inspected", "outcome": "passed", "percent": 7},
                {"kind": "pty-driver", "stage": "exit", "outcome": "forced"},
            ]
            events.write_text(
                "\n".join(json.dumps(event) for event in forced) + "\n",
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                observe(events, "session-001", "before")
            events.write_text(json.dumps({
                "kind": "pty-driver", "stage": "context_inspected",
                "outcome": "passed", "percent": 7, "content": "must not escape",
            }) + "\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                observe(events, "session-001", "before")

    def test_pty_failure_reason_allows_structural_context_diagnostics(self) -> None:
        import sys
        import tempfile

        sys.path.insert(0, str(ROOT / "tests"))
        import browser_operations_live  # noqa: PLC0415

        reason = browser_operations_live.pty_failure_reason
        with tempfile.TemporaryDirectory() as directory:
            events = Path(directory) / "events.jsonl"
            for stage in (
                "context_header_missing",
                "context_free_space_missing",
                "context_values_invalid",
                "context_prompt_missing",
                "context_free_value_separated",
                "context_free_value_missing",
                "context_raw_percent_present",
            ):
                events.write_text(json.dumps({
                    "kind": "pty-driver", "stage": stage, "outcome": "failed",
                }) + "\n", encoding="utf-8")
                self.assertEqual(reason(events), f"PTY_{stage.upper()}_FAILED")

    def test_status_context_failure_reason_is_content_free(self) -> None:
        import sys
        import tempfile

        sys.path.insert(0, str(ROOT / "tests"))
        import browser_operations_live  # noqa: PLC0415

        self.assertTrue(hasattr(browser_operations_live, "status_context_failure_reason"))
        reason = browser_operations_live.status_context_failure_reason
        nonce = "p004b-run-001"
        session = "00000000-0000-4000-8000-000000000001"
        stage = "before"
        with tempfile.TemporaryDirectory() as directory:
            events = Path(directory) / "status.jsonl"
            self.assertEqual(
                reason(events, nonce, session, stage), "STATUS_CONTEXT_MISSING"
            )

            events.write_text(json.dumps({
                "kind": "status-context", "percent": 7, "windowTokens": 1_000_000,
                "runNonce": nonce, "stage": stage,
            }) + "\n", encoding="utf-8")
            self.assertEqual(
                reason(events, nonce, session, stage), "STATUS_CONTEXT_AVAILABLE"
            )
            events.write_text(json.dumps({
                "kind": "status-context-unavailable", "runNonce": nonce,
                "stage": stage, "reasonCode": "NATIVE_FIELDS_NOT_SUPPLIED",
            }) + "\n", encoding="utf-8")
            self.assertEqual(
                reason(events, nonce, session, stage),
                "STATUS_CONTEXT_METADATA_UNAVAILABLE",
            )
            unavailable = {
                "kind": "status-context-unavailable", "runNonce": nonce,
                "stage": stage, "reasonCode": "NATIVE_FIELDS_NOT_SUPPLIED",
            }
            numeric = {
                "kind": "status-context", "percent": 8,
                "windowTokens": 1_000_000, "runNonce": nonce, "stage": stage,
            }
            events.write_text(
                json.dumps(unavailable) + "\n" + json.dumps(unavailable) + "\n",
                encoding="utf-8",
            )
            self.assertEqual(
                reason(events, nonce, session, stage),
                "STATUS_CONTEXT_METADATA_UNAVAILABLE",
            )
            events.write_text(
                json.dumps(unavailable) + "\n" + json.dumps(numeric) + "\n",
                encoding="utf-8",
            )
            self.assertEqual(
                browser_operations_live.status_context_observation(
                    events, nonce, session, stage,
                )["usedPercentage"],
                8,
            )
            self.assertEqual(
                reason(events, nonce, session, stage), "STATUS_CONTEXT_AVAILABLE"
            )
            events.write_text(json.dumps({
                "kind": "status-context-rejected", "runNonce": nonce,
                "stage": stage, "reasonCode": "INVALID_STATUS_PAYLOAD",
            }) + "\n", encoding="utf-8")
            self.assertEqual(
                reason(events, nonce, session, stage), "STATUS_CONTEXT_REJECTED"
            )
            events.write_text(json.dumps({
                "kind": "status-context", "percent": 7, "windowTokens": 1_000_000,
                "runNonce": nonce, "stage": stage, "content": "must not escape",
            }) + "\n", encoding="utf-8")
            self.assertEqual(
                reason(events, nonce, session, stage), "STATUS_CONTEXT_REJECTED"
            )

    def test_status_context_observation_rejects_symlinked_evidence(self) -> None:
        import sys
        import tempfile

        sys.path.insert(0, str(ROOT / "tests"))
        import browser_operations_live  # noqa: PLC0415

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target.jsonl"
            linked = root / "linked.jsonl"
            target.write_text(json.dumps({
                "kind": "status-context", "percent": 8,
                "windowTokens": 1_000_000, "runNonce": "p004b-run-001",
                "stage": "before",
            }) + "\n", encoding="utf-8")
            try:
                linked.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation is unavailable")
            with self.assertRaises(ValueError):
                browser_operations_live.status_context_observation(
                    linked, "p004b-run-001",
                    "00000000-0000-4000-8000-000000000001", "before",
                )

    def test_status_context_reason_uses_one_secure_snapshot(self) -> None:
        import sys
        import tempfile

        sys.path.insert(0, str(ROOT / "tests"))
        import browser_operations_live  # noqa: PLC0415

        malformed = ["{not-json"]
        unavailable = [json.dumps({
            "kind": "status-context-unavailable",
            "reasonCode": "NATIVE_FIELDS_NOT_SUPPLIED",
            "runNonce": "p004b-run-001", "stage": "before",
        })]
        with tempfile.TemporaryDirectory() as directory:
            evidence = Path(directory) / "status.jsonl"
            evidence.write_text("placeholder\n", encoding="utf-8")
            with mock.patch.object(
                browser_operations_live, "_read_regular_lines_nofollow",
                side_effect=(malformed, unavailable),
            ) as reader:
                self.assertEqual(
                    browser_operations_live.status_context_failure_reason(
                        evidence, "p004b-run-001",
                        "00000000-0000-4000-8000-000000000001", "before",
                    ),
                    "STATUS_CONTEXT_REJECTED",
                )
                self.assertEqual(reader.call_count, 1)

    def test_regular_evidence_reader_rejects_growth_and_special_files(self) -> None:
        import sys
        import tempfile

        sys.path.insert(0, str(ROOT / "tests"))
        import browser_operations_live  # noqa: PLC0415

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence = root / "evidence.jsonl"
            evidence.write_bytes(b"x" * browser_operations_live.MAX_STATUS_CONTEXT_BYTES)
            real_read = browser_operations_live.os.read
            appended = False

            def append_then_read(descriptor, count):
                nonlocal appended
                if not appended:
                    appended = True
                    with evidence.open("ab") as stream:
                        stream.write(b"x")
                return real_read(descriptor, count)

            with mock.patch.object(
                browser_operations_live.os, "read", side_effect=append_then_read,
            ):
                with self.assertRaises(ValueError):
                    browser_operations_live._read_regular_lines_nofollow(
                        evidence, browser_operations_live.MAX_STATUS_CONTEXT_BYTES,
                    )

            reason = browser_operations_live.status_context_failure_reason
            self.assertEqual(
                reason(root, "p004b-run-001",
                       "00000000-0000-4000-8000-000000000001", "before"),
                "STATUS_CONTEXT_REJECTED",
            )
            if hasattr(os, "mkfifo"):
                fifo = root / "evidence.fifo"
                os.mkfifo(fifo)
                self.assertEqual(
                    reason(fifo, "p004b-run-001",
                           "00000000-0000-4000-8000-000000000001", "before"),
                    "STATUS_CONTEXT_REJECTED",
                )

    def test_regular_evidence_reader_cannot_block_on_fifo_replacement(self) -> None:
        import sys
        import tempfile

        sys.path.insert(0, str(ROOT / "tests"))
        import browser_operations_live  # noqa: PLC0415

        nonblocking = getattr(os, "O_NONBLOCK", 0)
        if not nonblocking or not hasattr(os, "mkfifo"):
            self.skipTest("nonblocking FIFO support is unavailable")
        with tempfile.TemporaryDirectory() as directory:
            evidence = Path(directory) / "evidence.jsonl"
            evidence.write_text("placeholder\n", encoding="utf-8")
            real_open = browser_operations_live.os.open

            def replace_with_fifo(path, flags):
                if not flags & nonblocking:
                    raise AssertionError("evidence open is allowed to block")
                evidence.unlink()
                os.mkfifo(evidence)
                return real_open(path, flags)

            with mock.patch.object(
                browser_operations_live.os, "open", side_effect=replace_with_fifo,
            ):
                with self.assertRaises(ValueError):
                    browser_operations_live._read_regular_lines_nofollow(
                        evidence, browser_operations_live.MAX_STATUS_CONTEXT_BYTES,
                    )

    def test_empty_status_evidence_uses_one_secure_snapshot(self) -> None:
        import sys
        import tempfile

        sys.path.insert(0, str(ROOT / "tests"))
        import browser_operations_live  # noqa: PLC0415

        with tempfile.TemporaryDirectory() as directory:
            evidence = Path(directory) / "status.jsonl"
            evidence.touch()
            with mock.patch.object(
                browser_operations_live, "_read_regular_lines_nofollow",
                wraps=browser_operations_live._read_regular_lines_nofollow,
            ) as reader:
                self.assertEqual(
                    browser_operations_live.status_context_failure_reason(
                        evidence, "p004b-run-001",
                        "00000000-0000-4000-8000-000000000001", "before",
                    ),
                    "STATUS_CONTEXT_MISSING",
                )
                self.assertEqual(reader.call_count, 1)

    def test_claude_failure_reason_reduces_allowlisted_categories(self) -> None:
        import sys
        import tempfile

        sys.path.insert(0, str(ROOT / "tests"))
        import browser_operations_live  # noqa: PLC0415

        cases = (
            (124, True, "API Error: 401 authentication_error", "CLAUDE_TIMEOUT"),
            (124, False, "unrecognized diagnostic text", "CLAUDE_PROCESS_FAILED"),
            (1, False, "API Error: 401 authentication_error", "CLAUDE_AUTH_FAILURE"),
            (1, False, "API Error: 429 rate_limit_error", "CLAUDE_RATE_LIMIT"),
            (1, False, "API Error: 404 model_not_found", "CLAUDE_PROVIDER_MODEL_FAILURE"),
            (1, False, '[claude-code:unrecognized_model] {"model":"deepseek-v4-pro[1m]","query_source":"sdk"}', "CLAUDE_MODEL_ROUTE_ADVISORY"),
            (1, False, "TypeError: fetch failed ECONNREFUSED", "CLAUDE_TRANSPORT_FAILURE"),
            (2, False, "error: unknown option --not-real", "CLAUDE_CONTRACT_FAILURE"),
            (1, False, "ModuleNotFoundError: no module named example", "CLAUDE_RUNTIME_FAILURE"),
            (1, False, "unrecognized diagnostic text", "CLAUDE_PROCESS_FAILED"),
        )
        with tempfile.TemporaryDirectory() as directory:
            transcript = Path(directory) / "stage.transcript"
            for status, timed_out, content, expected in cases:
                with self.subTest(expected=expected):
                    transcript.write_text(content, encoding="utf-8")
                    self.assertEqual(
                        browser_operations_live.claude_failure_reason(
                            status, timed_out, transcript,
                        ),
                        expected,
                    )

    def test_claude_failure_reason_adds_content_free_process_fingerprint(self) -> None:
        import sys
        import tempfile

        sys.path.insert(0, str(ROOT / "tests"))
        import browser_operations_live  # noqa: PLC0415

        canary = "SYNTH_SECRET_P004B_STREAM_CANARY"
        cases = (
            ("", "EMPTY"),
            ('{"type":"system","secret":"' + canary + '"}\n', "SYSTEM"),
            ('{"type":"assistant","secret":"' + canary + '"}\n', "ASSISTANT"),
            ('{"type":"result","is_error":false,"result":"' + canary + '"}\n', "RESULT"),
            ('{"type":"result","is_error":true,"result":"' + canary + '"}\n', "RESULT_ERROR"),
            ("not-json " + canary + "\n", "INVALID"),
            ('{"type":"system","number":' + "9" * 5000 + '}\n', "INVALID"),
            ('{"type":"system","nested":' + "[" * 1100 + "0" + "]" * 1100 + '}\n', "INVALID"),
            ('{"type":"unknown","secret":"' + canary + '"}\n', "OTHER"),
        )
        with tempfile.TemporaryDirectory() as directory:
            transcript = Path(directory) / "stage.transcript"
            stream = Path(directory) / "stage.stream.jsonl"
            transcript.write_text("unrecognized diagnostic text", encoding="utf-8")
            for content, expected_state in cases:
                with self.subTest(expected_state=expected_state):
                    stream.write_text(content, encoding="utf-8")
                    reason = browser_operations_live.claude_failure_reason(
                        1, False, transcript, stream,
                    )
                    self.assertEqual(
                        reason,
                        f"CLAUDE_PROCESS_FAILED_EXIT_1_STREAM_{expected_state}",
                    )
                    self.assertNotIn(canary, reason)

    def test_claude_timeout_adds_content_free_stream_fingerprint(self) -> None:
        import sys
        import tempfile

        sys.path.insert(0, str(ROOT / "tests"))
        import browser_operations_live  # noqa: PLC0415

        canary = "SYNTH_SECRET_P004B_TIMEOUT_CANARY"
        cases = (
            ("", "EMPTY"),
            ('{"type":"system","secret":"' + canary + '"}\n', "SYSTEM"),
            ('{"type":"assistant","secret":"' + canary + '"}\n', "ASSISTANT"),
            ('{"type":"result","is_error":false,"result":"' + canary + '"}\n', "RESULT"),
            ('{"type":"result","is_error":true,"result":"' + canary + '"}\n', "RESULT_ERROR"),
            ("not-json " + canary + "\n", "INVALID"),
            ('{"type":"unknown","secret":"' + canary + '"}\n', "OTHER"),
        )
        with tempfile.TemporaryDirectory() as directory:
            transcript = Path(directory) / "stage.transcript"
            stream = Path(directory) / "stage.stream.jsonl"
            transcript.write_text("unrecognized diagnostic text", encoding="utf-8")
            for content, expected_state in cases:
                with self.subTest(expected_state=expected_state):
                    stream.write_text(content, encoding="utf-8")
                    reason = browser_operations_live.claude_failure_reason(
                        124, True, transcript, stream,
                    )
                    self.assertEqual(
                        reason,
                        f"CLAUDE_TIMEOUT_STREAM_{expected_state}",
                    )
                    self.assertNotIn(canary, reason)

    def test_claude_stream_fingerprint_enforces_exact_json_boundaries(self) -> None:
        import sys
        import tempfile

        sys.path.insert(0, str(ROOT / "tests"))
        import browser_operations_live  # noqa: PLC0415

        cases = (
            ('{"type":"system","number":' + "9" * 128 + '}\n', "SYSTEM"),
            ('{"type":"system","number":' + "9" * 129 + '}\n', "INVALID"),
            ('{"type":"system","nested":' + "[" * 63 + "0" + "]" * 63 + '}\n', "SYSTEM"),
            ('{"type":"system","nested":' + "[" * 64 + "0" + "]" * 64 + '}\n', "INVALID"),
            ('{"type":"system","items":[' + ",".join("0" for _ in range(4093)) + ']}\n', "SYSTEM"),
            ('{"type":"system","items":[' + ",".join("0" for _ in range(4094)) + ']}\n', "INVALID"),
        )
        with tempfile.TemporaryDirectory() as directory:
            transcript = Path(directory) / "stage.transcript"
            stream = Path(directory) / "stage.stream.jsonl"
            transcript.write_text("unrecognized diagnostic text", encoding="utf-8")
            for index, (content, expected_state) in enumerate(cases):
                with self.subTest(index=index, expected_state=expected_state):
                    stream.write_text(content, encoding="utf-8")
                    self.assertEqual(
                        browser_operations_live.claude_failure_reason(
                            124, True, transcript, stream,
                        ),
                        f"CLAUDE_TIMEOUT_STREAM_{expected_state}",
                    )

    def test_claude_timeout_rejects_unsafe_stream_evidence(self) -> None:
        import sys
        import tempfile

        sys.path.insert(0, str(ROOT / "tests"))
        import browser_operations_live  # noqa: PLC0415

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            transcript = root / "stage.transcript"
            transcript.write_text("unrecognized diagnostic text", encoding="utf-8")
            missing = root / "missing.stream"
            self.assertEqual(
                browser_operations_live.claude_failure_reason(
                    124, True, transcript, missing,
                ),
                "CLAUDE_EVIDENCE_REJECTED_INPUT",
            )
            oversized = root / "oversized.stream"
            oversized.write_bytes(
                b"x" * (browser_operations_live.MAX_CLAUDE_FAILURE_BYTES + 1)
            )
            self.assertEqual(
                browser_operations_live.claude_failure_reason(
                    124, True, transcript, oversized,
                ),
                "CLAUDE_EVIDENCE_REJECTED_INPUT",
            )
            target = root / "target.stream"
            target.write_text('{"type":"system"}\n', encoding="utf-8")
            linked = root / "linked.stream"
            try:
                linked.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation is unavailable")
            self.assertEqual(
                browser_operations_live.claude_failure_reason(
                    124, True, transcript, linked,
                ),
                "CLAUDE_EVIDENCE_REJECTED_INPUT",
            )

    def test_claude_failure_reason_cli_emits_structural_fingerprint(self) -> None:
        import sys
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            transcript = Path(directory) / "stage.transcript"
            stream = Path(directory) / "stage.stream.jsonl"
            transcript.write_text("unrecognized diagnostic text", encoding="utf-8")
            stream.write_text('{"type":"result","is_error":true}\n', encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable, str(PARSER), "--claude-failure-reason",
                    "1", "0", str(transcript), str(stream),
                ],
                check=False, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                result.stdout,
                "CLAUDE_PROCESS_FAILED_EXIT_1_STREAM_RESULT_ERROR\n",
            )
            self.assertEqual(result.stderr, "")

    def test_local_model_dispatch_probe_uses_only_sanitized_loopback_runtime(self) -> None:
        import sys
        import tempfile

        sys.path.insert(0, str(ROOT / "tests"))
        import browser_operations_live  # noqa: PLC0415

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            fake = root / "fake-claude"
            fake.write_text(
                """#!/usr/bin/env python3
import json, os, sys, urllib.request
required = {
    "ANTHROPIC_API_KEY": "P004B_LOCAL_ONLY",
    "ANTHROPIC_AUTH_TOKEN": "P004B_LOCAL_ONLY",
    "ANTHROPIC_MODEL": "deepseek-v4-pro[1m]",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
}
if any(os.environ.get(key) != value for key, value in required.items()):
    raise SystemExit(41)
if ("P004B_PARENT_SECRET" in os.environ
        or os.environ["HOME"] != "/opt/p004b/work/model-preflight/home"):
    raise SystemExit(42)
if "--bare" not in sys.argv or "--settings" in sys.argv or "--no-session-persistence" not in sys.argv:
    raise SystemExit(43)
request = urllib.request.Request(
    os.environ["ANTHROPIC_BASE_URL"] + "/v1/messages",
    data=json.dumps({"model": os.environ["ANTHROPIC_MODEL"]}).encode(),
    headers={"content-type": "application/json"}, method="POST",
)
try:
    urllib.request.urlopen(request, timeout=2)
except Exception:
    pass
raise SystemExit(1)
""",
                encoding="utf-8",
            )
            fake.chmod(0o700)
            with mock.patch.dict(os.environ, {"P004B_PARENT_SECRET": "must-not-cross"}):
                self.assertEqual(
                    browser_operations_live.probe_local_model_dispatch(
                        fake, "deepseek-v4-pro[1m]", root,
                    ),
                    "LOCAL_MODEL_REQUEST_OBSERVED",
                )
            self.assertFalse((root / "model-preflight").exists())

    def test_local_model_dispatch_probe_blocks_non_loopback_proxy_target(self) -> None:
        import sys
        import tempfile

        sys.path.insert(0, str(ROOT / "tests"))
        import browser_operations_live  # noqa: PLC0415

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            fake = root / "fake-claude"
            fake.write_text(
                """#!/usr/bin/env python3
import http.client, os
from urllib.parse import urlsplit
proxy = urlsplit(os.environ["HTTPS_PROXY"])
connection = http.client.HTTPConnection(proxy.hostname, proxy.port, timeout=2)
connection.request("CONNECT", "api.deepseek.com:443")
try:
    connection.getresponse()
except Exception:
    pass
raise SystemExit(1)
""",
                encoding="utf-8",
            )
            fake.chmod(0o700)
            self.assertEqual(
                browser_operations_live.probe_local_model_dispatch(
                    fake, "deepseek-v4-pro[1m]", root,
                ),
                "MODEL_PREFLIGHT_ISOLATION_FAILURE",
            )

    def test_local_model_dispatch_probe_os_boundary_blocks_proxy_bypass(self) -> None:
        import socket
        import sys
        import tempfile
        import threading

        sys.path.insert(0, str(ROOT / "tests"))
        import browser_operations_live  # noqa: PLC0415

        listener = socket.socket()
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.2", 0))
        listener.listen(1)
        listener.settimeout(3)
        host_port = listener.getsockname()[1]
        accepted: list[bool] = []

        def accept_once() -> None:
            try:
                connection, _address = listener.accept()
            except (TimeoutError, OSError):
                return
            with connection:
                accepted.append(True)

        thread = threading.Thread(target=accept_once, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                marker = root / "bypass-result"
                fake = root / "fake-claude"
                fake.write_text(
                    f"""#!/usr/bin/env python3
import json, os, pathlib, socket, urllib.request
request = urllib.request.Request(
    os.environ["ANTHROPIC_BASE_URL"] + "/v1/messages",
    data=json.dumps({{"model": os.environ["ANTHROPIC_MODEL"]}}).encode(),
    headers={{"content-type": "application/json"}}, method="POST",
)
try:
    urllib.request.urlopen(request, timeout=2)
except Exception:
    pass
probe = socket.socket()
probe.settimeout(1)
status = probe.connect_ex(("127.0.0.2", {host_port}))
probe.close()
(pathlib.Path.cwd().parents[1] / "bypass-result").write_text(
    "blocked" if status else "connected", encoding="utf-8"
)
raise SystemExit(1)
""",
                    encoding="utf-8",
                )
                fake.chmod(0o700)
                self.assertEqual(
                    browser_operations_live.probe_local_model_dispatch(
                        fake, "sonnet", root,
                    ),
                    "LOCAL_MODEL_REQUEST_OBSERVED",
                )
                self.assertEqual(marker.read_text(encoding="utf-8"), "blocked")
        finally:
            listener.close()
            thread.join(timeout=4)
        self.assertEqual(accepted, [])

    def test_local_model_dispatch_probe_requires_os_network_isolation(self) -> None:
        import sys
        import tempfile

        sys.path.insert(0, str(ROOT / "tests"))
        import browser_operations_live  # noqa: PLC0415

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            fake = root / "fake-claude"
            fake.write_text("#!/usr/bin/env python3\nraise SystemExit(0)\n", encoding="utf-8")
            fake.chmod(0o700)
            with mock.patch.object(browser_operations_live.shutil, "which", return_value=None):
                self.assertEqual(
                    browser_operations_live.probe_local_model_dispatch(
                        fake, "sonnet", root,
                    ),
                    "MODEL_PREFLIGHT_ISOLATION_UNAVAILABLE",
                )

    def test_local_model_dispatch_probe_hides_host_secret_and_unix_socket(self) -> None:
        import socket
        import sys
        import tempfile
        import threading

        sys.path.insert(0, str(ROOT / "tests"))
        import browser_operations_live  # noqa: PLC0415

        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            work = base / "work"
            work.mkdir()
            secret = base / "operator-credential"
            secret.write_text("P004B_HOST_SECRET", encoding="utf-8")
            socket_path = base / "host.sock"
            listener = socket.socket(socket.AF_UNIX)
            listener.bind(str(socket_path))
            listener.listen(1)
            listener.settimeout(3)
            accepted: list[bool] = []

            def accept_once() -> None:
                try:
                    connection, _address = listener.accept()
                except (TimeoutError, OSError):
                    return
                with connection:
                    accepted.append(True)

            thread = threading.Thread(target=accept_once, daemon=True)
            thread.start()
            marker = work / "filesystem-boundary"
            fake = work / "fake-claude"
            fake.write_text(
                f"""#!/usr/bin/env python3
import json, os, pathlib, socket, urllib.request
secret_visible = pathlib.Path({str(secret)!r}).is_file()
system_file_visible = pathlib.Path("/etc/hostname").is_file()
channel = socket.socket(socket.AF_UNIX)
try:
    channel.connect({str(socket_path)!r})
    socket_connected = True
except OSError:
    socket_connected = False
finally:
    channel.close()
request = urllib.request.Request(
    os.environ["ANTHROPIC_BASE_URL"] + "/v1/messages",
    data=json.dumps({{"model": os.environ["ANTHROPIC_MODEL"]}}).encode(),
    headers={{"content-type": "application/json"}}, method="POST",
)
try:
    urllib.request.urlopen(request, timeout=2)
except Exception:
    pass
(pathlib.Path.cwd().parents[1] / "filesystem-boundary").write_text(
    f"{{int(secret_visible)}}:{{int(socket_connected)}}:{{int(system_file_visible)}}",
    encoding="utf-8",
)
raise SystemExit(1)
""",
                encoding="utf-8",
            )
            fake.chmod(0o700)
            try:
                self.assertEqual(
                    browser_operations_live.probe_local_model_dispatch(
                        fake, "sonnet", work,
                    ),
                    "LOCAL_MODEL_REQUEST_OBSERVED",
                )
                self.assertEqual(marker.read_text(encoding="utf-8"), "0:0:0")
            finally:
                listener.close()
                thread.join(timeout=4)
            self.assertEqual(accepted, [])

    def test_local_model_dispatch_probe_does_not_treat_warning_as_dispatch(self) -> None:
        import sys
        import tempfile

        sys.path.insert(0, str(ROOT / "tests"))
        import browser_operations_live  # noqa: PLC0415

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            fake = root / "fake-claude"
            fake.write_text(
                """#!/usr/bin/env python3
import sys
sys.stderr.write('[claude-code:unrecognized_model] {"model":"deepseek-v4-pro[1m]","query_source":"sdk"}\\n')
raise SystemExit(1)
""",
                encoding="utf-8",
            )
            fake.chmod(0o700)
            self.assertEqual(
                browser_operations_live.probe_local_model_dispatch(
                    fake, "deepseek-v4-pro[1m]", root,
                ),
                "MODEL_DISPATCH_UNPROVEN",
            )

    def test_local_model_dispatch_probe_distinguishes_non_message_loopback_traffic(self) -> None:
        import sys
        import tempfile

        sys.path.insert(0, str(ROOT / "tests"))
        import browser_operations_live  # noqa: PLC0415

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            fake = root / "fake-claude"
            fake.write_text(
                """#!/usr/bin/env python3
import os, urllib.request
try:
    urllib.request.urlopen(os.environ["ANTHROPIC_BASE_URL"] + "/v1/models", timeout=2)
except Exception:
    pass
raise SystemExit(1)
""",
                encoding="utf-8",
            )
            fake.chmod(0o700)
            self.assertEqual(
                browser_operations_live.probe_local_model_dispatch(
                    fake, "sonnet", root,
                ),
                "LOCAL_NON_MESSAGE_REQUEST_OBSERVED",
            )

    def test_local_model_dispatch_probe_rejects_observed_request_after_timeout(self) -> None:
        import sys
        import tempfile

        sys.path.insert(0, str(ROOT / "tests"))
        import browser_operations_live  # noqa: PLC0415

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            fake = root / "fake-claude"
            fake.write_text(
                """#!/usr/bin/env python3
import json, os, time, urllib.request
request = urllib.request.Request(
    os.environ["ANTHROPIC_BASE_URL"] + "/v1/messages?beta=true",
    data=json.dumps({"model": os.environ["ANTHROPIC_MODEL"]}).encode(),
    headers={"content-type": "application/json"}, method="POST",
)
try:
    urllib.request.urlopen(request, timeout=2)
except Exception:
    pass
time.sleep(5)
""",
                encoding="utf-8",
            )
            fake.chmod(0o700)
            self.assertEqual(
                browser_operations_live.probe_local_model_dispatch(
                    fake, "sonnet", root, timeout_seconds=0.5,
                ),
                "MODEL_PREFLIGHT_TIMEOUT",
            )

    def test_local_model_dispatch_probe_terminates_descendants_after_timeout(self) -> None:
        import sys
        import tempfile
        import time

        sys.path.insert(0, str(ROOT / "tests"))
        import browser_operations_live  # noqa: PLC0415

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            fake = root / "fake-claude"
            marker = root / "orphan-marker"
            fake.write_text(
                """#!/usr/bin/env python3
import json, os, pathlib, subprocess, sys, time, urllib.request
request = urllib.request.Request(
    os.environ["ANTHROPIC_BASE_URL"] + "/v1/messages",
    data=json.dumps({"model": os.environ["ANTHROPIC_MODEL"]}).encode(),
    headers={"content-type": "application/json"}, method="POST",
)
try:
    urllib.request.urlopen(request, timeout=2)
except Exception:
    pass
marker = pathlib.Path.cwd().parents[1] / "orphan-marker"
subprocess.Popen([
    sys.executable, "-c",
    "import pathlib,sys,time; time.sleep(1); pathlib.Path(sys.argv[1]).write_text('survived')",
    str(marker),
])
time.sleep(5)
""",
                encoding="utf-8",
            )
            fake.chmod(0o700)
            self.assertEqual(
                browser_operations_live.probe_local_model_dispatch(
                    fake, "sonnet", root, timeout_seconds=0.25,
                ),
                "MODEL_PREFLIGHT_TIMEOUT",
            )
            time.sleep(1.25)
            self.assertFalse(marker.exists(), "timed-out preflight left a live descendant")

    def test_local_model_dispatch_probe_cleans_namespace_after_sigterm(self) -> None:
        import signal
        import sys
        import tempfile
        import time

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            started = root / "started"
            survivor = root / "survived"
            fake = root / "fake-claude"
            fake.write_text(
                """#!/usr/bin/env python3
import pathlib, subprocess, sys, time
root = pathlib.Path.cwd().parents[1]
(root / "started").write_text("yes", encoding="utf-8")
subprocess.Popen([
    sys.executable, "-c",
    "import pathlib,sys,time; time.sleep(1); pathlib.Path(sys.argv[1]).write_text('yes')",
    str(root / "survived"),
], start_new_session=True)
time.sleep(30)
""",
                encoding="utf-8",
            )
            fake.chmod(0o700)
            process = subprocess.Popen(
                [
                    sys.executable, str(PARSER), "--probe-local-model-dispatch",
                    str(fake), "sonnet", str(root),
                ],
                cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True,
            )
            deadline = time.monotonic() + 5
            while not started.exists() and time.monotonic() < deadline:
                time.sleep(0.05)
            self.assertTrue(started.exists(), "isolated probe did not start")
            process.send_signal(signal.SIGTERM)
            stdout, stderr = process.communicate(timeout=5)
            self.assertEqual(process.returncode, 0, stderr)
            self.assertEqual(stdout.strip(), "MODEL_PREFLIGHT_INTERRUPTED")
            time.sleep(1.25)
            self.assertFalse(survivor.exists(), "interrupted namespace left a detached descendant")
            self.assertFalse((root / "model-preflight").exists())

    def test_local_model_dispatch_probe_accepts_repeated_matching_local_retries(self) -> None:
        import sys
        import tempfile

        sys.path.insert(0, str(ROOT / "tests"))
        import browser_operations_live  # noqa: PLC0415

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            fake = root / "fake-claude"
            fake.write_text(
                """#!/usr/bin/env python3
import json, os, urllib.request
for _attempt in range(2):
    request = urllib.request.Request(
        os.environ["ANTHROPIC_BASE_URL"] + "/v1/messages?beta=true",
        data=json.dumps({"model": os.environ["ANTHROPIC_MODEL"]}).encode(),
        headers={"content-type": "application/json"}, method="POST",
    )
    try:
        urllib.request.urlopen(request, timeout=2)
    except Exception:
        pass
raise SystemExit(1)
""",
                encoding="utf-8",
            )
            fake.chmod(0o700)
            self.assertEqual(
                browser_operations_live.probe_local_model_dispatch(
                    fake, "sonnet", root,
                ),
                "LOCAL_MODEL_REQUEST_OBSERVED",
            )

    def test_local_model_dispatch_probe_accepts_matching_message_with_local_auxiliary_traffic(self) -> None:
        import sys
        import tempfile

        sys.path.insert(0, str(ROOT / "tests"))
        import browser_operations_live  # noqa: PLC0415

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            fake = root / "fake-claude"
            fake.write_text(
                """#!/usr/bin/env python3
import json, os, urllib.request
try:
    urllib.request.urlopen(os.environ["ANTHROPIC_BASE_URL"] + "/v1/models", timeout=2)
except Exception:
    pass
request = urllib.request.Request(
    os.environ["ANTHROPIC_BASE_URL"] + "/v1/messages?beta=true",
    data=json.dumps({"model": os.environ["ANTHROPIC_MODEL"]}).encode(),
    headers={"content-type": "application/json"}, method="POST",
)
try:
    urllib.request.urlopen(request, timeout=2)
except Exception:
    pass
raise SystemExit(1)
""",
                encoding="utf-8",
            )
            fake.chmod(0o700)
            self.assertEqual(
                browser_operations_live.probe_local_model_dispatch(
                    fake, "sonnet", root,
                ),
                "LOCAL_MODEL_REQUEST_OBSERVED",
            )

    def test_local_model_dispatch_probe_reports_model_mismatch_without_value(self) -> None:
        import sys
        import tempfile

        sys.path.insert(0, str(ROOT / "tests"))
        import browser_operations_live  # noqa: PLC0415

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            fake = root / "fake-claude"
            fake.write_text(
                """#!/usr/bin/env python3
import json, os, urllib.request
request = urllib.request.Request(
    os.environ["ANTHROPIC_BASE_URL"] + "/v1/messages?beta=true",
    data=json.dumps({"model": "P004B_UNEXPECTED_MODEL_MUST_NOT_ESCAPE"}).encode(),
    headers={"content-type": "application/json"}, method="POST",
)
try:
    urllib.request.urlopen(request, timeout=2)
except Exception:
    pass
raise SystemExit(1)
""",
                encoding="utf-8",
            )
            fake.chmod(0o700)
            result = browser_operations_live.probe_local_model_dispatch(
                fake, "sonnet", root,
            )
            self.assertEqual(result, "LOCAL_MODEL_MISMATCH_OBSERVED")
            self.assertNotIn("UNEXPECTED", result)

    def test_local_model_dispatch_probe_reports_claude_opus_route_without_version(self) -> None:
        import sys
        import tempfile

        sys.path.insert(0, str(ROOT / "tests"))
        import browser_operations_live  # noqa: PLC0415

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            fake = root / "fake-claude"
            fake.write_text(
                """#!/usr/bin/env python3
import json, os, urllib.request
request = urllib.request.Request(
    os.environ["ANTHROPIC_BASE_URL"] + "/v1/messages?beta=true",
    data=json.dumps({"model": "claude-opus-4-6"}).encode(),
    headers={"content-type": "application/json"}, method="POST",
)
try:
    urllib.request.urlopen(request, timeout=2)
except Exception:
    pass
raise SystemExit(1)
""",
                encoding="utf-8",
            )
            fake.chmod(0o700)
            result = browser_operations_live.probe_local_model_dispatch(
                fake, "deepseek-v4-pro[1m]", root,
            )
            self.assertEqual(result, "LOCAL_MODEL_CLAUDE_OPUS_ROUTE_OBSERVED")
            self.assertNotIn("4-6", result)

    def test_provider_free_preflight_does_not_probe_model_dispatch(self) -> None:
        import tempfile

        bash = shutil.which("bash")
        node = shutil.which("node")
        if not bash or not node:
            self.skipTest("bash and node are required for the provider-free preflight")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            marker = root / "claude-invoked"
            fake = root / "fake-claude"
            fake.write_text(
                f"#!/usr/bin/env sh\nprintf invoked >'{marker}'\nexit 1\n",
                encoding="utf-8",
            )
            fake.chmod(0o700)
            env = {
                **os.environ,
                "CLAUDE_BIN": str(fake),
                "NODE_BIN": node,
                "ANTHROPIC_BASE_URL": "https://api.deepseek.com/anthropic",
                "ANTHROPIC_MODEL": "deepseek-v4-pro[1m]",
            }
            result = subprocess.run(
                [bash, str(HARNESS), "--preflight"], cwd=ROOT, env=env,
                check=False, capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            aggregate = json.loads(result.stdout)
            self.assertIn(
                aggregate["reasonCode"],
                {"PREFLIGHT_READY", "PREFLIGHT_ADAPTER_UNAVAILABLE", "PREFLIGHT_ADAPTER_CONFLICT"},
            )
            self.assertNotIn("MODEL", aggregate["reasonCode"])
            self.assertFalse(marker.exists())
            self.assertEqual(aggregate["cleanup"], "verified")

    def test_provider_free_preflight_never_runs_unisolated_claude_version(self) -> None:
        import socket
        import tempfile
        import threading

        bash = shutil.which("bash")
        node = shutil.which("node")
        if not bash or not node:
            self.skipTest("bash and node are required for the provider-free preflight")
        listener = socket.socket()
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.2", 0))
        listener.listen(1)
        listener.settimeout(3)
        host_port = listener.getsockname()[1]
        accepted: list[bool] = []

        def accept_once() -> None:
            try:
                connection, _address = listener.accept()
            except (TimeoutError, OSError):
                return
            with connection:
                accepted.append(True)

        thread = threading.Thread(target=accept_once, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                version_marker = root / "version-network"
                fake = root / "fake-claude"
                fake.write_text(
                    f"""#!/usr/bin/env python3
import json, os, pathlib, socket, sys, urllib.request
if "--version" in sys.argv:
    probe = socket.socket()
    probe.settimeout(1)
    status = probe.connect_ex(("127.0.0.2", {host_port}))
    probe.close()
    if not status:
        pathlib.Path({str(version_marker)!r}).write_text("connected", encoding="utf-8")
    print("p004b-fake-claude")
    raise SystemExit(0)
request = urllib.request.Request(
    os.environ["ANTHROPIC_BASE_URL"] + "/v1/messages",
    data=json.dumps({{"model": os.environ["ANTHROPIC_MODEL"]}}).encode(),
    headers={{"content-type": "application/json"}}, method="POST",
)
try:
    urllib.request.urlopen(request, timeout=2)
except Exception:
    pass
raise SystemExit(1)
""",
                    encoding="utf-8",
                )
                fake.chmod(0o700)
                env = {
                    **os.environ,
                    "CLAUDE_BIN": str(fake),
                    "NODE_BIN": node,
                    "ANTHROPIC_BASE_URL": "https://api.deepseek.com/anthropic",
                    "ANTHROPIC_MODEL": "sonnet",
                }
                result = subprocess.run(
                    [bash, str(HARNESS), "--preflight"], cwd=ROOT, env=env,
                    check=False, capture_output=True, text=True, timeout=30,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertFalse(version_marker.exists())
        finally:
            listener.close()
            thread.join(timeout=4)
        self.assertEqual(accepted, [])

    def test_model_dispatch_diagnostic_is_explicit_and_not_an_acceptance_gate(self) -> None:
        diagnostic = ROOT / "tests" / "browser_operations_live.py"
        self.assertIn("--probe-local-model-dispatch", diagnostic.read_text(encoding="utf-8"))
        self.assertNotIn("--probe-local-model-dispatch", self.script)
        self.assertNotIn("MODEL_DISPATCH_STATE", self.script)
        self.assertNotIn("inline live model gate", self.script)

    def test_live_mode_requires_operator_bound_provider_endpoint(self) -> None:
        bash = shutil.which("bash")
        if not bash:
            self.skipTest("bash is required")
        env = {
            **os.environ,
            "ANTHROPIC_BASE_URL": "https://api.deepseek.com/anthropic",
            "P004B_LIVE_AUTHORIZED": "1",
            "P004B_LIVE_ACK": "I_ACKNOWLEDGE_BOUNDED_SYNTHETIC_BROWSER_PROBES",
            "P004B_AUTHORIZED_TOP_LEVEL_INVOCATIONS": "6",
            "P004B_AUTHORIZED_MAX_MODEL_TURNS": "40",
        }
        env.pop("P004B_AUTHORIZED_PROVIDER_ENDPOINT", None)
        result = subprocess.run(
            [bash, str(HARNESS), "--run-live"], cwd=ROOT, env=env,
            check=False, capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertEqual(
            result.stderr.strip(),
            "BLOCKED: P004B_AUTHORIZED_PROVIDER_ENDPOINT is required",
        )

    def test_live_mode_rejects_provider_endpoint_mismatch_before_dependencies(self) -> None:
        bash = shutil.which("bash")
        if not bash:
            self.skipTest("bash is required")
        env = {
            **os.environ,
            "ANTHROPIC_BASE_URL": "https://api.deepseek.com/anthropic",
            "P004B_AUTHORIZED_PROVIDER_ENDPOINT": "https://other.example/anthropic",
            "P004B_LIVE_AUTHORIZED": "1",
            "P004B_LIVE_ACK": "I_ACKNOWLEDGE_BOUNDED_SYNTHETIC_BROWSER_PROBES",
            "P004B_AUTHORIZED_TOP_LEVEL_INVOCATIONS": "6",
            "P004B_AUTHORIZED_MAX_MODEL_TURNS": "40",
        }
        result = subprocess.run(
            [bash, str(HARNESS), "--run-live"], cwd=ROOT, env=env,
            check=False, capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertEqual(
            result.stderr.strip(),
            "BLOCKED: configured provider endpoint does not match operator authorization",
        )

    def test_live_mode_requires_bounded_https_provider_endpoint(self) -> None:
        bash = shutil.which("bash")
        if not bash:
            self.skipTest("bash is required")
        base = {
            **os.environ,
            "P004B_LIVE_AUTHORIZED": "1",
            "P004B_LIVE_ACK": "I_ACKNOWLEDGE_BOUNDED_SYNTHETIC_BROWSER_PROBES",
            "P004B_AUTHORIZED_TOP_LEVEL_INVOCATIONS": "6",
            "P004B_AUTHORIZED_MAX_MODEL_TURNS": "40",
        }
        invalid = (
            "http://api.deepseek.com/anthropic",
            "https://user@api.deepseek.com/anthropic",
            "https://api.deepseek.com/anthropic?route=other",
            "https://api.deepseek.com/anthropic#other",
            "https://api.deepseek.com/anthropic path",
            "https:///anthropic",
            "https://" + "a" * 505,
            "https://a/" + "é" * 252,
        )
        for endpoint in invalid:
            with self.subTest(endpoint=endpoint):
                env = {
                    **base,
                    "ANTHROPIC_BASE_URL": endpoint,
                    "P004B_AUTHORIZED_PROVIDER_ENDPOINT": endpoint,
                }
                result = subprocess.run(
                    [bash, str(HARNESS), "--run-live"], cwd=ROOT, env=env,
                    check=False, capture_output=True, text=True, timeout=10,
                )
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertEqual(
                    result.stderr.strip(),
                    "BLOCKED: authorized provider endpoint must be a bounded HTTPS URL without credentials, query, or fragment",
                )

    def test_claude_failure_reason_never_returns_content(self) -> None:
        import sys
        import tempfile

        sys.path.insert(0, str(ROOT / "tests"))
        import browser_operations_live  # noqa: PLC0415

        canary = "SYNTH_SECRET_P004B_FAILURE_CANARY"
        with tempfile.TemporaryDirectory() as directory:
            transcript = Path(directory) / "stage.transcript"
            transcript.write_text(
                f"operator prompt and provider text {canary}", encoding="utf-8",
            )
            reason = browser_operations_live.claude_failure_reason(
                1, False, transcript,
            )
            self.assertEqual(reason, "CLAUDE_PROCESS_FAILED")
            self.assertNotIn(canary, reason)
            self.assertRegex(reason, r"^[A-Z][A-Z0-9_]{0,95}$")

    def test_claude_failure_reason_rejects_unsafe_evidence(self) -> None:
        import sys
        import tempfile

        sys.path.insert(0, str(ROOT / "tests"))
        import browser_operations_live  # noqa: PLC0415

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            missing = root / "missing.transcript"
            self.assertEqual(
                browser_operations_live.claude_failure_reason(1, False, missing),
                "CLAUDE_EVIDENCE_REJECTED_INPUT",
            )
            oversized = root / "oversized.transcript"
            oversized.write_bytes(
                b"x" * (browser_operations_live.MAX_CLAUDE_FAILURE_BYTES + 1)
            )
            self.assertEqual(
                browser_operations_live.claude_failure_reason(1, False, oversized),
                "CLAUDE_EVIDENCE_REJECTED_INPUT",
            )
            target = root / "target.transcript"
            target.write_text("unauthorized", encoding="utf-8")
            linked = root / "linked.transcript"
            try:
                linked.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation is unavailable")
            self.assertEqual(
                browser_operations_live.claude_failure_reason(1, False, linked),
                "CLAUDE_EVIDENCE_REJECTED_INPUT",
            )
            for status in (0, 256, True):
                with self.subTest(status=status):
                    self.assertEqual(
                        browser_operations_live.claude_failure_reason(
                            status, False, target,
                        ),
                        "CLAUDE_EVIDENCE_REJECTED_INPUT",
                    )
            self.assertEqual(
                browser_operations_live.claude_failure_reason(1, True, target),
                "CLAUDE_EVIDENCE_REJECTED_INPUT",
            )

    def test_claude_failure_reason_rejects_embedded_or_ambiguous_signatures(self) -> None:
        import sys
        import tempfile

        sys.path.insert(0, str(ROOT / "tests"))
        import browser_operations_live  # noqa: PLC0415

        cases = (
            "transport failed while requesting https://example.invalid/unauthorized",
            "path=/tmp/rate limit/tool not found",
            "API Error: 401 authentication_error\nTypeError: fetch failed ETIMEDOUT",
            "quoted text: 'error: unknown option --not-real'",
            "authentication_error quoted payload https://example.invalid/not-an-error",
            "authentication_error.example.invalid/path",
            "error: unknown option --not-real followed by quoted provider text",
        )
        with tempfile.TemporaryDirectory() as directory:
            transcript = Path(directory) / "stage.transcript"
            for content in cases:
                with self.subTest(content=content):
                    transcript.write_text(content, encoding="utf-8")
                    self.assertEqual(
                        browser_operations_live.claude_failure_reason(
                            1, False, transcript,
                        ),
                        "CLAUDE_PROCESS_FAILED",
                    )

    def test_claude_failure_reason_cli_emits_only_one_code(self) -> None:
        import sys
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            transcript = Path(directory) / "stage.transcript"
            transcript.write_text(
                "authentication_error\nSYNTH_SECRET_MUST_NOT_ESCAPE",
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable, str(PARSER), "--claude-failure-reason",
                    "1", "0", str(transcript),
                ],
                check=False, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "CLAUDE_AUTH_FAILURE\n")
            self.assertEqual(result.stderr, "")

    def test_harness_self_test_exercises_content_free_failure_reducer(self) -> None:
        bash = shutil.which("bash")
        if bash is None:
            self.skipTest("bash is unavailable")
        result = subprocess.run(
            [bash, str(HARNESS), "--self-test"], cwd=ROOT,
            check=False, capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            "live browser operations diagnostic self-test passed\n",
            result.stdout,
        )
        self.assertIn(
            "live browser operations diagnostic cleanup self-test passed\n",
            result.stdout,
        )
        self.assertIn(
            "live browser operations structural failure fingerprint self-test passed\n",
            result.stdout,
        )
        self.assertIn(
            "live browser operations structural timeout fingerprint self-test passed\n",
            result.stdout,
        )
        self.assertIn(
            "live browser operations diagnostic input rejection self-test passed\n",
            result.stdout,
        )
        self.assertIn(
            "live browser operations parser rejection self-test passed\n",
            result.stdout,
        )
        self.assertIn(
            "live browser operations allowlist rejection self-test passed\n",
            result.stdout,
        )
        self.assertIn(
            "live browser operations cleanup rejection self-test passed\n",
            result.stdout,
        )
        self.assertIn(
            "live browser operations timeout provenance self-test passed\n",
            result.stdout,
        )
        self.assertIn(
            "live browser operations timeout forgery resistance self-test passed\n",
            result.stdout,
        )
        self.assertIn(
            "live browser operations timeout signal resistance self-test passed\n",
            result.stdout,
        )
        self.assertIn(
            "live browser operations timeout descendant termination self-test passed\n",
            result.stdout,
        )
        self.assertIn(
            "live browser operations interruption cleanup self-test passed\n",
            result.stdout,
        )
        self.assertIn(
            "live browser operations child signal disposition self-test passed\n",
            result.stdout,
        )
        self.assertIn(
            "live browser operations multiple signal cleanup self-test passed\n",
            result.stdout,
        )
        self.assertNotIn("SYNTH_SECRET", result.stdout + result.stderr)

    def test_modes_authorization_and_bounds_are_explicit(self) -> None:
        for marker in (
            "--self-test", "--preflight", "--run-live", "P004B_LIVE_AUTHORIZED",
            "I_ACKNOWLEDGE_BOUNDED_SYNTHETIC_BROWSER_PROBES",
            "TOTAL_TIMEOUT_SECONDS=1800", 'timeout "$request_limit"',
            "P004B_AUTHORIZED_TOP_LEVEL_INVOCATIONS",
            "P004B_AUTHORIZED_MAX_MODEL_TURNS",
            "P004B_AUTHORIZED_PROVIDER_ENDPOINT",
            "MEASUREMENT_TOP_LEVEL_INVOCATIONS=4",
            "MEASUREMENT_MAX_MODEL_TURNS=32",
            "EXPECTED_TOP_LEVEL_INVOCATIONS=6", "EXPECTED_MAX_MODEL_TURNS=40",
            "browser-mcp-config.py", "ALLOW_MCP_CONFIG", "DENY_MCP_CONFIG",
            '--strict-mcp-config --mcp-config "$EMPTY_MCP_CONFIG"',
            '--strict-mcp-config --mcp-config "$stage_mcp_config"',
            'stage_mcp_config="$MEASUREMENT_MCP_CONFIG"',
        ):
            self.assertIn(marker, self.script)
        self.assertNotIn("--retry", self.script)
        self.assertNotIn("for attempt", self.script)
        self.assertNotIn(" mcp add ", self.script)

    def test_disposable_install_loopback_and_cleanup_are_mandatory(self) -> None:
        for marker in (
            "mktemp -d", "trap cleanup EXIT", 'HOME="$WORK/home"',
            'PROJECT="$WORK/project"', 'INSTALL_ROOT="$WORK/install"',
            'PROMPT_DIR="$WORK/prompts"', 'STREAM_DIR="$WORK/streams"',
            "tests/browser-fixture/server.mjs", "127.0.0.1", "LOOPBACK",
            'rm -f -- "$prompt_path" "$stream_path"', 'rm -rf -- "$WORK_REAL"',
            "scripts/build_nori_staging.py", "--non-interactive", 'link "$STAGING"',
            'switch "$PROFILE_NAME"', 'configure-browser-operations.mjs',
            'configure-native-execution-boundary.mjs',
            'command-guard-launcher.sh',
            '"--apply" --root "$PROJECT"', '"--check" --root "$PROJECT"',
            'CONFIGURED_UNPROVEN',
        ):
            self.assertIn(marker, self.script)
        self.assertNotIn('rm -rf -- "$HOME"', self.script)

    def test_nori_profile_selection_accepts_only_closed_runtime_layouts(self) -> None:
        direct = '"$HOME/.nori/profiles/$LINK_NAME"'
        namespaced = '"$HOME/.nori/profiles/personal/$LINK_NAME"'
        self.assertIn(direct, self.script)
        self.assertIn(namespaced, self.script)
        self.assertIn("PROFILE_NAME=\"$LINK_NAME\"", self.script)
        self.assertIn("PROFILE_NAME=\"personal/$LINK_NAME\"", self.script)
        self.assertIn("Nori linked profile layout is unrecognized", self.script)
        self.assertNotIn("PROFILE_NAME='personal/p0-04b-live'", self.script)
        self.assertNotIn('find "$HOME/.nori/profiles"', self.script)

    def test_existing_browser_runtime_is_linked_only_inside_disposable_roots(self) -> None:
        for marker in (
            "P004B_BROWSER_NODE_MODULES", "P004B_PLAYWRIGHT_BROWSERS_PATH",
            'PROBE_NODE_MODULES="$PROBE_SKILL_ROOT/node_modules"',
            'INSTALLED_NODE_MODULES="$HOME/.claude/skills/browser-operations/node_modules"',
            '[[ ! -e "$PROBE_NODE_MODULES" && ! -L "$PROBE_NODE_MODULES" ]]',
            '[[ ! -e "$INSTALLED_NODE_MODULES" && ! -L "$INSTALLED_NODE_MODULES" ]]',
            'ln -s -- "$BROWSER_NODE_MODULES/playwright"',
            'ln -s -- "$BROWSER_NODE_MODULES/playwright-core"',
            'export PLAYWRIGHT_BROWSERS_PATH="$BROWSER_CACHE"',
            "await adapter.open()", "await adapter.close()",
            "observed.observedVersion",
            '"$installed_adapter_identity" == "$ADAPTER_IDENTITY"',
            "browser runtime package root must be an absolute regular directory",
            "existing Playwright browser cache is unavailable",
        ):
            self.assertIn(marker, self.script)
        for forbidden in ("npm install", "npx ", "playwright install"):
            self.assertNotIn(forbidden, self.script)

    def test_raw_deletion_precedes_aggregation_and_no_installers_exist(self) -> None:
        self.assertLess(
            self.script.index('rm -f -- "$prompt_path" "$stream_path"'),
            self.script.index('aggregate_json="$(aggregate_results)"'),
        )
        for forbidden in ("npm install", "npx ", "pip install", "playwright install", "curl ", "wget "):
            self.assertNotIn(forbidden, self.script)
        for marker in (
            "AVAILABLE_UNRECOGNIZED", "CONFLICT", "GUARD_UNPROVEN",
            "OUTCOME_UNKNOWN", "HUMAN_CHALLENGE", "no automatic retry",
        ):
            self.assertIn(marker, self.script)
        self.assertLess(
            self.script.index('rm -f -- "$EMPTY_MCP_CONFIG"'),
            self.script.index('MEASUREMENT_SOURCE="$MEASUREMENT_DIR/source.json"'),
        )
        self.assertLess(
            self.script.index('rm -rf -- "$SESSION_STORE"'),
            self.script.index('MEASUREMENT_SOURCE="$MEASUREMENT_DIR/source.json"'),
        )

    def test_trusted_measurement_is_parent_reduced_and_session_bound(self) -> None:
        for marker in (
            "--evaluate-measurement-stream", "--status-context",
            "--pty-context", "STATUS_CONTEXT_METADATA_UNAVAILABLE",
            "--build-measurement", "MAIN_MEASUREMENT_SESSION",
            "ROLE_SESSIONS", "--session-id", "--resume",
            "context_fixture_ping", "ToolSearch", "Invoke Skill",
            "Invoke Agent", 'grep -R -l -E', '"$WORK_REAL"',
            "live-context-window-recorder.py", "--status-context",
            "browser-measurement-guard.py", "subagent.claim",
        ):
            self.assertIn(marker, self.script)
        self.assertLess(
            self.script.index('rm -f -- "$prompt_path" "$stream_path"'),
            self.script.index('--build-measurement'),
        )
        self.assertLess(
            self.script.index('--build-measurement'),
            self.script.index('aggregate_json="$(aggregate_results)"'),
        )

    def test_trusted_measurement_runs_from_disposable_project(self) -> None:
        project_cd = self.script.index('cd "$PROJECT"')
        first_probe = self.script.index(
            'run_context_probe main-before "$MAIN_MEASUREMENT_SESSION" new before'
        )
        self.assertLess(project_cd, first_probe)
        self.assertEqual(self.script.count('cd "$PROJECT"'), 1)

    def test_pty_fallback_is_limited_to_new_before_probes(self) -> None:
        self.assertIn(
            '[[ "$mode" == "new" && "$output_stage" == "before" ]]',
            self.script,
        )

    def test_live_probe_requests_the_protected_one_shot_route_with_references_only(self) -> None:
        for marker in (
            'OPS_BROWSER_VALUE_PASSWORD="$P004B_SYNTH_PASSWORD"',
            'OPS_BROWSER_VALUE_TOTP="$P004B_SYNTH_TOTP"',
            'OPS_BROWSER_VALUE_DISABLED=', 'OPS_BROWSER_VALUE_EXPECTED_FALSE=',
            'OPS_BROWSER_VALUE_EXPECTED_TRUE=', "synthetic deterministic", "--step workflow",
            'mcp__p004b-permission__approval_prompt', '"--evaluate-$phase-stream"',
            '/api/summary', '--aggregate-pair',
        ):
            self.assertIn(marker, self.script)
        self.assertNotIn("--workflow-step ey", self.script)
        self.assertNotIn("--permission-mode dontAsk", self.script)
        self.assertIn('--permission-mode default', self.script)
        self.assertIn('--permission-prompt-tool "$PERMISSION_PROMPT_TOOL"', self.script)
        self.assertIn('--tools Bash --allowedTools Bash', self.script)
        self.assertIn("P004B_PERMISSION_PROMPT_TOOL", self.script)
        self.assertIn("Claude Code does not advertise --permission-prompt-tool", self.script)
        self.assertIn("Claude Code does not advertise --include-hook-events", self.script)

    def test_every_stream_json_invocation_enables_verbose_mode(self) -> None:
        stream_json_invocations = self.script.count("--output-format stream-json")
        self.assertEqual(stream_json_invocations, 2)
        self.assertEqual(
            self.script.count("--verbose --output-format stream-json"),
            stream_json_invocations,
        )

    def test_package_gate_runs_only_provider_free_checks(self) -> None:
        gate = GATE.read_text(encoding="utf-8")
        for marker in (
            "python3 tests/test-live-browser-operation-safety.py",
            "node --test tests/browser-operations/workflow.test.mjs",
            "bash -n tests/live-browser-operations-smoke.sh",
            "bash tests/live-browser-operations-smoke.sh --self-test",
        ):
            self.assertIn(marker, gate)
        self.assertNotIn("live-browser-operations-smoke.sh --run-live", gate)

    @staticmethod
    def _workflow_token(value: dict[str, object]) -> str:
        encoded = base64.urlsafe_b64encode(
            json.dumps(value, separators=(",", ":")).encode("utf-8")
        )
        return encoded.rstrip(b"=").decode("ascii")

    def _workflow_command(self) -> str:
        origin = "http://127.0.0.1:43111"
        execution = [
            {"step": "navigate", "origin": f"{origin}/login"},
            {
                "step": "fill", "origin": f"{origin}/login",
                "locatorRole": "textbox", "locatorName": "Password",
                "valueRef": "env:OPS_BROWSER_VALUE_PASSWORD",
                "valueClass": "credential",
            },
            {
                "step": "submit", "origin": f"{origin}/router",
                "locatorRole": "button", "locatorName": "Save",
                "effect": "LOW_RISK_CHANGE",
            },
        ]
        validation = [
            {"step": "navigate", "origin": f"{origin}/login"},
            {
                "step": "inspect", "origin": f"{origin}/router",
                "locatorRole": "status", "locatorName": "Saved state",
                "predicate": "text-equals",
                "expectedRef": "env:OPS_BROWSER_VALUE_EXPECTED",
                "expectRef": "interface-state",
            },
        ]
        runner = ROOT / "skills" / "browser-operations" / "scripts" / "browser-runner.mjs"
        command = shlex.join([
            "node", str(runner),
            "--step", "workflow", "--operation-id", "op-live-browser-001",
            "--session-id", "session-live-browser-001", "--role", "main",
            "--objective-ref", "p004b-synthetic-probe", "--target", "router-fixture",
            "--environment", "test", "--service-origin", origin,
            "--auth-origin", origin, "--identity-ref",
            "operator-provided-protected-channel:synthetic-admin",
            "--credential-transport", "operator-provided-protected-channel",
            "--permission-mode", "default",
            "--action", "navigate", "--action", "fill", "--action", "submit",
            "--action", "inspect", "--effect", "LOW_RISK_CHANGE", "--risk", "low",
            "--precondition-ref", "synthetic-ready", "--validation-ref", "interface-state",
            "--compensation-ref", "synthetic-rollback", "--expires-in-seconds", "600",
            *[
                item
                for step in execution
                for item in ("--workflow-step", self._workflow_token(step))
            ],
            *[
                item
                for step in validation
                for item in ("--validation-step", self._workflow_token(step))
            ],
        ])
        return command

    @classmethod
    def _trusted_measurement(
        cls, nonce: str = "p004b-run-001",
        workflow_sessions: list[str] | None = None,
    ) -> dict[str, object]:
        context_session = "context-main-001"
        return {
            "schemaVersion": 1,
            "runNonce": nonce,
            "workflowSessionIds": workflow_sessions or ["session-live-browser-001"],
            "roleProbes": [
                {
                    "role": role, "sessionId": f"role-session-{index + 1}",
                    "contextObserved": True,
                }
                for index, role in enumerate(cls.ROLES)
            ],
            "contextStages": [
                {"stage": stage, "sessionId": context_session, "usedPercentage": percent}
                for stage, percent in zip(
                    ("before", "afterSkill", "afterSubagent", "afterDiscovery", "afterUse"),
                    (1, 2, 3, 4, 5), strict=True,
                )
            ],
            "toolSearch": {
                "sessionId": context_session, "mode": "available-used",
                "discovered": True, "used": True,
            },
            "mcp": {
                "sessionId": context_session, "connected": True,
                "toolsListed": True, "visibleToolCount": 1,
                "discoveryObserved": True, "useObserved": True,
            },
        }

    def _workflow_stream(self, path: Path, *, include_post: bool = True,
                         reason_code: str = "WORKFLOW_VALIDATED",
                         pre_decision: str = "ask", pre_outcome: str = "success",
                         pre_reason: str = (
                             "ASK_SENSITIVE_OPERATION: stage 1 "
                             "BROWSER_PROTECTED_RUNNER/LOW_RISK_CHANGE. Operator "
                             "confirmation is required before execution. Sensitive values "
                             "are redacted."
                         ),
                         post_event: str = "PostToolUse", post_outcome: str = "success",
                         extra_results: tuple[str, ...] = (), command: str | None = None,
                         result_override: dict[str, object] | None = None) -> None:
        command = command or self._workflow_command()
        pre_output = (
            "not-json" if pre_decision == "malformed" else json.dumps({
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": pre_decision,
                    "permissionDecisionReason": pre_reason,
                },
            })
        )
        events: list[dict[str, object]] = [
            {
                "type": "tool_use", "id": "workflow-tool-1", "name": "Bash",
                "session_id": "session-live-browser-001", "parent_tool_use_id": None,
                "input": {"command": command},
            },
            {
                "type": "system", "subtype": "hook_started",
                "hook_id": "pre-hook-1", "hook_name": "PreToolUse:Bash",
                "hook_event": "PreToolUse", "uuid": "pre-start-uuid",
                "session_id": "session-live-browser-001",
            },
            {
                "type": "system", "subtype": "hook_response",
                "hook_id": "pre-hook-1", "hook_name": "PreToolUse:Bash",
                "hook_event": "PreToolUse", "output": pre_output,
                "stdout": pre_output, "stderr": "", "exit_code": 0,
                "outcome": pre_outcome, "uuid": "pre-response-uuid",
                "session_id": "session-live-browser-001",
            },
        ]
        workflow_result: dict[str, object] = {
            "status": "ok" if reason_code in {
                "WORKFLOW_VALIDATED", "WORKFLOW_NOT_APPLIED",
            } else "outcome-unknown",
            "reasonCode": reason_code, "step": "workflow",
            "operationId": "op-live-browser-001",
            "effect": "LOW_RISK_CHANGE",
            "validationRequired": reason_code == "OUTCOME_UNKNOWN",
            "observation": None,
        }
        if result_override:
            workflow_result.update(result_override)
        events.append({
            "type": "tool_result", "tool_use_id": "workflow-tool-1",
            "session_id": "session-live-browser-001", "parent_tool_use_id": None,
            "content": json.dumps(workflow_result),
        })
        events.extend({
            "type": "tool_result", "tool_use_id": "workflow-tool-1", "content": content,
        } for content in extra_results)
        if include_post:
            events.extend((
                {
                    "type": "system", "subtype": "hook_started",
                    "hook_id": "post-hook-1", "hook_name": f"{post_event}:Bash",
                    "hook_event": post_event, "uuid": "post-start-uuid",
                    "session_id": "session-live-browser-001",
                },
                {
                    "type": "system", "subtype": "hook_response",
                    "hook_id": "post-hook-1", "hook_name": f"{post_event}:Bash",
                    "hook_event": post_event, "output": "", "stdout": "",
                    "stderr": "", "exit_code": 0, "outcome": post_outcome,
                    "uuid": "post-response-uuid",
                    "session_id": "session-live-browser-001",
                },
            ))
        events.append({
            "type": "result", "subtype": "success", "is_error": False,
            "session_id": "session-live-browser-001", "result": "discarded",
        })
        path.write_text(
            "".join(json.dumps(event) + "\n" for event in events),
            encoding="utf-8",
        )

    def _denied_stream(self, path: Path, command: str) -> None:
        session = "session-live-browser-deny-001"
        pre_output = json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse", "permissionDecision": "ask",
                "permissionDecisionReason": (
                    "ASK_SENSITIVE_OPERATION: stage 1 "
                    "BROWSER_PROTECTED_RUNNER/LOW_RISK_CHANGE. Operator confirmation "
                    "is required before execution. Sensitive values are redacted."
                ),
            },
        })
        events = [
            {"type": "tool_use", "id": "workflow-deny-tool-1", "name": "Bash",
             "session_id": session, "parent_tool_use_id": None,
             "input": {"command": command}},
            {"type": "system", "subtype": "hook_started", "hook_id": "deny-pre-hook-1",
             "hook_name": "PreToolUse:Bash", "hook_event": "PreToolUse",
             "uuid": "deny-pre-start", "session_id": session},
            {"type": "system", "subtype": "hook_response", "hook_id": "deny-pre-hook-1",
             "hook_name": "PreToolUse:Bash", "hook_event": "PreToolUse",
             "output": pre_output, "stdout": pre_output, "stderr": "", "exit_code": 0,
             "outcome": "success", "uuid": "deny-pre-response", "session_id": session},
            {"type": "tool_result", "tool_use_id": "workflow-deny-tool-1",
             "session_id": session, "parent_tool_use_id": None,
             "is_error": True, "content": "Permission denied"},
            {"type": "result", "subtype": "success", "is_error": False,
             "session_id": session, "result": "discarded"},
        ]
        path.write_text("".join(json.dumps(event) + "\n" for event in events), encoding="utf-8")

    @staticmethod
    def _permission_signal(
        path: Path, phase: str, fingerprint: str, operation_id: str,
    ) -> None:
        del operation_id
        path.write_text(json.dumps({
            "schemaVersion": 1, "runNonce": "p004b-run-001", "phase": phase,
            "decision": phase, "callCount": 1,
            "invocationFingerprint": fingerprint,
            "verified": True, "inputUnchanged": True,
        }, separators=(",", ":")) + "\n", encoding="utf-8")
        os.chmod(path, 0o600)

    @unittest.skipIf(os.name == "nt", "private permission signals require POSIX")
    def test_ordered_allow_then_deny_unlocks_active_without_claiming_human_approval(self) -> None:
        import sys
        import tempfile

        sys.path.insert(0, str(ROOT / "tests"))
        from browser_operations_live import (  # noqa: PLC0415
            _workflow_command, aggregate_results, evaluate_allowed_stream,
            evaluate_denied_stream,
        )

        runtime = {"claude": "observed", "provider": "observed", "model": "observed", "adapter": "playwright"}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            allow_stream, deny_stream = root / "allow.jsonl", root / "deny.jsonl"
            allow_signal, deny_signal = root / "allow.signal", root / "deny.signal"
            allow_command = self._workflow_command()
            deny_command = allow_command.replace("op-live-browser-001", "op-live-browser-deny-001").replace(
                "session-live-browser-001", "session-live-browser-deny-001",
            )
            self._workflow_stream(allow_stream, command=allow_command)
            self._denied_stream(deny_stream, deny_command)
            allow_evidence = _workflow_command(allow_command)
            deny_evidence = _workflow_command(deny_command)
            assert allow_evidence is not None and deny_evidence is not None
            self._permission_signal(allow_signal, "allow", allow_evidence["invocationFingerprint"], allow_evidence["operationId"])
            self._permission_signal(deny_signal, "deny", deny_evidence["invocationFingerprint"], deny_evidence["operationId"])
            allow = evaluate_allowed_stream(allow_stream, "P004B_TEST_CANARY", allow_signal, "p004b-run-001", "session-live-browser-001")
            deny = evaluate_denied_stream(deny_stream, "P004B_TEST_CANARY", deny_signal, "p004b-run-001", "session-live-browser-deny-001")
            wrong_allow_signal = root / "allow-wrong-phase.signal"
            self._permission_signal(
                wrong_allow_signal, "deny", allow_evidence["invocationFingerprint"],
                allow_evidence["operationId"],
            )
            self.assertNotEqual(evaluate_allowed_stream(
                allow_stream, "P004B_TEST_CANARY", wrong_allow_signal,
                "p004b-run-001", "session-live-browser-001",
            )["status"], "pass")
            result = aggregate_results(
                runtime, [allow, deny],
                measurement=self._trusted_measurement(workflow_sessions=[
                    "session-live-browser-001", "session-live-browser-deny-001",
                ]),
                expected_nonce="p004b-run-001",
                fixture_before={"enabled": False, "revision": 1},
                fixture_after={"enabled": False, "revision": 1},
            )
        self.assertEqual(result["permission"], {
            "mode": "synthetic-deterministic", "allow": "completed",
            "deny": "completed", "callCount": 2,
        })
        self.assertEqual(result["capabilityState"], "ACTIVE")
        self.assertEqual(result["workflow"]["outcome"], "WORKFLOW_VALIDATED")
        self.assertNotIn("human", json.dumps(result).lower())

    @unittest.skipIf(os.name == "nt", "private permission signals require POSIX")
    def test_permission_pair_rejects_reordering_reuse_and_changed_state(self) -> None:
        import sys

        sys.path.insert(0, str(ROOT / "tests"))
        from browser_operations_live import aggregate_results  # noqa: PLC0415

        runtime = {"claude": "observed", "provider": "observed", "model": "observed", "adapter": "playwright"}
        allow = {
            "status": "pass", "permissionPhase": "allow", "permissionDecision": "allow",
            "permissionCallCount": 1, "invocationFingerprint": "a" * 64,
            "operationId": "allow-op", "workflowSessionIds": ["allow-session"],
            "routeClass": "persistent-one-shot", "guardProof": "exact-native-approval",
            "workflowOutcome": "WORKFLOW_VALIDATED", "workflowExecutionSteps": 8,
            "workflowValidationSteps": 7, "workflowAuthentication": "completed",
            "workflowMutation": "completed", "workflowValidation": "completed",
            "toolCalls": 4, "hookEvents": 3,
        }
        deny = {
            "status": "pass", "permissionPhase": "deny", "permissionDecision": "deny",
            "permissionCallCount": 1, "invocationFingerprint": "b" * 64,
            "operationId": "deny-op", "workflowSessionIds": ["deny-session"],
            "routeClass": "workflow-denied", "guardProof": "exact-native-denial",
            "workflowOutcome": "NOT_OBSERVED", "workflowExecutionSteps": 7,
            "workflowValidationSteps": 7, "workflowAuthentication": "not-observed",
            "workflowMutation": "not-observed", "workflowValidation": "not-observed",
            "toolCalls": 2, "hookEvents": 1,
        }
        measurement = self._trusted_measurement(workflow_sessions=["allow-session", "deny-session"])
        variants = [
            ([deny, allow], 1),
            ([allow, {**deny, "workflowSessionIds": ["allow-session"]}], 1),
            ([allow, {**deny, "operationId": "allow-op"}], 1),
            ([allow, {**deny, "invocationFingerprint": "a" * 64}], 1),
            ([allow, {**deny, "permissionDecision": "allow"}], 1),
            ([allow, {**deny, "permissionCallCount": 2}], 1),
            ([allow, deny], 2),
            ([allow, deny], None),
        ]
        for samples, final_revision in variants:
            with self.subTest(samples=samples, final_revision=final_revision):
                result = aggregate_results(
                    runtime, samples, measurement=measurement,
                    expected_nonce="p004b-run-001",
                    fixture_before={"enabled": False, "revision": 1},
                    fixture_after=(
                        {"enabled": False, "revision": final_revision}
                        if final_revision is not None else None
                    ),
                )
                self.assertNotEqual(result["capabilityState"], "ACTIVE")
                self.assertNotEqual(result["status"], "pass")

    @unittest.skipIf(os.name == "nt", "private permission signals require POSIX")
    def test_denied_stream_rejects_post_hooks_runner_output_later_activity_and_bad_signals(self) -> None:
        import copy
        import sys
        import tempfile

        sys.path.insert(0, str(ROOT / "tests"))
        from browser_operations_live import _workflow_command, evaluate_denied_stream  # noqa: PLC0415

        command = self._workflow_command().replace("op-live-browser-001", "op-live-browser-deny-001").replace(
            "session-live-browser-001", "session-live-browser-deny-001",
        )
        session = "session-live-browser-deny-001"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base = root / "base.jsonl"
            signal = root / "deny.signal"
            self._denied_stream(base, command)
            evidence = _workflow_command(command)
            assert evidence is not None
            self._permission_signal(signal, "deny", evidence["invocationFingerprint"], evidence["operationId"])
            events = [json.loads(line) for line in base.read_text(encoding="utf-8").splitlines()]
            mutations: dict[str, list[dict[str, object]]] = {}
            post = copy.deepcopy(events)
            post.insert(-1, {
                "type": "system", "subtype": "hook_started", "hook_id": "late-post",
                "hook_name": "PostToolUse:Bash", "hook_event": "PostToolUse",
                "session_id": session,
            })
            mutations["post-hook"] = post
            runner = copy.deepcopy(events)
            runner.insert(-1, {
                "type": "tool_result", "tool_use_id": "workflow-deny-tool-1",
                "session_id": session, "parent_tool_use_id": None, "is_error": False,
                "content": json.dumps({"reasonCode": "WORKFLOW_VALIDATED"}),
            })
            mutations["runner-output"] = runner
            late = copy.deepcopy(events)
            late.insert(-1, {
                "type": "tool_use", "id": "late-bash", "name": "Bash",
                "session_id": session, "parent_tool_use_id": None,
                "input": {"command": command},
            })
            mutations["later-bash"] = late
            for name, mutated in mutations.items():
                with self.subTest(name=name):
                    stream = root / f"{name}.jsonl"
                    stream.write_text("".join(json.dumps(event) + "\n" for event in mutated), encoding="utf-8")
                    result = evaluate_denied_stream(
                        stream, "P004B_TEST_CANARY", signal, "p004b-run-001", session,
                    )
                    self.assertNotEqual(result["status"], "pass")

            bad_signal = root / "bad.signal"
            self._permission_signal(bad_signal, "allow", evidence["invocationFingerprint"], evidence["operationId"])
            self.assertNotEqual(evaluate_denied_stream(
                base, "P004B_TEST_CANARY", bad_signal, "p004b-run-001", session,
            )["status"], "pass")
            wrong_fingerprint = root / "wrong.signal"
            self._permission_signal(wrong_fingerprint, "deny", "f" * 64, evidence["operationId"])
            self.assertNotEqual(evaluate_denied_stream(
                base, "P004B_TEST_CANARY", wrong_fingerprint, "p004b-run-001", session,
            )["status"], "pass")
            malformed = root / "malformed.signal"
            malformed.write_text("{}\n", encoding="utf-8")
            os.chmod(malformed, 0o600)
            self.assertNotEqual(evaluate_denied_stream(
                base, "P004B_TEST_CANARY", malformed, "p004b-run-001", session,
            )["status"], "pass")
            linked = root / "linked.signal"
            linked.symlink_to(signal)
            self.assertNotEqual(evaluate_denied_stream(
                base, "P004B_TEST_CANARY", linked, "p004b-run-001", session,
            )["status"], "pass")

    def test_active_mode_without_authorization_stops_before_dependencies(self) -> None:
        if shutil.which("bash") is None:
            self.skipTest("bash is unavailable on this host")
        environment = os.environ.copy()
        environment.pop("P004B_LIVE_AUTHORIZED", None)
        result = subprocess.run(
            ["bash", str(HARNESS), "--run-live"], cwd=ROOT, env=environment,
            capture_output=True, text=True, timeout=10, check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("I_ACKNOWLEDGE_BOUNDED_SYNTHETIC_BROWSER_PROBES", result.stderr)

    def test_live_mode_rejects_external_permission_inputs_before_dependencies(self) -> None:
        if shutil.which("bash") is None:
            self.skipTest("bash is unavailable on this host")
        environment = os.environ.copy()
        environment.update({
            "P004B_LIVE_AUTHORIZED": "1",
            "P004B_LIVE_ACK": "I_ACKNOWLEDGE_BOUNDED_SYNTHETIC_BROWSER_PROBES",
            "P004B_AUTHORIZED_TOP_LEVEL_INVOCATIONS": "6",
            "P004B_AUTHORIZED_MAX_MODEL_TURNS": "40",
        })
        for name, value in (
            ("P004B_PERMISSION_PROMPT_TOOL", "mcp__approval__ask"),
            ("P004B_PERMISSION_MCP_CONFIG", "/tmp/operator.json"),
            ("P004B_REQUEST_COUNT", "2"),
        ):
            with self.subTest(name=name):
                selected = environment.copy()
                selected[name] = value
                result = subprocess.run(
                    ["bash", str(HARNESS), "--run-live"], cwd=ROOT, env=selected,
                    capture_output=True, text=True, timeout=10, check=False,
                )
                self.assertEqual(result.returncode, 2)
                self.assertIn("external permission handlers", result.stderr)

    def test_default_self_test_is_provider_free_and_content_free(self) -> None:
        if shutil.which("bash") is None:
            self.skipTest("bash is unavailable on this host")
        result = subprocess.run(
            ["bash", str(HARNESS)], cwd=ROOT, capture_output=True, text=True,
            timeout=20, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertIn("live browser operations self-test passed", result.stdout)
        self.assertNotIn("SYNTH_SECRET_", result.stdout)

    def test_parser_accepts_only_the_content_free_aggregate_schema(self) -> None:
        import sys

        sys.path.insert(0, str(ROOT / "tests"))
        from browser_operations_live import validate_aggregate  # noqa: PLC0415

        value = {
            "status": "pass", "reasonCode": "COMPATIBLE",
            "observedRuntime": {
                "claude": "observed", "provider": "observed", "model": "observed",
                "adapter": "playwright",
            },
            "capabilityState": "ACTIVE", "guardProof": "exact-native-approval", "roleCount": 12,
            "routeClass": "persistent-one-shot",
            "workflow": {
                "executionSteps": 3, "validationSteps": 2,
                "authentication": "completed", "mutation": "completed",
                "validation": "completed", "outcome": "WORKFLOW_VALIDATED",
            },
            "toolCalls": 4, "hookEvents": 3,
            "context": {
                "before": 1, "afterSkill": 2, "afterSubagent": 3,
                "afterDiscovery": 4, "afterUse": 5, "toolSearchMode": "available-used",
            },
            "cleanup": "verified",
            "permission": {
                "mode": "synthetic-deterministic", "allow": "completed",
                "deny": "completed", "callCount": 2,
            },
        }
        self.assertEqual(validate_aggregate(value), value)
        for mutation in (
            {**value, "rawPrompt": "forbidden"},
            {**value, "roleCount": 13},
            {**value, "cleanup": "unknown"},
            {**value, "guardProof": "exact-deny"},
            {**value, "routeClass": "legacy-read-only-multi-command"},
            {**value, "workflow": {**value["workflow"], "validation": "not-observed"}},
            {**value, "toolCalls": 1},
            {**value, "hookEvents": 1},
        ):
            with self.assertRaises(ValueError):
                validate_aggregate(mutation)
        self.assertNotIn("rawPrompt", json.dumps(validate_aggregate(value)))

    def test_live_aggregate_distinguishes_legacy_read_only_from_persistent_one_shot(self) -> None:
        import sys
        import tempfile

        sys.path.insert(0, str(ROOT / "tests"))
        from browser_operations_live import aggregate_results, evaluate_stream  # noqa: PLC0415

        runtime = {
            "claude": "observed", "provider": "observed", "model": "observed",
            "adapter": "playwright",
        }
        with tempfile.TemporaryDirectory() as directory:
            stream = Path(directory) / "workflow.jsonl"
            self._workflow_stream(stream)
            sample = evaluate_stream(stream, "P004B_TEST_CANARY")
        result = aggregate_results(runtime, [sample])
        self.assertEqual(result["status"], "inconclusive")
        self.assertEqual(result["capabilityState"], "AVAILABLE_RECOGNIZED")
        self.assertEqual(result["routeClass"], "persistent-one-shot")
        self.assertEqual(result["guardProof"], "exact-native-approval")
        self.assertEqual(result["roleCount"], 0)
        self.assertEqual(result["context"]["toolSearchMode"], "unavailable")
        self.assertEqual(result["workflow"], {
            "executionSteps": 3, "validationSteps": 2,
            "authentication": "completed", "mutation": "completed",
            "validation": "completed", "outcome": "WORKFLOW_VALIDATED",
        })

        legacy = {
            "status": "pass", "reasonCode": "STRUCTURAL_RESULT", "toolCalls": 1,
            "hookEvents": 2, "roleLabels": sample["roleLabels"],
            "contextPercentages": [1, 2, 3, 4, 5],
        }
        legacy_result = aggregate_results(runtime, [legacy])
        self.assertEqual(legacy_result["routeClass"], "legacy-read-only-multi-command")
        self.assertNotEqual(legacy_result["capabilityState"], "ACTIVE")
        self.assertNotEqual(legacy_result["status"], "pass")

        mixed_result = aggregate_results(runtime, [sample, legacy])
        self.assertEqual(mixed_result["routeClass"], "workflow-incomplete")
        self.assertNotEqual(mixed_result["capabilityState"], "ACTIVE")
        self.assertNotEqual(mixed_result["status"], "pass")

    def test_only_nonce_and_session_bound_trusted_measurement_can_unlock_active(self) -> None:
        import sys
        import tempfile

        sys.path.insert(0, str(ROOT / "tests"))
        from browser_operations_live import aggregate_results, evaluate_stream  # noqa: PLC0415

        runtime = {
            "claude": "observed", "provider": "observed", "model": "observed",
            "adapter": "playwright",
        }
        with tempfile.TemporaryDirectory() as directory:
            stream = Path(directory) / "workflow.jsonl"
            self._workflow_stream(stream)
            sample = evaluate_stream(stream, "P004B_TEST_CANARY")
        self.assertEqual(sample["workflowSessionIds"], ["session-live-browser-001"])

        without_measurement = aggregate_results(runtime, [sample])
        self.assertEqual(without_measurement["status"], "inconclusive")
        self.assertEqual(without_measurement["roleCount"], 0)
        self.assertEqual(without_measurement["context"]["toolSearchMode"], "unavailable")

        measurement = self._trusted_measurement()
        active = aggregate_results(
            runtime, [sample], measurement=measurement, expected_nonce="p004b-run-001",
        )
        self.assertEqual(active["status"], "inconclusive")
        self.assertNotEqual(active["capabilityState"], "ACTIVE")
        self.assertEqual(active["roleCount"], 12)
        self.assertEqual(active["context"], {
            "before": 1, "afterSkill": 2, "afterSubagent": 3,
            "afterDiscovery": 4, "afterUse": 5,
            "toolSearchMode": "available-used",
        })

        forged = dict(sample)
        forged["roleLabels"] = list(self.ROLES)
        forged["contextPercentages"] = [91, 92, 93, 94, 95]
        forged_result = aggregate_results(runtime, [forged])
        self.assertEqual(forged_result["status"], "inconclusive")
        self.assertEqual(forged_result["roleCount"], 0)
        self.assertEqual(forged_result["context"]["before"], 0)

        repeated_session = aggregate_results(
            runtime, [sample, sample], measurement=measurement,
            expected_nonce="p004b-run-001",
        )
        self.assertEqual(repeated_session["status"], "inconclusive")
        self.assertEqual(repeated_session["roleCount"], 0)

    def test_trusted_measurement_schema_is_exact_and_fail_closed(self) -> None:
        import copy
        import sys

        sys.path.insert(0, str(ROOT / "tests"))
        from browser_operations_live import validate_trusted_measurement  # noqa: PLC0415

        valid = self._trusted_measurement()
        self.assertEqual(
            validate_trusted_measurement(
                valid, "p004b-run-001", {"session-live-browser-001"},
            ),
            valid,
        )
        mutations: list[dict[str, object]] = []
        for key, value in (
            ("rawPrompt", "forbidden"), ("transcript", "forbidden"),
            ("secret", "forbidden"),
        ):
            mutation = copy.deepcopy(valid)
            mutation[key] = value
            mutations.append(mutation)
        wrong_nonce = copy.deepcopy(valid)
        wrong_nonce["runNonce"] = "different-run"
        mutations.append(wrong_nonce)
        boolean_version = copy.deepcopy(valid)
        boolean_version["schemaVersion"] = True
        mutations.append(boolean_version)
        wrong_session = copy.deepcopy(valid)
        wrong_session["workflowSessionIds"] = ["different-session"]
        mutations.append(wrong_session)
        reversed_stages = copy.deepcopy(valid)
        reversed_stages["contextStages"] = list(reversed(reversed_stages["contextStages"]))
        mutations.append(reversed_stages)
        duplicate_role = copy.deepcopy(valid)
        duplicate_role["roleProbes"][1]["role"] = duplicate_role["roleProbes"][0]["role"]
        mutations.append(duplicate_role)
        false_role = copy.deepcopy(valid)
        false_role["roleProbes"][0]["contextObserved"] = False
        mutations.append(false_role)
        boolean_percent = copy.deepcopy(valid)
        boolean_percent["contextStages"][0]["usedPercentage"] = True
        mutations.append(boolean_percent)
        cross_session = copy.deepcopy(valid)
        cross_session["contextStages"][4]["sessionId"] = "different-main-session"
        mutations.append(cross_session)
        incoherent_search = copy.deepcopy(valid)
        incoherent_search["toolSearch"]["used"] = False
        mutations.append(incoherent_search)
        incoherent_mcp = copy.deepcopy(valid)
        incoherent_mcp["mcp"]["useObserved"] = False
        mutations.append(incoherent_mcp)
        for mutation in mutations:
            with self.subTest(keys=sorted(mutation)):
                with self.assertRaises(ValueError):
                    validate_trusted_measurement(
                        mutation, "p004b-run-001", {"session-live-browser-001"},
                    )

    def test_trusted_measurement_file_rejects_symlinks_size_and_unsafe_permissions(self) -> None:
        import os
        import sys
        import tempfile

        sys.path.insert(0, str(ROOT / "tests"))
        from browser_operations_live import load_trusted_measurement  # noqa: PLC0415

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid = root / "measurement.json"
            valid.write_text(json.dumps(self._trusted_measurement()), encoding="utf-8")
            if os.name == "nt":
                self.assertIsNone(load_trusted_measurement(
                    valid, "p004b-run-001", {"session-live-browser-001"},
                ))
                return
            valid.chmod(0o600)
            self.assertIsNotNone(load_trusted_measurement(
                valid, "p004b-run-001", {"session-live-browser-001"},
            ))

            oversized = root / "oversized.json"
            oversized.write_bytes(b"{" + (b" " * 32768) + b"}")
            if os.name != "nt":
                oversized.chmod(0o600)
            self.assertIsNone(load_trusted_measurement(
                oversized, "p004b-run-001", {"session-live-browser-001"},
            ))

            link = root / "measurement-link.json"
            try:
                link.symlink_to(valid)
            except OSError:
                pass
            else:
                self.assertIsNone(load_trusted_measurement(
                    link, "p004b-run-001", {"session-live-browser-001"},
                ))

            if os.name != "nt":
                valid.chmod(0o644)
                self.assertIsNone(load_trusted_measurement(
                    valid, "p004b-run-001", {"session-live-browser-001"},
                ))

    def test_aggregate_cli_consumes_the_private_trusted_sidecar(self) -> None:
        import sys
        import tempfile

        if os.name == "nt":
            self.skipTest("trusted sidecar files are accepted only by the POSIX/WSL harness")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stream = root / "workflow.jsonl"
            sample_path = root / "sample.json"
            measurement_path = root / "measurement.json"
            self._workflow_stream(stream)
            evaluated = subprocess.run(
                [
                    sys.executable, str(PARSER), "--evaluate-stream", str(stream),
                    "P004B_TEST_CANARY", str(sample_path),
                ],
                cwd=ROOT, capture_output=True, text=True, check=False,
            )
            self.assertEqual(evaluated.returncode, 0, evaluated.stderr)
            measurement_path.write_text(
                json.dumps(self._trusted_measurement()), encoding="utf-8",
            )
            if os.name != "nt":
                measurement_path.chmod(0o600)
            aggregated = subprocess.run(
                [
                    sys.executable, str(PARSER), "--aggregate", str(measurement_path),
                    "p004b-run-001", "observed", "observed", "observed",
                    "playwright", str(sample_path),
                ],
                cwd=ROOT, capture_output=True, text=True, check=False,
            )
            self.assertEqual(aggregated.returncode, 0, aggregated.stderr)
            result = json.loads(aggregated.stdout)
            self.assertEqual(result["status"], "inconclusive")
            self.assertEqual(result["roleCount"], 12)

    def test_parent_parser_reduces_measurement_streams_to_structural_signals(self) -> None:
        import sys
        import tempfile

        sys.path.insert(0, str(ROOT / "tests"))
        from browser_operations_live import evaluate_measurement_stream  # noqa: PLC0415

        session = "context-main-001"
        nonce = "p004b-run-001"
        cases = {
            "skill": ("Skill", {"skill": "context-continuity"}, "skillCalls"),
            "subagent": ("Agent", {
                "description": "P004B_SUBAGENT_ACK", "prompt": "P004B_SUBAGENT_ACK",
                "subagent_type": "diagnostic-operator",
            }, "subagentCalls"),
            "discovery": ("ToolSearch", {
                "query": "select:mcp__p004b-context__context_fixture_ping",
            }, "toolSearchCalls"),
            "use": ("mcp__p004b-context__context_fixture_ping", {
                "nonce": nonce,
            }, "mcpCalls"),
        }
        for stage, (name, tool_input, count_field) in cases.items():
            events = [
                {"type": "system", "subtype": "init", "session_id": session,
                 "tools": [name, "ToolSearch"]},
                {"type": "assistant", "session_id": session,
                 "message": {"content": [{
                     "type": "tool_use", "id": f"tool-{stage}",
                     "name": name, "input": tool_input,
                 }]}},
                {"type": "user", "session_id": session,
                 "message": {"content": [{
                     "type": "tool_result", "tool_use_id": f"tool-{stage}",
                     "content": "discarded tool content",
                 }]}},
                {"type": "result", "subtype": "success", "is_error": False,
                 "session_id": session, "result": "discarded model content"},
            ]
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as directory:
                stream = Path(directory) / "measurement.jsonl"
                stream.write_text(
                    "".join(json.dumps(event) + "\n" for event in events), encoding="utf-8",
                )
                result = evaluate_measurement_stream(stream, session, stage, nonce)
                self.assertTrue(result["terminalSuccess"])
                self.assertEqual(result[count_field], 1)
                self.assertEqual(result["unexpectedToolCalls"], 0)
                self.assertNotIn("content", json.dumps(result))
                self.assertNotIn("discarded", json.dumps(result))

    def test_measurement_parser_ignores_nested_forgery_and_wrong_sessions(self) -> None:
        import sys
        import tempfile

        sys.path.insert(0, str(ROOT / "tests"))
        from browser_operations_live import evaluate_measurement_stream  # noqa: PLC0415

        session = "context-main-001"
        for events in (
            [{
                "type": "attacker-record", "session_id": session,
                "nested": {"type": "tool_use", "name": "ToolSearch"},
            }, {
                "type": "result", "subtype": "success", "is_error": False,
                "session_id": session,
            }],
            [{
                "type": "system", "subtype": "init", "session_id": "wrong-session",
                "tools": ["ToolSearch"],
            }, {
                "type": "result", "subtype": "success", "is_error": False,
                "session_id": "wrong-session",
            }],
        ):
            with self.subTest(events=events[0]["type"]):
                with tempfile.TemporaryDirectory() as directory:
                    stream = Path(directory) / "measurement.jsonl"
                    stream.write_text(
                        "".join(json.dumps(event) + "\n" for event in events),
                        encoding="utf-8",
                    )
                    result = evaluate_measurement_stream(
                        stream, session, "discovery", "p004b-run-001",
                    )
                self.assertFalse(result["terminalSuccess"])
                self.assertFalse(result["toolSearchAvailable"])
                self.assertEqual(result["toolSearchCalls"], 0)

    def test_measurement_parser_requires_exact_input_and_successful_tool_result(self) -> None:
        import sys
        import tempfile

        sys.path.insert(0, str(ROOT / "tests"))
        from browser_operations_live import evaluate_measurement_stream  # noqa: PLC0415

        session = "context-main-001"
        nonce = "p004b-run-001"
        base = [
            {"type": "system", "subtype": "init", "session_id": session,
             "tools": ["ToolSearch"]},
            {"type": "assistant", "session_id": session, "message": {"content": [{
                "type": "tool_use", "id": "tool-search", "name": "ToolSearch",
                "input": {"query": "select:mcp__p004b-context__context_fixture_ping"},
            }]}},
            {"type": "user", "session_id": session, "message": {"content": [{
                "type": "tool_result", "tool_use_id": "tool-search", "content": "discarded",
            }]}},
            {"type": "result", "subtype": "success", "is_error": False,
             "session_id": session},
        ]
        mutations = []
        missing = json.loads(json.dumps(base))
        del missing[2]
        mutations.append(missing)
        duplicate = json.loads(json.dumps(base))
        duplicate.insert(3, json.loads(json.dumps(duplicate[2])))
        mutations.append(duplicate)
        wrong_session = json.loads(json.dumps(base))
        wrong_session[2]["session_id"] = "wrong-session"
        mutations.append(wrong_session)
        failed = json.loads(json.dumps(base))
        failed[2]["message"]["content"][0]["is_error"] = True
        mutations.append(failed)
        nested = json.loads(json.dumps(base))
        nested[2]["parent_tool_use_id"] = "agent-parent"
        mutations.append(nested)
        smuggled = json.loads(json.dumps(base))
        smuggled[1]["message"]["content"][0]["input"] = {"query": "other"}
        mutations.append(smuggled)
        late = json.loads(json.dumps(base))
        late.append(json.loads(json.dumps(late[1])))
        mutations.append(late)
        with tempfile.TemporaryDirectory() as directory:
            for index, events in enumerate(mutations):
                stream = Path(directory) / f"measurement-{index}.jsonl"
                stream.write_text(
                    "".join(json.dumps(event) + "\n" for event in events), encoding="utf-8",
                )
                with self.subTest(index=index):
                    result = evaluate_measurement_stream(
                        stream, session, "discovery", nonce,
                    )
                    self.assertFalse(result["terminalSuccess"])

    def test_parent_builder_requires_coherent_stage_and_mcp_evidence(self) -> None:
        import copy
        import sys

        sys.path.insert(0, str(ROOT / "tests"))
        from browser_operations_live import build_trusted_measurement  # noqa: PLC0415

        session = "context-main-001"
        stages = [
            {"stage": stage, "sessionId": session, "usedPercentage": percent}
            for stage, percent in zip(
                ("before", "afterSkill", "afterSubagent", "afterDiscovery", "afterUse"),
                (1, 2, 3, 4, 5), strict=True,
            )
        ]
        base_signal = {
            "sessionId": session, "terminalSuccess": True,
            "skillCalls": 0, "subagentCalls": 0,
            "toolSearchAvailable": False, "toolSearchCalls": 0,
            "mcpCalls": 0, "unexpectedToolCalls": 0,
        }
        samples = {
            "skill": {**base_signal, "skillCalls": 1},
            "subagent": {**base_signal, "subagentCalls": 1},
            "discovery": {
                **base_signal, "toolSearchAvailable": True, "toolSearchCalls": 1,
            },
            "use": {**base_signal, "mcpCalls": 1},
        }
        mcp = {
            "connected": True, "toolsListed": True,
            "visibleToolCount": 1, "called": True,
            "callCount": 1, "runNonce": "p004b-run-001",
        }
        result = build_trusted_measurement(
            "p004b-run-001", ["session-live-browser-001"],
            self._trusted_measurement()["roleProbes"], stages, samples, mcp,
        )
        self.assertEqual(result, self._trusted_measurement())

        for mutation in (
            {**samples, "skill": {**samples["skill"], "terminalSuccess": False}},
            {**samples, "subagent": {**samples["subagent"], "sessionId": "wrong"}},
            {**samples, "discovery": {
                **samples["discovery"], "toolSearchAvailable": False,
            }},
            {**samples, "use": {**samples["use"], "mcpCalls": 0}},
            {**samples, "skill": {**samples["skill"], "skillCalls": 2}},
            {**samples, "use": {**samples["use"], "unexpectedToolCalls": 1}},
        ):
            with self.assertRaises(ValueError):
                build_trusted_measurement(
                    "p004b-run-001", ["session-live-browser-001"],
                    self._trusted_measurement()["roleProbes"], stages, mutation, mcp,
                )
        incomplete_mcp = copy.deepcopy(mcp)
        incomplete_mcp["called"] = False
        with self.assertRaises(ValueError):
            build_trusted_measurement(
                "p004b-run-001", ["session-live-browser-001"],
                self._trusted_measurement()["roleProbes"], stages, samples, incomplete_mcp,
            )
        duplicate_mcp = copy.deepcopy(mcp)
        duplicate_mcp["callCount"] = 2
        with self.assertRaises(ValueError):
            build_trusted_measurement(
                "p004b-run-001", ["session-live-browser-001"],
                self._trusted_measurement()["roleProbes"], stages, samples, duplicate_mcp,
            )

    def test_status_reducer_uses_only_nonce_bound_native_percentage(self) -> None:
        import sys
        import tempfile

        sys.path.insert(0, str(ROOT / "tests"))
        from browser_operations_live import status_context_observation  # noqa: PLC0415

        with tempfile.TemporaryDirectory() as directory:
            events = Path(directory) / "status.jsonl"
            events.write_text("".join((
                json.dumps({
                    "kind": "status-context", "percent": 7,
                    "windowTokens": 1_000_000, "runNonce": "p004b-run-001",
                    "stage": "before",
                }) + "\n",
                json.dumps({
                    "kind": "status-context", "percent": 8,
                    "windowTokens": 1_000_000, "runNonce": "p004b-run-001",
                    "stage": "before",
                }) + "\n",
            )), encoding="utf-8")
            self.assertEqual(status_context_observation(
                events, "p004b-run-001", "context-main-001", "before",
            ), {
                "stage": "before", "sessionId": "context-main-001",
                "usedPercentage": 8,
            })
            forged = json.loads(events.read_text(encoding="utf-8").splitlines()[0])
            forged["runNonce"] = "wrong"
            events.write_text(json.dumps(forged) + "\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                status_context_observation(
                    events, "p004b-run-001", "context-main-001", "before",
                )

    def test_parent_builder_cli_writes_one_owner_only_atomic_sidecar(self) -> None:
        import stat
        import sys
        import tempfile

        if os.name == "nt":
            self.skipTest("trusted sidecar files are accepted only by the POSIX/WSL harness")
        expected = self._trusted_measurement()
        session = "context-main-001"
        base = {
            "sessionId": session, "terminalSuccess": True,
            "skillCalls": 0, "subagentCalls": 0,
            "toolSearchAvailable": False, "toolSearchCalls": 0,
            "mcpCalls": 0, "unexpectedToolCalls": 0,
        }
        source = {
            "runNonce": expected["runNonce"],
            "workflowSessionIds": expected["workflowSessionIds"],
            "roleProbes": expected["roleProbes"],
            "contextStages": expected["contextStages"],
            "stageSamples": {
                "skill": {**base, "skillCalls": 1},
                "subagent": {**base, "subagentCalls": 1},
                "discovery": {
                    **base, "toolSearchAvailable": True, "toolSearchCalls": 1,
                },
                "use": {**base, "mcpCalls": 1},
            },
            "mcpSignal": {
                "connected": True, "toolsListed": True,
                "visibleToolCount": 1, "called": True,
                "callCount": 1, "runNonce": expected["runNonce"],
            },
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "source.json"
            output_path = root / "measurement.json"
            source_path.write_text(json.dumps(source), encoding="utf-8")
            source_path.chmod(0o600)
            result = subprocess.run(
                [
                    sys.executable, str(PARSER), "--build-measurement",
                    str(source_path), str(output_path),
                ],
                cwd=ROOT, capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(output_path.read_text(encoding="utf-8")), expected)
            self.assertEqual(stat.S_IMODE(output_path.stat().st_mode), 0o600)
            self.assertEqual(list(root.glob("*.tmp")), [])

    def test_workflow_evidence_accepts_only_the_exact_canonical_runner_command(self) -> None:
        import sys

        sys.path.insert(0, str(ROOT / "tests"))
        from browser_operations_live import _workflow_command  # noqa: PLC0415

        command = self._workflow_command()
        self.assertIsNotNone(_workflow_command(command))
        fake_runner = str(
            ROOT / "tmp" / "skills" / "browser-operations" / "scripts" / "browser-runner.mjs"
        )
        for adversarial in (
            f"echo harmless {command}",
            f"{command} echo trailing",
            f"{command} ; echo trailing",
            f"{command} > result.json",
            f"{command} --unknown x",
            f"{command} --step workflow",
            command.replace("--step workflow", "--step"),
            command.replace(str(ROOT / "skills" / "browser-operations" / "scripts" / "browser-runner.mjs"), fake_runner),
        ):
            with self.subTest(command=adversarial[-80:]):
                self.assertIsNone(_workflow_command(adversarial))

    def test_workflow_completion_requires_ordered_successful_hooks_and_one_coherent_result(self) -> None:
        import sys
        import tempfile

        sys.path.insert(0, str(ROOT / "tests"))
        from browser_operations_live import evaluate_stream  # noqa: PLC0415

        invalid_variants = (
            {"pre_decision": "deny"},
            {"pre_decision": "allow"},
            {"pre_decision": "malformed"},
            {"pre_reason": "P004B_SYNTHETIC_DECISION"},
            {"pre_outcome": "error"},
            {"post_event": "PostToolUseFailure"},
            {"post_outcome": "error"},
            {"extra_results": (json.dumps({
                "status": "ok", "reasonCode": "WORKFLOW_VALIDATED",
                "operationId": "op-live-browser-001", "step": "workflow",
                "effect": "LOW_RISK_CHANGE", "validationRequired": False,
                "observation": None,
            }),)},
        )
        for variant in invalid_variants:
            with self.subTest(variant=variant):
                with tempfile.TemporaryDirectory() as directory:
                    stream = Path(directory) / "workflow.jsonl"
                    self._workflow_stream(stream, **variant)
                    sample = evaluate_stream(stream, "P004B_TEST_CANARY")
                self.assertEqual(sample["routeClass"], "workflow-incomplete")
                self.assertNotEqual(sample["guardProof"], "exact-native-approval")

        incoherent_results = (
            {"status": "denied"},
            {"operationId": "different-operation"},
            {"step": "open"},
            {"effect": "SENSITIVE_READ"},
            {"validationRequired": True},
            {"observation": {"trust": "untrusted", "summary": "not content-free"}},
        )
        for result_override in incoherent_results:
            with self.subTest(result_override=result_override):
                with tempfile.TemporaryDirectory() as directory:
                    stream = Path(directory) / "workflow.jsonl"
                    self._workflow_stream(stream, result_override=result_override)
                    sample = evaluate_stream(stream, "P004B_TEST_CANARY")
                self.assertEqual(sample["routeClass"], "workflow-incomplete")
                self.assertNotEqual(sample["guardProof"], "exact-native-approval")

        for mutation in (
            "post-before-result", "duplicate-pre", "pre-before-tool-use",
            "hook-input-schema", "wrong-hook-name",
        ):
            with self.subTest(mutation=mutation):
                with tempfile.TemporaryDirectory() as directory:
                    stream = Path(directory) / "workflow.jsonl"
                    self._workflow_stream(stream)
                    events = [
                        json.loads(line) for line in stream.read_text(encoding="utf-8").splitlines()
                    ]
                    if mutation == "post-before-result":
                        events = events[:3] + events[4:6] + [events[3]] + events[6:]
                    elif mutation == "duplicate-pre":
                        events[3:3] = [dict(events[1]), dict(events[2])]
                    elif mutation == "pre-before-tool-use":
                        events = [dict(events[1]), dict(events[2]), events[0], *events[3:]]
                    elif mutation == "wrong-hook-name":
                        events[1]["hook_name"] = "PreToolUse:Write"
                        events[2]["hook_name"] = "PreToolUse:Write"
                    else:
                        events = [
                            event for event in events
                            if not (event.get("type") == "system"
                                    and event.get("subtype") in {
                                        "hook_started", "hook_response",
                                    })
                        ]
                        events.insert(1, {
                            "type": "hook_event", "hook_event_name": "PreToolUse",
                            "tool_use_id": "workflow-tool-1", "tool_name": "Bash",
                            "outcome": "success", "permissionDecision": "ask",
                        })
                        events.insert(3, {
                            "type": "hook_event", "hook_event_name": "PostToolUse",
                            "tool_use_id": "workflow-tool-1", "tool_name": "Bash",
                            "outcome": "success",
                        })
                    stream.write_text(
                        "".join(json.dumps(event) + "\n" for event in events),
                        encoding="utf-8",
                    )
                    sample = evaluate_stream(stream, "P004B_TEST_CANARY")
                self.assertEqual(sample["routeClass"], "workflow-incomplete")
                self.assertNotEqual(sample["guardProof"], "exact-native-approval")

    def test_outcome_unknown_cannot_be_overwritten_by_later_validated_result(self) -> None:
        import sys
        import tempfile

        sys.path.insert(0, str(ROOT / "tests"))
        from browser_operations_live import evaluate_stream  # noqa: PLC0415

        validated = json.dumps({
            "status": "ok", "reasonCode": "WORKFLOW_VALIDATED",
            "operationId": "op-live-browser-001", "step": "workflow",
            "effect": "LOW_RISK_CHANGE", "validationRequired": False,
            "observation": None,
        })
        with tempfile.TemporaryDirectory() as directory:
            stream = Path(directory) / "workflow.jsonl"
            self._workflow_stream(
                stream, reason_code="OUTCOME_UNKNOWN", extra_results=(validated,),
            )
            sample = evaluate_stream(stream, "P004B_TEST_CANARY")
        self.assertEqual(sample["routeClass"], "workflow-incomplete")
        self.assertEqual(sample["workflowOutcome"], "OUTCOME_UNKNOWN")
        self.assertNotEqual(sample["guardProof"], "exact-native-approval")

    def test_untrusted_metadata_and_error_terminal_cannot_unlock_active(self) -> None:
        import sys
        import tempfile

        sys.path.insert(0, str(ROOT / "tests"))
        from browser_operations_live import aggregate_results, evaluate_stream  # noqa: PLC0415

        runtime = {
            "claude": "observed", "provider": "observed", "model": "observed",
            "adapter": "playwright",
        }
        with tempfile.TemporaryDirectory() as directory:
            stream = Path(directory) / "workflow.jsonl"
            self._workflow_stream(stream)
            events = [
                json.loads(line) for line in stream.read_text(encoding="utf-8").splitlines()
            ]
            events = [event for event in events if event.get("type") != "status"]
            events[-1] = {
                "type": "result", "subtype": "error_max_turns", "is_error": True,
                "session_id": "session-live-browser-001", "result": "discarded",
            }
            events.extend({
                "type": "attacker-record", "agent_type": role,
                "nested": {"used_percentage": index + 1},
            } for index, role in enumerate((
                "audit-evidence-collector", "change-manager", "cloud-platform-operator",
                "database-operator", "diagnostic-operator", "incident-commander",
                "kubernetes-operator", "network-edge-operator", "observability-sre",
                "rca-facilitator", "release-cicd-operator",
                "security-operations-reviewer",
            )))
            stream.write_text(
                "".join(json.dumps(event) + "\n" for event in events), encoding="utf-8",
            )
            sample = evaluate_stream(stream, "P004B_TEST_CANARY")
        result = aggregate_results(runtime, [sample])
        self.assertNotEqual(result["status"], "pass")
        self.assertNotEqual(result["capabilityState"], "ACTIVE")
        self.assertEqual(result["roleCount"], 0)
        self.assertEqual(result["context"]["toolSearchMode"], "unavailable")

    def test_post_success_activity_and_cross_session_hooks_invalidate_workflow(self) -> None:
        import sys
        import tempfile

        sys.path.insert(0, str(ROOT / "tests"))
        from browser_operations_live import evaluate_stream  # noqa: PLC0415

        for mutation in (
            "extra-tool", "late-failure", "cross-session", "tool-envelope-session",
        ):
            with self.subTest(mutation=mutation):
                with tempfile.TemporaryDirectory() as directory:
                    stream = Path(directory) / "workflow.jsonl"
                    self._workflow_stream(stream)
                    events = [
                        json.loads(line)
                        for line in stream.read_text(encoding="utf-8").splitlines()
                    ]
                    terminal = events.pop()
                    if mutation == "extra-tool":
                        events.extend((
                            {"type": "tool_use", "id": "late-tool", "name": "WebFetch",
                             "input": {"url": "http://127.0.0.1:43111/"}},
                            {"type": "tool_result", "tool_use_id": "late-tool",
                             "content": "discarded"},
                        ))
                    elif mutation == "late-failure":
                        events.extend((
                            {"type": "system", "subtype": "hook_started",
                             "hook_id": "late-failure", "hook_name": "PostToolUseFailure:Bash",
                             "hook_event": "PostToolUseFailure", "uuid": "late-start",
                             "session_id": "session-live-browser-001"},
                            {"type": "system", "subtype": "hook_response",
                             "hook_id": "late-failure", "hook_name": "PostToolUseFailure:Bash",
                             "hook_event": "PostToolUseFailure", "output": "", "stdout": "",
                             "stderr": "failed", "exit_code": 2, "outcome": "error",
                             "uuid": "late-response",
                             "session_id": "session-live-browser-001"},
                        ))
                    elif mutation == "cross-session":
                        events[4]["session_id"] = "different-session"
                        events[5]["session_id"] = "different-session"
                    else:
                        for index, message_type in ((0, "assistant"), (3, "user")):
                            block = {
                                key: value for key, value in events[index].items()
                                if key not in {"session_id", "parent_tool_use_id"}
                            }
                            events[index] = {
                                "type": message_type, "session_id": "different-session",
                                "parent_tool_use_id": "different-parent",
                                "message": {"content": [block]},
                            }
                    events.append(terminal)
                    stream.write_text(
                        "".join(json.dumps(event) + "\n" for event in events),
                        encoding="utf-8",
                    )
                    sample = evaluate_stream(stream, "P004B_TEST_CANARY")
                self.assertEqual(sample["routeClass"], "workflow-incomplete")
                self.assertNotEqual(sample["guardProof"], "exact-native-approval")

    def test_tool_activity_before_workflow_is_rejected(self) -> None:
        import sys
        import tempfile

        sys.path.insert(0, str(ROOT / "tests"))
        from browser_operations_live import evaluate_stream  # noqa: PLC0415

        with tempfile.TemporaryDirectory() as directory:
            stream = Path(directory) / "workflow.jsonl"
            self._workflow_stream(stream)
            events = [
                json.loads(line) for line in stream.read_text(encoding="utf-8").splitlines()
            ]
            events.insert(0, {
                "type": "assistant", "session_id": "session-live-browser-001",
                "parent_tool_use_id": None, "message": {"content": [{
                    "type": "tool_use", "id": "pre-agent", "name": "Agent",
                    "input": {"subagent_type": "diagnostic-operator"},
                }]},
            })
            stream.write_text(
                "".join(json.dumps(event) + "\n" for event in events), encoding="utf-8",
            )
            sample = evaluate_stream(stream, "P004B_TEST_CANARY")
        self.assertEqual(sample["routeClass"], "workflow-incomplete")
        self.assertNotEqual(sample["guardProof"], "exact-native-approval")

    def test_workflow_evidence_rejects_noncanonical_base64url_records(self) -> None:
        import sys

        sys.path.insert(0, str(ROOT / "tests"))
        from browser_operations_live import _workflow_command  # noqa: PLC0415

        value: dict[str, object] = {
            "step": "navigate", "origin": "http://127.0.0.1:43111/login",
        }
        token = self._workflow_token(value)
        while len(token) % 4 == 0:
            value["marker"] = str(value.get("marker", "")) + "x"
            token = self._workflow_token(value)
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
        replacement = alphabet[alphabet.index(token[-1]) ^ 1]
        noncanonical = token[:-1] + replacement
        self.assertNotEqual(noncanonical, token)
        command = self._workflow_command()
        self.assertIsNotNone(_workflow_command(command))
        self.assertIn(token, command)
        self.assertIsNone(_workflow_command(command.replace(token, noncanonical, 1)))

    def test_nested_stream_events_count_the_observed_workflow_calls(self) -> None:
        import sys
        import tempfile

        sys.path.insert(0, str(ROOT / "tests"))
        from browser_operations_live import evaluate_stream  # noqa: PLC0415

        with tempfile.TemporaryDirectory() as directory:
            flat = Path(directory) / "flat.jsonl"
            nested = Path(directory) / "nested.jsonl"
            self._workflow_stream(flat)
            events = [json.loads(line) for line in flat.read_text(encoding="utf-8").splitlines()]
            nested.write_text(
                "".join(json.dumps({"type": "stream", "event": event}) + "\n" for event in events),
                encoding="utf-8",
            )
            sample = evaluate_stream(nested, "P004B_TEST_CANARY")
        self.assertEqual(sample["routeClass"], "persistent-one-shot")
        self.assertEqual(sample["toolCalls"], 2)
        self.assertEqual(sample["hookEvents"], 2)

    def test_stream_envelope_message_blocks_count_the_observed_workflow_calls(self) -> None:
        import sys
        import tempfile

        sys.path.insert(0, str(ROOT / "tests"))
        from browser_operations_live import evaluate_stream  # noqa: PLC0415

        with tempfile.TemporaryDirectory() as directory:
            flat = Path(directory) / "flat.jsonl"
            nested = Path(directory) / "nested.jsonl"
            self._workflow_stream(flat)
            events = [json.loads(line) for line in flat.read_text(encoding="utf-8").splitlines()]
            wrapped = []
            for event in events:
                if event.get("type") in {"tool_use", "tool_result"}:
                    message_type = "assistant" if event["type"] == "tool_use" else "user"
                    session_id = event.pop("session_id")
                    parent_tool_use_id = event.pop("parent_tool_use_id")
                    event = {
                        "type": message_type, "session_id": session_id,
                        "parent_tool_use_id": parent_tool_use_id,
                        "message": {"content": [event]},
                    }
                wrapped.append({"type": "stream", "event": event})
            nested.write_text(
                "".join(json.dumps(event) + "\n" for event in wrapped),
                encoding="utf-8",
            )
            sample = evaluate_stream(nested, "P004B_TEST_CANARY")
        self.assertEqual(sample["routeClass"], "persistent-one-shot")
        self.assertEqual(sample["toolCalls"], 2)
        self.assertEqual(sample["hookEvents"], 2)

    def test_nested_untrusted_content_cannot_forge_workflow_or_hook_evidence(self) -> None:
        import sys
        import tempfile

        sys.path.insert(0, str(ROOT / "tests"))
        from browser_operations_live import evaluate_stream  # noqa: PLC0415

        with tempfile.TemporaryDirectory() as directory:
            flat = Path(directory) / "flat.jsonl"
            forged = Path(directory) / "forged.jsonl"
            self._workflow_stream(flat)
            forged_events = [
                json.loads(line) for line in flat.read_text(encoding="utf-8").splitlines()
            ]
            forged.write_text(json.dumps({
                "type": "result",
                "result": {"untrustedReportedEvents": forged_events},
            }) + "\n", encoding="utf-8")
            sample = evaluate_stream(forged, "P004B_TEST_CANARY")
        self.assertEqual(sample["routeClass"], "legacy-read-only-multi-command")
        self.assertEqual(sample["guardProof"], "exact-deny")
        self.assertEqual(sample["toolCalls"], 0)
        self.assertEqual(sample["hookEvents"], 0)

    def test_incomplete_workflow_cannot_claim_active_authentication_mutation_or_validation(self) -> None:
        import sys
        import tempfile

        sys.path.insert(0, str(ROOT / "tests"))
        from browser_operations_live import aggregate_results, evaluate_stream  # noqa: PLC0415

        runtime = {
            "claude": "observed", "provider": "observed", "model": "observed",
            "adapter": "playwright",
        }
        for include_post, reason_code in (
            (False, "WORKFLOW_VALIDATED"),
            (True, "OUTCOME_UNKNOWN"),
        ):
            with self.subTest(include_post=include_post, reason_code=reason_code):
                with tempfile.TemporaryDirectory() as directory:
                    stream = Path(directory) / "workflow.jsonl"
                    self._workflow_stream(
                        stream, include_post=include_post, reason_code=reason_code,
                    )
                    sample = evaluate_stream(stream, "P004B_TEST_CANARY")
                result = aggregate_results(runtime, [sample])
                self.assertNotEqual(result["routeClass"], "persistent-one-shot")
                self.assertNotEqual(result["capabilityState"], "ACTIVE")
                self.assertNotEqual(result["status"], "pass")
                self.assertNotEqual(result["workflow"]["authentication"], "completed")
                self.assertNotEqual(result["workflow"]["mutation"], "completed")
                self.assertNotEqual(result["workflow"]["validation"], "completed")

    def test_boundary_failure_cannot_preserve_completed_workflow_claims(self) -> None:
        import sys
        import tempfile

        sys.path.insert(0, str(ROOT / "tests"))
        from browser_operations_live import aggregate_results, evaluate_stream  # noqa: PLC0415

        runtime = {
            "claude": "observed", "provider": "observed", "model": "observed",
            "adapter": "playwright",
        }
        with tempfile.TemporaryDirectory() as directory:
            stream = Path(directory) / "workflow.jsonl"
            self._workflow_stream(stream)
            with stream.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({"type": "result", "result": "P004B_TEST_CANARY"}) + "\n")
            sample = evaluate_stream(stream, "P004B_TEST_CANARY")
        result = aggregate_results(runtime, [sample])
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["capabilityState"], "OUTCOME_UNKNOWN")
        self.assertEqual(result["routeClass"], "workflow-incomplete")
        self.assertEqual(result["guardProof"], "exact-deny")
        self.assertEqual(result["workflow"]["outcome"], "OUTCOME_UNKNOWN")
        self.assertNotEqual(result["workflow"]["authentication"], "completed")
        self.assertNotEqual(result["workflow"]["mutation"], "completed")
        self.assertNotEqual(result["workflow"]["validation"], "completed")

    def test_zero_tool_calls_or_deny_only_proof_cannot_be_active(self) -> None:
        import sys

        sys.path.insert(0, str(ROOT / "tests"))
        from browser_operations_live import aggregate_results  # noqa: PLC0415

        sample = {
            "status": "pass", "reasonCode": "STRUCTURAL_RESULT", "toolCalls": 0,
            "hookEvents": 0, "roleLabels": [], "contextPercentages": [1, 2, 3, 4, 5],
        }
        result = aggregate_results({
            "claude": "observed", "provider": "observed", "model": "observed",
            "adapter": "playwright",
        }, [sample])
        self.assertEqual(result["status"], "inconclusive")
        self.assertNotEqual(result["capabilityState"], "ACTIVE")

    def test_parser_retains_only_bounded_numeric_context_samples(self) -> None:
        import sys
        import tempfile

        sys.path.insert(0, str(ROOT / "tests"))
        from browser_operations_live import evaluate_stream  # noqa: PLC0415

        events = [{
            "type": "attacker-record", "used_percentage": value,
            "content": "discard me",
        } for value in (11, 22, 33, 44, 55)]
        with tempfile.TemporaryDirectory() as directory:
            stream = Path(directory) / "stream.jsonl"
            stream.write_text(
                "".join(json.dumps(event) + "\n" for event in events),
                encoding="utf-8",
            )
            result = evaluate_stream(stream, "P004B_TEST_CANARY")
        self.assertEqual(result["contextPercentages"], [])
        self.assertNotIn("content", json.dumps(result))
        self.assertNotIn("discard", json.dumps(result))


if __name__ == "__main__":
    unittest.main()
