# Message Queue Operations Reference

Use this for RabbitMQ, Kafka, Redis Streams, queue backlog, consumer lag, broker health, partition leadership, dead-letter growth, and message flow interruption.

## Safety rules

- Treat queue names, topics, message samples, routing keys, consumer groups, and headers as `SENSITIVE_OUTPUT`.
- Start with health, backlog, lag, and cluster metadata.
- Do not purge, requeue, replay, delete topic/queue, reset offsets, or move messages without explicit approval and business owner alignment.
- Never display message payloads unless explicitly authorized and redacted.

## Read-only checks

### RabbitMQ

```bash
rabbitmq-diagnostics status
rabbitmq-diagnostics alarms
rabbitmqctl list_queues name messages_ready messages_unacknowledged consumers state
rabbitmqctl list_connections name user state channels recv_oct send_oct
rabbitmqctl list_consumers
```

Interpretation:
- `messages_ready` rising with consumers zero -> consumer outage.
- `messages_unacknowledged` high -> slow/stuck consumers.
- Memory/disk alarm -> broker throttling or blocked publishers.

### Kafka

```bash
kafka-topics.sh --bootstrap-server <broker> --describe
kafka-consumer-groups.sh --bootstrap-server <broker> --all-groups --describe
kafka-broker-api-versions.sh --bootstrap-server <broker>
```

Interpretation:
- Under-replicated partitions -> broker/storage/network issue.
- Consumer lag rising -> downstream consumer capacity or error.
- No leader -> partition unavailable.

### Redis Streams

```bash
redis-cli XINFO STREAM <stream>
redis-cli XINFO GROUPS <stream>
redis-cli XINFO CONSUMERS <stream> <group>
```


### Additional Kafka checks

```bash
kafka-consumer-groups.sh --bootstrap-server <broker> --group <group> --describe
kafka-acls.sh --bootstrap-server <broker> --list
kafka-configs.sh --bootstrap-server <broker> --describe --entity-type topics --entity-name <topic>
```

### Additional RabbitMQ checks

```bash
rabbitmq-diagnostics check_running
rabbitmqctl list_channels name user connection messages_unacknowledged
```

Risk: `SAFE_READ_ONLY` + `SENSITIVE_OUTPUT`; broker-wide channel/group listings can be `RESOURCE_INTENSIVE` in large environments.

### Managed and alternative queues

For Amazon MSK, Azure Service Bus, Google Pub/Sub, NATS, and Pulsar, prefer scoped queue/topic/subscription health, consumer lag/backlog, permission, and quota checks. Do not purge, replay, reset offsets, or alter retention without approval.

## Risk mapping

- Queue/topic/lag listing: `SAFE_READ_ONLY` + `SENSITIVE_OUTPUT`.
- Payload sampling: `SENSITIVE_OUTPUT`; approval required.
- Purge/replay/reset offsets/delete: `DESTRUCTIVE` or `STATE_CHANGING`.

## Evidence to capture

Broker/cluster, queue/topic, lag/backlog, consumers, partitions/leaders, alarm state, oldest message age, error logs, and owner/service mapping.

## Related references

- `references/database-operations.md`
- `references/monitoring-stack-operations.md`
- `references/disaster-recovery-drills.md`
