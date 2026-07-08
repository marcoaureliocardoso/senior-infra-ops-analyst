# Incident Severity Model

Use this for incident response. Severity describes current or potential user/service impact. It is separate from risk priority in `capacity-risk-taxonomy.md`.

| Severity | Meaning | Typical response |
|---|---|---|
| SEV1 | Major outage, security-impacting incident, data-loss risk, or critical service unavailable for many users | Immediate coordination, frequent updates, mitigation options, approval packet for disruptive actions. |
| SEV2 | Significant degradation or partial outage affecting a service, site, or important user group | Prompt triage, bounded diagnostics, mitigation plan, stakeholder updates. |
| SEV3 | Limited impact, workaround available, or non-critical degradation | Normal-priority triage, preserve evidence, plan corrective action. |
| SEV4 | Informational, warning, near miss, or low-risk anomaly | Monitor, document, tune alerting, or open backlog item. |

## Mitigation versus approval

Mitigation urgency never cancels safety gates. If the correct mitigation is disruptive, such as failover, service restart, firewall change, or rollback, present an approval packet:

- exact action
- why mitigation is justified
- expected effect
- blast radius
- rollback/backout path
- validation command
- risk of waiting

Emergency policy may authorize faster approval, but the agent must not silently execute disruptive actions.

## Related references

- `references/diagnostic-order.md`
- `references/risk-levels.md`
- `references/itsm-cmdb-workflows.md`
- `references/vendor-escalation.md`
