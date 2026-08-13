#!/usr/bin/env python3
"""Executable regression tests for CI workflow security invariants."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_LANGUAGES = "language: [python, javascript-typescript]"
CODEQL_SHA = "5595ccaf912efad79be6eef63a5619ff05969be3"
CODEQL_INIT_USE = f"github/codeql-action/init@{CODEQL_SHA} # v4"
CODEQL_ANALYZE_USE = f"github/codeql-action/analyze@{CODEQL_SHA} # v4"
PYTHON_MATRIX_BLOCK = (
    "    strategy:\n"
    "      fail-fast: false\n"
    "      matrix:\n"
    "        python-version: ['3.12', '3.14']"
)
PYTHON_WIRING = "          python-version: ${{ matrix.python-version }}"
SHELLCHECK_VERSION = "0.11.0"
SHELLCHECK_SHA256 = "8c3be12b05d5c177a04c29e3c78ce89ac86f1595681cab149b65b97c4e227198"
SHELLCHECK_URL = (
    "https://github.com/koalaman/shellcheck/releases/download/v0.11.0/"
    "shellcheck-v0.11.0.linux.x86_64.tar.xz"
)
EXPECTED_ACTION_USES = {
    "checkout": "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1",
    "setup-python": "actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97 # v7.0.0",
    "markdownlint": (
        "DavidAnson/markdownlint-cli2-action@"
        "21c1be1b93ad9ed58fa840aacc3f279cde2a72ff # v24.2.0"
    ),
    "cspell": (
        "streetsidesoftware/cspell-action@"
        "de2a73e963e7443969755b648a1008f77033c5b2 # v8.4.0"
    ),
    "codeql-init": CODEQL_INIT_USE,
    "codeql-analyze": CODEQL_ANALYZE_USE,
    "upload-artifact": (
        "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a # v7.0.1"
    ),
    "gh-release": (
        "softprops/action-gh-release@3d0d9888cb7fd7b750713d6e236d1fcb99157228 # v3.0.2"
    ),
}


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
        replace_init_with_shaped_scalar: bool = False,
        remove_analyze_step: bool = False,
        conditional_codeql_step: str | None = None,
        continue_on_error_step: str | None = None,
        codeql_job_control: str | None = None,
        step_control_style: str = "plain",
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
                analyze_step = f"- uses: {CODEQL_ANALYZE_USE}"
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
            if replace_init_with_shaped_scalar:
                canonical_block = (
                    f"      - uses: {CODEQL_INIT_USE}\n"
                    "        with:\n"
                    "          languages: ${{ matrix.language }}"
                )
                mutated_block = (
                    "      - name: Init-shaped scalar\n"
                    "        env:\n"
                    "          CODEQL_TEXT: |\n"
                    f"            - uses: {CODEQL_INIT_USE}\n"
                    "              with:\n"
                    "                languages: ${{ matrix.language }}\n"
                    "        run: echo ignored"
                )
                mutated = source.replace(canonical_block, mutated_block)
                self.assertNotEqual(mutated, source, "CodeQL init scalar mutation failed")
                source = mutated
            if remove_analyze_step:
                canonical = f"      - uses: {CODEQL_ANALYZE_USE}"
                mutated = source.replace(canonical, "      - run: echo analysis-disabled")
                self.assertNotEqual(mutated, source, "CodeQL analyze removal failed")
                source = mutated
            if conditional_codeql_step is not None:
                action_use = {
                    "init": CODEQL_INIT_USE,
                    "analyze": CODEQL_ANALYZE_USE,
                }[conditional_codeql_step]
                canonical = f"      - uses: {action_use}"
                control = "if: matrix.language == 'python'"
                if step_control_style == "quoted":
                    control = '"if": matrix.language == \'python\''
                elif step_control_style == "explicit":
                    control = "? if\n        : matrix.language == 'python'"
                elif step_control_style == "alias":
                    control = (
                        "env:\n          CONTROL_KEY: &control_key if\n"
                        "        *control_key: matrix.language == 'python'"
                    )
                elif step_control_style == "tagged":
                    control = "!!str if: matrix.language == 'python'"
                mutated = source.replace(
                    canonical,
                    f"{canonical}\n        {control}",
                )
                self.assertNotEqual(mutated, source, "CodeQL conditional step mutation failed")
                source = mutated
            if continue_on_error_step is not None:
                action_use = {
                    "init": CODEQL_INIT_USE,
                    "analyze": CODEQL_ANALYZE_USE,
                }[continue_on_error_step]
                canonical = f"      - uses: {action_use}"
                control = "continue-on-error: true"
                if step_control_style == "quoted":
                    control = '"continue-on-error": true'
                elif step_control_style == "explicit":
                    control = "? continue-on-error\n        : true"
                elif step_control_style == "alias":
                    control = (
                        "env:\n          CONTROL_KEY: &control_key continue-on-error\n"
                        "        *control_key: true"
                    )
                elif step_control_style == "tagged":
                    control = "!!str continue-on-error: true"
                mutated = source.replace(
                    canonical,
                    f"{canonical}\n        {control}",
                )
                self.assertNotEqual(mutated, source, "CodeQL continue-on-error mutation failed")
                source = mutated
            if codeql_job_control is not None:
                canonical = "  codeql:"
                mutated = source.replace(canonical, f"{canonical}\n    {codeql_job_control}")
                self.assertNotEqual(mutated, source, "CodeQL job control mutation failed")
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

    def test_init_shaped_scalar_cannot_impersonate_a_step(self) -> None:
        result = self.run_validator(replace_init_with_shaped_scalar=True)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("security.yml CodeQL init wiring", result.stdout + result.stderr)

    def test_codeql_analyze_is_a_mandatory_direct_step(self) -> None:
        result = self.run_validator(remove_analyze_step=True)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("security.yml CodeQL steps", result.stdout + result.stderr)

    def test_codeql_security_steps_are_unconditional_and_fail_closed(self) -> None:
        for parameter in ("conditional_codeql_step", "continue_on_error_step"):
            for step in ("init", "analyze"):
                for style in ("plain", "quoted", "explicit", "alias", "tagged"):
                    with self.subTest(parameter=parameter, step=step, style=style):
                        result = self.run_validator(
                            **{parameter: step},
                            step_control_style=style,
                        )
                        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                        self.assertIn("security.yml CodeQL steps", result.stdout + result.stderr)

    def test_codeql_job_is_unconditional_and_fail_closed(self) -> None:
        for control in (
            "if: false",
            "continue-on-error: true",
            "\"if\": false",
            "'continue-on-error': true",
            "? if\n    : false",
            "? continue-on-error\n    : true",
            "env:\n      CONTROL_KEY: &control_key if\n    *control_key: false",
            "env:\n      CONTROL_KEY: &control_key continue-on-error\n    *control_key: true",
            "!!str if: false",
            "!!str continue-on-error: true",
        ):
            with self.subTest(control=control):
                result = self.run_validator(codeql_job_control=control)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("security.yml CodeQL steps", result.stdout + result.stderr)


class WorkflowToolchainTests(unittest.TestCase):
    def workflow_text(self, name: str) -> str:
        return (ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")

    def run_mutated_validator(
        self,
        workflow_name: str,
        canonical: str,
        replacement: str,
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory(prefix="toolchain-workflow-validation-") as temporary:
            repository = Path(temporary)
            workflow_directory = repository / ".github" / "workflows"
            tests_directory = repository / "tests"
            shutil.copytree(ROOT / ".github" / "workflows", workflow_directory)
            tests_directory.mkdir()
            shutil.copy2(ROOT / "tests" / "validate-ci-workflows.sh", tests_directory)

            path = workflow_directory / workflow_name
            source = path.read_text(encoding="utf-8")
            mutated = source.replace(canonical, replacement, 1)
            self.assertNotEqual(mutated, source, f"canonical text not found in {workflow_name}")
            path.write_text(mutated, encoding="utf-8")

            return subprocess.run(
                ["bash", "tests/validate-ci-workflows.sh"],
                cwd=repository,
                check=False,
                capture_output=True,
                text=True,
            )

    def test_repository_actions_match_approved_immutable_releases(self) -> None:
        corpus = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted((ROOT / ".github" / "workflows").glob("*.yml"))
        )
        for name, expected in EXPECTED_ACTION_USES.items():
            with self.subTest(action=name):
                self.assertIn(f"uses: {expected}", corpus)

        for line in corpus.splitlines():
            match = re.search(r"\buses:\s*([^\s#]+)(?:\s+#\s*(\S+))?\s*$", line)
            if match is None or match.group(1).startswith("./"):
                continue
            reference = match.group(1)
            self.assertIn("@", reference, line)
            revision = reference.rsplit("@", 1)[1]
            self.assertRegex(revision, r"^[0-9a-f]{40}$", line)
            self.assertIsNotNone(match.group(2), line)

    def test_mutable_or_malformed_action_references_are_rejected(self) -> None:
        canonical = f"uses: {EXPECTED_ACTION_USES['markdownlint']}"
        for replacement in (
            "uses: DavidAnson/markdownlint-cli2-action@v24",
            "uses: DavidAnson/markdownlint-cli2-action@21c1be1",
            "uses: DavidAnson/markdownlint-cli2-action@gggggggggggggggggggggggggggggggggggggggg # v24.2.0",
            "uses: DavidAnson/markdownlint-cli2-action@21C1BE1B93AD9ED58FA840AACC3F279CDE2A72FF # v24.2.0",
            "uses: DavidAnson/markdownlint-cli2-action@21c1be1b93ad9ed58fa840aacc3f279cde2a72ff",
        ):
            with self.subTest(replacement=replacement):
                result = self.run_mutated_validator("ci.yml", canonical, replacement)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn(
                    "external action must use a full commit SHA",
                    result.stdout + result.stderr,
                )

    def test_alternate_yaml_keys_cannot_hide_an_action_reference(self) -> None:
        canonical = f"uses: {EXPECTED_ACTION_USES['markdownlint']}"
        for replacement in (
            f'"uses": {EXPECTED_ACTION_USES["markdownlint"]}',
            f"? uses\n        : {EXPECTED_ACTION_USES['markdownlint']}",
            (
                "env:\n"
                "          CONTROL_KEY: &control_key uses\n"
                f"        *control_key: {EXPECTED_ACTION_USES['markdownlint']}"
            ),
            f"!!str uses: {EXPECTED_ACTION_USES['markdownlint']}",
        ):
            with self.subTest(replacement=replacement):
                result = self.run_mutated_validator("ci.yml", canonical, replacement)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("canonical YAML mapping keys", result.stdout + result.stderr)

    def test_python_schema_matrix_is_exact_and_directly_wired(self) -> None:
        source = self.workflow_text("ci.yml")
        self.assertIn(PYTHON_MATRIX_BLOCK, source)
        self.assertEqual(source.count(PYTHON_WIRING), 1)

    def test_python_schema_matrix_mutations_are_rejected(self) -> None:
        for replacement in (
            PYTHON_MATRIX_BLOCK.replace("['3.12', '3.14']", "['3.12']"),
            PYTHON_MATRIX_BLOCK.replace("['3.12', '3.14']", "['3.14']"),
            PYTHON_MATRIX_BLOCK.replace("['3.12', '3.14']", "['3.12', '3.13', '3.14']"),
            PYTHON_MATRIX_BLOCK.replace(
                "        python-version: ['3.12', '3.14']",
                "        python-version: ['3.12', '3.14']\n        exclude:\n          - python-version: '3.14'",
            ),
            PYTHON_MATRIX_BLOCK.replace(
                "        python-version: ['3.12', '3.14']",
                "        python-version: ['3.12', '3.14']\n        include:\n          - python-version: '3.13'",
            ),
        ):
            with self.subTest(replacement=replacement):
                result = self.run_mutated_validator("ci.yml", PYTHON_MATRIX_BLOCK, replacement)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("nori-schema Python matrix", result.stdout + result.stderr)

    def test_python_matrix_in_a_decoy_job_cannot_satisfy_nori_schema(self) -> None:
        canonical = (
            "\n  nori-schema:\n"
            "    runs-on: ubuntu-24.04\n"
            "    timeout-minutes: 5\n"
            f"{PYTHON_MATRIX_BLOCK}"
        )
        replacement = (
            "\n  python-matrix-decoy:\n"
            "    runs-on: ubuntu-24.04\n"
            "    timeout-minutes: 1\n"
            f"{PYTHON_MATRIX_BLOCK}\n"
            "    steps:\n"
            "      - run: echo decoy\n"
            "\n  nori-schema:\n"
            "    runs-on: ubuntu-24.04\n"
            "    timeout-minutes: 5\n"
            "    strategy:\n"
            "      fail-fast: false\n"
            "      matrix:\n"
            "        runtime: ['3.12', '3.14']"
        )
        result = self.run_mutated_validator("ci.yml", canonical, replacement)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("nori-schema Python matrix", result.stdout + result.stderr)

    def test_python_schema_wiring_and_controls_are_fail_closed(self) -> None:
        mutations = (
            (PYTHON_WIRING, "          python-version: '3.14'", "Python setup wiring"),
            ("  nori-schema:\n", "  nori-schema:\n    if: false\n", "Python setup wiring"),
            (
                f"      - uses: {EXPECTED_ACTION_USES['setup-python']}\n",
                f"      - uses: {EXPECTED_ACTION_USES['setup-python']}\n        continue-on-error: true\n",
                "Python setup wiring",
            ),
        )
        for canonical, replacement, message in mutations:
            with self.subTest(replacement=replacement):
                result = self.run_mutated_validator("ci.yml", canonical, replacement)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn(message, result.stdout + result.stderr)

    def test_shellcheck_release_is_checksum_verified_before_use(self) -> None:
        source = self.workflow_text("security.yml")
        self.assertIn(SHELLCHECK_URL, source)
        self.assertIn(SHELLCHECK_SHA256, source)
        self.assertIn("sha256sum --check --strict", source)
        self.assertIn('echo "$RUNNER_TEMP/shellcheck-v0.11.0" >> "$GITHUB_PATH"', source)
        self.assertIn("version: 0.11.0", source)
        self.assertLess(source.index(SHELLCHECK_URL), source.index("shellcheck -x"))

    def test_shellcheck_supply_chain_mutations_are_rejected(self) -> None:
        mutations = (
            (SHELLCHECK_URL, SHELLCHECK_URL.replace("v0.11.0", "v0.10.0")),
            (SHELLCHECK_URL, SHELLCHECK_URL.replace("github.com", "downloads.example.com")),
            (SHELLCHECK_SHA256, "0" * 64),
            ("sha256sum --check --strict", "sha256sum --check"),
            ("sha256sum --check --strict", "true"),
            ("version: 0.11.0", "version: 0.10.0"),
            ("version: 0.11.0", "version check removed"),
            (
                "      - name: Provision verified ShellCheck 0.11.0",
                "      - name: Run unverified ShellCheck first\n"
                "        run: shellcheck -x tests/validate-package.sh\n"
                "      - name: Provision verified ShellCheck 0.11.0",
            ),
        )
        for canonical, replacement in mutations:
            with self.subTest(replacement=replacement):
                result = self.run_mutated_validator("security.yml", canonical, replacement)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("ShellCheck 0.11.0 provisioning", result.stdout + result.stderr)

    def test_package_gate_runs_nori_contract_suites_before_schema(self) -> None:
        source = (ROOT / "tests" / "validate-package.sh").read_text(
            encoding="utf-8"
        )
        commands = (
            "python3 tests/test-nori-package-contract.py",
            "python3 tests/test-content-discovery.py",
            "python3 tests/test-nori-staging.py",
            "python3 tests/test-nori-archive.py",
            "python3 scripts/build_nori_staging.py --source . --check-source",
            "python3 tests/validate-schema.py",
        )
        positions = []
        for command in commands:
            self.assertEqual(
                source.count(command), 1, f"package gate must run once: {command}"
            )
            positions.append(source.index(command))
        self.assertEqual(positions, sorted(positions))

    def test_make_package_archives_only_generated_staging(self) -> None:
        source = (ROOT / "Makefile").read_text(encoding="utf-8")
        self.assertIn("stage: validate-local", source)
        self.assertIn("scripts/build_nori_staging.py", source)
        self.assertIn("package: stage", source)
        self.assertIn("scripts/build_nori_archive.py", source)
        self.assertIn('--staging "$(STAGING_DIR)"', source)
        self.assertNotIn("zip -r", source)


if __name__ == "__main__":
    unittest.main()
