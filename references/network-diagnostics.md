# Network Diagnostics Reference

Use this for connectivity, routing, firewall, VPN, VLAN, DNS path, packet loss, and port reachability diagnostics.

## Safety rules

- Network checks may be `ACTIVE_PROBE` because they send packets to targets.
- Keep scope to one source, one destination, and one port when possible.
- Do not run broad scans, sweeps, packet captures, or traceroutes across many hosts without approval.
- Packet captures and state tables may reveal internal topology, IPs, ports, and user activity; treat them as `SENSITIVE_OUTPUT`.
- Prefer `Test-NetConnection`, `nc -vz`, or one HTTP HEAD request over scanners.

## Linux checks

| Risk | Command | Purpose | Interpretation |
|---|---|---|---|
| SAFE_READ_ONLY | `ip -brief addr` | Interface/IP state | Missing IP or down interface suggests local issue. |
| SAFE_READ_ONLY | `ip route` | Routing table | Missing/default route issue if target has no path. |
| SAFE_READ_ONLY + ACTIVE_PROBE | `ping -c 4 <target>` | ICMP reachability | Failure may be firewall policy, not proof host is down. |
| SAFE_READ_ONLY + ACTIVE_PROBE + SENSITIVE_OUTPUT | `nc -vz <target> <port>` | TCP port reachability | Reveals port state; open/refused/timeout separates service, host, and filtering clues. |
| SAFE_READ_ONLY + ACTIVE_PROBE + SENSITIVE_OUTPUT | `traceroute <target>` | Path visibility | Reveals topology; incomplete hops may be policy; compare with port test. |
| SAFE_READ_ONLY + SENSITIVE_OUTPUT + PRIVILEGED | `tcpdump -i <iface> host <target> -c 50` | Packet evidence | Requires approval or tight scope; redact before sharing. |

## Windows checks

| Risk | Command | Purpose | Interpretation |
|---|---|---|---|
| SAFE_READ_ONLY | `ipconfig /all` | Local IP/DNS/gateway | Confirms client-side configuration. |
| SAFE_READ_ONLY | `route print` | Routing table | Missing route points to local or gateway issue. |
| SAFE_READ_ONLY + ACTIVE_PROBE | `Test-NetConnection <target> -Port <port>` | TCP port reachability | TcpTestSucceeded false plus ping route clues narrows path. |
| SAFE_READ_ONLY + ACTIVE_PROBE | `tracert <target>` | Path visibility | Useful but can be blocked by policy. |

## Interpretation patterns

- DNS fails but direct IP works: name resolution or search suffix issue.
- TCP refused: host reachable but service not listening or local firewall actively rejects.
- TCP timeout: firewall, route, NAT, security group, or asymmetric path possible.
- ICMP works but TCP fails: service port/firewall path issue.
- Same target works from another source: client-side route/DNS/firewall difference.

## Related references

- `references/dns-dhcp.md`
- `references/pfsense-operations.md`
- `references/load-balancers-reverse-proxies.md`
- `references/pki-certificate-lifecycle.md`
