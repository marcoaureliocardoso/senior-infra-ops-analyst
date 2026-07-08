# /cert-check

Purpose: inspect TLS certificate chain, expiry, SAN coverage, trust, and renewal/deployment plan.

Expected input:
- hostname, port, certificate file path if local, owner, planned renewal window.

Behavior:
- Use `skills/pki-certificate-operations/SKILL.md`.
- Use `skills/pki-certificate-operations/templates/certificate-renewal-plan.md`.
- Never display private keys or passphrases.
