# Example: Long validation task continuity ledger

## Situation

A multi-stage package validation is approaching the preventive compaction threshold while the feature branch remains under review.

## Objective and completion criteria

- Complete deterministic package validation.
- Preserve the approved design and privacy invariants.
- Stop before push, PR, or merge without the required gate.

## Decisions and exclusions

- Auto-compaction remains enabled at the operator-selected percentage.
- Browser automation is outside the current delivery.
- No absolute context-window value is assumed.

## Evidence references

- Branch: `agent/example-continuity`
- Current commit: `0123456`
- Package gate: running; final exit code not yet observed
- Design: `docs/superpowers/specs/example-design.md`

## Native task state

- Completed: design approval and isolated worktree
- Active: deterministic validation
- Pending: independent review and CI/Security

## Authorization state

Any credential reuse from before compaction requires fresh native approval because current proof is not retained.

## Risks and rollback

- Risk: reporting a partial gate as complete
- Control: wait for the process exit code and failure count
- Rollback: remove only owned local continuity settings

## Immediate next action

Read the native task list, wait for validation to finish, record the exit code, and continue only if the gate passes.
