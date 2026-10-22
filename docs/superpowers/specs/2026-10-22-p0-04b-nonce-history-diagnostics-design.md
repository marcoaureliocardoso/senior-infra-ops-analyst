# P0-04B coherent nonce/history failure diagnostics

Date: 2026-10-22

Status: written specification approved on 2026-10-22, including the three
conversational refinements. The separate [implementation plan](../plans/2026-10-22-p0-04b-nonce-history-diagnostics.md)
awaits review and execution-method selection. No product-code implementation
or native execution is authorized by specification approval alone.
Original design baseline: `abdf8301e6f3354c88b1df4f7de68bebf1dbb651`.

## Intent and scope

Distinguish why ordinary audited offline resumed acceptance rejects SDK history
during the nonce/clear protocol. An operator must be able to separate rejection
before proven clear completion, a changed full profile, and rejection after
completion without inferring live state from missing checkpoints.

Use the existing failure record and exception-identity observation mechanism.
Do not change acceptance, history identity, relocation eligibility, input
ownership, proof issuance/consumption, retirement, rollback or production policy.
Both existing fixed case kinds, text-turn/SDK_TEXT and skill-turn/SDK_SKILL,
are in scope. Initial, live, provider, browser, debug and read-only observation
routes gain neither this diagnostic route nor new operational authority.

This approved specification narrowly amends only the no-new-diagnostic-extension
constraint of the [relocation design](2026-10-22-p0-04b-correlated-sdk-history-relocation-design.md).
Its post-clear-only window and every other operational constraint remain intact.
The extension is not implemented merely because this document exists.

## Evidence and remaining uncertainty

The consumed native attempt at `535e55a` returned
OFFLINE_CONTROLS_INCONCLUSIVE in 13.066s. Initial context/natural exit and the
synthetic SDK sample passed. Resumed context and nonce echo were recorded;
POST_SUBMIT / UNOWNED_NEW_PROFILE / text-turn / SDK_TEXT followed, with cursorX
18 and no recorded clear-completion checkpoint. Cleanup was proved.
See [validation notes](../../../tests/validation-notes.md).

Twenty additional asserted synthetic scenarios at executable-equivalent source
reproduced three distinct timing boundaries, the nested validation prerequisite
cycle, and diagnostic-site ambiguity for both case kinds. Twelve used real
Python PTY peers and eight used direct fixture APIs. No native Claude or
provider ran. Full findings and structural results remain outside Git under
`.review-runtime/p004b-terminal-state/p004b-535e55a-deep-investigation.md`.

Exact movement after clear proof succeeds synthetically; movement after echo or
on the clearing snapshot rejects. Reordering the driver's calls alone does not
help: nonce observation itself validates history before issuing clear evidence.
Candidate preparation also uses UNOWNED_NEW_PROFILE for a changed full profile
at the same row, whereas ordinary validation uses PINNED_PROFILE_CHANGED there.

The native records do not prove the live nonce phase, Ctrl+U write, old/new full
profile equality, emitting site or renderer cause. Checkpoints are best-effort;
their absence is not a sealed-state query. No observed runtime-version change
is established as causal. This specification must improve discrimination, not
promise that any particular compatibility remedy will succeed.

## Alternatives and selected architecture

| Approach | Benefit | Decision / cost |
|---|---|---|
| Optional closed annotation on the existing failure | Reuses bounded publication and cleanup; no new artifact channel | Selected; capture/projection/validators must be coherent |
| Separate sidecar or event stream | Independent capacity | Rejected: extra synchronization, retention and disposal contracts |
| Change the relocation window immediately | Might cover an earlier phase | Deferred: native equality and failure site remain unproved; changes authority |

Preserve the existing reason code and four-field resumeHistoryFailure object.
Add one optional sibling, nonceHistoryContext, only to an actual
RESUME_HISTORY_LAYOUT_REJECTED failure in ordinary resumed offline acceptance.
It is absent on success, cleanup and every excluded route. No new record, flag,
environment variable, generic observer callback or public row-exclusion API.

The conceptual components are a private call-scoped capture context, the
existing exception-identity failure freezer, and a pure bounded projector.
Their implementation interfaces belong in the separately approved plan.
No diagnostic object can act as a candidate, view, receipt, nonce/exit proof or
permission. Acceptance must never read this annotation.

## Closed payload

nonceHistoryContext is an exact-key object containing these seven string enums.
No other key, free-form string, number, list or nested payload is accepted.

