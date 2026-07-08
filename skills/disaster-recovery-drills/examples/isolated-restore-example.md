# Example: Isolated VM Restore Drill

## Scenario

Quarterly DR drill validates that the domain controller backup can be restored into an isolated network without touching production. The drill is evidence-only and must not promote restored services into production.

## Drill plan

| Item | Value |
|---|---|
| Drill type | Isolated restore validation |
| Asset | `DC-02` VM backup from previous night |
| RTO target | 4 hours |
| RPO target | 24 hours |
| Isolation boundary | Dedicated hypervisor port group with no route to production |
| Success criteria | VM boots, filesystem mounts, AD database present, event logs readable |
| Explicit non-goal | No production failover and no replication back to live AD |

## Evidence sequence

1. Confirm latest successful backup job and restore point timestamp.
2. Export backup job report and repository health summary.
3. Restore VM into isolated network with NIC disconnected or isolated VLAN.
4. Boot VM and capture boot time, disk status, and critical service state.
5. Validate application/service data presence without connecting to production.
6. Record elapsed time against RTO and restore point age against RPO.
7. Destroy or retain isolated VM according to retention policy.

## Interpretation

The restore point meets RPO if it is less than 24 hours old. The drill meets RTO if the VM is booted and basic service validation is complete within 4 hours. Any inability to boot, missing disk, or credential/access gap is a DR readiness finding even if production was not impacted.

## Findings

| Finding | Severity | Evidence | Action |
|---|---|---|---|
| Restore completed in 2h 15m | Pass | Drill timestamps | None |
| Restore point age 11h 40m | Pass | Backup report | None |
| Isolated network lacked documented DNS test method | Medium | Operator notes | Add DNS validation step to DR runbook |

## Approval gate

Do not connect restored identity services to production networks, do not seize roles, and do not enable replication without an approved disaster declaration and senior authorization.
