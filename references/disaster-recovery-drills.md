# Disaster Recovery Drills Reference

Use this for DR exercises, restore tests, failover readiness, backup validation, RTO/RPO checks, tabletop exercises, and recovery evidence.

## Safety rules

- Prefer tabletop and isolated restore tests before production failover.
- Treat backup locations, credentials, topology, recovery sites, and RTO/RPO data as `SENSITIVE_OUTPUT`.
- Production failover, DNS cutover, restore overwrite, replication break, and destructive testing require formal approval.
- Define abort criteria before starting.

## Drill types

- Tabletop: discuss scenario and decisions; no systems changed.
- Technical restore test: restore to isolated target and validate data/app behavior.
- Component failover: one dependency or replica.
- Full service failover: coordinated service move; highest risk.

## Read-only/pre-drill checks

```bash
# Examples only; adapt per platform.
ls -lh <backup-location>
restic snapshots || borg list <repo> || rclone lsd <remote>
aws backup list-recovery-points-by-backup-vault --backup-vault-name <vault>
az backup recoverypoint list --vault-name <vault> --resource-group <rg> --container-name <container> --item-name <item>
gcloud compute snapshots list
```

## Drill execution outline

1. Define scope, scenario, RTO/RPO, success criteria, and abort conditions.
2. Confirm approvals and communications.
3. Capture baseline service state.
4. Execute isolated restore or approved failover step.
5. Validate application, data integrity, access, monitoring, and logs.
6. Record timings and deviations.
7. Roll back or clean up.
8. Produce findings and corrective actions.

## Risk mapping

- Backup inventory: `SAFE_READ_ONLY` + `SENSITIVE_OUTPUT`.
- Isolated restore: `STATE_CHANGING` in test environment.
- Production failover/cutover: `DISRUPTIVE`, formal approval required.
- Restore overwrite/delete: `DESTRUCTIVE`, formal approval required.

## Evidence to capture

Scenario, participants, approvals, assets, backup point, start/end time, RTO/RPO result, validation evidence, failures, corrective actions, and next drill date.
