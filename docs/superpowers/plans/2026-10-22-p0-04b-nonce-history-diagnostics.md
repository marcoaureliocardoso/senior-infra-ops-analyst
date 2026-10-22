# P0-04B Coherent Nonce/History Diagnostics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce discriminating, content-free failure evidence without changing
the offline harness's acceptance or turning diagnostic work into repeated
compatibility repairs.

**Architecture:** A private dialogue session records clear-write observations;
a call-scoped sampler freezes coherent metadata against the actual rejecting
exception before revocation. The existing collector publishes one optional
annotation, preserving base records, cleanup and operational decisions.

**Tech Stack:** Existing Python unittest/PTY fixtures, contextvars, weak identity
registries, immutable terminal snapshots and provider-free Debian WSL validation.

**Spec:** [Approved coherent nonce/history specification](../specs/2026-10-22-p0-04b-nonce-history-diagnostics-design.md).

Status: specification and plan approved on 2026-10-22; direct/inline execution
selected, with one independent final review. Tasks 1 and 2 are committed;
Task 3 local implementation and final verification are in progress.
Planning baseline: `e82a332`; execution baseline: `79710ff`. No native attempt
is authorized by this plan.

## Global Constraints

- Do not change acceptance, history identity, relocation eligibility, input
  ownership, proof issuance/consumption, retirement, rollback or production policy.
- Ordinary audited offline resumed text-turn/SDK_TEXT and skill-turn/SDK_SKILL
  only. No initial/live/provider/browser/debug/observation activation or public flag.
- Preserve the existing reason code and four-field resumeHistoryFailure object.
  Add only optional sibling nonceHistoryContext, with the spec's exact seven
  string-enum fields. Missing evidence means unknown, never event absence.
- Keep 16 records and 3,072 bytes per phase and 16,384 bytes for the complete
  aggregate, including its newline. Add no checkpoint records.
- Preserve one /context submission, the existing 16-character non-submitted
  nonce, one echo-gated Ctrl+U, newer empty-input proof, one exit-proof consumption
  and independently guarded /exit/natural exit. Keep case order and first-inconclusive stop.
- Keep request/SDK ceilings, 25 seconds per dialogue and 165 seconds total
  including the existing cleanup reserve. No new input, retry, grace or timeout.
- Sample before revocation, on the same invocation/snapshot/frame. No acceptance
  revalidation, I/O, process polling, callbacks, lifetime refresh or proof mutation
  to obtain diagnostic facts. No operational decision may read the annotation.
- No retained transcript, frame, prompt, nonce value, row, profile/hash, credential,
  cookie, session ID, stack trace or serialized capability. Dispose raw evidence
  and temporary native history before aggregation; cleanup failure dominates.
- No dependency installation, operator configuration/credential access or runtime
  version pins. Keep package version unchanged; record actual test skips.
- No native Claude run, provider call, push, PR, merge, release, staging refresh
  or definitive TODO completion. Prior native grants remain consumed.

## Review Focus

1. A protected body raises while the diagnostic context manager exits: Task 1
   test_scope_exit_preserves_primary_exception must preserve the same exception
   and clear the context without accidentally suppressing/replacing rejection.
2. A move commits and another guard rejects on the same snapshot: Task 2
   test_failure_after_commit_uses_current_authorized_slot must not describe the
   now-retired original slot as current authority.
3. An earlier writer call returned success but a later clear attempt is ambiguous:
   Task 3 test_clear_ack_is_dialogue_bound_and_never_inferred_from_phase must not
   borrow ACKED from a different challenge/dialogue or infer it from PROVEN.
4. Collection fails or a guard reenters on another frame: Task 2
   test_nested_cross_frame_capture_cannot_replace_first_failure must discard
   mismatched detail, not freeze stale state or change the primary error.
5. A complete new annotation is too large after older optional details: Task 2
   test_new_detail_is_sacrificed_before_legacy_and_cleanup must drop the new block
   without hiding existing subreasons, base failures or either cleanup record.

