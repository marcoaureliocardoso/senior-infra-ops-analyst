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

The package-owned status line reads the same child environment configured for
native auto-compaction. Only ASCII integer thresholds from 70 through 75 are
accepted; missing or invalid values fall back to 72. It compares the unrounded
native `used_percentage`, warns only when usage is strictly greater, and does
not infer the warning from `remaining_percentage`. The conditional second line
is a deliberate exception to the compact one-line presentation. It is
stateless, performs no command submission, and does not disable or replace the
native automatic path. Because status-line installation is opt-in, an inherited
operator or Nori renderer remains unchanged and does not receive this warning.

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
after either numeric evidence reports `WINDOW_REPORTING_DIVERGENCE` or an
operator-provided value exactly equals the native runtime capacity. Both forms
require separate operator approval. The exact-match form affects only the real
automatic-probe child and never persists to settings. The real DeepSeek route
must first run without it.

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
null handling, strict unrounded threshold comparison, all preserved 70-75%
thresholds, invalid-threshold fallback, executable output and no-artifact
behavior, compact-hook and launcher failure paths, authorization
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

The 2026-08-12 post-repair rerun used the exact ordered manual hook checks and
again reached 8% in the automatic scenario without a completed ordered
automatic `PreCompact`/`PostCompact` pair before the bound. It therefore
exited `BLOCKED`, emitted no passing report, applied no absolute override to
the real route, and deleted content-bearing captures. Implementation review
and all CI/Security checks passed on `67956e3`; the automatic live acceptance
criterion remains unmet.

Three operator-approved confirmed-window diagnostics then attempted to make the
already observed 1,000,000-token capacity explicit only for the automatic child.
Those historical runs matched a generic `[1m]` footer label. Independent review
showed that label was insufficient structural capacity evidence, so it no longer
satisfies the gate. The repaired design requires one consistent value from
Claude Code's documented native status-line
`context_window.context_window_size` field; generic model/footer labels in the
PTY capture cannot satisfy it. The first historical run exposed that the filler
incorrectly reused a different session's percentage; the
second exposed that a large PTY write was not guaranteed to complete. Both
defects were repaired with deterministic regressions. After full bounded PTY
delivery was proven, the final real run still observed only 3% and no completed
ordered automatic pair before the ten-minute bound. The technique is therefore
permitted only as an operator-authorized compatibility diagnostic after the
stricter native-field gate passes. Its historical result is inconclusive, the
stricter route has not been used to claim acceptance, and the automatic live
acceptance criterion remains unmet.

## Consequences and limitations

Local configuration requires an explicit operator action. The default `72`
reserves recovery margin without claiming a token count, and Claude Code may
still compact earlier. The live automatic probe may use a process-scoped 5%
threshold solely to bound test time and cost. If a runtime exposes native
`--autocompact`, the probe selects `auto` explicitly; older runtimes remain
capability-driven. The real route never receives an automatic absolute fallback.
The loopback mock proves a threshold-behavior change with a measured boundary.
The runtime's generic 1,000,000-token label agrees with current official
DeepSeek model documentation but is not capacity evidence and does not justify
a divergence override. Only the documented native status-line capacity field
can qualify the separate exact-match diagnostic after explicit operator
approval. That diagnostic does not make the value a production default or
satisfy acceptance without a real completed ordered automatic pair.

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
