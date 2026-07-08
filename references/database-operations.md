# Database Operations Reference

Use this when investigating database availability, connection saturation, replication lag, slow queries, locks, storage pressure, backup health, or maintenance windows.

## Scope

Covers PostgreSQL, MySQL/MariaDB, Microsoft SQL Server, and MongoDB at a safe operational level. Prefer vendor-specific runbooks for engine-specific changes.

## Safety rules

- Treat query text, database names, usernames, connection strings, and result samples as `SENSITIVE_OUTPUT`.
- Start with metadata, health, sessions, locks, replication, and storage checks before query cancellation or restart.
- Do not run `KILL`, `pg_terminate_backend`, `DROP`, `ALTER`, index rebuilds, vacuum/full, failover, or restart without explicit approval.
- Limit result sets. Never dump tables or broad query results for diagnosis.
- Preserve timestamps, server names, replica roles, and transaction identifiers in evidence.

## Read-only checks

### PostgreSQL

```bash
psql -X -c "select now(), version();"
psql -X -c "select datname, numbackends, xact_commit, xact_rollback, deadlocks from pg_stat_database;"
psql -X -c "select pid, usename, state, wait_event_type, wait_event, now()-query_start as age from pg_stat_activity order by age desc limit 20;"
psql -X -c "select locktype, mode, granted, count(*) from pg_locks group by 1,2,3 order by count desc;"
psql -X -c "select * from pg_stat_replication;"
```

Interpretation:
- Many active sessions with same wait event -> bottleneck or blocking.
- `idle in transaction` with long age -> transaction leak risk.
- Replication lag or absent rows on a primary expected to replicate -> DR/read replica risk.

### MySQL / MariaDB

```bash
mysql -e "SHOW GLOBAL STATUS LIKE 'Threads%';"
mysql -e "SHOW FULL PROCESSLIST;"
mysql -e "SHOW ENGINE INNODB STATUS\\G"
mysql -e "SHOW REPLICA STATUS\\G" || mysql -e "SHOW SLAVE STATUS\\G"
```

Interpretation:
- Many `Locked` or long-running sessions -> blocking or slow query pressure.
- Replica IO/SQL thread stopped -> replication health issue.
- InnoDB deadlocks in latest section -> application transaction conflict.

### SQL Server

```powershell
Invoke-Sqlcmd -Query "SELECT @@SERVERNAME AS server_name, @@VERSION AS version_text;"
Invoke-Sqlcmd -Query "SELECT session_id,status,blocking_session_id,wait_type,cpu_time,total_elapsed_time FROM sys.dm_exec_requests ORDER BY total_elapsed_time DESC;"
Invoke-Sqlcmd -Query "SELECT name,state_desc,recovery_model_desc FROM sys.databases;"
```

Interpretation:
- Non-zero `blocking_session_id` chains -> lock contention.
- Long waits in storage/network classes -> infrastructure bottleneck.

### MongoDB

```javascript
db.adminCommand({ ping: 1 })
db.serverStatus().connections
db.currentOp({ active: true })
rs.status()
```

Interpretation:
- Connection exhaustion -> pool/application pressure.
- Long active ops -> query/index issue.
- Replica set unhealthy -> failover or quorum risk.

## Risk mapping

- Session/process inspection: `SAFE_READ_ONLY` + `SENSITIVE_OUTPUT`.
- Slow query and lock inspection: `SAFE_READ_ONLY` + `SENSITIVE_OUTPUT`.
- Backup metadata check: `SAFE_READ_ONLY`; add `SENSITIVE_OUTPUT` when paths or object names identify systems.
- Query cancellation, failover, restart, index rebuild: `STATE_CHANGING` or `DISRUPTIVE`, requires approval.

## Evidence to capture

- Engine/version, role, uptime, active sessions, waits/locks, replication state, storage free space, latest backup metadata, and affected services.

## Related references

- `references/storage-backup.md`
- `references/disaster-recovery-drills.md`
- `references/monitoring-stack-operations.md`
- `references/audit-compliance-evidence.md`
