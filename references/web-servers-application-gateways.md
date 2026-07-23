# Web Servers and Application Gateways Reference

Use this for Apache, NGINX, IIS, Tomcat/Jetty gateways, app gateway routing, HTTP errors, headers, redirects, static content, TLS binding, and upstream integration.

## Safety rules

- Treat headers, cookies, URLs, user agents, backend names, and logs as `SENSITIVE_OUTPUT`.
- Prefer config syntax tests, status, bounded logs, and HTTP HEAD/GET probes.
- Do not reload/restart, change bindings, enable debug logs, or alter rewrite rules without approval.
- Avoid broad access-log dumps.

## Read-only checks

### Linux web servers

```bash
curl -vI https://<host>/
nginx -t && nginx -T
apachectl -t && apachectl -S
journalctl -u nginx --since "1 hour ago" --no-pager
journalctl -u apache2 --since "1 hour ago" --no-pager || journalctl -u httpd --since "1 hour ago" --no-pager
```

### IIS

```powershell
Get-Website
Get-WebBinding
Get-IISSite
Get-WinEvent -LogName System -MaxEvents 100
Get-WinEvent -LogName Application -MaxEvents 100
```

## Interpretation patterns

- 400 -> client/request/header issue or gateway rule.
- 401/403 -> auth/ACL/app gateway policy.
- 404 -> route/content mismatch.
- 413/414 -> body/URI limit.
- 429 -> rate limiting.
- 500 -> application/internal error.
- 502 -> bad upstream gateway.
- 503 -> service unavailable or maintenance.
- 504 -> upstream timeout.

## Risk mapping

- HTTP probe: `ACTIVE_PROBE`.
- Config status/tests: `SAFE_READ_ONLY` + `SENSITIVE_OUTPUT`.
- Log reads: `SAFE_READ_ONLY` + `SENSITIVE_OUTPUT`.
- Reload, restart, and routing or security rule changes: `DISRUPTIVE_CHANGE`; require approval.

## Evidence to capture

URL, method, response code, correlation/request ID, gateway route, backend target, TLS binding, error log excerpt, config test, and recent deployment/change.

## Related references

- `references/load-balancers-reverse-proxies.md`
- `references/pki-certificate-lifecycle.md`
- `references/kubernetes-operations.md`
