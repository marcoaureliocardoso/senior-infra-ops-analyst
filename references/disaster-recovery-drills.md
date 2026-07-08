# Disaster Recovery Drills Reference

Use this for DR exercises, restore tests, failover readiness, backup validation, RTO/RPO checks, tabletop exercises, dependency validation, and recovery evidence.

## Safety rules

- Prefer tabletop and isolated restore tests before production failover.
- Treat backup locations, credentials, topology, recovery sites, access paths, and RTO/RPO data as `SENSITIVE_OUTPUT`.
- Production failover, DNS cutover, restore overwrite, replication break, queue replay, and destructive testing require formal approval.
- Define abort criteria, communications, roles, and rollback before starting any technical drill.
- Do not assume a backup is valid until restored and functionally validated.

## Drill types

| Drill type | State change | Typical goal | Approval level |
|---|---|---|---|
| Tabletop | None | Validate roles, sequence, gaps | Low |
| Backup inventory review | Read-only | Confirm recovery points and coverage | Low, sensitive output |
| Isolated restore | Test environment | Validate restore process and data integrity | Change approval for test scope |
| Component failover | Limited production/test | Validate one dependency or replica | Formal approval |
| Full service failover | Production-impacting | Validate end-to-end recovery | Highest approval |

## Pre-drill read-only checks

```bash
# Examples only; adapt per platform and scope.
ls -lh <backup-location>
restic -r <repo> snapshots || borg list <repo> || rclone lsd <remote>
aws backup list-recovery-points-by-backup-vault --backup-vault-name <vault>
az backup recoverypoint list --vault-name <vault> --resource-group <rg> --container-name <container> --item-name <item>
gcloud compute snapshots list
```

## Dependency checklist

| Layer | Validate before drill | Evidence |
|---|---|---|
| Identity | Admin/break-glass access works | Login test or access record |
| Network | Recovery path, firewall, VPN, DNS TTL | Route/firewall/DNS evidence |
| Compute | Target capacity and boot order | VM/host/cloud inventory |
| Storage | Recovery point, free space, encryption keys | Backup/snapshot metadata |
| Database | Consistency, replication, restore sequence | Backup logs, restore test |
| Application | Config, secrets, external integrations | Smoke test list |
| Monitoring | Alerts/dashboards for recovery state | Dashboard/alert evidence |
| ITSM | Change/incident/drill record | Approved ticket |

## Drill execution outline

1. Define scope, scenario, RTO/RPO, data set, success criteria, and abort conditions.
2. Confirm approvals, communication plan, participants, and escalation path.
3. Capture baseline state and recovery point metadata.
4. Execute tabletop, isolated restore, or approved failover step.
5. Validate data integrity, authentication, DNS/routing, TLS, application smoke tests, monitoring, and logs.
6. Record actual timings: decision time, start, restore/failover complete, validation complete, rollback/cleanup complete.
7. Roll back or clean up test resources.
8. Produce findings, corrective actions, owners, due dates, and next drill date.

## RTO/RPO interpretation

- RTO met: service restored and validated within the target time.
- RTO missed: identify the slowest phase, not just total duration.
- RPO met: restored data is no older than allowed objective.
- RPO missed: determine whether backup schedule, replication lag, failed job, or restore selection caused the miss.

## Risk mapping

- Backup inventory: `SAFE_READ_ONLY` + `SENSITIVE_OUTPUT`.
- Isolated restore: `STATE_CHANGING` in test environment; watch data handling.
- Component failover/DNS cutover: `DISRUPTIVE_CHANGE`, formal approval required.
- Restore overwrite/delete, replication break, destructive tests: `DESTRUCTIVE`, formal approval required.

## Evidence to capture

Scenario, participants, approvals, assets, dependencies, recovery point, commands/tools used, start/end timestamps, RTO/RPO result, validation evidence, failures, deviations, corrective actions, owners, due dates, and next drill date.

## Related references

- `references/storage-backup.md` for backup/restore mechanics.
- `references/database-operations.md` for database restore/replication concerns.
- `references/dns-dhcp.md` and `references/load-balancers-reverse-proxies.md` for cutover paths.
- `references/pki-certificate-lifecycle.md` for certificate validity in recovery environment.
- `references/itsm-cmdb-workflows.md` and `references/audit-compliance-evidence.md` for approvals and evidence.
