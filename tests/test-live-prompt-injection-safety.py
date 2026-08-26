#!/usr/bin/env python3
"""Static safety contract for the P0-06 active-model harness."""
from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "tests" / "live-prompt-injection-smoke.sh"
PACKAGE_GATE = ROOT / "tests" / "validate-package.sh"
ROLES = (
    "main",
    "audit-evidence-collector",
    "change-manager",
    "cloud-platform-operator",
    "database-operator",
    "diagnostic-operator",
    "incident-commander",
    "kubernetes-operator",
    "network-edge-operator",
    "observability-sre",
    "rca-facilitator",
    "release-cicd-operator",
    "security-operations-reviewer",
)


class LivePromptInjectionSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.script = HARNESS.read_text(encoding="utf-8") if HARNESS.is_file() else ""

    def setUp(self) -> None:
        if not HARNESS.is_file() and self._testMethodName != "test_harness_exists":
            self.skipTest("live prompt-injection harness is not implemented yet")

    def test_harness_exists(self) -> None:
        self.assertTrue(HARNESS.is_file(), "P0-06 live harness is missing")

    def test_explicit_ack_and_native_cli_safety_controls_are_required(self) -> None:
        for marker in (
            "P006_LIVE_ACK",
            "I_ACKNOWLEDGE_13_SYNTHETIC_MODEL_PROBES",
            "--no-session-persistence",
            "--permission-mode dontAsk",
            "--include-hook-events",
            "--output-format stream-json",
            "--max-turns 2",
            "env -i",
            "BWRAP_BIN",
            "umask 077",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.script)
        for forbidden in ("bypassPermissions", "--keep-artifacts", "set -x"):
            self.assertNotIn(forbidden, self.script)

    def test_exact_role_inventory_and_time_bounds_are_visible(self) -> None:
        for role in ROLES:
            with self.subTest(role=role):
                self.assertIn(role, self.script)
        self.assertIn("ROLE_TIMEOUT_SECONDS=120", self.script)
        self.assertIn("TOTAL_TIMEOUT_SECONDS=1800", self.script)
        self.assertIn('timeout "$ROLE_TIMEOUT_SECONDS"', self.script)
        self.assertIn("TOTAL_DEADLINE", self.script)

    def test_disposable_paths_and_immediate_raw_deletion_are_required(self) -> None:
        for marker in (
            "mktemp -d",
            "trap cleanup EXIT",
            'HOME="$WORK/home"',
            'XDG_CONFIG_HOME="$WORK/xdg/config"',
            'XDG_DATA_HOME="$WORK/xdg/data"',
            'XDG_CACHE_HOME="$WORK/xdg/cache"',
            'XDG_STATE_HOME="$WORK/xdg/state"',
            'PROJECT="$WORK/project"',
            'INSTALL_ROOT="$WORK/install"',
            'PROMPT_DIR="$WORK/prompts"',
            'STREAM_DIR="$WORK/streams"',
            'STATE_DIR="$WORK/state"',
            'AUDIT_DIR="$WORK/audit"',
            'rm -f -- "$prompt_path" "$stream_path"',
            'rm -rf -- "$WORK_REAL"',
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.script)
        self.assertNotIn('rm -rf -- "$HOME"', self.script)
        self.assertIn(
            "export HOME XDG_CONFIG_HOME XDG_DATA_HOME XDG_CACHE_HOME XDG_STATE_HOME",
            self.script,
        )
        for variable in (
            "XDG_CONFIG_HOME",
            "XDG_DATA_HOME",
            "XDG_CACHE_HOME",
            "XDG_STATE_HOME",
        ):
            self.assertLess(
                self.script.index(f'{variable}="$WORK/'),
                self.script.index('"$NORI_BIN" --non-interactive link'),
            )

    def test_provider_environment_is_allowlisted_and_never_printed(self) -> None:
        self.assertLess(
            self.script.index("SOURCE_CLAUDE_SETTINGS="),
            self.script.index('HOME="$WORK/home"'),
        )
        for marker in (
            "ALLOWED_CLAUDE_ENV=(",
            'load-claude-env.py" "$SOURCE_CLAUDE_SETTINGS"',
            'mkfifo "$CLAUDE_ENV_PIPE"',
            "ANTHROPIC_AUTH_TOKEN",
            "ANTHROPIC_API_KEY",
            "ANTHROPIC_BASE_URL",
            "ANTHROPIC_MODEL",
        ):
            self.assertIn(marker, self.script)
        for forbidden in ("printenv", "env >", "settings.json |", "authToken"):
            self.assertNotIn(forbidden, self.script)

    def test_standard_package_gate_runs_only_deterministic_mode(self) -> None:
        gate = PACKAGE_GATE.read_text(encoding="utf-8")
        for marker in (
            "python3 tests/test-prompt-injection-deny-tool.py",
            "python3 tests/test-live-prompt-injection-safety.py",
            "bash -n tests/live-prompt-injection-smoke.sh",
            "bash tests/live-prompt-injection-smoke.sh --self-test",
        ):
            self.assertIn(marker, gate)
        self.assertNotIn("live-prompt-injection-smoke.sh --run-live", gate)

    def test_installation_deny_hook_and_content_free_aggregation_are_mandatory(self) -> None:
        for marker in (
            "prompt_injection_install_policy.py",
            "prompt-injection-deny-tool.py",
            "P006_DENY_AUDIT_PATH",
            '"PreToolUse"',
            "evaluate_stream",
            "aggregate",
            "toolCallCount",
            "canaryExposureCount",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.script)
        self.assertIn(
            "results = [json.loads(value) for value in sys.argv[6:]]",
            self.script,
        )
        self.assertNotIn(
            "printf '%s\\n' \"${ROLE_RESULTS[@]}\" | python3 -",
            self.script,
        )
        self.assertNotIn(
            '[[ "${#ROLE_RESULTS[@]}" -eq 13 ]]',
            self.script,
        )

    def test_behavioral_failure_is_recorded_without_fail_fast(self) -> None:
        self.assertIn("classify_role_control", self.script)
        self.assertIn("validate_deny_audit", self.script)
        self.assertIn("runtime_inconclusive", self.script)
        self.assertIn('ROLE_RESULTS+=("$role_result")', self.script)
        self.assertIn('"CONTINUE")', self.script)
        self.assertIn('"ABORT_INCONCLUSIVE")', self.script)
        self.assertIn('"ABORT_BOUNDARY")', self.script)
        self.assertNotIn(
            '[[ "$role_outcome" == "PASS:NONE:0:0" ]] || failed',
            self.script,
        )

    def test_audited_tool_proposal_is_compatibility_failure_not_execution(self) -> None:
        self.assertIn("deny_audit_count", self.script)
        self.assertIn("toolCallCount", self.script)
        self.assertIn("ABORT_BOUNDARY", self.script)
        self.assertNotIn('[[ -s "$audit_path" ]]', self.script)

    def test_raw_role_files_are_removed_before_control_decision(self) -> None:
        deletion = self.script.index('rm -f -- "$prompt_path" "$stream_path"')
        decision = self.script.index('case "$role_control" in')
        self.assertLess(deletion, decision)

    def test_self_test_has_bounded_fixtures_and_no_real_dependency_lookup(self) -> None:
        for marker in (
            "passing.jsonl",
            "tool-call.jsonl",
            "canary.jsonl",
            "malformed.jsonl",
            "incomplete.jsonl",
            "mixed-axis.jsonl",
            "runtime_inconclusive",
            "validate_deny_audit",
            "classify_role_control",
            '"INCOMPATIBLE"',
            '"INCONCLUSIVE"',
            '"COMPATIBLE"',
            "live prompt injection parser self-test passed",
        ):
            self.assertIn(marker, self.script)
        self.assertIn('if [[ "$MODE" == "self-test" ]]', self.script)
        self.assertIn("self_test\n  exit 0", self.script)

    def test_real_mode_without_exact_ack_stops_before_dependency_checks(self) -> None:
        environment = os.environ.copy()
        environment.pop("P006_LIVE_ACK", None)
        result = subprocess.run(
            ["bash", str(HARNESS), "--run-live"],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("I_ACKNOWLEDGE_13_SYNTHETIC_MODEL_PROBES", result.stderr)
        self.assertNotIn("Claude Code CLI not found", result.stderr)

    def test_native_executable_claude_reaches_post_capability_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            claude = directory / "claude"
            nori = directory / "nori"
            bwrap = directory / "bwrap"
            node = directory / "node"
            node.write_text(
                "#!/usr/bin/env bash\n"
                "[[ \"${1:-}\" == '-p' ]] || exit 96\n"
                "printf '%s\\n' '22'\n",
                encoding="utf-8",
            )
            claude.write_text(
                "#!/usr/bin/env bash\n"
                "case \"${1:-}\" in\n"
                "  --help) printf '%s\\n' '--output-format --verbose "
                "--include-hook-events --no-session-persistence "
                "--permission-mode --agent' ;;\n"
                "  --version) printf '%s\\n' 'native Claude test double' ;;\n"
                "  *) exit 97 ;;\n"
                "esac\n",
                encoding="utf-8",
            )
            nori.write_text(
                "#!/usr/bin/env bash\n"
                "[[ \"${1:-}\" == '--help' ]] || exit 98\n"
                "printf '%s\\n' '--install-dir --non-interactive --agent'\n",
                encoding="utf-8",
            )
            bwrap.write_text("#!/usr/bin/env bash\nexit 99\n", encoding="utf-8")
            for executable in (claude, nori, bwrap, node):
                executable.chmod(0o700)

            environment = os.environ.copy()
            for key in (
                "ANTHROPIC_AUTH_TOKEN",
                "ANTHROPIC_API_KEY",
                "ANTHROPIC_BASE_URL",
                "ANTHROPIC_MODEL",
                "CLAUDE_CONFIG_DIR",
            ):
                environment.pop(key, None)
            environment.update({
                "P006_LIVE_ACK": "I_ACKNOWLEDGE_13_SYNTHETIC_MODEL_PROBES",
                "CLAUDE_BIN": str(claude),
                "NORI_BIN": str(nori),
                "BWRAP_BIN": str(bwrap),
                "CLAUDE_SETTINGS_SOURCE": str(directory / "missing-settings.json"),
                "HOME": str(directory / "operator-home"),
                "PATH": f"{directory}{os.pathsep}{environment['PATH']}",
            })
            result = subprocess.run(
                ["bash", str(HARNESS), "--run-live"],
                cwd=ROOT,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )

        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("provider credential is unavailable", result.stderr)
        self.assertNotIn("Claude Code capability detection failed", result.stderr)


if __name__ == "__main__":
    unittest.main()
