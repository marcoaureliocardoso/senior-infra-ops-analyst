# /ops-diagnose

Use the Command Driven Operations and Infrastructure Troubleshooting skills.

## Purpose

Actively diagnose an infrastructure symptom with safe read-only commands before giving conclusions.

## Expected input

- Target: host, service, IP, URL, VM, cluster, firewall, or cloud resource
- Symptom: unavailable, slow, error, login failure, backup failure, high usage, etc.
- Time window and production impact, if known
- Tool context: local shell, SSH, PowerShell, cloud CLI, API, MCP, or none

## Behavior

1. Confirm scope and risk.
2. Choose the relevant reference.
3. Execute narrowly scoped SAFE_READ_ONLY checks when access exists.
4. Summarize observed output, not raw dumps.
5. Interpret and choose next check.
6. Stop before any state-changing action.

## Example

`/ops-diagnose service intranet is unavailable from clients since 09:10; target pfsense + web01`

## Output

Situation, commands executed, evidence, interpretation, remaining hypotheses, next safe commands, approval-required actions.
