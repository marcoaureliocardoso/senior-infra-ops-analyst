# Senior Infrastructure Operations Analyst Skillset

Version: 0.4.1

A command-driven skillset that personifies a Senior Infrastructure Operations Analyst for safe, evidence-based hybrid infrastructure operations.

## Core behavior

The agent should not merely suggest diagnostics when tool access exists. It should execute narrowly scoped `SAFE_READ_ONLY` commands, summarize observed evidence, interpret results, and stop before approval-gated actions.

## Included skills

This package includes 24 skills covering core operations, incident/change/RCA, on-prem infrastructure, cloud, Kubernetes, databases, containers, load balancers, PKI, CI/CD, monitoring stacks, message queues, web gateways, privileged access, ITSM/CMDB, DR drills, vendor escalation, and audit evidence.

## What changed in v0.4.1

- Replaced boilerplate roadmap skill bodies with domain-specific required steps.
- Added `skills/kubernetes-operations/` and `references/kubernetes-operations.md` for general Kubernetes operations beyond K3s host checks.
- Added examples for all v0.4 roadmap domain skills.
- Removed duplicated root templates. Template ownership is now consistent: templates live under `skills/<skill>/templates/`.
- Updated slash commands to point to skill-owned templates.
- Deepened ITSM/CMDB workflows with API lookup patterns, state-change boundaries, and CI relationship checks.
- Deepened disaster recovery drills with dependency validation, RTO/RPO interpretation, and drill type risk mapping.
- Added cross-references between related references, especially TLS/load balancer/web/Kubernetes/monitoring/ITSM/audit domains.
- Expanded validation to check template ownership, roadmap examples, Kubernetes coverage, and repeated required-block patterns.

## Slash commands

- `/ops-diagnose` — evidence-driven diagnostics using the canonical diagnostic order.
- `/incident-triage` — incident worksheet using `skills/incident-response/templates/incident-worksheet.md` and SEV model.
- `/change-plan` — change plan using `skills/change-management/templates/change-plan.md`.
- `/rca` — RCA using `skills/root-cause-analysis/templates/`.
- `/cloud-check` — scoped AWS/Azure/GCP read-only checks.
- `/runbook` — runbook/playbook drafting using `skills/runbook-authoring/templates/`.
- `/db-triage` — database availability, sessions, locks, replication, storage, and backups.
- `/container-runtime-triage` — Docker/Podman/containerd/CRI runtime issues outside Kubernetes control plane.
- `/k8s-triage` — Kubernetes workload, service, ingress, storage, RBAC, and scheduling triage.
- `/cert-check` — TLS certificate chain, expiry, SAN, trust, and renewal validation.
- `/queue-triage` — queue depth, consumer lag, broker alarms, and message flow.
- `/dr-drill` — disaster recovery drill planning/evidence.
- `/audit-evidence` — audit/compliance evidence collection.
- `/vendor-escalate` — vendor support escalation package.

## Template convention

All reusable templates are owned by skills:

```text
skills/<skill>/templates/<artifact>.md
```

There is intentionally no root `templates/` directory in v0.4.1. This avoids duplicate artifacts with unclear ownership.

## Safety model

Commands are classified as:

- `SAFE_READ_ONLY`
- `LOW_RISK_CHANGE`
- `STATE_CHANGING`
- `DISRUPTIVE_CHANGE`
- `DESTRUCTIVE`

Operational modifiers include:

- `SENSITIVE_OUTPUT`
- `RESOURCE_INTENSIVE`
- `ACTIVE_PROBE`
- `PRIVILEGED`
- `REMOTE_SESSION_RISK`

SAFE_READ_ONLY commands may be executed automatically only when scoped, non-sensitive, and low load. Sensitive or broad diagnostics require minimization, redaction, and sometimes approval. State-changing actions require explicit approval.

## Assets

Examples and templates are included under specific skills. Templates are guided artifacts, not empty placeholders. Helper scripts live under:

```text
skills/command-driven-operations/scripts/
```

Use:

```bash
./skills/command-driven-operations/scripts/linux-baseline-readonly.sh --help
./skills/command-driven-operations/scripts/network-target-readonly.sh --help
```

For PowerShell:

```powershell
./skills/command-driven-operations/scripts/windows-baseline-readonly.ps1 -Help
```

These scripts are helpers, not permission grants.

## Validation

Run:

```bash
make validate-local
```

Optional live link check:

```bash
make validate-links
```

PowerShell parser validation requires a host with `pwsh` or Windows PowerShell installed.

## Repository metadata

`nori.json` includes placeholder repository/homepage/bugs metadata. Replace placeholder values before publishing to a public registry.