| Field | Allowed values | Meaning |
|---|---|---|
| site | HISTORY, CANDIDATE_IDENTITY, CANDIDATE_DESTINATION, COMPOSITION, OTHER | Literal rejection site category; not an inferred stack trace |
| noncePhase | NONE, ELIGIBLE, ECHO_PENDING, ECHO_MATCHED, CLEAR_PENDING, PROVEN, CONSUMED, REVOKED, UNKNOWN | State observed on the bound challenge before revocation |
| clearWrite | NOT_SENT, ACKED, UNKNOWN | Exact one-byte Ctrl+U write acknowledged by the existing writer |
| clearEvidence | ABSENT, PRESENT, UNKNOWN | Presence of matching privately registered clear-completion evidence |
| sdkBaseline | ABSENT, PRESENT, UNKNOWN | Immutable SDK identity established by the current resumed-view binding |
| placement | SAME_SLOT, OTHER_SLOT, NO_MATCH, MULTIPLE, UNKNOWN | Recognized SDK location relative to its current authorized placement |
| profile | EXACT, DIFFERENT, UNAVAILABLE | Full immutable HistoryProfile comparison when a unique match exists |

Each use of the existing UNOWNED_NEW_PROFILE label must get a distinct literal
site where its causes differ: ordinary new-row validation, candidate identity
inequality, and candidate destination/allowance rejection. COMPOSITION identifies
composed-row/input rejection; OTHER covers remaining layout guards. Site must
not be guessed from the generic reason or check label.

noncePhase is observed state, not proof of ownership. PROVEN cannot substitute
for clearEvidence. PRESENT reports private evidence presence and binding, not
a fresh validation of its lifetime or permission to exit. NONE means a bound
ordinary controller has not created a nonce challenge; unavailable binding is
UNKNOWN, not NONE or ABSENT.

ACKED requires the existing writer's validated successful return for the exact
Ctrl+U byte in the current dialogue. It proves neither UI receipt nor processing.
An exception or ambiguous acknowledgement is UNKNOWN unless the owned controller
can still positively establish that no clear write was attempted. Do not add a
write, terminal read, acknowledgement protocol or retry to obtain this field.

placement concerns recognized matching-case SDK profiles, not arbitrary row
content. With one such profile and a known current authorized SDK slot, report
SAME_SLOT or OTHER_SLOT. NO_MATCH means no recognized matching-case SDK profile,
not proof that a visual row disappeared. MULTIPLE means multiple recognized
profiles. Without a known reference slot or coherent classification use UNKNOWN.
Compare against current sdk_position, including a committed move, not a retired
original row. No row index is exported.

profile is EXACT or DIFFERENT only with a known immutable SDK baseline and one
recognized candidate. Compare kind, marker_x, complete gap tuple and complete
tail tuple without normalization. ASCII and NBSP remain different. Otherwise use
UNAVAILABLE; absence or duplication must not be converted to inequality.

Unavailable facts use their explicit unknown/unavailable value. If no trustworthy
capture context exists, omit the entire optional block. An omitted block always
means missing diagnostic information, never proof that an event did not occur.

## Coherent capture and failure lifecycle

1. Enter an ephemeral private diagnostic scope at the relevant ordinary resumed
   guard invocation, using the actual controller/challenge/view, current
   snapshot identity, frame and dialogue bindings already supplied by that path.
   Capture phase, clear-write acknowledgement and evidence presence before a
   failing validator can invalidate them. No user/report parameter can mint it.
2. At the actual rejecting site, classify only the already available snapshot
   against that scope's baseline/current placement. All exported facts must
   describe this same invocation and snapshot. The scope's earlier protocol
   events remain bound to the same current dialogue; no previous-dialogue cache.
3. Freeze the seven closed scalars against the actual exception identity before
   case/view/probe revocation. Freeze no snapshot, row, owner, profile or other
   operational reference into the error record. First failure wins; later nested
   catches must not overwrite it with revoked state or a different frame.
4. Perform the original rejection, revocation and cleanup without consulting the
   diagnostic. Project the frozen annotation through the existing structural
   collector. A serialized object or similarly attributed exception cannot mint
   a producer observation; serialized report data remains merely report data.
5. Clear the call scope on every return, rejection, cancellation and exception.
   Nested/reentrant calls must not borrow another invocation's context. Reject
   stale, cross-frame, cross-case or cross-controller association by omitting the
   extension, without changing the original operational result.

Before any guard that could revoke the challenge, protocol status must be
captured from its original live owner, not recovered afterward from REVOKED
state. Capture location/profile facts before the history guard mutates retirement.
If the needed original facts are unavailable, explicitly degrade or omit them.

The sampler may perform only bounded local reads and pure classification of the
existing bounded snapshot. It must not re-run acceptance/history/lifetime
validation, call a helper snapshot API, poll a process, renew frame/time metadata,
issue/consume proof, mutate retirement or call an external/custom callback.
Do not use an evidence getter that invokes validation/revocation merely to report
presence. Do not parse or normalize new terminal data for diagnostics.

## Collection, compatibility and retention

The annotation is optional and separately validated. Preserve existing base
fields, reason/check semantics, revocation and ordered cleanup facts. Old reports
without the block remain valid. Invalid keys/enums, oversized or mismatched
optional blocks are omitted without rejecting or changing the base failure.
Update every in-repository producer/projector/collector/replay validator together;
this does not promise interoperability with arbitrary mismatched harness versions.

