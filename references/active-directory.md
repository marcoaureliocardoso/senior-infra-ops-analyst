# Active Directory Diagnostics

Use for domain login, Group Policy, Kerberos, LDAP, DNS SRV, replication, account lockout, and domain controller health.

## Safety rules

- Treat DCs as production-critical.
- Do not reboot DCs, change DNS, seize FSMO roles, edit GPOs, or modify accounts/groups without approval.
- Preserve event logs and timestamps.
- Validate DNS and time before deeper AD conclusions.

## 1. Client/domain basics

| Risk | Command | Verifies | Interpretation |
|---|---|---|---|
| SAFE_READ_ONLY | `whoami /user` | Logged-in identity | Confirms domain/local identity. |
| SAFE_READ_ONLY | `echo %LOGONSERVER%` | Authenticating DC | Unexpected DC may indicate site/DNS issue. |
| SAFE_READ_ONLY | `nltest /dsgetdc:<domain>` | DC discovery | Failure points to DNS/domain reachability. |
| SAFE_READ_ONLY | `w32tm /query /status` | Time sync | Time skew breaks Kerberos. |
| SAFE_READ_ONLY | `gpresult /r` | Applied GPO summary | Missing/failed GPO can explain policy issues. |

## 2. DNS SRV records

| Risk | Command | Verifies | Interpretation |
|---|---|---|---|
| SAFE_READ_ONLY | `Resolve-DnsName _ldap._tcp.dc._msdcs.<domain> -Type SRV` | DC SRV records | Missing records break DC discovery. |
| SAFE_READ_ONLY | `Resolve-DnsName <dc-fqdn>` | DC A record | Wrong/missing DC record causes auth issues. |

## 3. Domain controller health

Run on a DC or admin workstation with tools installed.

| Risk | Command | Verifies | Interpretation |
|---|---|---|---|
| SAFE_READ_ONLY | `dcdiag /v` | General DC health | Errors need correlation; not every warning is outage. |
| SAFE_READ_ONLY | `repadmin /replsummary` | Replication summary | Failures/high deltas indicate replication issue. |
| SAFE_READ_ONLY | `repadmin /showrepl` | Detailed replication | Identify failing partners/naming contexts. |
| SAFE_READ_ONLY | `netdom query fsmo` | FSMO role holders | Confirms role placement/reachability. |
| SAFE_READ_ONLY | `Get-ADDomainController -Filter * | Select HostName,Site,IPv4Address,OperatingSystem` | DC inventory | Confirms expected DCs/sites. |

## 4. Account and lockout checks

Account, lockout, and security-event queries are SAFE_READ_ONLY but SENSITIVE_OUTPUT. Prefer a single known user or exact time window. Avoid broad enumeration unless the incident scope justifies it.

| Risk | Command | Verifies | Interpretation |
|---|---|---|---|
| SAFE_READ_ONLY | `Get-ADUser <user> -Properties LockedOut,Enabled,LastLogonDate,PasswordLastSet,BadPwdCount` | User state | Single-user issue may be lockout/password/disabled. |
| SAFE_READ_ONLY | `Search-ADAccount -LockedOut` | Locked accounts | Spike may indicate saved bad credentials or attack/noise. |
| LOW_RISK_CHANGE | `Unlock-ADAccount <user>` | Unlock account | Requires approval; validate cause to avoid recurrence. |
| DISRUPTIVE_CHANGE | Group membership/GPO/password policy edits | Policy/security change | Requires change plan and approval. |

## 5. Event logs

| Risk | Command | Verifies | Interpretation |
|---|---|---|---|
| SAFE_READ_ONLY | `Get-WinEvent -LogName 'Directory Service' -MaxEvents 100` | AD DS events | Replication/database/service errors. |
| SAFE_READ_ONLY | `Get-WinEvent -FilterHashtable @{LogName='Security'; Id=4740} -MaxEvents 50` | Lockout events | Identify locked user/caller computer. |
| SAFE_READ_ONLY | `Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='Microsoft-Windows-Time-Service'} -MaxEvents 50` | Time service | Time instability affects Kerberos. |

## 6. Diagnostic order for login failures

1. Determine scope: one user, one lab, one VLAN, all users.
2. Confirm client IP/DNS points to internal DNS/DC.
3. Resolve DC SRV records.
4. Test DC reachability: DNS, Kerberos 88, LDAP 389/636, SMB 445 as appropriate.
5. Check time sync.
6. Check account state.
7. Check DC health and replication.
8. Only then propose changes.
