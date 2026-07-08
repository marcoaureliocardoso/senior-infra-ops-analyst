---
name: Web Servers and Application Gateway Operations
description: Use when diagnosing IIS, Apache, NGINX, application gateways, virtual hosts, status codes, access/error logs, static content, upstream integration, or gateway policies.
version: 0.4.1
last_updated: 2026-07-08
maintainer: Marco Aurelio Cardoso
triggers:
  - web-gateway-operations
  - web servers and application gateway operations
---

# Web Servers and Application Gateway Operations

Use this skill when the operational domain materially changes the diagnostic order, evidence type, approval gate, or interpretation. The shared command-driven posture still applies, but the domain-specific reference and template are mandatory context.

<required>
1. Identify web server/gateway, site/vhost, hostname/path, upstream application, auth/WAF/policy layer, TLS termination, and affected clients.
2. Use `references/web-servers-application-gateways.md` for config tests, service status, bounded logs, virtual host/listener checks, and status-code interpretation.
3. Cross-reference load balancer and PKI references for TLS/routing issues, and monitoring stack references for access/error-rate evidence.
4. Treat URLs with tokens, cookies, headers, IPs, usernames, logs, and auth policy details as `SENSITIVE_OUTPUT`.
5. Run read-only checks first: config syntax, active listeners, recent error logs, access sample, upstream reachability, and a scoped HTTP probe when authorized.
6. Interpret HTTP failures by layer: DNS, TLS, listener, vhost, rewrite, auth, WAF, upstream, application, filesystem permissions, or saturation.
7. Require approval before reload, restart, config edit, WAF policy change, cache purge, cert deployment, or routing change.
8. Classify HTTP probes as `ACTIVE_PROBE` and broad logs as sensitive/resource-intensive.
9. Produce `skills/web-gateway-operations/templates/web-gateway-incident.md` with request path, status pattern, logs summary, upstream state, and approval-gated actions.
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

- `references/web-servers-application-gateways.md`
- `references/risk-levels.md`
- `references/command-execution-protocol.md`
- `references/diagnostic-order.md`
- `references/external-sources.md`
