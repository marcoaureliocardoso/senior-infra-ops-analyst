# ITSM and CMDB Workflows Reference

Use this for incident/change/problem records, CI ownership, impact analysis, dependency mapping, escalation notes, change evidence, service catalog linkage, and post-incident traceability.

## Safety rules

- Treat ticket IDs, user reports, CI names, asset tags, topology, service maps, requester data, and business impact as `SENSITIVE_OUTPUT`.
- Do not close, resolve, reassign, approve, cancel, change priority/severity, pause SLA, or alter CMDB relationships without explicit instruction.
- Keep diagnosis evidence linked to the correct incident/change/problem and CMDB CI.
- Prefer factual updates over speculation; use phrases like "observed", "reported", and "pending validation".
- CMDB can be stale. Treat it as evidence to verify, not automatic truth.

## Workflow map

| Workflow | Operational purpose | Common read-only evidence | State-changing boundary |
|---|---|---|---|
| Incident | Restore service and reduce impact | Impact, timeline, affected CI, linked alerts | Priority/severity, assignment, resolution, closure |
| Change | Control risk of alteration | Change window, approvals, implementation plan | Approval, implementation state, closure |
| Problem/RCA | Prevent recurrence | Related incidents, known errors, workaround | Problem status, known-error publication |
| CMDB | Map service, ownership, and dependencies | CI owner, criticality, dependency graph | CI relationship or attribute changes |
| Request | Fulfill standard service | Request item, approvals, entitlement | Fulfillment/approval state |

## Read-only checks

```text
- Search active incidents for the same service, CI, dependency, or symptom.
- Check recent changes affecting the CI or dependency chain.
- Check known errors/problems linked to the service.
- Confirm CI owner, support group, criticality, maintenance window, and dependencies.
- Compare alert source, user-reported impact, and CMDB service mapping.
- Verify whether a vendor ticket, change freeze, or CAB approval applies.
```

### Generic API examples

These are patterns, not vendor-neutral guarantees. Use only with authorized API tokens and approved scopes.

```bash
# ServiceNow-style read-only record lookup pattern
curl -sS -H "Authorization: Bearer <token>" \
  "https://<instance>/api/now/table/incident?sysparm_query=number=<INC>&sysparm_limit=1"

# Jira-style issue lookup pattern
curl -sS -H "Authorization: Bearer <token>" \
  "https://<site>/rest/api/3/issue/<KEY>"
```

Risk: `SAFE_READ_ONLY` + `SENSITIVE_OUTPUT`. Never paste tokens, cookies, or full ticket dumps into the final answer.

## CMDB relationship checks

| Check | Why it matters | Failure pattern |
|---|---|---|
| CI-to-service relation | Determines blast radius | Incident linked to server but service impact missing |
| Owner/support group | Determines escalation | Ticket sits with wrong team |
| Dependency map | Finds upstream/downstream impact | Database/network dependency omitted |
| Maintenance window | Avoids false incident correlation | Expected change mistaken for outage |
| Recent changes | Narrows cause | Unlinked change hides trigger |

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
Linked CI/change/problem/vendor ticket:
```


## Shell-history warning

Avoid placing bearer tokens, private tokens, cookies, or credentials directly on the command line because they can be captured in shell history, process listings, terminal logs, or audit tooling. Prefer approved secret stores, short-lived environment variables, `--netrc`/credential helpers where appropriate, or vendor CLI authentication. Redact tokens from examples and outputs.

## Risk mapping

- Reading records/CMDB: `SAFE_READ_ONLY` + `SENSITIVE_OUTPUT`.
- Adding a work note requested by the operator: `STATE_CHANGING` but usually low technical risk; still affects audit history.
- Assignment, priority, severity, approval, closure, SLA pause, CMDB relationship edits: `STATE_CHANGING`, approval required.
- Vendor/customer-visible comments: `STATE_CHANGING` + high communication sensitivity.

## Evidence to capture

Ticket ID, CI, service, impact, severity, timeline, recent changes, owner, support group, dependencies, communications, actions, approvals, linked RCA/change/problem/vendor records, and evidence source timestamps.

## Related references

- `references/incident-severity.md` for SEV classification.
- `references/diagnostic-order.md` for technical evidence flow.
- `references/rca-artifacts.md` for problem/RCA follow-up.
- `references/audit-compliance-evidence.md` for evidence retention and redaction.
- `references/vendor-escalation.md` for support handoff packages.
