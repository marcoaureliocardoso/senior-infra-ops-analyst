# Senior Infrastructure Operations Analyst Skillset

Version: 0.11.0

[![CI](https://github.com/marcoaureliocardoso/senior-infra-ops-analyst/actions/workflows/ci.yml/badge.svg)](https://github.com/marcoaureliocardoso/senior-infra-ops-analyst/actions/workflows/ci.yml)
[![Security](https://github.com/marcoaureliocardoso/senior-infra-ops-analyst/actions/workflows/security.yml/badge.svg)](https://github.com/marcoaureliocardoso/senior-infra-ops-analyst/actions/workflows/security.yml)
[![Release](https://github.com/marcoaureliocardoso/senior-infra-ops-analyst/actions/workflows/release.yml/badge.svg)](https://github.com/marcoaureliocardoso/senior-infra-ops-analyst/actions/workflows/release.yml)

A command-driven skillset that personifies a Senior Infrastructure Operations Analyst for safe, evidence-based hybrid infrastructure operations.

## Core behavior

The agent should not merely suggest diagnostics when tool access exists. It should execute commands when the native guard returns `allow`, use Claude Code's exact prompt for `ask`, reformulate `deny`, summarize observed evidence, and interpret results.

## Included skills

This package includes 24 skills covering core operations, incident/change/RCA, on-prem infrastructure, cloud, Kubernetes, databases, containers, load balancers, PKI, CI/CD, monitoring stacks, message queues, web gateways, privileged access, ITSM/CMDB, DR drills, vendor escalation, and audit evidence.

## Subagents

This package includes 12 role-focused subagents under `subagents/` that provide domain-specific operating posture for AI agents:

| Subagent | Domain | Max turns | Tools |
|---|---|---:|---|
| `incident-commander` | Incident coordination, severity, communication | 20 | `Read, Grep, Glob, TodoWrite, Skill` |
| `diagnostic-operator` | Evidence-first diagnostics across all domains | 16 | `Read, Grep, Glob, Bash, WebFetch, WebSearch, Skill` |
| `change-manager` | Change planning, risk review, rollback | 10 | `Read, Grep, Glob, WebFetch, WebSearch, Skill` |
| `rca-facilitator` | Root cause analysis, evidence mapping | 12 | `Read, Grep, Glob, WebFetch, WebSearch, Skill` |
| `observability-sre` | SLO/SLI, error budgets, alert audit | 14 | `Read, Grep, Glob, Bash, WebFetch, WebSearch, Skill` |
| `security-operations-reviewer` | Security review, credential exposure | 10 | `Read, Grep, Glob, WebFetch, WebSearch, Skill` |
| `cloud-platform-operator` | AWS, Azure, GCP diagnostics | 16 | `Read, Grep, Glob, Bash, WebFetch, WebSearch, Skill` |
| `kubernetes-operator` | K8s/K3s workloads, services, RBAC | 16 | `Read, Grep, Glob, Bash, WebFetch, WebSearch, Skill` |
| `database-operator` | DB availability, locks, replication | 16 | `Read, Grep, Glob, Bash, WebFetch, WebSearch, Skill` |
| `network-edge-operator` | Firewall, LB, proxy, DNS, gateway | 16 | `Read, Grep, Glob, Bash, WebFetch, WebSearch, Skill` |
| `release-cicd-operator` | CI/CD pipelines, deployments, artifacts | 14 | `Read, Grep, Glob, Bash, WebFetch, WebSearch, Skill` |
| `audit-evidence-collector` | Audit evidence, redaction, compliance | 12 | `Read, Grep, Glob, Bash, WebFetch, WebSearch, Skill` |

Each subagent inherits the project-wide safety model (`references/risk-levels.md`, `references/command-execution-protocol.md`) and preloads only its documented primary skills through the native Claude Code `skills` frontmatter. Native `tools` allowlists, `disallowedTools`, and `maxTurns` bound runtime capability; `Write` and `Edit` are denied to every role, while analytical roles also deny `Bash`.
Each definition ends with an explicit runtime-precedence block so a budget-exhausted handoff overrides the normal role output.
Other project skills remain available for on-demand discovery. See `subagents/` for full definitions.

## Native command guard

The eight executor roles with `Bash` carry a native `PreToolUse` hook that
invokes a shared deterministic Node.js validator from the Nori-installed
`command-driven-operations` skill. The four analytical roles remain shell-free.

The guard uses separate Bash and PowerShell lexers, builds the complete stage,
operator, redirect, and data-flow graph, and validates every stage against a
finite operational catalogue. Pipes are therefore analyzed rather than
blanket-blocked. Normal modes allow narrow reads and ask for bounded sensitive
reads and catalogued changes. `bypassPermissions` allows catalogued
non-destructive work; destructive work still asks. Unknown, ambiguous,
dynamic, unbounded, or exfiltrating calls deny with a redacted explanation.
Verbs must occupy their family-defined position, filters cannot add independent
file inputs, and log, scan, query, packet, and cloud-list bounds are checked
before authorization.

Profiles, agents, keychains, cached sessions, credential helpers, runtime
variables, and protected-file direct flows are preferred. A literal supplied
in conversation is already model/provider/transcript-visible. The guard
prevents additional disclosure and permits same-session, same-domain,
same-identity, same-transport reuse in `bypassPermissions`, while independently
re-evaluating every command. It never stores or derives a credential
identifier.

Mandatory static and installed-form validation:

```bash
node tests/run-command-guard-tests.mjs
python3 tests/test-command-guard-install-policy.py
bash tests/live-command-guard-smoke.sh --self-test
```

The real Claude Code/Nori harness is opt-in because it requires a configured
Linux/WSL environment with Bubblewrap and operator credentials:

```bash
bash tests/live-command-guard-smoke.sh --run-live
```

Observed runtime/model versions are recorded as evidence and are not package
requirements. See `docs/architecture/ADR-004-native-command-guard.md`.

## What changed in v0.11.0

- Added native `PreToolUse` hooks to the eight executor subagents and semantic source-to-installed validation of their shared guard path.
- Added strict event validation, separate Bash/PowerShell lexers, composition analysis, a finite infrastructure command catalogue, target binding, and mode-aware `allow`/`ask`/`deny` policy.
- Added redaction-before-normalization, stateless model-visible credential handling, direct protected-file flows, minimal append-only audit metadata, and fail-closed process behavior.
- Added 100% critical line/function/branch coverage, finite inventory/orphan checks, four property seeds, eleven killed security mutations, installed-form probes, and an opt-in OS-isolated live harness.
- Added ADR-004 and aligned model-facing execution/credential instructions without pinning Claude Code, Nori, Node.js, or the configured model.

## What changed in v0.10.0

- Added exact role-specific `maxTurns`, least-privilege tool allowlists, and critical `disallowedTools` to all 12 subagents.
- Removed `Bash` from incident coordination, change management, RCA, and security review; those roles delegate execution and evidence collection.
- Added cooperative turn budgets, per-tool rationales, external-query minimization, structured incomplete-work handoffs, and final output precedence.
- Added fail-closed runtime policy mutations, Nori-installed artifact comparison, schema tests for `type: skillset`, and an opt-in live Claude Code smoke harness.
- Added indexed ADRs for the P0-01 risk taxonomy, P0-02 skill preload, and P0-03 runtime controls.
- Preserved runtime portability through `model: inherit`; observed Claude Code, Nori, Node.js, and model identifiers remain test evidence rather than compatibility constraints.

## What changed in v0.9.1

- Completed a retroactive independent review of the v0.8.0 risk-taxonomy
  implementation and corrected all Important findings.
- Enforced exactly one canonical base risk level in explicit classifications,
  including nested skill content and scripts.
- Removed modifier-only and mixed-base classifications from container,
  Kubernetes, network probe, cloud, audit, vendor, and ITSM instructions.
- Added a shared control matrix for approval, validation, rollback, recovery,
  and compensating action requirements.
- Added mutation-style regression tests for unknown levels, modifier-only
  records, multiple bases, nested scripts, and false-positive resistance.
- Kept runtime selection portable without pinning Claude Code, Nori, or model
  versions.

## What changed in v0.9.0

- Preloaded each of the 12 subagents with its role-specific primary skills so domain instructions are present at startup without loading the full 24-skill catalog.
- Extended content validation to reject missing, empty, malformed, duplicated, unregistered, or documentation-divergent subagent skill preloads.
- Kept runtime selection portable through `model: inherit`, without pinning Claude Code, Nori, or model versions.

## What changed in v0.8.0

- Unified operational risk under four exclusive levels: `SAFE_READ_ONLY`, `LOW_RISK_CHANGE`, `DISRUPTIVE_CHANGE`, and `DESTRUCTIVE`.
- Added `EXTERNAL_SIDE_EFFECT` for tickets, comments, messages, approvals, CMDB relationships, and other externally persisted workflow actions.
- Added a deterministic highest-impact classification algorithm, explicit approval gates, and rollback-or-compensating-action handling.
- Reclassified ambiguous CI/CD, container, Kubernetes, database, PKI, monitoring, network-edge, and ITSM actions using the canonical vocabulary.
- Updated agent instructions, skills, subagents, slash commands, examples, and templates so Claude Code/Nori-compatible agents receive the same policy at every entry point.
- Extended content validation to reject deprecated or invented risk levels and require the complete canonical vocabulary in core policy artifacts.

## What changed in v0.7.0

- Strengthened troubleshooting methodology: hypothesis discipline (one command, one hypothesis), multi-layer evidence gathering, anti-thrashing mechanism, and backward tracing from symptom to original trigger — adapted from `systematic-debugging` and `root-cause-tracing` for infrastructure domains.
- `read-the-damn-docs` added as hard dependency — forces current documentation checks before acting on third-party infrastructure tools.
- Infrastructure troubleshooting and root cause analysis skills upgraded to v0.5.0.

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
- `DISRUPTIVE_CHANGE`
- `DESTRUCTIVE`

Operational modifiers include:

- `SENSITIVE_OUTPUT`
- `RESOURCE_INTENSIVE`
- `ACTIVE_PROBE`
- `PRIVILEGED`
- `REMOTE_SESSION_RISK`
- `EXTERNAL_SIDE_EFFECT`

Assign exactly one risk level based on the highest plausible impact, then add all applicable modifiers. SAFE_READ_ONLY commands may be executed automatically only when scoped, non-sensitive, and low load.
Sensitive or broad diagnostics require minimization, redaction, and sometimes approval. LOW_RISK_CHANGE, DISRUPTIVE_CHANGE, DESTRUCTIVE, and EXTERNAL_SIDE_EFFECT actions require explicit approval.

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

# Live-smoke parser only (no model/API consumption)
bash tests/live-subagent-runtime-smoke.sh --self-test

# Opt-in isolated Nori + Claude Code behavioral smoke
bash tests/live-subagent-runtime-smoke.sh

# Link validation (human-readable)
bash tests/validate-links.sh

# Link validation (machine-readable, for CI)
bash tests/validate-links.sh --json
```

CI runs all validators on every PR and push to main. See `.github/workflows/ci.yml`.

PowerShell parser validation requires a host with `pwsh` or Windows PowerShell installed.

## Docs

- [CHANGELOG](CHANGELOG.md)
- [Architecture decisions](docs/architecture/README.md)
- [ROADMAP](ROADMAP.md)
- [CONTRIBUTING](CONTRIBUTING.md)
- [SECURITY](SECURITY.md)
