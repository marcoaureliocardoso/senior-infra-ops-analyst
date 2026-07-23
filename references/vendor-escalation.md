# Vendor Escalation Management Reference

Use this when escalating incidents or defects to vendors, ISPs, cloud providers, OEMs, software support, or managed service providers.

## Safety rules

- Redact secrets, personal data, tokens, private keys, packet payloads, and full customer/user data.
- Share minimum necessary logs and evidence.
- Get approval before uploading configs, packet captures, database dumps, or support bundles.
- Preserve chain of custody for regulated or security-sensitive evidence.

## Escalation package

```text
Summary:
Business impact:
Severity requested:
Environment:
Version/build/firmware:
Topology/context:
Timeline:
Steps to reproduce:
Expected vs actual:
Evidence attached:
Changes before issue:
Workarounds tried:
Customer constraints:
Requested vendor action:
```

## Read-only collection examples

```bash
uname -a
cat /etc/os-release
systemctl status <service> --no-pager
journalctl -u <service> --since "4 hours ago" --no-pager
openssl version
```

## Risk mapping

- Version/status/log collection: `SAFE_READ_ONLY` + `SENSITIVE_OUTPUT`.
- Support bundles, packet captures, and core dumps: `SAFE_READ_ONLY` +
  `SENSITIVE_OUTPUT` + `RESOURCE_INTENSIVE`; require tight scope and approval
  before collection or sharing.
- Vendor remote session: `LOW_RISK_CHANGE` + `REMOTE_SESSION_RISK` +
  `EXTERNAL_SIDE_EFFECT`; require explicit authorization, exact participants,
  duration, scope, monitoring, and termination criteria.

## Evidence quality checklist

- Reproducible or clearly intermittent.
- Timezone included.
- Logs bounded to incident window.
- Version and topology included.
- Redaction noted.
- Business impact stated.
- Vendor ask is specific.

## Related references

- `references/itsm-cmdb-workflows.md`
- `references/audit-compliance-evidence.md`
- `references/incident-severity.md`
