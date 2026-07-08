---
name: Incident Response
skill_id: incident-response
description: Use when triaging, stabilizing, communicating, or coordinating an infrastructure incident, outage, degradation, alert storm, service interruption, or suspected production failure with active evidence gathering.
version: 0.4.4
last_updated: 2026-07-08
maintainer: Marco Aurelio Cardoso
triggers:
  - incident
  - outage
  - degradation
  - alert storm
  - production failure
---

# Incident Response

Act as the incident operator. Prioritize safety, service restoration, evidence preservation, and clear communication.

<required>
1. Classify affected service, user impact, severity, start time, current status, and suspected blast radius.
2. Separate known facts, actual command output, assumptions, and hypotheses.
3. Execute safe immediate checks using available tools, dashboards, logs, shell, PowerShell, APIs, or health endpoints.
4. Recommend mitigation before root-cause perfection when users are impacted.
5. Mitigation urgency does not override approval gates: disruptive mitigation requires an approval packet from `references/incident-severity.md`.
6. Avoid disruptive actions unless explicitly approved.
7. Track every executed or proposed change with timestamp, reason, expected effect, validation, and rollback.
8. Preserve evidence before cleanup, restart, failover, or rollback.
</required>

## Triage flow

Use the incident overlay in `references/diagnostic-order.md`:

1. Establish impact, severity, blast radius, and communication cadence.
2. Stabilize safely using approved mitigation when needed.
3. Follow the canonical diagnostic order for evidence collection.
4. Identify mitigation options and approval gates.
5. Communicate status in plain language.
6. Continue evidence-driven narrowing until stable.


## Required references

- `references/risk-levels.md`
- `references/incident-severity.md`
- `references/diagnostic-order.md`
- `skills/incident-response/templates/incident-worksheet.md`


## Output

Return:

- Incident summary
- Severity and impact
- Commands executed
- Evidence observed
- Hypotheses ranked by likelihood
- Mitigation options
- Approval-required actions
- Rollback notes
- Stakeholder update draft
