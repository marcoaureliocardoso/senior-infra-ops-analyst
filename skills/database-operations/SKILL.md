---
name: Database Operations
description: Use when diagnosing database availability, sessions, locks, replication, storage, backup health, or performance symptoms before recommending database changes.
version: 0.4.1
last_updated: 2026-07-08
maintainer: Marco Aurelio Cardoso
triggers:
  - database-operations
  - database operations
---

# Database Operations

Use this skill when the operational domain materially changes the diagnostic order, evidence type, approval gate, or interpretation. The shared command-driven posture still applies, but the domain-specific reference and template are mandatory context.

<required>
1. Identify engine, role, topology, affected application, data sensitivity, HA/replication mode, and the exact symptom before touching queries or service state.
2. Confirm whether the issue is availability, latency, lock contention, storage, replication lag, authentication, backup/restore, or maintenance/change related.
3. Use `references/database-operations.md` to select engine-specific read-only checks for PostgreSQL, MySQL/MariaDB, SQL Server, or Redis.
4. Run only scoped read-only queries first: sessions, locks, replication, size, wait/event, slow query indicators, backup status, and service reachability.
5. Classify SQL text, usernames, table names, connection strings, and query results as `SENSITIVE_OUTPUT`; summarize rather than dumping rows.
6. Interpret each result in operational terms: blocking chain, saturated storage, failed replica, exhausted connections, bad plan symptom, or client-side timeout.
7. Before proposing kill session, failover, restart, vacuum/reindex, schema change, purge, restore, or parameter change, classify risk and require approval.
8. Use `references/risk-levels.md`, `references/command-execution-protocol.md`, and the shared diagnostic order unless database safety requires a narrower order.
9. Produce `skills/database-operations/templates/database-incident.md` with engine, evidence, interpretation, mitigation options, rollback, and validation.
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

- `references/database-operations.md`
- `references/risk-levels.md`
- `references/command-execution-protocol.md`
- `references/diagnostic-order.md`
- `references/external-sources.md`
