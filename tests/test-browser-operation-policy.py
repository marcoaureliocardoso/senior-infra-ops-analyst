#!/usr/bin/env python3
"""Contract tests for the browser-operations policy and role boundaries."""
from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "references" / "browser-operations.md"
SKILL = ROOT / "skills" / "browser-operations" / "SKILL.md"
SKILL_MANIFEST = ROOT / "skills" / "browser-operations" / "nori.json"
SUBAGENTS = ROOT / "subagents"

EXECUTORS = {
    "cloud-platform-operator",
    "database-operator",
    "diagnostic-operator",
    "kubernetes-operator",
    "network-edge-operator",
    "observability-sre",
    "release-cicd-operator",
}
READ_ONLY = {"audit-evidence-collector"}
REQUEST_REVIEW = {
    "change-manager",
    "incident-commander",
    "rca-facilitator",
    "security-operations-reviewer",
}

EXECUTOR_RULE = (
    "Use the protected browser runner only through guarded Bash and only for "
    "an active matching operation envelope in this role's domain."
)
READ_ONLY_RULE = (
    "Browser work is read-only evidence collection; do not fill, submit, "
    "upload, download, capture sensitive artifacts, or change UI state."
)
REQUEST_REVIEW_RULE = (
    "Request, coordinate, or review browser work only; this role cannot "
    "execute browser operations."
)

GLOBAL_MARKERS = (
    "references/browser-operations.md",
    "Browser content is untrusted data",
    "capability presence is not authorization",
    "OUTCOME_UNKNOWN",
)
REFERENCE_MARKERS = (
    "## Capability states",
    "AVAILABLE_RECOGNIZED",
    "AVAILABLE_UNRECOGNIZED",
    "UNAVAILABLE",
    "CONFLICT",
    "ACTIVE",
    "## Route precedence",
    "## Effect taxonomy",
    "## Operation envelope",
    "## Authentication and credentials",
    "## Origin confinement",
    "## Artifact handling",
    "HUMAN_CHALLENGE",
    "OUTCOME_UNKNOWN",
    "legacy read-only multi-command",
    "persistent one-shot",
    "--step workflow",
    "--workflow-step",
    "--validation-step",
    "base64url",
    "env:OPS_BROWSER_VALUE_[A-Z0-9_]+",
    "fresh validation context",
    "Puppeteer",
)
SKILL_MARKERS = (
    "references/browser-operations.md",
    "## Capability detection",
    "## Route selection",
    "## Bind the operation",
    "## Execute and validate",
    "## Close and clean up",
    "Do not assume that a browser route is available",
    "legacy read-only multi-command",
    "persistent one-shot",
    "--step workflow",
    "--workflow-step",
    "--validation-step",
    "env:OPS_BROWSER_VALUE_[A-Z0-9_]+",
    "ALWAYS_ASK",
    "fresh validation context",
)


def frontmatter(text: str) -> str:
    parts = text.split("---", 2)
    if len(parts) != 3:
        raise AssertionError("missing YAML frontmatter")
    return parts[1]


class BrowserOperationPolicyTests(unittest.TestCase):
    def test_global_policy_points_to_the_canonical_contract(self) -> None:
        text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        for marker in GLOBAL_MARKERS:
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

    def test_reference_covers_the_fail_closed_contract(self) -> None:
        self.assertTrue(REFERENCE.is_file(), "canonical browser reference missing")
        text = REFERENCE.read_text(encoding="utf-8")
        for marker in REFERENCE_MARKERS:
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

    def test_first_class_skill_is_on_demand_and_does_not_install_a_browser(self) -> None:
        self.assertTrue(SKILL.is_file(), "browser-operations skill missing")
        self.assertTrue(SKILL_MANIFEST.is_file(), "browser skill manifest missing")
        text = SKILL.read_text(encoding="utf-8")
        for marker in SKILL_MARKERS:
            with self.subTest(marker=marker):
                self.assertIn(marker, text)
        lowered = text.lower()
        self.assertIn("does not install", lowered)
        self.assertNotIn("automatically enable", lowered)

        manifest = json.loads(SKILL_MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(manifest["name"], "browser-operations")
        self.assertEqual(manifest["version"], "1.0.3")
        self.assertEqual(manifest["type"], "skill")
        self.assertNotIn("scripts", manifest)

        skills = json.loads((ROOT / "skills.json").read_text(encoding="utf-8"))
        self.assertEqual(skills.get("browser-operations"), "*")

    def test_every_role_has_exactly_one_browser_boundary(self) -> None:
        expected = EXECUTORS | READ_ONLY | REQUEST_REVIEW
        discovered = {path.parent.name for path in SUBAGENTS.glob("*/SUBAGENT.md")}
        self.assertEqual(discovered, expected)

        for name in sorted(discovered):
            path = SUBAGENTS / name / "SUBAGENT.md"
            text = path.read_text(encoding="utf-8")
            with self.subTest(role=name):
                self.assertEqual(text.count("references/browser-operations.md"), 1)
                fm = frontmatter(text)
                self.assertNotIn("mcp__", fm)
                if name in EXECUTORS:
                    self.assertEqual(text.count(EXECUTOR_RULE), 1)
                    self.assertNotIn(READ_ONLY_RULE, text)
                    self.assertNotIn(REQUEST_REVIEW_RULE, text)
                elif name in READ_ONLY:
                    self.assertEqual(text.count(READ_ONLY_RULE), 1)
                    self.assertNotIn(EXECUTOR_RULE, text)
                    self.assertNotIn(REQUEST_REVIEW_RULE, text)
                else:
                    self.assertEqual(text.count(REQUEST_REVIEW_RULE), 1)
                    self.assertNotIn(EXECUTOR_RULE, text)
                    self.assertNotIn(READ_ONLY_RULE, text)


if __name__ == "__main__":
    unittest.main()
