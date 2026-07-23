# Kubernetes Operations Reference

Use this for general Kubernetes clusters: workloads, scheduling, services, ingress, storage, RBAC, network policy, autoscaling, node pressure, cluster events, and control-plane symptoms. Use `references/kubernetes-k3s.md` only for K3s-specific host-level service checks.

## Safety rules

- Confirm `kubectl config current-context`, namespace, and target object before any command.
- `kubectl get`, `describe`, `logs`, and `top` are read-only but often `SENSITIVE_OUTPUT`; logs and broad cluster queries can also be `RESOURCE_INTENSIVE`.
- Never run `apply`, `edit`, `patch`, `delete`, `rollout restart`, `scale`, `cordon`, `drain`, secret changes, or storage manipulation without explicit approval.
- Prefer namespace, label, pod, container, and time filters over cluster-wide commands.
- Do not use pod deletion as a first diagnostic step; collect events, describe output, and bounded logs first.

## Canonical Kubernetes diagnostic order

1. Context and scope: current context, namespace, object names, recent deployment/change.
2. Workload state: deployments/statefulsets/daemonsets/jobs, replica availability, rollout state.
3. Pod state: phase, restart count, node placement, image pull, events, probes.
4. Logs and events: bounded by namespace, pod, container, and tail/time.
5. Service path: service selector, endpoints/endpointslices, ports, ingress/gateway route.
6. Platform resources: node readiness, pressure, taints/tolerations, quotas, limits, HPA/VPA.
7. Storage and config: PVC/PV, storage class, ConfigMap/Secret mount errors, projected volumes.
8. Network and security: DNS, network policies, service mesh, RBAC authorization errors.
9. Control plane/provider: API availability, controller symptoms, cloud load balancer integration.

## Read-only commands

### Context and inventory

```bash
kubectl config current-context
kubectl get ns
kubectl get all -n <ns>
kubectl get events -n <ns> --sort-by=.lastTimestamp | tail -50
kubectl api-resources --verbs=list --namespaced -o name
kubectl get crd
```

Interpretation:
- Wrong context/namespace invalidates all later evidence.
- Recent events often explain scheduling, image, probe, mount, and quota failures.

### Workloads and pods

```bash
kubectl get deploy,statefulset,daemonset,job,cronjob -n <ns> -o wide
kubectl rollout status deployment/<name> -n <ns>
kubectl get pods -n <ns> -o wide
kubectl describe pod -n <ns> <pod>
kubectl logs -n <ns> <pod> -c <container> --tail=200
kubectl logs -n <ns> <pod> -c <container> --previous --tail=200
```

Interpretation:
- `Pending` usually points to scheduling, quota, PVC, taints, or node pressure.
- `ImagePullBackOff` points to registry, tag, auth, DNS, or network.
- `CrashLoopBackOff` needs current and previous logs plus probe/events.
- Available replicas below desired narrows to rollout, readiness, resources, or dependency failure.

### Service, ingress, and gateway path

```bash
kubectl get svc,endpoints,endpointslice -n <ns> -o wide
kubectl describe svc -n <ns> <service>
kubectl get ingress -n <ns> -o wide
kubectl describe ingress -n <ns> <ingress>
kubectl get gateway,httproute -n <ns> 2>/dev/null || true
```

Interpretation:
- Empty endpoints means selector mismatch, pods not Ready, or wrong namespace.
- Ingress address missing suggests controller/cloud integration problem.
- TLS errors often require `references/pki-certificate-lifecycle.md`.

### Resources, scheduling, and storage

```bash
kubectl top nodes
kubectl top pods -n <ns> --sort-by=memory
kubectl describe node <node>
kubectl get quota,limitrange -n <ns>
kubectl get hpa,poddisruptionbudget -n <ns>
kubectl get pvc,pv -n <ns>
kubectl describe pvc -n <ns> <pvc>
```

Interpretation:
- `MemoryPressure`, `DiskPressure`, or quota failures can make app symptoms look like application bugs.
- PVC pending/mount errors usually require storage class, provisioner, and node event checks.

### RBAC and policy checks

```bash
kubectl auth can-i <verb> <resource> -n <ns> --as <user-or-sa>
kubectl get role,rolebinding,clusterrole,clusterrolebinding -n <ns>
kubectl auth can-i get pods -n <ns>
kubectl get networkpolicy -n <ns>
kubectl get mutatingwebhookconfiguration,validatingwebhookconfiguration
```

Interpretation:
- RBAC denial appears as forbidden errors in controllers, operators, jobs, and apps.
- Network policies can break service-to-service traffic while pods and services look healthy.

## Risk mapping

- Scoped `get`: `SAFE_READ_ONLY`, often `SENSITIVE_OUTPUT`.
- `describe`, `logs`, `events`: `SAFE_READ_ONLY` + `SENSITIVE_OUTPUT`; broad scope such as `-A`, high-cardinality event streams, or large log windows can be `RESOURCE_INTENSIVE`.
- `top`: `SAFE_READ_ONLY` + `SENSITIVE_OUTPUT`; cluster-wide or sorted queries can be `RESOURCE_INTENSIVE`; requires metrics server and may fail if unavailable.
- `auth can-i`: `SAFE_READ_ONLY` + `SENSITIVE_OUTPUT` when users/service accounts are named.
- A narrowly scoped, non-mutating `exec` is at least `LOW_RISK_CHANGE` +
  `REMOTE_SESSION_RISK`; the invoked command inherits any higher plausible
  base level and applicable modifiers.
- Port-forward is `LOW_RISK_CHANGE` + `ACTIVE_PROBE` +
  `REMOTE_SESSION_RISK`; bind locally, limit duration, and identify the exact
  service and port.
- A temporary debug pod is `LOW_RISK_CHANGE`; add `PRIVILEGED` when elevated
  access is requested and raise the base to `DISRUPTIVE_CHANGE` when the pod
  can affect shared capacity, policy, traffic, or workloads.
- Require explicit approval for `exec`, port-forward, and temporary debug pods.
- `apply`, `patch`, `edit`, `scale`, and `cordon`: `LOW_RISK_CHANGE` when narrowly scoped and non-disruptive; otherwise `DISRUPTIVE_CHANGE`.
- `rollout restart` and `drain`: `DISRUPTIVE_CHANGE`. All listed changes require explicit approval.
- `kubectl delete namespace <ns>`, `kubectl delete pvc`, and broad deletes: `DESTRUCTIVE`; require formal approval, recovery evidence, and rollback/restore plan.

## Evidence to capture

Cluster/context, namespace, workload/controller, pod state, events, logs summary, service endpoints, ingress route, node/resource state, recent deployments, image tag, configuration source, risk classification, and validation command.

## Related references

- `references/container-runtime-operations.md` for Docker/containerd/CRI layer symptoms.
- `references/kubernetes-k3s.md` for K3s service and host-level specifics.
- `references/load-balancers-reverse-proxies.md` for ingress/LB symptoms.
- `references/pki-certificate-lifecycle.md` for TLS and certificate path issues.
- `references/monitoring-stack-operations.md` for Prometheus/Grafana/Kubernetes observability issues.
- `references/storage-backup.md` for PV/PVC/storage/backup concerns.
