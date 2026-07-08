# /change-plan

Use the Change Management and Command Driven Operations skills.

## Purpose

Create a production-grade change plan and run safe pre-checks when tools exist.

## Expected input

- Objective
- Target systems
- Environment and maintenance window
- Implementation approach
- Known dependencies
- Desired validation and rollback constraints

## Behavior

1. Define scope and blast radius.
2. Classify change risk.
3. Execute safe pre-checks only.
4. Produce step-by-step implementation plan.
5. Include validation, rollback, communications, freeze conditions, and evidence to retain.

## Example

`/change-plan upgrade RAM and SSD on lab PCs; preserve Windows activation and user profiles; rollback with original disk`

## Output

Objective, risk, pre-check commands, implementation steps, validation, rollback, communications, go/no-go criteria, evidence archive.
