# Example: Safe Automation Review — Bulk Firewall Alias Update

## Scenario

A script will update a pfSense alias used by backup repository firewall rules. The operator wants to add 12 new backup clients without disrupting existing backup traffic.

## Scope

- Target: pfSense alias `backup_clients`
- Environment: production firewall
- Change type: alias membership update
- Tooling: exported `config.xml`, pfSense API or GUI change record
- Approval: required before state change

## Review findings

| Area | Evidence | Interpretation | Action |
|---|---|---|---|
| Scope | Script reads hosts from `clients.txt` | Good, but input file needs allowlist validation | Add hostname/IP validation before update. |
| Dry-run | No dry-run flag | Operator cannot preview alias diff | Add `--dry-run` output showing add/remove/no-op. |
| Rollback | Config backup exists but not named in script | Rollback depends on manual recall | Save pre-change alias list to timestamped file. |
| Logging | Script only prints success | Audit trail is weak | Log timestamp, operator, target alias, diff, exit code. |
| Failure mode | Loop continues after API error | Partial update risk | Fail fast or batch with explicit partial-failure report. |

## Safer implementation notes

- Default mode must be preview-only.
- Require `--apply` plus exact alias name for actual change.
- Reject empty input files, duplicate entries, invalid IPs, and unexpected removals.
- Capture `before` and `after` alias membership.

## Approval gate

Do not run apply mode until the change record contains target alias, diff, maintenance window, validation command, rollback file, and approver.

## Validation after approval

| Check | Command/evidence | Expected result |
|---|---|---|
| Alias contents | pfSense alias export/API read | New clients present; existing clients retained. |
| Rule association | Firewall rule review | Alias still used only by backup rule. |
| Connectivity | One approved client TCP check to repository | Backup port reachable. |

## Rollback

Restore previous alias membership from the timestamped pre-change export and validate backup connectivity from an existing client.
