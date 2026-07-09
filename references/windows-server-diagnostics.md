# Windows Server Diagnostics

Use with PowerShell where possible. Prefer read-only checks first.

## 0. Safe identification

| Risk | Command | Verifies | Interpretation |
|---|---|---|---|
| SAFE_READ_ONLY | `$env:COMPUTERNAME; whoami; Get-Date` | Target, user, time | Wrong host/user/time invalidates diagnosis. |
| SAFE_READ_ONLY + SENSITIVE_OUTPUT | `Get-ComputerInfo \| Select-Object WindowsProductName,WindowsVersion,OsHardwareAbstractionLayer,CsDomain` | OS/domain | Confirm role and domain. |
| SAFE_READ_ONLY | `Get-CimInstance Win32_OperatingSystem \| Select LastBootUpTime,FreePhysicalMemory,TotalVisibleMemorySize` | Uptime/memory | Recent reboot or low memory may explain symptoms. |

## 1. Network and DNS

| Risk | Command | Verifies | Interpretation |
|---|---|---|---|
| SAFE_READ_ONLY + SENSITIVE_OUTPUT | `ipconfig /all` | IP, DNS, DHCP, gateway | Wrong DNS/gateway commonly causes domain/service failures. |
| SAFE_READ_ONLY + SENSITIVE_OUTPUT | `Get-NetIPConfiguration` | Interface/gateway/DNS | Cleaner structured network view. |
| SAFE_READ_ONLY | `route print` | Routes | Missing/wrong routes affect reachability. |
| SAFE_READ_ONLY | `Resolve-DnsName <name>` | DNS resolution | Failure indicates DNS/server/search zone issue. |
| SAFE_READ_ONLY | `Test-NetConnection <host> -Port <port>` | TCP connectivity | `TcpTestSucceeded=False` narrows network/firewall/service. |
| SAFE_READ_ONLY + SENSITIVE_OUTPUT | `Get-NetTCPConnection -State Listen` | Listening ports | Expected service not listening means service/app issue. |

## 2. Service state

| Risk | Command | Verifies | Interpretation |
|---|---|---|---|
| SAFE_READ_ONLY | `Get-Service <Name>` | Service status | Stopped service needs event logs before restart. |
| SAFE_READ_ONLY + SENSITIVE_OUTPUT | `Get-Service \| Where-Object {$_.Status -eq 'Stopped'} \| Select -First 30` | Stopped services | Only useful with known baseline. |
| SAFE_READ_ONLY + SENSITIVE_OUTPUT | `Get-WinEvent -LogName System -MaxEvents 100 \| Select TimeCreated,ProviderName,Id,LevelDisplayName,Message` | System events | Correlate errors with incident window. |
| SAFE_READ_ONLY + SENSITIVE_OUTPUT | `Get-WinEvent -LogName Application -MaxEvents 100 \| Select TimeCreated,ProviderName,Id,LevelDisplayName,Message` | App events | App/service failures. |
| DISRUPTIVE_CHANGE | `Restart-Service <Name>` | Restart service | Requires approval; may interrupt users and erase transient evidence. |

## 3. Disk and performance

| Risk | Command | Verifies | Interpretation |
|---|---|---|---|
| SAFE_READ_ONLY | `Get-PSDrive -PSProvider FileSystem` | Filesystem free space | Low free space can break services/logs/updates. |
| SAFE_READ_ONLY | `Get-Volume` | Volumes/filesystems | Offline/unhealthy volume indicates storage issue. |
| SAFE_READ_ONLY | `Get-Counter '\Processor(_Total)\% Processor Time','\Memory\Available MBytes','\PhysicalDisk(_Total)\Avg. Disk sec/Read','\PhysicalDisk(_Total)\Avg. Disk sec/Write'` | Resource pressure | High disk latency or low memory explains slowness. |
| SAFE_READ_ONLY + SENSITIVE_OUTPUT | `Get-Process \| Sort-Object CPU -Descending \| Select -First 10 Name,Id,CPU,WorkingSet` | Top processes | Identify heavy consumers without killing them. |

## 4. Windows update/change clues

| Risk | Command | Verifies | Interpretation |
|---|---|---|---|
| SAFE_READ_ONLY + SENSITIVE_OUTPUT | `Get-HotFix \| Sort-Object InstalledOn -Descending \| Select -First 20` | Recent patches | Correlate with incident start. |
| SAFE_READ_ONLY + SENSITIVE_OUTPUT | `Get-WinEvent -FilterHashtable @{LogName='System'; Id=1074,6005,6006,6008} -MaxEvents 20` | Shutdown/reboot events | Unexpected reboot or dirty shutdown. |
| DISRUPTIVE_CHANGE | `Restart-Computer` | Reboot | Requires approval and maintenance context. |

## 5. Quick command sequence for unknown Windows outage

```powershell
$env:COMPUTERNAME; whoami; Get-Date
Get-CimInstance Win32_OperatingSystem | Select LastBootUpTime,FreePhysicalMemory,TotalVisibleMemorySize
ipconfig /all
Get-NetIPConfiguration
route print
Get-PSDrive -PSProvider FileSystem
Get-Service | Where-Object {$_.Status -eq 'Stopped'} | Select -First 30
Get-WinEvent -LogName System -MaxEvents 50 | Select TimeCreated,ProviderName,Id,LevelDisplayName,Message
```

## Sensitivity and load notes

- Event logs, service lists, process lists, firewall rules, and domain information may include usernames, hostnames, IPs, paths, and security details. Redact before sharing.
- `Get-WinEvent` over large logs can be RESOURCE_INTENSIVE. Prefer exact `FilterHashtable`, event IDs, and time windows.

## Related references

- `references/active-directory.md`
- `references/network-diagnostics.md`
- `references/storage-backup.md`
- `references/audit-compliance-evidence.md`
