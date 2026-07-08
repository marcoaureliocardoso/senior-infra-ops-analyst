---
description: "Create a runbook or branching playbook for infrastructure operations."
---
# /runbook

Purpose: create a runbook or branching playbook for infrastructure operations.

Use:

```text
/runbook Create a playbook for diagnosing VPN users who cannot reach internal systems
```

Inputs expected:
- target system or service
- task type: routine runbook or branching playbook
- prerequisites
- commands and validation criteria
- rollback or escalation path

Behavior:
- Use `skills/runbook-authoring/SKILL.md`.
- Use `skills/runbook-authoring/templates/runbook.md` for linear procedures and `skills/runbook-authoring/templates/playbook.md` for branching incident workflows. For changes, use `skills/change-management/templates/change-plan.md` as supporting structure.
- For command evidence, use `skills/command-driven-operations/templates/command-record.md`.
- Distinguish linear runbooks from branching playbooks.

Output: procedure with prerequisites, safety gates, steps, expected outputs, interpretation, rollback/escalation, and evidence to archive.
