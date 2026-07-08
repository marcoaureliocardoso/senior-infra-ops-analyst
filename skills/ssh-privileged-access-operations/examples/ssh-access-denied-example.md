# Example: SSH Access Denied for Infrastructure Operator

## Scenario

An infrastructure operator cannot SSH to `backup-srv-01` using a managed key. Other operators can connect. Scope is authentication diagnostics and privileged access evidence, not account modification.

## Evidence sequence

| Step | Command/source | Risk | Observed result |
|---|---|---|---|
| Client debug | `ssh -vvv operator@backup-srv-01` | `SAFE_READ_ONLY + SENSITIVE_OUTPUT` | Public key offered, server rejects it. |
| Server auth logs | `journalctl -u ssh --since '30 min ago'` or `/var/log/auth.log` | `SAFE_READ_ONLY + SENSITIVE_OUTPUT + PRIVILEGED` | `Authentication refused: bad ownership or modes for directory`. |
| Account state | `getent passwd operator` | `SAFE_READ_ONLY` | Account exists with expected shell. |
| Authorized key source | IAM/PAM/AuthorizedKeysCommand logs | `SAFE_READ_ONLY + SENSITIVE_OUTPUT` | Key lookup succeeds. |
| Sudo entitlement | `sudo -l -U operator` where authorized | `SAFE_READ_ONLY + PRIVILEGED + SENSITIVE_OUTPUT` | Not checked until SSH auth is resolved. |

## Interpretation

The failure is likely server-side file ownership or mode policy, not missing account or absent key. Remediation may require changing permissions on the user home or `.ssh` directory, which is a state change.

## Safe next actions

- Confirm the expected ownership/mode standard for home and `.ssh` paths.
- Compare with a known-good account without exposing private key material.
- Open an access remediation ticket if file permissions must be corrected.

## Approval gate

Do not edit `sshd_config`, add keys manually, change sudoers, or chmod/chown user directories without approval. Privileged access changes require audit trail.
