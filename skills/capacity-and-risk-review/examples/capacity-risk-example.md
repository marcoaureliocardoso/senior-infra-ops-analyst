# Example: Capacity and Risk Review — Aging Virtualization Host

## Scenario

A single VMware host supports directory services, WSUS, and administrative systems. Storage alerts show datastore usage above 88% and backup jobs have grown from 2h to 6h.

## Evidence collected

| Evidence | Observation | Risk interpretation |
|---|---|---|
| Datastore usage | `datastore01` 88-92% used during business hours | High saturation risk; snapshots can exhaust space. |
| VM placement | DC, WSUS, and file services on same host | Single point of failure. |
| Backup duration | Full job regularly exceeds maintenance window | Recovery confidence and RPO at risk. |
| Hardware lifecycle | Warranty expired 18 months ago | Repair time and parts availability risk. |
| Monitoring | No alert for snapshot age | Slow-moving risk can become outage. |

## Risk matrix

| Risk | Likelihood | Impact | Urgency | Evidence strength | Priority | Exit criterion |
|---|---|---|---|---|---|---|
| Datastore exhaustion | High | High | High | Observed | P1 | Sustained free space above 25% and snapshot age alerts active. |
| Host hardware failure | Medium | High | Medium | Inferred | P2 | Workload replicated or replacement host approved. |
| Backup window overrun | High | Medium | High | Observed | P1 | Backup completes inside agreed window for 7 days. |

## Immediate mitigations

- Review snapshots and orphaned ISO/media attachments using read-only checks first.
- Confirm last successful restore test date.
- Add alert for datastore free space and snapshot age.

## Approval-required actions

- Deleting snapshots, resizing datastores, moving VMs, changing backup retention, or provisioning new capacity requires explicit approval.

## 30/60/90-day plan

| Horizon | Action | Owner | Validation |
|---|---|---|---|
| 30 days | Implement datastore and snapshot alerts | Infra | Alert test evidence. |
| 60 days | Perform isolated restore test | Infra/backup owner | Restore report with RTO/RPO. |
| 90 days | Approve host refresh or second-host resilience plan | Management/Infra | Approved procurement/change plan. |
