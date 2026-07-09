# Linux Diagnostics

Use for Debian, Ubuntu, RHEL-like systems, appliances based on Linux, and generic service hosts.

## 0. Safe identification

| Risk | Command | Verifies | Normal signal | Abnormal signal | Next step |
|---|---|---|---|---|---|
| SAFE_READ_ONLY | `hostnamectl` | Host identity, OS, kernel | Expected hostname/OS | Unexpected host or old kernel | Confirm target before changes |
| SAFE_READ_ONLY | `whoami && id` | Current privilege | Expected user/groups | Not enough privilege | Continue read-only or request access |
| SAFE_READ_ONLY | `date -Is && uptime` | Time and uptime | Correct time, stable uptime | Wrong time, recent reboot, high load | Check time sync/logs |
| SAFE_READ_ONLY + SENSITIVE_OUTPUT | `last -x \| head -20` | Recent reboot/shutdown/login | Expected events | Unexpected reboot/shutdown | Correlate with incident start |

## 1. Host health

| Risk | Command | Verifies | Interpretation |
|---|---|---|---|
| SAFE_READ_ONLY | `uptime` | Load average and uptime | Load much higher than CPU count suggests saturation or blocked I/O. |
| SAFE_READ_ONLY + SENSITIVE_OUTPUT | `top -b -n1 \| head -40` | CPU/memory/process pressure | High `%wa` suggests I/O wait; high `%st` suggests hypervisor contention. |
| SAFE_READ_ONLY | `free -h` | Memory and swap | Heavy swap use suggests memory pressure. |
| SAFE_READ_ONLY | `vmstat 1 5` | CPU, memory, I/O wait | `wa` high = storage pressure; `r` high = CPU queue. |
| SAFE_READ_ONLY + SENSITIVE_OUTPUT | `dmesg -T \| tail -100` | Kernel/hardware errors | OOM, disk, NIC, filesystem, segfault clues. |

## 2. Disk and filesystem

| Risk | Command | Verifies | Interpretation |
|---|---|---|---|
| SAFE_READ_ONLY | `df -hT` | Filesystem space/type | 90%+ requires capacity investigation; 100% may break services. |
| SAFE_READ_ONLY | `df -ih` | Inode usage | 100% inodes with free space means many small files. |
| SAFE_READ_ONLY | `lsblk -f` | Block devices and mountpoints | Missing/changed mount may explain service failure. |
| SAFE_READ_ONLY + RESOURCE_INTENSIVE + SENSITIVE_OUTPUT | `find /var/log -xdev -type f -size +100M -printf '%s %p\n' 2>/dev/null \| sort -n \| tail -20` | Large logs | Large logs may be symptom; inspect before cleanup. |
| SAFE_READ_ONLY + PRIVILEGED + SENSITIVE_OUTPUT | `lsof +L1 2>/dev/null \| head -50` | Deleted files held open | Space not freed until process closes file. Restart requires approval if production. |

## 3. Network local state

| Risk | Command | Verifies | Interpretation |
|---|---|---|---|
| SAFE_READ_ONLY | `ip -br addr` | Interfaces and IPs | Missing IP or DOWN interface narrows to local/network. |
| SAFE_READ_ONLY | `ip route` | Default/specific routes | Missing default route blocks external access. |
| SAFE_READ_ONLY | `ip neigh` | ARP/neighbor state | FAILED/INCOMPLETE can indicate L2/gateway issue. |
| SAFE_READ_ONLY + SENSITIVE_OUTPUT | `ss -tulpn` | Listening ports/processes | Service absent from expected port means app/bind issue. |
| SAFE_READ_ONLY | `resolvectl status 2>/dev/null \|\| cat /etc/resolv.conf` | DNS config | Wrong resolver/search domain causes name issues. |

## 4. Service state

| Risk | Command | Verifies | Interpretation |
|---|---|---|---|
| SAFE_READ_ONLY | `systemctl status <service> --no-pager` | Service state | Failed/inactive needs logs before restart. |
| SAFE_READ_ONLY + SENSITIVE_OUTPUT | `journalctl -u <service> --since "1 hour ago" --no-pager` | Service logs | Exact errors guide fix; preserve messages. |
| SAFE_READ_ONLY | `<daemon> -t` | Config syntax, daemon-specific | Use actual daemon validation command, e.g. `nginx -t`, `apachectl configtest`. |
| DISRUPTIVE_CHANGE | `systemctl restart <service>` | Restart service | Requires approval; may interrupt users and hide evidence. |
| LOW_RISK_CHANGE | `systemctl reload <service>` | Reload config | Requires approval unless confirmed non-production and safe. |

## 5. Package and update clues

| Risk | Command | Verifies | Interpretation |
|---|---|---|---|
| SAFE_READ_ONLY + SENSITIVE_OUTPUT | `grep -i "install\|upgrade\|remove" /var/log/dpkg.log* 2>/dev/null \| tail -50` | Recent Debian package changes | Correlate package upgrades with incident. |
| SAFE_READ_ONLY | `rpm -qa --last 2>/dev/null \| head -30` | Recent RPM package changes | Correlate updates with incident. |
| DISRUPTIVE_CHANGE | `apt upgrade`, `dnf update`, package removal | System state change | Requires change plan and approval. |

## 6. Quick command sequence for unknown Linux outage

Run only SAFE_READ_ONLY automatically:

```bash
hostnamectl
whoami && id
date -Is && uptime
ip -br addr
ip route
resolvectl status 2>/dev/null || cat /etc/resolv.conf
df -hT
df -ih
free -h
systemctl --failed --no-pager
journalctl -p warning..alert --since "1 hour ago" --no-pager | tail -200
```

Interpret before proposing changes.

## Sensitivity and load notes

- `journalctl`, `dmesg`, application logs, process lists, firewall rules, and service status can expose usernames, paths, tokens, internal hostnames, or private IPs. Redact before sharing.
- `find`, `du`, and large log scans are RESOURCE_INTENSIVE on busy filesystems. Prefer exact paths, `-xdev`, time windows, and result limits.
- Commands using `sudo` are PRIVILEGED even when read-only; confirm the target before running.

## Related references

- `references/network-diagnostics.md`
- `references/storage-backup.md`
- `references/command-execution-protocol.md`
- `references/monitoring-stack-operations.md`
