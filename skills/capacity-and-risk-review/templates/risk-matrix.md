# Risk Matrix

Use this to turn operational findings into prioritized, defensible actions. A good entry contains evidence, not vibes.

## Scoring guide

| Field | Low | Medium | High |
|---|---|---|---|
| Impact | inconvenience or localized degradation | service degradation, partial outage, compliance concern | major outage, data loss, security exposure, failed recovery |
| Likelihood | rare or requires multiple conditions | plausible under current operating patterns | already observed, trending, or one failure away |
| Urgency | can wait >90 days | should be addressed within 30-90 days | immediate or next change window |
| Reversibility | easy rollback or read-only | rollback possible with some risk | hard/slow/no rollback |
| Blast radius | one host/user/group | one service/site/subnet | many services/sites/users or shared dependency |

## Categories

- availability
- capacity
- performance
- backup-restore
- security
- change-risk
- observability
- dependency
- lifecycle/supportability
- documentation/process

## Matrix

| Risk | Category | Evidence | Impact | Likelihood | Urgency | Reversibility | Blast radius | Priority | Recommended action | Validation |
|---|---|---|---|---|---|---|---|---|---|---|
| Example: no recent restore test for critical VM backups | backup-restore | backup jobs are green, but no restore evidence in last 90 days | high | medium | 30 days | partial | service/site | P1 | run isolated restore test and document RTO/RPO result | restored VM/files verified by owner |
| Example: disk volume >90% and growing 4%/week | capacity | monitoring trend and `df`/logical disk output | high | high | now | easy/partial | host/service | P0 | free space short-term, then resize or lifecycle old data | volume <80% and trend stable |
|  |  |  | low/medium/high | low/medium/high | now/30/60/90 | easy/partial/hard |  | P0/P1/P2/P3 |  |  |

## Priority rules

- P0: active or imminent outage/security/data-loss risk. Act now with incident/change discipline.
- P1: high impact and plausible within 30 days. Schedule owner and date.
- P2: meaningful risk but not urgent. Track in improvement backlog.
- P3: hygiene/documentation item. Bundle with related work.

## Anti-patterns

- “Needs improvement” without a measurable failure mode.
- “High risk” without evidence, blast radius, or validation.
- Recommending disruptive changes without rollback and approval path.
