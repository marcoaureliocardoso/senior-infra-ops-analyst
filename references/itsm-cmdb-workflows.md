# ITSM and CMDB Workflows Reference

Use this for incident/change/problem records, CI ownership, impact analysis, dependency mapping, escalation notes, change evidence, and post-incident traceability.

## Safety rules

- Treat ticket IDs, user reports, CI names, asset tags, topology, and business impact as `SENSITIVE_OUTPUT`.
- Do not close, resolve, reassign, approve, cancel, or change priority without explicit instruction.
- Keep diagnosis evidence linked to the correct incident/change/problem and CMDB CI.
- Prefer factual updates over speculation.

## Workflow mapping

- Incident: restore service and reduce impact.
- Problem/RCA: identify underlying cause and preventive actions.
- Change: document controlled alteration, risk, rollback, and validation.
- CMDB: map service, CI, owner, dependency, environment, and support group.

## Read-only checks

```text
- Search active incidents for same service/CI.
- Check recent changes affecting the CI or dependency chain.
- Check known errors/problems linked to the service.
- Confirm CI owner, support group, criticality, maintenance window, and dependencies.
```

## Record update structure

```text
Observed:
Impact:
Evidence:
Action taken:
Risk/approval:
Next step:
Owner:
Timestamp:
```

## Risk mapping

- Reading records/CMDB: `SAFE_READ_ONLY` + `SENSITIVE_OUTPUT`.
- Updating notes: `STATE_CHANGING` but usually low operational risk; still requires user instruction.
- Priority/severity/approval/closure changes: `STATE_CHANGING`, approval required.

## Evidence to capture

Ticket ID, CI, service, impact, severity, timeline, recent changes, owner, communications, actions, approvals, and linked RCA/change/problem.
