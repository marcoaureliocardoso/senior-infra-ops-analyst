# Example: SLO Burn-Rate Investigation — Portal Availability

## Scenario

The portal availability SLO alert fired for the 30-minute fast-burn window. Users report intermittent login failures.

## SLO context

- SLI: successful HTTP requests / total HTTP requests for `/login` and `/home`
- SLO: 99.5% monthly availability
- Alert: fast burn, 30-minute window
- Scope: public portal, production

## Evidence collected

| Evidence | Query/source | Observation | Interpretation |
|---|---|---|---|
| Error ratio | Prometheus SLI query | 5xx rose from 0.2% to 7% | SLO burn is real, not alert noise. |
| Latency | p95 HTTP latency | p95 rose above 4s | Saturation or dependency slowness likely. |
| Proxy status | Reverse proxy dashboard | One upstream has elevated 502 | Backend-specific issue. |
| Application logs | Bounded log query | DB pool timeout messages | Database dependency pressure. |

## Safe next checks

- Check database connection count and wait events.
- Compare affected upstream host against recent deployment/change records.
- Review reverse proxy upstream health for the same time window.

## Approval gate

Restarting application workers, changing pool size, disabling a backend, or rolling back deployment is `DISRUPTIVE_CHANGE` and requires approval.

## Stakeholder summary

The SLO alert reflects a real increase in login failures. Evidence currently points to backend dependency pressure rather than monitoring noise. Next update after database and upstream health checks.