Keep 16 records and 3,072 bytes per phase and 16,384 bytes for the complete
aggregate, including its newline. Add no checkpoint records. Decorate only after
base records and cleanup have priority; sacrifice the new annotation first
under pressure. Collection failures remain non-blocking and cannot hide cleanup
failure, change the reason code, or promote inconclusive results to success.

Documentation-stage JSON sizing against retained sanitized failure reports,
using the longest permitted field strings as a conservative size projection,
gave 2,882 bytes per resumed phase and 5,919 aggregate bytes for `535e55a`;
`9f68a0f` gave 2,974 and 5,998 bytes respectively. Both fit existing limits.
This arithmetic is not an implemented collector test or a promise that every
future report fits; maintained tests and pressure/omission behavior remain required.

Store no transcript, frame, prompt, nonce value, command text, terminal row,
profile content/hash, credential, cookie, session ID, stack trace or serialized
capability in the annotation. No new artifact file, diagnostic side channel or
long-lived cache. Existing raw evidence and temporary native history must still
be deleted before aggregation; operational references live only in the original
bounded call/dialogue lifetime and are released on every path.

## Noninterference, timing and rollback

Preserve the exact input protocol: one /context submission, the existing
16-character non-submitted nonce, one echo-gated Ctrl+U, newer empty-input proof,
one exit-proof consumption and independently guarded /exit/natural exit.
Keep case order, first-inconclusive stop, request/SDK ceilings, 25 seconds per
dialogue and 165 seconds total including the existing cleanup reserve.

Diagnostic enablement, loss, malformed data or omission must not change guarded
decisions or input bytes under a controlled identical test schedule. No failure
handler can continue an operation or acquire input authority from this payload.
Additional bounded local computation can affect scheduling; zero timing overhead
is not claimed. Measure its cost, keep all work under original deadlines and
cancellation supervision, and never extend a deadline to accommodate collection.

Rollback removes the optional block, sampler and capture context together.
Original rejection and cleanup remain intact; no grant, revoked proof or retired
position is restored and no native attempt is repeated.

## Verification and acceptance criteria

The later implementation plan must require TDD, focused regressions, independent
whole-change review and a full immutable-source package gate with explicit skips.
This specification itself implements no verifier or diagnostic field.

- Promote the twenty investigated scenarios into reproducible maintained tests:
  twelve PTY cases, two observe-first cases, six site-ambiguity cases across both
  fixed case kinds. Preserve exact input counts and expected accept/reject results.
- Distinguish ECHO_MATCHED rejection, CLEAR_PENDING rejection on a clearing
  snapshot, and post-clear rejection. Test literal sites for ordinary new-row,
  same-position changed-profile, moved changed-profile and destination failures.
- Prove writer acknowledgement differs from UI clear proof; failed/ambiguous
  clear writes cannot become ACKED. Forged public phase cannot create evidence.
- Test no baseline, unrecognized profile, duplicates, current versus original
  placement after commit, ASCII/NBSP inequality, geometry change and unknown facts.
- Freeze before revocation; prove nested catches, replay, exceptions with copied
  attributes and cross-owner/frame attempts cannot forge or replace observations.
- Inject capture/projector/collector failures and reentrancy; compare input bytes,
  outcomes, proof consumption, retirement and cleanup against diagnostic absence
  under identical controlled schedules. Test cancellation and expiry throughout.
- Validate strict exact-key/enums and absence from success, cleanup, initial,
  live, provider/browser, debug and post-Enter observation routes.
- Exercise record/byte pressure, invalid payload omission and cleanup dominance.
  Before requesting another native attempt, demonstrate that all seven fields
  fit the retained native failure's structural report shape within unchanged
  phase and aggregate budgets, using only sanitized structural fixtures.
- Verify sampling uses no I/O or operational validator, advances no lifetime
  metadata, retains no raw content/operational object after publication, and
  releases its context on all paths. Report measured collection overhead without
  claiming a timing-independent native result.

A future separately authorized native attempt may remain inconclusive. Failure
to capture the block, UNKNOWN facts or a changed full profile cannot justify
relaxing guards or repeating the run. Diagnostics alone close no native,
provider/browser, platform, remote CI/Security or merge gate.

## Delivery and next approval

This is a documentation-only specification on the existing isolated branch.
Keep package version unchanged; index the proposal in ADR-010 and its index
without claiming implementation. No push, PR, merge, release, staging refresh
or definitive TODO completion is authorized here. The old native grants remain
consumed; do not access operator settings/credentials or install/update software.

The operator approved this written specification. The separately prepared plan
requires review and execution-method selection before product-code implementation.
Its causal-decision stop rule prevents automatic compatibility repairs or
repeated native attempts. Any later native run needs fresh authorization tied
to its exact final source and explicit limits.
