# Load Balancers and Reverse Proxies Reference

Use this for HAProxy, NGINX, Apache reverse proxy, cloud load balancers, health checks, backend pools, TLS termination, routing rules, and upstream failures.

## Safety rules

- Read effective configuration and health state before changing routing.
- Treat backend names, internal IPs, hostnames, headers, cookies, and certificates as `SENSITIVE_OUTPUT`.
- Do not reload, drain, disable backend, alter weights, rotate certificates, or change DNS without approval.
- Test config syntax before proposing reload.

## Read-only checks

### NGINX

```bash
nginx -T
nginx -t
systemctl status nginx --no-pager
journalctl -u nginx --since "1 hour ago" --no-pager
curl -vI https://<host>/
```

Interpretation:
- `nginx -t` fails -> no reload until fixed.
- 502 -> upstream unreachable/refused or protocol mismatch.
- 504 -> upstream timeout or saturated backend.
- 301/302 loop -> host/header/scheme rewrite issue.

### HAProxy

```bash
haproxy -c -f /etc/haproxy/haproxy.cfg
systemctl status haproxy --no-pager
journalctl -u haproxy --since "1 hour ago" --no-pager
echo "show stat" | socat - /run/haproxy/admin.sock
```

Interpretation:
- Backend DOWN with Layer4 -> TCP/connectivity issue.
- Backend DOWN with Layer7 -> HTTP health endpoint/protocol issue.
- Queue growth -> saturation or insufficient backends.

### Apache HTTPD reverse proxy

```bash
apachectl -t
apachectl -S
systemctl status apache2 --no-pager || systemctl status httpd --no-pager
```

## Cloud LB examples

```bash
aws elbv2 describe-load-balancers
aws elbv2 describe-target-health --target-group-arn <arn>
az network lb list -o table
az network application-gateway show --name <name> --resource-group <rg>
gcloud compute backend-services list
gcloud compute backend-services get-health <service> --global
```

## Risk mapping

- Config print and status: `SAFE_READ_ONLY` + `SENSITIVE_OUTPUT`.
- External curl: `ACTIVE_PROBE`.
- Reload, drain, weight change, cert replacement: `STATE_CHANGING`, requires approval.

## Evidence to capture

VIP/listener, protocol, route rule, backend pool, health status, last config test, observed response code, error logs, and recent changes.
