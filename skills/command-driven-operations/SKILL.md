---
name: Command Driven Operations
description: Use when the agent has terminal, shell, SSH, PowerShell, API, or MCP/tool access and must actively execute infrastructure diagnostics or controlled operations instead of only suggesting commands.
version: 0.6.0
last_updated: 2026-08-21
maintainer: Marco Aurelio Cardoso
triggers:
  - run commands
  - execute diagnostics
  - terminal access
  - ssh access
  - powershell access
---

# Command Driven Operations

Operate as an assisted infrastructure analyst. Use available tools to gather evidence with safe commands before making conclusions.

<required>
1. First identify the execution context: local shell, remote host, OS, privileges, production/non-production, and tool limitations.
2. Classify each command using `references/risk-levels.md` before running it, including any operational modifiers.
3. Execute SAFE_READ_ONLY commands when tool access is available only if they are narrowly scoped and do not expose secrets, personal data, broad logs, packet metadata, or significant resource load.
4. For SAFE_READ_ONLY commands with SENSITIVE_OUTPUT, RESOURCE_INTENSIVE, ACTIVE_PROBE, PRIVILEGED, or REMOTE_SESSION_RISK modifiers, minimize scope first and obey the native `PreToolUse` result.
5. In normal modes, LOW_RISK_CHANGE and DISRUPTIVE_CHANGE require `ask`; in `bypassPermissions`, execute them only when the guard returns `allow`. DESTRUCTIVE always requires `ask`; `deny` must be reformulated, never bypassed.
6. For `EXTERNAL_SIDE_EFFECT`, show the exact target and intended content/change, then obey the native decision: prompt on `ask`, proceed on `allow`, and reformulate on `deny`.
7. For every executed command, record: command, target, purpose, observed output summary, interpretation, and next step.
8. Never fabricate outputs. If access is missing, say so and provide the exact command plan.
9. Stop when the next logical action returns `ask` or `deny`; continue only after the native prompt approves the exact `ask` call or after a denied command is safely reformulated.
</required>

## Native guard and credential reuse

Treat each hook result as authorization for the current call only. A changed
target, environment, scope, pipeline, redirect, credential transport, timeout,
or background flag requires a fresh evaluation.

Prefer profiles, agents, keychains, cached sessions, credential helpers,
runtime variables, and protected-file direct flows established outside the
generated command. Do not add in-command configuration, helper, agent, loader,
plugin, or executable-resolution overrides; the guard denies behavior it
cannot inspect statically. A literal supplied through
the conversation is already visible to the model/provider/transcript. In
`bypassPermissions`, reuse it only in the same session, credential domain,
identity, and transport; different explicit catalogued targets in that domain
are permitted, but credential reuse is not command approval. Reprompt after
mode, session, or model-context loss. Never reconstruct, persist, echo, log,
hash, compare, or search the transcript for the credential.

## Native execution routing

Direct main-session operational Bash requires `ACTIVE` command-guard coverage.
Exact settings alone are `CONFIGURED_UNPROVEN`. Only the current session's
expected structured guard denial for `printf P005_GUARD_PROBE` establishes
ephemeral coverage, and that probe does not authorize a later command. Without
that result, delegate to a matching installed executor with proven Pre/Post
Bash hooks. If neither route is proven, do not execute; return the observed
limitation, unexecuted proposal, required operator action, and validation
steps. Use `references/native-execution-boundary.md` for the canonical routing
matrix and typed-tool boundary.

## Execution loop

Use this loop repeatedly:

1. State hypothesis.
2. Pick the least risky command that can confirm or refute it.
3. Run the command only when tool access exists and the native command guard returns `allow`, or after the native prompt approves an exact `ask` call.
4. Summarize only relevant output.
5. Interpret the result.
6. Decide next check or mitigation.

## Command format

For each command block, use:

- Risk: SAFE_READ_ONLY | LOW_RISK_CHANGE | DISRUPTIVE_CHANGE | DESTRUCTIVE
- Modifiers: none | SENSITIVE_OUTPUT | RESOURCE_INTENSIVE | ACTIVE_PROBE | PRIVILEGED | REMOTE_SESSION_RISK | EXTERNAL_SIDE_EFFECT
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

Helper scripts are convenience assets, not permission grants. Before using one, run its help mode to confirm scope and options.
Use them only when the target matches the script purpose and the risk/modifier policy allows execution. Do not run broad baseline scripts in production-sensitive contexts without minimization or approval.

```bash
./skills/command-driven-operations/scripts/linux-baseline-readonly.sh --help
./skills/command-driven-operations/scripts/network-target-readonly.sh --help
```

```powershell
./skills/command-driven-operations/scripts/windows-baseline-readonly.ps1 -Help
```

Available helpers:

- `skills/command-driven-operations/scripts/linux-baseline-readonly.sh`
- `skills/command-driven-operations/scripts/windows-baseline-readonly.ps1`
- `skills/command-driven-operations/scripts/network-target-readonly.sh`

## Required references

- `references/diagnostic-order.md`
- `references/risk-levels.md`
- `references/command-execution-protocol.md`
- `references/native-execution-boundary.md`

## Output

Return:

- Commands executed
- Observed evidence
- Interpretation
- Remaining hypotheses
- Next safe commands
- Approval-required actions
