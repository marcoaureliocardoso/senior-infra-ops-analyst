#!/usr/bin/env python3
"""Behavior contract for the canonical native execution boundary."""
from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "references" / "native-execution-boundary.md"
AGENTS = ROOT / "AGENTS.md"
SKILL = ROOT / "skills" / "command-driven-operations" / "SKILL.md"

PHASES = ("DIAGNOSE", "PROPOSE", "EXECUTE", "VALIDATE", "ROLLBACK")
STATES = (
    "ACTIVE",
    "CONFIGURED_UNPROVEN",
    "ABSENT",
    "CONFLICT",
    "UNSUPPORTED",
)
ROUTES = ("PROTECTED_BASH", "PROTECTED_EXECUTOR", "TYPED_TOOL", "NO_EXECUTION")
SECTIONS = (
    "Lifecycle phases",
    "Coverage states",
    "Routing matrix",
    "Protected Bash invariants",
    "Typed-tool invariants",
    "Delegation and refusal",
    "Browser and MCP boundaries",
    "Related references",
)
EXPECTED_ROWS = {
    "NARROW_DIAGNOSIS": "PROTECTED_BASH",
    "UNEXECUTED_PROPOSAL": "NO_EXECUTION",
    "CATALOGUED_NON_DESTRUCTIVE": "PROTECTED_BASH",
    "DESTRUCTIVE_SHELL": "PROTECTED_BASH",
    "AMBIGUOUS_SHELL": "NO_EXECUTION",
    "TRANSACTIONAL_MULTI_TARGET": "TYPED_TOOL",
    "EXTERNAL_WORKFLOW_MUTATION": "TYPED_TOOL",
    "EXECUTOR_FALLBACK": "PROTECTED_EXECUTOR",
    "NO_PROTECTED_ROUTE": "NO_EXECUTION",
}
REQUIRED_RULES = {
    "bounded read route is missing": "complete bounded read",
    "proposal/execution separation is missing": "must never be represented as executed evidence",
    "ACTIVE main-session gate is missing": "requires `ACTIVE` coverage",
    "settings-only state is missing": "settings alone establish `CONFIGURED_UNPROVEN`",
    "session probe contract is missing": "`printf P005_GUARD_PROBE`",
    "probe authorization boundary is missing": "does not authorize a later command",
    "missing-hook disposition is missing": "missing hook result",
    "unproven fallback is missing": "delegate to `PROTECTED_EXECUTOR` or use `NO_EXECUTION`",
    "destructive exact-decision rule is missing": "destructive shell operation always returns `ask`",
    "deny reformulation rule is missing": "must never be upgraded by prose",
    "transactional typed-tool rule is missing": "transaction boundary requires `TYPED_TOOL`",
    "multi-target typed-tool rule is missing": "coordinated multi-target state requires `TYPED_TOOL`",
    "idempotency typed-tool rule is missing": "durable idempotency requires `TYPED_TOOL`",
    "missing-capability rule is missing": "missing typed capability never weakens",
    "untrusted annotation rule is missing": "MCP annotations are untrusted hints",
    "scope boundary is missing": "P0-04B and P3-16 remain outside P0-05 implementation scope",
}


