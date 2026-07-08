# DNS and DHCP Diagnostics

Use for name resolution, domain lookup, lease, gateway, and client addressing issues.

## DNS diagnostic order

1. Confirm client DNS configuration.
2. Query default resolver.
3. Query expected resolver directly.
4. Query authoritative/internal DNS when known.
5. Compare A/AAAA/CNAME/MX/SRV records as relevant.
6. Check TTL, stale records, split DNS, and search suffix.
7. Check DNS service logs/listeners.

## DNS commands

| Risk | Command | Verifies | Interpretation |
|---|---|---|---|
| SAFE_READ_ONLY | `cat /etc/resolv.conf` | Linux resolver config | Wrong nameserver/search domain causes failed lookups. |
| SAFE_READ_ONLY | `resolvectl status` | systemd-resolved state | Confirms per-interface DNS. |
| SAFE_READ_ONLY | `dig <name> A` | A record via default resolver | NXDOMAIN = record absent; timeout = resolver path issue. |
| SAFE_READ_ONLY | `dig @<server> <name> A +short` | Specific resolver | Difference across servers indicates replication/config mismatch. |
| SAFE_READ_ONLY | `dig <name> +trace` | Public DNS delegation | Use mainly for internet domains. |
| SAFE_READ_ONLY | `Resolve-DnsName <name>` | Windows resolver | Similar to dig. |
| SAFE_READ_ONLY | `Resolve-DnsName _ldap._tcp.dc._msdcs.<domain> -Type SRV` | AD DC discovery | Missing SRV breaks domain auth. |

## DHCP diagnostic order

1. Confirm whether affected clients have valid IP/mask/gateway/DNS.
2. Compare affected and unaffected clients.
3. Check lease scope exhaustion.
4. Check DHCP logs.
5. Check VLAN relay/IP helper.
6. Check firewall rules for DHCP relay/server.

## DHCP commands

### Linux client

| Risk | Command | Verifies | Interpretation |
|---|---|---|---|
| SAFE_READ_ONLY | `ip -br addr` | Assigned IP | 169.254.x.x or missing IP indicates DHCP failure. |
| SAFE_READ_ONLY | `journalctl -u NetworkManager --since "1 hour ago" --no-pager` | DHCP events | Client-side lease failures. |
| DISRUPTIVE_CHANGE | `dhclient -r && dhclient` | Renew lease | Requires approval; can briefly interrupt network. |

### Windows client/server

| Risk | Command | Verifies | Interpretation |
|---|---|---|---|
| SAFE_READ_ONLY | `ipconfig /all` | Lease, server, DNS, gateway | Wrong/expired lease narrows issue. |
| SAFE_READ_ONLY | `Get-DhcpServerv4Scope` | Scope list | Server-side only; scope state. |
| SAFE_READ_ONLY | `Get-DhcpServerv4ScopeStatistics` | Scope utilization | Near 100% means lease exhaustion. |
| DISRUPTIVE_CHANGE | `ipconfig /release` / `ipconfig /renew` | Renew lease | Requires approval on remote systems; may drop session. |

## Common interpretations

- One client fails DHCP: local NIC/VLAN/cable/client config.
- Many clients in one VLAN fail: relay/IP helper/VLAN/firewall/scope.
- All clients fail: DHCP service/server/firewall.
- DNS works by FQDN but not short name: search suffix or DNS suffix issue.
- IP works but name fails: DNS path.
- Name resolves to old IP: stale record/cache/replication.


## Sensitivity and session-risk notes

- DNS/DHCP outputs can reveal internal domains, hostnames, MAC addresses, lease mappings, and user/device identity. Redact when sharing.
- DHCP release/renew on a remote system is REMOTE_SESSION_RISK because it can drop the management connection.
