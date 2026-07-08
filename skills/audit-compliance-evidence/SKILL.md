---
name: Audit and Compliance Evidence Collection
description: Use when collecting, redacting, organizing, and explaining evidence for audits, controls, access reviews, change evidence, backups, or compliance records.
version: 0.4.0
last_updated: 2026-07-08
maintainer: Marco Aurelio Cardoso
triggers:
  - audit-compliance-evidence
  - audit and compliance evidence collection
---

# Audit and Compliance Evidence Collection

Use this skill to operate the domain through evidence-first, command-driven diagnostics. Do not merely suggest commands when a safe tool is available; execute approved `SAFE_READ_ONLY` checks, interpret results, and stop before state-changing actions.

<required>
1. Confirm scope, affected service, environment, business impact, and whether this is incident, change, audit, or planned maintenance work.
2. Apply `references/diagnostic-order.md` unless a domain-specific order is safer; state any deviation.
3. Use `references/risk-levels.md` and `references/command-execution-protocol.md` before commands.
4. Consult `references/audit-compliance-evidence.md` for domain command order, safety rules, and interpretation.
5. Start with bounded read-only checks and capture concise evidence; redact sensitive output.
6. Interpret each result before choosing the next command.
7. Classify proposed remediation as `STATE_CHANGING`, `DISRUPTIVE`, or `DESTRUCTIVE` when applicable.
8. Require explicit approval before changes, restarts, failovers, purges, access changes, config writes, or vendor data sharing.
9. Use the template `skills/audit-compliance-evidence/templates/audit-evidence-record.md` when producing the final artifact.
</required>

## Output

Return:
- Situation and scope
- Commands executed or explicitly not executed
- Observations and interpretation
- Risk classification
- Recommended next action
- Approval gate, if needed
- Evidence/template artifact

## References

- `references/audit-compliance-evidence.md`
- `references/risk-levels.md`
- `references/command-execution-protocol.md`
- `references/diagnostic-order.md`
- `references/external-sources.md`
