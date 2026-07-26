#!/usr/bin/env python3
"""Static safety contract for the opt-in P0-04 command-guard harness."""
from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / "tests" / "live-command-guard-smoke.sh").read_text(
    encoding="utf-8"
)


class LiveCommandGuardSafetyTests(unittest.TestCase):
    def test_isolated_generated_home_and_history(self) -> None:
        self.assertIn('WORK="$(mktemp -d "$TMP_PARENT/p0-04-command-guard.XXXXXX")"', SCRIPT)
        self.assertIn('HOME="$WORK/home"', SCRIPT)
        self.assertIn('CLAUDE_CONFIG_DIR="$HOME/.claude"', SCRIPT)
        self.assertIn("HISTFILE=/dev/null", SCRIPT)

    def test_cleanup_is_limited_to_verified_runner_directory(self) -> None:
        self.assertIn('WORK_REAL="$(readlink -f "$WORK")"', SCRIPT)
        self.assertIn('"$(readlink -f "$TMP_PARENT")"/p0-04-command-guard.*', SCRIPT)
        self.assertIn('rm -rf -- "$WORK_REAL"', SCRIPT)
        self.assertNotIn('rm -rf -- "$HOME"', SCRIPT)

    def test_targets_and_credentials_are_disposable(self) -> None:
        self.assertIn("SYNTH_SECRET_", SCRIPT)
        self.assertIn("http://127.0.0.1", SCRIPT)
        self.assertNotRegex(SCRIPT, r"https?://(?!127\.0\.0\.1)[A-Za-z0-9.-]+")
        self.assertIn("unset AWS_PROFILE AZURE_CONFIG_DIR CLOUDSDK_CONFIG KUBECONFIG", SCRIPT)
        self.assertNotIn(".aws/credentials", SCRIPT)
        self.assertNotIn(".kube/config", SCRIPT)
        self.assertIn("loopback-http-fixture.py", SCRIPT)
        self.assertIn("--port 0", SCRIPT)
        self.assertNotIn("python3 -m http.server", SCRIPT)
        self.assertIn("POST /reload", SCRIPT)

    def test_installed_validator_receives_both_roots(self) -> None:
        self.assertIn('--installed-agents-dir "$INSTALLED_AGENTS_DIR"', SCRIPT)
        self.assertIn('--installed-skills-dir "$INSTALLED_SKILLS_DIR"', SCRIPT)

    def test_permission_modes_are_exercised_only_in_live_isolation(self) -> None:
        self.assertIn("--permission-mode bypassPermissions", SCRIPT)
        self.assertIn("--dangerously-skip-permissions", SCRIPT)
        self.assertIn("BWRAP_BIN", SCRIPT)
        self.assertIn('env -i "${PROBE_ENV[@]}" "$BWRAP_BIN"', SCRIPT)
        self.assertIn('if [[ "$MODE" == "run-live" ]]', SCRIPT)
        self.assertEqual(SCRIPT.count("--agent diagnostic-operator"), 2)
        self.assertNotIn("Use diagnostic-operator", SCRIPT)

    def test_operator_settings_are_imported_through_an_allowlist_without_copying(self) -> None:
        source_capture = SCRIPT.index("SOURCE_CLAUDE_SETTINGS=")
        isolated_home = SCRIPT.index('export HOME="$WORK/home"')
        self.assertLess(source_capture, isolated_home)
        self.assertIn("ALLOWED_CLAUDE_ENV=(", SCRIPT)
        self.assertIn('load-claude-env.py" "$SOURCE_CLAUDE_SETTINGS"', SCRIPT)
        self.assertIn("ANTHROPIC_AUTH_TOKEN", SCRIPT)
        self.assertIn("ANTHROPIC_API_KEY", SCRIPT)
        self.assertIn('mkfifo "$CLAUDE_ENV_PIPE"', SCRIPT)
        self.assertIn('wait "$ENV_LOADER_PID"', SCRIPT)
        self.assertNotRegex(SCRIPT, r"\bcp\b[^\n]*settings\.json")
        self.assertNotRegex(SCRIPT, r"\bcat\b[^\n]*settings\.json")

    def test_bubblewrap_handles_usrmerge_without_overlaying_symlinks(self) -> None:
        self.assertIn("add_runtime_path /bin", SCRIPT)
        self.assertIn("add_runtime_path /lib", SCRIPT)
        self.assertIn("add_runtime_path /lib64", SCRIPT)
        self.assertIn('--symlink "$target" "$path"', SCRIPT)
        self.assertNotIn("--ro-bind /usr /usr --ro-bind /bin /bin", SCRIPT)
        self.assertIn('"$BWRAP_BIN" "${BWRAP_ARGS[@]}" /usr/bin/true', SCRIPT)
        self.assertNotIn("--uid 0", SCRIPT)
        self.assertNotIn("--gid 0", SCRIPT)

    def test_bubblewrap_exposes_only_minimal_readonly_network_configuration(self) -> None:
        self.assertIn("add_readonly_etc /etc/resolv.conf", SCRIPT)
        self.assertIn("add_readonly_etc /etc/hosts", SCRIPT)
        self.assertIn("add_readonly_etc /etc/nsswitch.conf", SCRIPT)
        self.assertIn("add_readonly_etc /etc/ssl", SCRIPT)
        self.assertIn("add_readonly_etc /etc/ca-certificates.conf", SCRIPT)
        self.assertIn('--ro-bind "$source" "$path"', SCRIPT)
        self.assertNotIn("--ro-bind /etc /etc", SCRIPT)

    def test_versions_are_observational_not_pinned(self) -> None:
        for marker in ("Observed Node.js", "Observed Nori", "Observed Claude Code", "Observed model"):
            self.assertIn(marker, SCRIPT)
        self.assertNotRegex(SCRIPT, r"Nori requires|Claude Code requires|node [<>=]+[0-9]")

    def test_artifacts_are_scanned_for_synthetic_markers(self) -> None:
        self.assertIn("scan_retained_artifacts", SCRIPT)
        self.assertIn("synthetic credential retained", SCRIPT)

    def test_no_unscoped_destructive_target_is_embedded(self) -> None:
        forbidden = re.compile(r"\b(?:kubectl|aws|az|gcloud|ssh)\s+(?:delete|drain|terminate|rm)\b")
        self.assertIsNone(forbidden.search(SCRIPT))


if __name__ == "__main__":
    unittest.main()
