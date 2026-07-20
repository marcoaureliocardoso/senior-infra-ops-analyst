---
name: Root Cause Analysis
description: Use after an incident or recurring infrastructure problem to produce a blameless RCA, timeline, evidence map, action table, contributing factors, corrective actions, and prevention plan based on evidence.
version: 0.5.0
last_updated: 2026-07-20
maintainer: Marco Aurelio Cardoso
triggers:
  - rca
  - postmortem
  - recurring incident
  - root cause
  - action items
---

# Root Cause Analysis

Produce a blameless, evidence-based RCA. Focus on system behavior, contributing factors, detection gaps, response gaps, and durable fixes.

<required>
1. Build a timeline with concrete timestamps, timezone, source, and confidence level for each event.
2. Distinguish trigger, root cause, contributing factors, detection gaps, response gaps, recovery actions, and user impact.
3. Trace backward from the symptom to the original trigger. For each event in the timeline, ask: what caused this? Keep asking until you reach an event that was not caused by another event in the system — that is the trigger or root cause. Never stop at the first visible failure.
4. Avoid blaming individuals; describe system conditions, process gaps, tooling gaps, missing checks, and decision constraints.
5. Link every conclusion to evidence in an evidence map, or mark it as assumption/unknown.
6. Use logs, monitoring output, command history, ticket records, change records, config diffs, and communications when available.
7. Produce an action table with owner, priority, effort, due date, verification method, and failure mode addressed.
8. Include prevention, detection, response, documentation, and validation actions; do not list only remediation.
9. Where the root cause could recur at a different layer, add defense-in-depth: validate at the boundary where the bad state entered AND at the layer where it caused failure.
</required>

## Backward tracing from symptom to trigger

Infrastructure failures often manifest far from their origin. A database outage may be caused by a storage failure. A storage failure may be caused by a network partition. A network partition may be caused by a switch firmware bug. The visible symptom (database down) is three layers away from the root cause (switch firmware).

Trace backward through each layer until you find the original trigger:

1. **Observe the symptom.** What is the user-visible or monitoring-visible failure?
2. **Find the immediate cause.** What component or condition directly produced the symptom?
3. **Trace one level up.** What caused that component to be in that state? A config change? An upstream dependency? A resource limit?
4. **Keep tracing.** For each cause found, ask again: what caused THIS? Continue until:
   - You reach an external event (human action, hardware failure, external dependency)
   - You reach a known system limit or design constraint
   - You cannot find further evidence (document as assumption)
5. **Identify the trigger vs root cause.** The trigger is the event that activated the failure. The root cause is the underlying condition that made the trigger possible. Both matter.

```
Example trace chain:
Symptom: API 500 errors @ 14:32 UTC
  ↑ Caused by: Connection pool exhausted (all 100 connections in use)
    ↑ Caused by: 30-second query latency on /orders endpoint
      ↑ Caused by: Missing index on orders.created_at after schema migration
        ↑ Caused by: Migration script dropped index and recreation was skipped
          ↑ TRIGGER: Schema migration v4.2.1 applied @ 14:28 UTC
          ↑ ROOT CAUSE: Migration review checklist has no index verification step
```

**Do not stop at the first cause you find.** The connection pool exhaustion is a true statement, but fixing only that (increasing pool size) treats the symptom. The missing index and the broken migration checklist are where durable fixes live.

## Artifact definitions

Use `references/rca-artifacts.md`.

Evidence map:

- Claim or finding
- Evidence source
- Timestamp/window
- Observed fact
- Confidence
- Gaps or assumptions

Action table:

- Action
- Failure mode addressed
- Type: prevent, detect, respond, recover, document
- Owner
- Priority
- Effort
- Due date
- Verification method

## Assets

Use:

- `skills/root-cause-analysis/templates/evidence-map.md`
- `skills/root-cause-analysis/templates/action-table.md`
- `skills/root-cause-analysis/templates/rca-draft.md`

## Required references

- `references/diagnostic-order.md`
- `references/risk-levels.md`
- `references/rca-artifacts.md`

## Output

Return a complete RCA draft with timeline, evidence map, action table, open questions, and follow-up validation plan.
