---
name: Web Server and Application Gateway Operations
description: Use when diagnosing Apache, NGINX, IIS, Tomcat/Jetty gateway, HTTP error, redirect, header, TLS binding, or application gateway routing issues.
version: 0.4.0
last_updated: 2026-07-08
maintainer: Marco Aurelio Cardoso
triggers:
  - web-gateway-operations
  - web server and application gateway operations
---

# Web Server and Application Gateway Operations

Use this skill to operate the domain through evidence-first, command-driven diagnostics. Do not merely suggest commands when a safe tool is available; execute approved `SAFE_READ_ONLY` checks, interpret results, and stop before state-changing actions.

<required>
1. Confirm scope, affected service, environment, business impact, and whether this is incident, change, audit, or planned maintenance work.
2. Apply `references/diagnostic-order.md` unless a domain-specific order is safer; state any deviation.
3. Use `references/risk-levels.md` and `references/command-execution-protocol.md` before commands.
4. Consult `references/web-servers-application-gateways.md` for domain command order, safety rules, and interpretation.
5. Start with bounded read-only checks and capture concise evidence; redact sensitive output.
6. Interpret each result before choosing the next command.
7. Classify proposed remediation as `STATE_CHANGING`, `DISRUPTIVE`, or `DESTRUCTIVE` when applicable.
8. Require explicit approval before changes, restarts, failovers, purges, access changes, config writes, or vendor data sharing.
9. Use the template `skills/web-gateway-operations/templates/web-gateway-incident.md` when producing the final artifact.
</required>

## Output

Return:
- Situation and scope
- Commands executed or explicitly not executed
- Observations and interpretation
- Risk classification
- Recommended next action
- Approval gate, if needed
- Evidence/template artifact

## References

- `references/web-servers-application-gateways.md`
- `references/risk-levels.md`
- `references/command-execution-protocol.md`
- `references/diagnostic-order.md`
- `references/external-sources.md`
