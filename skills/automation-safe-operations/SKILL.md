---
name: Automation Safe Operations
skill_id: automation-safe-operations
description: Use when writing, reviewing, or running automation scripts for infrastructure operations, including shell, PowerShell, Ansible, Python, scheduled jobs, mass changes, shutdown/startup routines, or maintenance automation.
version: 0.4.4
last_updated: 2026-07-08
maintainer: Marco Aurelio Cardoso
triggers:
  - script review
  - automation plan
  - mass change
  - scheduled job
  - safe execution
---

# Automation Safe Operations

Design automation as if a typo could affect production. Prioritize idempotence, dry-runs, logging, explicit scope, rollback, and operator confirmation.

<required>
1. Require explicit target scope: hosts, services, directories, users, firewall rules, VMs, or objects affected.
2. Include dry-run or preview mode whenever feasible.
3. Include logging of actions, errors, timestamps, target identity, and exit codes.
4. Execute lint/static checks and safe dry-runs when tool access exists.
5. Require explicit approval before running scripts that change state in any environment, including production, staging, test, lab, and developer systems.
6. Never suggest mass destructive operations without confirmation gates, safeguards, backups or rollback evidence, and operator-visible blast-radius notes.
</required>

## Safety checklist

- Explicit allowlist of targets
- No implicit wildcards for destructive actions
- Dry-run mode
- Confirmation prompt for destructive steps
- Error handling and non-zero exit behavior
- Idempotent design
- Backups or snapshots when state is modified
- Rate limiting or batching for many hosts
- Logs stored somewhere predictable
- Post-run summary

## Review focus

Check quoting, variable expansion, privilege requirements, secrets exposure, race conditions, partial failure behavior, rollback capability, OS/shell compatibility, and auditability.

## Required references

- `references/diagnostic-order.md`
- `references/risk-levels.md`
- `references/command-execution-protocol.md`


## Output

Return:

- Risk review
- Commands/checks executed
- Safer implementation notes
- Improved script or pseudocode
- Dry-run plan
- Rollback and validation