def section(text: str, heading: str) -> str:
    match = re.search(
        rf"^## {re.escape(heading)}\s*$\n(.*?)(?=^## |\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    return match.group(1) if match else ""


def matrix_rows(text: str) -> dict[str, tuple[str, str, str]]:
    block = section(text, "Routing matrix")
    lines = [line for line in block.splitlines() if line.startswith("|")]
    if len(lines) < 3:
        return {}
    rows: dict[str, tuple[str, str, str]] = {}
    for line in lines[2:]:
        cells = [cell.strip().strip("`") for cell in line.strip("|").split("|")]
        if len(cells) != 4:
            continue
        operation, phase, route, condition = cells
        rows[operation] = (phase, route, condition)
    return rows


def boundary_errors(text: str) -> list[str]:
    errors: list[str] = []
    for heading in SECTIONS:
        if len(re.findall(rf"^## {re.escape(heading)}\s*$", text, re.MULTILINE)) != 1:
            errors.append(f"boundary section must occur exactly once: {heading}")

    lifecycle = section(text, "Lifecycle phases")
    coverage = section(text, "Coverage states")
    for phase in PHASES:
        if lifecycle.count(f"`{phase}`") != 1:
            errors.append(f"lifecycle phase must occur exactly once: {phase}")
    for state in STATES:
        if coverage.count(f"`{state}`") < 1:
            errors.append(f"coverage state is missing: {state}")

    rows = matrix_rows(text)
    if set(rows) != set(EXPECTED_ROWS):
        errors.append("routing matrix operations differ from the canonical set")
    for operation, expected_route in EXPECTED_ROWS.items():
        row = rows.get(operation)
        if row is None:
            continue
        phase, route, condition = row
        if phase not in PHASES:
            errors.append(f"routing matrix phase is invalid: {operation}")
        if route != expected_route or route not in ROUTES:
            errors.append(f"routing matrix route is invalid: {operation}")
        if not condition:
            errors.append(f"routing matrix minimum condition is empty: {operation}")

    for reason, witness in REQUIRED_RULES.items():
        if witness not in text:
            errors.append(reason)
    return errors


class NativeExecutionBoundaryTests(unittest.TestCase):
    def test_canonical_reference_exists_and_is_valid(self) -> None:
        self.assertTrue(REFERENCE.is_file(), "native execution boundary is missing")
        text = REFERENCE.read_text(encoding="utf-8")
        self.assertEqual(boundary_errors(text), [])

    def test_each_normative_rule_has_a_stable_negative_witness(self) -> None:
        if not REFERENCE.is_file():
            self.skipTest("canonical reference is not implemented yet")
        text = REFERENCE.read_text(encoding="utf-8")
        for reason, witness in REQUIRED_RULES.items():
            with self.subTest(reason=reason):
                changed = text.replace(witness, "REMOVED_REQUIREMENT")
                self.assertIn(reason, boundary_errors(changed))

    def test_matrix_rejects_route_phase_and_operation_drift(self) -> None:
        if not REFERENCE.is_file():
            self.skipTest("canonical reference is not implemented yet")
        text = REFERENCE.read_text(encoding="utf-8")
        mutations = (
            (
                "| `EXECUTOR_FALLBACK` | `EXECUTE` | `PROTECTED_EXECUTOR` |",
                "| `EXECUTOR_FALLBACK` | `EXECUTE` | `PROTECTED_BASH` |",
                "EXECUTOR_FALLBACK",
            ),
            (
                "| `NARROW_DIAGNOSIS` | `DIAGNOSE` |",
                "| `NARROW_DIAGNOSIS` | `NOT_A_PHASE` |",
                "NARROW_DIAGNOSIS",
            ),
            (
                "| `NARROW_DIAGNOSIS` |",
                "| `RENAMED_DIAGNOSIS` |",
                "canonical set",
            ),
        )
        for old, new, reason in mutations:
            with self.subTest(reason=reason):
                changed = text.replace(old, new, 1)
                self.assertTrue(
                    any(reason in error for error in boundary_errors(changed)),
                    boundary_errors(changed),
                )

    def test_prompt_bearing_instructions_share_concise_routing_contract(self) -> None:
        required = (
            "references/native-execution-boundary.md",
            "Direct main-session operational Bash requires `ACTIVE`",
            "`CONFIGURED_UNPROVEN`",
            "`printf P005_GUARD_PROBE`",
            "does not authorize",
            "delegate",
            "do not execute",
        )
        for path in (AGENTS, SKILL):
            text = path.read_text(encoding="utf-8")
            for clause in required:
                with self.subTest(path=path.name, clause=clause):
                    self.assertIn(clause, text)
            self.assertNotIn("| Operation | Phase | Route |", text)


if __name__ == "__main__":
    unittest.main()
