# Architecture Decision Records

This index is the versioned architectural history for implemented AI-first controls. Decisions describe the architecture that is actually enforced, not only the intended procedure.

| ADR | Status | Decision |
|---|---|---|
| [ADR-001](ADR-001-risk-taxonomy.md) | Accepted | Canonical operational risk taxonomy |
| [ADR-002](ADR-002-subagent-skill-preload.md) | Accepted | Focused native skill preload for subagents |
| [ADR-003](ADR-003-subagent-runtime-controls.md) | Accepted | Bounded, least-privilege subagent runtime |
| [ADR-004](ADR-004-native-command-guard.md) | Accepted | Native deterministic command authorization for executor subagents |
| [ADR-005](ADR-005-context-continuity-and-preventive-compaction.md) | Accepted | Native context continuity and preventive compaction |
| [ADR-006](ADR-006-canonical-nori-package.md) | Accepted | Canonical manifest and reproducible Nori package boundary |
| [ADR-007](ADR-007-first-class-subagents.md) | Accepted | First-class, independently versioned Nori subagent packages |
| [ADR-008](ADR-008-native-execution-boundary.md) | Accepted | Fail-closed native execution routing for main sessions and executor fallback |
| [ADR-009](ADR-009-global-prompt-injection-defense.md) | Accepted | Deterministic prompt-injection boundaries and runtime compatibility reporting |
| [ADR-010](ADR-010-browser-automation-boundary.md) | Accepted | Capability-detected, fail-closed browser operations for infrastructure UIs |

New implemented solutions must add an ADR or explicitly supersede an existing one. A superseding ADR names the previous record and the index retains both entries.

ADR-010 also indexes the test-only
[stage-owned structured SDK context profile](../superpowers/specs/2026-10-23-p0-04b-stage-owned-context-design.md)
and [inline implementation plan](../superpowers/plans/2026-10-23-p0-04b-stage-owned-context.md).
MAIN_STAGE_CONTEXT_V2 cannot satisfy the existing twelve-role/full browser gate;
operational guards stay CONFIGURED_UNPROVEN. Local/SDK controls and earlier
[one-client provenance](../reviews/2026-10-23-p0-04b-native-provenance-result.md)
are distinct from new native acceptance, live requests and remote CI/Security.

ADR-010 also references a [written nonce/history diagnostic proposal](../superpowers/specs/2026-10-22-p0-04b-nonce-history-diagnostics-design.md),
approved by the operator on 2026-10-22. Its [implementation plan](../superpowers/plans/2026-10-22-p0-04b-nonce-history-diagnostics.md)
was approved for direct/inline implementation with one independent final review.
The local same-call, same-snapshot failure annotation changes neither post-clear eligibility nor
input authority, retention limits or native execution grants.
The plan requires a causal decision and stops automatic repair/retry cycles;
instrumentation does not itself fix or establish the native cause.
Local regressions, independent review and the immutable package gate passed at
`94e68ab`; validation notes retain exact evidence and platform exclusions.
Native/browser/provider and remote gates remain open.

ADR-010 also indexes the test-only
[one-shot correlated SDK-history relocation](../superpowers/specs/2026-10-22-p0-04b-correlated-sdk-history-relocation-design.md).
Its written specification was approved on 2026-10-22. The
[implementation plan](../superpowers/plans/2026-10-22-p0-04b-correlated-sdk-history-relocation.md)
was approved for inline execution. All four tasks are implemented and passed
their focused gates, including the final 256-test group. Final independent
review requested no fix; the immutable gate passed at `4d3d057`, with explicit
adapter/platform exclusions recorded in validation notes. Exact profile correspondence and
complete same-frame context/input/lifetime validation precede atomic publication;
old positions stay retired. Native equality and compatibility remain unknown,
and no execution grant, timeout or production/browser boundary changes.
One authorized native offline attempt at `535e55a` remained inconclusive without
recorded nonce-clear completion; cleanup was proved and the grant is consumed. It does
not establish native relocation compatibility; see validation notes.

ADR-010 separately indexes the approved design for the
[bounded post-Enter acceptance extension](../superpowers/specs/2026-10-21-p0-04b-bounded-post-enter-acceptance-design.md).
The written specification is approved; its
[implementation plan](../superpowers/plans/2026-10-21-p0-04b-bounded-post-enter-acceptance.md)
was approved for native/inline execution. Tasks 1/2 are implemented locally and
the Task 2 gate passed 315 synthetic tests. Task 3 reproduced a preexisting
outer-publication cancellation/expiry gap and stopped for design review.
The operator approved the narrow written lifecycle amendment and plan revision;
the acceptance-only outer correction is implemented locally. Its focused gate
passed 109 tests and task completion was recorded. Independent whole-change
review found one numeric-token guard defect; its author TDD fix is implemented.
The author fix passed 184 regressions and the immutable full package gate at
`950bd19`; it was not independently re-reviewed. Native/provider/browser and
remote acceptance remain pending; see validation notes for skipped coverage.
The implementation extends only passive pending in audited resumed acceptance, retaining
the existing correlated-display and independent nonce/clear/exit contract.
The observation-only mode remains permanently read-only after Enter.

ADR-010 separately indexes the approved
[passive post-Enter observation specification](../superpowers/specs/2026-10-20-p0-04b-post-enter-observation-design.md).
The written specification is approved; its
[implementation plan](../superpowers/plans/2026-10-20-p0-04b-post-enter-observation.md)
was approved for inline execution. The observation-only mode is implemented
locally. One fresh independent review found four failure-path gaps, corrected
in one author TDD pass; the immutable full synthetic gate passed at `59c3869`.
Correction verification is not a second independent review.
It observes the later display without
granting input or acceptance. One authorized native run on `3c159a1` reached the
profile with cleanup proved and `acceptance: false`. The summary cannot establish
post-Enter menu persistence or its timing. Default enforced behavior remains
unchanged; full native/provider/browser acceptance and new grants are separate.

