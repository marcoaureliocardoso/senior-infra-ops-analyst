---
description: "Diagnose load balancer or reverse proxy backend health, routing, TLS, sticky sessions, PROXY protocol, and upstream errors."
allowed-tools: Task(subagent_type:network-edge-operator)
---
# /lb-triage

Purpose: diagnose load balancer or reverse proxy backend health, routing, TLS, sticky sessions, PROXY protocol, or upstream errors.

Expected input:
- product, VIP/hostname, backend pool, symptom, time window, recent change.

Behavior:
- Use `skills/load-balancer-operations/SKILL.md`.
- Use `skills/load-balancer-operations/templates/load-balancer-check.md`.
- Cross-check `references/load-balancers-reverse-proxies.md`, `references/pki-certificate-lifecycle.md`, and `references/web-servers-application-gateways.md`.
- Do not disable backends, reload config, change routing, or alter certificates without approval.

Example:
`/lb-triage HAProxy VIP portal.example.edu returns 503 for some users after deploy`
