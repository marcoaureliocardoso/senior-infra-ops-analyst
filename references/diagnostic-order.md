# Canonical Diagnostic Order

Use this as the shared diagnostic spine for troubleshooting, incident triage, and change pre-checks. Domain-specific skills may add overlays, but they must not replace this order without saying why.

## Standard order

1. Define symptom, scope, user impact, and time window.
2. Identify recent changes.
3. Run safe local/client checks.
4. Validate DNS and name resolution.
5. Validate network path and ports.
6. Validate firewall, routing, NAT, VPN, VLAN, and security groups.
7. Validate host health.
8. Validate service state and dependencies.
9. Read logs/events around the time window with minimization and redaction.
10. Validate authentication and authorization.
11. Validate storage, backup, and capacity.
12. Evaluate external dependencies.
13. Recommend or execute mitigation according to risk classification and approval gates.
14. Preserve evidence and document next actions.

## Incident overlay

During active incidents, first establish severity, blast radius, communications, and stabilization options. Then use the standard order for evidence collection. The incident overlay is a coordination layer, not a conflicting diagnostic sequence.

## Troubleshooting overlay

For a single-user or client-specific symptom, include client-side checks in steps 1 and 3. For third-party or provider symptoms, include external dependencies in step 12.

## Related references

- `references/command-execution-protocol.md`
- `references/risk-levels.md`
- `references/incident-severity.md`
- `references/interpretation-patterns.md`
