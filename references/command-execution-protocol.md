# Command Execution Protocol

Use this protocol when the agent has terminal, SSH, PowerShell, API, MCP, or other execution capability.

## 1. Establish context

Before running commands, determine as much as possible:

- Target: local machine, remote host, VM, container, firewall, hypervisor, cluster, domain controller
- OS/platform: Linux, Windows, pfSense/FreeBSD, ESXi, Kubernetes/K3S
- Environment: production, homologation, lab, unknown
- Privilege level: user, admin/root, read-only API, elevated shell
- Impact: affected service and users

If the context is unknown, start with safe identification commands.

## 2. Pick least-risk evidence

Use the smallest command that can answer the next question.

Bad pattern:

```bash
systemctl restart nginx
```

Better pattern:

```bash
systemctl status nginx --no-pager
journalctl -u nginx --since "30 minutes ago" --no-pager
ss -tulpn | grep ':80\|:443'
```

## 3. Command record format

For each command executed, keep this mental record:

| Field | Content |
|---|---|
| Command | Exact command run |
| Target | Host/service/component |
| Risk | SAFE_READ_ONLY / LOW_RISK_CHANGE / DISRUPTIVE_CHANGE / DESTRUCTIVE |
| Modifiers | SENSITIVE_OUTPUT / RESOURCE_INTENSIVE / ACTIVE_PROBE / PRIVILEGED / REMOTE_SESSION_RISK / EXTERNAL_SIDE_EFFECT, if any |
| Scope and expected effect | Exact boundary and intended impact |
| Approval evidence | Required for every approval-gated action |
| Validation | Expected post-action signal |
| Rollback or compensating action | Required for every approval-gated action |
| Recovery evidence | Required for DESTRUCTIVE actions |
| Purpose | What it verifies |
| Observed signal | Relevant output summary |
| Interpretation | What it confirms/refutes |
| Next step | Next check or approval gate |

## 4. Output handling

- Summarize relevant output instead of dumping huge logs.
- Preserve exact error messages when they matter.
- Do not expose secrets, tokens, private keys, cookies, session IDs, passwords, broad user lists, packet metadata, or private topology unless strictly necessary.
- If sensitive output appears, redact it and say it was redacted.
- Prefer `--tail`, `--since`, `-c`, filters, namespaces, hostnames, service names, and exact time windows over broad output.
- Do not run broad filesystem scans, broad account enumeration, cluster-wide log pulls, or wide packet captures automatically in production without tight scoping or approval.
- Never claim a command was executed when it was only suggested.

## 5. Native authorization gates

Apply the canonical control matrix in `references/risk-levels.md`.

For executor `Bash` calls, obey the native `PreToolUse` result for the exact
command. `allow` authorizes only that call. `ask` invokes the native operator
prompt and cannot be downgraded in a non-interactive surface. `deny` is
non-overridable for that call: use its redacted explanation to reformulate the
operation safely.

| Classification | Normal permission modes | `bypassPermissions` |
|---|---|---|
| Narrow SAFE_READ_ONLY | `allow` | `allow` |
| Bounded read with approval modifier | `ask` | `allow` |
| Catalogued LOW_RISK_CHANGE | `ask` | `allow` |
| Catalogued DISRUPTIVE_CHANGE | `ask` | `allow` |
| Catalogued DESTRUCTIVE | `ask` | `ask` |
| Ambiguous, encoded, evasive, unmodelled, or exfiltrating | `deny` | `deny` |

Before proposing a command that can produce `ask`, prepare:

- Objective
- Exact command
- Target
- Expected impact
- Expected duration
- Validation
- Rollback or compensating action
- Safer alternative

Proceed only when the native result is `allow`, or after Claude Code completes
the exact `ask` decision. External tools not covered by the executor Bash hook
retain their own explicit approval requirements.

## Credential use and reuse

Prefer provider-managed authentication, profiles, SSO/cached sessions,
agents, askpass, keychains, credential helpers, runtime variables, and
protected credential files established outside the generated command. Inline
configuration, helper, agent, loader, plugin, and executable-resolution
overrides deny because their effective behavior is not statically proven.
HTTP proxy, name-resolution, or insecure-TLS overrides and Kubernetes endpoint,
credential, trust, impersonation, or plugin overrides also deny when the
current binding cannot represent their effective destination. A credential supplied in the conversation is
already model/provider/transcript-visible; the guard reduces further
disclosure but cannot make that input secret from the model.

In normal modes, a detected model-visible literal raises the decision to at
least `ask`. In `bypassPermissions`, it may be reused without asking for the
value again only in the same session, domain, identity, and transport, even
across different explicit catalogued targets in that domain. Re-evaluate the
complete current command every time. Credential reuse is not command approval,
and destructive actions still ask. Reprompt after a mode, session, or model
context boundary. Never reconstruct, persist, echo, log, hash, compare, or
search the transcript for credential material.

Encrypted credentials may flow only from a catalogued decryptor directly to a
catalogued stdin consumer. Intermediate filters, display, logging, generic
files, background jobs, or unrelated consumers are denied.

## 6. Remote execution caution

Before SSH or remote PowerShell:

- Confirm target identity and environment.
- Avoid commands that write to shell history with secrets.
- Prefer read-only probes first.
- Use hostname/IP in the command record.
- Do not fan out to multiple hosts without an explicit allowlist.

## Exit code and clock evidence

For operational evidence, record command exit codes and the clock source used for timestamps. Prefer UTC for incident timelines. Examples:

```bash
date -u
timedatectl 2>/dev/null || true
<command>; rc=$?; echo "exit_code=$rc"
```

For PowerShell:

```powershell
Get-Date -AsUTC
<command>
$LASTEXITCODE
```

Do not interpret partial output as successful execution until the exit code or tool status is understood.

## Related references

- `references/risk-levels.md`
- `references/diagnostic-order.md`
- `references/interpretation-patterns.md`
