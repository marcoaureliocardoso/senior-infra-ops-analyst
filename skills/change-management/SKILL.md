---
name: Change Management
skill_id: change-management
description: Use when planning, reviewing, approving, executing, or documenting infrastructure changes, maintenance windows, migrations, upgrades, firewall rules, deployments, patches, or configuration changes.
version: 0.4.4
last_updated: 2026-07-08
maintainer: Marco Aurelio Cardoso
triggers:
  - change plan
  - maintenance window
  - rollback plan
  - migration
  - upgrade
---

# Change Management

Treat every infrastructure change as a controlled operation with scope, validation, rollback, and communication.

<required>
1. Define objective, scope, affected services, affected users, dependencies, and maintenance window.
2. Identify risk level, blast radius, prerequisites, and backout conditions.
3. Provide pre-checks, execution steps, validation steps, rollback steps, and post-change monitoring.
4. Execute only safe pre-checks automatically when tool access exists.
5. Require explicit approval before state-changing implementation steps.
6. Record evidence before and after the change.
</required>

## Change plan structure

1. Objective
2. Operational reason
3. Scope
4. Systems affected
5. Dependencies
6. Risk assessment
7. Preconditions
8. Backup/snapshot/restore point
9. Safe pre-checks to execute
10. Implementation steps requiring approval
11. Validation commands
12. Rollback commands
13. Communication
14. Post-change monitoring
15. Evidence to archive

## Risk signals

Escalate risk if the change touches firewall, routing, VPN, VLANs, DNS, DHCP, identity, certificates, authentication, production storage, backups, hypervisors, shared infrastructure, remote access paths, or automation affecting multiple hosts.

## Required references

- `references/risk-levels.md`
- `references/diagnostic-order.md`
- `skills/change-management/templates/change-plan.md`

## Output

Return a complete change plan ready for operator approval and execution.
