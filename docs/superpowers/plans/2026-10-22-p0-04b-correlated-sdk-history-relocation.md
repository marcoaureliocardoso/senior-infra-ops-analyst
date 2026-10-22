# P0-04B Correlated SDK-History Relocation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Support one exact SDK-history relocation after proven nonce clearing,
without weakening independent input, context, lifetime or exit authorization.

**Architecture:** Separate immutable historical identity from current placement.
Evaluate a sealed, read-only placement proposal through all composed readers,
then atomically publish it only after full same-frame validation. The existing
driver coordinates this before ordinary history rejection; exit stays guarded.

**Tech Stack:** Existing Python unittest, private weak registries, immutable
terminal snapshots, Node/xterm helper, Python PTY peers and Debian WSL gates.

**Spec:** [Approved relocation specification](../specs/2026-10-22-p0-04b-correlated-sdk-history-relocation-design.md).

Status: written specification and this plan approved on 2026-10-22; operator
selected native/inline execution (option 2). Tasks 1-3 completed locally at
`d3bcc1a`, `61f222b` and `722bbe6`, with 109/72/191 focused tests respectively.
Task 4 is under regression validation; final independent review and immutable
package gate remain pending. Planning baseline: `c78997d`. No native execution
is authorized by this document or the execution-method selection.

## Global Constraints

- Only ordinary audited offline resumed `text-turn` / `skill-turn`, with matching
  SDK_TEXT / SDK_SKILL, after sealed nonce/clear completion and before exit-proof
  consumption or any exit write; at most one committed relocation per case.
- Exact entire `HistoryProfile`: kind, marker_x, gap tuple and tail tuple.
  ASCII and NBSP are different; no normalization, hashes or fuzzy matching.
- The old position remains retired; destination collisions, duplicates, profile
  changes, second movement and disappearance after commit are terminal.
- Full unchanged `ContextSample`, current receipt/witness/history, empty-input
  anchor, all original owners and lifetimes must validate on the same snapshot.
- No public flag, setting, environment variable, caller-supplied row exclusion,
  generic adapter, external callback bypass or temporary live mapping.
- No extra input, nonce, clear, timeout, pending/grace period or automatic retry.
  Preserve 25 seconds per dialogue and 165 seconds overall including the existing
  five-second cleanup reserve; keep existing SDK/request ceilings and case order.
- Keep the existing 16-character non-submitted nonce, one exact-echo Ctrl+U,
  newer empty frame, one exit-proof consumption and guarded `/exit`/natural exit0.
- Observation-only remains irreversibly read-only after Enter. Initial/live,
  provider/browser/debug and production permissions do not gain this route.
- Keep existing structural schemas/budgets: 16 records/3072 bytes per phase,
  16384 bytes for the aggregate including newline; no new diagnostic extension.
- No persisted frames, prompts, history, row text, profile hashes, credentials
  or candidates. Raw evidence/history must be disposed before aggregation.
- Cleanup failure dominates outcomes; original cancellation/deadline supervision
  spans parsing, reap, disposal and final publication. No renewed approval.
- Old native grants remain consumed. No native Claude execution, provider call,
  operator configuration/credential access or installation in these tasks.
- No package version bump for this test-only change. No push, PR, merge, release,
  staging refresh or definitive TODO completion in this plan.

## Review Focus

1. A public PROVEN phase with no real clear must not create eligibility: Task 1
   `test_public_proven_does_not_issue_clear_evidence`.
2. A source retired before the window must allow only exact new correspondence,
   never resurrection: Task 2 `test_retired_source_is_identity_not_authority`.
3. Equal rounded percentage can conceal changed Decimal numbers or metric rows:
   Task 3 `test_same_percentage_changed_sample_rejects_transaction`.
4. An early composed read can accidentally retire rows before a later failure:
   Task 3 `test_rejected_composition_never_publishes_candidate_state`.
5. A valid relocation followed by already-buffered bad output must not reach
   exit: Task 4 `test_relocation_drain_checks_every_frame_before_exit`.

## File Map

