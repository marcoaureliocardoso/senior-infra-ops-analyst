#!/usr/bin/env python3
"""Static safety contract for the opt-in P0-04A live harness."""
from __future__ import annotations

import re
import os
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "tests" / "live-context-continuity-smoke.sh"
PTY_DRIVER = ROOT / "tests" / "claude-pty-driver.py"


class LiveContextContinuitySafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.script = HARNESS.read_text(encoding="utf-8") if HARNESS.is_file() else ""

    def test_harness_exists(self) -> None:
        self.assertTrue(HARNESS.is_file(), "live context continuity harness is missing")

    def test_required_contract_markers_are_present(self) -> None:
        for marker in (
            "set -euo pipefail", "umask 077", "mktemp -d", "CLAUDE_CONFIG_DIR",
            "P0_04A_LIVE_NORMAL_CREDENTIALS_ACK", "Bubblewrap", "--self-test",
            "--run-live", "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=5",
            "CLAUDE_CODE_AUTO_COMPACT_WINDOW", "context-continuity-evidence.json",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.script)

    def test_forbidden_credential_and_execution_patterns_are_absent(self) -> None:
        for marker in (
            "cp $REAL_HOME/.claude/settings.json",
            "cat $SOURCE_CLAUDE_SETTINGS",
            "set -x",
            "env >",
            "printenv",
            "--dangerously-skip-permissions",
        ):
            self.assertNotIn(marker, self.script)

    def test_generated_home_cleanup_and_content_capture_lifecycle_are_bounded(self) -> None:
        self.assertIn('WORK_REAL="$(readlink -f "$WORK")"', self.script)
        self.assertIn('HOME="$WORK/home"', self.script)
        self.assertIn('CLAUDE_CONFIG_DIR="$HOME/.claude"', self.script)
        self.assertIn('rm -rf -- "$WORK_REAL"', self.script)
        self.assertNotIn('rm -rf -- "$HOME"', self.script)
        for suffix in ("*.jsonl", "*.pty", "*.transcript", "*.requests", "*.prompt"):
            self.assertIn(suffix, self.script)
        self.assertIn("--keep-artifacts", self.script)
        self.assertIn("contains model content", self.script)

    def test_settings_import_is_allowlisted_nul_delimited_and_never_copied(self) -> None:
        self.assertIn("ALLOWED_CLAUDE_ENV=(", self.script)
        self.assertIn('load-claude-env.py" "$SOURCE_CLAUDE_SETTINGS"', self.script)
        self.assertIn('mkfifo "$CLAUDE_ENV_PIPE"', self.script)
        self.assertIn("read -r -d '' entry", self.script)
        self.assertNotRegex(self.script, r"\bcp\b[^\n]*settings\.json")
        self.assertNotRegex(self.script, r"\bcat\b[^\n]*settings\.json")

    def test_interactive_onboarding_and_trust_are_generated_not_copied(self) -> None:
        self.assertIn("seed_isolated_onboarding", self.script)
        self.assertIn("hasCompletedOnboarding", self.script)
        self.assertIn("hasCompletedProjectOnboarding", self.script)
        self.assertIn("hasTrustDialogAccepted", self.script)
        self.assertIn('settings["theme"] = "dark"', self.script)
        self.assertIn('"$HOME/.claude.json"', self.script)
        self.assertNotRegex(self.script, r"\bcp\b[^\n]*\.claude\.json")
        self.assertNotIn('"model": "operator-model"', self.script)
        self.assertIn("claude-pty-driver.py", self.script)
        driver = PTY_DRIVER.read_text(encoding="utf-8")
        self.assertIn('b"\\r"', driver)
        self.assertIn("wait_for", driver)
        self.assertIn('"TERM=xterm-256color"', self.script)
        self.assertIn('DRIVER_TIMEOUT=$((MANUAL_TIMEOUT - 5))', self.script)
        self.assertNotIn('/opt/claude --agent diagnostic-operator', self.script)

    def test_live_process_is_non_root_bubblewrap_and_time_bounded(self) -> None:
        self.assertIn("BWRAP_BIN", self.script)
        self.assertIn('"$BWRAP_BIN" "${BWRAP_ARGS[@]}" /usr/bin/true', self.script)
        self.assertIn("MANUAL_TIMEOUT=600", self.script)
        self.assertIn("AUTOMATIC_TIMEOUT=600", self.script)
        self.assertIn('timeout "$MANUAL_TIMEOUT"', self.script)
        self.assertNotIn("--uid 0", self.script)
        self.assertNotIn("--gid 0", self.script)
        self.assertIn("/usr/bin/id -u", self.script)

    def test_confirmed_window_option_is_live_only_and_requires_one_value(self) -> None:
        bash = os.environ.get("GIT_BASH", r"C:\Program Files\Git\bin\bash.exe")
        if not Path(bash).is_file():
            self.skipTest("Git Bash is unavailable")

        cases = (
            (["--self-test", "--confirmed-window-diagnostic"], "requires a positive integer"),
            (["--self-test", "--confirmed-window-diagnostic", "1000000"], "valid only with --run-live"),
            (["--run-live", "--confirmed-window-diagnostic", "invalid"], "requires a positive integer"),
            (
                [
                    "--run-live", "--confirmed-window-diagnostic", "1000000",
                    "--confirmed-window-diagnostic", "1000000",
                ],
                "at most once",
            ),
        )
        environment = os.environ.copy()
        environment["P0_04A_LIVE_NORMAL_CREDENTIALS_ACK"] = (
            "I_ACCEPT_PROVIDER_CREDENTIAL_EGRESS_RISK"
        )
        for arguments, marker in cases:
            with self.subTest(arguments=arguments):
                result = subprocess.run(
                    [bash, str(HARNESS), *arguments],
                    cwd=ROOT,
                    env=environment,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                self.assertEqual(result.returncode, 2)
                self.assertIn(marker, result.stderr)

    def test_confirmed_window_value_is_injected_only_into_automatic_child(self) -> None:
        assignment = 'CLAUDE_CODE_AUTO_COMPACT_WINDOW="$CONFIRMED_WINDOW_DIAGNOSTIC"'
        self.assertEqual(self.script.count(assignment), 1)
        automatic = self.script.index('--dialogue automatic')
        assignment_position = self.script.index(assignment)
        self.assertLess(assignment_position, automatic)
        self.assertLess(automatic - assignment_position, 800)

    def test_network_targets_are_loopback_only_and_no_production_target_is_embedded(self) -> None:
        self.assertIn("127.0.0.1", self.script)
        self.assertIn("run_mock_window_probe", self.script)
        self.assertIn("mock-anthropic-gateway.py", self.script)
        self.assertNotRegex(
            self.script,
            r"https?://(?!127\.0\.0\.1|localhost)[A-Za-z0-9.-]+",
        )
        forbidden = re.compile(r"\b(?:kubectl|aws|az|gcloud|ssh)\s+(?:delete|drain|terminate|rm)\b")
        self.assertIsNone(forbidden.search(self.script))

    def test_evidence_is_normalized_scanned_and_content_files_are_deleted(self) -> None:
        self.assertIn("context-inventory.mjs", self.script)
        self.assertIn("find_forbidden_evidence", self.script)
        self.assertIn('"$PROBES/automatic-driver.jsonl"', self.script)
        self.assertIn("CLAUDE_CODE_EFFORT_LEVEL=low", self.script)
        self.assertIn('CLAUDE_RUNTIME_ARGS+=(--autocompact auto)', self.script)
        self.assertIn('window_tokens', self.script)
        self.assertIn('target_tokens', self.script)
        self.assertIn('"windowTokens"', self.script)
        self.assertIn('live-context-window-recorder.py', self.script)
        self.assertIn('--events "$PROBES/live-context-window-events.jsonl"', self.script)
        self.assertNotIn('--capture "$PROBES/manual.pty" --confirmed', self.script)
        self.assertIn('--dialogue automatic', self.script)
        self.assertIn('--filler "$PROBES/automatic.prompt"', self.script)
        self.assertIn('--compact-events "$PROBES/live-compact-hook-events.jsonl"', self.script)
        self.assertIn("live-compact-event-recorder.py", self.script)
        self.assertNotIn('--append-system-prompt-file "$PROBES/automatic.prompt"', self.script)
        self.assertIn('set_isolated_diagnostic_threshold 5', self.script)
        self.assertIn('set_isolated_diagnostic_threshold 72', self.script)
        self.assertNotIn("emit bounded repetitive synthetic text", self.script)
        self.assertIn("SYNTH_SECRET", self.script)
        self.assertNotIn("credential-first.jsonl", self.script)
        self.assertIn("rm -f --", self.script)
        self.assertIn("context-continuity-evidence.json", self.script)
        self.assertIn('"reasonCode"] == "WINDOW_REPORTING_DIVERGENCE"', self.script)
        self.assertIn('CLAUDE_CODE_AUTO_COMPACT_WINDOW="$MOCK_OBSERVED_WINDOW"', self.script)


if __name__ == "__main__":
    unittest.main()
