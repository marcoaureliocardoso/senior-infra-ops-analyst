---
description: "Diagnose Kubernetes workload, service, ingress, storage, scheduling, RBAC, and cluster symptoms with scoped read-only commands."
allowed-tools: Task(subagent_type:kubernetes-operator)
---
# /k8s-triage

Purpose: diagnose Kubernetes workload, service, ingress, storage, scheduling, RBAC, or cluster symptoms with scoped read-only commands.

Expected input:
- cluster/context, namespace, workload/service/ingress, symptom, time window, recent deployment/change.

Behavior:
- Use `skills/kubernetes-operations/SKILL.md`.
- Use `skills/kubernetes-operations/templates/kubernetes-incident.md`.
- Use `references/kubernetes-operations.md` first; use `references/kubernetes-k3s.md` only for K3s-specific host/service checks.
- Do not run apply/edit/patch/delete/restart/scale/cordon/drain without explicit approval.

Example:
`/k8s-triage ns=academic workload=portal-web symptom="HTTP 503 after deployment"`

Output:
- Context and namespace
- Object status and recent events
- Logs/describe summary
- Service/ingress/storage/resource interpretation
- Risk-classified next action