| File | Responsibility |
|---|---|
| `tests/terminal_input_challenge.py` | Sealed private clear-completion evidence, invalidation and non-circular lifetime checks |
| `tests/terminal_resume_history.py` | Immutable baseline identity, candidate registry, read-only history projection, atomic commit and monotonic tombstones |
| `tests/terminal_context_echo.py` | Candidate-aware composed readers, unchanged current receipt/display proof and protected-row inventory |
| `tests/headless_context_driver.py` | Invoke one synchronous transaction before strict history validation on eligible frames |
| `tests/resume_history_fixtures.py` | Owned resumed fixture plus deterministic PTY and namespace peers |
| `tests/test-terminal-input-challenge.py` | Clear evidence and existing input protocol regressions |
| `tests/test-terminal-sdk-relocation.py` (new) | Candidate, composition, replay, atomicity and lifetime matrix |
| `tests/test-headless-context-driver.py`, `tests/test-offline-terminal-resume-safety.py` | Concrete input, routing, aggregation and disposal regressions |
| `tests/validate-package.sh` | Include the new unit suite in the existing complete gate |
| ADR-010/index, spec/plan, CHANGELOG, validation notes | Separate design approval, implementation, review, synthetic gate and native compatibility status |

Keep the existing driver, history and echo boundaries; no unrelated module
split. Reuse `sample_context`, existing exception reasons and fixed synthetic
profiles. No production module or observation implementation is a change target.

## Environment and Commands

Before implementation, use the worktree skill to verify the existing linked
`p0-04b-browser-automation` worktree, branch, HEAD/common Git directories and
operator changes. Preserve unrelated edits and consumed attempt markers. Host
Git uses command-local `-c safe.directory=<absolute-worktree>` only.

Focused suite commands below use this PowerShell launcher; replace only its
last argument with the named test file. Pass unittest selectors as extra args.

```powershell
$relocationTestArgs = @(
  '-d', 'Debian', '--cd',
  '/mnt/c/projects/senior-infra-ops-analyst/senior-infra-ops-analyst/.worktrees/p0-04b-browser-automation',
  '--', 'env', '-i', 'HOME=/tmp',
  'PATH=/home/marco/.local/opt/node-v24.17.0-linux-x64/bin:/usr/bin:/bin',
  'PYTHONNOUSERSITE=1', 'PYTHONDONTWRITEBYTECODE=1',
  'P004B_TERMINAL_NODE=/home/marco/.local/opt/node-v24.17.0-linux-x64/bin/node',
  'P004B_TERMINAL_MODULE_ROOT=/mnt/c/projects/senior-infra-ops-analyst/.review-runtime/p004b-terminal-state/node_modules',
  '/usr/bin/python3', 'tests/test-terminal-input-challenge.py'
)
& wsl.exe @relocationTestArgs
```

These are verified-local dependency routes, not product/runtime version pins.
Check their presence read-only before tests. No bare PowerShell `bash`, operator
Claude settings or dependency installation. RED must be a behavioral assertion,
not a missing import, symbol or runtime. Define a failing public test assertion
before implementing its private API; use guarded lookup where necessary.
GREEN means exit0/unittest OK with no unexpected skips. Track task steps in the
native task list if available, otherwise keep these checkboxes truthful.

### Task 1: Sealed Clear-Completion Provenance

**Files:** Modify `tests/terminal_input_challenge.py` around `NonceInputChallenge`
initialization, `_check`, `observe`, `invalidate` and `consume_exit`; test in
`tests/test-terminal-input-challenge.py`.

**Interfaces:** Add private sealed `_NonceClearEvidence` (opaque, non-copyable,
non-serializable handle) and `_nonce_clear_evidence(probe, *, state, scope,
native_owner, controller_owner, transition_owner) -> _NonceClearEvidence | None`.
Add `_validate_nonce_clear_evidence(evidence, *, probe, state, scope,
native_owner, controller_owner, transition_owner) -> None`; invalid evidence
raises the existing `InputProofError`. Neither function evaluates history or
returns an input grant. Preserve all public nonce method signatures.

- [ ] **Step 1: Add failing tests** named
  `test_public_proven_does_not_issue_clear_evidence`,
  `test_clear_evidence_requires_real_echo_clear_and_new_empty_frame` and
  `test_clear_evidence_is_bound_revocable_and_not_exit_authority`.
  Assert ELIGIBLE/ECHO_MATCHED/CLEAR_PENDING and forged PROVEN yield no evidence;
  real completion yields one opaque registered handle. Wrong owner/scope,
  cancellation/expiry, consumed/revoked proof, copied/serialized handle and
  restored public phase reject. Obtaining/validating it neither consumes exit
  nor calls the position-only history validator; ordinary exit still does.
  Core assertions after fixture setup:

  ```python
  self.assertIsNone(before_clear)
  self.assertIsNotNone(after_real_clear)
  self.assertIs(probe._proof, original_exit_proof)
  self.assertFalse(challenge_module._CHALLENGES[probe]['consumed'])
  ```
- [ ] **Step 2: Run** `tests/test-terminal-input-challenge.py`; demonstrate the
  new behavioral assertions fail for missing genuine completion provenance.
