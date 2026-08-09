# ADR-005: Context continuity and preventive compaction

- Status: Accepted
- Date: 2026-08-08
- Scope: P0-04A continuity across Claude Code context compaction

## Context

Long operational sessions can exhaust their effective context or lose the
objective, decisions, evidence references, authorization state, runtime state,
and next action during compaction. Nori distributes project instructions,
skills, subagents, and hook definitions, but local Claude Code settings remain
operator-owned and must not be replaced as a whole.

Claude Code supplies native auto-compaction, compact instructions, task lists,
status lines, lifecycle hooks, context inspection, and capability-dependent
tool search. Provider and gateway window reporting can vary, so the package
cannot pin a Claude Code, Nori, model, provider, or absolute window version.
Compaction can retain a session identifier while discarding the context that
justified credential reuse; reuse therefore needs an explicit invalidation
boundary.

## Decision

Use native Claude Code mechanisms discovered at runtime, with a small
package-owned settings merger and content-free evidence normalizer. Keep
auto-compaction enabled, set `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` to `72` when the
operator has not selected a value from 70 through 75, and never configure
`CLAUDE_CODE_AUTO_COMPACT_WINDOW` as the normal default.

## Implemented architecture

The root instructions contain short Compact Instructions and require the native
task list for long work. The `context-continuity` skill provides:

- an idempotent `--check`, `--apply`, and `--remove-owned` configurator for
  project-local or user-local settings;
- an opt-in `--status-line` showing the documented context percentage or a
  neutral unknown state;
- non-blocking `PreCompact` and `PostCompact` hooks distributed to all 12
  subagents through `{{skills_dir}}`;
- synchronous invalidation of pending and active credential reuse, with
  fail-safe all-binding invalidation when the session identity is unverifiable;
- static and runtime inventory of skills, subagents, MCPs, task capabilities,
  context percentages, tool search, and window evidence.

The configurator records a sidecar containing only values it owns. Apply and
rollback preserve unrelated scalar settings, environment values, hook arrays,
and changes made by the operator after the initial application. It rejects
disablement, an out-of-range percentage, a pre-existing status line when opt-in
was requested, unsafe files, duplicate JSON keys, and conflicting owned values.

## Enforcement points

- `AGENTS.md` preserves objective and next action through native tasks and
  invalidates authorization that cannot be proved after compaction.
- `configure-context-continuity.mjs` merges only owned local settings and keeps
  the normal configuration percentage-based.
- `compact-hook.mjs` and its bounded launcher always return success to Claude
  Code, retain no transcript, prompt, response, compact summary, command,
  header, credential, or secret, and require fresh approval on degradation.
- `binding-store.mjs` makes credential reuse empty for the exact compacted
  session, or for every bounded state file when identity is unavailable.
- `context-inventory.mjs` emits numeric-only measurements, booleans, bounded
  identifiers, and closed reason codes. It refuses an output-file argument.
- Source and installed-form validators require canonical hook definitions and
  byte-equal continuity scripts without adding the skill body to every
  subagent preload.

`CLAUDE_CODE_AUTO_COMPACT_WINDOW` is permitted only in a disposable diagnostic
after numeric evidence reports `WINDOW_REPORTING_DIVERGENCE` and the operator
approves the exception. The real DeepSeek route must first run without it.

## Alternatives rejected

- Instructions alone cannot set a threshold or deterministically invalidate
  persisted authorization state.
- A checked-in replacement settings file can overwrite operator preferences.
- A package-owned scalar status line can silently replace another status line.
- Blocking compaction can strand the session.
- Transcript or compact-summary checkpoints create a second secret-bearing
  conversation artifact.
- A default absolute-window override can hide incorrect gateway reporting.

## Validation evidence

Deterministic evidence includes strict settings merge/rollback tests, status-line
null handling, compact-hook and launcher failure paths, authorization
invalidation, 100% critical command-guard coverage, security mutations,
canonical source/installed hook validation for 12 subagents, inventory tests for
25 skills and 12 subagents, and a content-free parser self-test covering task,
compaction, tool-search, MCP, and window reason-code branches.

The 2026-08-09 isolated run through the operator-configured DeepSeek route
passed Nori installation and preservation, main plus 12 role context probes,
repeated skill and bounded-output probes, the one-tool MCP fixture, an explicit
ToolSearch probe, focused and unfocused manual compaction, authorization
invalidation, loopback mock threshold behavior, `/resume`, actual `/rewind`,
post-rewind task/context/authorization verification, and isolated `/clear`.
Both manual compactions emitted ordered real `PreCompact/PostCompact` pairs.
The automatic probe then reached 8% native context usage with 70,000 bounded
synthetic units and a process-scoped 5% threshold, but did not complete an
ordered automatic `PreCompact/PostCompact` cycle before the ten-minute limit.
The live gate therefore remains blocked, emitted no passing final report, and
deleted all content-bearing captures. Independent review and CI/Security remain
separate gates on the reviewed head.

## Consequences and limitations

Local configuration requires an explicit operator action. The default `72`
reserves recovery margin without claiming a token count, and Claude Code may
still compact earlier. The live automatic probe may use a process-scoped 5%
threshold solely to bound test time and cost. If a runtime exposes native
`--autocompact`, the probe selects `auto` explicitly; older runtimes remain
capability-driven. The real route never receives an automatic absolute fallback.
The loopback mock proves a threshold-behavior change with a measured boundary.
The runtime's 1,000,000-token label agrees with current official DeepSeek model
documentation, so an absolute real-route diagnostic currently lacks its
required incorrect-reporting evidence and is not eligible.

Hooks do not block native compaction. If invalidation cannot be verified, reuse
is conservatively removed and the next credential-bearing call requires fresh
native approval. Numeric-only evidence supports comparison but cannot
reconstruct the conversation. Tool search remains a runtime capability and may
honestly report unavailable on the configured gateway.

P0-04B browser automation is outside this decision except for its future
interfaces and measurable context impact.

## Forward compatibility

The package probes current runtime capabilities and records observed versions as
evidence, not constraints. New Claude Code fields are ignored unless they can be
reduced to the closed retained schema. Future task tools, MCP discovery, or tool
search implementations may add reason-code branches without relaxing the
prohibition on raw content. An absolute-window override remains exceptional
even if provider defaults or context sizes change.
