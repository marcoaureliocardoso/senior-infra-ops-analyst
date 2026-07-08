---
description: "Triage and stabilize an infrastructure incident."
---
# /incident-triage

Purpose: triage and stabilize an infrastructure incident.

Use:

```text
/incident-triage Users cannot access the academic system after firewall maintenance
```

Inputs expected:
- symptom
- affected users/services
- start time or detection time
- recent changes
- available tools/logs/dashboards

Behavior:
- Use `skills/incident-response/SKILL.md`.
- Use `skills/incident-response/templates/incident-worksheet.md`.
- Use `references/incident-severity.md` for SEV classification.
- Use `references/diagnostic-order.md` for evidence collection.
- Do not execute disruptive mitigation without approval.

Output: incident worksheet with SEV, impact, facts, commands, hypotheses, mitigation options, approval gates, and stakeholder update.
