# Senior Infrastructure Operations Analyst Skillset

Version: 0.4.4

[![CI](https://github.com/marcoaureliocardoso/senior-infra-ops-analyst/actions/workflows/ci.yml/badge.svg)](https://github.com/marcoaureliocardoso/senior-infra-ops-analyst/actions/workflows/ci.yml)
[![Security](https://github.com/marcoaureliocardoso/senior-infra-ops-analyst/actions/workflows/security.yml/badge.svg)](https://github.com/marcoaureliocardoso/senior-infra-ops-analyst/actions/workflows/security.yml)
[![Release](https://github.com/marcoaureliocardoso/senior-infra-ops-analyst/actions/workflows/release.yml/badge.svg)](https://github.com/marcoaureliocardoso/senior-infra-ops-analyst/actions/workflows/release.yml)

A command-driven skillset that personifies a Senior Infrastructure Operations Analyst for safe, evidence-based hybrid infrastructure operations.

## Core behavior

The agent should not merely suggest diagnostics when tool access exists. It should execute narrowly scoped `SAFE_READ_ONLY` commands, summarize observed evidence, interpret results, and stop before approval-gated actions.

## Included skills

This package includes 24 skills covering core operations, incident/change/RCA, on-prem infrastructure, cloud, Kubernetes, databases, containers, load balancers, PKI, CI/CD, monitoring stacks, message queues, web gateways, privileged access, ITSM/CMDB, DR drills, vendor escalation, and audit evidence.

## What changed in v0.4.4

- Added YAML frontmatter with operational descriptions to all 20 slash commands.

## What changed in v0.4.3

- Added populated examples for the 7 original core skills.
- Added `## Related references` sections to all original references and tightened cross-reference validation.
- Added a cloud operations template and 6 slash commands for SSH, load balancers, monitoring stacks, web gateways, CI/CD, and ITSM updates.
- Aligned safety and risk classifications for Kubernetes/K3s, network probes, pfSense `pfctl -d`, token handling, and state-changing approval gates.
- Expanded validation for all skill examples, related references, cloud templates, and broken internal links.

## What changed in v0.4.2

- Populated 13 previously skeletal roadmap examples with realistic evidence sequences, interpretations, safe next actions, approval gates, and output records.
- Clarified `AGENTS.md` expanded-domain reference heading for v0.4.0/v0.4.1 coverage.
- Updated validation to detect skeletal example files and empty field-only example patterns.

## What changed in v0.4.1

- Replaced boilerplate roadmap skill bodies with domain-specific required steps.
- Added `skills/kubernetes-operations/` and `references/kubernetes-operations.md` for general Kubernetes operations beyond K3s host checks.
- Removed duplicated root templates. Template ownership is now consistent: templates live under `skills/<skill>/templates/`.
- Updated slash commands to point to skill-owned templates.
- Deepened ITSM/CMDB workflows with API lookup patterns, state-change boundaries, and CI relationship checks.
- Deepened disaster recovery drills with dependency validation, RTO/RPO interpretation, and drill type risk mapping.
- Added cross-references between related references.
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
- `/ssh-triage` — SSH, bastion, PAM, sudo, key, and privileged-access triage.
- `/lb-triage` — load balancer and reverse proxy health/routing/TLS triage.
- `/monitoring-stack-triage` — Prometheus/Grafana/Zabbix/ELK/OpenSearch triage.
- `/web-gateway-triage` — web server, application gateway, WAF, and upstream triage.
- `/cicd-triage` — CI/CD pipeline, runner, artifact, and deployment-gate triage.
- `/itsm-update` — ITSM/CMDB factual update and impact-analysis drafting.

## Template convention

All reusable templates are owned by skills:

```text
skills/<skill>/templates/<artifact>.md
```

There is intentionally no root `templates/` directory from v0.4.1 onward. This avoids duplicate artifacts with unclear ownership.

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
