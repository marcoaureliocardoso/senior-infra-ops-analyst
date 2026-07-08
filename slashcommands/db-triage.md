---
description: "Diagnose database availability, sessions, locks, replication, storage, and backup health."
---
# /db-triage

Purpose: diagnose database availability, sessions, locks, replication, storage, or backup health.

Expected input:
- engine, instance/cluster, affected service, symptom, time window, available credentials/tooling.

Behavior:
- Use `skills/database-operations/SKILL.md`.
- Use `references/database-operations.md` and `references/risk-levels.md`.
- Fill `skills/database-operations/templates/database-incident.md`.

Example:
`/db-triage engine=postgres service=portal symptom="timeouts after login" window="last 30m"`
