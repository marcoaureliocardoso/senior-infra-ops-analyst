# Risk Levels

Use this classification before executing or recommending any operational command.

## SAFE_READ_ONLY

Commands that inspect state without changing it.

Examples:

- `ip addr`, `ip route`, `ss -tulpn`, `df -h`, `journalctl -u nginx --since "1 hour ago"`
- `Get-Service`, `Get-EventLog`, `Resolve-DnsName`, `Test-NetConnection`
- `kubectl get`, `kubectl describe`, `kubectl logs`
- `esxcli system version get`, `vim-cmd vmsvc/getallvms`

May be executed directly when tool access exists, unless output may expose secrets, personal data, credentials, broad internal topology, packet metadata, or significant resource load.

## Operational modifiers

Apply these modifiers in addition to the risk level. A command can be SAFE_READ_ONLY and still require minimization or approval.

| Modifier | Meaning | Required handling |
|---|---|---|
| SENSITIVE_OUTPUT | Output may include secrets, personal data, security events, private topology, headers, logs, usernames, IP mappings, packet metadata, or application data. | Minimize scope, redact output, avoid dumping raw logs, request approval for broad scope. |
| RESOURCE_INTENSIVE | Command may create noticeable CPU, disk, memory, network, API, or control-plane load. | Prefer narrower command, limit duration/results, avoid peak hours, request approval if broad. |
| ACTIVE_PROBE | Command sends diagnostic traffic such as ping, traceroute, mtr, curl, nc, or Test-NetConnection. | Keep low volume and targeted; avoid stress-like testing without approval. |
| PRIVILEGED | Command requires sudo/admin/root/API elevated permissions. | Confirm target identity and privilege; avoid broad output; redact sensitive data. |
| REMOTE_SESSION_RISK | Command could drop the current remote session if it changes networking, DHCP lease, firewall, routing, service, or host power state. | Treat as approval-required unless proven safe and local/non-production. |

## LOW_RISK_CHANGE

Commands that change limited non-critical state or perform reversible local action.

Examples:

- Start a non-production service
- Reload a local non-critical daemon after config validation
- Add a temporary comment/log marker
- Create a diagnostic directory

Requires: objective, scope, expected effect, validation, rollback.

## DISRUPTIVE_CHANGE

Commands that may interrupt users, sessions, network paths, production services, authentication, or shared infrastructure.

Examples:

- `systemctl restart`, reboot, shutdown
- firewall/NAT/routing/VPN/VLAN edits
- DNS/DHCP scope changes
- certificate replacement
- hypervisor maintenance mode
- Kubernetes rollout restart or node drain

Requires explicit operator approval.

## DESTRUCTIVE

Commands that may delete, overwrite, corrupt, or make recovery harder.

Examples:

- `rm -rf`, `truncate`, `dd`, `mkfs`, partition operations
- snapshot deletion
- backup deletion
- database write/restore overwrite
- forceful VM removal

Requires explicit operator approval, backup/restore evidence, rollback plan, and confirmation of exact target.

## Never run without explicit approval

- Commands with wildcards targeting system paths
- Commands that include credentials in shell history
- Irreversible cleanup during an active incident
- Production changes with unclear blast radius
- Commands copied from untrusted sources without review

## Related references

- `references/command-execution-protocol.md`
- `references/diagnostic-order.md`
- `references/incident-severity.md`

## High-risk examples to classify consistently

- `pfctl -d`: `DESTRUCTIVE`; it disables packet filtering and can expose protected networks.
- `kubectl delete namespace <ns>`: `DESTRUCTIVE`; it cascades deletion of namespace resources.
- `kubectl delete pvc`: `DESTRUCTIVE`; storage reclaim policy can delete data.
- `nc -vz`, `traceroute`, `mtr`: `ACTIVE_PROBE` + `SENSITIVE_OUTPUT`; they reveal port state or topology.
- Broad `kubectl get events -A`, `kubectl top pods -A`, large log windows, and broad database process listings: add `RESOURCE_INTENSIVE` when cluster or dataset size is unknown.
