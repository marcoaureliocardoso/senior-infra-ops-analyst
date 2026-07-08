# /incident-triage

Use the Incident Response and Command Driven Operations skills.

## Purpose

Triage an active incident, establish impact, gather evidence, and propose safe mitigation.

## Expected input

- Affected service and users
- Start time/timezone
- Current symptoms
- Recent changes
- Known alerts/logs/tickets
- Available access/tools

## Behavior

1. Assign provisional severity from user impact and scope.
2. Build a live incident summary.
3. Execute only safe, scoped diagnostics.
4. Identify likely layer: DNS, network, firewall, host, service, auth, storage, cloud, dependency.
5. Provide stakeholder update text.
6. Stop before disruptive mitigation unless approved.

## Example

`/incident-triage VPN users cannot authenticate after certificate renewal; started 08:30 America/Sao_Paulo`

## Output

Severity, impact, timeline, commands executed, observed evidence, hypotheses, mitigation options, rollback notes, next update.