---

## File Map and Boundaries

| File | Responsibility |
|---|---|
| `tests/terminal_nonce_history_diagnostics.py` (new) | Private sessions/scopes, pure frozen observation, schema and exception-identity projection |
| `tests/terminal_input_challenge.py` | Read-only phase/evidence presence reader; no new validation or permission |
| `tests/terminal_resume_history.py` | Literal failure-site tags and freeze before existing revocation |
| `tests/terminal_context_echo.py` | Supply exact composition-site snapshot/frame to the existing layout error |
| `tests/headless_context_driver.py` | Ordinary-route session lifetime, exact writer acknowledgement and call scopes |
| `tests/terminal_structural_diagnostics.py` | Optional annotation validation, replay and last-priority decoration |
| `tests/offline-terminal-resume-probe.py` | Mount the new runtime module in the existing read-only namespace allowlist |
| `tests/resume_history_fixtures.py` | Staged nonce fixture without altering defaults or native runtime paths |
| `tests/nonce_history_fixtures.py` (new) | Maintained deterministic Python peers and controlled synthetic driver runner |
| `tests/fixtures/nonce-history-structural-reports.json` (new) | Sanitized structural sizing shapes, no native content or private paths |
| `tests/test-terminal-nonce-history-diagnostics.py` (new) | Binding, schema, freezing, pure reads and diagnostic-site matrices |
| `tests/test-nonce-history-driver.py` (new) | Concrete I/O/phase cases, noninterference, exclusion and cleanup |
| Existing resume-failure/structural/offline/wiring suites | Compatibility, projection, mount and aggregation regressions |
| `tests/validate-package.sh` | Register both new suites in the existing integral gate |
| ADR-010/index, spec/plan, CHANGELOG, validation notes | Truthful implementation/review/gate status and causal handoff |

Do not split unrelated large modules or refactor operational validation. The new
module is an observer, not a replacement history validator or terminal adapter.
Keep fixtures outside the native namespace and package staging; mount only the
new observer runtime module. Existing debug validation/replay must keep working;
change no debug activation or content-export path.

## Environment and Commands

Before implementation, verify the existing linked p0-04b-browser-automation
worktree via the worktree skill and preserve operator changes. Use host Git with
command-local safe.directory, not WSL Git on the Windows-format linked .git.

Use this PowerShell launcher for each named Python suite/selector below:

```powershell
$nonceDiagnosticArgs = @(
  '-d', 'Debian', '--cd',
  '/mnt/c/projects/senior-infra-ops-analyst/senior-infra-ops-analyst/.worktrees/p0-04b-browser-automation',
  '--', 'env', '-i', 'HOME=/tmp',
  'PATH=/home/marco/.local/opt/node-v24.17.0-linux-x64/bin:/usr/bin:/bin',
  'PYTHONNOUSERSITE=1', 'PYTHONDONTWRITEBYTECODE=1',
  'P004B_TERMINAL_NODE=/home/marco/.local/opt/node-v24.17.0-linux-x64/bin/node',
  'P004B_TERMINAL_MODULE_ROOT=/mnt/c/projects/senior-infra-ops-analyst/.review-runtime/p004b-terminal-state/node_modules',
  '/usr/bin/python3'
)
& wsl.exe @nonceDiagnosticArgs tests/test-terminal-nonce-history-diagnostics.py
```

These are verified local test dependencies, not product/runtime pins. Check
presence read-only; use the authorized host WSL route when required. Do not use
bare PowerShell bash, read operator settings or invoke installed Claude.
RED must be an unmet behavioral assertion, not an import/dependency error; use
guarded symbol lookup in initial tests where needed. Record complete focused
results in this plan's execution ledger, not raw native evidence.

## Task 1: Private Observation Session, Scope and Pure State Reader