- [ ] **Step 3: Implement** the interfaces above. Mint evidence only in the
  actual CLEAR_PENDING-to-PROVEN branch; privately bind the real proof identity,
  completion frame, original anchor/owners/run/deadline and challenge record.
  Split non-history lifetime checks from `_check` for reuse, preserving `_check`
  behavior. Check private issuance/consumption, not public phase alone. Remove
  evidence on invalidation, consumption and case teardown; expose no raw nonce.
- [ ] **Step 4: Run** input-challenge, resume-history and context-echo suites;
  verify GREEN and unchanged ordinary proof/exit behavior.
- [ ] **Step 5: Commit** only Task 1 files as
  `test: seal resumed nonce clear completion evidence`.

### Task 2: Exact Non-Authoritative History Projection

**Files:** Modify `tests/terminal_resume_history.py` around view binding,
validation, `_history_indices` and case closure; create
`tests/test-terminal-sdk-relocation.py`; extend `tests/resume_history_fixtures.py`;
add the new test command beside resume-history in `tests/validate-package.sh`.

**Interfaces:** Add private sealed `_SDKRelocationCandidate` and
`_prepare_sdk_relocation(view, probe, evidence, receipt, *, policy, snapshot,
frame, state, scope, native_owner, controller_owner, transition_owner)
-> _SDKRelocationCandidate | None`. Extend `validate_resume_view` only with
private `_history_read=None`, accepting an exact live candidate, never a map or
row list. No publication API is activated in the driver in this task.

- [ ] **Step 1: Extend `CaseFixture`** with `proven_resume() -> dict`, exercising
  real initial completion, validated SDK, owned resumed context, nonce echo and
  clear using existing public protocol methods. Return named bindings `view`,
  `command`, `receipt`, `probe`, `snapshot`, `frame`, `evidence`; do not mint
  capabilities by registry injection. Support both fixed case kinds.
- [ ] **Step 2: Add failing `SDKRelocationTests`** with
  `test_exact_candidate_is_read_only_and_not_an_exclusion_grant` and
  `test_retired_source_is_identity_not_authority`. Assert stable SDK gives None;
  exact one-row move prepares a candidate with no live map/retirement/used-state
  mutation, while default validation still rejects the moved frame. Allow
  exact correspondence from an already retired source but reject return at its
  old row. Add `test_candidate_identity_collision_and_replay_matrix`: mutate
  kind/marker/gap/tail, ASCII/NBSP, cell width, duplicates, first-late SDK,
  geometry, source/destination, owner/frame and a copied handle; all reject.
  Use a fresh case for each rejection because rejection revokes the whole case.
  Candidate preparation's read-only assertions are:

  ```python
  self.assertIsNotNone(candidate)
  self.assertEqual(record['profiles'], original_profiles)
  self.assertEqual(record['retired'], original_retired)
  self.assertFalse(record['sdk_relocated'])
  ```
- [ ] **Step 3: Run** the new suite and reproduce failing behavioral assertions.
- [ ] **Step 4: Implement** candidate preparation as a private pure proposal:
  preserve immutable original SDK identity, separate placement and monotonic
  retired inventory. Name the new private view fields `sdk_identity`
  (original index/profile pair or None), `sdk_position` (current index or None)
  and `sdk_relocated` (initially False); leave `profiles` as the original map.
  A private weak candidate registry must be purged by case closure/revocation.
  Stage frame/time/retirement changes rather than mutating
  live records. Candidate validation must use the exact snapshot/owners and
  sealed Task 1 evidence, reject all disallowed history and expose only the
  coherent projected indices to internal readers. Missing/invalid eligibility
  must never convert ordinary rejection into None. None means no SDK placement
  change to propose. Preserve legacy diagnostics and observation guard behavior.
- [ ] **Step 5: Run** new relocation, resume-history, failure-diagnostic and
  input-challenge suites; verify GREEN and cleanup of private candidates.
- [ ] **Step 6: Commit** Task 2 files as
  `test: model exact one-shot SDK history relocation candidates`.

### Task 3: Composed Same-Frame Commit

**Files:** Modify `tests/terminal_context_echo.py`,
`tests/terminal_resume_history.py`;
test in `tests/test-terminal-sdk-relocation.py`.

