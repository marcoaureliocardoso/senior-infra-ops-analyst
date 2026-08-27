#!/usr/bin/env python3
"""Mutation tests for bounded P0-06 security claims."""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = "tests/prompt_injection_claims.py"
MUTABLE = (
    "README.md",
    "docs.md",
    "CHANGELOG.md",
    "tests/validation-notes.md",
    "docs/architecture/ADR-009-global-prompt-injection-defense.md",
)


class PromptInjectionClaimsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tempdir = tempfile.TemporaryDirectory()
        cls.sandbox = Path(cls.tempdir.name) / "package"
        shutil.copytree(
            ROOT,
            cls.sandbox,
            ignore=shutil.ignore_patterns(
                ".git", ".worktrees", ".tmp", "__pycache__"
            ),
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tempdir.cleanup()

    def setUp(self) -> None:
        self.originals = {
            path: (self.sandbox / path).read_text(encoding="utf-8")
            for path in MUTABLE
        }

    def tearDown(self) -> None:
        for path, text in self.originals.items():
            (self.sandbox / path).write_text(text, encoding="utf-8")

    def run_validator(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, VALIDATOR, "--root", str(self.sandbox)],
            cwd=self.sandbox,
            capture_output=True,
            text=True,
            check=False,
        )

    def mutate(self, relative: str, old: str, new: str) -> None:
        path = self.sandbox / relative
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text)
        path.write_text(text.replace(old, new, 1), encoding="utf-8")

    def append(self, relative: str, addition: str) -> None:
        path = self.sandbox / relative
        path.write_text(
            path.read_text(encoding="utf-8") + addition,
            encoding="utf-8",
        )

    def test_current_claims_are_accepted(self) -> None:
        result = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_missing_deterministic_taxonomy_is_rejected(self) -> None:
        self.mutate(
            "docs/architecture/ADR-009-global-prompt-injection-defense.md",
            "DG-EFFECT",
            "DG-OMITTED",
        )
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing guarantee taxonomy", result.stdout)

    def test_universal_output_confidentiality_claim_is_rejected(self) -> None:
        self.append(
            "README.md",
            "\nThe package guarantees protected values are never emitted.\n",
        )
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("universal confidentiality claim", result.stdout)

    def test_equivalent_universal_confidentiality_claims_are_rejected(self) -> None:
        additions = (
            "\nProtected values are never emitted.\n",
            "\nModel output cannot ever expose protected values.\n",
            "\nThe package always prevents protected-value disclosure.\n",
        )
        for addition in additions:
            with self.subTest(addition=addition):
                self.append("README.md", addition)
                result = self.run_validator()
                (self.sandbox / "README.md").write_text(
                    self.originals["README.md"],
                    encoding="utf-8",
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("universal confidentiality claim", result.stdout)

    def test_monolithic_active_merge_gate_is_rejected(self) -> None:
        self.append(
            "docs.md",
            "\nThe active-model matrix must pass before P0-06 can merge.\n",
        )
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("monolithic active merge gate", result.stdout)

    def test_current_output_failure_cannot_be_hidden(self) -> None:
        self.mutate("README.md", "RC-OUTPUT=FAIL", "RC-OUTPUT=PASS")
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("current compatibility disclosure", result.stdout)

    def test_corrected_runtime_evidence_cannot_be_removed(self) -> None:
        self.mutate(
            "CHANGELOG.md",
            "65fd95da1c4890741180f2e2c9c80820d8421a4d",
            "OMITTED_CORRECTED_COMMIT",
        )
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("historical compatibility evidence", result.stdout)


if __name__ == "__main__":
    unittest.main()
