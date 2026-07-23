---
name: Runbook Authoring
description: Use when creating or improving infrastructure runbooks, standard operating procedures, maintenance guides, recovery procedures, checklists, or handover documentation.
version: 0.4.5
last_updated: 2026-07-23
maintainer: Marco Aurelio Cardoso
triggers:
  - runbook
  - playbook
  - sop
  - handover
  - operational procedure
---

# Runbook Authoring

Write runbooks that an operator can follow under pressure without guessing.

<required>
1. State purpose, scope, prerequisites, required access, risk level, and expected duration.
2. Include pre-checks, step-by-step commands, expected output, interpretation, validation, rollback, and escalation criteria.
3. Separate `SAFE_READ_ONLY` diagnostics from `LOW_RISK_CHANGE`, `DISRUPTIVE_CHANGE`, and `DESTRUCTIVE` actions.
4. Mark disruptive actions and approval gates clearly.
5. Include evidence to capture for audit, troubleshooting, or handover.
</required>

## Runbook template

1. Purpose
2. Scope
3. Systems affected
4. Required access
5. Preconditions
6. Risk and impact
7. Command sequence
8. Expected outputs and interpretation
9. Validation
10. Rollback
11. Troubleshooting branches
12. Escalation
13. Evidence/logs to retain
14. Last reviewed date

## Required references

- `references/diagnostic-order.md`
- `references/risk-levels.md`

## Runbook versus playbook

- A runbook is a mostly linear operational procedure for a known task.
- A playbook is branching and decision-driven: if condition X is observed, follow path Y.
- Choose runbook for routine maintenance and playbook for incident/triage flows.

## Output

Return a complete runbook draft in Markdown.

## Template completeness rule

Do not leave skeletal placeholders as finished runbooks. Every template-based output must include purpose, inputs, ordered steps, risk classification, expected observations, interpretation, rollback or stop conditions, validation, and escalation path.
