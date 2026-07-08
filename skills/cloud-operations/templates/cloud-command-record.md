# Cloud Command Record

Use this template when recording scoped AWS, Azure, or GCP read-only diagnostics.

## Scope

- Provider:
- Account/subscription/project:
- Region/zone/resource group:
- Target resource:
- Environment:
- Symptom:
- Time window:
- Operator/tool context:

## Identity and boundary confirmation

| Check | Command | Result | Interpretation |
|---|---|---|---|
| Current identity | `<aws sts get-caller-identity / az account show / gcloud auth list>` |  | Confirms account boundary before resource queries. |
| Current scope | `<region/project/subscription command>` |  | Prevents wrong-account/wrong-region evidence. |

## Commands executed

| Time UTC | Risk | Command | Scope limiter | Exit code | Evidence summary | Interpretation |
|---|---|---|---|---|---|---|
|  | SAFE_READ_ONLY + SENSITIVE_OUTPUT |  |  |  |  |  |

## Findings by layer

| Layer | Evidence | Likely meaning | Next safe check |
|---|---|---|---|
| Compute |  |  |  |
| Network |  |  |  |
| Identity/IAM |  |  |  |
| Storage/backup |  |  |  |
| Monitoring/logs |  |  |  |
| Quota/capacity |  |  |  |

## Approval-required actions

| Proposed action | Risk | Blast radius | Rollback | Validation command | Approval owner |
|---|---|---|---|---|---|
|  | STATE_CHANGING / DISRUPTIVE_CHANGE / DESTRUCTIVE |  |  |  |  |

## Redaction checklist

- Remove account IDs if not needed.
- Redact public IPs when sharing outside the support boundary.
- Redact IAM ARNs, user IDs, tokens, keys, request IDs when required.
- Do not paste secrets or bearer tokens from shell history or command lines.
