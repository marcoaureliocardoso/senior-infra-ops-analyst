# pfSense Operations

Use for pfSense-style firewall operations. Prefer GUI/API backups and read-only CLI checks before changes. Many pfSense commands are FreeBSD-based.

## Safety rules

- Export/confirm a recent configuration backup before firewall, NAT, DHCP, VPN, or routing changes.
- Do not flush states, restart services, or edit rules during production hours without approval.
- Avoid editing low-level config files directly unless it is a documented emergency recovery procedure.
- Prefer GUI/API changes that preserve config history when available.

## 1. Safe CLI identification

| Risk | Command | Verifies | Interpretation |
|---|---|---|---|
| SAFE_READ_ONLY | `hostname` | Target firewall | Confirm you are on the correct appliance. |
| SAFE_READ_ONLY | `date` | Time | Wrong time breaks certs, VPN, logs, auth. |
| SAFE_READ_ONLY | `uptime` | Load/uptime | Recent reboot or high load is incident evidence. |
| SAFE_READ_ONLY + SENSITIVE_OUTPUT | `ifconfig` | Interfaces, link, IPs | Interface down/errors guide L1/L2 checks. |
| SAFE_READ_ONLY + SENSITIVE_OUTPUT | `netstat -rn` | Routing table | Missing/wrong default/static routes affect traffic. |

## 2. Firewall and states

| Risk | Command | Verifies | Interpretation |
|---|---|---|---|
| SAFE_READ_ONLY + PRIVILEGED + SENSITIVE_OUTPUT | `pfctl -sr` | Loaded filter rules | Confirms runtime rules; compare with intended GUI rules. |
| SAFE_READ_ONLY + PRIVILEGED + SENSITIVE_OUTPUT | `pfctl -sn` | NAT rules | NAT mismatch can break outbound/inbound traffic. |
| SAFE_READ_ONLY + PRIVILEGED + SENSITIVE_OUTPUT | `pfctl -ss \| head -50` | State table samples | Confirms whether sessions are being created. |
| SAFE_READ_ONLY + PRIVILEGED | `pfctl -si` | PF counters/state summary | High drops, state exhaustion, counters indicate firewall pressure. |
| DISRUPTIVE_CHANGE | `pfctl -F states` | Flush all states | Breaks active sessions; requires approval. |
| DESTRUCTIVE | `pfctl -d` | Disable packet filter | Removes packet filtering; emergency-only with explicit senior approval, rollback plan, and out-of-band access. |

## 3. Logs

| Risk | Command | Verifies | Interpretation |
|---|---|---|---|
| SAFE_READ_ONLY + SENSITIVE_OUTPUT | `clog /var/log/filter.log \| tail -100` | Firewall log | Blocks/pass actions near incident time. |
| SAFE_READ_ONLY + SENSITIVE_OUTPUT | `clog /var/log/system.log \| tail -100` | System log | Service, interface, package, boot issues. |
| SAFE_READ_ONLY + SENSITIVE_OUTPUT | `clog /var/log/dhcpd.log \| tail -100` | DHCP log | Lease/renewal failures. |
| SAFE_READ_ONLY + SENSITIVE_OUTPUT | `clog /var/log/openvpn.log \| tail -100` | OpenVPN log | VPN auth/tunnel errors. |
| SAFE_READ_ONLY + SENSITIVE_OUTPUT | `clog /var/log/ipsec.log \| tail -100` | IPsec log | Phase1/Phase2/auth/tunnel clues. |

## 4. Interfaces and packet capture

| Risk | Command | Verifies | Interpretation |
|---|---|---|---|
| SAFE_READ_ONLY | `ifconfig <interface>` | Interface status/errors | Errors/collisions/drops suggest link/NIC issue. |
| SAFE_READ_ONLY + PRIVILEGED + SENSITIVE_OUTPUT | `tcpdump -ni <interface> host <ip> -c 50` | Whether packets reach interface | Packets on LAN but not WAN suggests firewall/NAT/routing. |
| SAFE_READ_ONLY + PRIVILEGED + SENSITIVE_OUTPUT | `tcpdump -ni <interface> port <port> -c 50` | Service-specific traffic | Confirms SYN/SYN-ACK flow direction. |

`tcpdump` is read-only but SENSITIVE_OUTPUT and ACTIVE_PROBE-adjacent operationally because it captures traffic metadata. Use exact host/port/interface filters, short packet counts, and no payload capture unless approved.

## 5. DNS/DHCP service checks

| Risk | Command | Verifies | Interpretation |
|---|---|---|---|
| SAFE_READ_ONLY + SENSITIVE_OUTPUT | `sockstat -4 -l \| grep ':53\|:67\|:68'` | DNS/DHCP listeners | Expected services not listening means service/config issue. |
| SAFE_READ_ONLY + SENSITIVE_OUTPUT | `ps aux \| grep -E 'unbound\|dnsmasq\|dhcpd'` | Service processes | Missing process indicates service stopped. |
| DISRUPTIVE_CHANGE | Restart DNS/DHCP services | Service recovery | Requires approval; can interrupt resolution/leases. |

## 6. GUI operations requiring approval

- Add/edit/delete firewall rules
- NAT/port-forward changes
- Gateway/routing changes
- VPN phase changes
- DHCP scope/options changes
- DNS resolver/forwarder changes
- Package install/update/remove
- Reboot or service restart

## 7. Emergency diagnostic order

1. Confirm target firewall and time.
2. Check interface status and routing.
3. Check firewall/NAT runtime rules.
4. Check state table and counters.
5. Check logs for blocks/errors.
6. Run targeted packet capture.
7. Present mitigation requiring approval.


## Sensitivity notes

Runtime firewall/NAT rules, state tables, VPN logs, and packet captures reveal private topology and user/session metadata. Summarize relevant signals and redact addresses, usernames, public IPs, and tunnel identifiers when sharing outside the operator context.

## Related references

- `references/network-diagnostics.md`
- `references/dns-dhcp.md`
- `references/incident-severity.md`
