# Architecture Decision Records

This index is the versioned architectural history for implemented AI-first controls. Decisions describe the architecture that is actually enforced, not only the intended procedure.

| ADR | Status | Decision |
|---|---|---|
| [ADR-001](ADR-001-risk-taxonomy.md) | Accepted | Canonical operational risk taxonomy |
| [ADR-002](ADR-002-subagent-skill-preload.md) | Accepted | Focused native skill preload for subagents |
| [ADR-003](ADR-003-subagent-runtime-controls.md) | Accepted | Bounded, least-privilege subagent runtime |
| [ADR-004](ADR-004-native-command-guard.md) | Accepted | Native deterministic command authorization for executor subagents |
| [ADR-005](ADR-005-context-continuity-and-preventive-compaction.md) | Accepted | Native context continuity and preventive compaction |

New implemented solutions must add an ADR or explicitly supersede an existing one. A superseding ADR names the previous record and the index retains both entries.
