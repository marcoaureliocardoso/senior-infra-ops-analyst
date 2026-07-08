---
name: Kubernetes Operations
description: Use when diagnosing Kubernetes clusters, workloads, services, ingress, storage, RBAC, scheduling, autoscaling, network policy, control-plane, or platform symptoms beyond K3s-only checks.
version: 0.4.4
last_updated: 2026-07-08
maintainer: Marco Aurelio Cardoso
triggers:
  - kubernetes-operations
  - kubernetes operations
---

# Kubernetes Operations

Use this skill when the operational domain materially changes the diagnostic order, evidence type, approval gate, or interpretation. The shared command-driven posture still applies, but the domain-specific reference and template are mandatory context.

<required>
1. Confirm cluster context, namespace, workload, service, ingress, storage class, node pool, environment, recent changes, and production impact before commands.
2. Use `references/kubernetes-operations.md` for canonical Kubernetes checks and `references/kubernetes-k3s.md` only for K3s-specific host/service details.
3. Cross-reference container runtime, load balancer, PKI, monitoring stack, cloud, storage/backup, and network references based on the failing layer.
4. Treat manifests, logs, pod descriptions, events, node names, labels, secrets references, image names, and ingress hosts as `SENSITIVE_OUTPUT`.
5. Run scoped read-only checks first: context, namespace objects, workload status, events, pod describe, logs with tail/time, service endpoints, ingress, nodes, and resource usage.
6. Interpret failures by layer: scheduling, image pull, probe, config/secret mount, service selector, ingress/TLS, DNS, network policy, storage/PVC, node pressure, or control plane.
7. Require approval before apply/edit/patch/delete, rollout restart, scale, cordon/drain, secret/config change, storage manipulation, or cluster component restart.
8. Classify cluster-wide queries and logs as `RESOURCE_INTENSIVE`; limit by namespace, label, pod, container, and time window whenever possible.
9. Produce `skills/kubernetes-operations/templates/kubernetes-incident.md` with namespace, objects, events, logs summary, layer diagnosis, gated actions, and validation.
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

- `references/kubernetes-operations.md`
- `references/risk-levels.md`
- `references/command-execution-protocol.md`
- `references/diagnostic-order.md`
- `references/external-sources.md`
