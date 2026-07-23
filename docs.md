# Noridoc: senior-infra-ops-analyst

Path: `senior-infra-ops-analyst/`

## Overview

A command-driven skillset that personifies a Senior Infrastructure Operations Analyst for safe, evidence-based hybrid infrastructure operations. Designed for operators who have terminal, shell, SSH, or API access and need structured diagnostics, incident triage, change planning, RCA, and runbook authoring — all gated by an explicit safety model.

24 skills, 20 slash commands, 12 subagents, and 33 reference documents cover the full operational surface: Linux, Windows Server, networking, pfSense, VMware, Kubernetes/K3s, cloud (AWS/Azure/GCP), databases, containers, load balancers, PKI, CI/CD, monitoring stacks, message queues, web gateways, SSH/privileged access, ITSM/CMDB workflows, disaster recovery, vendor escalation, and audit evidence.

Version: 0.9.0 | Author: Marco Aurelio Cardoso | License: MIT

## Directory structure

```text
senior-infra-ops-analyst/
├── AGENTS.md                  # Main agent instructions
├── nori.json                  # Skillset manifest (skills, references, subagents)
├── profile.json               # Nori profile metadata
├── skills.json                # Skill tier map
├── .nori-version               # Version and registry tracking
├── docs.md                    # This file
├── README.md                  # Project readme
├── CHANGELOG.md               # Release history
├── ROADMAP.md                 # Planned improvements
├── skills/                    # 24 operational skills
│   └── <skill>/
│       ├── SKILL.md           # Skill definition
│       ├── nori.json          # Per-skill metadata
│       ├── examples/          # Realistic evidence examples
│       └── templates/         # Reusable artifacts
├── subagents/                 # 12 role-focused subagents with primary-skill preload
├── slashcommands/             # 20 operator slash commands
├── references/                # 33 domain reference documents
└── tests/                     # Validators and CI scripts
```

### Skills

| Skill | Description |
|-------|-------------|
| `command-driven-operations` | Safe terminal/SSH/PowerShell/API command execution with risk classification |
| `cloud-operations` | Scoped AWS/Azure/GCP read-only diagnostics |
| `incident-response` | Incident triage, stabilization, communication, and coordination |
| `infrastructure-troubleshooting` | Linux, Windows, network, DNS, DHCP, firewall, VPN, virtualization diagnostics |
| `change-management` | Change planning, review, approval, execution, and documentation |
| `root-cause-analysis` | Blameless post-incident RCA with timeline and contributing factors |
| `automation-safe-operations` | Safe automation script authoring and review |
| `monitoring-observability` | Monitoring, logging, alerting, dashboard, SLO/SLI design and review |
| `runbook-authoring` | Runbook and SOP creation with guided templates |
| `capacity-and-risk-review` | Capacity, technical debt, operational risk, and lifecycle review |
| `database-operations` | Database availability, sessions, locks, replication, storage, and backups |
| `container-runtime-operations` | Docker, Podman, containerd, CRI-O diagnostics outside Kubernetes |
| `kubernetes-operations` | Cluster, workload, service, ingress, storage, RBAC, and scheduling triage |
| `load-balancer-operations` | NGINX, HAProxy, Apache reverse proxy, and cloud LB diagnostics |
| `pki-certificate-operations` | Certificate expiry, trust chain, SAN mismatch, TLS handshake diagnostics |
| `cicd-operations` | Pipeline failures, runner capacity, deployment gates, and artifact issues |
| `monitoring-stack-operations` | Prometheus, Grafana, Zabbix, ELK/Elastic/OpenSearch diagnostics |
| `message-queue-operations` | RabbitMQ, Kafka, Redis Streams broker health and consumer diagnostics |
| `web-gateway-operations` | IIS, Apache, NGINX, application gateway, virtual host, and WAF diagnostics |
| `ssh-privileged-access-operations` | SSH reachability, authentication, sudo/PAM, bastion, and key management |
| `itsm-cmdb-workflows` | Incident, change, problem, CMDB, CI ownership, and impact analysis |
| `disaster-recovery-drills` | Tabletop exercises, restore tests, failover readiness, and RTO/RPO validation |
| `vendor-escalation-management` | Support escalation packages for vendors, ISPs, and cloud providers |
| `audit-compliance-evidence` | Audit evidence collection, redaction, organization, and explanation |

### Slash commands

