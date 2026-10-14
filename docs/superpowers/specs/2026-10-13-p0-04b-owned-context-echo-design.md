# P0-04B owned context echo design

Status: specification and plan operator-approved; local implementation present.
One independent review completed; findings corrected by author TDD and a matching
complete package gate. No second review; native acceptance remains pending.
No new native/provider execution is authorized by this file.
Source baseline: `afb20a0f9ae2a231b36576e5a19a4cfccfcec332`.

## Intent and observed evidence

Allow the isolated offline input challenge to distinguish a proven echo of its
own fixed context command from the current editable input. Keep ordinary input
assessment strict and preserve nonce, consent, deadline and acceptance gates.
This is a test-harness refinement, not production credential-entry support.

One authorized offline run on the baseline detected Claude Code 2.1.295 and
fresh numeric context at 16%. It stopped before nonce generation with
`INPUT_PROBE_INELIGIBLE / UNSUPPORTED_ROW` and
`OTHER_CAPTURED_ROW / CONTROL_COMMAND_SHAPE`. The bounded debug observation
located the rejecting command-shaped row at 10 and the empty cursor row at 37,
column 2, in the alternate buffer. These coordinates and runtime version are
evidence, not implementation constants or compatibility requirements.

Source tracing identified a screen-wide rejection in
`TerminalInputPolicy.empty_input_assessment`, before selection of the
cursor-bound empty candidate. That assessment is also used throughout nonce
verification and owned exit writing; changing only construction is insufficient.
The passive readiness classifier's recognition of control-command shapes does
not establish edit ownership.

Both owned leaders were reaped and disposable roots removed. SDK, after/resume
and skill-turn were not run; loopback message count was zero. The authorization
is consumed. External developer evidence is retained under the basenames
`p004b-offline-afb20a0-aggregate.json` and `p004b-offline-afb20a0-result.md`.
Only structural data is retained locally; the authorized sanitized recut was
sent to chat, where its copy may persist. No deleted raw frame is reconstructed.

## Decision and alternatives

Add an ephemeral, branded in-process `ContextEchoReceipt` for one controlled
context transition. Its only effect is to let a receipt-aware assessment exclude
one exactly correlated off-cursor command echo from candidate classification.
It grants neither terminal input, consent, nonce success nor command execution.

Cursor-only assessment was not selected: it would discard the existing global
ambiguity checks without proving why another marker row is harmless. Keeping
the existing unconditional rejection remains safe but does not resolve the
observed automation blockage. A regex-only history exception was rejected:
matching a public command string is descriptive, not provenance.

This specification refines only the blanket history-echo rejection in the
[pinned-input design](2026-10-09-p0-04b-pinned-input-proof-design.md).
Unowned history, suggestions, drafts, menus, authentication and unknown shapes
remain ineligible. All other requirements of that design remain in force.

## Scope and authority boundary

- Only the existing audited offline launcher may supply the private capability.
  Network isolation, hidden operator state, dropped capabilities and disposable
  HOME/config/project remain mandatory. No real provider or operator credential
  is read or used.
- Bind the receipt to the exact terminal object, live native process, offline
  scope, run owner, context transition and original monotonic deadline. Track
  actual parsed frame progression and observed buffer/viewport geometry.
- Bindings are in memory, non-transferable and unavailable through JSON, CLI,
  environment flags, screen text, diagnostics or provider/tool messages. Merely
  possessing a run identifier or a lookalike object cannot mint a receipt.
- Do not persist the receipt, marker, session identifier, raw cells, transcript,
  prompt, hashes of content or arbitrary exception text. No global preference,
  provider setting, dependency or installed package behavior changes.
- Every new native process or resumed measurement needs a fresh transition and
  proof. Earlier receipts, including those from another phase of the same case,
  do not transfer. Previously rendered resume history is not implicitly owned.

## Correlated transition

The controller establishes the following progression within the original
context-dialogue deadline. Native output is evidence only, never authority.

1. **Empty baseline:** drain queued output and prove the existing supported
   current empty-input anchor, with startup consent completed and revoked.
   Unowned marker rows, draft/suggestion text, authentication, menus, invalid
   geometry or competing candidates prevent the owned-command path.
