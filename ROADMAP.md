# Roadmap

## Completed in v0.4.4

- Added YAML frontmatter with operational descriptions to all 20 slash commands.

## Completed in v0.4.3

- Populated examples for original core skills.
- Added full related-reference coverage for original references.
- Added missing operator slash commands for SSH, load balancing, monitoring stack, web gateway, CI/CD, and ITSM workflows.
- Added cloud operations template and stronger cross-reference/content validation.
- Tightened safety classification and approval gates across original and Kubernetes/network references.

## Completed in v0.4.2

- Populated roadmap-domain examples with realistic, non-skeletal evidence records.
- Clarified expanded-domain reference labeling in `AGENTS.md`.
- Added validation checks for skeletal examples.

## Completed in v0.4.1

- Converted roadmap skills from generic wrappers into domain-specific operational skills.
- Added dedicated Kubernetes operations coverage beyond K3s host/service checks.
- Added examples for roadmap domain skills.
- Removed root template duplication and standardized template ownership under each skill.
- Deepened ITSM/CMDB and disaster recovery drill guidance.
- Added cross-reference sections across related references.

## Completed in v0.4.0

The previous roadmap domains received dedicated skills, references, and templates:

- database operations
- container runtime operations beyond Kubernetes control-plane checks
- load balancers and reverse proxies
- PKI and certificate lifecycle operations
- CI/CD operations
- monitoring stack operations: Prometheus, Grafana, Zabbix, ELK/Elastic/OpenSearch
- message queues
- web servers and application gateways
- SSH and privileged access management
- ITSM/CMDB workflows
- disaster recovery drills
- vendor escalation management
- audit and compliance evidence collection

## Future improvements

| Priority | Item | Owner | Notes |
|---|---|---|---|
| P1 | MCP/tool-specific adapters | Maintainer | ServiceNow, Jira Service Management, Zabbix API, Grafana API, GitHub/GitLab, cloud support APIs. |
| P1 | Offline functional tests | Maintainer | Exercise each slash command against mock evidence and expected output. |
| P2 | Vendor deep dives | Maintainer/contributors | Oracle, SQL Server Always On, PostgreSQL HA, MySQL Group Replication, Redis Cluster, enterprise LBs, managed Kubernetes. |
| P2 | Runnable labs | Contributors | Disposable containers or mock CLIs for safe skill testing. |
| P3 | External link maintenance | Maintainer | Scheduled CI link validation and stale-link replacement. |
