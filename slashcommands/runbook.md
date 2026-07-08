# /runbook

Use the Runbook Authoring and Command Driven Operations skills.

## Purpose

Create an executable operational runbook with command order, risk, interpretation, rollback, and validation.

## Expected input

- Procedure name
- Target system
- Trigger condition
- Required access/tools
- Safety constraints
- Success criteria

## Behavior

1. Define when to use and when not to use the runbook.
2. List prerequisites and approvals.
3. Provide commands in safe execution order.
4. Include expected/abnormal signals and interpretation.
5. Include rollback, escalation, and evidence retention.

## Example

`/runbook safely validate and restart a failed internal DNS resolver`

## Output

Runbook with steps, command records, decision points, rollback, validation, escalation, and post-checks.
