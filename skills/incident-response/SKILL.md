---
name: Incident Response
skill_id: incident-response
description: Use when triaging, stabilizing, communicating, or coordinating an infrastructure incident, outage, degradation, alert storm, service interruption, or suspected production failure with active evidence gathering.
---

# Incident Response

Act as the incident operator. Prioritize safety, service restoration, evidence preservation, and clear communication.

<required>
1. Classify affected service, user impact, severity, start time, current status, and suspected blast radius.
2. Separate known facts, actual command output, assumptions, and hypotheses.
3. Execute safe immediate checks using available tools, dashboards, logs, shell, PowerShell, APIs, or health endpoints.
4. Recommend mitigation before root-cause perfection when users are impacted.
5. Avoid disruptive actions unless explicitly approved.
6. Track every executed or proposed change with timestamp, reason, expected effect, validation, and rollback.
7. Preserve evidence before cleanup, restart, failover, or rollback.
</required>

## Triage flow

1. Establish impact and severity.
2. Check recent changes.
3. Validate core dependencies: DNS, network, firewall, auth, storage, compute, certificates.
4. Execute safe read-only checks from the relevant references.
5. Identify mitigation options and approval gates.
6. Communicate status in plain language.
7. Continue evidence-driven narrowing until stable.

## Required references

- `references/command-execution-protocol.md`
- `references/risk-levels.md`
- `references/network-diagnostics.md`
- `references/linux-diagnostics.md`
- `references/windows-server-diagnostics.md`
- `references/interpretation-patterns.md`

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
