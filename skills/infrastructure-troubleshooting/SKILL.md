---
name: Infrastructure Troubleshooting
skill_id: infrastructure-troubleshooting
description: Use when diagnosing Linux, Windows, network, DNS, DHCP, firewall, VPN, virtualization, container, storage, authentication, or service availability problems using active command-driven evidence collection.
version: 0.4.1
last_updated: 2026-07-08
maintainer: Marco Aurelio Cardoso
triggers:
  - troubleshoot
  - connectivity issue
  - service unavailable
  - dns issue
  - firewall issue
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

Use `references/diagnostic-order.md` as the canonical order. Client-side symptoms are handled in steps 1 and 3; external dependencies are handled in step 12.

## Required references

- `references/risk-levels.md`
- `references/diagnostic-order.md`
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
