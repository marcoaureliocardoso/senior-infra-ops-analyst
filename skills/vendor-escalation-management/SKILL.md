---
name: Vendor Escalation Management
description: Use when preparing or managing support escalations to vendors, ISPs, cloud providers, OEMs, MSPs, or software support teams.
version: 0.4.3
last_updated: 2026-07-08
maintainer: Marco Aurelio Cardoso
triggers:
  - vendor-escalation-management
  - vendor escalation management
---

# Vendor Escalation Management

Use this skill when the operational domain materially changes the diagnostic order, evidence type, approval gate, or interpretation. The shared command-driven posture still applies, but the domain-specific reference and template are mandatory context.

<required>
1. Identify vendor/product, contract/support level, version, architecture, impact, urgency, prior troubleshooting, and exact support ask.
2. Use `references/vendor-escalation.md` to assemble bounded evidence: timeline, symptoms, logs summary, configs/diffs, topology excerpt, reproduction, and business impact.
3. Cross-reference incident response, audit evidence, security/sensitive-output policy, cloud/provider references, and ITSM records before sharing artifacts.
4. Redact credentials, private keys, tokens, personal data, internal IPs where not needed, customer data, and unrelated logs before packaging.
5. Run or request only vendor-safe read-only diagnostics that are scoped, documented, and approved by the operator.
6. Interpret vendor data requests by risk: harmless metadata, sensitive bundle, privileged collector, disruptive reproduction, or data export.
7. Require approval before uploading support bundles, enabling debug logs, running vendor collectors, granting remote sessions, or sharing topology.
8. Maintain a clear escalation state: opened, waiting for vendor, waiting for customer, escalated severity, workaround applied, RCA pending, or closed.
9. Produce `skills/vendor-escalation-management/templates/vendor-escalation-package.md` with concise problem statement, evidence, redactions, questions, and next action.
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

- `references/vendor-escalation.md`
- `references/risk-levels.md`
- `references/command-execution-protocol.md`
- `references/diagnostic-order.md`
- `references/external-sources.md`
