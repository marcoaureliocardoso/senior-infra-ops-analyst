# Roadmap

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

- Add vendor-specific deep dives for Oracle, SQL Server Always On, PostgreSQL HA stacks, MySQL Group Replication, Redis Cluster, enterprise load balancers, and managed Kubernetes distributions.
- Add MCP/tool-specific adapters for ServiceNow, Jira Service Management, Zabbix API, Grafana API, GitHub/GitLab, and cloud provider support APIs.
- Add offline integration tests for each slash command and template.
- Add live link validation in CI where outbound network access is available.
- Add optional runnable labs using disposable containers or mock CLIs for safe skill testing.
