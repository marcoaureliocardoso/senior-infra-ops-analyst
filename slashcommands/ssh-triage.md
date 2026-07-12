---
description: "Diagnose SSH login, privilege escalation, bastion, key, PAM, sudo, and privileged-access workflow issues."
allowed-tools: Task(subagent_type:diagnostic-operator)
---
# /ssh-triage

Purpose: diagnose SSH login, privilege escalation, bastion, key, PAM, sudo, or privileged-access workflow issues.

Expected input:

- target host/bastion, username or role, symptom, time window, whether break-glass or privileged access is involved.

Behavior:

- Use `skills/ssh-privileged-access-operations/SKILL.md`.
- Use `skills/ssh-privileged-access-operations/templates/privileged-access-review.md`.
- Treat usernames, hostnames, source IPs, key fingerprints, and access logs as sensitive.
- Do not change keys, sudoers, PAM, MFA, groups, or account state without explicit approval.

Example:
`/ssh-triage user cannot SSH to admin bastion after key rotation; target=bastion01 window=last 1h`
