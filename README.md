# Senior Infrastructure Operations Analyst Skillset

Version: 0.3.2

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
