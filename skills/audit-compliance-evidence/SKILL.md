---
name: Audit and Compliance Evidence Collection
description: Use when collecting, redacting, organizing, and explaining evidence for audits, controls, access reviews, change evidence, backups, or compliance records.
version: 0.4.4
last_updated: 2026-07-08
maintainer: Marco Aurelio Cardoso
triggers:
  - audit-compliance-evidence
  - audit and compliance evidence collection
---

# Audit and Compliance Evidence Collection

Use this skill when the operational domain materially changes the diagnostic order, evidence type, approval gate, or interpretation. The shared command-driven posture still applies, but the domain-specific reference and template are mandatory context.

<required>
1. Identify audit/control objective, scope, system/CI, evidence owner, period, retention need, sensitivity, and accepted evidence sources.
2. Use `references/audit-compliance-evidence.md` to collect traceable, minimal, time-bounded evidence with command/source, timestamp, and interpretation separated.
3. Cross-reference ITSM/CMDB, change management, backup/storage, SSH/PAM, cloud, monitoring, and incident/RCA references depending on the control.
4. Treat screenshots, user lists, access groups, logs, tickets, asset inventories, and topology as `SENSITIVE_OUTPUT`.
5. Prefer read-only source-of-record queries; do not alter configuration, tickets, groups, or audit records to make evidence look cleaner.
6. Interpret evidence against the control: design evidence, operating effectiveness, exception, compensating control, missing evidence, or stale record.
7. Require approval before exporting broad user lists, logs, support bundles, access reports, or evidence containing personal or sensitive data.
8. Preserve chain of custody: command/source, collector, timestamp, scope, redactions, hash/file name when applicable, and retention location.
9. Produce `skills/audit-compliance-evidence/templates/audit-evidence-record.md` with objective, evidence, interpretation, gaps, redaction, and follow-up.
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

- `references/audit-compliance-evidence.md`
- `references/risk-levels.md`
- `references/command-execution-protocol.md`
- `references/diagnostic-order.md`
- `references/external-sources.md`
