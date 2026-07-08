---
name: Monitoring Stack Operations
description: Use when diagnosing Prometheus, Grafana, Zabbix, ELK/Elastic/OpenSearch, alerting, scraping, ingestion, dashboard, or query failures.
version: 0.4.4
last_updated: 2026-07-08
maintainer: Marco Aurelio Cardoso
triggers:
  - monitoring-stack-operations
  - monitoring stack operations
---

# Monitoring Stack Operations

Use this skill when the operational domain materially changes the diagnostic order, evidence type, approval gate, or interpretation. The shared command-driven posture still applies, but the domain-specific reference and template are mandatory context.

<required>
1. Identify stack component, data source, target/service, alert rule, dashboard, time range, and whether the issue is monitoring-only or service-impacting.
2. Use `references/monitoring-stack-operations.md` for Prometheus, Grafana, Zabbix, Elastic/ELK, and OpenSearch checks.
3. Cross-reference `references/observability-slo-sli.md` when changing alerts, SLOs, burn-rate alerts, or dashboard definitions.
4. Treat metrics labels, logs, screenshots, query results, credentials, endpoints, and user data as `SENSITIVE_OUTPUT`.
5. Run read-only checks first: target/scrape health, query status, datasource health, alert state, ingestion lag, disk pressure, and selected recent logs.
6. Interpret failure by layer: exporter down, scrape error, label mismatch, query too expensive, datasource auth, index ingestion delay, retention/disk, or alert rule noise.
7. Require approval before disabling alerts, deleting indices, changing retention, reloading configs, silencing broad alerts, or restarting collectors.
8. Classify broad queries and log searches as `RESOURCE_INTENSIVE` and limit by time, label, namespace, host, or index.
9. Produce `skills/monitoring-stack-operations/templates/monitoring-stack-incident.md` with signal path, broken layer, query evidence, impact on detection, and safe remediation.
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

- `references/monitoring-stack-operations.md`
- `references/risk-levels.md`
- `references/command-execution-protocol.md`
- `references/diagnostic-order.md`
- `references/external-sources.md`
