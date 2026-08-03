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
    def run_validator(
        self,
        language_line: str | None = None,
        *,
        init_languages: str | None = None,
        include_security_workflow: bool = True,
        misplace_init_wiring: bool = False,
        put_matrix_language_in_init_env: bool = False,
        nest_matrix_language_in_with_scalar: bool = False,
        duplicate_init_with: bool = False,
        duplicate_init_languages: bool = False,
        move_language_matrix_to_decoy_job: bool = False,
        add_codeql_matrix_expansion: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
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
            if init_languages is not None:
                canonical = "languages: ${{ matrix.language }}"
                mutated = source.replace(canonical, init_languages)
                self.assertNotEqual(mutated, source, "canonical CodeQL init wiring was not found")
                source = mutated
            if misplace_init_wiring:
                canonical = "languages: ${{ matrix.language }}"
                analyze_step = "- uses: github/codeql-action/analyze@v3"
                mutated = source.replace(canonical, "languages: python").replace(
                    analyze_step,
                    f"- name: Unrelated metadata\n        {canonical}\n      {analyze_step}",
                )
                self.assertNotEqual(mutated, source, "CodeQL wiring displacement failed")
                source = mutated
            if put_matrix_language_in_init_env:
                canonical_block = (
                    "        with:\n"
                    "          languages: ${{ matrix.language }}"
                )
                mutated_block = (
                    "        env:\n"
                    "          languages: ${{ matrix.language }}\n"
                    "        with:\n"
                    "          languages: python"
                )
                mutated = source.replace(canonical_block, mutated_block)
                self.assertNotEqual(mutated, source, "CodeQL init env mutation failed")
                source = mutated
            if nest_matrix_language_in_with_scalar:
                canonical_block = (
                    "        with:\n"
                    "          languages: ${{ matrix.language }}"
                )
                mutated_block = (
                    "        with:\n"
                    "          config: |\n"
                    "            languages: ${{ matrix.language }}\n"
                    "          languages: python"
                )
                mutated = source.replace(canonical_block, mutated_block)
                self.assertNotEqual(mutated, source, "CodeQL nested scalar mutation failed")
                source = mutated
            if duplicate_init_with:
                canonical_block = (
                    "        with:\n"
                    "          languages: ${{ matrix.language }}"
                )
                mutated_block = (
                    f"{canonical_block}\n"
                    "        with:\n"
                    "          languages: python"
                )
                mutated = source.replace(canonical_block, mutated_block)
                self.assertNotEqual(mutated, source, "CodeQL duplicate with mutation failed")
                source = mutated
            if duplicate_init_languages:
                canonical = "          languages: ${{ matrix.language }}"
                mutated = source.replace(canonical, f"{canonical}\n          languages: python")
                self.assertNotEqual(mutated, source, "CodeQL duplicate languages mutation failed")
                source = mutated
            if move_language_matrix_to_decoy_job:
                mutated = source.replace(
                    "        language: [python, javascript-typescript]",
                    "        runtime: [python, javascript-typescript]",
                ).replace(
                    "\n  shellcheck:\n",
                    "\n  matrix-decoy:\n"
                    "    runs-on: ubuntu-24.04\n"
                    "    timeout-minutes: 1\n"
                    "    strategy:\n"
                    "      matrix:\n"
                    "        language: [python, javascript-typescript]\n"
                    "    steps:\n"
                    "      - run: echo decoy\n"
                    "\n  shellcheck:\n",
                )
                self.assertNotEqual(mutated, source, "CodeQL decoy job mutation failed")
                source = mutated
            if add_codeql_matrix_expansion is not None:
                canonical = "        language: [python, javascript-typescript]"
                mutated = source.replace(
                    canonical,
                    f"{canonical}\n        {add_codeql_matrix_expansion}:\n"
                    "          - language: javascript-typescript",
                )
                self.assertNotEqual(mutated, source, "CodeQL matrix expansion mutation failed")
                source = mutated
            if include_security_workflow:
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

    def test_codeql_init_uses_matrix_language_exactly_once(self) -> None:
        for init_languages in ("languages: python", "languages: javascript-typescript", ""):
            with self.subTest(init_languages=init_languages):
                result = self.run_validator(init_languages=init_languages)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("security.yml CodeQL init wiring", result.stdout + result.stderr)

    def test_security_workflow_is_mandatory(self) -> None:
        result = self.run_validator(include_security_workflow=False)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("security.yml is required", result.stdout + result.stderr)

    def test_matrix_language_must_belong_to_the_init_step(self) -> None:
        result = self.run_validator(misplace_init_wiring=True)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("security.yml CodeQL init wiring", result.stdout + result.stderr)

    def test_matrix_language_must_be_the_init_with_parameter(self) -> None:
        result = self.run_validator(put_matrix_language_in_init_env=True)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("security.yml CodeQL init wiring", result.stdout + result.stderr)

    def test_nested_scalar_cannot_impersonate_the_init_with_parameter(self) -> None:
        result = self.run_validator(nest_matrix_language_in_with_scalar=True)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("security.yml CodeQL init wiring", result.stdout + result.stderr)

    def test_duplicate_init_mapping_keys_are_rejected(self) -> None:
        for mutation in (
            {"duplicate_init_with": True},
            {"duplicate_init_languages": True},
        ):
            with self.subTest(mutation=mutation):
                result = self.run_validator(**mutation)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("security.yml CodeQL init wiring", result.stdout + result.stderr)

    def test_language_matrix_must_belong_to_the_codeql_job(self) -> None:
        result = self.run_validator(move_language_matrix_to_decoy_job=True)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("security.yml CodeQL languages", result.stdout + result.stderr)

    def test_codeql_matrix_rejects_include_and_exclude_expansion(self) -> None:
        for key in ("include", "exclude"):
            with self.subTest(key=key):
                result = self.run_validator(add_codeql_matrix_expansion=key)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("security.yml CodeQL languages", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
