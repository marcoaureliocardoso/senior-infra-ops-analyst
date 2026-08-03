#!/usr/bin/env python3
"""Executable regression tests for CI workflow security invariants."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_LANGUAGES = "language: [python, javascript-typescript]"


class CiWorkflowValidationTests(unittest.TestCase):
    def run_validator(self, language_line: str | None = None) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory(prefix="ci-workflow-validation-") as temporary:
            repository = Path(temporary)
            workflow_directory = repository / ".github" / "workflows"
            tests_directory = repository / "tests"
            workflow_directory.mkdir(parents=True)
            tests_directory.mkdir()

            source = (ROOT / ".github" / "workflows" / "security.yml").read_text(encoding="utf-8")
            if language_line is not None:
                mutated = source.replace(CANONICAL_LANGUAGES, language_line)
                self.assertNotEqual(mutated, source, "canonical CodeQL matrix was not found")
                source = mutated
            (workflow_directory / "security.yml").write_text(source, encoding="utf-8")
            shutil.copy2(ROOT / "tests" / "validate-ci-workflows.sh", tests_directory)

            return subprocess.run(
                ["bash", "tests/validate-ci-workflows.sh"],
                cwd=repository,
                check=False,
                capture_output=True,
                text=True,
            )

    def test_pristine_security_workflow_passes(self) -> None:
        result = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_codeql_language_set_is_exact(self) -> None:
        for language_line in (
            "language: [python]",
            "language: [javascript-typescript]",
            "language: [python, javascript-typescript, go]",
        ):
            with self.subTest(language_line=language_line):
                result = self.run_validator(language_line)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("security.yml CodeQL languages", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
