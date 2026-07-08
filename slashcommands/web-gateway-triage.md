# /web-gateway-triage

Purpose: diagnose web server or application gateway 4xx/5xx, TLS, routing, WAF, upstream, cache, or header issues.

Expected input:
- product, hostname/path, status code, upstream, time window, recent change.

Behavior:
- Use `skills/web-gateway-operations/SKILL.md`.
- Use `skills/web-gateway-operations/templates/web-gateway-incident.md`.
- Use `references/web-servers-application-gateways.md` plus PKI/LB references when TLS or upstream routing is involved.
- Do not reload/restart, change WAF rules, purge cache, or alter routing without approval.

Example:
`/web-gateway-triage nginx portal.example.edu/login returns intermittent 502 after 09:30`
