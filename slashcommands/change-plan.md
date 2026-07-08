# /change-plan

Purpose: produce an approval-ready infrastructure change plan.

Use:

```text
/change-plan Replace firewall rule for backup repository access during maintenance window
```

Inputs expected:
- objective
- target systems
- affected services/users
- maintenance window
- rollback or restore point
- known dependencies

Behavior:
- Use `skills/change-management/SKILL.md`.
- Use `templates/change-plan.md` as the output structure.
- Use `references/risk-levels.md` for risk and modifiers.
- Execute only safe pre-checks when tool access exists.
- Stop before state-changing steps until approval is explicit.

Output: completed change plan with risk, pre-checks, implementation, validation, rollback, backout conditions, and post-change monitoring.
