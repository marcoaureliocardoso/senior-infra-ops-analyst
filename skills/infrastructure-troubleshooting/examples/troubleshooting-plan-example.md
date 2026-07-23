# Example: Troubleshooting Plan — Web Application 502 Through Reverse Proxy

## Symptom

Users receive intermittent HTTP 502 from `portal.example.edu` after a deployment.

## Canonical order

| Step | Evidence | Interpretation | Next action |
|---|---|---|---|
| Client symptom | Browser and synthetic check show 502 | Problem is user-visible | Confirm scope and time window. |
| DNS/path | DNS resolves to expected reverse proxy | Name resolution is not primary cause | Check proxy/upstream path. |
| Proxy health | Reverse proxy upstream status shows one backend down | Backend-specific failure likely | Inspect backend service and logs. |
| Backend listener | `ss -tuln` shows app not listening on expected port | App process or config problem | Check service status and recent deploy. |
| Logs | App log shows DB connection timeout | Backend dependency failure | Check database reachability and pool saturation. |

## Commands executed

| Risk | Command | Evidence summary |
|---|---|---|
| SAFE_READ_ONLY + ACTIVE_PROBE | `curl -I https://portal.example.edu/health` | Intermittent 502. |
| SAFE_READ_ONLY + SENSITIVE_OUTPUT | `nginx -T` scoped to vhost | Upstream points to `app01:8080`, `app02:8080`. |
| SAFE_READ_ONLY | `systemctl status portal-app --no-pager` | `app02` service failed. |

## Remaining hypotheses

1. Application failed after deployment on one node.
2. Database connectivity caused app startup failure.
3. Reverse proxy health check is too permissive.

## Approval gate

Restarting the application or rolling back deployment is `DISRUPTIVE_CHANGE` and requires explicit approval with validation and rollback notes.
