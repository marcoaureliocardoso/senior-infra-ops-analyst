#!/usr/bin/env python3
"""Mutation tests for the curated changelog release-history contract."""
from __future__ import annotations

import os
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
VERSION_LINE_ERROR = "noncanonical version-bearing line"
CURRENT_RELEASE = "### 0.12.0 - 2026-08-13"
CURRENT_RELEASE_BULLET_COUNT = 18
UNPUBLISHED_LEDGER = [
    ("0.14.0", "2026-08-25", None),
    ("0.13.0", "2026-08-21", None),
    ("0.11.1", "2026-08-08", None),
    ("0.11.0", "2026-07-26", None),
    ("0.9.1", "2026-07-23", None),
    ("0.9.0", "2026-07-23", None),
    ("0.8.0", "2026-07-23", None),
]
TAGGED_LEDGER = [
    ("0.12.0", "2026-08-13"),
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
        cls.nori_version = cls.sandbox / ".nori-version"
        cls.docs = cls.sandbox / "docs.md"
        cls.skill_manifest = cls.sandbox / "skills/command-driven-operations/nori.json"
        cls.skill = cls.sandbox / "skills/command-driven-operations/SKILL.md"
        cls.skills_catalog = cls.sandbox / "skills.json"
        cls.original_readme = cls.readme.read_text(encoding="utf-8")
        cls.original_changelog = cls.changelog.read_text(encoding="utf-8")
        cls.original_manifest = cls.manifest.read_text(encoding="utf-8")
        cls.original_nori_version = cls.nori_version.read_text(encoding="utf-8")
        cls.original_docs = cls.docs.read_text(encoding="utf-8")
        cls.original_skill_manifest = cls.skill_manifest.read_text(encoding="utf-8")
        cls.original_skill = cls.skill.read_text(encoding="utf-8")
        cls.original_skills_catalog = cls.skills_catalog.read_text(encoding="utf-8")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tempdir.cleanup()

    def tearDown(self) -> None:
        self.readme.write_text(self.original_readme, encoding="utf-8")
        self.changelog.write_text(self.original_changelog, encoding="utf-8")
        self.manifest.write_text(self.original_manifest, encoding="utf-8")
        self.nori_version.write_text(self.original_nori_version, encoding="utf-8")
        self.docs.write_text(self.original_docs, encoding="utf-8")
        self.skill_manifest.write_text(self.original_skill_manifest, encoding="utf-8")
        self.skill.write_text(self.original_skill, encoding="utf-8")
        self.skills_catalog.write_text(self.original_skills_catalog, encoding="utf-8")

    def run_validator(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "tests/validate-content.py"],
            cwd=self.sandbox,
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
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

    def test_current_unpublished_metadata_is_consistent(self) -> None:
        self.assertEqual(self.original_changelog.count(
            "### 0.14.0 (unreleased) - declared 2026-08-25"
        ), 1)
        self.assertIn('"version": "0.14.0"', self.original_manifest)
        self.assertIn('"version": "0.14.0"', self.original_nori_version)
        self.assertIn("Version: 0.14.0", self.original_readme)
        self.assertIn("Version: 0.14.0", self.original_docs)
        self.assertIn('"version": "1.1.0"', self.original_skill_manifest)
        self.assertIn("version: 0.6.0", self.original_skill)
        self.assertIn("last_updated: 2026-08-21", self.original_skill)
        self.assertIn('"command-driven-operations": "*"', self.original_skills_catalog)

    def test_0130_wrong_unpublished_date_is_rejected(self) -> None:
        self.replace_changelog(
            "### 0.13.0 (unreleased) - declared 2026-08-21",
            "### 0.13.0 (unreleased) - declared 2026-08-20",
        )
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unpublished-ledger drift", result.stdout)

    def test_current_version_metadata_drift_is_rejected(self) -> None:
        mutations = (
            (self.nori_version, self.original_nori_version.replace("0.14.0", "0.14.1"),
             "current-version metadata drift"),
            (self.readme, self.original_readme.replace("Version: 0.14.0", "Version: 0.14.1", 1),
             "current-version metadata drift"),
            (self.docs, self.original_docs.replace("Version: 0.14.0", "Version: 0.14.1", 1),
             "current-version metadata drift"),
            (self.skill_manifest, self.original_skill_manifest.replace("1.1.0", "1.1.1", 1),
             "component-version drift"),
            (self.skill, self.original_skill.replace("version: 0.6.0", "version: 0.6.1", 1),
             "skill-version drift"),
            (self.skill, self.original_skill.replace("2026-08-21", "2026-08-20", 1),
             "skill-date drift"),
            (self.skills_catalog, self.original_skills_catalog.replace(
                '"command-driven-operations": "*"', '"command-driven-operations": "1.1.0"', 1
            ), "skills catalogue"),
        )
        for path, content, expected in mutations:
            with self.subTest(path=path.name, expected=expected):
                path.write_text(content, encoding="utf-8")
                result = self.run_validator()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected, result.stdout)
                self.tearDown()

    def test_0120_misclassified_as_unpublished_is_rejected(self) -> None:
        mutated = self.original_changelog.replace(CURRENT_RELEASE, "", 1)
        mutated = mutated.replace(
            UNRELEASED_HEADING,
            UNRELEASED_HEADING
            + "\n\n### 0.12.0 (unreleased) - declared 2026-08-08; "
            "updated through 2026-08-13",
            1,
        )
        self.changelog.write_text(mutated, encoding="utf-8")
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("tagged-ledger drift", result.stdout)

    def test_0120_duplicated_across_taxonomies_is_rejected(self) -> None:
        self.changelog.write_text(
            self.original_changelog.replace(
                UNRELEASED_HEADING,
                UNRELEASED_HEADING
                + "\n\n### 0.12.0 (unreleased) - declared 2026-08-08; "
                "updated through 2026-08-13",
                1,
            ),
            encoding="utf-8",
        )
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("noncanonical version-bearing line", result.stdout)

    def test_0120_wrong_release_date_is_rejected(self) -> None:
        self.assertIn(CURRENT_RELEASE, self.original_changelog)
        self.replace_changelog(CURRENT_RELEASE, "### 0.12.0 - 2026-08-12")
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("tagged-ledger drift", result.stdout)

    def test_0120_release_bullet_loss_is_rejected(self) -> None:
        self.assertIn(CURRENT_RELEASE, self.original_changelog)
        start = self.original_changelog.index(CURRENT_RELEASE)
        end = self.original_changelog.index("\n### 0.10.0", start)
        release_block = self.original_changelog[start:end]
        self.assertEqual(
            release_block.count("\n- "), CURRENT_RELEASE_BULLET_COUNT
        )
        self.changelog.write_text(
            self.original_changelog.replace(
                "\n- Left P0-04B browser automation out of scope.", "", 1
            ),
            encoding="utf-8",
        )
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("current-release bullet-count drift", result.stdout)

    def test_fictional_033_tagged_heading_is_rejected(self) -> None:
        self.replace_changelog(
            "### 0.3.4 - 2026-07-08",
            "### 0.3.4 - 2026-07-08\n\n### 0.3.3 - 2026-07-08",
        )
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(VERSION_LINE_ERROR, result.stdout)

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

    def test_normalized_version_heading_spelling_is_rejected(self) -> None:
        canonical = "### 0.10.0 - 2026-07-27"
        mutations = (
            "###  0.10.0 - 2026-07-27",
            "###\t0.10.0 - 2026-07-27",
            "### 0.10.0 - 2026-07-27 ",
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                self.replace_changelog(canonical, mutation)
                result = self.run_validator()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(VERSION_LINE_ERROR, result.stdout)

    def test_normalized_taxonomy_spelling_is_rejected(self) -> None:
        self.replace_changelog(TAGGED_HEADING, "##  Tagged versions")
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("tagged-ledger drift", result.stdout)

    def test_required_version_moved_under_unexpected_h2_is_rejected(self) -> None:
        self.replace_changelog(
            "### 0.3.4 - 2026-07-08",
            "## Appendix\n\n### 0.3.4 - 2026-07-08",
        )
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unexpected changelog taxonomy heading", result.stdout)

    def test_manifest_version_must_match_highest_recorded_state(self) -> None:
        self.assertIn('"version": "0.14.0"', self.original_manifest)
        self.manifest.write_text(
            self.original_manifest.replace(
                '"version": "0.14.0"', '"version": "0.14.1"', 1
            ),
            encoding="utf-8",
        )
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("current-version mismatch", result.stdout)
        self.assertIn("highest recorded package state", result.stdout)

    def test_tagged_versions_must_be_strict_reverse_semver_order(self) -> None:
        swapped = self.original_changelog.replace(
            "### 0.10.0 - 2026-07-27", "### TEMP", 1
        ).replace(
            "### 0.7.0 - 2026-07-20", "### 0.10.0 - 2026-07-27", 1
        ).replace("### TEMP", "### 0.7.0 - 2026-07-20", 1)
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
        self.assertIn(VERSION_LINE_ERROR, result.stdout)

    def test_indented_wrong_level_version_heading_is_rejected(self) -> None:
        self.changelog.write_text(
            " #### 9.9.9 - 2026-08-12\n\n" + self.original_changelog,
            encoding="utf-8",
        )
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(VERSION_LINE_ERROR, result.stdout)

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
        self.assertIn(VERSION_LINE_ERROR, result.stdout)

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
        self.assertIn(VERSION_LINE_ERROR, result.stdout)

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
            TAGGED_HEADING + "\n\n" + CURRENT_RELEASE,
            "```markdown\n"
            + TAGGED_HEADING
            + "\n\n"
            + CURRENT_RELEASE
            + "\n```",
        )
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("tagged-ledger drift", result.stdout)

    def test_noncanonical_atx_version_heading_is_rejected(self) -> None:
        self.replace_changelog(
            TAGGED_HEADING,
            TAGGED_HEADING + "\n\n### 0.3.3 (draft)",
        )
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("noncanonical version heading", result.stdout)

    def test_noncanonical_version_bearing_witnesses_are_rejected(self) -> None:
        witnesses = (
            "> ### 0.3.3 - 2026-07-08",
            "- ### 0.3.3 - 2026-07-08",
            "> - ### 0.3.3 - 2026-07-08",
            "### 0.3.3-rc.1 - 2026-07-08",
            "### 0.3.3+build.7 - 2026-07-08",
        )
        for witness in witnesses:
            with self.subTest(witness=witness):
                self.replace_changelog(
                    TAGGED_HEADING,
                    TAGGED_HEADING + "\n\n" + witness,
                )
                result = self.run_validator()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(VERSION_LINE_ERROR, result.stdout)

    def test_ascii_ordered_list_version_is_rejected(self) -> None:
        self.replace_changelog(
            TAGGED_HEADING,
            TAGGED_HEADING + "\n\n1. 0.3.3 - 2026-07-08",
        )
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(VERSION_LINE_ERROR, result.stdout)

    def test_unicode_decimal_digits_do_not_form_version_syntax(self) -> None:
        witnesses = (
            "### 1.2.3\u0664 note",
            "\u0661. 0.3.3 - 2026-07-08",
        )
        for witness in witnesses:
            with self.subTest(witness=witness):
                self.replace_changelog(
                    TAGGED_HEADING,
                    TAGGED_HEADING + "\n\n" + witness,
                )
                result = self.run_validator()
                self.assertEqual(
                    result.returncode,
                    0,
                    result.stdout + result.stderr,
                )

    def test_direct_version_leading_line_is_rejected(self) -> None:
        self.replace_changelog(
            TAGGED_HEADING,
            TAGGED_HEADING + "\n\n0.3.3 - 2026-07-08",
        )
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(VERSION_LINE_ERROR, result.stdout)

    def test_multiline_version_leading_paragraph_is_rejected(self) -> None:
        self.replace_changelog(
            TAGGED_HEADING,
            TAGGED_HEADING + "\n\n0.3.3 - 2026-07-08\ncontinued\n---",
        )
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(VERSION_LINE_ERROR, result.stdout)

    def test_three_line_version_leading_paragraph_is_rejected(self) -> None:
        self.replace_changelog(
            TAGGED_HEADING,
            TAGGED_HEADING
            + "\n\n0.3.3 - 2026-07-08\ncontinued\nstill continued\n---",
        )
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(VERSION_LINE_ERROR, result.stdout)

    def test_indented_version_leading_line_is_rejected(self) -> None:
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
                self.assertIn(VERSION_LINE_ERROR, result.stdout)

    def test_blank_line_does_not_end_lexical_version_detection(self) -> None:
        self.replace_changelog(
            TAGGED_HEADING,
            TAGGED_HEADING
            + "\n\n0.3.3 - 2026-07-08\n\nordinary heading\n---",
        )
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(VERSION_LINE_ERROR, result.stdout)

    def test_standalone_underline_does_not_hide_later_version_line(self) -> None:
        self.replace_changelog(
            TAGGED_HEADING,
            TAGGED_HEADING
            + "\n\n---\n0.3.3 - 2026-07-08\ncontinued\n---",
        )
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(VERSION_LINE_ERROR, result.stdout)

    def test_version_mentions_that_do_not_start_meaningful_content_are_accepted(self) -> None:
        witnesses = (
            "Version 0.3.4 introduced new validation.",
            "- Version 0.3.4 remains documented here.",
        )
        for witness in witnesses:
            with self.subTest(witness=witness):
                self.replace_changelog(
                    TAGGED_HEADING,
                    TAGGED_HEADING + "\n\n" + witness,
                )
                result = self.run_validator()
                self.assertEqual(
                    result.returncode,
                    0,
                    result.stdout + result.stderr,
                )

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
