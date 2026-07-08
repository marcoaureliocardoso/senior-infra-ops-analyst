# Example: RabbitMQ Queue Backlog

## Scenario

Background jobs are delayed. The application team reports that messages are entering RabbitMQ but processing is slow. Scope is read-only queue, consumer, broker, and node health diagnostics.

## Evidence sequence

| Step | Command/source | Risk | Observed result |
|---|---|---|---|
| List queues | `rabbitmqctl list_queues name messages messages_ready messages_unacknowledged consumers` | `SAFE_READ_ONLY + SENSITIVE_OUTPUT` | `email.dispatch` has 48k ready messages and 0 consumers. |
| Check consumers | Management API queue detail | `SAFE_READ_ONLY + SENSITIVE_OUTPUT` | Consumer count dropped to zero 18 minutes ago. |
| Check broker alarms | `rabbitmqctl alarms` | `SAFE_READ_ONLY` | No memory or disk alarm. |
| Check node health | `rabbitmq-diagnostics status` | `SAFE_READ_ONLY + SENSITIVE_OUTPUT` | Broker running, cluster partition not reported. |
| Check publish rate | Management UI/API metrics | `SAFE_READ_ONLY + SENSITIVE_OUTPUT` | Publish rate normal; delivery rate zero. |

## Interpretation

The queue backlog is caused by absent consumers, not broker resource alarm or cluster outage. The next diagnostic branch is worker deployment/runtime health, not queue purge or broker restart.

## Safe next actions

- Identify the worker service that consumes `email.dispatch`.
- Check worker deployment/container/runtime logs.
- Confirm whether the last deployment or credential rotation coincides with consumer drop.

## Approval gate

Do not purge queues, requeue messages, restart the broker, or change queue policies without explicit approval. These actions can lose data, duplicate processing, or widen impact.
