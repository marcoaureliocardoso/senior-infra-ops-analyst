# Storage and Backup Diagnostics

Use for disk full, datastore issues, backup failures, restore readiness, snapshots, retention, and recoverability.

## Safety rules

- Do not delete logs, backups, snapshots, or large files during an incident without preserving evidence and getting approval.
- Do not run repair tools, filesystem checks with repair, or overwrite restores without a change plan.
- Verify backup status and restore target before recommending destructive remediation.

## 1. Linux storage checks

| Risk | Command | Verifies | Interpretation |
|---|---|---|---|
| SAFE_READ_ONLY | `df -hT` | Filesystem usage/type | 90%+ warning; 100% can break services. |
| SAFE_READ_ONLY | `df -ih` | Inode usage | Full inodes mean many files, not necessarily large files. |
| SAFE_READ_ONLY | `lsblk -f` | Devices/mounts | Missing mount or wrong FS UUID can break apps. |
| SAFE_READ_ONLY + RESOURCE_INTENSIVE + SENSITIVE_OUTPUT | `du -xhd1 /var 2>/dev/null \| sort -h` | Directory growth | Use same filesystem only with `-x`. |
| SAFE_READ_ONLY + RESOURCE_INTENSIVE + SENSITIVE_OUTPUT | `find / -xdev -type f -size +1G -printf '%s %p\n' 2>/dev/null \| sort -n \| tail -20` | Large files | Investigate before deletion. |
| SAFE_READ_ONLY + PRIVILEGED + SENSITIVE_OUTPUT | `lsof +L1 2>/dev/null \| head -50` | Open deleted files | Space may not free until process restart. |
| DESTRUCTIVE | `rm`, `truncate`, `mkfs`, `fsck -y` | Deletes/repairs/writes | Requires approval, backup, exact target. |

## 2. Windows storage checks

| Risk | Command | Verifies | Interpretation |
|---|---|---|---|
| SAFE_READ_ONLY | `Get-Volume` | Volume health/free space | Low free space/offline volume. |
| SAFE_READ_ONLY | `Get-PSDrive -PSProvider FileSystem` | Drive free space | Quick capacity view. |
| SAFE_READ_ONLY + SENSITIVE_OUTPUT | `Get-CimInstance Win32_LogicalDisk -Filter "DriveType=3" \| Select DeviceID,Size,FreeSpace` | Drive capacity | Fast volume-level capacity view. |
| SAFE_READ_ONLY + SENSITIVE_OUTPUT | `See PowerShell storage event example below` | Disk/storage events | Hardware/FS clues with a bounded time window. |
| DESTRUCTIVE | `Remove-Item`, format, chkdsk repair | Deletes/repairs/writes | Requires approval and backup evidence. |

## 3. Backup status questions

Collect:

- Last successful backup timestamp
- Backup type: full/incremental/differential/snapshot
- Scope: host, VM, volume, database, files, system state
- Retention policy
- Offsite/immutable copy status
- Last restore test date
- Error messages from failed jobs
- RPO and RTO expectations

## 4. Generic backup command patterns

Use the product-specific CLI/API when known. If unknown, ask for product or inspect service names/log locations.

| Risk | Command | Verifies | Interpretation |
|---|---|---|---|
| SAFE_READ_ONLY | `systemctl list-units '*backup*' --no-pager` | Linux backup services | Identify backup agent. |
| SAFE_READ_ONLY + SENSITIVE_OUTPUT | `journalctl --since "24 hours ago" \| grep -i backup \| tail -100` | Backup-related logs | Generic clue when product unknown. |
| SAFE_READ_ONLY + SENSITIVE_OUTPUT | `See PowerShell backup service example below` | Windows backup services | Identify backup agent. |
| SAFE_READ_ONLY + SENSITIVE_OUTPUT | `See PowerShell backup event example below` | Backup/VSS events | Failed VSS writers, product errors. |

## 5. Snapshot caution

Snapshots are not backups by themselves. Before snapshot removal/consolidation:

1. Confirm VM/app backup exists.
2. Confirm datastore free space.
3. Confirm snapshot age/size.
4. Confirm maintenance window if high I/O risk.
5. Prepare rollback/abort expectations.
6. Get explicit approval.


## Sensitivity and load notes

- Broad `du`, `find`, recursive `Get-ChildItem`, and full-disk scans are RESOURCE_INTENSIVE. Start at the affected mount/drive and limit depth/time.
- Backup logs may include hostnames, paths, usernames, repository names, and policy details. Redact before sharing.


## PowerShell examples with regex alternation

These are provided outside tables so regex alternation remains copy-safe.

```powershell
Get-WinEvent -FilterHashtable @{LogName='System'; StartTime=(Get-Date).AddHours(-24)} |
  Where-Object {$_.ProviderName -match 'disk|ntfs|stor'} |
  Select-Object -First 100

Get-Service |
  Where-Object {$_.Name -match 'backup|veeam|acronis|wbengine'}

Get-WinEvent -LogName Application -MaxEvents 200 |
  Where-Object {$_.Message -match 'backup|VSS|shadow'}
```