- `/ops-diagnose` — Evidence-driven diagnostics using the canonical diagnostic order
- `/incident-triage` — Incident worksheet with SEV model
- `/change-plan` — Change plan from `skills/change-management/templates/`
- `/rca` — Root cause analysis from `skills/root-cause-analysis/templates/`
- `/cloud-check` — Scoped AWS/Azure/GCP read-only checks
- `/runbook` — Runbook/SOP drafting from `skills/runbook-authoring/templates/`
- `/db-triage` — Database availability, sessions, locks, replication, storage
- `/container-runtime-triage` — Container runtime diagnostics outside Kubernetes
- `/k8s-triage` — Kubernetes workload, service, ingress, storage, RBAC triage
- `/cert-check` — TLS certificate chain, expiry, SAN, trust validation
- `/queue-triage` — Queue depth, consumer lag, broker health
- `/dr-drill` — Disaster recovery drill planning and evidence
- `/audit-evidence` — Audit/compliance evidence collection
- `/vendor-escalate` — Vendor support escalation package
- `/ssh-triage` — SSH, bastion, PAM, sudo, and key diagnostics
- `/lb-triage` — Load balancer and reverse proxy health/routing/TLS
- `/monitoring-stack-triage` — Prometheus/Grafana/Zabbix/ELK/OpenSearch triage
- `/web-gateway-triage` — Web server, application gateway, WAF, and upstream triage
- `/cicd-triage` — CI/CD pipeline, runner, artifact, and deployment-gate triage
- `/itsm-update` — ITSM/CMDB factual update and impact analysis

### Subagents

Each subagent preloads only the primary skills listed in its definition through Claude Code's native `skills` frontmatter. The focused preload provides role knowledge at startup while leaving non-primary project skills available for on-demand discovery.

| Subagent | Role |
|----------|------|
| `diagnostic-operator` | Initial evidence collection and diagnostic triage |
| `incident-commander` | Incident coordination, communication, and stabilization |
| `change-manager` | Change planning, risk assessment, and rollback design |
| `rca-facilitator` | Blameless post-incident root cause analysis |
| `cloud-platform-operator` | Scoped cloud infrastructure diagnostics |
| `database-operator` | Database-specific diagnostics and health assessment |
| `kubernetes-operator` | Kubernetes cluster and workload diagnostics |
| `network-edge-operator` | Firewall, load balancer, and edge networking triage |
| `observability-sre` | SLO/SLI evaluation, alert review, and dashboard analysis |
| `release-cicd-operator` | Pipeline, deployment gate, and artifact diagnostics |
| `security-operations-reviewer` | Security posture review and access audit |
| `audit-evidence-collector` | Structured audit and compliance evidence collection |

### References (by domain)

**Core operations:**
`command-execution-protocol.md`, `risk-levels.md`, `diagnostic-order.md`, `interpretation-patterns.md`, `incident-severity.md`, `rca-artifacts.md`, `external-sources.md`

**Platform diagnostics:**
`linux-diagnostics.md`, `windows-server-diagnostics.md`, `network-diagnostics.md`, `dns-dhcp.md`, `active-directory.md`, `pfsense-operations.md`, `vmware-operations.md`

**Infrastructure services:**
`database-operations.md`, `container-runtime-operations.md`, `kubernetes-operations.md`, `kubernetes-k3s.md`, `load-balancers-reverse-proxies.md`, `pki-certificate-lifecycle.md`, `message-queues.md`, `web-servers-application-gateways.md`, `ssh-privileged-access.md`, `storage-backup.md`

**Platform engineering:**
`cloud-operations.md`, `cicd-operations.md`, `monitoring-stack-operations.md`, `observability-slo-sli.md`, `capacity-risk-taxonomy.md`

**Governance:**
`itsm-cmdb-workflows.md`, `disaster-recovery-drills.md`, `vendor-escalation.md`, `audit-compliance-evidence.md`

### Safety model

Commands are classified into risk tiers with operational modifiers:

**Risk tiers:**
- `SAFE_READ_ONLY` — Scoped, non-sensitive, low-load commands. Auto-executable.
- `LOW_RISK_CHANGE` — Limited, reversible or compensable, non-disruptive state changes. Requires explicit approval.
- `DISRUPTIVE_CHANGE` — Broad service disruption possible. Requires approval and rollback plan.
- `DESTRUCTIVE` — Data/configuration loss, critical safeguard removal, or recovery impairment possible. Requires approval, rollback, and verification.

**Operational modifiers:**
- `SENSITIVE_OUTPUT` — Output contains secrets, tokens, or PII. Requires redaction.
- `RESOURCE_INTENSIVE` — High CPU, memory, or I/O. Scope and throttle.
- `ACTIVE_PROBE` — Sends traffic to external systems. Minimize and target narrowly.
- `PRIVILEGED` — Requires elevated access. Verify scope and necessity.
- `REMOTE_SESSION_RISK` — Operates over SSH or remote session. Connection state risk.
- `EXTERNAL_SIDE_EFFECT` — Changes tickets, messages, comments, approvals, CMDB, or other external workflow state. Requires exact-target approval.

Assign exactly one risk tier based on the highest plausible impact, then add all applicable operational modifiers.

### Integration

This skillset is designed for the Nori agent ecosystem. When installed, skills are loaded into `~/.claude/skills/`, subagents into `~/.claude/agents/`, and slash commands into `~/.claude/commands/`.
Each subagent uses native `skills` frontmatter to preload its role-specific instructions. The `AGENTS.md` file provides the main workflow instructions — dual-mode operation (copilot and full-send) with structured checkpoints for safe infrastructure operations.
