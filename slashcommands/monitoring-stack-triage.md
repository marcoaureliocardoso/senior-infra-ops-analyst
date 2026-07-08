# /monitoring-stack-triage

Purpose: diagnose Prometheus, Grafana, Zabbix, ELK/Elastic/OpenSearch, alerting, scraping, dashboard, or log pipeline issues.

Expected input:
- tool, target/dashboard/alert, symptom, time window, affected service.

Behavior:
- Use `skills/monitoring-stack-operations/SKILL.md`.
- Use `skills/monitoring-stack-operations/templates/monitoring-stack-incident.md`.
- Treat metrics labels, logs, dashboards, API tokens, and topology as sensitive.
- Do not silence alerts, delete indices, change scrape config, restart collectors, or mutate dashboards without approval.

Example:
`/monitoring-stack-triage Prometheus target api01 is down and Grafana panels show no data since 14:05`
