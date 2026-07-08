---
description: "Prepare a factual ITSM or CMDB incident, change, or problem update without mutating records unless explicitly requested."
---
# /itsm-update

Purpose: prepare a factual ITSM/CMDB incident/change/problem update or impact analysis without mutating records unless explicitly requested.

Expected input:
- ticket ID, service/CI, current evidence, action taken, next step, audience.

Behavior:
- Use `skills/itsm-cmdb-workflows/SKILL.md`.
- Use `skills/itsm-cmdb-workflows/templates/itsm-cmdb-update.md`.
- Separate observed facts from hypotheses.
- Do not change priority, severity, assignee, state, SLA, approval, or CMDB relationships without explicit instruction.

Example:
`/itsm-update INC001234 service=portal include latest DNS evidence and next owner`