2. **Controlled command edit:** insert only the fixed `/context`, without Enter,
   into that anchor. Before each concrete write and after waits, recheck scope,
   native/helper lifetime, cancellation, deadline, auth/menu state and the exact
   already-owned prefix. Bound partial writes; never overwrite an unknown draft.
3. **Exact command echo:** require a newer parsed frame with the entire command
   in the anchored cells, the supported prefix and exact cursor advancement.
   Wrong/extra text, relocation or an echo only in another row cannot satisfy
   this checkpoint. No receipt or permission follows from a write acknowledgement.
   Exact partial echoes may accumulate within the original deadline, but none
   authorizes Enter before the complete command echo is verified.
4. **Owned submission:** recheck the full owned command and write one Enter.
   Consume this submission permission once. Enter is forbidden when command echo
   is missing or mismatched; no alternative key, erase or repeat is attempted.
5. **Fresh context and history:** require the existing fresh numeric observation
   after submission. At most one newly observed exact command echo may be bound
   as off-cursor history, with supported cells and correlated geometry. It must
   be absent from the empty baseline and must not be a pre-existing resume row.
   An older unchanged grid, duplicate echo, current-row command, unrelated marker
   or ambiguous transition does not establish this receipt.

The post-submission input still requires one supported, genuinely empty candidate
at the actual cursor. When no historical echo is present, ordinary strict
assessment remains sufficient; no exclusion is needed. When an unsupported echo
is present, only the verified receipt may supply the narrow exception. Failure
never switches to the passive path as recovery.

The command edit is distinct from the later 16-character nonce edit. Its owned
Enter submits only `/context`; it cannot submit the nonce, arbitrary text or a
permission answer. There is no speculative Enter, Escape, interrupt or clearing
key during an unproved state.

## Assessment and proof lifecycle

Preserve the default pure policy APIs and their strict rejection order for
callers without a receipt. Add a separate receipt-aware assessment path that
excludes only its exact validated historical row; it must still inspect all
other rows for authentication, menus, ambiguity and unsupported content.
Never strip arbitrary marker rows or accept command shape alone as ownership.

Recheck receipt bindings and expected history before each active assessment.
After history binding, unexpected change, disappearance, duplication, movement
or viewport/buffer change revokes the dependent transition. No automatic
re-binding, receipt substitution or receipt-dropping fallback is permitted.
The controller's structural view may classify an owned row specially but must
not overwrite the actual terminal snapshot or falsify native observations.

Use the same receipt-aware criterion for initial nonce eligibility, pretype
checks, echo normalization, clear verification, completed-proof rechecks,
one-shot proof consumption and every partial `/exit` write. The receipt itself
never creates `InputOwnershipProof`: exactly 16 random ASCII hexadecimal
characters must still echo in the current anchor and one guarded Ctrl+U must
restore a newer empty frame before proof consumption.

Authentication/menu transitions, cancellation, deadline expiry, process/helper
loss, protocol errors or owner substitution revoke the receipt and dependent
proof. A later disappearance of the forbidden state does not restore authority.
All failures remain terminal for the current attempt. Cleanup stays permitted;
it does not justify speculative input or another native execution.

## Components and observation

- A focused test-only receipt component owns immutable private bindings and the
  controlled command-echo lifecycle; no file, network or logging effects.
- `tests/terminal_input_policy.py` owns pure row classification and the strict
  default contract. Receipt-aware selection must share the actual ordered
  assessment rather than maintain a divergent permissive parser.
- `tests/headless_context_driver.py` owns concrete checked writes, observed
  transition evidence, receipt lifecycle and integration with owned exit writes.
- `tests/terminal_input_challenge.py` retains nonce/clear/consumption authority
  and reuses the same correlated assessment throughout its state machine.
- `tests/terminal_context_debug.py` observes the actual rejecting evaluation and
  local snapshot. It cannot reclassify a different row retrospectively, mint a
  receipt, extend its deadline or restore revoked authority. If observation
  provenance cannot be established, omit content with a closed status.
