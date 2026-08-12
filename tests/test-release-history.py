#!/usr/bin/env python3
"""Mutation tests for the curated changelog release-history contract."""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
README_HEADING = "## Version history"
README_LINK = (
    "See [CHANGELOG.md](CHANGELOG.md) for unpublished package states, tagged\n"
    "versions, and release notes."
)
UNRELEASED_HEADING = "## Unreleased package states"
TAGGED_HEADING = "## Tagged versions"
CURRENT_UNRELEASED = (
    "### 0.12.0 (unreleased) - declared 2026-08-08; updated through 2026-08-12"
)
UNPUBLISHED_LEDGER = [
    ("0.12.0", "2026-08-08", "2026-08-12"),
    ("0.11.1", "2026-08-08", None),
    ("0.11.0", "2026-07-26", None),
    ("0.9.1", "2026-07-23", None),
    ("0.9.0", "2026-07-23", None),
    ("0.8.0", "2026-07-23", None),
]
TAGGED_LEDGER = [
    ("0.10.0", "2026-07-27"),
    ("0.7.0", "2026-07-20"),
    ("0.6.1", "2026-07-20"),
    ("0.6.0", "2026-07-11"),
    ("0.5.1", "2026-07-09"),
    ("0.5.0", "2026-07-09"),
    ("0.4.4", "2026-07-08"),
    ("0.4.3", "2026-07-08"),
    ("0.4.2", "2026-07-08"),
    ("0.4.1", "2026-07-08"),
    ("0.4.0", "2026-07-08"),
    ("0.3.4", "2026-07-08"),
    ("0.3.2", "2026-07-08"),
    ("0.3.1", "2026-07-08"),
    ("0.2.1", "2026-07-08"),
]