**Files:** Create `tests/terminal_nonce_history_diagnostics.py` and
`tests/test-terminal-nonce-history-diagnostics.py`; modify
`tests/terminal_input_challenge.py`, `tests/resume_history_fixtures.py`,
`tests/offline-terminal-resume-probe.py`, `tests/test-offline-terminal-resume-safety.py`
and `tests/validate-package.sh`.

**Interfaces produced in the new observer module:**
- `_NonceHistorySession`: private, sealed, non-serializable, weak-referenceable
  observation handle. No public constructor and no input-authority interface.
- `_create_nonce_history_session(view, *, state, scope, native_owner,
  controller_owner, transition_owner, probe=None) -> _NonceHistorySession | None`.
  Check exact existing private identity bindings by local reads only. An
  observation-only view or mismatched binding yields None; the driver also gates
  creation with its existing acceptance_owned route. Current ordinary creation
  precedes any challenge and starts NOT_SENT; a late session with an existing
  probe starts UNKNOWN and cannot invent a past write acknowledgement.
  Bind the first actual challenge once; a later different challenge cannot reset
  or borrow its writer facts. None after a challenge was bound is unavailable,
  not evidence that no challenge exists.
- `_nonce_history_scope(session, *, probe, snapshot, frame) -> AbstractContextManager[None]`.
  None is an inert scope. Snapshot/frame affinity and observed protocol facts
  are scoped to the protected call; nested calls cannot borrow a foreign scope.
  Capture failure makes observation unavailable, never suppresses the body.
  Capture the immutable SDK identity and current authorized slot at entry,
  before guard mutation, as ephemeral inputs for failure-only classification.
  Do not scan every frame eagerly or read a later mutated/projected map to
  reconstruct those inputs. Release them with the scope; they never enter the
  frozen error payload.
- `_note_nonce_clear_attempt(session, *, probe) -> None` and
  `_note_nonce_clear_ack(session, *, probe, count) -> None`: observation-only;
  attempt makes clearWrite UNKNOWN; validated exact one-byte success makes ACKED.
  Mismatch/failure leaves uncertainty; neither helper raises into operation.
- `_close_nonce_history_session(session) -> None`: release all ephemeral owner
  references and state, idempotently, without operational invalidation or I/O.
- `valid_nonce_history_context(value: object) -> bool`: exact seven-key schema
  and exact enum sets from the spec, not coercion of arbitrary objects.

**Interface produced in `terminal_input_challenge.py`:**
`_read_nonce_history_status(probe, *, view, state, scope, native_owner,
controller_owner, transition_owner) -> tuple[str, str] | None`.
Return observed phase and privately registered evidence presence. Only exact
registered challenge/scope/owner identities may produce known facts. No lifetime
validation, process polling, getter that revokes, metadata update or history
composition. Caller distinguishes a known absent challenge from unavailable
binding; public PROVEN alone cannot produce PRESENT.

**Fixture interface:** Extend existing CaseFixture.proven_resume keyword
arguments with `nonce_phase='PROVEN'`; preserve every existing default and return
key. Allow ELIGIBLE, ECHO_PENDING, ECHO_MATCHED, CLEAR_PENDING and PROVEN, stopping
the actual fixture protocol at that phase. Return the corresponding actual
snapshot/frame and evidence (None before real proof), without registry injection.

- [ ] **Step 1: Write** tests in new class NonceHistoryDiagnosticsTests:
  test_scope_binds_actual_snapshot_and_restores_on_all_paths (exact snapshot/frame
  affinity; foreign view/controller cannot borrow context); test_scope_exit_preserves_primary_exception
  (the identical raised exception escapes and context clears);
  test_status_reader_is_pure_and_public_phase_is_not_evidence (all five staged
  phases, forged public PROVEN without sealed evidence, unchanged metadata);
  test_clear_write_status_is_observation_not_permission (late UNKNOWN, attempt
  UNKNOWN, exact acknowledgement ACKED, copied/foreign handle ineffective);
  test_closed_schema_rejects_extra_keys_and_non_strings (all spec enums; reject
  bool/int/coercible objects/free text); test_scope_and_session_release_owned_references
  (close/GC/reentrancy release, no row or owner survives in exported metadata).
