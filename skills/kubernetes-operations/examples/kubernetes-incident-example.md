# Example: Kubernetes Service Returning 503

## Situation

Users receive HTTP 503 from `portal.example.local`. Scope is namespace `academic`, service `portal-web`.

## Evidence sequence

1. `kubectl config current-context` confirmed the expected production cluster.
2. `kubectl get pods -n academic -o wide` showed two `portal-web` pods running but not Ready.
3. `kubectl describe pod` showed readiness probe failures on `/healthz`.
4. `kubectl logs --tail=200` showed database connection timeouts.
5. `kubectl get endpoints portal-web -n academic` showed no ready endpoints.

## Interpretation

Ingress and service routing are probably correct; there are no ready backend endpoints because readiness probes fail. The next diagnostic branch is database reachability from the application context, not load balancer reconfiguration.

## Approval gate

Do not restart or scale the deployment yet. If a rollout restart is proposed, classify it as `DISRUPTIVE_CHANGE` and require approval.
