# RCA Draft

Use this template after filling `evidence-map.md` and `action-table.md`. Keep it blameless and evidence-based.

## Executive summary

One paragraph describing impact, trigger, root cause, mitigation, and prevention.

## Impact

Affected services, users, time window, severity, and operational consequence.

## Detection

How the issue was detected, alert quality, delay, and first responder.

## Timeline

| Time | Event | Source | Confidence | Relevance |
|---|---|---|---|---|
|  |  |  | high/medium/low |  |

## What happened

Narrative based only on known evidence. Mark uncertainty explicitly.

## Root cause

The deepest supported cause. Do not stop at symptoms such as “service restarted” or “disk full” without explaining why.

## Contributing factors

People, process, technology, monitoring, documentation, capacity, change, dependency, or vendor factors.

## Evidence map

Summarize the strongest evidence. Link to `evidence-map.md` for details.

## What went well

Response behaviors, monitoring, backups, rollback, communication, or teamwork that helped.

## What did not go well

Gaps in alerting, runbooks, access, logs, capacity, testing, ownership, or escalation.

## Corrective and preventive actions

Use `action-table.md`. Each action needs owner, priority, due date, validation method, and rollback/side-effect note.

## Follow-up validation

How to prove the issue is fixed and does not recur.

## Open questions

Questions that remain unresolved and the evidence needed to close them.

## Anti-patterns

- Blaming individuals.
- Listing actions without owners or due dates.
- Calling a symptom the root cause.
- Omitting evidence that contradicts the preferred hypothesis.
