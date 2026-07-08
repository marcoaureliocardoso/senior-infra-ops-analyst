---
name: ITSM and CMDB Workflows
description: Use when updating or correlating incident, change, problem, CMDB, CI ownership, dependency, impact, support group, or service record workflows.
version: 0.4.3
last_updated: 2026-07-08
maintainer: Marco Aurelio Cardoso
triggers:
  - itsm-cmdb-workflows
  - itsm and cmdb workflows
---

# ITSM and CMDB Workflows

Use this skill when the operational domain materially changes the diagnostic order, evidence type, approval gate, or interpretation. The shared command-driven posture still applies, but the domain-specific reference and template are mandatory context.

<required>
1. Identify record type, ticket/change/problem ID, service, CI, owner, support group, business impact, dependency chain, and desired workflow action.
2. Use `references/itsm-cmdb-workflows.md` to correlate incidents, changes, known errors, CI relationships, ownership, maintenance windows, and audit trail.
3. Cross-reference incident severity, change management, RCA, audit evidence, and vendor escalation references when records drive operational decisions.
4. Treat ticket details, CI names, topology, user reports, asset tags, impact statements, and internal notes as `SENSITIVE_OUTPUT`.
5. Perform read-only record lookups and relationship checks before proposing updates, reassignment, priority change, approval, or closure.
6. Interpret workflow data as supporting evidence, not ground truth: stale CMDB, missing owner, unlinked change, duplicate incident, or wrong CI can mislead diagnosis.
7. Require approval or explicit instruction before changing state, priority, assignment, closure, approval status, SLA pause, or CMDB relationships.
8. Use shared risk vocabulary even for ticket changes: they are `STATE_CHANGING` because they alter audit history and workflow obligations.
9. Produce `skills/itsm-cmdb-workflows/templates/itsm-cmdb-update.md` with record summary, CI mapping, linked evidence, proposed updates, and approval boundary.
</required>

## Output

Return:
- Situation and scope
- Domain-specific command/evidence sequence
- Commands executed or explicitly not executed
- Observations and interpretation
- Risk classification and modifiers
- Recommended next action
- Approval gate, if needed
- Completed template artifact

## References

- `references/itsm-cmdb-workflows.md`
- `references/risk-levels.md`
- `references/command-execution-protocol.md`
- `references/diagnostic-order.md`
- `references/external-sources.md`