- `tests/offline-terminal-resume-probe.py` keeps case order, prompts, SDK limits,
  audit, isolation, stop-at-first-inconclusive and identity-checked disposal.
  The selected driver validates in-process capabilities before native launch.

The implementation plan will define exact private signatures and closed reason
codes for these responsibilities without adding a public activation interface.
Existing PTY acceptance event schemas and installed/live defaults stay unchanged.
Observers may retain only bounded closed statuses, counts, coordinates and
booleans. A successful diagnostic checkpoint is not acceptance evidence.

## Limits and privacy

Keep 25 seconds per offline context dialogue, 165 seconds per enclosing run,
at most two cases, existing SDK turn/request limits, IPC/capture bounds and
the original deadline. Command-echo verification consumes that same budget.
No operational grace period, automatic retry or renderer/version fallback.

Keep diagnostics at 16 records and 3 KiB per phase and the complete outer report
at 16 KiB, including audit facts, disposal receipt and final newline. New
checkpoints must fit these limits or be explicitly omitted/rejected; a large
report cannot become success. Do not add redundant full structural checkpoints.

The separately opt-in debug mode remains limited to one temporary frame of
128 KiB and one sanitized rejecting/cursor recut of 4 KiB. Actual namespace
isolation remains the primary protection from real operator data; sanitization
is not universal secrecy assurance. Owned raw capture, native history and roots
must be removed before aggregation; failed disposal suppresses content and
success. Chat copies may persist, and cleanup is not a secure-erasure guarantee.

## Acceptance and residual risks

Required synthetic TDD and integration coverage:

- Strict no-receipt APIs still reject the historical command-shaped fixture.
  The observed two-row geometry passes only with independently established
  command echo, submission, fresh numeric evidence and the matching receipt.
- Reject receipt forgery/serialization, unaudited host, foreign terminal,
  native/run/transition replacement, reused receipt and pre-existing resume echo.
- Reject missing, incomplete-at-submission or wrong command echo, cursor or buffer mismatch, draft,
  suggestion, duplicate history, changed history and unsupported whitespace or
  cell width. Partial writes do not create submission or nonce authority.
- Revoke for auth/menu both before command submission and during every nonce,
  clear, proof and exit phase; also expiry, cancellation, child/helper failure,
  lost ownership and late results after waits. No extra key is sent after failure.
- Cover valid echo/nonce/clear/natural exit and adversarial partial exit writes
  through the actual selected driver; preserve observer provenance, diagnostic
  caps, raw/root disposal, signals, default/live rejection and Nori staging.

Independent scoped code review and the complete package gate must pass on the
same immutable candidate before a new native experiment. A fake UI pass is not
Claude acceptance. New runtime incompatibility, autocomplete/menu behavior,
unchanged context signatures or unproved resume history may still block safely.
Do not claim SDK/resume or skill-turn success before observing them.

The future exact-final-commit offline grant must explicitly include the owned
`/context` edit/echo/Enter sequence, the unsubmitted nonce and guarded Ctrl+U,
synthetic-key consent, disposable native history, existing ceilings, chosen
debug export policy and no repetition. This design approval grants none of
those executions. Original provider-backed browser acceptance, remote
CI/Security, PR and main merge remain independent pending gates. The definitive
unversioned TODO is not marked complete by a spec, synthetic test or local gate.

## Documentation, rollback and approval

Record this test-only refinement in indexed ADR-010. Implementation
updates its status, CHANGELOG and validation notes with actual evidence;
keep existing unreleased root/component versions unless packaging changes.
No raw frame, receipt or runtime history enters Git, Nori staging or releases.

Rollback reverts receipt-aware assessment and its controller/challenge/debug
integration as one unit, preserving the baseline strict active rejection and
explicit passive path. Rollback does not restore a consumed execution grant.

Current approval covers the written specification, the
[implementation plan](../plans/2026-10-13-p0-04b-owned-context-echo.md) and inline
local implementation with synthetic TDD and one independent final review.
Native experiments remain separately gated by a fresh exact-final-commit grant.
