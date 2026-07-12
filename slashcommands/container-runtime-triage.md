---
description: "Diagnose Docker, Podman, or containerd runtime failures outside Kubernetes control-plane checks."
allowed-tools: Task(subagent_type:diagnostic-operator)
---
# /container-runtime-triage

Purpose: diagnose Docker/Podman/containerd runtime failures outside Kubernetes control-plane checks.

Expected input:
- runtime, host, container/image, symptom, time window.

Behavior:
- Use `skills/container-runtime-operations/SKILL.md`.
- Use `skills/container-runtime-operations/templates/container-runtime-triage.md`.
- Do not exec/restart/prune without approval.
