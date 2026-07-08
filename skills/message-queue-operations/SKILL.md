---
name: Message Queue Operations
description: Use when diagnosing RabbitMQ, Kafka, Redis Streams, broker health, queue depth, consumer lag, dead-letter queues, partition leadership, or message flow issues.
version: 0.4.1
last_updated: 2026-07-08
maintainer: Marco Aurelio Cardoso
triggers:
  - message-queue-operations
  - message queue operations
---

# Message Queue Operations

Use this skill when the operational domain materially changes the diagnostic order, evidence type, approval gate, or interpretation. The shared command-driven posture still applies, but the domain-specific reference and template are mandatory context.

<required>
1. Identify broker type, cluster, queue/topic/stream, producer, consumer group, message criticality, ordering/durability assumptions, and user impact.
2. Use `references/message-queues.md` for broker-specific read-only checks: queue depth, consumer count, lag, partitions, replicas, alarms, DLQ, and disk/memory pressure.
3. Cross-reference application gateway, database, CI/CD, and monitoring stack references when queue symptoms are downstream effects.
4. Treat message payloads, routing keys, queue names, consumer groups, broker URLs, and topic names as `SENSITIVE_OUTPUT`.
5. Run metadata and health checks before consuming, replaying, purging, resetting offsets, changing retention, or restarting brokers/consumers.
6. Interpret symptoms as producer outage, consumer failure, poison messages, broker resource alarm, partition leadership issue, network split, or downstream dependency failure.
7. Require approval before purge, replay, offset reset, retention change, rebalance intervention, broker restart, or DLQ redrive.
8. Classify lag and cluster-wide queries as potentially `RESOURCE_INTENSIVE`; bound by queue/topic, group, and time window.
9. Produce `skills/message-queue-operations/templates/queue-incident.md` with depth/lag evidence, producer/consumer status, risk, and gated remediation.
</required>

## Output

Return:
- Situation and scope
- Domain-specific command/evidence sequence
- Commands executed or explicitly not executed
- Observations and interpretation
- Risk classification and modifiers
- Recommended next action
- Approval gate, if needed
- Completed template artifact

## References

- `references/message-queues.md`
- `references/risk-levels.md`
- `references/command-execution-protocol.md`
- `references/diagnostic-order.md`
- `references/external-sources.md`
