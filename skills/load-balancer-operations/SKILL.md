---
name: Load Balancer and Reverse Proxy Operations
description: Use when diagnosing NGINX, HAProxy, Apache reverse proxy, cloud load balancers, backend pool health, routing, TLS termination, or gateway errors.
version: 0.4.3
last_updated: 2026-07-08
maintainer: Marco Aurelio Cardoso
triggers:
  - load-balancer-operations
  - load balancer and reverse proxy operations
---

# Load Balancer and Reverse Proxy Operations

Use this skill when the operational domain materially changes the diagnostic order, evidence type, approval gate, or interpretation. The shared command-driven posture still applies, but the domain-specific reference and template are mandatory context.

<required>
1. Identify listener/VIP, hostname, route rule, backend pool, health check, TLS termination point, recent config or certificate changes, and impacted clients.
2. Use `references/load-balancers-reverse-proxies.md` to inspect effective config, syntax validity, health state, logs, and backend response behavior.
3. Cross-reference `references/pki-certificate-lifecycle.md` for TLS/SNI/certificate issues and `references/web-servers-application-gateways.md` for upstream web errors.
4. Run bounded read-only checks first: config test, status, health endpoint state, selected log window, backend mapping, and one scoped external probe when authorized.
5. Treat hostnames, internal IPs, cookies, headers, routes, cert details, and backend names as `SENSITIVE_OUTPUT`.
6. Interpret status codes and health failures by layer: DNS, TLS, listener, routing, WAF/gateway, upstream connection, backend saturation, or application error.
7. Do not reload, drain, disable, weight-shift, rotate certificates, change DNS, or modify routes without explicit approval and rollback plan.
8. Classify probes as `ACTIVE_PROBE` and broad config/log reads as sensitive or resource-intensive when applicable.
9. Produce `skills/load-balancer-operations/templates/load-balancer-check.md` with listener, backend health, TLS state, config validation, and proposed safe next action.
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

- `references/load-balancers-reverse-proxies.md`
- `references/risk-levels.md`
- `references/command-execution-protocol.md`
- `references/diagnostic-order.md`
- `references/external-sources.md`
