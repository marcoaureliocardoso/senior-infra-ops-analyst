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
- Support bundles, packet captures, core dumps: `SENSITIVE_OUTPUT`; approval required before sharing.
- Vendor remote session: `REMOTE_SESSION_RISK`; requires explicit authorization and monitoring.

## Evidence quality checklist

- Reproducible or clearly intermittent.
- Timezone included.
- Logs bounded to incident window.
- Version and topology included.
- Redaction noted.
- Business impact stated.
- Vendor ask is specific.
