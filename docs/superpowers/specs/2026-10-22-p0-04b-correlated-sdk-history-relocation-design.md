# P0-04B correlated SDK-history relocation

Date: 2026-10-22

Status: conversational architectural direction approved; written specification
awaiting operator review. This document does not implement behavior, approve an
implementation plan or authorize a native execution.

## Intent and boundary

Allow one strictly correlated relocation of already proven synthetic SDK
history in the disposable offline acceptance harness. Preserve independent
current-input ownership and the existing context/nonce/clear/natural-exit
contract. Compatibility must remain fail-closed when any correspondence or
current-frame proof is missing.

This narrowly amends the position-only SDK-history rule in the
[resumed-history design](2026-10-17-p0-04b-resumed-history-view-design.md),
within ordinary audited resumed acceptance under the
[bounded post-Enter design](2026-10-21-p0-04b-bounded-post-enter-acceptance-design.md).
It does not replace that design's fence, passive pending classification,
outer cancellation/deadline/disposal transaction or acceptance predicates.

The production browser boundary remains the actual P0-04B objective. This is
not a general terminal adapter, history normalizer or new production capability.
There are no new public flags, settings, environment variables or caller-supplied
row exclusions. Initial/non-resumed, live, provider, browser, debug and
observation-only routes retain their existing contracts. In particular,
`--observe-post-enter` remains irreversibly read-only after Enter.

## Evidence and limits

The single authorized native offline run at source `9f68a0f` ended inconclusively
after nonce clearing, with POST_SUBMIT / UNOWNED_NEW_PROFILE / text-turn /
SDK_TEXT. Its runtime was 2.1.307. No timeout expired. Cleanup was proved;
skill-turn was not run. See [validation notes](../../../tests/validation-notes.md).

Inspection of source `db6f3ab` and the retained prompt-ready checkpoint establishes
that an SDK_TEXT profile was already pinned earlier: readiness and diagnostics
used the same snapshot, and only validated historical indices could exclude
that SDK-shaped row from the empty-input assessment at that stage. Later the
guard recognized SDK_TEXT outside the original pinned inventory.

This is source-grounded evidence of a change in recognized SDK-class placement,
not proof of semantic row identity, exact old/new indices, renderer causality
or complete profile equality. In particular, the guard rejected history before
the remaining proofs could finish on the failing frame. Earlier nonce/context
success cannot stand in for those missing current-frame checks.

Sixteen throwaway synthetic scenarios reproduced stable, moved, first-late,
padding-mutated and retired-return trajectories, plus baseline binding checks,
for both case kinds. They used fixed peers, not native Claude or a provider.
The report remains outside Git at
`.review-runtime/p004b-terminal-state/p004b-9f68a0f-unowned-sdk-investigation.md`.
No raw native frame was retained or reconstructed. Native full-profile equality
is unknown; the selected design may legitimately remain inconclusive there.

## Alternatives and decision

| Approach | Benefit | Limitation / decision |
|---|---|---|
| Keep fixed row identity | Smallest contract; already fail-closed | Safe fallback, but leaves observed compatibility failure unresolved |
| One exact, transactional SDK relocation | Separates proven identity from one placement change without weakening input proof | Selected; requires composed same-frame validation and can still reject native behavior |
| General moving/normalized history | Broader renderer compatibility | Rejected: larger authority surface, ambiguous identity and uncontrolled exclusions |

Do not increase timeouts, retry automatically, change client/provider versions,
ignore post-proof frames, normalize whitespace or drop natural exit as a remedy.

## Activation and lifecycle

The only eligible cases are existing audited offline resumed `text-turn` and
`skill-turn`, with the matching SDK_TEXT or SDK_SKILL baseline respectively.
Completed initial handshake, validated synthetic SDK sample, original owned
context submission and live resumed-view provenance remain prerequisites.

The relocation window opens only after the private controller has proved the
nonce echo and its single clear on a newer empty-input frame. It closes before
exit-proof consumption or any exit write. A public phase value such as PROVEN,
a diagnostic record, or a matching row string cannot open it.

At most one relocation may commit per resumed case. A rejected candidate ends
the dialogue with revocation; there is no pending/grace interval, retry loop,
new nonce, extra clear or additional command. Existing 25-second dialogue and
165-second total limits, including cleanup reserve, remain unchanged. No clock,
approval, credential permission or consumed execution grant is renewed.

## Identity, placement and retirement

Keep the immutable SDK identity established at initial resumed-view binding
separate from its authorized current placement. Equality means the entire
existing `HistoryProfile`: kind, marker_x, gap tuple and tail tuple. ASCII and
NBSP are different; no trimming, folding, fuzzy matching or hash surrogate.
Existing exact-width and cell-width requirements remain in force.

The baseline must contain exactly one matching proven SDK profile. First-ever
history, the wrong SDK kind, duplicates or a mutated profile are not relocation.
The candidate frame must contain exactly one exact match at a new row, with no
recognized SDK profile at the old placement or any retired position.

The source position may already have retired under existing POST_SUBMIT rules.
Its immutable baseline identity may identify the candidate only while the same
case and provenance remain live; this does not revive the old position or grant
input. A retired destination is never eligible. After commit, the old placement
is permanently retired and cannot return even with identical content.

The destination cannot overlap current input/cursor, the owned current-context
history row, context heading/metric/sample rows, another pinned history row,
any retired row or protected pre-Enter inventory. Current context evidence and
other historical classes cannot relocate through this mechanism. No old or new
position is exempt from the remaining unknown-marker/authentication/menu rules.

After commit, the new placement must remain present and exactly equal through
exit-proof consumption and the guarded exit write. Disappearance, mutation,
second movement, duplication or old-position return is terminal, not another
opportunity to correlate. This deliberately favors bounded proof over renderer
tolerance.

