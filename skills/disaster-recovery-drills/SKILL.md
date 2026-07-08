---
name: Disaster Recovery Drills
description: Use when planning or executing tabletop exercises, restore tests, failover readiness checks, RTO/RPO validation, and DR evidence collection.
version: 0.4.4
last_updated: 2026-07-08
maintainer: Marco Aurelio Cardoso
triggers:
  - disaster-recovery-drills
  - disaster recovery drills
---

# Disaster Recovery Drills

Use this skill when the operational domain materially changes the diagnostic order, evidence type, approval gate, or interpretation. The shared command-driven posture still applies, but the domain-specific reference and template are mandatory context.

<required>
1. Identify service, scenario, assets, dependencies, RTO/RPO, data criticality, recovery site/target, participants, and allowed drill type.
2. Use `references/disaster-recovery-drills.md` for tabletop, isolated restore, component failover, and full-service failover planning and evidence collection.
3. Cross-reference storage/backup, database, DNS/DHCP, cloud, load balancer, PKI, monitoring, ITSM/CMDB, and audit evidence references.
4. Treat backup locations, topology, credentials, recovery procedures, asset lists, and RTO/RPO results as `SENSITIVE_OUTPUT`.
5. Run read-only prechecks first: backup inventory, latest restore point, replication status, dependency map, monitoring status, and approval/communication readiness.
6. Interpret drill results against measurable success criteria: restored data integrity, service smoke tests, auth path, DNS/routing, monitoring, and RTO/RPO timing.
7. Require formal approval before production failover, DNS cutover, restore overwrite, replication break, destructive test, or user-impacting validation.
8. Define abort criteria, rollback, communications, evidence collection, and cleanup before any technical drill step.
9. Produce `skills/disaster-recovery-drills/templates/dr-drill-plan.md` with scenario, sequence, roles, timings, validation, deviations, and corrective actions.
</required>

## Output

Return:
- Situation and scope
- Domain-specific command/evidence sequence
- Commands executed or explicitly not executed
- Observations and interpretation
- Risk classification and modifiers
- Recommended next action
- Approval gate, if needed
- Completed template artifact

## References

- `references/disaster-recovery-drills.md`
- `references/risk-levels.md`
- `references/command-execution-protocol.md`
- `references/diagnostic-order.md`
- `references/external-sources.md`
