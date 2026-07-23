# Command Record

Use this for every executed or proposed command. Separate observed output from interpretation.

| Field | Value |
|---|---|
| Timestamp |  |
| Operator/Agent |  |
| Target |  |
| Environment | production / staging / lab / unknown |
| Command |  |
| Risk | SAFE_READ_ONLY / LOW_RISK_CHANGE / DISRUPTIVE_CHANGE / DESTRUCTIVE |
| Modifiers | SENSITIVE_OUTPUT / RESOURCE_INTENSIVE / ACTIVE_PROBE / PRIVILEGED / REMOTE_SESSION_RISK / EXTERNAL_SIDE_EFFECT / none |
| Purpose | What hypothesis does this test? |
| Approval status | not required / requested / approved / denied |
| Output summary | Short factual summary; redact secrets and personal data. |
| Interpretation | What does the output confirm or refute? |
| Next action |  |

For `EXTERNAL_SIDE_EFFECT`, record the exact external target, intended content/change, approval evidence, and rollback or compensating action.

## Example

| Field | Value |
|---|---|
| Timestamp | 2026-07-08 10:15 BRT |
| Target | dns01 |
| Command | `dig intranet.example A` |
| Risk | SAFE_READ_ONLY |
| Modifiers | ACTIVE_PROBE |
| Purpose | Check whether the resolver returns the expected A record. |
| Output summary | Resolver returned NXDOMAIN. |
| Interpretation | DNS path works, but the record is missing or wrong in the queried zone. |
| Next action | Compare zone file/authoritative resolver before changing records. |

## Interpretation

Explain what the output confirms or refutes.
