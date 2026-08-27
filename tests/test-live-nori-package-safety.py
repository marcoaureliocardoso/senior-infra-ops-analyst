#!/usr/bin/env python3
"""Safety contract for isolated Nori package installation validation."""
from __future__ import annotations

import os
import re
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "tests" / "live-nori-package-smoke.sh"
TEMP_PROFILE = "personal/senior-infra-ops-analyst-package-smoke"
LINK_NAME = "senior-infra-ops-analyst-package-smoke"


class LiveNoriPackageSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.script = HARNESS.read_text(encoding="utf-8") if HARNESS.is_file() else ""

    def test_harness_exists(self) -> None:
        self.assertTrue(HARNESS.is_file(), "live Nori package harness is missing")

    def test_isolation_and_cleanup_contract_is_explicit(self) -> None:
        for marker in (
            "set -euo pipefail",
            "umask 077",
            "mktemp -d",
            'HOME="$WORK/home"',
            'XDG_CONFIG_HOME="$WORK/xdg"',
            'INSTALL_ROOT="$WORK/install"',
            'WORK_REAL="$(readlink -f "$WORK")"',
            'rm -rf -- "$WORK_REAL"',
            "trap cleanup EXIT",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.script)
        self.assertNotIn('rm -rf -- "$HOME"', self.script)

    def test_only_temporary_profile_and_agent_are_used(self) -> None:
        self.assertIn(TEMP_PROFILE, self.script)
        self.assertEqual(self.script.count(TEMP_PROFILE), 1)
        self.assertIn(f'LINK_NAME="{LINK_NAME}"', self.script)
        self.assertIn('link "$STAGING" --name "$LINK_NAME"', self.script)
        self.assertIn('switch "$PROFILE_NAME"', self.script)
        self.assertIn("--agent claude-code", self.script)
        self.assertNotRegex(
            self.script,
            r"(?:link|switch|unlink)[^\n]*personal/senior-infra-ops-analyst(?:\s|$)",
        )

    def test_external_side_effect_commands_are_never_invoked(self) -> None:
        for command in ("login", "logout", "upload", "upload-skill"):
            self.assertNotRegex(
                self.script,
                rf'"\$NORI_BIN"[^\n]*\s{re.escape(command)}(?:\s|$)',
            )
        self.assertNotIn("--force", self.script)

    def test_no_operator_configuration_or_sensitive_output_is_read(self) -> None:
        for marker in (
            "printenv",
            "env >",
            "set -x",
            "$REAL_HOME/.nori",
            "$REAL_HOME/.claude",
            "settings.json",
            "credentials",
            "authToken",
            "transcript",
            "$PROMPT",
            "--prompt",
            "prompt.txt",
            "prompt.json",
        ):
            self.assertNotIn(marker, self.script)

    def test_capabilities_are_detected_without_a_version_pin(self) -> None:
        for marker in (
            '"$NORI_BIN" --version',
            '"$NORI_BIN" --help',
            '"$NORI_BIN" link --help',
            '"$NORI_BIN" switch --help',
            "--install-dir",
            "--non-interactive",
            "--name",
            "--agent",
        ):
            self.assertIn(marker, self.script)
        self.assertNotRegex(self.script, r"0\.\d+\.\d+")

    def test_managed_block_and_unmanaged_sentinel_are_verified(self) -> None:
        for marker in (
            "operator-content-sentinel",
            "# BEGIN NORI-AI MANAGED BLOCK",
            "# END NORI-AI MANAGED BLOCK",
            "# Nori Skills System",
            "managedBlockCount",
            "canonicalContent",
            "unmanagedSentinel",
            "sourceSkillCount",
            "installedSkillCount",
            "packagedSkillsComplete",
            "unexpectedSkillsAbsent",
            "subagentCount",
            "subagentsExact",
            "subagentManifestsValid",
            "subagentSemanticExact",
            "legacySubagentsAbsent",
            "commandCount",
            "commandsExact",
        ):
            self.assertIn(marker, self.script)

    def test_installed_prompt_injection_policy_is_verified_content_free(self) -> None:
        for marker in (
            "prompt_injection_install_policy.py",
            '--installed-claude "$INSTALLED_CLAUDE"',
            '--installed-agents-dir "$INSTALLED_AGENTS_DIR"',
            "p006GlobalPolicyInstalled",
            "p006SubagentPolicyExact",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.script)

    def test_argument_validation_fails_closed(self) -> None:
        bash = os.environ.get("GIT_BASH", r"C:\Program Files\Git\bin\bash.exe")
        if not Path(bash).is_file() or not HARNESS.is_file():
            self.skipTest("Git Bash or harness is unavailable")
        cases = (
            (["--run-live"], "--nori-bin is required"),
            (["--run-live", "--nori-bin", "relative/nori"], "absolute path"),
            (
                ["--run-live", "--nori-bin", "/definitely/missing/nori"],
                "executable file",
            ),
            (["--self-test", "--run-live"], "choose exactly one mode"),
        )
        for arguments, expected in cases:
            with self.subTest(arguments=arguments):
                result = subprocess.run(
                    [bash, str(HARNESS), *arguments],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=10,
                )
                self.assertEqual(result.returncode, 2)
                self.assertIn(expected, result.stderr)


if __name__ == "__main__":
    unittest.main()