ADR-010 records the locally implemented, approved test-only
[correlated context-display evidence contract](../superpowers/specs/2026-10-19-p0-04b-correlated-context-display-design.md).
It distinguishes observed numbers, an owned current-command display and nonce
ownership, without claiming native recomputation from terminal output. The
[implementation plan](../superpowers/plans/2026-10-19-p0-04b-correlated-context-display.md)
uses HISTORY_COMMIT_V1 only in audited resumed dialogues: equal numbers need
an owned new-history display commit, a consumed private witness and independent
nonce ownership. This narrowly supersedes resumed signature inequality, not
default/live behavior. Review/gate evidence is separate in validation notes;
native support remains unproven and the prior execution grant remains consumed.

ADR-010 also records the optional frozen HISTORY_ELIGIBILITY diagnostic extension
approved on 2026-10-20. Closed row/display categories attach only to the original
failure journal, never to input authority; base failure/cleanup records retain
priority within unchanged budgets. Native usefulness still needs separate proof.

ADR-010 also indexes the test-only
[headless terminal design](../superpowers/specs/2026-10-07-p0-04b-headless-terminal-adapter-design.md)
and [implementation plan](../superpowers/plans/2026-10-07-p0-04b-headless-terminal-adapter.md).
This harness addition does not establish native resume or provider-backed
acceptance; the observed offline limitation remains in its evidence record.

The approved [remediation design](../superpowers/specs/2026-10-07-p0-04b-review-remediation-design.md)
separates the [harness author fix pass](../superpowers/plans/2026-10-07-p0-04b-harness-review-fixes.md)
from the [production lifetime correction](../superpowers/plans/2026-10-07-p0-04b-approval-lifetime-remediation.md).
Implemented input/cancellation/lifetime corrections do not complete native/provider
acceptance. The scoped production review identified an ownership gap; its
original-grant fix pass and verification are recorded in ADR-010/validation notes.

ADR-010 also records the isolated offline
[pinned-input proof spec](../superpowers/specs/2026-10-09-p0-04b-pinned-input-proof-design.md)
and [implementation plan](../superpowers/plans/2026-10-09-p0-04b-pinned-input-proof.md).
Synthetic echo/clear ownership proof does not establish native/provider acceptance
or enable this route for production/live credential input.

The implemented test-only [owned context echo refinement](../superpowers/specs/2026-10-13-p0-04b-owned-context-echo-design.md)
and [implementation plan](../superpowers/plans/2026-10-13-p0-04b-owned-context-echo.md)
are also linked from ADR-010. Its private correlated history exception preserves
strict default/live assessment, nonce ownership, disposal and original limits.
Synthetic verification is not fresh native acceptance or production authority;
the pending gates and evidence are recorded in `tests/validation-notes.md`.

The test-only [content-free rejection observer](../superpowers/specs/2026-10-14-p0-04b-context-rejection-diagnostics-design.md)
and [implementation plan](../superpowers/plans/2026-10-14-p0-04b-context-rejection-diagnostics.md)
are indexed in ADR-010. Frozen phase/check/write-count evidence does not alter
strict input ownership, raw-debug eligibility, disposal or acceptance. The cause
of the last native rejection remains unknown; matching verification and review
status are recorded separately in the validation notes.

The test-only [normalized eligibility subreason specification](../superpowers/specs/2026-10-15-p0-04b-normalized-eligibility-diagnostics-design.md)
preserves that four-field observer and adds only closed assessment detail at its
original rejecting boundary. The approved
[implementation plan](../superpowers/plans/2026-10-15-p0-04b-normalized-eligibility-diagnostics.md)
has a local implementation with 181 covering tests passed. Source `9311976`
passed the complete package gate and scoped independent review; exact evidence,
platform/capability skips and remaining gates are recorded in validation notes.
This diagnostic addition does not accept autocomplete rows or authorize a run.

The implemented development-only
[rejected edit-row diagnostic](../superpowers/specs/2026-10-15-p0-04b-rejected-edit-row-debug-design.md)
permits one bounded, sanitized rejected-row excerpt after verified disposal,
under separate explicit offline opt-in and final-commit execution authorization.
Its sealed first-failure binding, memory-only transport and parent-only publication
are described in ADR-010. The approved
[implementation plan](../superpowers/plans/2026-10-15-p0-04b-rejected-edit-row-debug.md)
has completed local implementation and verification. One review finding was fixed
with TDD; corrected source 3d26c56 passed 212 covering tests and the complete gate.
Exact evidence is separate in validation notes. It does not extend old raw-debug eligibility,
change production policy or establish native/provider/browser acceptance.

The test-only [correlated command-menu refinement](../superpowers/specs/2026-10-15-p0-04b-correlated-command-menu-design.md)
and [implementation plan](../superpowers/plans/2026-10-15-p0-04b-correlated-command-menu.md)
are implemented locally with 281 covering tests. One private pre-Enter exclusion
requires the original owned command; actual Enter retires it, and later numeric,
history/nonce/exit checks stay strict. ADR-010 records the boundary and rollback.
Candidate fb60e0d passed the complete local package gate and scoped independent
review with no findings. Exact hashes, skips and separate reviewer evidence are
recorded in validation notes; synthetic success neither establishes native compatibility nor renews
the consumed e76cf95 execution grant.

ADR-010 also records the approved diagnostic-only resumed-history failure
subreasons: closed labels freeze before revocation, without retaining terminal
content or changing ownership/acceptance. The native cause and compatibility
remain unproved; `tests/validation-notes.md` records the local gate status.
