# P0-04B test-only headless terminal adapter

Status: written specification awaiting operator review; conversational scope
approved. No implementation or authenticated execution is authorized by this
document. Baseline: `aee77a866c72ab1379a849935d4aec25cc0c2a29`.

## Intent and evidence

Repair the acceptance harness's terminal observation path without changing
the distributed skillset's runtime policy, authorization or provider behavior.
Success means accurate bounded terminal state and strictly validated current
input readiness, not merely finding a chevron or making a probe exit zero.

The offline investigation in `tests/validation-notes.md` compared the same
private captures. Headless preserved an additional alternate-buffer row absent
from the simplified renderer, with the cursor on a marker/whitespace row.
NBSP appeared in that row, but the current renderer's Python `rstrip()` removes
it before readiness matching. This is decoder disagreement, not a second
proven NBSP defect, an operational input proof, or the historical paid cause.
Claude Code 2.1.292 was observed; no runtime version will be pinned.

## Decision and alternatives

Use `@xterm/headless` behind a test-only Python/Node state adapter, selected
explicitly for P0-04B context probes. Preserve separate readiness policy.
This replaces the incomplete terminal-state model only on that selected path.

Adding more individual VT patches was rejected: prior passive approximations
did not identify a validated remedy. Broadening the chevron regex was rejected:
history and menus cannot establish a current operational input row. Replacing
every shared-driver dialogue was rejected as unnecessary P0-04A scope expansion.

