# SSH and Privileged Access Management Reference

Use this for SSH access failures, sudo/PAM issues, key lifecycle, bastion/jump host operations, privileged command audit, break-glass access, and session controls.

## Safety rules

- Treat usernames, hostnames, keys, fingerprints, source IPs, MFA state, and auth logs as `SENSITIVE_OUTPUT`.
- Never print private keys or copy credentials into chat.
- Do not change `sshd_config`, sudoers, PAM, authorized_keys, groups, or MFA policy without approval and rollback.
- Validate syntax before proposing reload: `sshd -t`, `visudo -c`.

## Read-only checks

```bash
ssh -vvv <user>@<host> true
ssh-keygen -lf <public-key-file>
sshd -T
sshd -t
journalctl -u ssh --since "1 hour ago" --no-pager || journalctl -u sshd --since "1 hour ago" --no-pager
sudo -l -U <user>
visudo -c
getent passwd <user>
groups <user>
```

Interpretation:
- `Permission denied (publickey)` -> key not accepted, account mismatch, permissions, or policy.
- `Too many authentication failures` -> agent offered too many keys.
- `Authentication refused: bad ownership or modes` -> file permission issue.
- `sudo: user is not in sudoers` -> privilege policy mismatch.

## Risk mapping

- SSH verbose probe: `SAFE_READ_ONLY` + `ACTIVE_PROBE` + `SENSITIVE_OUTPUT`.
- Config expansion and syntax: `SAFE_READ_ONLY` + `SENSITIVE_OUTPUT`.
- Sudo policy inspection: `SAFE_READ_ONLY` + `SENSITIVE_OUTPUT`.
- Key rotation and sudoers/PAM/group changes: `DISRUPTIVE_CHANGE` + `PRIVILEGED`; add `REMOTE_SESSION_RISK` when access could be lost and require approval.

## Evidence to capture

User, host, source, auth method, server decision, key fingerprint, policy source, sudo rule, time, correlation with change, and rollback owner.

## Related references

- `references/linux-diagnostics.md`
- `references/active-directory.md`
- `references/audit-compliance-evidence.md`
