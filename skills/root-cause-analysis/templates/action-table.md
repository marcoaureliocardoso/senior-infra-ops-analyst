# Action Table

Use this to convert RCA findings into corrective and preventive actions. Each action must address a specific failure mode and include a verification method.

## Action types

| Type | Purpose | Example |
|---|---|---|
| prevent | reduce chance of recurrence | add pre-deploy validation for invalid config |
| detect | improve time to detection | add SLO burn-rate alert |
| respond | improve operator response | create runbook for known failure mode |
| recover | improve restoration/rollback | test backup restore or automate rollback |
| document | capture knowledge/process | update topology and escalation path |

## Table

| Action | Failure mode addressed | Type | Owner | Priority | Effort | Due date | Verification method |
|---|---|---|---|---|---|---|---|
| Example: add validation check that rejects empty upstream list before proxy reload | bad config can remove all backends | prevent |  | P1 | medium |  | failed config is blocked in staging and production pre-check |
| Example: add alert for elevated TCP refused rate on service port | service down detected only by users | detect |  | P1 | low |  | alert fires in synthetic test and links to runbook |
|  |  | prevent/detect/respond/recover/document |  | P0/P1/P2/P3 | low/medium/high |  |  |

## Priority guide

- P0: required to stop active recurrence or data-loss/security risk.
- P1: closes a major incident contributor.
- P2: improves resilience or response but not urgent.
- P3: documentation or backlog hygiene.

## Verification examples

- Automated test added and passing.
- Synthetic check or alert fires under controlled test.
- Runbook executed by another operator successfully.
- Restore, failover, rollback, or capacity action tested and documented.

## Completion criteria

- [ ] Owner accepted the action.
- [ ] Due date is realistic.
- [ ] Verification method is objective.
- [ ] Action addresses a cause or contributing factor, not just a symptom.
- [ ] Any risky change has rollback and approval path.
