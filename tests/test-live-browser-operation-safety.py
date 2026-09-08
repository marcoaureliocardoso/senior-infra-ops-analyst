#!/usr/bin/env python3
"""Static and provider-free safety contract for the P0-04B live harness."""
from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "tests" / "live-browser-operations-smoke.sh"
PARSER = ROOT / "tests" / "browser_operations_live.py"
GATE = ROOT / "tests" / "validate-package.sh"


class LiveBrowserOperationSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.script = HARNESS.read_text(encoding="utf-8") if HARNESS.is_file() else ""

    def setUp(self) -> None:
        if not HARNESS.is_file() and self._testMethodName != "test_harness_files_exist":
            self.skipTest("live browser harness is not implemented yet")

    def test_harness_files_exist(self) -> None:
        self.assertTrue(HARNESS.is_file())
        self.assertTrue(PARSER.is_file())

    def test_modes_authorization_and_bounds_are_explicit(self) -> None:
        for marker in (
            "--self-test", "--preflight", "--run-live", "P004B_LIVE_AUTHORIZED",
            "I_ACKNOWLEDGE_BOUNDED_SYNTHETIC_BROWSER_PROBES", "REQUEST_COUNT",
            "TOTAL_TIMEOUT_SECONDS", "REQUEST_COUNT -ge 1", "REQUEST_COUNT -le 13",
            "TOTAL_TIMEOUT_SECONDS -le 1800", 'timeout "$PER_REQUEST_TIMEOUT_SECONDS"',
        ):
            self.assertIn(marker, self.script)
        self.assertNotIn("--retry", self.script)
        self.assertNotIn("for attempt", self.script)

    def test_disposable_install_loopback_and_cleanup_are_mandatory(self) -> None:
        for marker in (
            "mktemp -d", "trap cleanup EXIT", 'HOME="$WORK/home"',
            'PROJECT="$WORK/project"', 'INSTALL_ROOT="$WORK/install"',
            'PROMPT_DIR="$WORK/prompts"', 'STREAM_DIR="$WORK/streams"',
            "tests/browser-fixture/server.mjs", "127.0.0.1", "LOOPBACK",
            'rm -f -- "$prompt_path" "$stream_path"', 'rm -rf -- "$WORK_REAL"',
            "scripts/build_nori_staging.py", "--non-interactive", 'link "$STAGING"',
            'switch "$PROFILE_NAME"', 'configure-browser-operations.mjs',
            '"--apply" --root "$PROJECT"', '"--check" --root "$PROJECT"',
            'CONFIGURED_UNPROVEN',
        ):
            self.assertIn(marker, self.script)
        self.assertNotIn('rm -rf -- "$HOME"', self.script)

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

    def test_live_probe_requests_the_protected_one_shot_route_with_references_only(self) -> None:
        for marker in (
            'OPS_BROWSER_VALUE_PASSWORD="$P004B_SYNTH_PASSWORD"',
            'OPS_BROWSER_VALUE_TOTP="$P004B_SYNTH_TOTP"',
            'OPS_BROWSER_VALUE_DISABLED=', 'OPS_BROWSER_VALUE_EXPECTED=',
            "persistent one-shot", "--step workflow",
        ):
            self.assertIn(marker, self.script)
        self.assertNotIn("--workflow-step ey", self.script)

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

    def _workflow_stream(self, path: Path, *, include_post: bool = True,
                         reason_code: str = "WORKFLOW_VALIDATED") -> None:
        origin = "http://127.0.0.1:43111"
        execution = [
            {"step": "navigate", "origin": f"{origin}/login"},
            {
                "step": "fill", "origin": f"{origin}/login",
                "locatorRole": "textbox", "locatorName": "Password",
                "valueRef": "env:OPS_BROWSER_VALUE_PASSWORD",
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
        command = " ".join([
            "node", "skills/browser-operations/scripts/browser-runner.mjs",
            "--step", "workflow",
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
        events: list[dict[str, object]] = [
            {
                "type": "tool_use", "id": "workflow-tool-1", "name": "Bash",
                "input": {"command": command},
            },
            {
                "type": "hook_event", "hook_event_name": "PreToolUse",
                "tool_use_id": "workflow-tool-1", "tool_name": "Bash",
            },
        ]
        if include_post:
            events.append({
                "type": "hook_event", "hook_event_name": "PostToolUse",
                "tool_use_id": "workflow-tool-1", "tool_name": "Bash",
            })
        events.append({
            "type": "tool_result", "tool_use_id": "workflow-tool-1",
            "content": json.dumps({
                "status": "ok" if reason_code == "WORKFLOW_VALIDATED" else "outcome-unknown",
                "reasonCode": reason_code, "step": "workflow",
                "operationId": "op-live-browser-001",
                "effect": "SENSITIVE_READ",
                "validationRequired": reason_code != "WORKFLOW_VALIDATED",
                "observation": None,
            }),
        })
        roles = [
            "audit-evidence-collector", "change-manager", "cloud-platform-operator",
            "database-operator", "diagnostic-operator", "incident-commander",
            "kubernetes-operator", "network-edge-operator", "observability-sre",
            "rca-facilitator", "release-cicd-operator", "security-operations-reviewer",
        ]
        events.extend(
            {
                "type": "status", "agent_type": role,
                **({"used_percentage": index + 1} if index < 5 else {}),
            }
            for index, role in enumerate(roles)
        )
        events.append({"type": "result", "result": "discarded"})
        path.write_text(
            "".join(json.dumps(event) + "\n" for event in events),
            encoding="utf-8",
        )

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
            "toolCalls": 2, "hookEvents": 2,
            "context": {
                "before": 1, "afterSkill": 2, "afterSubagent": 3,
                "afterDiscovery": 4, "afterUse": 5, "toolSearchMode": "available-used",
            },
            "cleanup": "verified",
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
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["capabilityState"], "ACTIVE")
        self.assertEqual(result["routeClass"], "persistent-one-shot")
        self.assertEqual(result["guardProof"], "exact-native-approval")
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

    def test_workflow_evidence_rejects_noncanonical_base64url_records(self) -> None:
        import sys

        sys.path.insert(0, str(ROOT / "tests"))
        from browser_operations_live import _decode_step  # noqa: PLC0415

        value: dict[str, object] = {"step": "navigate", "origin": "http://127.0.0.1:43111"}
        token = self._workflow_token(value)
        while len(token) % 4 == 0:
            value["marker"] = str(value.get("marker", "")) + "x"
            token = self._workflow_token(value)
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
        replacement = alphabet[alphabet.index(token[-1]) ^ 1]
        noncanonical = token[:-1] + replacement
        self.assertNotEqual(noncanonical, token)
        self.assertEqual(_decode_step(token), value)
        self.assertIsNone(_decode_step(noncanonical))

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
                    event = {"type": message_type, "message": {"content": [event]}}
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

        events = [
            {"type": "status", "used_percentage": value, "content": "discard me"}
            for value in (11, 22, 33, 44, 55)
        ] + [{"type": "result", "result": "discard me too"}]
        with tempfile.TemporaryDirectory() as directory:
            stream = Path(directory) / "stream.jsonl"
            stream.write_text(
                "".join(json.dumps(event) + "\n" for event in events),
                encoding="utf-8",
            )
            result = evaluate_stream(stream, "P004B_TEST_CANARY")
        self.assertEqual(result["contextPercentages"], [11, 22, 33, 44, 55])
        self.assertNotIn("content", json.dumps(result))
        self.assertNotIn("discard", json.dumps(result))


if __name__ == "__main__":
    unittest.main()
