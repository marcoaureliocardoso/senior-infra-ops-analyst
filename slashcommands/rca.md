# /rca

Use the Root Cause Analysis skill.

## Purpose

Create a blameless RCA from evidence, not guesses.

## Expected input

- Incident summary
- Timeline or approximate window
- Alerts, logs, command outputs, change records, tickets, messages
- User impact
- Recovery action taken

## Behavior

1. Build timeline with timestamp/source/confidence.
2. Separate trigger, root cause, contributing factors, and impact.
3. Create an evidence map.
4. Create an action table.
5. Mark assumptions and open questions.

## Example

`/rca internet outage on campus; backup link did not take over; recovered after manual gateway change`

## Output

RCA draft, evidence map, action table, open questions, validation plan.
