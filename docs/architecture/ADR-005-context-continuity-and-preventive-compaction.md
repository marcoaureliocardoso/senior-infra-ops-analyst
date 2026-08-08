# ADR-005: Context continuity and preventive compaction
- Status: Accepted
- Date: 2026-08-08
- Scope: P0-04A continuity across Claude Code context compaction
## Context
Long operational sessions can exhaust the effective context window or lose the
current objective, decisions, evidence, authorization state, runtime state, and
next actions during compaction. The package already distributes root
instructions, skills, subagents, and command-authorization hooks through Nori,
but Nori does not safely own arbitrary operator settings or environment values.
Its managed instruction and hook loaders preserve surrounding operator content,
while its scalar status-line setting and whole-file settings rollback can
replace or discard later preferences.
Claude Code provides native percentage-based auto-compaction, compact
instructions, persistent task lists, status lines, compaction hooks, context
inspection, and capability-dependent MCP tool search. Provider and gateway
window reporting can vary, so a model, provider, version, or absolute window
cannot be the package contract.
P0-04 also permits bounded reuse of an approved literal credential using
non-secret session-scoped binding state. Compaction can retain the native
session identifier while removing the model context that justified reuse, so
that binding must be explicitly invalidated.
## Decision
Adopt a hybrid native architecture:
1. Add short Compact Instructions and semantic native task-list guidance to the
   Nori-managed root instructions.
2. Provide an explicit idempotent configurator that merges only P0-04A-owned
   keys into local Claude Code settings and supports read-only check,
   apply, and owned-only rollback.
3. Keep auto-compaction enabled and default
   `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` to configurable value `72`, preserving an
   existing value from 70 through 75. Treat disablement or an out-of-range value
   as a visible conflict.
4. Never set `CLAUDE_CODE_AUTO_COMPACT_WINDOW` during normal configuration. Use
   it only after a controlled diagnostic demonstrates incorrect effective
   window reporting and the operator approves the evidence-gated exception.
5. Offer a stateless native status line as an explicit opt-in and never silently
   replace an existing operator or Nori status line.
6. Install strict `PreCompact` and `PostCompact` hooks that always exit `0`,
   never persist conversation content or secrets, and retain only bounded
   non-secret invalidation metadata.
7. Synchronously invalidate pending and active credential-reuse bindings in
   `PreCompact`; verify or retry in `PostCompact`. Missing proof after compaction
   requires fresh native approval.
8. Measure instructions, skills, subagents, MCPs, and tool search separately
   using counts, bytes, percentages, booleans, and reason codes only.
9. Validate behavior through deterministic fixtures, an isolated Nori install,
   and real Claude Code sessions using the operator-configured DeepSeek route.
   Runtime versions and identifiers are observations, not requirements.
The detailed contracts and acceptance criteria are in
`docs/superpowers/specs/2026-08-08-p0-04a-context-continuity-design.md`.
## Alternatives rejected
- Instructions alone: cannot set a threshold, surface usage, or invalidate
  persisted authorization state deterministically.
- Checked-in replacement settings: can overwrite preferences and cannot provide
  safe per-key rollback.
- Nori scalar status line and whole-file restore as the sole mechanism: cannot
  prove preservation of operator changes made after installation.
- Default absolute-window override: embeds a provider assumption and can hide a
  gateway reporting defect.
- Blocking compaction when invalidation fails: can strand a session and violates
  the non-blocking-hook requirement.
- Persisting transcript or compact-summary checkpoints: expands secret and
  personal-data exposure and creates a second transcript-like artifact.
## Consequences
The package gains a small explicit setup step because local settings are
operator-owned. In return, configuration is inspectable, idempotent,
conflict-aware, and reversible per owned key.
The 72-percent default reserves recovery margin without encoding a token count.
Claude Code may still compact earlier, and a live test may use a lower
process-scoped value to bound test cost.
Compaction never depends on a package hook succeeding, but credential reuse
does. A failed or unverifiable invalidation produces degraded-continuity
evidence and requires fresh approval rather than preserving a stale grant.
Context measurements are intentionally less convenient than transcript capture:
they can compare costs and capabilities but cannot reconstruct conversation
content. This limitation is a privacy and secret-handling invariant.
MCP tool search remains capability-based. The package records whether the
configured DeepSeek route supports it and does not force an unsupported
`tool_reference` path.
## Validation obligations
Implementation must prove owned-only settings merge and rollback, non-blocking
content-free hooks, authorization invalidation, task-list continuity, status-line
null handling, numeric-only context evidence, installed Nori preservation, and
real manual and automatic compaction through DeepSeek. Complete package,
independent-review, CI, and security gates are required before merge.
This ADR records the approved design. Its validation evidence must be updated to
describe implemented behavior before P0-04A can be marked complete.
