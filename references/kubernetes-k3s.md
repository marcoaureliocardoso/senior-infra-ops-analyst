# Kubernetes / K3S Diagnostics

Use for Kubernetes and K3S clusters, workloads, services, ingress, nodes, pods, events, and resource pressure.

## Safety rules

- `kubectl get`, `describe`, `logs`, and `top` are generally SAFE_READ_ONLY, but `describe` and `logs` can expose sensitive configuration, secret names, headers, tokens accidentally printed by apps, or personal data.
- `kubectl delete`, `rollout restart`, `scale`, `cordon`, `drain`, `apply`, `patch`, and `edit` change state and require approval in production.
- Never delete pods as a first diagnostic step without checking events/logs and impact.
- Confirm namespace and context before commands.

## 1. Safe context checks

| Risk | Command | Verifies | Interpretation |
|---|---|---|---|
| SAFE_READ_ONLY | `kubectl config current-context` | Target cluster | Wrong context can cause wrong-cluster actions. |
| SAFE_READ_ONLY | `kubectl get nodes -o wide` | Node health/versions/IPs | NotReady or version skew narrows issue. |
| SAFE_READ_ONLY | `kubectl get namespaces` | Namespace inventory | Confirms expected namespace. |
| SAFE_READ_ONLY | `kubectl get events -A --sort-by=.lastTimestamp | tail -50` | Recent cluster events | Scheduling, image pull, probe, node events. |

## 2. Workload checks

| Risk | Command | Verifies | Interpretation |
|---|---|---|---|
| SAFE_READ_ONLY | `kubectl get pods -n <ns> -o wide` | Pod state/node/IP | Pending/CrashLoop/ImagePull errors guide next step. |
| SAFE_READ_ONLY | `kubectl describe pod -n <ns> <pod>` | Pod events/spec | Probe, mount, scheduling, image errors. |
| SAFE_READ_ONLY | `kubectl logs -n <ns> <pod> --tail=200` | App/container logs | App startup/runtime error. |
| SAFE_READ_ONLY | `kubectl logs -n <ns> <pod> -c <container> --previous --tail=200` | Previous crashed container | Critical for CrashLoopBackOff. |
| SAFE_READ_ONLY | `kubectl get deploy,statefulset,daemonset -n <ns> -o wide` | Controller state | Desired vs available mismatch. |
| DISRUPTIVE_CHANGE | `kubectl rollout restart deployment/<name> -n <ns>` | Restart workload | Requires approval; can interrupt users. |

## 3. Service and ingress

| Risk | Command | Verifies | Interpretation |
|---|---|---|---|
| SAFE_READ_ONLY | `kubectl get svc,endpoints,endpointslice -n <ns>` | Service-to-pod mapping | Empty endpoints means selector/pod readiness issue. |
| SAFE_READ_ONLY | `kubectl describe svc -n <ns> <svc>` | Service selector/ports | Selector/targetPort mismatch breaks traffic. |
| SAFE_READ_ONLY | `kubectl get ingress -A -o wide` | Ingress routes | Wrong host/address/class clue. |
| SAFE_READ_ONLY | `kubectl describe ingress -n <ns> <ingress>` | Ingress details/events | TLS/class/routing errors. |

## 4. Resources

| Risk | Command | Verifies | Interpretation |
|---|---|---|---|
| SAFE_READ_ONLY | `kubectl top nodes` | Node CPU/memory | Requires metrics server; saturation clue. |
| SAFE_READ_ONLY | `kubectl top pods -A --sort-by=cpu` | Pod CPU usage | Heavy consumers. |
| SAFE_READ_ONLY | `kubectl top pods -A --sort-by=memory` | Pod memory usage | OOM risk. |
| SAFE_READ_ONLY | `kubectl describe node <node>` | Node pressure/events | DiskPressure/MemoryPressure/PIDPressure. |

## 5. K3S host-level checks

| Risk | Command | Verifies | Interpretation |
|---|---|---|---|
| SAFE_READ_ONLY | `systemctl status k3s --no-pager` | K3S server service | Failed/inactive explains cluster API issue. |
| SAFE_READ_ONLY | `journalctl -u k3s --since "1 hour ago" --no-pager | tail -200` | K3S server logs | API, datastore, network plugin errors. |
| SAFE_READ_ONLY | `systemctl status k3s-agent --no-pager` | K3S agent service | Worker node health. |
| SAFE_READ_ONLY | `journalctl -u k3s-agent --since "1 hour ago" --no-pager | tail -200` | Agent logs | Node/container runtime issues. |
| DISRUPTIVE_CHANGE | `systemctl restart k3s` | Restart control plane | Requires approval; cluster API interruption. |

## 6. Diagnostic order for app unavailable

1. Confirm context and namespace.
2. Get pods, controllers, events.
3. Check pod describe and logs.
4. Check service endpoints.
5. Check ingress/TLS/routes.
6. Check node pressure and resources.
7. Check K3S service logs if cluster-level symptoms.
8. Present remediation options requiring approval.


## Sensitivity and control-plane load notes

- `kubectl logs` is SENSITIVE_OUTPUT. Use `--tail`, namespace, pod, container, and time-window filters.
- `kubectl get events -A` and cluster-wide queries can be noisy on large clusters. Prefer a namespace when known.
- Avoid cluster-wide log collection or repeated polling during control-plane instability without approval.
