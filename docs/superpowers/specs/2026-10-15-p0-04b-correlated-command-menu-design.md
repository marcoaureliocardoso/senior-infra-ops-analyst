# P0-04B correlated command-menu observation

Status: specification and implementation plan operator-approved; inline execution
selected. Locally implemented with 281 covering tests passed on source 99c9c60.
Candidate fb60e0d passed the immutable full gate and scoped independent review
with no findings. Later result-only documentation is separate from that source.
No new native execution is authorized by specification or implementation approval.
Source baseline: `e76cf95b0476c89ad3f8de11c239bb2be52d73b7`.

## Intent and observed evidence

Let the isolated offline harness distinguish one correlated command-completion
row from its own editable command input, without weakening ordinary terminal
assessment or transferring authority to rendered text. The immediate target is
the existing fixed `/context` handshake, not general terminal automation.
Success is a narrowly justified pre-Enter assessment followed by the unchanged
single submission and fresh numeric proof, or an honest terminal inconclusive
result when that justification or native behavior is unavailable.

One newly authorized offline attempt on the baseline observed Claude Code
2.1.301 and stopped in text-turn/before. The frozen failure was
INPUT_PROBE_REVOKED with EDIT_PENDING / NORMALIZED_ELIGIBILITY / eight command
bytes / zero Enter bytes and UNSUPPORTED_ROW / OTHER_CAPTURED_ROW /
UNRECOGNIZED_SHAPE. The separate edit-row diagnostic reached READY only after
owned cleanup. Its authorized chat-only excerpt identified a command-completion
suggestion for the same fixed command outside the input row. Do not reproduce
that excerpt, its description or a recovered frame in this specification or Git.

The host reported exit 1; the recorded before-dialogue result was 2. There was
one case, zero gateway messages and no SDK, after/resume or skill-turn execution.
Both native/helper leaders were reaped and case/outer roots absent. The one-shot
grant is consumed and no retry occurred. Content-free external evidence is
`C:\projects\senior-infra-ops-analyst\.review-runtime\p004b-terminal-state\p004b-offline-e76cf95-structural-result.json`.
It deliberately excludes the excerpt. This observation identifies the rejecting
row in this attempt; it does not recover or prove earlier deleted native rows.
The observed runtime is evidence, not a compatibility pin.

Source tracing explains the immediate rejection: `_prefix` first verifies the
owned command cells, then normalizes only that input row and invokes the strict
ordered empty-input assessment. Another marker-bearing command-completion row
remains. Its description prevents an empty-prompt or bare-control-command match,
so the assessment rejects it before Enter. A context-related description can
also change descriptive freshness; that is not numeric context proof.

