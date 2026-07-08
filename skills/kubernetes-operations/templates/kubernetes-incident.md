# Kubernetes Incident Template

## Scope

- Cluster/context:
- Namespace:
- Workload/service/ingress:
- Environment:
- Impact:
- Recent change/deployment:

## Read-only evidence

| Layer | Command/source | Observation | Interpretation | Risk/modifiers |
|---|---|---|---|---|
| Context | `kubectl config current-context` |  |  | SAFE_READ_ONLY + SENSITIVE_OUTPUT |
| Workload | `kubectl get deploy,pods -n <ns> -o wide` |  |  | SAFE_READ_ONLY |
| Events | `kubectl get events -n <ns> --sort-by=.lastTimestamp` |  |  | SAFE_READ_ONLY + SENSITIVE_OUTPUT |
| Logs | `kubectl logs -n <ns> <pod> --tail=200` |  |  | SAFE_READ_ONLY + SENSITIVE_OUTPUT |
| Service path | `kubectl get svc,endpoints,endpointslice -n <ns>` |  |  | SAFE_READ_ONLY + SENSITIVE_OUTPUT |

## Layer diagnosis

- Scheduling:
- Image/runtime:
- Probe/readiness:
- Service/endpoints:
- Ingress/LB/TLS:
- DNS/network policy:
- Storage/config/secret:
- Node/control plane:

## Gated actions

| Proposed action | Risk | Approval required | Rollback | Validation |
|---|---|---:|---|---|
|  |  | Yes/No |  |  |

## Final recommendation

State the safest next action, why it follows from evidence, and what should be validated after execution.
