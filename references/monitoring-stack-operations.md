# Monitoring Stack Operations Reference

Use this for Prometheus, Alertmanager, Grafana, Zabbix, ELK/Elastic, and OpenSearch operations: missing metrics, broken dashboards, alert floods, storage pressure, query failures, and log ingestion issues.

## Safety rules

- Treat labels, logs, dashboard variables, datasource URLs, and alert annotations as `SENSITIVE_OUTPUT`.
- Start with health/status APIs and bounded queries.
- Avoid broad log searches, expensive PromQL/range queries, index deletes, retention changes, silences, and alert rule edits without approval.
- A silence is state-changing and can hide outages; require approval and expiration.

## Read-only checks

### Prometheus / Alertmanager

```bash
curl -s http://<prometheus>:9090/-/ready
curl -s http://<prometheus>:9090/api/v1/status/config
curl -s 'http://<prometheus>:9090/api/v1/query?query=up'
curl -s http://<alertmanager>:9093/api/v2/status
```

Interpretation:
- `up == 0` -> target unreachable/scrape failure.
- Ready false -> TSDB/config/startup issue.
- Many alerts with same dependency -> upstream/root service issue.

### Grafana

```bash
curl -s http://<grafana>:3000/api/health
curl -s -H "Authorization: Bearer <redacted>" http://<grafana>:3000/api/datasources
```

### Zabbix

```bash
zabbix_server -V
zabbix_get -s <agent> -k agent.ping
```

### Elastic / OpenSearch

```bash
curl -s http://<cluster>:9200/_cluster/health
curl -s http://<cluster>:9200/_cat/indices?v
curl -s http://<cluster>:9200/_cat/nodes?v
```

Interpretation:
- Red cluster -> unavailable primary shards.
- Yellow cluster -> replicas unassigned.
- Disk watermark warnings -> shard allocation/storage pressure.

## Risk mapping

- Health and status APIs: `SAFE_READ_ONLY`.
- Log queries and config dumps: `SAFE_READ_ONLY` + `SENSITIVE_OUTPUT`; broad queries may be `RESOURCE_INTENSIVE`.
- Silences, rule edits, datasource changes, index deletion: `STATE_CHANGING` or `DESTRUCTIVE`.

## Evidence to capture

Affected monitor, datasource, query, target status, alert labels after redaction, storage state, ingestion rate, last config change, and monitoring blind spots.

## Related references

- `references/observability-slo-sli.md`
- `references/kubernetes-operations.md`
- `references/audit-compliance-evidence.md`
