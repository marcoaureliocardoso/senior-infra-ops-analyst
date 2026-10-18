# P0-04B Resumed-History View Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the offline initial-dialogue/SDK/resume regression using new, case-bound history evidence without transferring input or credential authority.

**Architecture:** One private test-only component separates pure fixture/SDK classification from case witnesses and resumed-view lifetime. The
selected driver produces initial completion facts and composes a fresh resumed view with existing command/menu/nonce proofs. The offline supervisor
alone joins actual process results and stream validation; serialized output cannot activate that path.

**Tech Stack:** Existing Python unittest, controlled Python PTY/CLI peers, passive Node/xterm and Debian WSL. No new dependency, provider client or installed runtime.

**Spec:** [Approved resumed-history specification](../specs/2026-10-17-p0-04b-resumed-history-view-design.md).

## Global Constraints

- Written specification operator-approved. This plan awaits review and execution-method selection; no implementation or native execution is approved by this file.
- Planning baseline: `2f9891db26198ddf22ab907dcf3d40d5a58dfcd3`. Record the exact clean HEAD after plan approval as the execution baseline; review the complete implementation range from it, not main or HEAD~1.
- Reuse the linked `p0-04b-browser-automation` worktree. Preserve operator changes, use command-local Windows Git safe.directory and do not use WSL Git.
- Audited offline scope only: loopback only, hidden operator state, dropped capabilities, disposable HOME/config/project/history. No production session, provider request, operator credential/configuration read or new public activation interface.
- Keep at most two cases, 25 seconds per context dialogue and SDK process, existing SDK `--max-turns 4`, and gateway rejection beyond four messages per case. Keep the original 165-second enclosing run ceiling; no renewal, relaunch or repetition.
- Keep the current text fixture. The offline skill fixture is exactly `P0-04B synthetic. Invoke Skill(context-continuity) once; reply P004B_SKILL_OK. No browser.` Live/provider-backed prompts remain unchanged.
- New witnesses/views are branded in-process objects, not JSON, flags, IDs, event files, diagnostics or shape matches. Old scopes, receipts and InputOwnershipProof never transfer.
- The fresh view binds case/root/session/invocation, current terminal/native/scope/run/controller/transition, original current deadline and parsed frames. Root identity is rechecked at the concrete-write boundary.
- Each expected history kind has at most one complete, captured, off-cursor physical row: 120 width-one cells, ASCII indentation and ASCII-space/NBSP padding. Reject tabs, wide/format/control cells, wrapping, truncation, unknown markers and drafts.
- BOUND history cannot disappear or move. Only an acknowledged current `/context` Enter permits POST_SUBMIT retirement; a retired or initially absent old kind cannot be adopted later. Ambiguous old/new ownership rejects.
- Share one ordered assessment over the same consumed frame after validating every exclusion. Never overwrite raw snapshots, permit caller-supplied exclusion lists, or bypass current input, echo, numeric-freshness, nonce or `/exit` checks.
- Keep exactly eight `/context` bytes, one owned Enter, 16 unsubmitted hex characters, one guarded Ctrl+U and owned `/exit` plus one Enter. No fallback key, second Enter or `/exit` menu exception.
- Keep 16 records/3072 bytes per structural phase and 16384 bytes per complete report. No new prompt/row/transcript/hash/session/nonce retention or debug-content permission.
- Default/live callers remain strict. Only one additional reviewed source module may be mounted read-only through the existing individual-file allowlist; no broader mount, installation, dependency or preference change.
- Root/component versions stay unchanged for this test-only scope. English documentation only. Do not mark the definitive unversioned TODO complete.
- The b5e0e55 native grant is consumed. Real Claude/provider/browser execution, push, PR, merge, release and external workflow writes require separate authority. Synthetic results are not native acceptance or remote CI/Security.

## Review Focus

1. A resumed API-key/theme/trust screen must not inherit the initial dialogue's automatic startup keys; Task 4 tests zero writes with a pending resume offer.
2. An owned root can be replaced during a writable wait; Task 4 tests a fresh identity check before the next concrete write and irreversible revocation.
3. Valid history, a correlated menu and another unknown marker can coexist; Task 3 tests one assessment and the actual remaining rejecting row/debug provenance.
4. Retired `/context` history can collide with a fresh command's row; Task 3 tests ambiguity rejection, no baseline-row promotion and no numeric freshness from exclusion.
5. Exit-zero SDK output can name another session, hide a nested call or substitute an earlier stream; Tasks 1 and 5 test rejection before resume and descriptor-bound output rather than a reopened path.