The official [interactive reference](https://code.claude.com/docs/en/interactive-mode#commands)
describes the slash-command menu. Its separate
[prompt-suggestion controls](https://code.claude.com/docs/en/interactive-mode#prompt-suggestions)
do not establish a supported way to disable this command menu. The native attempt
did not reach Enter, so whether its first Enter executes or merely completes the
selected command remains unobserved.

## Decision and alternatives

Add a private per-command correlated menu observation inside the existing owned
context-command lifecycle. Its only effect is to exclude at most one validated
off-cursor command-completion row from the existing pre-Enter ordered assessment.
It cannot grant input ownership, consent, submission, history, nonce or exit proof.

Cursor-only assessment was rejected because it would discard global ambiguity
checks without explaining another marker. An unconditional command/description
regex exception was rejected because matching content is not provenance.
An extra Escape was not selected: it adds a state-dependent input action and
would require a different protocol and authorization. Disabling unrelated prompt
suggestions is not a demonstrated remedy and changing operator preferences is
outside scope.

This refines only the pre-Enter suggestion rejection in the
[owned-context-echo design](2026-10-13-p0-04b-owned-context-echo-design.md).
Its default rejection of unowned menus remains. The
[pinned-input proof](2026-10-09-p0-04b-pinned-input-proof-design.md), history receipt,
nonce/clear/exit protocol and
[separate debug contract](2026-10-15-p0-04b-rejected-edit-row-debug-design.md)
are otherwise unchanged.

## Scope and independent authority

- Activate only inside the existing audited offline owned-command route. Require
  network isolation, hidden operator state, dropped capabilities, synthetic-only
  authentication and disposable HOME/config/project/history. No new public CLI
  flag, environment activation, dependency, mount or installed-package behavior.
- Bind observation to the actual command record, terminal, live native process,
  offline scope, run, transition, baseline, original deadline and parsed frame
  progression. A copied object, serialized row index, diagnostic or lookalike
  snapshot cannot create or transfer that binding.
- Preserve strict ordinary/default/live assessments. Do not accept arbitrary
  row exclusions from external data or make a global parser exception.
- Keep only the already authorized fixed command. No arbitrary completion,
  command argument, plugin/MCP selection, credential input or alternate key.
- Treat every row and description as untrusted data. Appearance alone is never
  evidence that a row came from a trusted renderer, and a classifier is not an
  arbitrary-code sandbox. The narrow exception depends on the independently
  established offline command transition and exact owned-input checks together.

## Correlation and classification

1. **Strict baseline.** Establish the existing supported empty cursor-bound
   input after startup consent. The whole baseline must pass ordinary strict
   assessment, with no detected competing marker/menu or unowned draft.
   Record the original baseline in the private command record, not in a file.
2. **Owned edit.** Preserve actual write acknowledgements, partial-prefix checks,
   cursor/anchor/cell geometry and deadline/lifetime checks. Partial command echo
   gains no menu exception. In particular, a suggestion cannot rescue missing,
   wrong, incomplete or regressing command cells.
3. **Full echo before menu correlation.** The fixed eight-byte command must
   already have been written and must appear exactly in the owned cursor row in
   a newer parsed frame, with the correct cursor and unchanged surrounding input
   cells. Zero Enter bytes have been written. No past matching row suffices.
4. **One bounded other row.** A candidate must be outside the actual cursor row,
   in the same captured buffer/viewport, and absent as a competing marker from
   the strict baseline. Its validated cells must identify a selected completion
   whose complete command token is exactly the owned fixed command, followed by
   a distinct separated nonempty description field. Empty-prompt shape, bare
   history-command shape, another command, ambiguous fields or another matching
   row do not qualify. Preserve existing unsupported-cell, whitespace and format
   character rejection. Do not use an English description, absolute coordinates,
   version number, static binary offset, color alone or arbitrary trailing text
   alone as the recognition criterion.
5. **Conjunctive validation.** Classification and the full independently owned
   transition must both hold. If either is incomplete, use the ordinary ordered
   rejection; do not catch a revoked failure and reinterpret it as permission.
   Lack of evidence remains a blocker rather than a permissive fallback.

The bounded selected-row grammar is:

- Use a row from the existing validated 120-cell capture, outside the cursor row.
  All participating cells have width one; wide, continuation or malformed cells
  are unsupported in this first adapter.
- Allow leading ASCII space padding, one existing `❯` marker, one or more ASCII
  spaces, then the exact fixed `/context` token in ordinary width-one cells.
- Require at least two ASCII space cells between that token and a nonempty
  display-description field. Command suffixes and single-space continuations
  fail this grammar. No exact padding width or absolute position is required.
- Description cells may contain supported printable width-one Unicode but not
  another marker, control/format characters or unsupported whitespace. Remove
  only renderer trailing ASCII padding when testing whether the field is empty.
  Its wording has no authority and no expected English literal is embedded.
- Require exactly one such new selected row. A bare command/history row, another
  target, another matching row or any remaining unsupported marker keeps the
  existing ordered rejection. The full independent correlation is still required;
  this grammar alone never justifies an exclusion.

The implementation plan must name positive/negative tests for this grammar, not
expand it silently. Unknown layouts or multiple completions remain unsupported;
this is not a universal UI recognizer. The single exported row does not establish
every surrounding menu layout.

This field grammar cannot prove whether arbitrary text was a description or
arguments in some other UI. Do not claim that distinction from spaces alone.
The independently owned cursor input must contain only the fixed command with
no arguments, and the complete per-command correlation is mandatory even for a
shape-matching row. No text from the other row is inserted or submitted.

## Assessment and observation lifetime

Perform independent scope/input/correlation checks before the one ordered
assessment. Pass only the privately validated row exclusion into that assessment;
continue all original checks for every other row. The current input-row
normalization remains unchanged. Do not rewrite the actual snapshot, remove all
marker rows, repeat assessment after rejection or manufacture diagnostic success.

Once correlated, bind the exact row cells/index and current geometry to the
command's existing pre-Enter state. Recheck every actual observed frame and
immediately before concrete Enter, including output drained during writable
waits. Unexpected disappearance, mutation, duplication, movement, viewport/buffer
change, authentication/menu conflict or binding/lifetime loss revokes the
transition. A later restoration cannot recover it. A route that never observed
a menu may continue with the original strict assessment without an exclusion.

The observation is distinct from `ContextEchoReceipt` and `InputOwnershipProof`.
It must not masquerade as either, and cannot be reused by a resumed process or
another dialogue, command, scope or transition. Release its content-bearing
bindings on failure/cancellation/cleanup and retire them irreversibly once the
one actual Enter has been acknowledged. Menu disappearance after that authorized
submission is not itself pre-Enter ownership loss; no exclusion survives it.

Keep the original actual-byte ownership, one-shot submission, latest pre-Enter
numeric/frame barrier and existing receipt rules. After Enter, require fresh
numeric context beyond that barrier. A description, menu redraw, general READY,
contextFresh or old numeric grid cannot replace this proof. If Enter only accepts
the completion and no fresh numeric context follows, stop within the original
deadline as inconclusive. Never send a second Enter, Tab, Escape or fallback key.

The exception ends before history binding, nonce eligibility and all later
proof/clear/exit checks. Those paths retain their existing strict or separately
proven history-receipt assessment. A persistent menu after Enter remains an
unsupported state, not historical ownership. No `/exit` menu exception is added.

## Components and diagnostics

- `tests/terminal_context_echo.py` owns the private menu observation/correlation,
  the actual command-state lifetime and its one validated pre-Enter exclusion.
  Reuse its private command record and existing scope/deadline guards; avoid a
  separately transferable capability or parallel permissive state machine.
- `tests/terminal_input_policy.py` retains the shared pure ordered row assessment
  and strict public/default behavior. A pure layout helper may classify a row,
  but may not mint a binding, observe freshness, perform IO or authorize input.
- `tests/headless_context_driver.py` and `tests/claude-pty-driver.py` retain actual
  checked writes, cancellation and fresh-frame handling. No new key or extra
  submission is introduced, and disabled/non-context callers remain unchanged.
- `tests/terminal_input_challenge.py` retains nonce/history/exit authority. Any
  compatibility adjustment must preserve these contracts; it cannot consume or
  infer the pre-Enter menu exception.
- Existing journal/debug/collector modules continue observing the actual first
  rejecting assessment, including its actual rejected index after a validated
  exclusion. Do not report the excluded menu as the rejecting row or broaden
  capture eligibility to compensate for a changed operational result.
- The offline launcher keeps case order, synthetic prompts, SDK/request budgets,
  audits, first-inconclusive stopping, memory-only debug transport and disposal.

Prefer existing modules and mounts. New public types, activation surfaces,
dependencies or package staging changes require a revised design, not a hidden
implementation expansion. Keep new observations internal and diagnostics closed
and content-free; do not log descriptions, cells, snapshots, hashes or session IDs.

## Limits, privacy and operational parity

Keep 25 seconds per context dialogue, 165 seconds total, at most two synthetic
cases and all current SDK/request ceilings. No renewed deadline, timeout grace,
automatic retry, renderer/version fallback or runtime/provider pin. Preserve
the original Enter/Ctrl+U/exit sequence and native event/acceptance schemas.

Keep 16 records/3072 actual JSON bytes per structural phase and 16384 bytes for
the complete intermediate/final report. Do not add per-frame public records that
silently exhaust this budget. Retain no new raw content outside owned temporary
memory/history; existing raw capture and roots remain disposable. The separate
explicit debug modes, whole-excerpt minimization, post-disposal publication and
latched outer deadline/cancellation checks remain unchanged.

No actual native execution is part of synthetic implementation verification.
No operator preferences, credentials/configuration, provider endpoint, production
input policy, Nori manifest or package version is changed by this test-only scope.

## Verification and acceptance

Required synthetic TDD and controlled-peer integration:

- Valid sole target completion above/below the input, ordinary strict no-menu
  flow and original rejection without private correlation. Use synthetic
  descriptions; do not persist or replay the authorized chat-only native excerpt.
- Missing/wrong/partial command echo, wrong cursor/prefix/tail, pre-existing row,
  foreign/copy/serialized observation, substitution of an equal-but-distinct
  original baseline/evidence snapshot, stale frame, expired scope, native/helper
  loss and cross-dialogue reuse reject. Genuine newer controller captures remain
  usable for revalidation; they cannot replace the original bound evidence.
- Other command, argument-bearing owned input, token suffix/single-space
  continuation, bare history echo, ordinary description,
  duplicate candidates/markers, current-row candidate, unsupported/invisible cells
  and authentication/selection conflicts never gain an exclusion.
- Description wording and supported relative row positions are not pinned. A
  menu description containing context-related labels or percentages cannot supply
  numeric proof or change the original post-Enter freshness barrier.
- Menu loss/change/movement/duplication followed by restoration remains revoked,
  including a redraw during writable wait. No extra write occurs after loss.
- Count one ordered assessment per decision. Original first-failure order,
  enum observation, row projection, observer-loss isolation and cleanup remain
  valid; rejected and excluded rows cannot be confused.
- Exercise both native-like Enter behaviors: direct command execution may reach
  fresh numeric proof; completion-only yields inconclusive with one Enter and no
  retry. Persistent post-Enter menu cannot become a history/nonce/exit exception.
- Assert actual bytes, FD/capture closure, native/helper reap, absent roots,
  original deadlines/cancellation, report limits and unchanged default/live and
  installed/staging behavior. Re-run existing receipt/nonce/partial-exit tests.

After implementation, obtain scoped independent review and a complete package
gate on the final immutable source; if review needs a source correction, run a
fresh complete gate on that corrected candidate. Record reviewed versus gated
hashes honestly. A synthetic UI pass is not native acceptance.

Only a fresh exact-final-commit grant permits another real offline attempt. It
must explicitly include the chosen debug export policy and potentially persistent
chat copy when enabled. The consumed e76cf95 grant cannot be reused. Real
text/skill-turn/resume success and provider/browser acceptance must be observed
separately; remote CI/Security, integration and the definitive TODO remain pending.

## Residual risks, rollback and approval

The native observation covers one rejected row, not the entire renderer protocol.
A conservative recognizer may still reject another layout or partial redraw.
Enter behavior remains unobserved. Completion UI may also appear during `/exit`;
this design deliberately does not authorize an exception there. The workflow may
therefore reach a later inconclusive result even after this issue is resolved.
Do not broaden phases, keys or retained content to conceal that limitation.

Private Python state is a trusted-process discipline, not protection from
arbitrary same-process mutation or a guarantee of physical memory zeroization.
An authorized chat copy cannot be erased by local cleanup. No successful menu
classification completes the broader P0-04B acceptance or authorizes a retry.

Rollback removes this correlated pre-Enter observation and its validated
assessment exclusion together, restoring the original strict rejection. Keep
owned command/history/nonce proofs and debug disposal controls intact. Reversion
does not restore a consumed grant or remove a chat copy already exported.

Implementation must update indexed ADR-010, CHANGELOG, validation notes and spec
status with enforced behavior and observed results; a design-only commit does
not claim implementation. Root/component versions stay unchanged unless the
actual scope changes packaging. No push, PR, merge, release or definitive TODO
completion follows from this specification.

The operator approved this written specification. The
[implementation plan](../plans/2026-10-15-p0-04b-correlated-command-menu.md)
was approved for inline implementation with one fresh final independent reviewer.
Exact immutable verification and review evidence is in `tests/validation-notes.md`.
No native execution grant is implied by either approval stage.
