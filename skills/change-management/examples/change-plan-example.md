# Example: Change Plan — Reverse Proxy TLS Certificate Renewal

## Operational reason

The public certificate for `portal.example.edu` expires in 12 days. Renewal prevents browser errors and service interruption.

## Scope

- Systems: reverse proxy `rp01`, certificate store, DNS name `portal.example.edu`
- Services/users: student portal users
- Window: 22:00-22:30 local time
- Dependencies: CA renewal, DNS, load balancer health checks, application upstream

## Pre-checks

| Check | Command/evidence | Expected result |
|---|---|---|
| Current certificate | `openssl s_client -connect portal.example.edu:443 -servername portal.example.edu </dev/null` | Current SAN and expiry confirmed. |
| Config syntax | `nginx -t` or equivalent | Syntax OK before any reload. |
| Backend health | LB/reverse-proxy status page | Upstreams healthy. |

## Implementation steps

1. Stage renewed certificate and chain with restricted permissions.
2. Validate certificate chain and SAN coverage.
3. Validate reverse proxy config syntax.
4. Reload, not restart, the proxy if supported.
5. Re-check external TLS path and application smoke test.

## Risk and approval

Reloading the proxy is `STATE_CHANGING`; it requires an approved change record. Replacing the private key or certificate file must be scoped to the target vhost.

## Rollback

Restore previous certificate files from timestamped backup, validate config, reload proxy, and re-check TLS expiry to confirm rollback.

## Backout conditions

- Config syntax fails.
- Certificate chain validation fails.
- External smoke test fails after reload.
- Error rate rises above baseline for 5 minutes.

## Post-change monitoring

Monitor TLS handshake errors, HTTP 5xx, backend health, and synthetic check success for at least 30 minutes.
