# Network Diagnostics

Use for connectivity, routing, firewall, VPN, VLAN, packet loss, latency, and service reachability.

## 1. Local network state

### Linux

| Risk | Command | Verifies | Interpretation |
|---|---|---|---|
| SAFE_READ_ONLY | `ip -br addr` | Interface/IP state | DOWN or missing IP indicates local/L2/DHCP issue. |
| SAFE_READ_ONLY | `ip route get <target>` | Chosen route/source IP | Reveals interface/gateway used for target. |
| SAFE_READ_ONLY | `ip neigh show` | ARP/neighbor state | FAILED/INCOMPLETE suggests gateway/L2 issue. |

### Windows

| Risk | Command | Verifies | Interpretation |
|---|---|---|---|
| SAFE_READ_ONLY | `ipconfig /all` | IP/DNS/gateway | Wrong DHCP/DNS/gateway is common root cause. |
| SAFE_READ_ONLY | `route print` | Route table | Wrong default route or metric can misdirect traffic. |
| SAFE_READ_ONLY | `Get-NetAdapter` | Link state | Disconnected/disabled narrows issue. |

## 2. DNS checks

| Risk | Command | Verifies | Interpretation |
|---|---|---|---|
| SAFE_READ_ONLY | `dig <name>` | Default resolver lookup | Fails = resolver/search/domain problem. |
| SAFE_READ_ONLY | `dig @<dns-server> <name>` | Specific DNS server | Difference between servers indicates DNS server/zone mismatch. |
| SAFE_READ_ONLY | `nslookup <name> <dns-server>` | Windows-friendly lookup | NXDOMAIN vs timeout changes next action. |
| SAFE_READ_ONLY | `Resolve-DnsName <name> -Server <dns-server>` | Windows DNS | Use for structured DNS testing. |

## 3. Reachability and ports

| Risk | Command | Verifies | Interpretation |
|---|---|---|---|
| SAFE_READ_ONLY + ACTIVE_PROBE | `ping -c 4 <target>` | ICMP reachability | Failure does not prove TCP failure; ICMP may be blocked. |
| SAFE_READ_ONLY + ACTIVE_PROBE | `traceroute <target>` | Path hops | Useful for routing asymmetry clues; may be filtered. |
| SAFE_READ_ONLY + ACTIVE_PROBE + RESOURCE_INTENSIVE | `mtr -rw <target>` | Loss/latency over path | Loss at final hop matters more than filtered intermediate hops. |
| SAFE_READ_ONLY + ACTIVE_PROBE | `nc -vz <target> <port>` | TCP connection | Refused = host reached/no listener; timeout = drop/path/firewall. |
| SAFE_READ_ONLY + ACTIVE_PROBE | `Test-NetConnection <target> -Port <port>` | Windows TCP connection | Same interpretation as above. |
| SAFE_READ_ONLY + ACTIVE_PROBE + SENSITIVE_OUTPUT | `curl -vI https://<host>/` | HTTPS endpoint/TLS/header | TLS/cert/proxy/app errors become visible. Use `-k` only to continue testing after explicitly noting that certificate validation is being bypassed. |

## 4. Firewall/routing clues

| Risk | Command | Verifies | Interpretation |
|---|---|---|---|
| SAFE_READ_ONLY + PRIVILEGED + SENSITIVE_OUTPUT | `sudo nft list ruleset` | Linux nftables rules | Read-only, but may require privilege. Redact sensitive info. |
| SAFE_READ_ONLY + PRIVILEGED + SENSITIVE_OUTPUT | `sudo iptables -S` | Linux iptables rules | Check drops/NAT; do not flush. |
| SAFE_READ_ONLY + SENSITIVE_OUTPUT | `Get-NetFirewallRule -Enabled True \| Select -First 50` | Windows Firewall rules | Baseline only; filter by port/app for precision. |
| DISRUPTIVE_CHANGE | Firewall flush/rule edits | Traffic policy | Requires approval and rollback. |

## 5. Diagnostic order for “service unreachable”

1. Resolve name to IP.
2. Confirm client route to IP.
3. Test TCP port.
4. If timeout, check firewall/routing/NAT/VPN/path.
5. If refused, check service listener on target.
6. If connected but app fails, check TLS/proxy/app logs.
7. If intermittent, test packet loss/latency and resource saturation.


## Sensitivity and load notes

- `ping`, `traceroute`, `mtr`, `nc`, `curl`, and `Test-NetConnection` are ACTIVE_PROBE commands. Keep them targeted and low-volume.
- Firewall rule dumps, headers, routes, and DNS outputs may reveal internal topology. Summarize and redact when sharing.
- Avoid broad packet captures or high-rate tests without approval.
