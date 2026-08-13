#!/usr/bin/env python3
"""Mutation tests for the canonical Nori package contract."""
from __future__ import annotations

import importlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CANONICAL_FIELDS = {
    "name",
    "version",
    "description",
    "author",
    "license",
    "repository",
    "keywords",
    "dependencies",
}
SUBAGENT_FIELDS = {"name", "version", "type", "description"}


class NoriPackageContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.sandbox = Path(self.tempdir.name) / "package"
        shutil.copytree(
            ROOT,
            self.sandbox,
            ignore=shutil.ignore_patterns(
                ".git", ".worktrees", ".tmp", "__pycache__"
            ),
        )
        self.manifest_path = self.sandbox / "nori.json"
        self.canonicalize_subagents()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def read_manifest(self) -> dict[str, object]:
        return json.loads(self.manifest_path.read_text(encoding="utf-8"))

    def write_manifest(self, manifest: dict[str, object]) -> None:
        self.manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def canonicalize_manifest(self) -> dict[str, object]:
        manifest = self.read_manifest()
        manifest["keywords"] = manifest.pop("tags", manifest.get("keywords", []))
        manifest["dependencies"] = {
            "skills": {"read-the-damn-docs": "latest"}
        }
        for field in (
            "type",
            "skills",
            "references",
            "subagents",
            "homepage",
            "bugs",
        ):
            manifest.pop(field, None)
        self.write_manifest(manifest)
        return manifest

    def run_validator(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "tests/validate-schema.py"],
            cwd=self.sandbox,
            capture_output=True,
            text=True,
            check=False,
        )

    def package_module(self):
        return importlib.import_module("scripts.nori_package")

    def canonicalize_subagents(self) -> None:
        subagents_dir = self.sandbox / "subagents"
        for source in sorted(subagents_dir.glob("*.md")):
            text = source.read_text(encoding="utf-8")
            name_match = re.search(r"^name:\s*(\S+)\s*$", text, re.MULTILINE)
            description_match = re.search(
                r"^description:\s*(.+?)\s*$", text, re.MULTILINE
            )
            self.assertIsNotNone(name_match)
            self.assertIsNotNone(description_match)
            assert name_match is not None
            assert description_match is not None
            subagent_id = source.stem
            target = subagents_dir / subagent_id
            target.mkdir()
            (target / "SUBAGENT.md").write_text(text, encoding="utf-8")
            (target / "nori.json").write_text(
                json.dumps(
                    {
                        "name": subagent_id,
                        "version": "1.0.0",
                        "type": "subagent",
                        "description": description_match.group(1),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            source.unlink()

    def subagent_manifest(self, subagent_id: str) -> tuple[Path, dict[str, object]]:
        path = self.sandbox / "subagents" / subagent_id / "nori.json"
        return path, json.loads(path.read_text(encoding="utf-8"))

    def write_subagent_manifest(
        self, path: Path, manifest: dict[str, object]
    ) -> None:
        path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def repository_errors(self) -> list[str]:
        return self.package_module().validate_repository_inventory(self.sandbox)

    def test_repository_manifest_uses_only_canonical_fields(self) -> None:
        manifest = json.loads((ROOT / "nori.json").read_text(encoding="utf-8"))
        self.assertEqual(set(manifest), CANONICAL_FIELDS)

    def test_canonical_manifest_is_accepted(self) -> None:
        self.canonicalize_manifest()
        result = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_legacy_tags_are_rejected(self) -> None:
        manifest = self.canonicalize_manifest()
        manifest["tags"] = manifest.pop("keywords")
        self.write_manifest(manifest)
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("legacy field is not allowed: tags", result.stdout)

    def test_array_skill_dependencies_are_rejected(self) -> None:
        manifest = self.canonicalize_manifest()
        manifest["dependencies"] = {"skills": ["read-the-damn-docs"]}
        self.write_manifest(manifest)
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("dependencies.skills must be an object", result.stdout)

    def test_wrong_dependency_version_is_rejected(self) -> None:
        manifest = self.canonicalize_manifest()
        manifest["dependencies"] = {
            "skills": {"read-the-damn-docs": "*"}
        }
        self.write_manifest(manifest)
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "read-the-damn-docs dependency must be 'latest'", result.stdout
        )

    def test_post_upload_subagent_dependencies_are_accepted(self) -> None:
        manifest = self.canonicalize_manifest()
        dependencies = manifest["dependencies"]
        assert isinstance(dependencies, dict)
        dependencies["subagents"] = {
            path.name: "1.0.0"
            for path in sorted((self.sandbox / "subagents").iterdir())
            if path.is_dir()
        }
        self.write_manifest(manifest)
        result = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_post_upload_subagent_dependencies_must_match_local_components(self) -> None:
        manifest = self.canonicalize_manifest()
        dependencies = manifest["dependencies"]
        assert isinstance(dependencies, dict)
        dependencies["subagents"] = {
            "diagnostic-operator": "9.9.9",
            "unknown-operator": "1.0.0",
        }
        self.write_manifest(manifest)
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "dependencies.subagents must match first-class local component versions",
            result.stdout,
        )

    def test_reintroduced_inventory_field_is_rejected(self) -> None:
        manifest = self.canonicalize_manifest()
        manifest["skills"] = ["context-continuity"]
        self.write_manifest(manifest)
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unexpected field: skills", result.stdout)

    def test_duplicate_keyword_is_rejected(self) -> None:
        manifest = self.canonicalize_manifest()
        keywords = manifest["keywords"]
        assert isinstance(keywords, list)
        keywords.append(keywords[0])
        self.write_manifest(manifest)
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("keywords contains duplicates", result.stdout)

    def test_missing_agents_md_is_rejected(self) -> None:
        self.canonicalize_manifest()
        (self.sandbox / "AGENTS.md").unlink()
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("AGENTS.md is required", result.stdout)

    def test_empty_agents_md_is_rejected(self) -> None:
        self.canonicalize_manifest()
        (self.sandbox / "AGENTS.md").write_text("", encoding="utf-8")
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("AGENTS.md must not be empty", result.stdout)

    def test_missing_skill_catalog_entry_is_rejected(self) -> None:
        self.canonicalize_manifest()
        skills_path = self.sandbox / "skills.json"
        skills = json.loads(skills_path.read_text(encoding="utf-8"))
        skills.pop("context-continuity")
        skills_path.write_text(
            json.dumps(skills, indent=2) + "\n", encoding="utf-8"
        )
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "packaged skill 'context-continuity' not found in skills.json",
            result.stdout,
        )

    def test_missing_per_skill_metadata_is_rejected(self) -> None:
        self.canonicalize_manifest()
        (self.sandbox / "skills" / "context-continuity" / "nori.json").unlink()
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("skills/context-continuity/nori.json not found", result.stdout)

    def test_filesystem_discovery_exposes_package_assets(self) -> None:
        self.canonicalize_subagents()
        module = self.package_module()
        self.assertIn("context-continuity", module.discover_skill_ids(self.sandbox))
        self.assertIn(
            "references/risk-levels.md",
            module.discover_reference_paths(self.sandbox),
        )
        self.assertIn(
            "diagnostic-operator", module.discover_subagent_ids(self.sandbox)
        )
        self.assertEqual(
            module.subagent_definition_path(
                self.sandbox, "diagnostic-operator"
            ).relative_to(self.sandbox).as_posix(),
            "subagents/diagnostic-operator/SUBAGENT.md",
        )

    def test_repository_subagents_use_exact_first_class_manifests(self) -> None:
        self.canonicalize_subagents()
        self.assertEqual(self.repository_errors(), [])
        manifests = sorted((self.sandbox / "subagents").glob("*/nori.json"))
        self.assertEqual(len(manifests), 12)
        for path in manifests:
            with self.subTest(subagent=path.parent.name):
                manifest = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(set(manifest), SUBAGENT_FIELDS)
                self.assertEqual(manifest["name"], path.parent.name)
                self.assertEqual(manifest["version"], "1.0.0")
                self.assertEqual(manifest["type"], "subagent")

    def test_flat_subagent_definition_is_rejected(self) -> None:
        self.canonicalize_subagents()
        source = (
            self.sandbox / "subagents" / "diagnostic-operator" / "SUBAGENT.md"
        )
        legacy = self.sandbox / "subagents" / "diagnostic-operator.md"
        legacy.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        self.assertIn(
            "legacy flat subagent definition is not allowed: "
            "subagents/diagnostic-operator.md",
            self.repository_errors(),
        )

    def test_subagent_missing_definition_is_rejected(self) -> None:
        self.canonicalize_subagents()
        (
            self.sandbox / "subagents" / "diagnostic-operator" / "SUBAGENT.md"
        ).unlink()
        self.assertIn(
            "subagents/diagnostic-operator/SUBAGENT.md not found",
            self.repository_errors(),
        )

    def test_subagent_missing_manifest_is_rejected(self) -> None:
        self.canonicalize_subagents()
        path, _ = self.subagent_manifest("diagnostic-operator")
        path.unlink()
        self.assertIn(
            "subagents/diagnostic-operator/nori.json not found",
            self.repository_errors(),
        )

    def test_subagent_manifest_identity_type_and_version_are_enforced(self) -> None:
        self.canonicalize_subagents()
        path, original = self.subagent_manifest("diagnostic-operator")
        mutations = (
            ("name", "other-operator", "name must match directory id"),
            ("type", "inlined-subagent", "type must be 'subagent'"),
            ("version", "latest", "is not valid semver (X.Y.Z)"),
        )
        for field, value, message in mutations:
            with self.subTest(field=field):
                manifest = dict(original)
                manifest[field] = value
                self.write_subagent_manifest(path, manifest)
                self.assertTrue(
                    any(message in error for error in self.repository_errors())
                )
        self.write_subagent_manifest(path, original)

    def test_subagent_manifest_description_must_match_frontmatter(self) -> None:
        self.canonicalize_subagents()
        path, manifest = self.subagent_manifest("diagnostic-operator")
        manifest["description"] = "Different registry description."
        self.write_subagent_manifest(path, manifest)
        self.assertIn(
            "subagents/diagnostic-operator/nori.json description must match "
            "SUBAGENT.md frontmatter",
            self.repository_errors(),
        )

    def test_subagent_manifest_rejects_unexpected_fields(self) -> None:
        self.canonicalize_subagents()
        path, manifest = self.subagent_manifest("diagnostic-operator")
        manifest["scripts"] = []
        self.write_subagent_manifest(path, manifest)
        self.assertIn(
            "subagents/diagnostic-operator/nori.json unexpected field: scripts",
            self.repository_errors(),
        )

    def test_invalid_subagent_directory_id_is_rejected(self) -> None:
        self.canonicalize_subagents()
        source = self.sandbox / "subagents" / "diagnostic-operator"
        target = self.sandbox / "subagents" / "Invalid_Operator"
        source.rename(target)
        self.assertIn(
            "packaged subagent id is invalid: 'Invalid_Operator'",
            self.repository_errors(),
        )

    def test_linked_subagent_directory_is_rejected_by_inventory(self) -> None:
        source = self.sandbox / "subagents" / "diagnostic-operator"
        target = self.sandbox.parent / "operator-subagent"
        source.rename(target)
        try:
            source.symlink_to(target, target_is_directory=True)
        except OSError:
            target.rename(source)
            self.skipTest("directory symlink creation is unavailable")
        self.assertIn(
            "symlink or reparse point is not allowed: "
            "subagents/diagnostic-operator",
            self.repository_errors(),
        )


if __name__ == "__main__":
    unittest.main()