---

## File boundaries and verification route

Create `tests/terminal_resume_history.py` for the pure profiles/SDK parser and
private case/view registries. Keep those sections explicit; classifiers do no IO,
while the issuer's root/lifetime checks inspect only its owned disposable case.
No constructor or API accepts a serialized capability or arbitrary row indices.

Create `tests/test-terminal-resume-history.py` and the test-only helper
`tests/resume_history_fixtures.py`. The helper owns `history_snapshot`,
`sdk_stream`, `CaseFixture` and `write_fake_cli`; no test-only factory belongs in
the runtime component. Do not mount this helper into the native namespace.

Modify existing policy/echo/challenge/driver/collector/launcher/wiring tests only
at the integration boundaries named below. Do not restructure unrelated files.
Documentation closeout owns this plan/spec, ADR-010, CHANGELOG and validation notes.

All Python and full-gate commands below use this clean host PowerShell route,
changing only the final command. Verify these runtime paths still exist; they
are observed test locations, not product version requirements.

```powershell
wsl.exe -d Debian `
  --cd /mnt/c/projects/senior-infra-ops-analyst/senior-infra-ops-analyst/.worktrees/p0-04b-browser-automation `
  -- env -i HOME=/tmp `
  PATH=/home/marco/.local/opt/node-v24.17.0-linux-x64/bin:/usr/bin:/bin `
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 `
  P004B_TERMINAL_NODE=/home/marco/.local/opt/node-v24.17.0-linux-x64/bin/node `
  P004B_TERMINAL_MODULE_ROOT=/mnt/c/projects/senior-infra-ops-analyst/.review-runtime/p004b-terminal-state/node_modules `
  python3 tests/test-terminal-resume-history.py
