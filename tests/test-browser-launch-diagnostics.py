#!/usr/bin/env python3
"""Provider-free behavioral tests for the external launch diagnostic boundary."""
import importlib.util
import io
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
MODULE = ROOT / "tests/browser_launch_diagnostics.py"
SUPPRESSED = {"category": "UNKNOWN", "reasonCode": "DIAGNOSTIC_SUPPRESSED"}


class LaunchDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(MODULE.is_file(), "versioned diagnostic reducer is missing")
        spec = importlib.util.spec_from_file_location("launch_diagnostics", MODULE)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def test_context_failure_does_not_become_generic_suppression(self):
        self.assertEqual(self.module.reduce_line(
            b"BLOCKED: trusted context probe failed: main-before (PTY_CONTEXT_INSPECTED_FAILED)\n"
        ), {"category": "CONTEXT", "reasonCode": "PTY_CONTEXT_INSPECTED_FAILED",
            "probe": "main-before"})

    def test_native_status_and_pty_fallback_failures_are_distinct(self):
        cases = (
            (b"BLOCKED: trusted status context failed: main-after-use (STATUS_CONTEXT_REJECTED)",
             {"category": "CONTEXT", "reasonCode": "STATUS_CONTEXT_REJECTED", "probe": "main-after-use"}),
            (b"BLOCKED: trusted PTY context failed: role-11 (PTY_CONTEXT_EVIDENCE_REJECTED)",
             {"category": "CONTEXT", "reasonCode": "PTY_CONTEXT_EVIDENCE_REJECTED", "probe": "role-11"}),
        )
        for line, expected in cases:
            with self.subTest(line=line):
                self.assertEqual(self.module.reduce_line(line), expected)

    def test_all_closed_context_probe_labels_are_retained(self):
        for probe in ("main-before", "main-after-skill", "main-after-subagent",
                      "main-after-discovery", "main-after-use", *(f"role-{n}" for n in range(12))):
            line = f"BLOCKED: trusted context probe failed: {probe} (PTY_PROMPT_READY_FAILED)".encode()
            self.assertEqual(self.module.reduce_line(line), {
                "category": "CONTEXT", "reasonCode": "PTY_PROMPT_READY_FAILED", "probe": probe})

    def test_measurement_failure_retains_structural_fingerprint(self):
        reason = "CLAUDE_FAILURE_EXIT_2_STREAM_RESULT_ERROR_TERMINAL_MAX_TURNS_MODEL_ADVISORY_PRESENT_REASON_PROCESS"
        for stage in ("skill", "subagent", "discovery", "use"):
            line = f"BLOCKED: trusted measurement stage failed: {stage} ({reason})".encode()
            self.assertEqual(self.module.reduce_line(line), {
                "category": "MEASUREMENT", "reasonCode": reason, "measurement": stage})

    def test_workflow_request_and_evidence_are_not_conflated(self):
        reason = "CLAUDE_EVIDENCE_REJECTED_INPUT"
        self.assertEqual(self.module.reduce_line(
            f"BLOCKED: deny workflow request was inconclusive ({reason})".encode()),
            {"category": "WORKFLOW_REQUEST", "reasonCode": reason, "phase": "deny"})
        self.assertEqual(self.module.reduce_line(
            b"BLOCKED: allow workflow evidence rejected (STREAM_INVALID; cleanup=verified)"),
            {"category": "WORKFLOW_EVIDENCE", "reasonCode": "STREAM_INVALID",
             "phase": "allow", "cleanupReported": "verified"})

    def test_canary_source_is_a_closed_category_not_content(self):
        for source in ("ASSISTANT_TEXT", "ASSISTANT_THINKING", "ASSISTANT_TOOL_INPUT",
                       "USER_INPUT", "TOOL_RESULT", "SYSTEM_METADATA", "TERMINAL_RESULT",
                       "RAW_INVALID", "UNKNOWN", "MULTIPLE"):
            line = f"BLOCKED: allow workflow evidence rejected (CANARY_EXPOSED; source={source}; cleanup=verified)".encode()
            self.assertEqual(self.module.reduce_line(line), {
                "category": "WORKFLOW_EVIDENCE", "reasonCode": "CANARY_EXPOSED",
                "phase": "allow", "sourceCategory": source, "cleanupReported": "verified"})

    def test_exit_and_cleanup_are_only_reported_observations(self):
        for stage in ("STARTUP", "SELF_TEST", "RUNTIME", "INSTALL", "CONFIGURE", "FIXTURE_START",
                      "CONTEXT_MAIN", "CONTEXT_ROLE", "MEASUREMENT_SKILL", "MEASUREMENT_SUBAGENT",
                      "MEASUREMENT_DISCOVERY", "MEASUREMENT_USE", "WORKFLOW_ALLOW", "WORKFLOW_DENY",
                      "FIXTURE_ALLOW", "FIXTURE_DENY", "SIDECAR", "AGGREGATE", "CLEANUP", "FINALIZE", "UNKNOWN"):
            line = f"BLOCKED: unexpected harness exit (stage={stage}, exit=2, cleanup=verified)".encode()
            self.assertEqual(self.module.reduce_line(line), {
                "category": "HARNESS", "reasonCode": "UNEXPECTED_EXIT", "stageReported": stage,
                "exitReported": 2, "cleanupReported": "verified"})
        self.assertEqual(self.module.reduce_line(
            b"BLOCKED: harness cleanup failed (stage=FIXTURE_DENY, exit=2, cleanup=failed)"),
            {"category": "HARNESS", "reasonCode": "CLEANUP_FAILED", "stageReported": "FIXTURE_DENY",
             "exitReported": 2, "cleanupReported": "failed"})

    def test_static_pre_provider_and_sidecar_diagnostics_are_categorized(self):
        cases = (
            (b"BLOCKED: Node.js not found", "RUNTIME", "NODE_MISSING"),
            (b"BLOCKED: Nori linked profile layout is unrecognized", "INSTALL", "PROFILE_LAYOUT_UNRECOGNIZED"),
            (b"BLOCKED: command hook configuration was not installed exactly", "CONFIGURE", "COMMAND_CONFIGURATION_REJECTED"),
            (b"BLOCKED: GUARD_UNPROVEN", "GUARD", "GUARD_UNPROVEN"),
            (b"BLOCKED: loopback fixture exited during startup", "FIXTURE", "FIXTURE_START_FAILED"),
            (b"BLOCKED: raw prompt, stream, PTY, or transcript retained before sidecar construction", "SIDECAR", "RAW_EVIDENCE_RETAINED"),
            (b"BLOCKED: total timeout reached during trusted measurement", "BUDGET", "TOTAL_TIMEOUT"),
        )
        for line, category, reason in cases:
            self.assertEqual(self.module.reduce_line(line), {"category": category, "reasonCode": reason})

    def test_closed_fingerprint_reason_and_exit_are_validated(self):
        for reason in ("AUTH", "RATE_LIMIT", "PROVIDER_MODEL", "TRANSPORT", "CONTRACT", "RUNTIME", "PROCESS"):
            code = f"CLAUDE_FAILURE_EXIT_1_STREAM_EMPTY_TERMINAL_NONE_MODEL_ADVISORY_ABSENT_REASON_{reason}"
            self.assertEqual(self.module.reduce_line(
                f"BLOCKED: allow workflow request was inconclusive ({code})".encode())["reasonCode"], code)
        code = "CLAUDE_FAILURE_EXIT_124_STREAM_ASSISTANT_TERMINAL_NONE_MODEL_ADVISORY_ABSENT_REASON_TIMEOUT"
        self.assertEqual(self.module.reduce_line(
            f"BLOCKED: allow workflow request was inconclusive ({code})".encode())["reasonCode"], code)
        for code in ("CLAUDE_EVIDENCE_REJECTED_PARSER", "CLAUDE_EVIDENCE_REJECTED_ALLOWLIST", "CLAUDE_EVIDENCE_REJECTED_CLEANUP"):
            self.assertEqual(self.module.reduce_line(
                f"BLOCKED: allow workflow request was inconclusive ({code})".encode())["reasonCode"], code)

    def test_warning_classification_does_not_report_a_cause(self):
        record = self.module.reduce_line(b"Warning: Detected unsettled top-level await at file:///private/location.mjs")
        self.assertEqual(record, {"category": "RUNTIME_WARNING", "reasonCode": "UNSETTLED_TOP_LEVEL_AWAIT"})

    def test_unknown_labels_and_partial_matches_never_escape(self):
        inputs = (
            b"BLOCKED: trusted context probe failed: role-12 (PTY_PROMPT_READY_FAILED)",
            b"BLOCKED: trusted context probe failed: private-token (PTY_PROMPT_READY_FAILED)",
            b"BLOCKED: trusted context probe failed: main-before (PTY_PRIVATE_TOKEN_FAILED)",
            b"BLOCKED: allow workflow evidence rejected (CANARY_EXPOSED; source=PRIVATE_TOKEN; cleanup=verified)",
            b"BLOCKED: allow workflow evidence rejected (STREAM_INVALID; source=ASSISTANT_TEXT; cleanup=verified)",
            b"BLOCKED: unexpected harness exit (stage=PRIVATE_TOKEN, exit=2, cleanup=verified)",
            b"BLOCKED: unexpected harness exit (stage=RUNTIME, exit=256, cleanup=verified)",
            b"BLOCKED: unexpected harness exit (stage=RUNTIME, exit=0, cleanup=verified)",
            b"BLOCKED: harness cleanup failed (stage=RUNTIME, exit=2, cleanup=verified)",
            b"BLOCKED: trusted status context failed: main-before (PTY_PROMPT_READY_FAILED)",
            b"BLOCKED: trusted measurement stage failed: skill (CLAUDE_FAILURE_EXIT_999_STREAM_EMPTY_TERMINAL_NONE_MODEL_ADVISORY_ABSENT_REASON_PROCESS)",
            b"BLOCKED: trusted measurement stage failed: skill (CLAUDE_FAILURE_EXIT_1_STREAM_EMPTY_TERMINAL_NONE_MODEL_ADVISORY_ABSENT_REASON_TIMEOUT)",
            b"prefix BLOCKED: GUARD_UNPROVEN", b"BLOCKED: GUARD_UNPROVEN suffix",
            b"BLOCKED: GUARD_UNPROVEN\nprivate-token", b"\x1b[31mBLOCKED: GUARD_UNPROVEN\x1b[0m",
            b"BLOCKED: GUARD_UNPROVEN\x00", b"\xff", b"x" * 4097,
            b'{"status":"pass","credential":"private-token"}',
        )
        for line in inputs:
            with self.subTest(length=len(line)):
                self.assertEqual(self.module.reduce_line(line), SUPPRESSED)

    def test_crlf_is_accepted_but_embedded_controls_are_not(self):
        self.assertEqual(self.module.reduce_line(b"BLOCKED: GUARD_UNPROVEN\r\n"),
                         {"category": "GUARD", "reasonCode": "GUARD_UNPROVEN"})
        self.assertEqual(self.module.reduce_line(b"BLOCKED:\tGUARD_UNPROVEN"), SUPPRESSED)

    def test_stream_discards_overlong_line_without_parsing_its_suffix(self):
        source = io.BytesIO(b"x" * 10000 + b"BLOCKED: GUARD_UNPROVEN\nBLOCKED: Node.js not found\n")
        output = io.StringIO()
        self.assertEqual(self.module.reduce_stream(source, output), 0)
        self.assertEqual([json.loads(line) for line in output.getvalue().splitlines()], [
            SUPPRESSED, {"category": "RUNTIME", "reasonCode": "NODE_MISSING"}])

    def test_stream_deduplicates_without_retaining_input_content(self):
        output = io.StringIO()
        self.assertEqual(self.module.reduce_stream(io.BytesIO(b"private-token\n" * 1000), output), 0)
        self.assertEqual(output.getvalue(), '{"category":"UNKNOWN","reasonCode":"DIAGNOSTIC_SUPPRESSED"}\n')

    def test_stream_input_limit_is_closed_and_not_a_truncated_match(self):
        output = io.StringIO()
        status = self.module.reduce_stream(io.BytesIO(b"x" * (1024 * 1024 + 1)), output)
        self.assertEqual(status, 2)
        self.assertEqual(json.loads(output.getvalue().splitlines()[-1]),
                         {"category": "FILTER", "reasonCode": "INPUT_LIMIT"})

    def test_stream_output_limit_never_claims_success(self):
        source = io.BytesIO(b"".join(
            f"BLOCKED: unexpected harness exit (stage=RUNTIME, exit={n}, cleanup=verified)\n".encode()
            for n in range(1, 256)) + b"BLOCKED: GUARD_UNPROVEN\nBLOCKED: Node.js not found\n")
        output = io.StringIO()
        self.assertEqual(self.module.reduce_stream(source, output), 2)
        records = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual(len(records), 257)
        self.assertEqual(records[-1], {"category": "FILTER", "reasonCode": "OUTPUT_LIMIT"})

    def test_real_cli_never_emits_unknown_content_or_traceback(self):
        result = subprocess.run([sys.executable, str(MODULE)], input=b"private-token\nBLOCKED: GUARD_UNPROVEN\n",
                                capture_output=True, timeout=5, check=False)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, b"")
        self.assertEqual([json.loads(line) for line in result.stdout.splitlines()], [
            SUPPRESSED, {"category": "GUARD", "reasonCode": "GUARD_UNPROVEN"}])

    def test_real_harness_unauthorized_stop_remains_content_free(self):
        import os
        env = {key: value for key, value in os.environ.items() if not key.startswith(("P004B_", "ANTHROPIC_"))}
        result = subprocess.run(["bash", str(ROOT / "tests/live-browser-operations-smoke.sh"), "--run-live"],
                                env=env, capture_output=True, timeout=5, check=False)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self.module.reduce_line(result.stderr), {
            "category": "AUTHORIZATION", "reasonCode": "LIVE_AUTHORIZATION_MISSING"})

    def test_real_pty_reducer_output_survives_the_launch_boundary(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            events = Path(directory) / "events.jsonl"
            events.write_text('{"kind":"pty-driver","stage":"context_free_value_missing","outcome":"failed"}\n', encoding="utf-8")
            result = subprocess.run([sys.executable, str(ROOT / "tests/browser_operations_live.py"),
                                     "--pty-failure-reason", str(events)],
                                    capture_output=True, timeout=5, check=False)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout, b"PTY_CONTEXT_FREE_VALUE_MISSING_FAILED\n")
            self.assertEqual(self.module.reduce_line(
                b"BLOCKED: trusted context probe failed: main-before (" + result.stdout.rstrip(b"\n") + b")"),
                {"category": "CONTEXT", "reasonCode": "PTY_CONTEXT_FREE_VALUE_MISSING_FAILED", "probe": "main-before"})

    def test_startup_authentication_stops_survive_the_closed_launch_boundary(self):
        import tempfile
        for stage, expected in (
            ("api_key_approval_required", "PTY_API_KEY_APPROVAL_REQUIRED_FAILED"),
            ("login_required", "PTY_LOGIN_REQUIRED_FAILED"),
        ):
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as directory:
                events = Path(directory) / "events.jsonl"
                events.write_text(json.dumps({
                    "kind": "pty-driver", "stage": stage, "outcome": "failed",
                }) + "\n", encoding="utf-8")
                result = subprocess.run(
                    [sys.executable, str(ROOT / "tests/browser_operations_live.py"),
                     "--pty-failure-reason", str(events)],
                    capture_output=True, timeout=5, check=False,
                )
                self.assertEqual(result.returncode, 0)
                self.assertEqual(result.stdout.decode().strip(), expected)
                self.assertEqual(self.module.reduce_line(
                    f"BLOCKED: trusted context probe failed: main-before ({expected})".encode()),
                    {"category": "CONTEXT", "reasonCode": expected, "probe": "main-before"})

    def test_real_cli_rejects_arguments_without_echo(self):
        result = subprocess.run([sys.executable, str(MODULE), "private-token"],
                                capture_output=True, timeout=5, check=False)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stderr, b"")
        self.assertEqual(json.loads(result.stdout), {"category": "FILTER", "reasonCode": "ARGUMENTS_REJECTED"})

    def test_all_workflow_rejection_reasons_remain_distinct(self):
        for reason in ("CANARY_EXPOSED", "STREAM_INVALID", "STREAM_INCONCLUSIVE", "WORKFLOW_INCOMPLETE",
                       "PERMISSION_INCONCLUSIVE", "DENY_STREAM_INCONCLUSIVE", "WORKFLOW_EVIDENCE_REJECTED"):
            self.assertEqual(self.module.reduce_line(
                f"BLOCKED: deny workflow evidence rejected ({reason}; cleanup=verified)".encode()),
                {"category": "WORKFLOW_EVIDENCE", "reasonCode": reason, "phase": "deny", "cleanupReported": "verified"})

    def test_filter_io_failure_has_no_exception_content(self):
        class BrokenInput:
            def readline(self, size):
                raise OSError("private-token")
        import unittest.mock
        output = io.StringIO()
        with unittest.mock.patch.object(self.module.sys, "stdin", type("Input", (), {"buffer": BrokenInput()})()), \
                unittest.mock.patch.object(self.module.sys, "stdout", output), \
                unittest.mock.patch.object(self.module.sys, "argv", [str(MODULE)]):
            self.assertEqual(self.module.main(), 2)
        self.assertEqual(json.loads(output.getvalue()), {"category": "FILTER", "reasonCode": "IO_REJECTED"})

    def test_terminal_carriage_return_is_not_silently_removed(self):
        self.assertEqual(self.module.reduce_line(b"BLOCKED: GUARD_UNPROVEN\r"), SUPPRESSED)

    def test_exact_byte_limit_preserves_valid_final_record(self):
        final = b"BLOCKED: GUARD_UNPROVEN\n"
        source = io.BytesIO(b"x" * (1024 * 1024 - len(final) - 1) + b"\n" + final)
        output = io.StringIO()
        self.assertEqual(self.module.reduce_stream(source, output), 0)
        self.assertEqual([json.loads(line) for line in output.getvalue().splitlines()], [
            SUPPRESSED, {"category": "GUARD", "reasonCode": "GUARD_UNPROVEN"}])

    def test_invalid_input_types_do_not_raise_or_echo(self):
        for value in (None, "private-token", 7, bytearray(b"private-token")):
            self.assertEqual(self.module.reduce_line(value), SUPPRESSED)

    def test_maximum_payload_has_lf_crlf_and_eof_parity(self):
        prefix = b"Warning: Detected unsettled top-level await at "
        payload = prefix + b"x" * (4096 - len(prefix))
        expected = {"category": "RUNTIME_WARNING", "reasonCode": "UNSETTLED_TOP_LEVEL_AWAIT"}
        for ending in (b"\n", b"\r\n", b""):
            with self.subTest(ending=repr(ending)):
                output = io.StringIO()
                self.assertEqual(self.module.reduce_line(payload + ending), expected)
                self.assertEqual(self.module.reduce_stream(io.BytesIO(payload + ending), output), 0)
                self.assertEqual(json.loads(output.getvalue()), expected)

    def test_payload_over_boundary_is_suppressed_for_each_delimiter(self):
        prefix = b"Warning: Detected unsettled top-level await at "
        payload = prefix + b"x" * (4097 - len(prefix))
        for ending in (b"\n", b"\r\n", b""):
            output = io.StringIO()
            self.assertEqual(self.module.reduce_line(payload + ending), SUPPRESSED)
            self.assertEqual(self.module.reduce_stream(io.BytesIO(payload + ending), output), 0)
            self.assertEqual(json.loads(output.getvalue()), SUPPRESSED)

    def test_closed_output_does_not_turn_error_handling_into_traceback(self):
        import unittest.mock
        output = io.StringIO()
        output.close()
        with unittest.mock.patch.object(self.module.sys, "stdin", type("Input", (), {"buffer": io.BytesIO(b"private-token\n")})()), \
                unittest.mock.patch.object(self.module.sys, "stdout", output), \
                unittest.mock.patch.object(self.module.sys, "argv", [str(MODULE)]):
            try:
                status = self.module.main()
            except Exception as error:
                self.fail(f"closed output escaped the diagnostic boundary: {type(error).__name__}")
            self.assertEqual(status, 2)


if __name__ == "__main__":
    unittest.main()
