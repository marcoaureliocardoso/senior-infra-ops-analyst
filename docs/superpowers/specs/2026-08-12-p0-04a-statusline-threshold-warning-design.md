# P0-04A Status-Line Threshold Warning Design

## Context

The continuity status line currently renders one neutral percentage line. The
configured auto-compaction threshold is advisory to Claude Code rather than a
package-enforced ceiling. If native automatic compaction does not begin when
`used_percentage` crosses that threshold, the operator needs a visible manual
recovery suggestion that consumes no model context and performs no action.

The operator approved a status-line warning rather than automatic command
submission or an operating-system notification.

Native automatic compaction remains enabled and remains the primary path. The
warning is a visual fallback only; it neither replaces nor disables the planned
automatic trigger.

## Decision

Keep the existing first line unchanged. When the native numeric
`context_window.used_percentage` is strictly greater than the effective
auto-compaction threshold, append this second line:

```text
Suggested: /compact Preserve objective, decisions, evidence locations, operational state, blockers, authorizations requiring revalidation, and immediate next action.
```

The comparison uses the unrounded native percentage. Equality does not warn.
The first line continues to round the displayed percentage exactly as it does
today. The warning therefore describes the threshold condition without
claiming that compaction failed or that no native compaction is in progress.

## Effective Threshold

Read `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` from the status-line process environment.
Accept only an ASCII integer from 70 through 75. Missing, malformed, fractional,
or out-of-range input falls back to the package default of 72. Do not infer a
threshold from an absolute context-window size.

The renderer remains compatible with its existing `remaining_percentage`
fallback for the first line. The warning, however, requires a valid native
`used_percentage`, as requested; it is not inferred from remaining percentage.

## Data Flow and Privacy

Claude Code invokes the status-line command with its documented JSON on stdin.
The renderer reads only `context_window.used_percentage` and, for the existing
neutral first line, `remaining_percentage`. It reads the threshold environment
key, writes one or two display lines to stdout, and exits zero.

The warning:

- never submits `/compact`, sends terminal input, or changes conversation state;
- never writes files, network messages, notifications, transcript content, or
  deduplication state;
- remains visible on every refresh while the valid percentage is above the
  threshold;
- disappears after usage is no longer above the threshold or becomes
  unavailable after compaction.

Malformed or oversized status input continues to degrade to `ctx --` without a
warning and without blocking Claude Code.

## Alternatives Rejected

- Automatically submit `/compact`: changes conversation state without a fresh
  operator decision and risks racing native compaction.
- Desktop notification: platform-specific, can repeat on every refresh, and
  requires state or side effects to suppress spam.
- Persist a one-shot warning marker: unnecessary state and conflicts with the
  approved stateless status-line design.
- Hard-code 72 in the comparison: ignores preserved operator choices from 70
  through 75.

## Test Strategy

Use TDD against the real renderer and executable entrypoint:

1. `used_percentage == threshold` retains one line and does not warn.
2. A fractional or integer percentage strictly above threshold renders the
   exact suggestion as a second line.
3. Preserved thresholds from 70 through 75 control the comparison.
4. Missing, malformed, fractional, and out-of-range thresholds fall back to 72.
5. `remaining_percentage` alone preserves the first-line fallback without
   emitting the warning.
6. Malformed and oversized JSON remains non-blocking and neutral.
7. The executable creates no local artifact and emits no stderr.
8. The complete deterministic package gate, independent review, and PR
   CI/Security checks remain required.

## Acceptance Criteria

- The exact suggestion appears only when valid native `used_percentage` is
  strictly greater than the effective configured threshold.
- Native automatic compaction remains enabled and unchanged.
- Existing percentage and neutral-state behavior remains compatible.
- The status line stays local, stateless, content-free, non-blocking, and
  action-free.
- Documentation explains that the warning is advisory and manual compaction
  remains an operator action.