```

Use explicit scripts, not discovery. If WSL is sandbox-denied, use the authorized
bounded WSL route; do not try bare Bash or change execution policy. Expected
GREEN is unittest OK/exit 0, with every warning/skip reported. Expected RED is
the named missing behavior, not a syntax/import/dependency error. Use apply_patch
for source edits and stage only task-owned paths with command-local Git safety.

### Task 1: Pure history profiles and SDK validation

**Files:** Create `tests/terminal_resume_history.py`,
`tests/test-terminal-resume-history.py`, `tests/resume_history_fixtures.py`;
modify `tests/validate-package.sh` to run the new suite after the input-policy suite.

**Interfaces:**

- Define `TEXT_PROMPT` as the current exact text fixture and `SKILL_PROMPT` as the spec's short fixture.
- Define frozen `HistoryProfile(kind: str, marker_x: int, gap: tuple[int, ...], tail: tuple[int, ...])` and `SDKFacts(valid: bool, reason: str, skill_calls: int)`.
- Produce `match_history_row(row: tuple[TerminalCell, ...], kind: str) -> HistoryProfile | None` for `CONTEXT`, `EXIT`, `SDK_TEXT`, `SDK_SKILL` only.
- Produce `parse_sdk_sample(raw: bytes, *, expected_session: str, case_kind: str) -> SDKFacts` for `text-turn`/`skill-turn` only. Facts are ordinary immutable data, never branded authority.
- Test helper `history_snapshot(history: tuple[tuple[int, str], ...] = (), *, cursor_row: int = 37) -> TerminalSnapshot` builds 40x120 width-one cells with an empty cursor row; `sdk_stream(session: str, case_kind: str) -> bytes` builds hand-authored valid init/message/result events.

- [ ] Verify isolation/HEAD/clean status with local Git, preserve any operator delta, and run existing `test-terminal-input-policy.py`, `test-terminal-context-echo.py` and `test-terminal-input-challenge.py` as the baseline. Stop and report an unexplained failure before edits.
- [ ] Add `test_public_fixture_profiles_are_complete_and_content_free` and `test_sdk_text_and_skill_require_session_lifecycle_and_exact_calls`. Load the new module behind an assertion that its file exists, so the initial RED names the missing component rather than crashing import.

  ```python
  self.assertIsNotNone(match_history_row(history_snapshot(((5, '❯ /context'),)).rows[5], 'CONTEXT'))
  self.assertIsNone(match_history_row(history_snapshot(((5, '❯ /context extra'),)).rows[5], 'CONTEXT'))
  facts = parse_sdk_sample(sdk_stream('synthetic-session', 'text-turn'), expected_session='synthetic-session', case_kind='text-turn')
  self.assertEqual((facts.valid, facts.reason, facts.skill_calls), (True, 'VALID', 0))
  ```

- [ ] Add independent tables for 119/121 cells, width 0/2, multi-character token cells, Cf/control/tab, NBSP vs ASCII padding, duplicate markers and
  truncated/wrapped prompts. Assert None for invalid profiles and no source text in the profile repr. For SDK input assert rejection of
  wrong/missing/duplicate init/result, wrong session on any session-bearing event, failure result, nested/unexpected calls, unmatched/failed tool
  result and calls after terminal result.
- [ ] Run the new suite RED. Implement only these pure functions/constants/types. Inspect raw cells before trimming; treat empty width-one display
  cells as ASCII space, preserve gap/tail SPACE=0 versus NBSP=1 geometry, and require at least one gap cell. Never retain arbitrary cell text. Bound
  SDK bytes at the existing 5,000,000-byte stream limit, reject duplicate JSON keys/nonfinite constants, cap nesting at 32, events at 4096 and content
  blocks at 64.
- [ ] Accept SDK envelope types `system`, `assistant`, `user`, `result` only for this initial supported profile. Require matching session identity,
  one initial `system/init`, one final `result/subtype=success/is_error=false`, no nested message owner, and exact text-zero-tool or
  skill-one-call/result semantics. Unknown envelopes fail closed. SDK reason values are `VALID`, `BOUNDS`, `MALFORMED`, `SESSION_MISMATCH`,
  `LIFECYCLE`, `TOOL_CONTRACT`; invalid call counts saturate at 4 and never become success.
- [ ] Add `test_classifiers_do_not_open_files_spawn_or_mutate_input`; run new suite and policy suite GREEN. Register the suite in the package gate and commit as `test: add pure resumed-history profiles and SDK validation`.

### Task 2: Case witnesses and one-shot fresh views

**Files:** Extend `tests/terminal_resume_history.py` and its new suite/helper;
modify `tests/terminal_input_policy.py`, `tests/terminal_context_echo.py`,
`tests/terminal_input_challenge.py` and their focused suites for the fact boundaries below.

**Interfaces:** Consume Task 1 types/functions. Define branded, weak-registry-backed
`OfflineCase`, `InitialCompletionSink`, `PendingInitialCompletion`, `SDKLaunch`,
`ResumeOffer`, `ResumedHistoryView`, and `ResumeHistoryError(RuntimeError)`.
All constructors reject direct/serialized construction; repr contains only type.

Produce these private module interfaces (keyword bindings are exact):

```python
create_offline_case(root: Path, *, session_id: str, case_kind: str, owner: object) -> OfflineCase
initial_completion_sink(case: OfflineCase, *, state: TerminalState, scope: OfflineProbeScope, command: tuple[str, ...]) -> InitialCompletionSink
validate_initial_sink(sink: InitialCompletionSink, *, state: TerminalState, scope: OfflineProbeScope, command: tuple[str, ...]) -> None
bind_initial_sink(sink: InitialCompletionSink, *, controller_owner: object, native_owner: object, transition_owner: object) -> None
capture_initial_completion(sink: InitialCompletionSink, *, controller_owner: object, state: TerminalState, scope: OfflineProbeScope, native_owner: object, transition_owner: object, context_command: OwnedContextCommand, probe: NonceInputChallenge, frame: int, exit_written: int) -> PendingInitialCompletion
finish_initial_completion(pending: PendingInitialCompletion, *, result: int, native_cleanup: str, helper_cleanup: str) -> None
sdk_started(case: OfflineCase, *, child: object, command: tuple[str, ...], stream: BinaryIO) -> SDKLaunch
sdk_finished(launch: SDKLaunch) -> SDKFacts
offer_resume(case: OfflineCase, *, state: TerminalState, scope: OfflineProbeScope, command: tuple[str, ...]) -> ResumeOffer
validate_resume_offer(offer: ResumeOffer, *, state: TerminalState, scope: OfflineProbeScope, command: tuple[str, ...]) -> None
try_bind_resume_view(offer: ResumeOffer, *, policy: TerminalInputPolicy, snapshot: TerminalSnapshot, frame: int, native_owner: object, controller_owner: object, transition_owner: object) -> ResumedHistoryView | None
validate_resume_view(view: ResumedHistoryView, *, policy: TerminalInputPolicy, snapshot: TerminalSnapshot, frame: int, state: TerminalState, scope: OfflineProbeScope, native_owner: object, controller_owner: object, transition_owner: object) -> frozenset[int]
finish_resume_view(view: ResumedHistoryView) -> None
revoke_resume_view(view: ResumedHistoryView) -> None
resume_view_decision(view: ResumedHistoryView) -> str
close_offline_case(case: OfflineCase) -> None
```

Import `BinaryIO` from typing. Use postponed annotations and local proof-component imports to avoid a cycle
when the collector/journal imports the closed resume reason constants.
Task 2 implements PENDING/BOUND validation and cleanup only; Task 3 owns the
registered command-backed POST_SUBMIT transition and retirement.
The returned index set is private validation output, not an argument to a
capability-aware public method. Case facts never contain a row, nonce, transcript
or reusable old proof. Root checks use lstat device/inode/UID/directory identity,
reject links and verify the owned project cwd; namespace audit precedes issuance.

- [ ] Add context-managed fixture `CaseFixture` with root/case/state/scope/policy/native/controller/transition/sink and exact `resume_command:
  tuple[str, ...]` bindings. Methods `complete_initial() -> None` and `validate_sdk(case_kind: str) -> SDKFacts` drive real component state
  transitions; exit revokes the case and closes owned test resources. Reuse existing echo/challenge cell recipes, not a test-mode production
  constructor. Unit process-lifetime doubles are not transport/native evidence; Task 4/5 cover real Python children.
- [ ] Add RED tests `test_case_cannot_advance_from_events_exit_flags_or_sdkfacts`, `test_foreign_replayed_and_serialized_bindings_reject`, and `test_initial_completion_requires_consumed_proof_exact_exit_and_cleanup`.

  ```python
  with self.assertRaises(ResumeHistoryError):
      offer_resume(uncompleted.case, state=uncompleted.state, scope=uncompleted.scope, command=uncompleted.resume_command)
  self.assertFalse(hasattr(SDKFacts(True, 'VALID', 0), 'offer_resume'))
  self.assertEqual(parse_sdk_sample(b'{}\n', expected_session='synthetic-session', case_kind='text-turn').valid, False)
  ```

- [ ] Add `_initial_context_facts(command, *, state, scope, native_owner, transition_owner) -> tuple[int, int]` in the echo component. Query its
  private registry, exact bindings, `RECEIPT_READY`, eight acknowledged/echoed bytes and the actual submission path; return `(8, 1)` only as a
  completion fact after natural exit, not live authority. Do not invoke the live-owner validator, which correctly rejects an exited process. Add
  `_initial_nonce_completed(probe, *, state, scope, native_owner, transition_owner) -> bool` in the challenge component: exact type/scope
  registry/bindings, CONSUMED state and cleared marker/proof, not a copied object or writable public phase alone.
- [ ] Implement the case/sink logic using those fact boundaries. Capture a private pending fact before finally invalidates old command/probe; finalize
  only after driver result 0, exact six exit bytes, native poll 0, native/helper CLEANUP_COMPLETED and helper reaped. Do not keep command/probe/raw
  references in the finalized case ledger. Reject wrong/late/duplicate completion and cleanup-deadline results even when leaders are reaped.
- [ ] Implement SDK witness joining only after initial completion. Bind the actual supervisor-launched child identity, exact fixed
  argv/session/project descriptor and exclusively opened owned stdout stream. `sdk_finished` reads the actual completed returncode and that still-open
  descriptor, checks fstat identity and parses it internally. A caller-provided SDKFacts, replacement child or reopened stream path cannot
  independently advance the case. The producer is the trusted supervisor, not an arbitrary data adapter.
- [ ] Implement one offered resume and fresh binding. Add private `TerminalInputPolicy._input_is_fresh() -> bool` and reuse it in existing raw
  readiness and binding. Add `_empty_input_assessment(snapshot, excluded_row=None, *, _excluded_rows=frozenset())` as the shared private multi-row
  primitive; public/default methods remain unchanged. Only genuine witness/profile validation supplies its bounded disjoint indices, never a
  caller-facing row list.
- [ ] `try_bind_resume_view` returns None only while raw freshness or an operational marker is not yet available;
  auth/menu/draft/unsupported/ambiguous operational frames revoke. A valid history-free view is a branded object, never None/passive fallback. Add
  `test_history_profiles_pin_once_before_submission`: early disappearance/replacement/movement, restoration and newly appearing absent kinds revoke.
  Same frame number requires the same actual snapshot identity; later frames are monotonic. Root/owner/case/deadline/cancellation loss revokes.
  Post-submission cases belong to Task 3.
- [ ] Implement `close_offline_case` as idempotent irreversible revocation/release of case, sink, pending, SDK, offer and view references;
  process/descriptor closing remains the supervisor's responsibility. Use closed error reasons `RESUME_HISTORY_SCOPE_REJECTED`,
  `RESUME_HISTORY_SDK_REJECTED`, `RESUME_HISTORY_LAYOUT_REJECTED`, `RESUME_HISTORY_REPLAY_REJECTED`, `RESUME_HISTORY_REVOKED`. Errors contain no
  dynamic content. Run new, policy, echo and challenge suites RED/GREEN, then commit as `test: bind completed offline cases to fresh resume views`.

### Task 3: One composed assessment across proof consumers

**Files:** Modify `tests/terminal_input_policy.py`, `tests/terminal_context_echo.py`,
`tests/terminal_input_challenge.py`, `tests/terminal_context_debug.py`;
test existing policy/echo/challenge/debug suites and the new resume suite.

**Interfaces:** Consume Task 2 view/validation API. Add optional private
`_resume_view=None` to `begin_context_command`, `NonceInputChallenge.__init__`,
`assess_context_input`, `validate_context_history` and the later exit helper.
Add `_controller_owner=None` to those same private boundaries so every view
consumer supplies the actual controller identity, not an inferred diagnostic.
Preserve prior argument/default behavior. Store the view/controller in the original owned
command record; no caller can swap it after construction.

Produce `_compose_input_assessment(policy, actual_snapshot, *, frame, state,
scope, native_owner, controller_owner, transition_owner, resume_view=None,
context_receipt=None, context_command=None, normalized_snapshot=None)` returning
`tuple[EmptyInputAssessment, int | None, ContextRejectionObservation | None]`.
This private echo-component helper has no index-list argument. It obtains
validated resume/history/menu indices itself and rejects overlap.
Also produce `note_resume_submission(view: ResumedHistoryView, *, command: OwnedContextCommand) -> None`
and `_register_resume_dependent(view: ResumedHistoryView, dependent: object) -> None`
in the resume component. Accept only actual registered command/probe dependents
with matching bindings. Registration does not grant or extend authority.

- [ ] Write `test_history_menu_and_unknown_row_use_one_ordered_assessment` and `test_retired_baseline_row_cannot_be_promoted_to_new_history` RED.
  Compose a valid SDK row, a proven eight-byte completion menu and a different unknown row; assert the unknown row's actual index/cause, not an
  excluded row. Assert default `empty_input_anchor` still returns None on the same historical frame.
- [ ] Consume Task 2's shared multi-row primitive through the new private composition boundary. Validate exact index types/ranges/disjointness before
  the call, retaining raw whole-screen auth/menu checks and exactly one cursor-bound empty candidate. No second parser or diagnostic projection
  participates in authority.
- [ ] Implement composition on the original consumed snapshot before normalization. Existing command/nonce prefix checks alone may supply a normalized
  current row; every other row must equal the actual snapshot, and no history exclusion may cover the cursor. Never validate a derived snapshot as a
  new native frame. Obtain each exclusion once, then call the underlying ordered primitive once.
- [ ] Thread composition through `_prefix`, `bind_history`, `_history_rows`, receipt validation and every challenge
  assessment/check/observe/clear/consume path. Fresh history searches omit validated old slots but cannot adopt a baseline row. Add
  `_resume_submission_acked(command, view) -> bool` backed by the command registry, its original view binding and actual post-ack phase;
  `note_resume_submission` uses it. Implement POST_SUBMIT and one-way row retirement now, with no reappearance/adoption. Register current
  command/probe as weak dependents so revocation invalidates both and clears the nonce without recursive reactivation.
- [ ] Preserve actual raw snapshot/frame pairs in the challenge. A lifetime check of a cached context snapshot must use that snapshot's stored frame,
  not relabel it with a newer frame; each IO still validates the latest actual frame. Carry the same view through normalized nonce echoes and every
  partial owned exit. No receipt-dropping or view-dropping recovery.
- [ ] Propagate ResumeHistoryError on the new-view route to the driver's explicit failure reducer, including from exit consumption. Preserve existing False semantics for ordinary no-view InputProofError; never flatten a resume rejection into success or dynamic exception text.
- [ ] Extend the frozen rejection observation to retain only the exact already-validated exclusion indices and original snapshot/error identity for
  passive debug re-evaluation. It must not call a revoked live view to reconstruct authority. Add
  `test_debug_keeps_actual_rejection_after_view_revocation` and assert the excluded SDK/menu rows cannot be exported as the failure.
- [ ] Add `test_retirement_and_exclusion_cannot_refresh_old_numeric_grid`, plus matrices for frame reuse, root/case/terminal substitutions, auth/menu
  during nonce/clear/partial exit, expiry and restoration after revocation. New/default contracts must differ only with a genuine fresh view. Run the
  new suite and policy/echo/challenge/journal/debug suites GREEN; commit as `test: compose resume history with owned input proofs`.

### Task 4: Selected driver, completion producer and concrete-write guards

**Files:** Modify `tests/headless_context_driver.py`, `tests/claude-pty-driver.py`;
test `tests/test-headless-context-driver.py`, `tests/test-terminal-wiring.py`,
`tests/test-terminal-cancellation.py`, `tests/test-headless-driver-signals.py`;
extend `tests/resume_history_fixtures.py` only for controlled peers.

**Interfaces:** Add keyword-only `_initial_completion_sink=None`,
`_resume_offer=None` to both `drive` and `drive_context`. Only the existing
selected offline context route may receive them; dictionaries, conflicting
sink/offer arguments, missing scope, another dialogue/platform/terminal or the
live CLI must reject before launch/writes. Neither option becomes a CLI flag.
Extend `exit_input_owned` with `_resume_view=None`, `_controller_owner=None` and
its existing current state/scope/native/transition/frame bindings.

- [ ] Add `test_initial_completion_is_finalized_only_after_owned_success_and_cleanup` RED. Use a real helper and Python PTY peer, asserting the exact
  byte stream `/context\r` + 16 hex bytes + `\x15` + `/exit\r`, a completed sink, and natural exit/reap. Partial exit, wrong count and helper-close
  failure must yield no completion fact.
- [ ] Add `test_resume_auth_theme_trust_never_inherits_startup_keys` (Review Focus 1) and `test_replaced_root_during_writable_wait_stops_before_write`
  (Review Focus 2). Use explicit file/read-write barriers in the controlled peer, not sleep ordering guesses. Assert zero startup answer bytes and no
  byte after identity loss respectively.
- [ ] Implement private argument validation in `drive` before native launch and forward only exact branded objects. In scoped `drive_context`, create
  one fresh transition before launch and retain it for command/probe/exit; remove the later second assignment. Bind the actual Popen owner once,
  including the initial sink. With a resume offer, pending auth/theme/trust fails before the generic startup auto-key loops.
- [ ] For an offered resume, wait only through `try_bind_resume_view`; None means still pending, never ordinary readiness fallback. Recheck the bound
  view/composed empty anchor after settling and before command construction. Drain/pump/revalidate every consumed frame, including writable waits, and
  recheck root/lifetime immediately before each concrete write.
- [ ] Notify POST_SUBMIT only from the actual successful one-byte Enter acknowledgement. Pass the new view through command/receipt/nonce and
  partial-exit consumers; complete it only after natural exit and successful cleanup. Before initial-dialogue invalidation capture the pending
  completion fact, then finalize it only after both cleanup results are known. Observer failure cannot finalize a fact or alter the operational
  result.
- [ ] Apply the existing strict command acknowledgement bounds to nonce/exit writes too: exact integer `0 < count <= len(pending)`. Preserve original
  cancellation/deadline handling, FD closure and cleanup. Recognize ResumeHistoryError explicitly in the failure reducer; do not coerce it into a
  successful/unknown generic state or create permission from its metadata.
- [ ] Add actual peer success for pinned history and post-Enter retirement, failure for reappearance/duplicate/current-row history, completion-only
  Enter, unchanged numeric grid, late auth, partial exit and signals. A sink/view serialized through JSON and a valid shape without a view must never
  reach a write. Run driver/wiring/cancellation/signals plus the new suite GREEN and commit as `test: enforce fresh resume views at terminal writes`.

### Task 5: Offline supervisor, closed reporting and isolated end-to-end fixtures

**Files:** Modify `tests/offline-terminal-resume-probe.py`,
`tests/terminal_structural_diagnostics.py`, `tests/terminal_context_diagnostics.py`
only for closed reason compatibility; test existing collector/journal/offline/
wiring/debug suites and extend the controlled helper.

**Interfaces:** The offline case supervisor consumes Task 2 interfaces and Task 4
private driver keywords. It adds `validSDKSample: bool` to each reduced case;
only genuine internal witness completion may advance the workflow. Retained
booleans describe the verdict but cannot mint a view when read back.
Collector adds optional top-level record field `resumeViewDecision` accepting
only `VALID`/`REJECTED` on the selected route's existing checkpoints/failure.
Raw `structure.readiness` remains unchanged; no new diagnostic records are required.

- [ ] Add `test_exit_zero_wrong_session_never_launches_after` and `test_sdk_witness_reads_bound_descriptor_not_replaced_path` (Review Focus 5) RED.
  Wrong-session actual output must give `validSDKSample is False`, no after invocation and one stopped case. Replacing its pathname with an older
  valid stream must not rescue invalid actual output; conversely an invalid replacement must not override valid output on the still-bound descriptor.
  An SDKFacts instance or edited event file cannot bypass the actual child/stream join.
- [ ] Create one case after its owned root/session/project exist in the isolated inner process. Supply the initial completion sink to before. Replace
  SDK `subprocess.run` with one owned Popen/wait path and an exclusively created owner-only read/write stdout file using no-follow semantics. Bind
  that open stream to SDKLaunch, retain it through validation, never reopen a pathname for witness input, and terminate/reap on failure within the
  original 25-second budget. Never retry SDK or resume preparation.
- [ ] Use the existing exact argv contracts: initial/resume is `/opt/probe/claude`, `--session-id`/`--resume`, the case session and
  `--strict-mcp-config --mcp-config <owned-root>/mcp.json`. SDK keeps `-p <fixed-prompt> --resume <session>` plus the same MCP arguments,
  `--permission-mode default --tools Skill --allowedTools Skill(context-continuity) --include-hook-events --verbose --output-format stream-json
  --max-turns 4`. No extra executable/environment override is introduced.
- [ ] Have `sdk_finished` read at most 5,000,001 bytes from the bound descriptor, parse only within the original budget and release transient data.
  Use Task 1 constants/Skill witness, not a divergent validator. Report validSkillSample/skillCalls from validated facts; `case_complete` requires
  validSDKSample and existing case gates. Offer resume only from sealed SDK_VALIDATED state, not the report dictionary. In finally call
  `close_offline_case` before identity-checked disposal; the parent still owns closing stream descriptors and children.
- [ ] Mount only `terminal_resume_history.py` as an additional read-only file in `_namespace`. Reject before capability issuance outside the audited
  namespace. Preserve root identity disposal, reduced proof events, debug eligibility, before/SDK/after order, at most two cases and
  first-inconclusive stop.
- [ ] Add collector RED/GREEN tests for the closed decision strings, wrong types/events, no raw/session/hash fields, detached copies and unchanged
  16-record/3072-byte/16384-byte budgets. Add the five RESUME_HISTORY reasons only as closed failures. Permit matching command-journal attachment only
  when actually frozen by that journal; do not synthesize normalized siblings for a new error category.
- [ ] Add `write_fake_cli(path: Path, *, mode: str) -> None` in the test helper. Its synthetic `--version`, interactive before/resume UI and `-p`
  stream/loopback behavior exercise real Popen/PTY/bwrap without executing installed Claude. Modes cover two-case success, SDK rejection, resumed-view
  loss, cleanup failure and interruption. All prompts/screens are public hand-authored fixtures, never deleted native captures.
- [ ] Run `test_isolated_fake_text_and_skill_resume_both_complete`: assert ordered two cases, correct request/call counts, validSDKSample, natural
  exits, no unexpected writes, reaped leaders and absent roots. Also assert missing capability/debug/collector failure never creates a passive
  fallback or raw export. Label this fixture runtime as a test double, not native acceptance.
- [ ] Run new, collector, journal, offline, wiring, debug, cancellation and signals suites GREEN. Run the complete covering command/driver/challenge/echo suites as well; commit as `test: wire validated offline SDK resume cases end to end`.

### Task 6: Immutable verification, one scoped review and honest closeout

**Files:** Update `docs/architecture/ADR-010-browser-automation-boundary.md`,
`CHANGELOG.md`, `tests/validation-notes.md`, this plan and its spec. No version bump
unless implementation actually changes packaging; stop for scope review if it does.

**Interfaces:** Consume all prior deliverables. The final review range starts at
the recorded execution baseline and includes every task, not the inherited branch
history. The author owns fixes and verification; one fresh independent reviewer
owns the completed scoped verdict. No native or external workflow action follows.

- [ ] Re-read every spec section and map its requirements to tests/tasks. Record TDD RED/GREEN, actual bytes/state/cleanup results, all
  warnings/skips, residual layout risks and source paths without protected content. Update ADR/spec status to implemented only for enforced/tested
  local behavior; keep native acceptance pending.
- [ ] Run all covering suites and documentation checks; commit the candidate before review. Run `git diff --check` and record its full SHA. No source
  mutation during review. Supply the spec/plan, complete implementation range, five Review Focus cases and exact verification claims; reviewer must
  list every declined-to-judge behavior.
- [ ] Use requesting-code-review with one fresh reviewer. For native execution, use the most capable available review model; if service limits prevent
  a verdict, report the pending gate instead of inventing one or silently replacing a completed seat. Address valid findings with author TDD and the
  same reviewer for clarification, not a second independent opinion. Explicitly rule on every exclusion/minor and its consequence.
- [ ] On the final clean corrected source, run the complete clean-prefix `bash tests/validate-package.sh`. Expected exit 0 and `package validation
  passed`; inspect warnings, skips, absent capabilities and local schema/workflow results. Preserve logs outside Git and verify HEAD/source blobs did
  not change through the gate. Any source fix requires a fresh matching gate; never call an interrupted run passed.
- [ ] Write result-only closeout with reviewed/gated SHAs, one review verdict, all rulings and pending native/provider/browser/remote CI/Security
  gates. Check content and architecture tests after documentation-only closeout; distinguish its later SHA from the immutable source candidate. Commit
  only owned paths, confirm clean worktree and retain branch/worktree/consumed-grant metadata.
- [ ] Stop with the final commit and remaining requirements. Do not execute Claude, update staging, push, create PR, merge, release or mark the definitive TODO done. A new exact-final-commit offline grant is required even if synthetic cases pass.

## Plan self-review and execution handoff

Coverage map: pure rows/SDK and source fixtures -> Task 1; root/case/session/
completion and one-shot lifetime -> Task 2; composition, retirement, numeric
freshness and debug provenance -> Task 3; concrete IO, startup, nonce/exit and
signals -> Task 4; actual supervisor/process joins, mounts, reports/disposal and
two-case fixtures -> Task 5; immutable gate/review/docs/rollback status -> Task 6.
Every Review Focus item has an explicit owning test. No implementation task is
complete merely because a mocked or serialized result says so.

Recommended execution is native/inline: the tasks deliberately share private
proof interfaces and must be integrated sequentially. The alternative is
subagent-driven execution with a fresh implementer/reviewer per task and a final
whole-deliverable review. The operator must review this plan and choose the
method before code changes. Neither choice grants a new native experiment.