- [ ] **Step 2: Run** the new suite through the launcher. Expected: assertions
  fail on missing observation behavior; no setup/import/runtime failures.
- [ ] **Step 3: Implement** the interfaces above with one private ContextVar for
  current scope and weak identity registries. Use exact local identity reads;
  no operational validation or callback invocation. Catch only capture failures
  outside the yielded protected body; cleanup must not replace its exception.
  Unit tests may inspect private context/registry identities for lifetime and
  writer-state assertions, never inject provenance. Projection and cross-frame
  freeze assertions belong to Task 2, which adds that projection interface.
- [ ] **Step 4: Integrate** the new module into the existing namespace read-only
  mount list and register its unit suite in validate-package.sh. Add
  test_namespace_mounts_only_observer_runtime_not_diagnostic_fixtures to the
  offline safety suite: module mounted, fixture/test/JSON files not mounted.
- [ ] **Step 5: Run** new unit suite, test-terminal-input-challenge.py,
  test-terminal-resume-history.py and the named mount test under
  OfflineTerminalResumeSafetyTests. Expected: all pass with unchanged defaults.
- [ ] **Step 6: Commit** as `test: model coherent nonce history observation scopes`.

## Task 2: Literal Failure Sites, Pre-Revocation Freeze and Bounded Transport

**Files:** Modify the observer module/new unit suite, `tests/terminal_resume_history.py`,
`tests/terminal_context_echo.py`, `tests/terminal_structural_diagnostics.py`,
`tests/test-terminal-resume-failure-diagnostics.py`,
`tests/test-terminal-structural-diagnostics.py` and
`tests/test-offline-terminal-resume-safety.py`; create the structural JSON fixture.

**Consumes:** Task 1 session/scope and status-reader interfaces.
**Produces in observer module:**
- `_freeze_nonce_history_failure(error, *, record, snapshot, frame, site) -> None`.
  Require the active private scope and actual matching exception/base observation.
  Classify SDK profiles by the existing pure matcher, using the real view's
  identity/current authorized slot captured at this guard's entry, not a live
  mutated or projected candidate map.
  Freeze only the spec's seven enums, first failure only; never retain the passed
  record/snapshot/profile. Internal capture errors simply omit the annotation.
- `nonce_history_failure_diagnostic(error) -> dict[str, str] | None`: project only
  the private exception-identity observation; copied attributes are ineffective.

**Private integration signatures in history:** Keep existing arguments and add
keyword-only `_nonce_site='OTHER', _nonce_snapshot=None, _nonce_frame=None` to
`_fail` and `_resume_layout_error`; add `_nonce_frame=None` to `_profiles` and
`_history_indices`. Thread actual existing snapshot/frame from their callers.
Default/no active scope means no new annotation and original behavior. Existing
public guard signatures and exception reasons remain unchanged.

The freezer runs after the existing base failure capture and before original
revocation. Tag _history_indices with HISTORY; the identity inequality branch
of _prepare_sdk_relocation with CANDIDATE_IDENTITY; its destination/allowance
branch with CANDIDATE_DESTINATION. Tag composition guards in history and the
two _resume_layout_error sites in echo with COMPOSITION and their actual snapshot/
frame. Other layout failures use OTHER. Never infer site from the check label.
Pass the actual frame to _profiles/_history_indices even for read-only candidate
validation, where the live record's older stored frame is not the current frame.

