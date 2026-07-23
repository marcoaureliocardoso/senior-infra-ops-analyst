# Example: HAProxy Backend Health Failure

## Scenario

Users receive intermittent 503 responses from `portal.example.local`. HAProxy is the frontend load balancer, with three backend application servers.

## Evidence sequence

| Step | Command/source | Risk | Observed result |
|---|---|---|---|
| Check frontend listener | `ss -tulpn` &#124; `grep ':443'` | `SAFE_READ_ONLY + PRIVILEGED` | HAProxy listening on TCP 443. |
| Check HAProxy status | HAProxy stats page or socket `show stat` | `SAFE_READ_ONLY + SENSITIVE_OUTPUT` | `app02` and `app03` down; `app01` up but saturated. |
| Check recent logs | `journalctl -u haproxy --since '30 min ago'` | `SAFE_READ_ONLY + SENSITIVE_OUTPUT` | Backend health checks failing with HTTP 500. |
| Probe backends from LB | `curl -vI http://app02:8080/healthz` | `SAFE_READ_ONLY + ACTIVE_PROBE` | `app02` returns HTTP 500. |
| Validate certificate path | `openssl s_client -connect portal.example.local:443 -servername portal.example.local` | `SAFE_READ_ONLY + ACTIVE_PROBE` | TLS chain valid; not a certificate issue. |

## Interpretation

The load balancer is accepting traffic and TLS is healthy. 503s are caused by unhealthy backend application instances, not frontend listener failure. Traffic changes on the load balancer may reduce impact, but removing backends is `DISRUPTIVE_CHANGE`.

## Safe next actions

- Notify application owner with failing backend health details.
- Check application logs on `app02` and `app03`.
- Confirm whether health endpoint failure maps to database/cache dependency.

## Approval gate

Do not disable backends, reload HAProxy, or alter weights without approval. If user impact is severe, propose a mitigation plan with rollback and validation.
