# Example: PostgreSQL Lock Triage

## Scenario

Users report timeouts when saving records in the student portal. Application logs show database query timeouts. Scope is read-only PostgreSQL session, lock, replication, and storage diagnostics.

## Evidence sequence

| Step | Query/command | Risk | Observed result |
|---|---|---|---|
| Check active sessions | `select pid, usename, state, wait_event_type, wait_event, now()-query_start age, left(query,120) from pg_stat_activity where state <> 'idle';` | `SAFE_READ_ONLY + SENSITIVE_OUTPUT` | 18 active sessions; 11 waiting on locks. |
| Identify blockers | `select blocked_locks.pid blocked_pid, blocking_locks.pid blocking_pid from pg_locks blocked_locks join pg_locks blocking_locks using (locktype,database,relation,page,tuple,virtualxid,transactionid,classid,objid,objsubid) where not blocked_locks.granted and blocking_locks.granted;` | `SAFE_READ_ONLY + SENSITIVE_OUTPUT` | One reporting transaction blocks several writes. |
| Check long transactions | `select pid, now()-xact_start age, state, left(query,160) from pg_stat_activity where xact_start is not null order by age desc limit 10;` | `SAFE_READ_ONLY + SENSITIVE_OUTPUT` | Oldest transaction age is 42 minutes. |
| Check replication | `select application_name, state, sync_state, write_lag, flush_lag, replay_lag from pg_stat_replication;` | `SAFE_READ_ONLY` | Replica lag below 2 seconds. |
| Check disk | `df -h` on database host | `SAFE_READ_ONLY` | Data volume 71% used. |

## Interpretation

The primary symptom is lock contention caused by one long-running transaction. Replication and disk capacity do not explain the immediate timeout. Terminating the blocking backend could restore writes, but it is a state-changing action and may roll back work.

## Mitigation options

| Option | Risk | When appropriate | Approval required |
|---|---|---|---|
| Ask application owner to stop the report/job gracefully | Lower | Owner reachable and impact tolerable | Yes, via incident commander or service owner |
| Cancel query with `pg_cancel_backend(pid)` | Moderate | Query is safe to cancel, transaction can remain | Yes |
| Terminate session with `pg_terminate_backend(pid)` | Disruptive | User impact is severe and rollback consequence is understood | Explicit approval required |

## Output record

- Service: student portal
- DB engine: PostgreSQL
- Probable cause: long-running transaction blocking writes
- Evidence retained: sanitized query snippets, blocker PID, lock graph
- Next action: approval request to cancel or terminate blocker
