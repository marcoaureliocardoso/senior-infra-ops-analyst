---
name: Capacity and Risk Review
skill_id: capacity-and-risk-review
description: Use when reviewing infrastructure capacity, technical debt, operational risk, lifecycle risk, resilience, backup posture, hardware constraints, cloud resource posture, or upgrade priorities using evidence and diagnostic commands.
version: 0.4.3
last_updated: 2026-07-08
maintainer: Marco Aurelio Cardoso
triggers:
  - capacity review
  - risk review
  - technical debt
  - lifecycle risk
  - upgrade priority
---

# Capacity and Risk Review

Review infrastructure like a senior operator accountable for continuity, resilience, and maintainability.

<required>
1. Identify current state, constraints, dependencies, single points of failure, service criticality, lifecycle status, and operational bottlenecks.
2. Execute safe inventory and capacity commands when tool access exists; scope broad scans before running them.
3. Assess risk across availability, performance, capacity, recoverability, security exposure, maintainability, lifecycle, cost, and operational toil.
4. Classify each risk by likelihood, impact, urgency, evidence strength, reversibility, blast radius, and time-to-failure.
5. Prioritize recommendations by impact, urgency, effort, reversibility, dependency, cost, and evidence confidence.
6. Separate immediate mitigations, quick wins, structural improvements, and decisions that require management acceptance.
7. Include evidence needed to validate each risk and a measurable exit criterion for each recommendation.
8. Do not execute changes, broad scans, failover tests, cleanup actions, quota changes, capacity resizing, decommissioning, or backup/restore actions without explicit approval, even when the review is non-production.
</required>

## Risk model

Use `references/capacity-risk-taxonomy.md`.

Core categories:

- Availability and single points of failure
- Performance and saturation
- Storage growth and backup capacity
- Recovery and restore confidence
- Security exposure and access drift
- Patch, warranty, OS, hypervisor, firmware, and vendor lifecycle
- Monitoring and detection gaps
- Documentation and knowledge concentration
- Manual burden and automation risk
- Cloud quota, region, identity, network, cost, and backup posture

## Evidence rules

A risk must be marked as one of:

- Observed: backed by command output, monitoring, logs, inventory, or tickets
- Inferred: likely from architecture or symptoms, but still needs confirmation
- Assumed: based on missing data; do not treat as fact

## Assets

Use:

- `skills/capacity-and-risk-review/templates/risk-matrix.md`
- `skills/capacity-and-risk-review/templates/30-60-90-plan.md`

## Required references

- `references/diagnostic-order.md`
- `references/risk-levels.md`
- `references/capacity-risk-taxonomy.md`


## Output

Return:

- Executive summary
- Evidence collected
- Risk matrix
- Top risks and rationale
- Immediate actions
- 30/60/90-day improvement plan
- Evidence still needed
- Open decisions
