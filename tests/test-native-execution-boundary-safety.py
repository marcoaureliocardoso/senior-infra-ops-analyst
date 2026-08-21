#!/usr/bin/env python3
"""Static safety contract for P0-05 configuration and future live evidence."""
from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "skills/command-driven-operations/scripts/configure-native-execution-boundary.mjs"
SETTINGS = ROOT / "skills/command-driven-operations/scripts/main-session-settings.mjs"
LIVE = ROOT / "tests/live-native-execution-boundary-smoke.sh"
PACKAGE_GATE = ROOT / "tests/validate-package.sh"


class NativeExecutionBoundarySafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cli = CLI.read_text(encoding="utf-8")
        cls.settings = SETTINGS.read_text(encoding="utf-8")
        cls.live = LIVE.read_text(encoding="utf-8")
        cls.package_gate = PACKAGE_GATE.read_text(encoding="utf-8")

    def test_configuration_modules_have_no_network_or_process_execution(self) -> None:
        combined = self.cli + self.settings
        for forbidden in (
            "node:child_process",
            "node:http",
            "node:https",
            "node:net",
            "fetch(",
            "execSync",
            "spawnSync",
        ):
            self.assertNotIn(forbidden, combined)

    def test_configuration_never_reads_transcripts_credentials_or_home(self) -> None:
        combined = (self.cli + self.settings).lower()
        for forbidden in (
            "transcript_path",
            "read transcript",
            "credential",
            "password",
            "authorization",
            "homedir(",
            "process.env.home",
            "process.env.userprofile",
        ):
            self.assertNotIn(forbidden, combined)

    def test_no_recursive_delete_or_broad_target_is_present(self) -> None:
        self.assertNotRegex(self.cli, r"rm\([^\n]+recursive\s*:\s*true")
        self.assertNotIn("rmSync", self.cli)
        self.assertNotIn("rmdirSync", self.cli)
        self.assertNotRegex(self.cli, r"(?:rm|rmdir)\([^\n]*(?:homedir|\.root)")

    def test_transaction_record_is_content_free(self) -> None:
        transaction_literals = re.findall(
            r"atomicReplace\(paths\.transaction,\s*\{(.*?)\}\);",
            self.cli,
            re.DOTALL,
        )
        self.assertEqual(len(transaction_literals), 2)
        for literal in transaction_literals:
            self.assertNotRegex(
                literal.lower(),
                r"command|settings\s*:|prompt|transcript|secret|credential|token",
            )
            self.assertIn("ownershipTemporary", literal)

    def test_public_report_excludes_paths_commands_and_operator_values(self) -> None:
        report = re.search(
            r"function publicReport\(.*?\) \{(.*?)\n\}",
            self.cli,
            re.DOTALL,
        )
        self.assertIsNotNone(report)
        body = report.group(1)
        self.assertNotRegex(
            body.lower(),
            r"path|command|settings|ownership|environment|runtimeidentity",
        )
        for field in (
            "state",
            "reasonCode",
            "preHookExact",
            "postHookExact",
            "liveProof",
            "changed",
            "conflicts",
        ):
            self.assertIn(field, body)

    def test_live_proof_is_not_written_by_the_configurator(self) -> None:
        self.assertNotRegex(
            self.cli,
            r"(?:writeDurableFile|atomicReplace)\([^\n]+liveProof",
        )
        self.assertIn("liveProof: false", self.cli)

    def test_live_provider_use_is_explicitly_opt_in_and_acknowledged(self) -> None:
        self.assertIn("--self-test", self.live)
        self.assertIn("--run-live", self.live)
        self.assertIn("P0_05_LIVE_PROVIDER_ACK", self.live)
        self.assertIn("I_AUTHORIZE_BOUNDED_PROVIDER_USE", self.live)
        self.assertIn("provider credentials enter the disposable Claude process", self.live)

    def test_live_probe_is_exact_unknown_harmless_fixture(self) -> None:
        self.assertEqual(self.live.count("PROBE='printf P005_GUARD_PROBE'"), 1)
        self.assertGreaterEqual(self.live.count("$PROBE"), 1)
        self.assertNotRegex(
            self.live,
            re.compile(r"\b(?:kubectl|aws|az|gcloud|ssh)\s+(?:delete|drain|terminate|rm)\b"),
        )
        self.assertIn("DENY_UNKNOWN_COMMAND", self.live)

    def test_live_harness_uses_disposable_scopes_and_bounded_driver(self) -> None:
        self.assertIn('WORK="$(mktemp -d "$TMP_PARENT/p0-05-native-boundary.XXXXXX")"', self.live)
        self.assertIn('HOME="$WORK/home"', self.live)
        self.assertIn('CLAUDE_CONFIG_DIR="$HOME/.claude"', self.live)
        self.assertIn('PROJECT="$WORK/project"', self.live)
        self.assertIn('AUDIT_DIR="$WORK/audit"', self.live)
        self.assertIn("native-execution-boundary-pty.py", self.live)
        self.assertIn("timeout 300", self.live)
        self.assertIn('rm -rf -- "$WORK_REAL"', self.live)
        self.assertNotIn('rm -rf -- "$HOME"', self.live)

    def test_live_harness_does_not_retain_sensitive_or_terminal_content(self) -> None:
        lowered = self.live.lower()
        self.assertNotIn("transcript_path", lowered)
        self.assertNotIn("capture.pty", lowered)
        self.assertNotIn("prompt history", lowered)
        self.assertNotRegex(self.live, r"\benv\b[^\n]*\|")
        self.assertIn("ALLOWED_CLAUDE_ENV", self.live)
        self.assertIn("load-claude-env.py", self.live)
        self.assertNotRegex(self.live, r"\b(?:cat|cp)\b[^\n]*settings\.json")
        self.assertIn("--clean-environment", self.live)
        self.assertNotIn('env -i "${PROBE_ENV[@]}"', self.live)

    def test_real_provider_route_is_filesystem_isolated_before_claude_starts(self) -> None:
        self.assertIn("BWRAP_BIN", self.live)
        self.assertIn("--die-with-parent", self.live)
        self.assertIn('--bind "$WORK_REAL" "$WORK_REAL"', self.live)
        self.assertIn('--ro-bind "$CLAUDE_BIN" /opt/claude', self.live)
        self.assertIn("add_readonly_etc /etc/resolv.conf", self.live)
        self.assertNotIn("--ro-bind /etc /etc", self.live)
        self.assertIn('if [[ "$MODE" == "run-live" ]]', self.live)

    def test_main_hooks_are_removed_before_protected_executor_fallback(self) -> None:
        removal = self.live.index("--remove-owned")
        fallback = self.live.index("executor-fallback")
        self.assertLess(removal, fallback)
        self.assertEqual(self.live.count("--agent diagnostic-operator"), 1)
        self.assertIn("run_stage main-bypass bypassPermissions", self.live)

    def test_self_test_uses_fake_tools_and_package_gate_runs_it(self) -> None:
        self.assertIn("create_fake_claude", self.live)
        self.assertIn("create_fake_nori", self.live)
        self.assertIn('if [[ "$MODE" == "self-test" ]]', self.live)
        self.assertIn("python3 tests/test-native-execution-boundary-pty.py", self.package_gate)
        self.assertIn("bash -n tests/live-native-execution-boundary-smoke.sh", self.package_gate)
        self.assertIn(
            "bash tests/live-native-execution-boundary-smoke.sh --self-test",
            self.package_gate,
        )


if __name__ == "__main__":
    unittest.main()
