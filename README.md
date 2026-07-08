# Senior Infrastructure Operations Analyst Skillset

Version: 0.4.0

A command-driven skillset that personifies a Senior Infrastructure Operations Analyst. It is designed for safe, evidence-based infrastructure and cloud operations.

## Core behavior

The agent should not merely suggest diagnostics when tool access exists. It should execute narrowly scoped SAFE_READ_ONLY commands, summarize observed evidence, interpret results, and stop before approval-gated actions.

## Included skills

- command-driven-operations
- cloud-operations
- incident-response
- infrastructure-troubleshooting
- change-management
- root-cause-analysis
- automation-safe-operations
- monitoring-observability
- runbook-authoring
- capacity-and-risk-review


## What changed in v0.3.3

- Added project hygiene files: `.gitignore`, `.gitattributes`, `Makefile`, pre-commit config, GitHub Actions validation, `CONTRIBUTING.md`, `SECURITY.md`, `CHANGELOG.md`, and `ROADMAP.md`.
- Added `references/diagnostic-order.md` to remove competing diagnostic sequences.
- Added `references/incident-severity.md` with SEV1-SEV4 and mitigation approval rules.
- Expanded root templates and aligned `templates/change-plan.md` with `change-management`.
- Required all skills to reference shared risk vocabulary in `references/risk-levels.md`.
- Added safety sections for DNS/DHCP, network, and cloud references.
- Improved AWS/Azure/GCP parity and added provider-native active-probe guidance.
- Hardened helper scripts for non-root, non-systemd, and missing TCP probe tools.
- Expanded validation from syntax checks to content and consistency checks.
- Added skill metadata fields: version, last_updated, triggers, and maintainer.

## Slash commands

- `/ops-diagnose` — evidence-driven diagnostics using the canonical diagnostic order.
- `/incident-triage` — incident worksheet using `templates/incident-worksheet.md` and SEV model.
- `/change-plan` — change plan using `templates/change-plan.md`.
- `/rca` — RCA using `skills/root-cause-analysis/templates/`.
- `/cloud-check` — scoped AWS/Azure/GCP read-only checks.
- `/runbook` — runbook/playbook drafting using structured templates.

## What changed in v0.3.2

- Expanded skeletal templates into guided operator artifacts with instructions, scoring rubrics, example rows, validation prompts, and anti-patterns.
- Added `--help` / `-h` support to Bash helper scripts and `-Help` support to the PowerShell helper.
- Expanded `references/external-sources.md` into a curated operations reference map covering SRE, RFCs, Linux, Windows Server, pfSense, Kubernetes, VMware/Broadcom, backup, AWS, Azure, and GCP.
- Fixed the `nori.json` versus `AGENTS.md` mismatch by adding `references/external-sources.md` to required references.
- Added validation assets for environments that have PowerShell installed, including a parser-based syntax check script.

## What changed in v0.3.1

- Fixed Markdown table rendering for commands that contain shell or PowerShell pipelines.
- Hardened `network-target-readonly.sh` against shell injection by validating target and port and avoiding direct interpolation in `bash -c`.
- Made operational modifiers more explicit in command matrices for active probes, sensitive output, privileged reads, logs, packet captures, and broad inventories.
- Clarified that helper scripts are optional assets and must follow the same risk/modifier approval policy.

## What changed in v0.3.0

- Added Cloud Operations skill and `references/cloud-operations.md` for AWS, Azure, and GCP.
- Expanded Monitoring and Observability with SLI/SLO/error-budget structure.
- Expanded Capacity and Risk Review with a formal risk taxonomy.
- Expanded RCA with definitions for evidence map and action table.
- Added richer slash commands with expected inputs, behavior, examples, and outputs.
- Added templates, examples, and read-only helper scripts as assets.

## Safety model

Commands are classified as:

- SAFE_READ_ONLY
- LOW_RISK_CHANGE
- DISRUPTIVE_CHANGE
- DESTRUCTIVE

Operational modifiers include:

- SENSITIVE_OUTPUT
- RESOURCE_INTENSIVE
- ACTIVE_PROBE
- PRIVILEGED
- REMOTE_SESSION_RISK

SAFE_READ_ONLY commands may be executed automatically only when scoped, non-sensitive, and low load. Sensitive or broad diagnostics require minimization, redaction, and sometimes approval. State-changing actions require explicit approval.

## Assets

Examples and templates are included under specific skills. Templates are intentionally guided artifacts, not empty placeholders. They include fields, expected evidence, scoring hints, example rows, and validation prompts.

Read-only helper scripts live under:

`skills/command-driven-operations/scripts/`

Each helper script includes a quick help mode. Use:

```bash
./skills/command-driven-operations/scripts/linux-baseline-readonly.sh --help
./skills/command-driven-operations/scripts/network-target-readonly.sh --help
```

For PowerShell:

```powershell
./skills/command-driven-operations/scripts/windows-baseline-readonly.ps1 -Help
```

These scripts are helpers, not permission grants. They should be reviewed before use and run only in authorized environments.

Validation helpers live under:

`tests/`

## Keywords

infrastructure, infrastructure operations, IT operations, sysadmin, DevOps, SRE, safe operations, command-driven operations, command-driven diagnostics, incident response, RCA, change management, runbook, observability, SLI, SLO, error budget, capacity planning, risk assessment, Linux, Windows Server, Active Directory, DNS, DHCP, networking, firewall, pfSense, VPN, VMware, Kubernetes, K3s, storage, backup, restore, cloud, AWS, Azure, GCP.


## Repository metadata

`nori.json` includes placeholder repository/homepage/bugs metadata. Replace the placeholder values before publishing to a public registry.

## Validation

Run:

```bash
make validate-local
```

Optional live link check:

```bash
make validate-links
```


## Validation reports

- Live validation report: `tests/reports/live-validation-2026-07-08.md`
- PowerShell parser validation helper: `tests/validate-powershell-syntax.ps1`


## v0.4.0 roadmap domain coverage

Version 0.4.0 converts the roadmap into operational content. New domains include databases, container runtimes, load balancers/reverse proxies, PKI/certificate lifecycle, CI/CD, monitoring stacks, message queues, web servers/application gateways, SSH/PAM, ITSM/CMDB, disaster recovery drills, vendor escalation, and audit/compliance evidence collection.

Each new domain follows the same pattern:

```text
skills/<domain>/SKILL.md
references/<domain>.md
skills/<domain>/templates/<artifact>.md
```

New slash commands:

```text
/db-triage
/container-runtime-triage
/cert-check
/queue-triage
/dr-drill
/audit-evidence
/vendor-escalate
```

These commands do not bypass approval gates. They activate the relevant skill, reference, and template while preserving the shared command execution and risk classification rules.