**Interfaces:** Add `_sdk_relocation_protected_rows(receipt, *, view, snapshot,
frame, state, scope, native_owner, controller_owner, transition_owner)
-> frozenset[int]` in echo: internal inventory only, not authority. Add private
`_history_read=None` propagation through echo `_live`, `_resume_indices`,
`_validate_resumed_display`, `validate_context_history`, `assess_context_input`
and `_compose_input_assessment`; defaults preserve existing behavior.
Add `_try_commit_sdk_relocation(view, probe, receipt, *, policy, snapshot, frame,
state, scope, native_owner, controller_owner, transition_owner) -> bool` in
history. False means no eligible placement change; rejection raises existing
closed errors after revocation. True means one atomic commit, not an exit grant.

- [ ] **Step 1: Add failing tests**
  `test_exact_relocation_commits_only_after_complete_same_frame_assessment`,
  `test_same_percentage_changed_sample_rejects_transaction` and
  `test_rejected_composition_never_publishes_candidate_state`.
  For both kinds, assert valid commit preserves original exit-proof identity and
  permits its later independently validated consumption. Changing Decimal free/
  buffer with unchanged rounded used percentage, sample rows, witness, receipt,
  context row or input anchor rejects before publication. Place a valid SDK
  candidate before an unknown/auth/menu row to prove complete scanning.
  For the valid transaction and a fresh negative case respectively:

  ```python
  self.assertTrue(committed)
  self.assertTrue(record['sdk_relocated'])
  self.assertIn(old_index, record['retired'])
  self.assertIs(probe._proof, original_exit_proof)
  self.assertEqual(history.resume_view_decision(rejected_view), 'REJECTED')
  ```
- [ ] **Step 2: Add failing** `test_transaction_lifetime_replay_and_collision_matrix`
  and `test_committed_placement_is_unique_stable_and_monotonic`.
  Exercise every protected destination: cursor/input, owned context, heading/
  metrics, other pinned/retired/pre-Enter inventory. Deterministically inject
  stale frame, cross-case/session, frame advancement, cancellation, expiry and
  reentrancy immediately before commit, and lifetime loss after commit before
  exit. Assert no published partial map/tombstone/used flag on rejection, then
  revoked case/proofs. After success reject disappearance, mutation, second move
  and source return; no candidate can be reused or consume exit twice.
- [ ] **Step 3: Run** the relocation suite to confirm behavioral RED.
- [ ] **Step 4: Implement** the interfaces above. The protected inventory is
  derived from the registered receipt, original display tracker/pre-Enter
  inventory, current and bound full sample, cursor, pinned rows and tombstones;
  an invalid receipt never supplies trusted inventory. This inventory helper
  checks exact registry/owner bindings without calling `_live` or the old
  position-only validator on the moved frame; full live validation follows
  under the candidate overlay. Thread the sealed proposal
  explicitly through every nested history/display reader, including `_live`;
  candidate reads stage or omit live metadata writes and cannot retire rows.
  Validate Task 1 provenance, unchanged complete sample/witness/receipt and
  composed empty-input anchor against that single actual snapshot. Recheck live
  owner/frame/deadline and commit placement+tombstone+used state synchronously
  with no callback, I/O or asynchronous gap. Failed proposals revoke terminally.
- [ ] **Step 5: Run** relocation, resume-history, input-challenge, context-echo,
  context-display, history-rejection and post-Enter-observation suites; verify
  GREEN, defaults unchanged and no new structural output.
- [ ] **Step 6: Commit** Task 3 files as
  `test: compose exact SDK relocation transactions`.

### Task 4: Real-Driver Synthetic Lifecycle and Delivery Gates

**Files:** Modify `tests/headless_context_driver.py`, `tests/resume_history_fixtures.py`,
`tests/test-headless-context-driver.py`, `tests/test-offline-terminal-resume-safety.py`,
`tests/validation-notes.md`, `CHANGELOG.md`, ADR-010/index and this spec/plan.
No outer aggregator behavior change is planned; regress its existing lifecycle.

**Interfaces:** Extend `write_context_peer(..., mode=..., barrier_fd=..., case_kind=...)`
with deterministic post-clear relocation modes, reusing the existing pipe
barrier after `input_probe_cleared`. Extend `write_fake_cli(path, *, mode)` for
namespace positive/negative trajectories. All are fixed Python peers, not
installed Claude; retain existing driver and report interfaces.

- [ ] **Step 1: Extend the fixed peer fixtures, then add failing driver tests**
  `test_relocation_reaches_natural_exit_with_exact_protocol_bytes`,
  `test_relocation_drain_checks_every_frame_before_exit` and
  `test_relocation_partial_writes_do_not_reopen_input`.
  For both kinds, exact move must produce context+one Enter, 16 non-submitted
  nonce bytes, one Ctrl+U and guarded `/exit\r`, with natural exit0. Compare byte
  counts without exporting nonce content. Negative peers mutate padding,
  duplicate, return or move again, and queue a bad frame after a valid one;
  assert zero exit bytes before consumption, or no remaining bytes after a
  failure during guarded partial exit. Leaders/helper must be reaped.
  Assertions on private peer input (never exported):

  ```python
  self.assertEqual(result, 0)
  self.assertEqual(data[:9], b'/context\r')
  self.assertEqual(len(data[9:25]), 16)
  self.assertEqual(data[25:], b'\x15/exit\r')
  self.assertTrue(all(child.poll() is not None for child in children))
  self.assertTrue(f.state.helper_reaped)
  ```
