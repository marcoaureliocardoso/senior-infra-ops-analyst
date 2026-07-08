---
description: "Produce a blameless root cause analysis from incident evidence."
---
# /rca

Purpose: produce a blameless RCA from incident evidence.

Use:

```text
/rca Analyze yesterday's DNS outage using the incident notes and command outputs
```

Inputs expected:
- incident summary
- timeline
- command output or logs
- changes around the incident
- mitigation and recovery actions

Behavior:
- Use `skills/root-cause-analysis/SKILL.md`.
- Use templates under `skills/root-cause-analysis/templates/`:
  - `evidence-map.md`
  - `action-table.md`
  - `rca-draft.md`
- Separate facts from hypotheses.
- Produce corrective actions with owner, priority, due date, validation, and risk.

Output: RCA draft, evidence map, action table, contributing factors, and prevention plan.
