---
name: SSH and Privileged Access Operations
description: Use when diagnosing SSH reachability, authentication, sudo/PAM, privileged access, bastion, key lifecycle, account lockout, or access review issues.
version: 0.4.1
last_updated: 2026-07-08
maintainer: Marco Aurelio Cardoso
triggers:
  - ssh-privileged-access-operations
  - ssh and privileged access operations
---

# SSH and Privileged Access Operations

Use this skill when the operational domain materially changes the diagnostic order, evidence type, approval gate, or interpretation. The shared command-driven posture still applies, but the domain-specific reference and template are mandatory context.

<required>
1. Identify target host, access path, account, bastion/jump host, auth method, PAM/sudo policy, lockout risk, and operational need.
2. Use `references/ssh-privileged-access.md` for safe checks of listener, logs, SSH config, authorized keys metadata, sudo policy, and PAM/account status.
3. Cross-reference Linux, Active Directory, network, firewall, audit evidence, and vendor escalation references when access depends on those layers.
4. Treat usernames, keys, bastion names, source IPs, groups, sudo rules, and auth logs as `SENSITIVE_OUTPUT`.
5. Run read-only checks before changing keys, groups, sudoers, PAM, firewall rules, or account status.
6. Interpret failures as network/firewall, DNS, host listener, key mismatch, expired account, locked account, PAM/LDAP/AD issue, sudo policy, or bastion route failure.
7. Require approval before adding/removing keys, unlocking accounts, changing groups/sudoers, modifying sshd_config, or restarting SSH.
8. Classify remote access attempts as `REMOTE_SESSION_RISK` and avoid interactive sessions unless necessary and authorized.
9. Produce `skills/ssh-privileged-access-operations/templates/privileged-access-review.md` with access path, evidence, risk, approval, and audit notes.
</required>

## Output

Return:
- Situation and scope
- Domain-specific command/evidence sequence
- Commands executed or explicitly not executed
- Observations and interpretation
- Risk classification and modifiers
- Recommended next action
- Approval gate, if needed
- Completed template artifact

## References

- `references/ssh-privileged-access.md`
- `references/risk-levels.md`
- `references/command-execution-protocol.md`
- `references/diagnostic-order.md`
- `references/external-sources.md`
