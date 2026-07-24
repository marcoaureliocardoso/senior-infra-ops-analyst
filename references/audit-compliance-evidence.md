# Audit and Compliance Evidence Collection Reference

Use this for collecting evidence for audits, controls, access reviews, change records, backup proof, vulnerability remediation, configuration baselines, and compliance narratives.

## Safety rules

- Treat evidence as `SENSITIVE_OUTPUT`; minimize and redact.
- Do not alter systems to make evidence look compliant.
- Preserve source, timestamp, collector, command, scope, and hash when needed.
- Separate observation from interpretation.

## Evidence types

- Access evidence: users, groups, privileged roles, MFA state.
- Configuration evidence: baseline, policy, hardening, firewall, logging.
- Change evidence: approval, implementation, validation, rollback.
- Backup/DR evidence: job result, restore test, RTO/RPO proof.
- Monitoring evidence: alert rules, uptime/SLO, incident timeline.

## Collection examples

```bash
date -Is
hostname -f
id
sudo -l
getent group sudo || getent group wheel
systemctl is-enabled <service>
sha256sum <evidence-file>
```

```powershell
Get-Date -Format o
$env:COMPUTERNAME
whoami /all
Get-LocalGroupMember Administrators
Get-WinEvent -LogName Security -MaxEvents 20
```

## Evidence record template

```text
Control/objective:
System/CI:
Collector:
Timestamp/timezone:
Command/source:
Result summary:
Raw evidence location:
Redactions:
Integrity/hash:
Interpretation:
Gaps/exceptions:
Owner:
```

## Risk mapping

- Evidence collection: `SAFE_READ_ONLY` + `SENSITIVE_OUTPUT`.
- Exporting full logs, user lists, or config dumps: `SAFE_READ_ONLY` +
  `SENSITIVE_OUTPUT` + `RESOURCE_INTENSIVE`; approval, tight scope, and
  redaction required.
- Remediation actions: classify as `LOW_RISK_CHANGE`, `DISRUPTIVE_CHANGE`, or `DESTRUCTIVE` according to impact; keep them separate from evidence collection.

## Related references

- `references/itsm-cmdb-workflows.md`
- `references/ssh-privileged-access.md`
- `skills/change-management/SKILL.md`
- `references/storage-backup.md`
