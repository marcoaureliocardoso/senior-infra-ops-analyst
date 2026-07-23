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

## 5. Approval gates

Stop before executing any `LOW_RISK_CHANGE`, `DISRUPTIVE_CHANGE`, or `DESTRUCTIVE` action. Also stop before an action with `EXTERNAL_SIDE_EFFECT`. Present:

- Objective
- Exact command
- Target
- Expected impact
- Expected duration
- Validation
- Rollback or compensating action
- Safer alternative

Proceed only after explicit approval.

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
