#!/usr/bin/env python3
"""Canonical local projection only; no Nori registry or native client."""
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from browser_context_project import prepare_project, validate_projection

ROOT=Path(__file__).resolve().parents[1]
NODE=Path(os.environ.get("P004B_TERMINAL_NODE",shutil.which("node") or "/missing"))


@unittest.skipUnless(NODE.is_file(),"explicit existing Node runtime required")
class ProjectTests(unittest.TestCase):
    def test_project_fixture_uses_canonical_files_not_operator_settings(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=prepare_project(ROOT,root,node_path=NODE)
            self.assertEqual(set(p),{"project","config","home","claim","signal"})
            self.assertEqual((p["project"]/"CLAUDE.md").read_bytes(),(ROOT/"AGENTS.md").read_bytes())
            self.assertFalse((p["home"]/".claude.json").exists())
            self.assertFalse((p["project"]/".git").exists())
            self.assertTrue(all(path.is_relative_to(root) for path in p.values()))

    def test_flat_agents_and_placeholder_paths_pass_existing_validator(self):
        with tempfile.TemporaryDirectory() as d:
            p=prepare_project(ROOT,Path(d),node_path=NODE)
            self.assertEqual(len(list((p["project"]/".claude/agents").glob("*.md"))),12)
            self.assertEqual(validate_projection(p),[])
            for path in (p["project"]/".claude/agents").glob("*.md"):
                self.assertNotIn("{{skills_dir}}",path.read_text())

    def test_only_agent_measurement_hook_is_claimed(self):
        with tempfile.TemporaryDirectory() as d:
            p=prepare_project(ROOT,Path(d),node_path=NODE)
            settings=json.loads(p["config"].read_text())
            self.assertIn("hooks",settings)
            self.assertFalse(p["claim"].exists())
            self.assertNotIn("ACTIVE",json.dumps(settings))
            self.assertTrue((p["project"]/".claude/measurement-guard.py").is_file())

    def test_symlink_missing_agent_and_dependency_drift_fail(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=prepare_project(ROOT,root,node_path=NODE)
            target=p["project"]/".claude/agents/diagnostic-operator.md"
            target.unlink();self.assertTrue(validate_projection(p))
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=prepare_project(ROOT,root,node_path=NODE)
            target=p["project"]/".claude/skills/context-continuity/scripts/settings.mjs"
            target.write_text("drift");self.assertTrue(validate_projection(p))
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/"project").symlink_to(ROOT,target_is_directory=True)
            with self.assertRaises(ValueError):prepare_project(ROOT,root,node_path=NODE)


if __name__=="__main__":unittest.main()