- [ ] **Step 1: Write** tests in new class NonceHistoryFreezeTests:
  test_actual_sites_freeze_before_revocation (both kinds; baseline/placement/
  profile and original phase survive invalidation); test_same_label_distinguishes_identity_and_destination_sites
  (same-position padding mutation and an already-pinned destination/used allowance,
  all original errors unchanged; retired destination still uses its original
  RETIRED_PROFILE_RETURNED check); test_failure_after_commit_uses_current_authorized_slot
  (report SAME_SLOT at committed slot, never the retired original);
  test_nested_cross_frame_capture_cannot_replace_first_failure (foreign scope,
  stale frame, projected map, reentry and copied exception attributes);
  test_sampler_performs_no_io_validation_or_metadata_refresh (forbidden methods
  raise if called; original guard behavior unchanged when sampler fails).
- [ ] **Step 2: Run** the new tests. Expected: missing annotation assertions fail;
  exact guarded rejection and real fixture setup still occur.
- [ ] **Step 3: Implement** freeze/projection and literal tags as specified.
  Preserve _FAILURE_OBSERVATIONS and original revocation/return ordering.
  Each call scope describes one guard invocation; a committed move cannot leave
  a stale position snapshot for a later guard, even on the same terminal frame.
- [ ] **Step 4: Write** collector/replay tests: test_new_detail_is_sacrificed_before_legacy_and_cleanup;
  test_old_reports_and_invalid_optional_detail_preserve_base (exact-key/enum,
  malformed, oversized, missing data and wrong point/reason);
  test_full_annotation_fits_retained_structural_shapes (both retained reports,
  all seven longest labels, phase <=3072, aggregate with newline <=16384);
  test_replayed_diagnostic_cannot_supply_acceptance (all enums are only report
  data; success predicates do not read them). Expected: RED on transport/detail.
- [ ] **Step 5: Implement** optional nonceHistoryContext handling in
  TerminalDiagnostics.add/report, separately from resumeHistoryFailure. Decorate
  last after legacy annotations; omit invalid/new overflow without changing base
  rejected/truncated facts. Keep the 16-record limit and both cleanup records.
  Audit context_stage_report, _bounded_standard_report and _valid_edit_base replay
  consumers; retain their existing operational contract and excluded-route behavior.
- [ ] **Step 6: Run** new unit suite, test-terminal-resume-failure-diagnostics.py,
  test-terminal-structural-diagnostics.py, test-terminal-context-debug.py and
  test-offline-terminal-resume-safety.py. Expected: all pass; no raw content,
  serialized capability, new authority or increased budget in fixtures/reports.
- [ ] **Step 7: Commit** as `test: freeze and transport nonce history failure facts`.

## Task 3: Real Driver Lifecycle and Maintained Causal Discrimination Matrix

**Files:** Modify driver, unit/new driver suites, resume-history fixtures,
offline safety suite, wiring suite, validate-package.sh and result documentation;
create `tests/nonce_history_fixtures.py` and `tests/test-nonce-history-driver.py`.

**Consumes:** Task 1 scope/status/write interfaces and Task 2 freezer/projector.
**Fixture interface:** `run_nonce_phase_case(case_kind: str, variant: str, *,
diagnostic_mode='normal', clear_fault=None) -> dict` in nonce_history_fixtures.
Variants: stable, echo-move, echo-padding, clear-move, clear-padding,
post-clear-move. diagnostic_mode: normal, absent, capture-failure, collector-failure;
clear_fault: None, would-block, io-error, bad-count. These are test-only controls,
never CLI/settings/runtime options. Return exitCode, inputBytes, diagnostics,
processReaped, helperReaped and caseRootAbsent. Fix the nonce generator only in
tests for byte-identical comparisons; never print/persist that synthetic nonce.
Use bounded pipe handshakes for phase and clear-frame readiness, not sleeps.
Release phase barriers from the real fixed protocol operation/nonce-observer
result in the test peer/controller wrapper, not from optional diagnostic emission
or collector success. Capture/collector loss must not change the fixture's
schedule, block its peer or create a false operational regression. Add no such
callback or handshake to product code.

