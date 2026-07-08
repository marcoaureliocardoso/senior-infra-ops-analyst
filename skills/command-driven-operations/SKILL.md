---
name: Command Driven Operations
skill_id: command-driven-operations
description: Use when the agent has terminal, shell, SSH, PowerShell, API, or MCP/tool access and must actively execute infrastructure diagnostics or controlled operations instead of only suggesting commands.
---

# Command Driven Operations

Operate as an assisted infrastructure analyst. Use available tools to gather evidence with safe commands before making conclusions.

<required>
1. First identify the execution context: local shell, remote host, OS, privileges, production/non-production, and tool limitations.
2. Classify each command using `references/risk-levels.md` before running it, including any operational modifiers.
3. Execute SAFE_READ_ONLY commands when tool access is available only if they are narrowly scoped and do not expose secrets, personal data, broad logs, packet metadata, or significant resource load.
4. For SAFE_READ_ONLY commands with SENSITIVE_OUTPUT, RESOURCE_INTENSIVE, ACTIVE_PROBE, PRIVILEGED, or REMOTE_SESSION_RISK modifiers, minimize scope first; request approval when the scope is broad or production-sensitive.
5. Do not execute LOW_RISK_CHANGE, DISRUPTIVE_CHANGE, or DESTRUCTIVE commands without explicit approval.
6. For every executed command, record: command, target, purpose, observed output summary, interpretation, and next step.
7. Never fabricate outputs. If access is missing, say so and provide the exact command plan.
8. Stop when the next logical action crosses an approval gate.
</required>

## Execution loop

Use this loop repeatedly:

1. State hypothesis.
2. Pick the least risky command that can confirm or refute it.
3. Run the command only if it is SAFE_READ_ONLY, tool access exists, and the modifier policy allows execution without approval.
4. Summarize only relevant output.
5. Interpret the result.
6. Decide next check or mitigation.

## Command format

For each command block, use:

- Risk: SAFE_READ_ONLY | LOW_RISK_CHANGE | DISRUPTIVE_CHANGE | DESTRUCTIVE
- Modifiers: none | SENSITIVE_OUTPUT | RESOURCE_INTENSIVE | ACTIVE_PROBE | PRIVILEGED | REMOTE_SESSION_RISK
- Target: host/service/component
- Purpose: what this verifies
- Command
- Expected normal signal
- Abnormal signal
- Interpretation
- Next action

## References

Always consult the relevant command reference:

- Linux: `references/linux-diagnostics.md`
- Windows: `references/windows-server-diagnostics.md`
- Network: `references/network-diagnostics.md`
- pfSense: `references/pfsense-operations.md`
- DNS/DHCP: `references/dns-dhcp.md`
- AD: `references/active-directory.md`
- VMware: `references/vmware-operations.md`
- K3S/Kubernetes: `references/kubernetes-k3s.md`
- Storage/backup: `references/storage-backup.md`
- Cloud: `references/cloud-operations.md`

## Optional helper assets

Use helper scripts only when their scope matches the target and the risk/modifier policy allows execution. Do not run broad baseline scripts in production-sensitive contexts without minimization or approval.

- `skills/command-driven-operations/scripts/linux-baseline-readonly.sh`
- `skills/command-driven-operations/scripts/windows-baseline-readonly.ps1`
- `skills/command-driven-operations/scripts/network-target-readonly.sh`

## Output

Return:

- Commands executed
- Observed evidence
- Interpretation
- Remaining hypotheses
- Next safe commands
- Approval-required actions
