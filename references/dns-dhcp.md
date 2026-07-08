# DNS and DHCP Reference

Use this for name resolution, forward/reverse lookup, resolver configuration, lease, scope, reservation, option, and relay issues.

## Safety rules

- DNS queries are usually `SAFE_READ_ONLY + ACTIVE_PROBE` because they send requests to resolvers.
- DHCP scope/reservation inspection may expose MAC addresses, hostnames, usernames, and topology; treat as `SENSITIVE_OUTPUT`.
- Zone changes, forwarder changes, DHCP scope changes, reservation edits, lease deletion, and service restarts require explicit approval.
- Do not dump full zones, full lease databases, or large AD-integrated DNS data unless tightly scoped and approved.

## DNS checks

| Risk | Command | Purpose | Interpretation |
|---|---|---|---|
| SAFE_READ_ONLY + ACTIVE_PROBE | `dig <name> A` | Resolve A record through default resolver | NXDOMAIN vs timeout separates zone answer from resolver path. |
| SAFE_READ_ONLY + ACTIVE_PROBE | `dig @<resolver> <name> A +short` | Test specific resolver | Resolver-specific failure suggests forwarder/zone/replication issue. |
| SAFE_READ_ONLY + ACTIVE_PROBE | `dig <ip>.in-addr.arpa PTR` | Reverse lookup | Missing PTR may affect auth/logging, not always outage. |
| SAFE_READ_ONLY + ACTIVE_PROBE | `Resolve-DnsName <name>` | Windows DNS lookup | Compare with Linux `dig` when clients differ. |
| SAFE_READ_ONLY + SENSITIVE_OUTPUT | `Get-DnsClientServerAddress` | Windows resolver config | Reveals internal resolver IPs. |

## DHCP checks

| Risk | Command | Purpose | Interpretation |
|---|---|---|---|
| SAFE_READ_ONLY + SENSITIVE_OUTPUT | `ipconfig /all` | Client DHCP options | Wrong gateway/DNS/suffix points to scope/options issue. |
| SAFE_READ_ONLY + SENSITIVE_OUTPUT | `Get-DhcpServerv4Scope` | DHCP scope state | Low available leases suggests capacity issue. |
| SAFE_READ_ONLY + SENSITIVE_OUTPUT | `Get-DhcpServerv4Lease -ScopeId <scope>` | Lease state | Scope narrowly; may reveal endpoints. |

## Approval-gated actions

- Add/edit/delete DNS records.
- Change resolver forwarders or conditional forwarders.
- Restart DNS/DHCP services.
- Change DHCP scope options, reservations, or exclusions.
- Delete leases in production.

## Related references

- `references/network-diagnostics.md`
- `references/active-directory.md`
- `references/pfsense-operations.md`
- `references/load-balancers-reverse-proxies.md`