## Transactional composition

The existing driver remains the single coordinator. A private candidate is a
non-authoritative, immutable proposal tied to the actual snapshot and live
case/run/state/scope/controller/transition/native/helper identities. It is not
a history view, receipt, ownership proof, serialized token or input capability.
Cross-frame, cross-case and cross-session replay are invalid.

Eligible detection must occur before irreversible history rejection/revocation,
without catching an arbitrary failure and continuing with relaxed validation.
Use a private read-only candidate overlay through the composed readers; do not
temporarily install a mapping, mutate retirement state, consume a proof or set
a validation-bypass flag merely to make downstream checks pass.

Every predicate below must succeed against the same snapshot and original live
owners, without terminal input or external I/O during evaluation:

1. Matching case, run, session, controller, policy, scope, transition and both
   process owners; cancellation absent and all original lifetimes unexpired.
2. Unchanged terminal buffer/viewport geometry and the strict unique SDK match,
   valid source retirement and collision-free destination described above.
3. Unchanged complete current `ContextSample`, including numeric values and
   sample geometry; original current-command witness/receipt and owned context
   row remain valid. Equal percentage alone is insufficient.
4. Exact sealed nonce/clear completion provenance and the current empty-input
   anchor. Revalidate the composed current input with only the proposed SDK
   placement substitution; all other exclusions and guards remain unchanged.
5. No unknown/auth/menu marker, invalid transition, revoked receipt, replay,
   stale frame or previously used relocation allowance.

The private nonce-completion fact must be verifiable without circularly asking
the old position-only history validator to approve the new location. It must
also not bypass context/input validation: completion provenance is only one
predicate, not authority. Public `.phase` or diagnostics cannot substitute for
the sealed live proof. Candidate-aware reads must reach every dependent guard
explicitly; validation must not mix old and proposed maps.

Only after the whole assessment succeeds, publish the new placement, monotonic
old-position tombstone and used-once state in one private atomic commit.
Recheck owner/frame/lifetime freshness immediately before that commit. Frame
advancement, cancellation, expiry, reentrancy or failure discards the proposal
and revokes the dialogue, without partial state or input. No asynchronous gap
may separate successful assessment from publication.

Commit does not consume or mint exit authority. The existing proof consumption
and fixed guarded `/exit` write still perform their original current-frame
checks using the committed view. Later frames revalidate all existing evidence
and the new stable placement. There is no extra input and no unguarded fallback.

## Failure, retention and rollback

Any unproved correspondence or conflicting predicate produces the existing
closed inconclusive outcome, with zero further operational input. Failed or
partial redraws cannot be waited through by this exception. Cleanup failures
still dominate results; both owned processes and disposable roots must be
reaped/disposed before aggregation. Stop on the first inconclusive case.

Candidate profiles and owner references stay within the existing bounded
in-memory dialogue lifetime and are revoked/discarded with it. Do not persist
frames, prompts, history, row text, profile hashes, credentials or serialized
candidates. Existing structural diagnostics and byte budgets remain unchanged;
no new content or diagnostic extension is part of this design.

Rollback removes the relocation path and restores strict fixed-position
rejection. It must never restore an old placement, resurrect a revoked proof,
repeat an execution or loosen production/browser permissions.

## Verification and acceptance criteria

An implementation plan must require TDD, review and immutable-source validation;
this section is the contract, not that plan. Both case kinds need coverage.

- Positive: stable history preserves existing behavior; one exact relocation
  after real nonce/clear completion composes with unchanged current evidence,
  commits once and reaches independently guarded natural exit.
- Identity negatives: missing baseline, late first profile, wrong SDK kind,
  changed marker/gap/tail (including ASCII/NBSP), duplicate, return at a retired
  source/destination, second move and disappearance after commit.
- Collision negatives: cursor/current input, current context history,
  heading/metrics/sample rows, other pinned or pre-Enter protected inventory;
  unknown/auth/menu markers cannot be hidden by either old or new positions.
- Transaction negatives: altered current sample with the same percentage,
  stale receipt/witness/anchor, missing sealed nonce provenance, forged public
  phase, consumed exit, replayed/cross-owner candidate, frame advance,
  cancellation/expiry/reentrancy before commit and after commit before exit.
- Atomicity: rejected assessment leaves no published mapping, new exclusion,
  consumed input proof or partial retirement; terminal revocation still occurs.
  All composed readers see one coherent candidate or committed placement.
- Lifecycle: driver/PTY and outer aggregator tests prove input counts/fencing,
  unchanged limits, first-inconclusive stop, reap/disposal and no retained raw
  evidence on positive, negative, cancellation and cleanup-failure paths.
- Scope: initial/live/provider/debug and observation-only paths remain unchanged;
  observation never gains post-Enter input or an acceptance witness.

Before completion claims, run focused regressions, the full package gate and
independent review against the final source, reporting skipped coverage. A
separately authorized, exact-final-commit native offline run must still pass
both cases to establish native compatibility. Strict native profile equality
is not assumed; another inconclusive result is a valid safety outcome, not
permission to relax the contract. Provider/browser, platform and remote
CI/Security gates remain separate and are not established by synthetic tests.

## Delivery and next approval

This specification and ADR/index references are documentation only; package
version and release claims remain unchanged. No implementation plan, product
change, new native run, push, PR, merge, staging refresh or TODO completion is
included in this approval stage.

After operator review and approval of this written specification, create a
separate implementation plan for review and execution-method selection. Any
later native attempt needs a fresh authorization tied to its final source and
explicit limits; previous one-shot grants remain consumed.
