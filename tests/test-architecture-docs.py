#!/usr/bin/env python3
"""Mutation tests for required architecture decision records."""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_ADR_005 = (
    "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE",
    "72",
    "PreCompact",
    "PostCompact",
    "credential reuse",
    "numeric-only",
    "DeepSeek",
    "CLAUDE_CODE_AUTO_COMPACT_WINDOW",
    "Validation evidence",
)
REQUIRED_ADR_006 = (
    "AGENTS.md",
    "Canonical manifest",
    "Filesystem discovery",
    "Staging allowlist",
    "Symlinks and reparse points",
    "Isolated Nori validation",
    "External side effects",
    "Rollback",
)
REQUIRED_ADR_008 = (
    "references/native-execution-boundary.md",
    "CONFIGURED_UNPROVEN",
    "P005_GUARD_PROBE",
    "DENY_UNKNOWN_COMMAND",
    "Operator ownership",
    "Runtime proof",
    "nonce value emitted by the guard",
    "denied probe cannot invoke `PostToolUse`",
    "same-principal local actor",
    "Alternatives rejected",
    "Validation evidence",
    "P0-04B",
    "P3-16",
)
REQUIRED_ADR_009 = (
    "references/untrusted-input-handling.md",
    "Authority and provenance",
    "data, not instructions",
    "PROMPT_INJECTION_ATTEMPT",
    "PreToolUse",
    "Automatic persistence",
    "Active-model validation",
    "Alternatives rejected",
    "Residual risks",
    "P0-04B",
    "DG-POLICY",
    "DG-AUTHZ",
    "DG-EFFECT",
    "DG-EVIDENCE",
    "RC-AUTHORITY",
    "RC-TOOL-PROPOSAL",
    "RC-OUTPUT",
    "not a deterministic P0-06 merge gate",
    "CANARY_EXPOSED",
)


class ArchitectureDocumentationTests(unittest.TestCase):
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
        cls.index_path = cls.sandbox / "docs" / "architecture" / "README.md"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tempdir.cleanup()

    def setUp(self) -> None:
        if not self.index_path.exists():
            self.fail("architecture fixture missing from package")
        self.original_index = self.index_path.read_text(encoding="utf-8")

    def tearDown(self) -> None:
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.index_path.write_text(self.original_index, encoding="utf-8")
        source_dir = ROOT / "docs" / "architecture"
        for source in source_dir.glob("ADR-*.md"):
            target = self.index_path.parent / source.name
            shutil.copy2(source, target)

    def run_validator(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "tests/validate-content.py"],
            cwd=self.sandbox,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_architecture_docs_are_accepted(self) -> None:
        result = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_missing_architecture_index_is_rejected(self) -> None:
        self.index_path.unlink()
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing architecture decision index", result.stdout)

    def test_missing_index_entry_is_rejected(self) -> None:
        text = self.original_index.replace(
            "ADR-002-subagent-skill-preload.md", "ADR-002-omitted.md", 1
        )
        self.index_path.write_text(text, encoding="utf-8")
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("architecture index missing ADR", result.stdout)

    def test_missing_adr_file_is_rejected(self) -> None:
        (self.index_path.parent / "ADR-003-subagent-runtime-controls.md").unlink()
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing architecture decision record", result.stdout)

    def test_adr004_missing_required_heading_is_rejected(self) -> None:
        path = self.index_path.parent / "ADR-004-native-command-guard.md"
        text = path.read_text(encoding="utf-8")
        path.write_text(
            text.replace("## Credential handling", "## Credential notes", 1),
            encoding="utf-8",
        )
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ADR-004 missing required heading", result.stdout)

    def test_adr005_documents_implemented_continuity_contract(self) -> None:
        path = self.index_path.parent / "ADR-005-context-continuity-and-preventive-compaction.md"
        text = path.read_text(encoding="utf-8")
        for fragment in REQUIRED_ADR_005:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, text)
        for heading in (
            "## Implemented architecture", "## Enforcement points",
            "## Validation evidence", "## Consequences and limitations",
            "## Forward compatibility",
        ):
            self.assertIn(heading, text)

    def test_adr006_documents_canonical_nori_package_contract(self) -> None:
        path = self.index_path.parent / "ADR-006-canonical-nori-package.md"
        self.assertTrue(path.is_file(), "ADR-006 record is missing")
        text = path.read_text(encoding="utf-8")
        self.assertIn("ADR-006-canonical-nori-package.md", self.original_index)
        for fragment in REQUIRED_ADR_006:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, text)

    def test_adr008_documents_native_execution_boundary(self) -> None:
        path = self.index_path.parent / "ADR-008-native-execution-boundary.md"
        self.assertTrue(path.is_file(), "ADR-008 record is missing")
        text = path.read_text(encoding="utf-8")
        self.assertEqual(
            self.original_index.count("ADR-008-native-execution-boundary.md"), 1
        )
        for fragment in REQUIRED_ADR_008:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, text)
        for heading in (
            "## Context", "## Decision", "## Routing matrix",
            "## Operator ownership", "## Runtime proof",
            "## Alternatives rejected", "## Validation evidence",
            "## Consequences and residual risks", "## Follow-ups",
        ):
            self.assertIn(heading, text)

    def test_adr009_documents_global_prompt_injection_defense(self) -> None:
        path = self.index_path.parent / "ADR-009-global-prompt-injection-defense.md"
        self.assertTrue(path.is_file(), "ADR-009 record is missing")
        text = path.read_text(encoding="utf-8")
        self.assertEqual(
            self.original_index.count("ADR-009-global-prompt-injection-defense.md"),
            1,
        )
        for fragment in REQUIRED_ADR_009:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, text)
        for heading in (
            "## Context",
            "## Decision",
            "## Authority model",
            "## Enforcement layers",
            "## Sanitized records",
            "## Validation evidence",
            "## Alternatives rejected",
            "## Consequences and residual risks",
            "## Follow-ups",
        ):
            self.assertIn(heading, text)

    def test_operator_docs_expose_owned_configuration_and_rollback(self) -> None:
        for name in ("README.md", "docs.md"):
            text = (self.sandbox / name).read_text(encoding="utf-8")
            with self.subTest(name=name):
                for marker in (
                    "--check", "--apply", "--status-line", "--remove-owned",
                    "70", "75", "72", "CLAUDE_CODE_AUTO_COMPACT_WINDOW",
                ):
                    self.assertIn(marker, text)
                self.assertNotIn("CLAUDE_CODE_AUTO_COMPACT_WINDOW is the default", text)

    def test_operator_docs_explain_prompt_injection_defense_and_limits(self) -> None:
        for name in ("README.md", "docs.md"):
            text = (self.sandbox / name).read_text(encoding="utf-8")
            with self.subTest(name=name):
                for marker in (
                    "## Prompt-injection defense",
                    "references/untrusted-input-handling.md",
                    "data, not instructions",
                    "authentication data, not instructions",
                    "sanitized current-response record",
                    "native authorization gates remain authoritative",
                    "runtime-specific evidence, not immunity",
                    "deterministic package guarantees",
                    "runtime compatibility",
                    "RC-OUTPUT=FAIL",
                    "does not guarantee output confidentiality",
                    "not required for deterministic P0-06 merge acceptance",
                    "P0-04B",
                ):
                    self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