The [official headless documentation](https://github.com/xtermjs/xterm.js/tree/master/headless)
describes Node terminal-state support and experimental API surfaces. The adapter
must use the installed package's public typings, not undocumented internals.
Its test-only dependency lock is reproducibility metadata, not a pin on Claude
Code, Nori, provider, model or context capacity.

## Scope and dependency ownership

- Modify only harness code, tests, test provisioning and associated documentation.
- Add a private npm manifest/lock under `tests/terminal-runtime/`, initially
  recording the investigated `@xterm/headless` 6.0.0 artifact. No addons.
- Install only in an explicit test-owned external directory with the lock,
  lifecycle scripts disabled, no global installation and isolated npm config.
- Reuse the retained local dependency when its metadata matches the lock.
  No implicit download, npm invocation or module discovery from a probe.
- CI provisioning is explicit, separate from test execution and credential-free.
- Do not add dependencies to `nori.json`, skills, installed Claude settings,
  browser runtime or Nori staging. Verify staging exclusion through existing
  package-contract tests.
- Update ADR-010 and its links when implementation is accepted; retain the
  existing 0.15.0 unreleased release scope rather than inventing a new release.

## Integration boundary

Add explicit driver options `--terminal-engine headless`, `--terminal-node`
and `--terminal-module-root`. The latter two are canonical absolute paths to
the trusted executable and test-owned module directory. Resolve and validate
them before starting Claude; reject symlinked/ambiguous module artifacts and
unexpected package metadata. No shell evaluation or `NODE_PATH`/`NODE_OPTIONS`.

Only `dialogue=context` accepts headless selection. The existing default remains
legacy for other callers. The P0-04B smoke caller explicitly selects headless
for every context measurement, including its dedicated startup entrypoint.
Selection failure never falls back to legacy. The native Claude command after
`--`, startup claim binding, one-use approval, session routing and model-turn
budget remain unchanged. Missing test dependency must block before native
startup, claim consumption or credential transport in the authorized caller.

Proposed responsibilities:

- `tests/terminal-state-adapter.mjs`: one passive, persistent Node terminal;
  parse bounded PTY chunks and return private state snapshots.
- `tests/terminal_state_adapter.py`: validated paths, private IPC, schema,
  deadlines, lifecycle and typed snapshots; never decides authorization.
- `tests/claude-pty-driver.py`: readiness/auth/context semantics and probe input,
  consuming snapshots instead of the legacy renderer on the selected path.
- `tests/browser-context-driver.py` and `tests/live-browser-operations-smoke.sh`:
  explicit selection and preflight wiring; no changes to native consent.

## State and private transport

Use one Node process per selected PTY session, clean child environment, fixed
40-row/120-column geometry matching the existing PTY, and 1000-row scrollback.
Feed raw bytes in order without lossy per-chunk Unicode decoding. Await each
documented write callback before acknowledging state; preserve UTF-8 and VT
sequences split across chunk boundaries. Maintain normal/alternate buffers,
cursor restoration, scrolling, delayed wrapping and character widths.

Requests are framed private pipe messages with monotonic IDs and only init,
feed, snapshot and close operations. Reject duplicate/unknown fields, IDs,
nonfinite values, malformed encoding and unexpected child output. Use existing
8 MiB capture budget, at most 64 KiB per decoded feed chunk, 128 KiB per IPC
frame and 16 UTF-16 units per returned cell. Overflow makes state unproven,
never silently clips a cell into an accepted prompt. Replies expose only the
active viewport/cursor/cell metadata needed by the Python consumer.

Snapshots can contain private native text in memory/private pipes, not public
diagnostics or durable records. Never log IPC, raw stderr, screen rows, cursor
cell text, prompts, session identifiers, credentials or terminal reply bytes.
Unknown child errors map to closed reason codes. Existing approved disposable
capture/history cleanup remains mandatory before aggregate emission.

Terminal-generated `onData`/binary replies are discarded and counted by closed
classifications. Never forward them to the PTY in this iteration. Window/title,
clipboard, link handling, file/network actions and host information are not
enabled. A future bidirectional adapter requires a separate bounded contract.

## Readiness and observation semantics

The adapter proves terminal state, not consent or readiness. Python remains
the owner of the latter decisions. Use active-buffer cells and terminal column
coordinates, not string slices at `cursorX` or codepoint distances.

Readiness requires a unique supported input candidate on the current cursor
row, in the active visible viewport, with a valid cell-position relation:
empty input, existing controlled `ready` fixture, or native quoted `Try`
suggestion. Treat ASCII space/tab and NBSP padding deliberately. Preserve the
legacy `rstrip()` boundary for row text used by existing classifiers; reject
other invisible/zero-width padding and ambiguous cursor relationships.

Reject authentication, theme/trust headings, numbered and unnumbered selector
rows, known slash-command text, synthetic SDK prompt text, historical markers,
off-viewport/inactive-buffer rows and unknown formats. A marker anywhere in a
buffer, a live process or a valid session file is never sufficient.

Keep a freshness barrier for every startup selection or context transition.
Only post-barrier changes to the input candidate/cursor/buffer state establish
freshness; unrelated status output cannot refresh a stale input row. Preserve
full terminal state rather than resetting it at an arbitrary byte offset.
If freshness cannot be proved, block. Recheck all predicates after the existing
settle interval and immediately before sending the next synthetic slash command.

Use the selected state consistently for startup auth, approval selector checks,
theme/trust transitions, readiness and `/context` observations. Do not mix a
headless readiness decision with legacy authentication/context rendering.
Keep exact numeric `/context` labels and ambiguity rejection; capture the
post-command structured percentage while visible, not from unrelated history.
No authorization or credential proof is created by any terminal observation.

## Failure, limits and recovery

State/protocol errors, child exit, missing capability, oversized payload,
timeout or unproved readiness block with closed stages/reasons. No automatic
retry and no paid execution. IPC operations share the existing monotonic probe
deadline, with a maximum two seconds per IPC request; no operation may extend
the 120-second workflow or 1800-second live
run budget. Terminate/reap the helper on every success, failure or interruption.
Do not orphan descendants or suppress cleanup failures into successful evidence.

Experimental API compatibility is proved only by the fixture suite and observed
runtime; passive decoding may still be insufficient without terminal feedback.
Registry integrity is verified during locked provisioning. An operator-owned
local dependency/executable is a trusted test input, not protection against
same-principal local tampering or a compromised upstream package.

Rollback removes explicit headless selection from the test caller and reverts
adapter/provisioning changes together. Retained dependencies may stay outside
the checkout. Do not restore approvals or present legacy fallback as acceptance.

## Acceptance before any authenticated run

1. TDD covers active/alternate restoration, scroll regions, wrap, wide/combining
   cells, split UTF-8/CSI chunks, normalization, deadline and shutdown behavior.
2. Positive input fixtures pass only with current cursor/freshness; history,
   menu, auth, stale frames, inactive buffers and unsupported padding block.
3. IPC/dependency failure fixtures prove zero native startup/input effects,
   bounded private output, no terminal-reply forwarding and no silent fallback.
4. Existing shared-driver/P0-04A tests pass with unchanged legacy defaults;
   P0-04B wiring, startup claim, context numeric and cleanup tests pass.
5. Full package validation and staging-contract checks pass; independent review
   verifies interfaces, safety negatives, normalization and lifecycle boundaries.
6. Repeat synthetic loopback SDK-to-TUI text/real-Skill controls on the observed
   runtime in isolated namespaces, with no operator state or real provider.
   Demonstrate native resumed `/context`, valid numeric inspection, natural exit
   and verified cleanup. A passive snapshot alone is not sufficient.
7. If offline controls remain inconclusive, record the limitation and stop;
   do not relax gates or silently add bidirectional terminal behavior.
8. Any authenticated P0-04B acceptance needs a fresh, immutable-final-commit
   operator grant with the existing six-invocation/40-turn/synthetic-loopback
   scope and budgets. Historical grants stay consumed; TODO/CI/Security/merge
   remain pending until their actual gates are satisfied.

## Approval sequence

Review this written specification next. After approval, write and review a
task-based implementation plan and select its execution method. Then implement
with TDD in the existing isolated worktree. No provider call, push, PR, merge
or release is included in the specification-writing stage.