- [ ] **Step 2: Add failing namespace tests**
  `test_relocation_cases_require_full_proofs_and_disposal` and
  `test_relocation_inconclusive_stops_before_skill_case`.
  Assert both positive cases require every existing proof and natural exit;
  negative text stops before skill. Cancellation/expiry at candidate/commit/
  report-read/teardown, helper death and cleanup failure never publish success.
  Assert original 165-second budget, bounded structural schema, no raw files,
  and roots absent before aggregation. Regression-test observation zero-input,
  initial/live/debug routing and diagnostics loss without acceptance changes.
- [ ] **Step 3: Run** the driver and offline suites, reproducing behavioral RED:
  the exact moved SDK still fails ordinary fixed-position validation before exit.
  Then integrate `_try_commit_sdk_relocation` in driver `resume_live()` before
  its ordinary `validate_resume_view` call, only with the actual resumed probe
  and receipt after genuine completion and before consumption. Do not use public
  PROVEN alone to authorize it. Perform normal strict validation and
  `probe.observe` afterward; existing proof consumption/write gates use only
  the committed view. Do not add candidate parameters to public nonce methods
  or exit writers. Pre-proof/observation-only paths retain strict validation.
  Stop for design review if broader production/outer lifecycle changes are needed.
- [ ] **Step 4: Run** driver, offline-safety, claude-PTY-driver, cancellation,
  headless-signals, structural-diagnostics and observation-report suites; require
  GREEN and truthful platform/capability skips. This is synthetic execution only.
- [ ] **Step 5: Update** ADR/index, CHANGELOG and validation notes with actual
  local implementation/results, not native acceptance. Keep version unchanged;
  the existing Unreleased section is the only changelog target. Mark task steps
  only when evidenced; retain consumed grants and unknown native equality.
- [ ] **Step 6: Run** content, architecture-docs and release-history checks plus
  `git diff --check`; commit as `test: integrate SDK relocation with guarded driver lifecycle`.

## Whole-Change Review and Immutable Gate

- [ ] Self-review every spec requirement against Tasks 1-4 and every Review Focus
  test. Recheck all nested history readers, atomicity, fixed input and rollback.
- [ ] Request one fresh independent whole-change review of the immutable range
  from `c78997d` to the final implementation, using the selected workflow's review
  skill. Review the spec/plan, input authority, replay/collision and disposal.
- [ ] Reproduce validated findings with author RED/GREEN tests and correct them.
  Record reviewer and fix commits and whether corrections were independently
  re-reviewed; author verification is not independent review.
- [ ] Run the complete gate on immutable corrected committed source: use the
  launcher above with its final two arguments replaced by `/bin/bash` and
  `tests/validate-package.sh`. Require exit0 and `package validation passed`.
  Record exact commit, tests/skips and canonical contents/types/modes before and
  after; store transient gate artifacts outside Git without operator state.
- [ ] Rerun documentation checks after recording the gate. For docs-only commits,
  prove executable-source equivalence to the gated commit; no behavior inherits
  an earlier gate. Report remote CI/Security and platform exclusions separately.
- [ ] Hand off final source and remaining native/browser/provider gates. No new
  native run occurs until fresh final-commit authorization; strict native profile
  equality can still fail. Do not retry automatically or mark P0-04B completed.

## Rollback and Handoff

Remove the driver transaction call and its private candidate/composition path
together to restore strict fixed-position rejection. Keep ordinary nonce,
history, context and observer guards; never resurrect a retired position or
consumed grant. No rollback run is implicit permission to execute native Claude.

Coverage mapping: completion provenance to Task 1; exact identity/retirement to
Task 2; protected inventory, same-frame composition, atomicity and stable exit
to Task 3; concrete I/O, cleanup, routing and aggregation to Task 4. Final review
and immutable gate cover the cumulative behavior. Native compatibility remains
a separate experiment, not a promised consequence of this plan.

The operator reviewed the plan and selected native/inline execution. This
preserves the tightly coupled private interfaces under one implementer, with a
fresh independent final review still required. No native attempt is included.
