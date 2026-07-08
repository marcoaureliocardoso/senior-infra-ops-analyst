# Capacity and Risk Taxonomy

Use this to classify infrastructure risks consistently.

## Scoring dimensions

| Dimension | Low | Medium | High |
|---|---|---|---|
| Impact | local inconvenience | service degradation | outage, data loss, security exposure |
| Likelihood | unlikely or controlled | plausible within planning horizon | already observed or imminent |
| Urgency | can wait >90 days | 30-90 days | now to 30 days |
| Reversibility | easy rollback | partial rollback | hard or irreversible |
| Blast radius | one host/user | one service/site | multiple services/sites |
| Evidence strength | assumption | inferred | observed |
| Time-to-failure | unknown/long | trending | predicted or active |

## Categories and examples

### Availability

Risks: single firewall, single hypervisor, no spare link, no HA for critical service.
Evidence: topology, uptime, failover config, dependency map.

### Performance and saturation

Risks: CPU steal, memory pressure, disk latency, queue buildup, link saturation.
Evidence: metrics, `iostat`, `free`, hypervisor counters, cloud metrics.

### Storage growth

Risks: filesystem near full, snapshots consuming datastore, backup repository growth.
Evidence: `df`, datastore usage, backup reports, growth trend.

### Recoverability

Risks: untested restore, missing offsite copy, backups failing silently, RPO/RTO undefined.
Evidence: backup jobs, restore tests, retention policy, immutable/offline copy.

### Security exposure

Risks: broad firewall rules, public management ports, stale admin accounts, weak segmentation.
Evidence: firewall rules, IAM/AD groups, VPN config, audit logs.

### Lifecycle

Risks: EOL OS, unsupported hypervisor, firmware age, expiring warranty/certificates.
Evidence: versions, vendor lifecycle, cert expiry, hardware inventory.

### Maintainability and toil

Risks: manual repetitive procedures, no runbooks, undocumented scripts, single-person knowledge.
Evidence: tickets, procedures, handover docs, automation inventory.

### Cloud-specific

Risks: quota exhaustion, single region/zone, unmanaged public IPs, permissive IAM, untagged resources, missing backup policy, cost anomaly.
Evidence: cloud inventory, monitoring, activity logs, IAM policies, backup vaults, billing/cost reports.

## Recommendation format

- Risk statement
- Evidence
- Impact
- Likelihood
- Urgency
- Recommended action
- Effort
- Reversibility
- Validation
- Owner/decision needed
