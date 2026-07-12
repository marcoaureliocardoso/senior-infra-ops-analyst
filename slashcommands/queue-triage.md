---
description: "Diagnose queue backlog, consumer lag, broker alarms, partition leadership, and message flow interruptions."
allowed-tools: Task(subagent_type:diagnostic-operator)
---
# /queue-triage

Purpose: diagnose queue backlog, consumer lag, broker alarms, partition leadership, and message flow interruption.

Expected input:
- broker type, queue/topic/stream, producer, consumer group, impact, time window.

Behavior:
- Use `skills/message-queue-operations/SKILL.md`.
- Use `skills/message-queue-operations/templates/queue-incident.md`.
- Do not purge/replay/reset offsets without approval.
