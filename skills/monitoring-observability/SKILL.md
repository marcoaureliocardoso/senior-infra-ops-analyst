---
name: Monitoring and Observability
skill_id: monitoring-observability
description: Use when designing, reviewing, or improving monitoring, logging, alerting, dashboards, SLOs, SLIs, error budgets, health checks, capacity metrics, or incident detection for infrastructure and cloud services.
version: 0.4.4
last_updated: 2026-07-08
maintainer: Marco Aurelio Cardoso
triggers:
  - slo
  - sli
  - dashboard
  - alert tuning
  - observability
---

# Monitoring and Observability

Design monitoring that detects user-impacting problems early, explains what changed, and avoids alert fatigue.

<required>
1. Identify the service, users, dependencies, critical user journeys, failure modes, and ownership.
2. Define SLIs before alerts: availability, latency, error rate, saturation, freshness, durability, backup success, or job completion.
3. Map each SLI to an SLO target, measurement window, data source, known blind spots, and error-budget implication.
4. Execute safe metric/log/alert checks when tool access exists, using narrow time windows and redaction for sensitive data.
5. Separate paging alerts, ticket alerts, dashboards, reports, logs, traces, and capacity indicators.
6. For each alert, specify symptom, impact, threshold, duration, severity, owner, runbook, first diagnostic command, and escalation path.
7. Flag noisy, duplicate, unactionable, missing, stale, or threshold-only alerts that do not map to user impact.
</required>

## SLO/SLI model

Use `references/observability-slo-sli.md`.

Minimum SLI definition:

- Service or user journey
- Indicator formula
- Good event / total event definition
- Data source and query
- Window: rolling, calendar, or incident window
- Target and rationale
- Error budget and burn-rate alerting approach
- Known gaps and proxy limitations

## Alert design

Prefer symptoms over causes. A page should mean a human must act now.

Good alert examples:

- API availability below SLO over a burn-rate window
- backup job failed and no recent successful restore point exists
- certificate expires within actionable window
- disk saturation trend predicts exhaustion before next maintenance window

Bad alert examples:

- CPU > 80% without impact or duration
- every warning log line
- duplicate host/service alerts for the same failure

## Assets

Use:

- `skills/monitoring-observability/templates/slo-spec.md`
- `skills/monitoring-observability/templates/alert-rule.md`
- `skills/monitoring-observability/examples/dashboard-outline.md`

## Required references

- `references/diagnostic-order.md`
- `references/risk-levels.md`
- `references/observability-slo-sli.md`


## Output

Return:

- Observability gaps
- Checks executed
- SLI/SLO table
- Alert rules with severity and first action
- Dashboard layout
- Noise-reduction recommendations
- Runbook stubs or links
