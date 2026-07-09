# Example: Prometheus Target Down After Node Reboot

## Scenario

Grafana dashboards show missing host metrics for `lab-vm-07`. Prometheus alert `NodeExporterDown` fired 12 minutes after a planned reboot.

## Evidence sequence

| Step | Command/source | Risk | Observed result |
|---|---|---|---|
| Check alert context | Prometheus alert detail | `SAFE_READ_ONLY` | `up{job="node",instance="lab-vm-07:9100"} == 0`. |
| Check target status | Prometheus `/targets` page or API | `SAFE_READ_ONLY + SENSITIVE_OUTPUT` | Last scrape error: connection refused. |
| Check service on host | `systemctl status node_exporter --no-pager` | `SAFE_READ_ONLY + PRIVILEGED` | Service inactive after reboot. |
| Check listener | `ss -tulpn` &#124; `grep 9100` | `SAFE_READ_ONLY + PRIVILEGED` | No listener on 9100. |
| Check dashboard impact | Grafana dashboard for host metrics | `SAFE_READ_ONLY` | Only this host missing; no global scrape issue. |

## Interpretation

Prometheus and Grafana are healthy. The failure is host-local: node exporter did not start after reboot. Starting/enabling the service is a state change and needs approval or existing runbook authorization.

## Safe next actions

- Confirm whether node exporter should be enabled on this host class.
- Check service unit errors with `journalctl -u node_exporter --since '1 hour ago'`.
- Request approval to start and enable the service if policy requires it.

## Approval gate

Do not silence the alert or edit Prometheus scrape configuration until the host-local exporter failure is confirmed as non-remediable or out of scope.
