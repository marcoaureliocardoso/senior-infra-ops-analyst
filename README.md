# Senior Infrastructure Operations Analyst Skillset

Version: 0.3.1

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

Examples and templates are included under specific skills. Read-only helper scripts live under:

`skills/command-driven-operations/scripts/`

These scripts are helpers, not permission grants. They should be reviewed before use and run only in authorized environments.

## Keywords

infrastructure, infrastructure operations, IT operations, sysadmin, DevOps, SRE, safe operations, command-driven operations, command-driven diagnostics, incident response, RCA, change management, runbook, observability, SLI, SLO, error budget, capacity planning, risk assessment, Linux, Windows Server, Active Directory, DNS, DHCP, networking, firewall, pfSense, VPN, VMware, Kubernetes, K3s, storage, backup, restore, cloud, AWS, Azure, GCP.
