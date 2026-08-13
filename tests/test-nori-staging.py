#!/usr/bin/env python3
"""Behavior tests for safe reproducible Nori staging."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts" / "build_nori_staging.py"
ROOT_FILES = {"AGENTS.md", "LICENSE", "nori.json", "skills.json"}
ROOT_DIRS = {"references", "skills", "slashcommands", "subagents"}
sys.path.insert(0, str(ROOT))

from scripts.nori_package import build_staging, validate_staging  # noqa: E402


class NoriStagingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.temp_root = Path(self.tempdir.name)
        self.source = self.temp_root / "source"
        self.destination = self.temp_root / "staging"
        shutil.copytree(
            ROOT,
            self.source,
            ignore=shutil.ignore_patterns(
                ".git", ".worktrees", ".tmp", "__pycache__"
            ),
        )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def run_builder(
        self, *extra: str, destination: Path | None = None
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(BUILDER),
                "--source",
                str(self.source),
                "--destination",
                str(destination or self.destination),
                *extra,
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    def build(self, *extra: str) -> subprocess.CompletedProcess[str]:
        result = self.run_builder(*extra)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def run_source_check(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(BUILDER),
                "--source",
                str(self.source),
                "--check-source",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    @staticmethod
    def file_hash(path: Path) -> str:
        digest = hashlib.sha256()
        digest.update(path.read_bytes())
        return digest.hexdigest()

    def test_build_contains_only_allowlisted_roots_and_matching_files(self) -> None:
        self.build("--json")
        self.assertEqual(
            {entry.name for entry in self.destination.iterdir()},
            ROOT_FILES | ROOT_DIRS,
        )
        for staged in sorted(path for path in self.destination.rglob("*") if path.is_file()):
            relative = staged.relative_to(self.destination)
            source = self.source / relative
            self.assertTrue(source.is_file(), relative.as_posix())
            self.assertEqual(self.file_hash(staged), self.file_hash(source))

    def test_build_contains_all_first_class_subagent_packages(self) -> None:
        self.build()
        subagents = self.destination / "subagents"
        directories = sorted(path for path in subagents.iterdir() if path.is_dir())
        self.assertEqual(len(directories), 12)
        self.assertEqual(list(subagents.glob("*.md")), [])
        for directory in directories:
            with self.subTest(subagent=directory.name):
                self.assertTrue((directory / "SUBAGENT.md").is_file())
                manifest = json.loads(
                    (directory / "nori.json").read_text(encoding="utf-8")
                )
                self.assertEqual(set(manifest), {"name", "version", "type", "description"})
                self.assertEqual(manifest["name"], directory.name)
                self.assertEqual(manifest["version"], "1.0.0")
                self.assertEqual(manifest["type"], "subagent")

    def test_json_inventory_is_sorted_and_does_not_enter_staging(self) -> None:
        result = self.build("--json")
        inventory = json.loads(result.stdout)
        paths = [entry["path"] for entry in inventory]
        self.assertEqual(paths, sorted(paths))
        self.assertEqual(paths[0], "AGENTS.md")
        self.assertFalse((self.destination / "inventory.json").exists())
        for entry in inventory:
            self.assertEqual(set(entry), {"path", "size", "sha256"})

    def test_check_detects_staged_byte_drift(self) -> None:
        self.build()
        path = self.destination / "AGENTS.md"
        path.write_text("altered\n", encoding="utf-8")
        result = self.run_builder("--check")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("content differs from source: AGENTS.md", result.stderr)

    def test_missing_agents_md_is_rejected_before_copy(self) -> None:
        (self.source / "AGENTS.md").unlink()
        result = self.run_builder()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("AGENTS.md is required", result.stderr)
        self.assertFalse(self.destination.exists())

    def test_root_claude_md_is_rejected_before_copy(self) -> None:
        (self.source / "CLAUDE.md").write_text("legacy\n", encoding="utf-8")
        result = self.run_builder()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("root CLAUDE.md is not allowed", result.stderr)

    def test_sensitive_file_inside_allowed_tree_is_rejected(self) -> None:
        (self.source / "references" / ".env").write_text(
            "SECRET=do-not-copy\n", encoding="utf-8"
        )
        result = self.run_builder()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("sensitive path is not allowed", result.stderr)
        self.assertNotIn("do-not-copy", result.stdout + result.stderr)

    def test_existing_destination_requires_replace(self) -> None:
        self.destination.mkdir()
        result = self.run_builder()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("destination already exists; use --replace", result.stderr)

    def test_replace_refuses_unexpected_existing_content(self) -> None:
        self.destination.mkdir()
        sentinel = self.destination / "operator-file.txt"
        sentinel.write_text("preserve me\n", encoding="utf-8")
        result = self.run_builder("--replace")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unexpected destination entry", result.stderr)
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "preserve me\n")

    def test_replace_refuses_allowed_names_with_unrecognized_bytes(self) -> None:
        self.destination.mkdir()
        sentinel = self.destination / "AGENTS.md"
        sentinel.write_text("operator instructions\n", encoding="utf-8")
        result = self.run_builder("--replace")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("content differs from source: AGENTS.md", result.stderr)
        self.assertEqual(
            sentinel.read_text(encoding="utf-8"), "operator instructions\n"
        )

    def test_replace_accepts_only_a_previous_managed_staging_tree(self) -> None:
        self.build()
        old_hash = self.file_hash(self.destination / "AGENTS.md")
        result = self.run_builder("--replace")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.file_hash(self.destination / "AGENTS.md"), old_hash)

    def test_source_or_ancestor_destination_is_rejected(self) -> None:
        for destination in (self.source, self.source.parent):
            with self.subTest(destination=destination):
                result = self.run_builder("--replace", destination=destination)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("unsafe staging destination", result.stderr)
                self.assertTrue((self.source / "AGENTS.md").is_file())

    def test_destination_symlink_is_rejected_without_touching_target(self) -> None:
        operator_target = self.temp_root / "operator-target"
        operator_target.mkdir()
        sentinel = operator_target / "AGENTS.md"
        sentinel.write_text("operator instructions\n", encoding="utf-8")
        try:
            self.destination.symlink_to(operator_target, target_is_directory=True)
        except OSError:
            self.skipTest("directory symlink creation is unavailable")
        result = self.run_builder("--replace")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("destination is a symlink or reparse point", result.stderr)
        self.assertTrue(self.destination.is_symlink())
        self.assertEqual(
            sentinel.read_text(encoding="utf-8"), "operator instructions\n"
        )

    def test_source_root_symlink_is_rejected(self) -> None:
        linked_source = self.temp_root / "linked-source"
        try:
            linked_source.symlink_to(self.source, target_is_directory=True)
        except OSError:
            self.skipTest("directory symlink creation is unavailable")
        result = subprocess.run(
            [
                sys.executable,
                str(BUILDER),
                "--source",
                str(linked_source),
                "--destination",
                str(self.destination),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("source root is a symlink or reparse point", result.stderr)
        self.assertFalse(self.destination.exists())

    def test_replace_restores_destination_when_content_arrives_during_copy(self) -> None:
        self.build()
        sentinel = self.destination / "operator-late-file.txt"
        original_copy = shutil.copyfile
        injected = False

        def copy_and_inject(*args: object, **kwargs: object) -> object:
            nonlocal injected
            result = original_copy(*args, **kwargs)
            if not injected:
                sentinel.write_text("preserve me\n", encoding="utf-8")
                injected = True
            return result

        with mock.patch(
            "scripts.nori_package.shutil.copyfile", side_effect=copy_and_inject
        ):
            with self.assertRaisesRegex(ValueError, "unexpected destination entry"):
                build_staging(self.source, self.destination, replace=True)
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "preserve me\n")

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFO creation is unavailable")
    def test_check_rejects_special_destination_file(self) -> None:
        self.build()
        expected_regular_files = sum(
            1 for path in self.destination.rglob("*") if path.is_file()
        ) - 1
        agents = self.destination / "AGENTS.md"
        agents.unlink()
        try:
            os.mkfifo(agents)
        except OSError:
            self.skipTest("FIFO creation is unavailable")
        errors, inventory = validate_staging(self.source, self.destination)
        self.assertIn("non-regular destination entry: AGENTS.md", errors)
        self.assertEqual(len(inventory), expected_regular_files)

    def test_symlink_inside_allowed_tree_is_rejected(self) -> None:
        outside = self.temp_root / "outside.txt"
        outside.write_text("not packaged\n", encoding="utf-8")
        link = self.source / "references" / "escape.md"
        try:
            link.symlink_to(outside)
        except OSError:
            self.skipTest("symlink creation is unavailable")
        result = self.run_builder()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("symlink or reparse point", result.stderr)
        self.assertNotIn("not packaged", result.stdout + result.stderr)

        source_result = self.run_source_check()
        self.assertNotEqual(source_result.returncode, 0)
        self.assertIn("symlink or reparse point", source_result.stderr)

if __name__ == "__main__":
    unittest.main()
