# Architecture Decision Records

This index is the versioned architectural history for implemented AI-first controls. Decisions describe the architecture that is actually enforced, not only the intended procedure.

| ADR | Status | Decision |
|---|---|---|
| [ADR-001](ADR-001-risk-taxonomy.md) | Accepted | Canonical operational risk taxonomy |
| [ADR-002](ADR-002-subagent-skill-preload.md) | Accepted | Focused native skill preload for subagents |
| [ADR-003](ADR-003-subagent-runtime-controls.md) | Accepted | Bounded, least-privilege subagent runtime |
| [ADR-004](ADR-004-native-command-guard.md) | Accepted | Native deterministic command authorization for executor subagents |
| [ADR-005](ADR-005-context-continuity-and-preventive-compaction.md) | Accepted | Native context continuity and preventive compaction |
| [ADR-006](ADR-006-canonical-nori-package.md) | Accepted | Canonical manifest and reproducible Nori package boundary |
| [ADR-007](ADR-007-first-class-subagents.md) | Accepted | First-class, independently versioned Nori subagent packages |
| [ADR-008](ADR-008-native-execution-boundary.md) | Accepted | Fail-closed native execution routing for main sessions and executor fallback |
| [ADR-009](ADR-009-global-prompt-injection-defense.md) | Accepted | Deterministic prompt-injection boundaries and runtime compatibility reporting |

New implemented solutions must add an ADR or explicitly supersede an existing one. A superseding ADR names the previous record and the index retains both entries.
