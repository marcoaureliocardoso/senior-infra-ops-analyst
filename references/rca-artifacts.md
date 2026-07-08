# RCA Artifacts Reference

Use this to define RCA outputs consistently.

## Evidence map

An evidence map links conclusions to facts.

| Field | Meaning |
|---|---|
| Finding/claim | What the RCA says happened. |
| Evidence source | Log, metric, command output, ticket, config diff, alert, message. |
| Timestamp/window | When the evidence applies. |
| Observed fact | What was actually observed. |
| Confidence | high, medium, low. |
| Gap/assumption | What is still unknown. |

Rules:

- Do not put raw secrets, tokens, personal data, or excessive logs in the RCA.
- Prefer summarized evidence with exact timestamps and source names.
- Mark correlation vs causation.

## Action table

An action table converts lessons into trackable work.

| Field | Meaning |
|---|---|
| Action | Concrete corrective/preventive item. |
| Failure mode addressed | What recurrence path this reduces. |
| Type | prevent, detect, respond, recover, document. |
| Owner | Responsible person/team if known. |
| Priority | critical, high, medium, low. |
| Effort | small, medium, large. |
| Due date | Date or proposed window. |
| Verification method | How to prove the action worked. |

Good action: "Add DNS health check for resolver X and alert after 5m failure; verify with synthetic query test."

Weak action: "Improve monitoring."

## Timeline entry format

- Timestamp and timezone
- Event
- Source
- Confidence
- Impact or relevance

## RCA quality gates

- Every major claim has evidence or is labeled as assumption.
- The RCA separates trigger, root cause, and contributing factors.
- Actions cover prevention, detection, response, and recovery.
- At least one action has a validation method.
- The document is blameless and system-focused.

## Related references

- `references/incident-severity.md`
- `references/diagnostic-order.md`
- `references/itsm-cmdb-workflows.md`
- `references/audit-compliance-evidence.md`
