---
name: Infrastructure Troubleshooting
skill_id: infrastructure-troubleshooting
description: Use when diagnosing Linux, Windows, network, DNS, DHCP, firewall, VPN, virtualization, container, storage, authentication, or service availability problems using active command-driven evidence collection.
---

# Infrastructure Troubleshooting

Diagnose infrastructure issues methodically. Start from observed symptoms and command output, not guesses.

<required>
1. Build a problem statement with symptom, scope, affected components, expected behavior, actual behavior, and time window.
2. Choose the likely fault layer: client, DNS, network, firewall, host, service, storage, authentication, application, or external dependency.
3. Execute safe read-only checks when tool access exists.
4. For every command, explain what it verifies and what result confirms or refutes the hypothesis.
5. Do not recommend broad restarts, firewall flushes, permission changes, or config edits before evidence supports them.
6. Stop and request approval before any command that changes state or may disrupt production.
</required>

## Diagnostic order

1. Scope and time
2. Recent changes
3. Client-side symptoms
4. Name resolution
5. Network path
6. Firewall and routing
7. Host health
8. Service health
9. Logs and events
10. Authentication and permissions
11. Storage and capacity
12. External dependencies

## Required references

Use the command matrices in:

- `references/command-execution-protocol.md`
- `references/linux-diagnostics.md`
- `references/windows-server-diagnostics.md`
- `references/network-diagnostics.md`
- `references/dns-dhcp.md`
- `references/pfsense-operations.md`
- `references/active-directory.md`
- `references/storage-backup.md`
- `references/interpretation-patterns.md`

## Output

Return:

- Problem statement
- Commands executed or exact command plan
- Evidence observed
- Interpretation guide
- Ranked fault domains
- Safe next action
- Approval-required actions
- Escalation criteria
