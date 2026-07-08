# Alert Rule Template

Use this to design an actionable alert. Alerts should represent user impact or urgent risk, not mere curiosity.

| Field | Value | Guidance |
|---|---|---|
| Alert name |  | Include service + symptom. |
| Service |  |  |
| Symptom |  | What is actually wrong? |
| User impact |  | Who is affected and how? |
| SLI/SLO link |  | Link to SLO if this is reliability-related. |
| Threshold |  | Include units and comparator. |
| Duration/window |  | Avoid instant flapping unless truly urgent. |
| Severity | page / ticket / info | Tie severity to urgency. |
| Owner |  | Must be actionable by this owner. |
| First diagnostic command |  | Use safe read-only first command. |
| Runbook |  | Link/name. |
| Escalation |  | When and to whom. |
| Suppression/deduplication rule |  | Prevent alert storms. |
| Validation test |  | How to prove the alert works. |

## Anti-patterns

- Alert with no owner.
- Alert that says “check logs” without first commands.
- Alert that fires after users complain but before operators have evidence.
- Alert based on host-only metrics when the service has no user impact.
