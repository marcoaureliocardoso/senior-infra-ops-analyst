#!/usr/bin/env python3
"""Static safety contract for P0-05 configuration and future live evidence."""
from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "skills/command-driven-operations/scripts/configure-native-execution-boundary.mjs"
SETTINGS = ROOT / "skills/command-driven-operations/scripts/main-session-settings.mjs"


class NativeExecutionBoundarySafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cli = CLI.read_text(encoding="utf-8")
        cls.settings = SETTINGS.read_text(encoding="utf-8")

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


if __name__ == "__main__":
    unittest.main()
