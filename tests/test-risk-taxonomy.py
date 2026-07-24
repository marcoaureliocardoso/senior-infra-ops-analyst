#!/usr/bin/env python3
"""Regression tests for operational risk taxonomy validation."""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REFERENCE_REL = Path("references/linux-diagnostics.md")
SCRIPT_REL = Path("skills/command-driven-operations/scripts/risk-help.sh")
NESTED_REFERENCE_REL = Path(
    "skills/command-driven-operations/audit/nested-risk.md"
)
POWERSHELL_REL = Path(
    "skills/command-driven-operations/scripts/windows-baseline-readonly.ps1"
)


class RiskTaxonomyValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tempdir = tempfile.TemporaryDirectory()
        cls.sandbox = Path(cls.tempdir.name) / "package"
        shutil.copytree(
            ROOT,
            cls.sandbox,
            ignore=shutil.ignore_patterns(".git", ".worktrees", "__pycache__"),
        )
        cls.reference_path = cls.sandbox / REFERENCE_REL
        cls.original_reference = cls.reference_path.read_text(encoding="utf-8")
        cls.script_path = cls.sandbox / SCRIPT_REL
        cls.nested_reference_path = cls.sandbox / NESTED_REFERENCE_REL
        cls.powershell_path = cls.sandbox / POWERSHELL_REL
        cls.original_powershell = cls.powershell_path.read_text(encoding="utf-8")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tempdir.cleanup()

    def tearDown(self) -> None:
        self.reference_path.write_text(
            self.original_reference,
            encoding="utf-8",
        )
        if self.script_path.exists():
            self.script_path.unlink()
        if self.nested_reference_path.exists():
            self.nested_reference_path.unlink()
        self.powershell_path.write_text(
            self.original_powershell,
            encoding="utf-8",
        )

    def run_validator(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "tests/validate-content.py"],
            cwd=self.sandbox,
            capture_output=True,
            text=True,
            check=False,
        )

    def replace_once(self, old: str, new: str) -> str:
        self.assertIn(old, self.original_reference)
        return self.original_reference.replace(old, new, 1)

    def assert_rejected(self, content: str, expected_message: str) -> None:
        self.reference_path.write_text(content, encoding="utf-8")
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(expected_message, result.stdout + result.stderr)

    def test_valid_taxonomy_is_accepted(self) -> None:
        result = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_unknown_risk_label_is_rejected(self) -> None:
        content = self.replace_once(
            "| SAFE_READ_ONLY | `hostnamectl`",
            "| HIGH_RISK | `hostnamectl`",
        )
        self.assert_rejected(content, "unknown risk token HIGH_RISK")

    def test_plain_unknown_risk_label_is_rejected(self) -> None:
        content = self.replace_once(
            "| SAFE_READ_ONLY | `hostnamectl`",
            "| HIGH | `hostnamectl`",
        )
        self.assert_rejected(content, "unknown risk token HIGH")

    def test_modifier_only_classification_is_rejected(self) -> None:
        content = self.replace_once(
            "| SAFE_READ_ONLY + SENSITIVE_OUTPUT | `last -x",
            "| SENSITIVE_OUTPUT | `last -x",
        )
        self.assert_rejected(content, "classification requires exactly one base level")

    def test_multiple_base_levels_are_rejected(self) -> None:
        content = self.replace_once(
            "| SAFE_READ_ONLY | `hostnamectl`",
            "| SAFE_READ_ONLY + LOW_RISK_CHANGE | `hostnamectl`",
        )
        self.assert_rejected(content, "classification requires exactly one base level")

    def test_unknown_risk_label_in_nested_script_is_rejected(self) -> None:
        self.script_path.write_text(
            "#!/usr/bin/env bash\n# Risk: HIGH\n",
            encoding="utf-8",
        )
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("unknown risk token HIGH", result.stdout + result.stderr)

    def test_risk_classification_script_label_is_rejected(self) -> None:
        content = self.original_powershell.replace(
            "Risk classification: SAFE_READ_ONLY + SENSITIVE_OUTPUT.",
            "Risk classification: HIGH_RISK.",
            1,
        )
        self.powershell_path.write_text(content, encoding="utf-8")
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("unknown risk token HIGH_RISK", result.stdout + result.stderr)

    def test_multiline_multiple_bases_in_script_are_rejected(self) -> None:
        content = self.original_powershell.replace(
            "Risk classification:\n  SAFE_READ_ONLY + SENSITIVE_OUTPUT",
            "Risk classification:\n  SAFE_READ_ONLY + LOW_RISK_CHANGE",
            1,
        )
        self.powershell_path.write_text(content, encoding="utf-8")
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(
            "classification requires exactly one base level",
            result.stdout + result.stderr,
        )

    def test_non_classification_change_identifier_is_accepted(self) -> None:
        content = self.original_reference + (
            "\nVendor metadata may expose the uppercase identifier LAST_CHANGE.\n"
        )
        self.reference_path.write_text(content, encoding="utf-8")
        result = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_non_risk_read_only_identifier_is_accepted(self) -> None:
        content = self.original_reference + "\n- IAM role: `READ_ONLY`\n"
        self.reference_path.write_text(content, encoding="utf-8")
        result = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_modifier_only_prose_is_rejected(self) -> None:
        content = self.original_reference + (
            "\nScoped log reads are SENSITIVE_OUTPUT.\n"
        )
        self.assert_rejected(
            content,
            "classification requires exactly one base level",
        )

    def test_escaped_pipe_does_not_hide_invalid_risk_cell(self) -> None:
        self.nested_reference_path.parent.mkdir(parents=True, exist_ok=True)
        self.nested_reference_path.write_text(
            "| Action | Command | Risk |\n"
            "|---|---|---|\n"
            "| Inspect | `echo x \\| grep x` | HIGH_RISK |\n",
            encoding="utf-8",
        )
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("unknown risk token HIGH_RISK", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
