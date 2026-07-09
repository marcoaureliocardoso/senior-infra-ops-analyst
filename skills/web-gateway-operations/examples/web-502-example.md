# Example: NGINX 502 from Application Gateway

## Scenario

Users receive HTTP 502 from `https://library.example.local`. NGINX terminates TLS and proxies to an upstream application on `127.0.0.1:8080`.

## Evidence sequence

| Step | Command/source | Risk | Observed result |
|---|---|---|---|
| Check external response | `curl -vI https://library.example.local/` | `SAFE_READ_ONLY + ACTIVE_PROBE` | TLS succeeds; response is HTTP 502. |
| Check NGINX config syntax | `nginx -t` | `SAFE_READ_ONLY + PRIVILEGED` | Syntax OK. |
| Check listener | `ss -tulpn` &#124; `grep -E ':443` &#124; `:8080'` | `SAFE_READ_ONLY + PRIVILEGED` | NGINX listens on 443; upstream not listening on 8080. |
| Check NGINX error logs | `journalctl -u nginx --since '30 min ago'` or error log tail | `SAFE_READ_ONLY + SENSITIVE_OUTPUT` | `connect() failed (111: Connection refused) while connecting to upstream`. |
| Check app service | `systemctl status library-api --no-pager` | `SAFE_READ_ONLY + PRIVILEGED` | Application service failed after config reload. |

## Interpretation

TLS and NGINX frontend are functioning. The 502 is caused by the local upstream application not listening on the configured port. Reloading NGINX is unlikely to fix the issue; the next diagnostic branch is application service failure.

## Safe next actions

- Review application service logs.
- Compare application port configuration with NGINX upstream config.
- Confirm whether a recent deployment changed the listening port or environment file.

## Approval gate

Do not restart the application, edit NGINX upstreams, or roll back deployment without approval. Those actions are state changes and need validation and rollback criteria.
