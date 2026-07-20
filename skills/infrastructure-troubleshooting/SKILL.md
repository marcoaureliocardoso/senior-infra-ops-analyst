---
name: Infrastructure Troubleshooting
description: Use when diagnosing Linux, Windows, network, DNS, DHCP, firewall, VPN, virtualization, container, storage, authentication, or service availability problems using active command-driven evidence collection.
version: 0.5.0
last_updated: 2026-07-20
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
5. Form ONE hypothesis at a time. State it explicitly: "I think X is the cause because Y." Test with the smallest possible evidence-gathering command. Do not test multiple hypotheses simultaneously.
6. When evidence refutes the hypothesis, form a new one. Do not stack unverified assumptions.
7. Do not recommend broad restarts, firewall flushes, permission changes, or config edits before evidence supports them.
8. Stop and request approval before any command that changes state or may disrupt production.
9. IF 3+ hypotheses are refuted: STOP. Re-examine fundamentals — are you diagnosing the right layer? Is the problem statement correct? Question the fault domain, not just the hypothesis.
</required>

## Multi-layer evidence gathering

When the problem spans multiple components (client → DNS → load balancer → app server → database), gather evidence at EACH boundary BEFORE forming a hypothesis:

```
For EACH component boundary:
  - Verify the component is reachable
  - Check its own health/error indicators
  - Confirm it sees the downstream/upstream correctly
  - Log what enters and exits the boundary
```

This reveals WHERE the failure occurs before you investigate WHY. Do not skip layers — the symptom layer is rarely the root cause.

## Hypothesis discipline

**Before every diagnostic command**, state the hypothesis it tests. After the result, confirm or refute explicitly:

```
Hypothesis: DNS resolution is failing for api.internal
Test: dig api.internal @10.0.1.53
Result: NXDOMAIN
→ Hypothesis CONFIRMED. DNS server does not have the record.
```

```
Hypothesis: Firewall is dropping traffic to port 5432
Test: nc -zv db-primary 5432 from app host
Result: Connection refused (not timeout)
→ Hypothesis REFUTED. Port is reachable, service is rejecting connections.
```

Never test multiple hypotheses in one command. One command, one hypothesis, one variable.

## When 3+ hypotheses fail

Three refuted hypotheses signal the diagnosis is attacking the wrong layer. STOP and re-examine:

- Is the problem statement accurate? Re-check symptoms with fresh evidence.
- Are you diagnosing the right fault domain? If network checks all pass, move up the stack.
- Is this a compound failure? Two independent faults can masquerade as one.
- Is the environment different from what you assume? Verify topology, config, and state.

Do not form a 4th hypothesis until you've re-validated fundamentals. Escalate or add instrumentation instead of guessing deeper.

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
