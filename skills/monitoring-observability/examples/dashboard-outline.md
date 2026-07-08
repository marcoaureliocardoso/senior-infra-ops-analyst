# Dashboard Outline Example

Use this as a service dashboard outline. Replace tool names with the local stack, such as Prometheus/Grafana, Zabbix, ELK/OpenSearch, CloudWatch, Azure Monitor, Google Cloud Monitoring, VMware Aria, or pfSense/Netgate logs.

## 1. Header

- Service name, owner, runbook link, escalation contact, environment.
- Current status: healthy / degraded / incident / maintenance.

## 2. SLO panel

Data source: metrics backend.

Suggested queries:
- availability SLI over 5m, 1h, 24h, 30d
- latency p50/p95/p99
- error rate by endpoint or dependency
- error budget remaining and burn rate

## 3. Saturation and capacity

- CPU, memory, disk, inode, network, queue depth, connection count.
- Forecast panel: current trend, time to threshold, top capacity risks.

## 4. Dependency health

- DNS, identity, database, storage, upstream API, firewall/VPN, cloud provider health.
- Show dependency status separately from service symptoms.

## 5. Recent changes

Data source: deployment logs, Git, ITSM, cloud activity log, hypervisor events.

- Last deployment/change.
- Config diff or change ticket.
- Operator and timestamp.

## 6. Logs/events

- Top error signatures with redaction.
- Time-bounded log query around alert start.
- Link to detailed log search, not raw sensitive output.

## 7. Backup and recovery posture

- Last successful backup.
- Last restore test.
- RPO/RTO status.
- Snapshot age warning.

## 8. Layout recommendation

Top row: status, SLO, burn rate, active alerts.
Middle row: latency/error/saturation and dependency health.
Bottom row: recent changes, logs, capacity forecast, runbook/owner links.
