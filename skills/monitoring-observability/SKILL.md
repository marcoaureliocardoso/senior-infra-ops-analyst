---
name: Monitoring and Observability
skill_id: monitoring-observability
description: Use when designing, reviewing, or improving monitoring, logging, alerting, dashboards, SLOs, health checks, capacity metrics, or incident detection for infrastructure services.
---

# Monitoring and Observability

Design monitoring that detects real user-impacting problems early without drowning operators in noise.

<required>
1. Identify the service, users, dependencies, and failure modes.
2. Define symptoms worth alerting on, not only low-level resource thresholds.
3. Execute safe metric/log checks when tool access exists.
4. Separate alerts, dashboards, logs, traces, reports, and capacity indicators.
5. Include severity, threshold, duration, owner, runbook link, and expected operator action for each alert.
6. Flag noisy, unactionable, duplicate, or missing alerts.
</required>

## Monitoring model

Cover availability, latency, error rate, saturation, capacity trend, dependency health, certificate expiration, backup success/failure, authentication failures, and security-relevant anomalies.

## Alert quality

A good alert has clear symptom, real impact, threshold, duration, severity, owner, first diagnostic step, escalation path, and runbook.

## Output

Return:

- Observability gaps
- Checks executed
- Recommended metrics and logs
- Alert rules
- Dashboard layout
- Runbook links or runbook stubs
- Noise-reduction recommendations