**Driver integration:** Create the observer session only inside existing
acceptance_owned after resume-view binding, before the nonce challenge. Pass
the actual current probe into each scope (None before construction); late session
creation must not invent a past clear ACK. Close the session in the existing
finally on every route. Session factory/lifecycle failures disable observation
without changing rejection, callbacks, operation order or cleanup.

Scope each existing protected invocation with its actual snapshot/frame:
the transaction and following validation in resume_live separately; ready's
composed assessment after binding; context_command/probe observation in pump;
probe._check in operation_live; exit_owned; command_write's checks; and direct
context-command/probe construction, type/submit/bind/clear/proof-consumption
calls in the main dialogue. Do not move, combine or skip those calls. Keep
post-Enter input-sealed return, initial/debug/live paths and startup handling out.
Also scope the existing resumed forbidden-UI layout-error creation in pump and
auth_clear, passing its actual snapshot/frame and OTHER site. Before a view can
be bound there may be no trustworthy session; omit the optional annotation then.

Mark the clear attempt immediately before the existing concrete fixed Ctrl+U
write, after original guards and dispatch consumption. Mark ACKED only after
the existing exact one-byte successful writer-count validation. Observation
failure cannot change count, dispatch, pending bytes, retries or transport errors.
Add optional nonce_history_context to diagnose's private metadata mapping, and
project it from the actual caught exception; never recover phase from revoked
objects in the outer catch. No new checkpoint, stream or file.

- [ ] **Step 1: Write** real-driver tests in NonceHistoryDriverTests:
  test_phase_matrix_preserves_exact_input_and_outcomes (twelve cases: each kind
  across all six variants; stable/post-clear-move => exit0/32 bytes, echo variants
  => exit2/25 bytes/no clear, clear variants => exit2/26 bytes/clear ACK/no proof;
  no rejected case sends /exit). Assert literal site, nonce phase, clear status,
  evidence presence, baseline, placement and full-profile comparison.
  test_observe_first_still_rejects_moved_clearing_snapshot (two real protocol API
  cases, no driver reorder; missing clear proof and original nested history error).
  test_mutation_site_matrix_is_discriminated_without_reclassification (six cases:
  each kind, transaction/same slot, transaction/moved, ordinary/same slot; preserve
  UNOWNED_NEW_PROFILE versus PINNED_PROFILE_CHANGED exactly).
- [ ] **Step 2: Run** the new driver suite. Expected: new diagnostic assertions
  fail while existing outcome/byte-count assertions remain correct. Product
  compatibility failures are expected outcomes, not reasons to loosen guards.
- [ ] **Step 3: Implement** only the integration above. Add the new driver suite
  to validate-package.sh. Port hand-authored scratch peer logic into the maintained
  fixture, not native frames/transcripts; keep fixture-only audit substitutions
  explicitly labelled as synthetic, never real isolation evidence.
- [ ] **Step 4: Write** tests test_clear_ack_is_dialogue_bound_and_never_inferred_from_phase
  (both kinds; EAGAIN then success, I/O error, invalid count, foreign probe/dialogue);
  test_capture_loss_preserves_bytes_errors_and_cleanup (normal/absent/capture and
  collector loss under the same handshakes); test_annotation_excluded_routes_never_activate_session
  (initial/live/debug/observation/success/cleanup); test_cancellation_and_expiry_release_observation_scope
  (before guard, on write wait, during rejection and disposal). Assert process/
  helper reap and root absence for all cases; no scope or operational reference
  survives. Expected: operational equivalence. If an observation requirement
  fails, record that RED before its minimal observer-only correction; tests
  already passing are coverage, not a claimed RED/GREEN fix.
- [ ] **Step 5: Run** new unit/driver suites, test-terminal-input-challenge.py,
  test-terminal-sdk-relocation.py, test-offline-terminal-resume-safety.py,
  test-terminal-wiring.py, test-terminal-cancellation.py and
  test-headless-driver-signals.py. Expected: all pass; record counts/skips and
  measure bounded sampler overhead without changing deadlines or claiming zero
  scheduling effects. Keep unknown native profile equality and consumed grants.
  Time observer entry/exit, freezer and projector calls only with test-side
  perf_counter wrappers; report call counts and elapsed values, not a new runtime
  hook or pass/fail time threshold. Assert pure profile classification scans at
  most the existing 40 rows per failure and performs no external reads.
