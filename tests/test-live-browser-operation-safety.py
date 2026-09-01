#!/usr/bin/env python3
"""Static and provider-free safety contract for the P0-04B live harness."""
from __future__ import annotations

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
            'switch "$PROFILE_NAME"',
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

    def test_package_gate_runs_only_provider_free_checks(self) -> None:
        gate = GATE.read_text(encoding="utf-8")
        for marker in (
            "python3 tests/test-live-browser-operation-safety.py",
            "bash -n tests/live-browser-operations-smoke.sh",
            "bash tests/live-browser-operations-smoke.sh --self-test",
        ):
            self.assertIn(marker, gate)
        self.assertNotIn("live-browser-operations-smoke.sh --run-live", gate)

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
            "capabilityState": "ACTIVE", "guardProof": "exact-deny", "roleCount": 12,
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
        ):
            with self.assertRaises(ValueError):
                validate_aggregate(mutation)
        self.assertNotIn("rawPrompt", json.dumps(validate_aggregate(value)))

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
