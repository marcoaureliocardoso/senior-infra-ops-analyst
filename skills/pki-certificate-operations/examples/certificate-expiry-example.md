# Example: TLS Certificate Expiry Check

## Scenario

A monitoring alert warns that `portal.example.local` certificate expires in 11 days. The operator must verify the certificate chain, SAN coverage, renewal owner, and rollout risk.

## Evidence sequence

| Step | Command/source | Risk | Observed result |
|---|---|---|---|
| Inspect presented cert | `openssl s_client -connect portal.example.local:443 -servername portal.example.local </dev/null 2>/dev/null | openssl x509 -noout -subject -issuer -dates -ext subjectAltName` | `SAFE_READ_ONLY + ACTIVE_PROBE` | Certificate expires in 11 days; SAN includes portal hostname. |
| Check chain | `openssl s_client -showcerts -connect portal.example.local:443 -servername portal.example.local` | `SAFE_READ_ONLY + ACTIVE_PROBE + SENSITIVE_OUTPUT` | Intermediate chain present. |
| Check load balancer config owner | CMDB/ITSM CI lookup | `SAFE_READ_ONLY + SENSITIVE_OUTPUT` | Certificate terminates on HAProxy pair. |
| Check renewal source | ACME/CA portal or certificate inventory | `SAFE_READ_ONLY + SENSITIVE_OUTPUT` | Renewal request not yet created. |
| Check dependency map | Load balancer and web gateway references | `SAFE_READ_ONLY` | Same certificate used by 2 VIPs. |

## Interpretation

The immediate risk is renewal delay, not a broken chain. Because the same certificate is reused across two VIPs, rollout must validate both endpoints and include rollback to the previous certificate bundle.

## Change outline

- Create or confirm renewal request with CA.
- Validate private key handling and certificate chain file order.
- Apply to standby node first if HA pair supports staged rollout.
- Validate both VIPs with SNI after reload.
- Monitor TLS errors and 5xx rate after change.

## Approval gate

Do not replace certificate files, reload HAProxy/NGINX, or export private keys without explicit approved change and secure handling procedure.
