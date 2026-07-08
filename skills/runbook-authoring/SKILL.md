---
name: Runbook Authoring
skill_id: runbook-authoring
description: Use when creating or improving infrastructure runbooks, standard operating procedures, maintenance guides, recovery procedures, checklists, or handover documentation.
---

# Runbook Authoring

Write runbooks that an operator can follow under pressure without guessing.

<required>
1. State purpose, scope, prerequisites, required access, risk level, and expected duration.
2. Include pre-checks, step-by-step commands, expected output, interpretation, validation, rollback, and escalation criteria.
3. Separate read-only diagnostics from state-changing actions.
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

## Output

Return a complete runbook draft in Markdown.


## Template completeness rule

Do not leave skeletal placeholders as finished runbooks. Every template-based output must include purpose, inputs, ordered steps, risk classification, expected observations, interpretation, rollback or stop conditions, validation, and escalation path.
