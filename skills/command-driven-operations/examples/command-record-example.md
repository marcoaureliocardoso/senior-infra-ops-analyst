# Example: Command Execution Record

## Scenario

A web service is unreachable from users. The operator has shell access to the affected Linux host and must collect narrow read-only evidence before proposing any restart or configuration change.

## Command record

| Field | Value |
|---|---|
| Target | `web-01.example.local` |
| Hypothesis | Service may be down or not listening on expected port. |
| Command | `ss -tulpn` &#124; `grep ':443'` |
| Risk | `SAFE_READ_ONLY + PRIVILEGED` |
| Purpose | Confirm whether a local process is listening on HTTPS. |
| Observed result | No listener on TCP 443; NGINX process not shown. |
| Interpretation | The host is reachable, but HTTPS is not bound locally. Next branch is service status and logs. |
| Next command | `systemctl status nginx --no-pager` |
| Approval gate | Restarting NGINX is `DISRUPTIVE_CHANGE` and requires approval unless an existing runbook authorizes it. |

## Follow-up evidence

`systemctl status nginx --no-pager` shows the service failed after a configuration reload. `nginx -t` should be run before any restart because it is read-only and can confirm whether syntax is the blocker.

## Operator note

Do not record secrets, full environment dumps, private keys, or unredacted user data in the command record. Store only the evidence needed to justify the next diagnostic step.
