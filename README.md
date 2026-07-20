# Senior Infrastructure Operations Analyst Skillset

Version: 0.6.1

[![CI](https://github.com/marcoaureliocardoso/senior-infra-ops-analyst/actions/workflows/ci.yml/badge.svg)](https://github.com/marcoaureliocardoso/senior-infra-ops-analyst/actions/workflows/ci.yml)
[![Security](https://github.com/marcoaureliocardoso/senior-infra-ops-analyst/actions/workflows/security.yml/badge.svg)](https://github.com/marcoaureliocardoso/senior-infra-ops-analyst/actions/workflows/security.yml)
[![Release](https://github.com/marcoaureliocardoso/senior-infra-ops-analyst/actions/workflows/release.yml/badge.svg)](https://github.com/marcoaureliocardoso/senior-infra-ops-analyst/actions/workflows/release.yml)

A command-driven skillset that personifies a Senior Infrastructure Operations Analyst for safe, evidence-based hybrid infrastructure operations.

## Core behavior

The agent should not merely suggest diagnostics when tool access exists. It should execute narrowly scoped `SAFE_READ_ONLY` commands, summarize observed evidence, interpret results, and stop before approval-gated actions.

## Included skills

This package includes 24 skills covering core operations, incident/change/RCA, on-prem infrastructure, cloud, Kubernetes, databases, containers, load balancers, PKI, CI/CD, monitoring stacks, message queues, web gateways, privileged access, ITSM/CMDB, DR drills, vendor escalation, and audit evidence.

## Subagents

This package includes 12 role-focused subagents under `subagents/` that provide domain-specific operating posture for AI agents:

| Subagent | Domain | Tools |
|---|---|---|
| `incident-commander` | Incident coordination, severity, communication | `Read, Grep, Glob, TodoWrite` |
| `diagnostic-operator` | Evidence-first diagnostics across all domains | `Read, Grep, Glob, Bash` |
| `change-manager` | Change planning, risk review, rollback | `Read, Grep, Glob, Bash` |
| `rca-facilitator` | Root cause analysis, evidence mapping | `Read, Grep, Glob, Bash` |
| `observability-sre` | SLO/SLI, error budgets, alert audit | `Read, Grep, Glob, Bash` |
| `security-operations-reviewer` | Security review, credential exposure | `Read, Grep, Glob` |
| `cloud-platform-operator` | AWS, Azure, GCP diagnostics | `Read, Grep, Glob, Bash` |
| `kubernetes-operator` | K8s/K3s workloads, services, RBAC | `Read, Grep, Glob, Bash` |
| `database-operator` | DB availability, locks, replication | `Read, Grep, Glob, Bash` |
| `network-edge-operator` | Firewall, LB, proxy, DNS, gateway | `Read, Grep, Glob, Bash` |
| `release-cicd-operator` | CI/CD pipelines, deployments, artifacts | `Read, Grep, Glob, Bash` |
| `audit-evidence-collector` | Audit evidence, redaction, compliance | `Read, Grep, Glob, Bash` |

Each subagent inherits the project-wide safety model (`references/risk-levels.md`, `references/command-execution-protocol.md`) and references its domain-specific skills and references. See `subagents/` for full definitions.

## What changed in v0.6.1

- Nori registry packaging metadata: `.nori-version`, `profile.json`, `skills.json`, `docs.md` (comprehensive Noridoc covering all components), and `skills/*/nori.json` for all 24 skills.
- Link validation fix: fictional/placeholder URLs (`.local` domains, bare hostnames, example domains) excluded from link audit, eliminating 6 permanent false positives.

## What changed in v0.6.0

- 12 role-focused subagents under `subagents/` covering all infrastructure operations domains: incident commander, diagnostic operator, change manager, RCA facilitator, observability SRE, security operations reviewer, cloud platform operator, Kubernetes operator, database operator, network edge operator, release CI/CD operator, and audit evidence collector.
- Each subagent follows the official Nori format with `name`, `description`, `tools`, and `model: inherit` frontmatter fields.
- All subagents registered in `nori.json` under the `"subagents"` array.
- 20 slash commands mapped to subagents via `allowed-tools: Task(subagent_type:<name>)`.
- Validation extended: schema checks (uniqueness, file correspondence) and content checks (frontmatter completeness, `<required>` blocks, cross-references, 60-line anti-stub threshold, tool-set validation, `allowed-tools` integrity).
- `AGENTS.md` updated with subagents delegation table.
- `.claude/` added to `.gitignore`.

## What changed in v0.5.1

- Robust link-checking across all markdown files with GET fallback for HEAD-rejecting servers.
- Historical link health tracking with living issue (trend data, auto-close/reopen).
- Level 1 deterministic link auto-fix for known patterns (RFC Editor → datatracker.ietf.org).
- 13 RFC links corrected after context verification.
- Documentation audit against Nori Skills standards — `skill_id` redundancy removed, CONTRIBUTING.md and SECURITY.md updated.

## What changed in v0.5.0

- Complete CI critical revision: 4 modular workflows (CI, Release, Security, Scheduled Maintenance).
- 9 parallel CI jobs: package validation, lint hygiene, markdown lint, spell check, link check, nori.json schema, CodeQL, ShellCheck.
- Markdownlint tuned for AI-first document conventions (rules that waste LLM tokens disabled).
- New validators: `validate-schema.py`, `validate-ci-workflows.sh`.
- Automated release workflow with version consistency check.
- 48 markdown violations fixed, 6 bugs corrected, TBD placeholders replaced with real URLs.

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

```bash
# Full local validation (content + schema + CI workflows)
bash tests/validate-package.sh

# Schema-only check
python3 tests/validate-schema.py

# CI workflow quality check
bash tests/validate-ci-workflows.sh

# Link validation (human-readable)
bash tests/validate-links.sh

# Link validation (machine-readable, for CI)
bash tests/validate-links.sh --json
```

CI runs all validators on every PR and push to main. See `.github/workflows/ci.yml`.

PowerShell parser validation requires a host with `pwsh` or Windows PowerShell installed.

## Docs

- [CHANGELOG](CHANGELOG.md)
- [ROADMAP](ROADMAP.md)
- [CONTRIBUTING](CONTRIBUTING.md)
- [SECURITY](SECURITY.md)
