# Interpretation Patterns

Use these patterns to avoid jumping from symptoms to fixes.

## Connectivity problem

Order:

1. Local IP/interface
2. Local route
3. DNS resolution
4. Gateway reachability
5. Target reachability
6. Target port
7. Firewall/NAT/VPN
8. Service bind/listen
9. Service logs

Interpretation:

- DNS fails but IP works: name resolution path likely.
- Ping fails but TCP connects: ICMP may be blocked; not necessarily outage.
- TCP timeout: routing/firewall/drop or service unreachable.
- TCP refused: host reachable but service not listening or actively rejecting.
- Intermittent loss: path instability, congestion, duplex/MTU, Wi-Fi, or overloaded endpoint.

## Service down

Order:

1. Service status
2. Listening ports
3. Recent logs
4. Config validation
5. Dependencies
6. Resource pressure
7. Recent changes

Interpretation:

- Service inactive + clean stop timestamp: likely manual/maintenance action.
- Service crash loop + config error: validate config before restart.
- Service active + no port listening: wrong bind/config or failed dependency.
- Port listening + user error: check app logs, proxy, firewall, auth, backend.

## High latency

Order:

1. Scope users/segments
2. CPU/load/memory/swap
3. Disk I/O
4. Network loss/latency
5. Dependency latency
6. Application logs

Interpretation:

- High load + low CPU idle: CPU saturation.
- High load + low CPU usage: I/O wait, blocked processes, storage, NFS, lock contention.
- Swap in use with major faults: memory pressure.
- Latency only cross-site/VPN: network path or VPN bottleneck.

## Disk full

Order:

1. Filesystem usage
2. Inodes
3. Largest directories
4. Recently modified large files
5. Log growth
6. Application impact
7. Backup/retention policy

Interpretation:

- Space full but deleted files still held: process has open deleted files.
- Inodes full but space available: many small files.
- Logs growing rapidly: symptom may be upstream error loop.
- Do not delete during incident without preserving evidence.

## Authentication failure

Order:

1. Scope users/systems
2. Time sync
3. DNS to domain controllers
4. DC health
5. Account state
6. Kerberos/LDAP errors
7. Recent GPO/cert changes

Interpretation:

- Many users suddenly fail: domain/DC/DNS/time/cert path likely.
- One user fails: account/password/lockout/profile likely.
- Kerberos errors: time, SPN, DNS, domain trust, encryption/cipher issues.

## Related references

- `references/diagnostic-order.md`
- `references/command-execution-protocol.md`
- `references/risk-levels.md`
