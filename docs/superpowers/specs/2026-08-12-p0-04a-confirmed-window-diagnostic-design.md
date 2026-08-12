# P0-04A Confirmed-Window Diagnostic Design

## Context

The real DeepSeek validation twice observed 8 percent context use while the
automatic-compaction process had `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=5`, but no
ordered automatic `PreCompact`/`PostCompact` pair occurred. The runtime and
provider documentation both report a 1,000,000-token window, so the existing
incorrect-window exception does not apply.

Current Claude Code defect reports indicate that percentage auto-compaction can
be skipped when the window source remains implicit even if the reported window
is correct. The operator approved one diagnostic that makes the already
observed capacity explicit without lowering or persisting it.

## Decision

Extend only the opt-in live harness with
`--confirmed-window-diagnostic <tokens>`. The option is valid only with
`--run-live`. Before the automatic scenario, a disposable status-line observer
must read Claude Code's documented native
`context_window.context_window_size` JSON field and retain only numeric capacity
and percentage events. The harness requires one consistent observed capacity
and exact equality with the operator-provided integer. A mismatch, missing or
conflicting native capacity, duplicate option, invalid integer, or use in
self-test mode exits `BLOCKED` before the provider diagnostic. A generic model
or footer label in the PTY capture is not capacity evidence.

For the automatic child process only, pass both:

- `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=5`; and
- `CLAUDE_CODE_AUTO_COMPACT_WINDOW=<confirmed native capacity>`.

Do not write the absolute value to Claude settings, the Nori installation, the
continuity sidecar, or the production profile. Do not retain raw prompts,
transcripts, compact summaries, credentials, or debug logs. Retained evidence
may state only that the confirmed-window diagnostic was selected, whether the
values matched, numeric capacity and context observations, structural hook
phases, and closed reason codes.

## Interpretation

- An exact real `PreCompact(auto)` followed by `PostCompact(auto)` confirms
  source-gated percentage behavior. The production design then requires a
  separately approved compatibility amendment; this diagnostic does not make
  an absolute window a normal default.
- No `PreCompact(auto)` is inconclusive about source gating and preserves the
  existing release block. The next design may permit an operator-authorized,
  runtime-confirmed compatibility technique.
- `PreCompact(auto)` without `PostCompact(auto)` proves that triggering began
  but compaction did not complete; the release remains blocked and the stage is
  recorded without synthesizing a pair.

## Safety and acceptance

- The confirmed value must equal the native `/context` window exactly.
- The 100,000-unit filler bound and 600-second automatic timeout remain.
- The normal invocation continues to run without
  `CLAUDE_CODE_AUTO_COMPACT_WINDOW`.
- Static tests cover missing values, invalid modes, mismatches, exact matches,
  and process-only injection.
- The complete deterministic gate must pass before the live run.
- A passing live result still requires documentation, independent review, and
  CI/Security on the exact reviewed head before the PR can leave draft.
