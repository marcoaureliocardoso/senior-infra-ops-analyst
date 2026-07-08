# Evidence Map

Use this to separate observed facts from hypotheses during RCA. Every important claim should map to evidence, a time window, and confidence.

## Confidence scale

| Confidence | Meaning |
|---|---|
| High | directly observed from authoritative source and time-aligned with the incident |
| Medium | observed indirectly or from a reliable but incomplete source |
| Low | plausible but not yet proven; requires follow-up evidence |

## Evidence map

| Claim/finding | Evidence source | Timestamp/window | Observed fact | Confidence | Gap/assumption |
|---|---|---|---|---|---|
| Example: database latency increased before API errors | metrics dashboard / DB slow query log | 2026-07-08 09:10-09:20 | p95 latency rose from 80 ms to 2.4 s before 5xx spike | high | need query fingerprint to identify workload |
| Example: deployment may have triggered cache misses | deployment log + cache metric | 2026-07-08 09:05 | deployment completed five minutes before cache hit ratio dropped | medium | correlation; need config diff |
|  |  |  |  | high/medium/low |  |

## Evidence quality checklist

- [ ] Source is named: log, metric, command, ticket, dashboard, config diff, alert, user report.
- [ ] Time zone and incident window are explicit.
- [ ] Evidence is scoped enough to avoid irrelevant noise.
- [ ] Sensitive fields are redacted before sharing.
- [ ] Each hypothesis is marked as proven, disproven, or still open.

## Useful source types

- Alert timeline and notification history.
- Metrics around golden signals: latency, traffic, errors, saturation.
- Logs/events around the incident window.
- Recent changes: deployments, firewall/DNS/IAM/routing/config/storage.
- Command output collected during the incident.
- User impact reports with timestamps and scope.

## Do not

- Treat “last change wins” as root cause without evidence.
- Mix remediation tasks into the evidence table.
- Include raw secrets, tokens, full packet payloads, or unnecessary personal data.