- [ ] **Step 6: Update** spec/plan status, ADR-010/index, CHANGELOG and validation
  notes with local implementation/results only. Preserve package version and
  native/browser/provider/remote gates. Run content, architecture-doc and
  release-history checks plus git diff --check. Expected: all pass.
- [ ] **Step 7: Commit** as `test: integrate coherent nonce history diagnostics`.

## Whole-Change Review and Immutable Gate

- [ ] Self-review every spec requirement and all five Review Focus tests; prove
  no annotation value enters an acceptance/input/relocation predicate.
- [ ] Request one fresh independent review of the immutable range from the
  planning baseline through final code, including spec/plan and execution rulings.
  Review literal sites, same-call affinity, yielded-body exceptions, optional
  budgets, clear acknowledgement and absence of behavioral expansion.
- [ ] Fix validated blocking findings by author RED/GREEN and green regressions,
  following the selected workflow's single fix-pass rule; report reviewer/fix
  commits and whether fixes were independently re-reviewed. Do not claim a
  synthetic/native acceptance merely because a review is clean.
- [ ] Run the full package gate on an immutable export of final committed source,
  through the same clean WSL environment with /bin/bash tests/validate-package.sh
  instead of the Python suite. Require exit0 and package validation passed.
  Verify archive hash plus canonical contents/types/modes before and after,
  disposable-root removal, explicit skips and absence of provider/operator state.
- [ ] Record exact source/evidence/elapsed/result, rerun document checks and
  git diff --check, and commit the result-only documentation. Prove executable
  equivalence for any docs-only successor; no behavior inherits an earlier gate.
- [ ] Hand off the local branch/worktree and the causal decision below. Do not
  publish, refresh staging, complete the definitive TODO or request repeated
  native attempts as part of local implementation.

## Causal Decision and Explicit Stop Rule

This plan implements measurement, not a root-cause fix or completed P0-04B.
The production browser boundary remains the objective; the terminal harness is
only validation infrastructure. No compatibility repair belongs in these tasks.

Only after local discrimination tests, budget proof, independent review and the
immutable gate pass may a separate exact-final-source native authorization be
proposed. It is not granted by approval of this plan. For this diagnostic cycle,
propose at most one native attempt, retaining original scope/limits and stopping
on the first inconclusive case. Never execute it automatically.

| Future coherent evidence | Required handoff, not an automatic change |
|---|---|
| Exact profile, rejection before clear completion | Evaluate the nonce/history prerequisite cycle and a separately approved phase-aware contract, or a different measurement route |
| Different full profile | Identify the strict comparison/representation conflict; extending the window alone does not address equality |
| Exact profile with observed PROVEN and evidence PRESENT | Inspect the literal rejecting predicate and other current-frame proofs; presence alone does not prove lifetime/ownership or a code defect |
| Missing/UNKNOWN/incoherent facts or another inconclusive measurement | Stop; report that this diagnostic path did not establish the cause and reassess the measurement architecture |

At that handoff, distinguish an observed native fact, a reproduced causal
mechanism and a remaining hypothesis. Choose a separately scoped causal fix or
an architectural alternative; do not append a new exception/diagnostic layer or
solicit another native authorization automatically. No result here authorizes
whitespace normalization, timeout increase, weaker proof, retry or early input.

## Rollback and Execution Handoff

Remove the new observer session/scope, failure annotation and collector handling
together, restoring the original bounded diagnostic contract without changing
original guard/revocation/cleanup logic. No rollback restores a consumed grant.

The operator reviewed the plan and selected direct/inline execution with one
fresh independent final reviewer. This selection does not approve a native run.
