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
            'configure-native-execution-boundary.mjs',
            'command-guard-launcher.sh',
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
        self.assertNotIn("--permission-mode dontAsk", self.script)
        self.assertIn('--permission-mode default', self.script)
        self.assertIn('--permission-prompt-tool "$PERMISSION_PROMPT_TOOL"', self.script)
        self.assertIn("P004B_PERMISSION_PROMPT_TOOL", self.script)
        self.assertIn("Claude Code does not advertise --permission-prompt-tool", self.script)
        self.assertIn("Claude Code does not advertise --include-hook-events", self.script)

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
    def _trusted_measurement(cls, nonce: str = "p004b-run-001") -> dict[str, object]:
        context_session = "context-main-001"
        return {
            "schemaVersion": 1,
            "runNonce": nonce,
            "workflowSessionIds": ["session-live-browser-001"],
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

    def test_live_mode_requires_one_bounded_operator_approval_handler_before_dependencies(self) -> None:
        if shutil.which("bash") is None:
            self.skipTest("bash is unavailable on this host")
        environment = os.environ.copy()
        environment.update({
            "P004B_LIVE_AUTHORIZED": "1",
            "P004B_LIVE_ACK": "I_ACKNOWLEDGE_BOUNDED_SYNTHETIC_BROWSER_PROBES",
        })
        environment.pop("P004B_PERMISSION_PROMPT_TOOL", None)
        missing = subprocess.run(
            ["bash", str(HARNESS), "--run-live"], cwd=ROOT, env=environment,
            capture_output=True, text=True, timeout=10, check=False,
        )
        self.assertEqual(missing.returncode, 2)
        self.assertIn("P004B_PERMISSION_PROMPT_TOOL", missing.stderr)

        environment["P004B_PERMISSION_PROMPT_TOOL"] = "mcp__approval__ask --broad"
        invalid = subprocess.run(
            ["bash", str(HARNESS), "--run-live"], cwd=ROOT, env=environment,
            capture_output=True, text=True, timeout=10, check=False,
        )
        self.assertEqual(invalid.returncode, 2)
        self.assertIn("P004B_PERMISSION_PROMPT_TOOL", invalid.stderr)

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
        self.assertEqual(active["status"], "pass")
        self.assertEqual(active["capabilityState"], "ACTIVE")
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
            self.assertEqual(result["status"], "pass")
            self.assertEqual(result["roleCount"], 12)

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
