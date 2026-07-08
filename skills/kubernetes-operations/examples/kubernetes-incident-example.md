# Example: Kubernetes Service Returning 503

## Situation

Users receive HTTP 503 from `portal.example.local`. Scope is namespace `academic`, service `portal-web`, and its ingress path. The operator has read-only Kubernetes access.

## Evidence sequence

| Step | Command | Risk | Observed result |
|---|---|---|---|
| Confirm context | `kubectl config current-context` | `SAFE_READ_ONLY` | Expected production cluster context confirmed. |
| List workload state | `kubectl get pods -n academic -o wide` | `SAFE_READ_ONLY + SENSITIVE_OUTPUT` | Two `portal-web` pods are Running but not Ready. |
| Inspect pod events | `kubectl describe pod -n academic <portal-pod>` | `SAFE_READ_ONLY + SENSITIVE_OUTPUT` | Readiness probe fails on `/healthz`. |
| Read bounded logs | `kubectl logs -n academic deploy/portal-web --tail=200` | `SAFE_READ_ONLY + SENSITIVE_OUTPUT` | Database connection timeouts. |
| Check service endpoints | `kubectl get endpoints portal-web -n academic` | `SAFE_READ_ONLY` | No ready endpoints. |
| Check ingress route | `kubectl describe ingress -n academic portal-web` | `SAFE_READ_ONLY + SENSITIVE_OUTPUT` | Ingress points to expected service and port. |

## Interpretation

Ingress and service routing are probably correct; there are no ready backend endpoints because readiness probes fail. The next diagnostic branch is database reachability from the application context, not load balancer reconfiguration.

## Safe next actions

1. Check recent rollout history with `kubectl rollout history deployment/portal-web -n academic`.
2. Verify whether database/network policy changes occurred in the incident window.
3. Compare failing readiness probe with the application health-check contract.
4. Prepare a mitigation option, such as rollback or config correction, but do not execute it without approval.

## Approval gate

Do not restart, scale, patch, roll back, delete pods, or edit ConfigMaps/Secrets without explicit approval. Those actions are `DISRUPTIVE_CHANGE` or may destroy evidence.
