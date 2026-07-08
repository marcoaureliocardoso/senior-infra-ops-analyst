# Example: Incident Worksheet — Campus DNS Resolution Failure

## Summary

Users report that internal systems are unreachable by name, but some services respond by IP. First report: 09:12 local time.

## Severity

- Provisional severity: SEV2
- Impact: multiple departments unable to access internal applications by hostname
- Blast radius: campus LAN clients using internal DNS
- Status: active degradation

## Facts vs hypotheses

| Type | Item |
|---|---|
| Fact | `ping 10.0.10.20` succeeds from admin workstation. |
| Fact | `Resolve-DnsName portal.internal` times out against primary DNS. |
| Hypothesis | Primary DNS service is unhealthy or blocked. |
| Hypothesis | Recent firewall rule change affected DNS traffic. |

## Commands executed

| Time UTC | Risk | Command | Evidence summary | Interpretation |
|---|---|---|---|
| 12:18 | SAFE_READ_ONLY | `ipconfig /all` | Client DNS points to `10.0.0.5`. | Client is using expected DNS server. |
| 12:19 | SAFE_READ_ONLY + ACTIVE_PROBE | `Test-NetConnection 10.0.0.5 -Port 53` | TCP 53 failed. | DNS server or firewall path problem. |
| 12:20 | SAFE_READ_ONLY + SENSITIVE_OUTPUT | DNS service status check | Service running. | Network path/firewall more likely. |

## Mitigation options

| Option | Risk | Approval needed | Validation |
|---|---|---|---|
| Switch DHCP DNS option to secondary resolver | STATE_CHANGING | Yes | Clients resolve internal names after renew. |
| Add temporary firewall allow rule for DNS | STATE_CHANGING | Yes | Port 53 reachable from affected VLAN. |

## Communication update

Internal DNS resolution is degraded for campus clients. The team confirmed IP connectivity works and is checking DNS reachability and recent network changes. Next update in 30 minutes or sooner if mitigated.
