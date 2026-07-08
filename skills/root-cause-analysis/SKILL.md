---
name: Root Cause Analysis
skill_id: root-cause-analysis
description: Use after an incident or recurring infrastructure problem to produce a blameless RCA, timeline, evidence map, action table, contributing factors, corrective actions, and prevention plan based on evidence.
version: 0.4.1
last_updated: 2026-07-08
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
3. Avoid blaming individuals; describe system conditions, process gaps, tooling gaps, missing checks, and decision constraints.
4. Link every conclusion to evidence in an evidence map, or mark it as assumption/unknown.
5. Use logs, monitoring output, command history, ticket records, change records, config diffs, and communications when available.
6. Produce an action table with owner, priority, effort, due date, verification method, and failure mode addressed.
7. Include prevention, detection, response, documentation, and validation actions; do not list only remediation.
</required>

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

- `references/risk-levels.md`
- `references/rca-artifacts.md`


## Output

Return a complete RCA draft with timeline, evidence map, action table, open questions, and follow-up validation plan.
