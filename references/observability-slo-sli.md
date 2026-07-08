# Observability, SLI, SLO, and Alerting Reference

Use this when building or reviewing monitoring.

## SLI types

| SLI | Typical formula | Common data source | Notes |
|---|---|---|---|
| Availability | successful requests / valid requests | load balancer, service metrics, synthetic checks | Prefer user-visible success. |
| Latency | percentile below threshold / requests | APM, ingress, reverse proxy | Use p95/p99 when tail latency matters. |
| Error rate | failed requests / total requests | app metrics, proxy logs | Define expected vs unexpected errors. |
| Saturation | resource usage / limit | host, VM, container, DB, queue | Use prediction when exhaustion is gradual. |
| Freshness | up-to-date outputs / expected outputs | jobs, pipelines, backups | Useful for batch and reporting systems. |
| Durability | retained objects / expected objects | storage, backup, DB | Needs restore validation, not just backup success. |
| Job success | successful jobs / scheduled jobs | scheduler, backup, ETL | Include missed runs and late runs. |

## SLO definition checklist

- Service and user journey
- SLI formula
- Data source/query
- Inclusion/exclusion rules
- Objective target
- Measurement window
- Error budget policy
- Alerting approach
- Dashboard location
- Runbook owner
- Known limitations

## Burn-rate guidance

Use multiple windows when possible:

- Fast burn: severe current issue, page immediately.
- Slow burn: budget being consumed, create ticket or escalate during business hours.
- Exhaustion prediction: capacity or reliability trend needs planning.

## Alert review questions

1. Does this alert represent user impact or imminent risk?
2. Can the operator act on it immediately?
3. Is there a runbook with first commands?
4. Is the threshold based on baseline/SLO or a generic number?
5. Does it duplicate another alert?
6. Does it include service, target, time window, owner, severity, and escalation?

## Interpretation patterns

- SLI bad, dependencies healthy: likely service/application/local capacity issue.
- Dependency bad before service bad: dependency likely contributed.
- Host metrics bad but SLI good: dashboard issue or early-warning ticket, not page.
- Logs noisy but SLI good: investigate trend, do not page unless risk is imminent.
- Backup success without restore test: recoverability confidence is incomplete.

## Related references

- `references/monitoring-stack-operations.md`
- `references/incident-severity.md`
- `references/diagnostic-order.md`
