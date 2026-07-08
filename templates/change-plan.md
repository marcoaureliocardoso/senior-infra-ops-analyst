# Change Plan

Use this template with `skills/change-management/SKILL.md`. Fill every section or mark it `N/A` with a reason.

## 1. Objective

What will change, on which systems, and what outcome is expected?

Example: Replace DNS forwarder on the secondary resolver to restore recursive lookup reliability.

## 2. Operational reason

Why is this change needed now? Link to incident, risk, lifecycle, capacity, security, or maintenance evidence.

## 3. Scope

In scope:
- _List exact targets._

Out of scope:
- _List related systems that must not be touched._

## 4. Systems affected

| System | Role | Environment | Owner | Criticality |
|---|---|---|---|---|
|  |  |  |  |  |

## 5. Affected users/services

Expected visible impact and affected user groups.

## 6. Dependencies

Upstream/downstream dependencies, DNS, DHCP, firewall, identity, storage, cloud, backup, monitoring, or vendor dependencies.

## 7. Risk classification

Use `references/risk-levels.md`.

| Action | Risk | Modifiers | Reason |
|---|---|---|---|
|  |  |  |  |

## 8. Blast radius

Maximum credible impact if the change fails.

## 9. Maintenance window

Start, end, timezone, freeze windows, and communication deadlines.

## 10. Preconditions

- Authorized change window confirmed.
- Current config captured.
- Backup/snapshot/restore point verified when applicable.
- Monitoring and rollback owner available.

## 11. Backout conditions

Stop or rollback if:
- validation fails;
- error rate/latency exceeds threshold;
- affected service becomes unreachable;
- unexpected dependency impact is observed;
- rollback window would be exceeded.

## 12. Backup/snapshot/restore evidence

| Evidence | Location | Timestamp | Verified by |
|---|---|---|---|
|  |  |  |  |

## 13. Safe pre-checks

| Risk | Command | Purpose | Expected normal signal | Interpretation if abnormal |
|---|---|---|---|---|
| SAFE_READ_ONLY |  |  |  |  |

## 14. Implementation steps requiring approval

| Step | Risk | Command/action | Expected effect | Validation | Rollback |
|---|---|---|---|---|---|
| 1 |  |  |  |  |  |

## 15. Validation commands

| Command | Success signal | Failure signal | Next action |
|---|---|---|---|
|  |  |  |  |

## 16. Rollback commands

| Trigger | Command/action | Expected effect | Validation |
|---|---|---|---|
|  |  |  |  |

## 17. Post-change monitoring

Metrics, logs, alerts, dashboards, and duration of watch period.

## 18. Communication

Before: _Who is notified and when._

During: _Where status updates go._

After: _Completion or rollback notice._

## 19. Evidence to archive

Commands, outputs, screenshots, config diff, ticket/change ID, approvals, timestamps, and validation results.

## Anti-patterns

- No rollback command.
- Missing backout conditions.
- “Restart and observe” without success/failure thresholds.
- Changing firewall, DNS, DHCP, identity, storage, or hypervisor config without approval.
