# Example: RCA — Backup Repository Unreachable

## Incident summary

Nightly backups failed because backup clients could not reach the repository over TCP 9443 between 01:00 and 04:30.

## Evidence map

| Evidence | Source | Supports | Confidence |
|---|---|---|---|
| Backup job logs show connection timeout | Backup console | Network path interruption | High |
| Firewall change approved at 00:45 | Change record | Temporal correlation | Medium |
| Rule diff removed backup alias entry | Firewall config diff | Direct causal mechanism | High |
| Manual TCP check after rollback succeeds | Operator command | Recovery validation | High |

## Contributing factors

- Change plan did not include backup client validation.
- Alias diff was not reviewed before apply.
- Monitoring alerted on failed backup only after the full window elapsed.

## Root cause statement

A firewall alias update removed backup clients from the allow rule, blocking repository access. The change lacked a pre/post validation step for backup client connectivity.

## Action table

| Action | Owner | Type | Due | Validation |
|---|---|---|---|---|
| Add alias diff review to firewall change template | Infra | Prevention | 14 days | Template updated and used in next change. |
| Add synthetic TCP check from one backup client | Monitoring | Detection | 30 days | Alert fires in test. |
| Add backup validation to maintenance checklist | Backup owner | Process | 14 days | Checklist attached to change. |

## What not to claim

Do not blame the operator personally. The evidence points to a process and validation gap around alias changes.
