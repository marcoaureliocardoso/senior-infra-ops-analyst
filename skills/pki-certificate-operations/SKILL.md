---
name: PKI and Certificate Lifecycle Operations
description: Use when diagnosing certificate expiry, trust chain, SAN mismatch, TLS handshake, renewal, deployment validation, or certificate inventory issues.
version: 0.4.4
last_updated: 2026-07-08
maintainer: Marco Aurelio Cardoso
triggers:
  - pki-certificate-operations
  - pki and certificate lifecycle operations
---

# PKI and Certificate Lifecycle Operations

Use this skill when the operational domain materially changes the diagnostic order, evidence type, approval gate, or interpretation. The shared command-driven posture still applies, but the domain-specific reference and template are mandatory context.

<required>
1. Identify endpoint, certificate owner, CA, trust boundary, SAN requirements, renewal method, deployment targets, and dependent services.
2. Use `references/pki-certificate-lifecycle.md` for remote handshake, local certificate metadata, chain validation, key-match checks, and renewal gates.
3. Cross-reference load balancer, web gateway, Kubernetes ingress, and cloud references when certificates terminate outside the application host.
4. Never print private keys, passphrases, ACME tokens, PFX contents, CA signing material, or full sensitive SAN lists.
5. Run read-only checks first: expiry, issuer, SAN, fingerprint, chain verification, SNI behavior, listener response, and clock assumptions.
6. Interpret TLS failures as expiry, missing intermediate, wrong trust anchor, hostname mismatch, key mismatch, SNI/listener mismatch, cipher/protocol issue, or clock drift.
7. Require approval before renewal, import, trust-store update, private key movement, certificate replacement, service reload, DNS cutover, or CA changes.
8. Use shared risk vocabulary for `SENSITIVE_OUTPUT`, `ACTIVE_PROBE`, `STATE_CHANGING`, and key-handling risk.
9. Produce `skills/pki-certificate-operations/templates/certificate-renewal-plan.md` with inventory, checks, renewal path, validation, rollback, and evidence.
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

- `references/pki-certificate-lifecycle.md`
- `references/risk-levels.md`
- `references/command-execution-protocol.md`
- `references/diagnostic-order.md`
- `references/external-sources.md`
