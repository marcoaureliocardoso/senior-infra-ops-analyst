---
name: Container Runtime Operations
description: Use when diagnosing Docker, Podman, containerd, CRI-O, image, log, resource, port, or runtime failures outside Kubernetes control-plane checks.
version: 0.4.4
last_updated: 2026-07-08
maintainer: Marco Aurelio Cardoso
triggers:
  - container-runtime-operations
  - container runtime operations
---

# Container Runtime Operations

Use this skill when the operational domain materially changes the diagnostic order, evidence type, approval gate, or interpretation. The shared command-driven posture still applies, but the domain-specific reference and template are mandatory context.

<required>
1. Identify runtime, host, container/image, compose/unit/orchestrator context, namespace, network mode, storage driver, and impact scope.
2. Distinguish runtime-level issues from Kubernetes/control-plane issues; if pods/controllers are involved, cross-check `references/kubernetes-operations.md`.
3. Use `references/container-runtime-operations.md` for bounded checks: runtime info, container state, recent logs, image metadata, mounts, ports, networks, and resource pressure.
4. Treat container logs, environment variables, labels, image names, volume paths, and registry endpoints as `SENSITIVE_OUTPUT`.
5. Prefer `inspect`, `ps`, `logs --tail`, `stats --no-stream`, and service status before exec, restart, prune, pull, or image removal.
6. Interpret failures by layer: image pull/auth, entrypoint crash, healthcheck failure, port binding conflict, filesystem mount, cgroup pressure, DNS, or host firewall.
7. Classify exec into containers, restarts, image pulls, network connects, volume operations, and prune/delete actions before approval.
8. Use shared risk and command-execution references for modifiers such as `RESOURCE_INTENSIVE`, `ACTIVE_PROBE`, and `PRIVILEGED`.
9. Produce `skills/container-runtime-operations/templates/container-runtime-triage.md` with runtime, container state, logs summary, hypothesis, next safe checks, and gated actions.
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

- `references/container-runtime-operations.md`
- `references/risk-levels.md`
- `references/command-execution-protocol.md`
- `references/diagnostic-order.md`
- `references/external-sources.md`
