# P0-04B isolated pinned-input proof

Status: written specification operator-approved; implementation-plan review and
execution-method selection pending. No implementation, native experiment or authenticated execution is
authorized by this document. Source baseline:
`c4b6a7a1d1079635598dd18ea0bbb37d14c9669f`.

## Intent and evidence

Establish current input ownership after a native `/context` observation without
requiring the prompt to move. Preserve rejection of stale/history/menu/auth
states, operational authorization and all existing acceptance prerequisites.
This changes the test harness's proof contract, not distributed skill behavior.

The authorized offline baseline observed numeric context at 16%, one candidate
at alternate-buffer cursor `(2,37)`, and no input/location freshness. After
Escape and a barrier reset, all freshness flags stayed false until timeout.
Both owned leaders were reaped and disposable roots removed; SDK/resume and
Skill phases never started. That grant is consumed. See
[the validation and investigation record](../../../tests/validation-notes.md).

The [official fullscreen reference](https://code.claude.com/docs/en/fullscreen)
describes fixed-bottom input and alternate-buffer rendering. The
[commands reference](https://code.claude.com/docs/en/commands) describes a context
usage grid, not a guaranteed modal dismissal protocol. Escape is contextual in
the [interactive reference](https://code.claude.com/docs/en/interactive-mode).
These support a renderer/proof mismatch hypothesis, not every detail of the
installed runtime, a proven Claude bug or an explanation of discarded captures.

## Decision and alternatives

Add an explicitly selected, one-shot edit/echo/clear challenge in the isolated
offline harness. The marker is never submitted. A matched echo and verified
return to empty input produce an ephemeral ownership proof for the next exact
synthetic slash command. A numeric grid or unchanged chevron alone produces no
such proof.

Forcing the classic renderer remains a possible separately authorized diagnostic
comparison, but is not the selected remedy and cannot prove fullscreen behavior.
Accepting a cached prompt or arbitrary redraw is rejected because it does not
prove current input ownership. Status-line-only measurement would not establish
the required SDK-to-TUI/native-resume behavior. No legacy fallback is added.

## Scope and trust boundary

- First implementation is offline-only: audited loopback namespace, dropped
  capabilities, hidden operator state, disposable HOME/config/project, synthetic
  key, empty MCP configuration and existing owned-process supervision.
- Existing callers stay passive unless a trusted offline launcher supplies the
  explicit in-process probe scope. A CLI/environment boolean, screen content,
  provider message or serialized dictionary cannot create that scope.
- The scope establishes isolated test eligibility, not human consent. The
  execution host still needs a fresh, exact-commit operator grant before running
  Claude. An isolation audit or this specification cannot authorize execution.
- Scope and proof bind the selected terminal/native instance, disposable run,
  context transition and original monotonic deadline. They are one-shot and
  non-transferable; identifiers and marker remain private in memory.
- Live/authenticated wrappers cannot activate the challenge in this iteration.
  Expanding it to them requires a separate design and explicit operator grant.
- No provider client, model proxy, browser operation, credential reuse, global
  preference change, runtime/version pin, dependency installation or terminal
  reply forwarding is introduced.

## Eligibility is not readiness

Keep the existing supported cell/cursor geometry, visible active-buffer rules,
padding checks, auth/menu rejection and ambiguity checks. Evaluate those
structural checks independently from freshness so a stale candidate can be
classified as probe-eligible without being authorized for a slash command.

Only a marker-and-supported-padding row with no visible draft/suggestion text is
eligible in this iteration. Existing cell metadata cannot independently prove
that a quoted `Try` tail is ghost text rather than an actual draft with its cursor
at the start; do not infer empty input from it. Quoted suggestions and the
controlled `ready` fixture remain supported by passive tests, but neither is
eligible for this active edit. Existing drafts, history echoes,
unknown formats, multiple candidates, non-current rows, invalid/invisible cells,
authentication and selectors make the probe ineligible.

Startup selection/consent must already have completed and been revoked. Fresh
numeric context must have been observed after the owned `/context` submission.
The challenge cannot recover failed startup, missing numeric evidence or an
expired deadline. Drain available output and recheck phase-specific structural/
auth predicates immediately before each permitted edit: empty input before
typing, exact owned echo before clearing. If an authentication/menu transition is observed
at any point, invalidate the scope/proof and stop, even if it later disappears.

## Context output and Escape

Do not infer a modal merely because the input lacks freshness. On the selected
active path, try the ownership protocol only when the complete supported
inline-input shape is eligible. A known modal or unknown/ambiguous layout blocks
this path; this iteration adds no modal navigation or dismissal recognizer.
It does not send speculative Escape, double Escape, Enter or interrupt keys.
The existing passive path remains available only through its original explicit
selection, never as recovery after an active-path failure.

## Challenge state machine

1. `ELIGIBLE`: retain the empty-input anchor and original deadline in memory.
   Generate exactly 16 random ASCII hexadecimal characters for this challenge.
   Require sufficient same-row terminal space; never wrap or paste multi-line
   content. The permitted write is this exact marker, without CR/LF or Enter.
2. `ECHO_PENDING`: require a post-write snapshot showing the exact marker in the
   anchored input cells, matching buffer/viewport/row and cursor advance.
   Partial echo may be assembled within the original deadline; wrong/extra
   characters, competing candidates, relocation or authentication block. An
   echo in history, status, another row or an inactive buffer is not evidence.
3. `ECHO_MATCHED`: after a fresh owned-echo/cursor/auth check, permit one `Ctrl+U`
   (`0x15`) to remove only the owned marker from the previously empty draft.
   This edit is allowed only when exact echo ownership remains established.
   It is not a generic cleanup key for an unknown draft, selector or password.
4. `CLEAR_PENDING`: require a new snapshot proving the marker absent, the
   supported empty input restored and its cursor back in the expected padding.
   A write acknowledgement or timeout does not prove draft removal.
5. `PROVEN`: produce a branded immutable in-process proof, separate from
   diagnostic JSON. Recheck structural/auth predicates after the existing settle
   interval and immediately before consuming it for the next exact synthetic
   slash command. A completed challenge does not itself submit that command.

Permit only one challenge per context transition. Issue no Enter while echo or
clear is pending. Proof consumption is atomic and single-use; changed terminal,
run, transition, input ownership, auth/menu state, cancellation, protocol error
or deadline invalidates it. Later input cannot reuse an old completed challenge.
Every resumed native instance and measurement requires its own proof.

The actual input bytes of the marker/clear protocol are test-owned actions,
not terminal-generated replies. The Node terminal adapter remains passive.
Unknown key interpretation or inability to clear is an inconclusive result,
not permission to try other clear keys, another marker or a renderer fallback.

## Components and integration

- `tests/terminal_input_policy.py`: pure structural eligibility plus unchanged
  passive readiness; distinguish active echo/clear observations from arbitrary
  status/history changes. Never accept a public marker prefix as ownership.
- Proposed `tests/terminal_input_challenge.py`: private typed scope, marker,
  state machine and consumable proof; no file/network/logging side effects.
- `tests/headless_context_driver.py`: bounded PTY actions, current-state checks,
  proof consumption and failure cleanup. No observer callback can authorize IO.
- `tests/claude-pty-driver.py`: optional selected-path in-process scope; existing
  defaults and non-context dialogues remain unchanged.
- `tests/offline-terminal-resume-probe.py`: supply that scope only after the
  existing isolation audit succeeds. Preserve text-turn then skill-turn order,
  original synthetic SDK prompts, case acceptance and stop-at-first-inconclusive.
- Live startup wrappers and acceptance parsers reject unsupported activation;
  no change to one-use synthetic-key consent, claims or protected credentials.

## Failure, privacy and limits

Active edits in an unproven UI may be interpreted as shortcuts rather than text.
Contain that residual risk in the isolated disposable offline environment; do
not infer that preflight structure makes such edits safe in a real credential
or production session. An observed mismatch never authorizes another edit.
If exact owned echo is lost, terminate through the existing supervisor instead
of attempting speculative erasure or `/exit`. No automatic repetition occurs.

Preserve the 25-second offline context dialogue, 165-second enclosing execution
ceiling, two-case maximum, SDK turn/request limits, IPC/capture bounds and cleanup
semantics. The challenge consumes the original remaining budget; it does not
reset deadlines or add a post-timeout operational grace period. Close-IPC errors
and physical disposal evidence remain separate; no failure is promoted to success.

Retain no marker, cell text, hashes, draft, session identifier or exception text
in durable evidence. Existing authorized temporary captures/native state may
contain synthetic input; remove them, history and the entire private roots before
aggregate emission. Clearing input can leave a private native kill buffer, which
also ends with the disposed process; it is not a retained artifact.

Diagnostics use only closed phase/reason codes, bounded coordinates and
booleans. Keep the 16-record/3-KiB per-phase and 16-KiB outer report limits, with
explicit rejection/truncation. PTY acceptance event schemas remain unchanged;
diagnostics cannot mint or restore an ownership proof or operational approval.
The only challenge-backed submission in this iteration is the fixed `/exit`
command after numeric context inspection. The proof cannot authorize arbitrary
text, `/clear`, another `/context`, model input, a tool call or a permission answer.

## Acceptance and delivery gates

1. TDD proves fixed-position echo/clear and natural exit, and covers partial or
   missing echo, wrong row/buffer/cursor, extra text, history replay, relocation,
   existing draft, unsupported padding, known modal and ambiguous layouts.
2. Negative tests prove zero challenge edits before isolation/scope/startup/
   structural/numeric gates, and zero slash submissions before successful clear.
   Auth/menu transitions before typing, after echo, before clear and before send
   revoke authority without synthetic-key consent reuse.
3. Tests fence one-shot ownership, transition/instance substitution, expiry,
   cancellation, child/helper errors and cleanup; a reported successful edit or
   reaped leader alone cannot satisfy acceptance.
4. Existing passive/legacy, numeric context, signal, startup approval, offline
   stop/no-retry, privacy/bounds and Nori staging contracts remain green. No
   implementation/dependency reaches the distributed skillset or staging.
5. Full package validation and independent review must pass before any native
   experiment. Record skips as limitations, not native acceptance. Update indexed
   ADR-010, CHANGELOG and concise README guidance during implementation; retain
   the existing unreleased root/component versions unless packaging changes.
6. A fresh exact-final-commit offline grant must explicitly include unsubmitted
   marker insertion/removal, synthetic-key consent, disposable native history,
   structural-only retention, existing ceilings and no repetition. A grant to
   the old passive commit cannot authorize this new interaction.
7. Native acceptance still requires both text-turn and real Skill controls,
   SDK-to-TUI resume, fresh numeric observations, natural exit and independent
   raw/root cleanup. Inconclusive means stop and report, not widen recognition.
8. Authenticated acceptance, remote CI/Security, PR and merge remain separate
   gates. The definitive unversioned TODO stays incomplete until its actual
   implementation/acceptance/review/CI/Security/main-merge criteria are satisfied.

Rollback removes active selection and reverts challenge/proof integration as a
unit, leaving the explicit passive path's prior fail-closed behavior intact.
Neither rollback nor spec approval restores a consumed execution grant.

## Approval sequence

The operator approved the conversational approach and this written specification.
The [implementation plan](../plans/2026-10-09-p0-04b-pinned-input-proof.md) needs review and an
execution-method choice before implementation. Native execution requires its
own later exact-commit grant; no push, PR, merge or release is authorized here.