class ReleaseHistoryTests(unittest.TestCase):
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
        cls.readme = cls.sandbox / "README.md"
        cls.changelog = cls.sandbox / "CHANGELOG.md"
        cls.manifest = cls.sandbox / "nori.json"
        cls.original_readme = cls.readme.read_text(encoding="utf-8")
        cls.original_changelog = cls.changelog.read_text(encoding="utf-8")
        cls.original_manifest = cls.manifest.read_text(encoding="utf-8")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tempdir.cleanup()

    def tearDown(self) -> None:
        self.readme.write_text(self.original_readme, encoding="utf-8")
        self.changelog.write_text(self.original_changelog, encoding="utf-8")
        self.manifest.write_text(self.original_manifest, encoding="utf-8")

    def run_validator(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "tests/validate-content.py"],
            cwd=self.sandbox,
            capture_output=True,
            text=True,
            check=False,
        )

    def replace_changelog(self, old: str, new: str) -> None:
        self.assertIn(old, self.original_changelog)
        self.changelog.write_text(
            self.original_changelog.replace(old, new, 1), encoding="utf-8"
        )

    def test_current_package_accepts_curated_release_history_contract(self) -> None:
        self.assertIn(UNRELEASED_HEADING, self.original_changelog)
        self.assertIn(TAGGED_HEADING, self.original_changelog)
        result = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_0120_misclassified_as_tagged_is_rejected(self) -> None:
        mutated = self.original_changelog.replace(CURRENT_UNRELEASED, "", 1)
        mutated = mutated.replace(
            TAGGED_HEADING,
            TAGGED_HEADING + "\n\n### 0.12.0 - 2026-08-08",
            1,
        )
        self.changelog.write_text(mutated, encoding="utf-8")
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unpublished-ledger drift", result.stdout)

    def test_fictional_033_tagged_heading_is_rejected(self) -> None:
        self.replace_changelog(
            "### 0.3.4 - 2026-07-08",
            "### 0.3.4 - 2026-07-08\n\n### 0.3.3 - 2026-07-08",
        )
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("tagged-ledger drift", result.stdout)

    def test_missing_021_tagged_heading_is_rejected(self) -> None:
        self.replace_changelog("### 0.2.1 - 2026-07-08", "")
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("tagged-ledger drift", result.stdout)

    def test_wrong_0100_tag_date_is_rejected(self) -> None:
        self.replace_changelog(
            "### 0.10.0 - 2026-07-27", "### 0.10.0 - 2026-07-24"
        )
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("tagged-ledger drift", result.stdout)

    def test_manifest_version_must_match_first_unpublished_state(self) -> None:
        self.assertIn('"version": "0.12.0"', self.original_manifest)
        self.manifest.write_text(
            self.original_manifest.replace(
                '"version": "0.12.0"', '"version": "0.12.1"', 1
            ),
            encoding="utf-8",
        )
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("current-version mismatch", result.stdout)

    def test_tagged_versions_must_be_strict_reverse_semver_order(self) -> None:
        swapped = self.original_changelog.replace(
            "### 0.10.0 - 2026-07-27", "### TEMP - 2026-07-27", 1
        ).replace(
            "### 0.7.0 - 2026-07-20", "### 0.10.0 - 2026-07-20", 1
        ).replace("### TEMP - 2026-07-27", "### 0.7.0 - 2026-07-27", 1)
        self.changelog.write_text(swapped, encoding="utf-8")
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("semantic-order drift", result.stdout)

    def test_level_two_version_heading_is_rejected(self) -> None:
        self.replace_changelog(
            "### 0.10.0 - 2026-07-27", "## 0.10.0 - 2026-07-27"
        )
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("version heading must be level three", result.stdout)

    def test_out_of_taxonomy_level_three_version_heading_is_rejected(self) -> None:
        self.changelog.write_text(
            "### 9.9.9 - 2026-08-12\n\n" + self.original_changelog,
            encoding="utf-8",
        )
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("version heading outside taxonomy", result.stdout)

    def test_wrong_level_version_heading_is_rejected(self) -> None:
        self.changelog.write_text(
            "#### 9.9.9 - 2026-08-12\n\n" + self.original_changelog,
            encoding="utf-8",
        )
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("version heading must be level three", result.stdout)

    def test_indented_out_of_taxonomy_version_heading_is_rejected(self) -> None:
        self.changelog.write_text(
            "  ### 9.9.9 - 2026-08-12\n\n" + self.original_changelog,
            encoding="utf-8",
        )
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("version heading outside taxonomy", result.stdout)

    def test_indented_wrong_level_version_heading_is_rejected(self) -> None:
        self.changelog.write_text(
            " #### 9.9.9 - 2026-08-12\n\n" + self.original_changelog,
            encoding="utf-8",
        )
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("version heading must be level three", result.stdout)

    def test_indented_version_heading_inside_taxonomy_is_rejected(self) -> None:
        self.changelog.write_text(
            self.original_changelog.replace(
                TAGGED_HEADING,
                TAGGED_HEADING + "\n\n  ### 9.9.9 - 2026-08-12",
                1,
            ),
            encoding="utf-8",
        )
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("version heading must be unindented", result.stdout)

    def test_fenced_code_version_example_is_ignored(self) -> None:
        self.changelog.write_text(
            "```markdown\n### 9.9.9 - 2026-08-12\n```\n\n"
            + self.original_changelog,
            encoding="utf-8",
        )
        result = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_invalid_backtick_fence_info_does_not_hide_version_heading(self) -> None:
        self.changelog.write_text(
            "```markdown`invalid\n ### 9.9.9 - 2026-08-12\n```\n\n"
            + self.original_changelog,
            encoding="utf-8",
        )
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("version heading outside taxonomy", result.stdout)

    def test_tilde_fenced_code_version_example_is_ignored(self) -> None:
        self.changelog.write_text(
            "~~~markdown\n### 9.9.9 - 2026-08-12\n~~~\n\n"
            + self.original_changelog,
            encoding="utf-8",
        )
        result = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_unclosed_fence_cannot_hide_canonical_taxonomy(self) -> None:
        self.changelog.write_text(
            "```markdown\n" + self.original_changelog,
            encoding="utf-8",
        )
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("changelog fence drift", result.stdout)

    def test_required_taxonomy_and_version_in_fence_are_rejected(self) -> None:
        self.replace_changelog(
            UNRELEASED_HEADING + "\n\n" + CURRENT_UNRELEASED,
            "```markdown\n"
            + UNRELEASED_HEADING
            + "\n\n"
            + CURRENT_UNRELEASED
            + "\n```",
        )
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unpublished-ledger drift", result.stdout)

    def test_noncanonical_atx_version_heading_is_rejected(self) -> None:
        self.replace_changelog(
            TAGGED_HEADING,
            TAGGED_HEADING + "\n\n### 0.3.3 (draft)",
        )
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("noncanonical version heading", result.stdout)

    def test_setext_version_heading_is_rejected(self) -> None:
        self.replace_changelog(
            TAGGED_HEADING,
            TAGGED_HEADING + "\n\n0.3.3 - 2026-07-08\n---",
        )
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("setext version heading", result.stdout)

    def test_multiline_setext_version_heading_is_rejected(self) -> None:
        self.replace_changelog(
            TAGGED_HEADING,
            TAGGED_HEADING + "\n\n0.3.3 - 2026-07-08\ncontinued\n---",
        )
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("setext version heading", result.stdout)

    def test_three_line_setext_version_heading_is_rejected(self) -> None:
        self.replace_changelog(
            TAGGED_HEADING,
            TAGGED_HEADING
            + "\n\n0.3.3 - 2026-07-08\ncontinued\nstill continued\n---",
        )
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("setext version heading", result.stdout)

    def test_indented_multiline_setext_version_heading_is_rejected(self) -> None:
        for indentation in range(1, 4):
            with self.subTest(indentation=indentation):
                prefix = " " * indentation
                self.replace_changelog(
                    TAGGED_HEADING,
                    TAGGED_HEADING
                    + f"\n\n{prefix}0.3.3 - 2026-07-08"
                    + f"\n{prefix}continued\n{prefix}---",
                )
                result = self.run_validator()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("setext version heading", result.stdout)

    def test_blank_line_ends_multiline_setext_candidate_paragraph(self) -> None:
        self.replace_changelog(
            TAGGED_HEADING,
            TAGGED_HEADING
            + "\n\n0.3.3 - 2026-07-08\n\nordinary heading\n---",
        )
        result = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_fenced_multiline_setext_version_examples_are_ignored(self) -> None:
        self.changelog.write_text(
            "```markdown\n0.3.3 - 2026-07-08\ncontinued\n---\n```\n\n"
            "~~~markdown\n0.3.3 - 2026-07-08\ncontinued\n---\n~~~\n\n"
            + self.original_changelog,
            encoding="utf-8",
        )
        result = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_legacy_version_heading_is_rejected(self) -> None:
        mutated = self.original_readme.replace(
            README_HEADING,
            "## What changed in v9.9.9\n\n- Regression.\n\n" + README_HEADING,
            1,
        )
        self.readme.write_text(mutated, encoding="utf-8")
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("README failure: duplicates release history", result.stdout)

    def test_missing_version_history_heading_is_rejected(self) -> None:
        self.readme.write_text(
            self.original_readme.replace(README_HEADING, "## Releases", 1),
            encoding="utf-8",
        )
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("README failure: missing version history heading", result.stdout)

    def test_missing_or_incorrect_changelog_link_is_rejected(self) -> None:
        self.readme.write_text(
            self.original_readme.replace(
                README_LINK,
                "See [release notes](docs/releases.md) for version history.",
                1,
            ),
            encoding="utf-8",
        )
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("README failure: missing canonical changelog link", result.stdout)


if __name__ == "__main__":
    unittest.main()
