# P0-04B Post-Enter Observation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Observe one isolated resumed text-turn display after its single owned
/context Enter without changing acceptance or permitting further terminal input.

**Architecture:** Add a mutually exclusive offline observation mode with a
branded request, one-way command/history handoff and separate read-only guard.
Consume bounded parsed output until the first terminal observation, then dispose
all owned raw evidence before publishing a distinct structural-only report.

**Tech Stack:** Existing Python unittest/PTY/namespace harness, Debian WSL,
Bubblewrap, existing Node/xterm helper, native runtime only under a later grant.
No new dependencies or runtime/provider/version pins.

**Spec:** [Approved written design](../specs/2026-10-20-p0-04b-post-enter-observation-design.md).
Design and plan approved by the operator on 2026-10-20; option 2 selected:
inline implementation with a fresh final independent reviewer. Tasks 1-5 are
implemented locally. Review at `6bfe16b` found four Important issues; one author
RED/GREEN pass at `59c3869` fixed them, without a second reviewer dispatch.
The immutable full package gate passed at `59c3869`. Exact evidence, exclusions
and residual native gates are recorded in `tests/validation-notes.md`.
This plan's temporary SDD workspace is removed only after final completion;
commits and the validation record retain the delivery history.
Planning baseline: `af14ac1580624c49fcd322c048fe1f25c0de3801`.

## Global Constraints

- Test-only mode `--observe-post-enter`; mutually exclusive with `--run-offline`,
  `--audit-isolation`, both content-debug flags and duplicate mode selection.
- One synthetic text-turn case only; unchanged initial handshake, one SDK
  invocation, resumed observation. No skill-turn or second case.
- Eight command bytes, full exact owned echo, exactly one acknowledged Enter;
  every pre-Enter writable-wait frame updates the final submission boundary.
- After activation, the terminal-input writer must reject every further byte.
- Keep 25 seconds per context dialogue and 165 seconds total with the existing
  outer supervision/cleanup allowance included, not added.
- Keep SDK `--max-turns 4` and the existing four loopback-message ceiling;
  one SDK invocation is not permission for multiple invocations or retry.
- Keep 16 records / 3072 actual JSON bytes per phase and 16384 bytes for the outer
  report including final disposal metadata and newline.
- Require loopback-only gateway, hidden operator state, dropped capabilities,
  synthetic authentication and disposable HOME/config/project/history.
- Separate schema `p004b-post-enter-observation-v1`, literal `acceptance: false`;
  no acceptance receipts, resumed nonce/clear/exit, raw export or content debug.
- Preserve all existing default/live/provider/acceptance behavior, original
  pre-Enter menu retirement and HISTORY_COMMIT_V1 inventory constraints.
- All real native grants are consumed. No installed Claude invocation, provider,
  browser, settings/credentials access, dependency install, automatic retry,
  push/PR/merge/release/staging refresh or definitive TODO completion here.
- File changes are English. Root/component versions remain unchanged unless
  separately approved packaging scope changes.

## Review Focus

1. Writable-wait output can change the last valid menu/inventory/sample after
   preparation; activation must use the final checked pre-Enter state (Task 2).
2. Existing revocation closes the shared case; handoff must withdraw acceptance
   without renewing the case or destroying its independent guard facts (Task 1).
3. A recognized first menu can hide another bad row; classify the whole snapshot
   and preserve conflicting numeric/history evidence (Task 3).
4. An attempted write through an alternate callback or terminal response can
   escape the main command writer; seal every input path before consuming more
   post-Enter output (Task 4).
5. A zero-exit structural report or cleanup fault can be mistaken for acceptance;
   schema separation and parent-only post-disposal publication are mandatory
   even under malformed child output/report pressure (Task 5).

## File Structure and Responsibilities

| File | Responsibility |
| --- | --- |
| `tests/terminal_resume_history.py` | Branded observation request, detached read-only case/history guard, case closure |
| `tests/terminal_context_echo.py` | Original command correlation, final pre-Enter seed, single-ack handoff and irreversible acceptance retirement |
| `tests/terminal_post_enter_observation.py` (new) | Sealed observer, ordered structural transition state and bounded closed summary |
| `tests/headless_context_driver.py` | Exclusive observer dispatch, input latch, latest-output drain, supervision |
| `tests/claude-pty-driver.py` | Private typed request forwarding; no general CLI activation |
| `tests/offline-terminal-resume-probe.py` | Explicit outer/inner mode, single case, namespace mount, cleanup and separate parent result |
| `tests/post_enter_observation_fixtures.py` (new) | Synthetic owned setup and state transitions; never mounted into native runs |
| `tests/test-terminal-post-enter-observation.py` (new) | Request/guard/handoff/observer unit and adversarial tests |
| `tests/test-post-enter-observation-report.py` (new) | Closed schema, bounds, parent result and cleanup tests |
| Existing history/echo/display/driver/offline safety test files | Default behavior regressions and synthetic PTY/CLI integration |
| `tests/validate-package.sh`, `tests/test-terminal-wiring.py` | Include new synthetic suites and verify read-only test mounts |
| ADR-010, architecture index, spec/plan, CHANGELOG, validation notes | Enforced versus proposed status and exact review/gate evidence |

Do not split the existing driver or build another generic recorder. The new
observer is a focused unit; request and case lifecycle remain owned by history.

## Verification Commands and Environment

Commands in tasks below run from the existing linked worktree in Debian WSL.
Use the established explicit Node PATH, not bare host Bash. Host paths and the
current helper executable are operational test inputs, not product pins.

Worktree: `C:/projects/senior-infra-ops-analyst/senior-infra-ops-analyst/.worktrees/p0-04b-browser-automation`.
WSL worktree: `/mnt/c/projects/senior-infra-ops-analyst/senior-infra-ops-analyst/.worktrees/p0-04b-browser-automation`.
Host Git uses command-local `-c safe.directory=<absolute-worktree>`.

For focused Python suites use the following environment, with one task's test
path in place of the final script. Do not run it now as part of plan writing:

```powershell
$postEnterTestArgs = @(
  '-d', 'Debian', '--cd',
  '/mnt/c/projects/senior-infra-ops-analyst/senior-infra-ops-analyst/.worktrees/p0-04b-browser-automation',
  '--', 'env', '-i', 'HOME=/tmp',
  'PATH=/home/marco/.local/opt/node-v24.17.0-linux-x64/bin:/usr/bin:/bin',
  'PYTHONNOUSERSITE=1', 'PYTHONDONTWRITEBYTECODE=1',
  'P004B_TERMINAL_NODE=/home/marco/.local/opt/node-v24.17.0-linux-x64/bin/node',
  'P004B_TERMINAL_MODULE_ROOT=/mnt/c/projects/senior-infra-ops-analyst/.review-runtime/p004b-terminal-state/node_modules',
  '/usr/bin/python3', 'tests/test-terminal-post-enter-observation.py'
)
& wsl.exe @postEnterTestArgs
```

The command above intentionally names explicit local inputs. Preserve these
arguments; do not silently omit either
terminal-helper variable. Synthetic fixtures must never resolve/launch Claude.
Initial TDD failures must be missing behavior/assertion failures, not setup
errors, import-path failures, absent helper variables or a missing dependency.

### Task 1: Observation-only case request and independent history guard

**Files:** Modify `tests/terminal_resume_history.py` around case registries,
`close_offline_case`, `offer_resume`, `validate_resume_view`; create the fixture
and observation test files; extend `tests/test-terminal-resume-history.py`.

**Interfaces:**

- Produce branded, non-copyable `PostEnterObservationRequest` and
  `PostEnterHistoryGuard` handles using the module's existing sealed-registry
  discipline. Constructors and serialized dicts must not create them.
- `offer_post_enter_observation(case, *, state, scope, command) -> PostEnterObservationRequest`:
  require actual namespace audit, text-turn `SDK_VALIDATED` case and fresh
  state/scope, and internally create the exact resume offer. Latch observation
  purpose on the request/offer/view. No Boolean is an authority token.
- `observation_resume_offer(request, *, state, scope, command) -> ResumeOffer`:
  validate the original request and return its exact live offer for the existing
  pre-Enter startup/binding route; no independently created replacement offer.
- `detach_post_enter_history(request, *, view, command, snapshot, frame,
  controller_owner) -> PostEnterHistoryGuard`: require POST_SUBMIT and original
  command acknowledgement; atomically consume request/offer/view, set the case
  to OBSERVING, and retain original identity/history/retirement guard facts.
  Freeze the independently checked eight-byte/full-echo/one-Enter facts before
  command retirement. The guard must not call `_current_command_acked` after
  that command is removed, nor replace acknowledgement with diagnostic fields.
- `validate_post_enter_history(guard, *, policy, snapshot, frame, state, scope,
  native_owner, controller_owner, transition_owner) -> frozenset[int]`: check
  original lifetime/case/geometry and pinned/retired history; return only old
  surviving history indices, not a writable anchor or view.
- `close_post_enter_history(guard) -> None`: idempotent release; case closure
  invalidates requests/guards alongside all existing dependents.

- [x] **Step 1:** Add `test_detach_withdraws_view_without_closing_case`, asserting
  old view decision REJECTED, valid guard, unchanged root/deadlines and case
  OBSERVING. Add `test_detached_observation_cannot_mint_acceptance` and reject
  missing SDK/audit, skill-turn, copied request, wrong owners, replay and wrong
  state/scope. Existing ordinary view tests must remain unchanged.

  ```python
  self.assertEqual(history.resume_view_decision(original_view), 'REJECTED')
  self.assertIsInstance(guard, history.PostEnterHistoryGuard)
  self.assertEqual(history._CASES[case_record]['phase'], 'OBSERVING')
  self.assertEqual(history._CASES[case_record]['deadline'], original_deadline)
  ```

- [x] **Step 2:** Run `python3 tests/test-terminal-post-enter-observation.py -k detach`
  in the defined environment; expect a missing-interface/assertion failure.
- [x] **Step 3:** Implement the interfaces above. Transfer the original binding
  once without `revoke_resume_view`, `close_offline_case`, reopening a case or
  extending deadlines. Include the new registries in actual case closure.
  Preserve the default validator; factor only shared pure profile comparison
  if needed, keeping acceptance checks independent.
- [x] **Step 4:** Add/run guard tests for retired-history return, moved/replaced
  old history, close/root loss, clock regression/deadline, native/helper loss,
  foreign controller, geometry and copied bindings. Run the complete new suite
  and `tests/test-terminal-resume-history.py`; expect all tests OK, no native.
  Pin `test_guard_does_not_require_retired_command_registry` while preserving
  rejection for unproved acknowledgement and loss of the original case/scope.
- [x] **Step 5:** Commit only this tested lifecycle unit and its tests as
  `test: separate post-enter observation case guards`.

### Task 2: Final pre-Enter seed and irreversible command handoff

**Files:** Modify `tests/terminal_context_echo.py` around `OwnedContextCommand`,
`begin_context_command`, `submission_written`, menu/display release; create the
sealed observer shell in `tests/terminal_post_enter_observation.py`; extend new
fixtures/tests plus `tests/test-terminal-context-echo.py`; extend the request's
private result association in `tests/terminal_resume_history.py`.

**Interfaces:**

- Extend `begin_context_command(..., _post_enter_request=None)` only for an
  exact Task 1 request matching the original observation-purpose view.
  Reject a purpose-marked view without its exact request, and reject that
  request in a normal acceptance command. No generic Boolean activation.
- `_prepare_post_enter_observation(command, snapshot, frame, *, request,
  controller_owner) -> PostEnterObservation`: require COMMAND_ECHO_MATCHED and
  original live bindings; store the optional exact menu reference privately.
- `OwnedContextCommand.post_enter_observation() -> PostEnterObservation`:
  retrieve only that original prepared observer; no caller-provided indices,
  summaries, snapshot copies or public row exclusions.
- Existing `submission_written(count) -> None` activates only a prepared
  observation command after ordinary acknowledgement checks and
  `note_resume_submission`, while the final menu/view facts are still available.
  It calls Task 1 detach, then irreversibly removes the command's acceptance
  registry entries. The observer remains in its own registry. Normal commands
  retain exactly their current behavior and menu retirement order.
- New `PostEnterObservation` is sealed/non-copyable; its phases are PREPARED,
  AWAIT_DISPLAY, CANDIDATE and FINISHED. Only the actual command ack activates it.
- `take_post_enter_result(request) -> dict | None` in history consumes only the
  actual privately associated observer's frozen summary after observer close.
  Keep the request-to-observer association until this read or case closure;
  after close it contains no raw evidence. Never accept a caller-supplied dict
  as the source of an observation result. Pending/missing results return None.

- [x] **Step 1:** Add `test_handoff_uses_last_writable_wait_frame` with different
  numeric baseline/menu inventory in a later valid pre-Enter frame. Assert the
  handed-off private barrier matches that frame, not the preparation frame.
  Add `test_handoff_retires_all_acceptance_paths`:

  ```python
  self.assertIs(case.observer, case.command.post_enter_observation())
  self.assertEqual(case.observer.phase, 'AWAIT_DISPLAY')
  with self.assertRaises(RuntimeError): case.command.bind_history(case.after, 4)
  with self.assertRaises(RuntimeError): case.command.context_display_percent(case.after, 4)
  ```

  Keep the bound observer reference available for cleanup even after command
  retirement; its getter may use a sealed association, not restore `_COMMANDS`.
- [x] **Step 2:** Run the new suite with `-k handoff`; expect assertion failures
  for absent behavior, then implement the minimal preparation/activation paths.
- [x] **Step 3:** Finalize seed inventory, sample, menu and frame at the last
  consumed valid pre-Enter boundary. Process every writable-wait observation
  before actual Enter; do not freeze preparation early. On partial mutation or
  failure close the case, never roll back to a usable acceptance command.
- [x] **Step 4:** Add/run bad counts `0`, `2`, `True`, duplicate ack, stale/copied
  seed, wrong/missing/partial echo, late UI, expired deadline, unrelated request,
  menu change and no-menu controls. Assert ordinary post-Enter lingering-menu
  rejection and inventory-promotion rejection still pass in existing echo,
  display and frozen-history-rejection suites.
- [x] **Step 5:** Commit the tested unit as
  `test: hand off owned submission to read-only observation`.

### Task 3: Ordered observational classifier and closed summary

**Files:** Complete `tests/terminal_post_enter_observation.py`; extend synthetic
fixtures and `tests/test-terminal-post-enter-observation.py`; create
`tests/test-post-enter-observation-report.py`.

**Interfaces:**

- `PostEnterObservation.observe(snapshot, frame) -> None`: validate Task 1 guard
  and every relevant row, update monotonic transient/history/numeric state.
  Require actual ordered consumed frames, strictly beyond the final submit
  barrier for profile discovery; Boolean/stale/foreign frame evidence rejects.
- `PostEnterObservation.candidate_ready -> bool`: discovery only, never authority.
- `PostEnterObservation.complete(snapshot, frame) -> None`: after driver drain,
  require the same full profile/sample/anchor and no intervening invalidation;
  freeze CURRENT_PROFILE_OBSERVED or the first terminal failure.
- `PostEnterObservation.stop(outcome, stop_category) -> None`: finite spec enums
  only, first terminal result wins; it cannot convert failure into completion.
- `PostEnterObservation.close() -> None`: release raw references and guard,
  preserving only an already frozen closed structural summary.
- `PostEnterObservation.summary() -> dict`: defensive content-free copy only;
  only after FINISHED, no caller mutation, arbitrary error, raw cells,
  coordinates or IDs. Observation close must freeze failure if still pending.
- `valid_observation_summary(value) -> bool`: strict field/type/enum validation.
  Use exactly the spec's menu/input/commit/numeric/outcome/stop categories.
  Exact keys are `outcome`, `stopCategory`, `profileObserved` and optional
  `menuState`, `inputState`, `commitRelation`, `numericRelation`. Omit unobserved
  optional facts except inputState may explicitly use UNOBSERVED. Require the
  first three keys; no additional keys or arbitrary strings.

- [x] **Step 1:** Add `test_known_menu_does_not_hide_unknown_row`, with exact
  menu at cell 8 plus unknown marker at 39; assert terminal
  UNSUPPORTED_TRANSITION / UNKNOWN_ROW, no candidate or receipt. Add a known
  menu plus conflicting numeric sample and later baseline restoration; assert
  NUMERIC_CONFLICT cannot recover.

  ```python
  summary = observer.summary()
  self.assertEqual(summary['outcome'], 'UNSUPPORTED_TRANSITION')
  self.assertEqual(summary['stopCategory'], 'UNKNOWN_ROW')
  self.assertFalse(summary['profileObserved'])
  self.assertFalse(observer.candidate_ready)
  ```

- [x] **Step 2:** Run new tests to a real RED; implement the ordered assessment:
  all independent guards first, all rows inspected, only exact original menu
  and exact original owned-input echo can be transient. Preserve history
  retirement, inventory and numeric conflict state throughout waiting.
- [x] **Step 3:** Add/run `test_menu_and_input_disappearance_are_monotonic`,
  `test_same_cell_history_is_classified_not_promoted`,
  `test_candidate_loss_never_returns_to_waiting` and
  `test_full_profile_needs_latest_revalidation`. Assert original cell reuse
  ends INVENTORIED_CELL_REPLACEMENT, while a fully valid new-cell profile can
  freeze CURRENT_PROFILE_OBSERVED without creating a witness/receipt/nonce.
- [x] **Step 4:** Cover no-menu path; moved/mutated/duplicated/reappearing menu
  or command echo; arbitrary draft, malformed/wide/invisible cells; old history
  return/movement; complete/incomplete/conflicting numeric samples; auth elsewhere;
  clock/owner/geometry loss and immutable first terminal result. Run both new
  suites and original history/echo/display/rejection suites; expect OK.
- [x] **Step 5:** Pin summary assertions, including `type(profileObserved) is bool`,
  unknown keys/enums rejected, booleans not accepted as counts, mutation of a
  returned dict not changing internal facts, and no serialized cell text/path
  or content-derived hash. Commit as
  `test: classify bounded post-enter display observations`.

### Task 4: Headless driver observation route and zero-write boundary

**Files:** Modify `tests/headless_context_driver.py:85` onward and
`tests/claude-pty-driver.py:293` onward; extend `tests/test-headless-context-driver.py`,
`tests/test-claude-pty-driver.py`, new fixtures/report tests.

**Interfaces:**

- Extend `drive(...)` and `drive_context(...)` with private keyword
  `_post_enter_observation=None`, an exact Task 1 request, not a Boolean.
  It is exclusive with `_resume_offer`, initial sink and both content-debug
  objects. Resolve its internally bound offer for the unchanged pre-Enter path.
- Local `write_terminal(data: bytes) -> int` owns all actual input calls in
  `drive_context`; `seal_terminal_input() -> None` irreversibly latches no input.
  Route existing `os.write` and supplied writer paths through this boundary,
  preserving partial-write behavior before submission. Never forward helper
  terminal responses. A later attempt stops WRITE_ATTEMPT before IO.
- After Enter ack/Task 2 activation, seal input synchronously before another
  pump/callback. Replace post-Enter `resume_live`/command observation with the
  independent observer route, not with an exception handler around rejection.
- On `candidate_ready`, drain bounded available output under the same deadline,
  observing each frame, then call `complete` with the latest snapshot.
- Driver result zero means only completed profile observation. The inner
  harness takes the closed summary with Task 2 `take_post_enter_result` before
  case closure, then defers all publication until parent disposal; never
  emit normal resumed passed context/display/nonce/exit events. On any exit,
  close observer and reap/helper-close using existing supervision.

- [x] **Step 1:** Add controlled synthetic PTY tests
  `test_observer_seals_every_write_after_one_enter` and
  `test_observation_never_constructs_acceptance_receipts`, with spies for all
  actual writer/os.write paths, display bind, nonce and exit constructors.
  Assert post-boundary write byte count equals zero and no acceptance call.

  ```python
  self.assertEqual(post_enter_bytes, b'')
  bind_history.assert_not_called()
  nonce_constructor.assert_not_called()
  self.assertNotIn('context_display', passed_resumed_stages)
  ```

- [x] **Step 2:** Run targeted tests to RED; implement the private forwarding,
  checked handoff, writer latch and observer pump route. Keep the original
  route selected when no request exists; do not change its rejection timing.
- [x] **Step 3:** Test a fragmented/delayed menu-to-profile peer, same-cell
  replacement, completion-only peer until deadline, write attempt from an
  alternate callback, attempted parser response, last-frame candidate loss,
  native/helper exit, cancellation and no available output. Use original
  remaining deadline; assert natural exit/nonce absent in resumed observation.
- [x] **Step 4:** Run full headless/CLI/signal/cancellation suites plus Tasks 1-3
  suites; expect OK with controlled peers only. Assert initial handshake and
  ordinary resumed acceptance remain byte-for-byte behaviorally unchanged.
- [x] **Step 5:** Commit as
  `test: isolate passive driver observation after submission`.

### Task 5: Offline mode, parent disposal and immutable verification

**Files:** Modify `tests/offline-terminal-resume-probe.py` mode/namespace/case
dispatch, `tests/test-offline-terminal-resume-safety.py`, new report tests,
`tests/test-terminal-wiring.py`, `tests/validate-package.sh`; update the spec,
plan, ADR/index, CHANGELOG and `tests/validation-notes.md` truthfully.

**Interfaces:**

- `run_post_enter_observation(*, source, claude, node, module_root) -> dict`:
  reuse `_namespace` with exclusive observation selector; inner mode is exactly
  `--inner-post-enter-observation`. Both layers independently reject mixed or
  repeated mode/debug combinations before resolving/launching native.
- Extend private namespace/control dispatch with `post_enter_observation=False`;
  true selects exactly one text-turn setup, Task 1 request for resume, Task 4
  driver, and a separate result path. Default controls keep existing `run_cases`
  order/aggregation. Mount the new observer read-only only when needed.
- `valid_post_enter_report(value) -> bool`,
  `fit_post_enter_report(value, *, reserve_disposal: bool) -> dict` and
  `post_enter_exit_code(value) -> int` live in the offline probe/report seam.
  Require schema, `mode: 'observe-post-enter'`, `acceptance: false`, closed
  outcome/summary and cleanup evidence. Summary relation enums come from Task 3.
- Retain no default coordinate-bearing phase diagnostics or reduced acceptance
  event stream in the new result. Setup uses booleans `initialCompleted` and
  `sdkValidated`; cleanup uses `nativeReaped`, `helperReaped`, `caseRootAbsent`
  and `disposableRootAbsent`. Keep only closed base failure/cleanup categories
  and the bounded optional observational summary; all metadata obeys spec bounds.
  Root keys are exactly `schema`, `mode`, `acceptance`, `outcome`, `stopCategory`,
  `setup`, `cleanup` and optional `summary`. Each setup/cleanup field is Boolean;
  unknown keys, malformed nested mappings and arbitrary strings reject. Before
  parent disposal, disposableRootAbsent is false, never trusted from child JSON.
- Only the parent may publish after actual native/helper/namespace reap and
  identity-checked raw/history/root deletion. Child JSON cannot attest parent
  cleanup. CLEANUP_FAILED suppresses observation detail and forces exit two.
  Exit zero requires CURRENT_PROFILE_OBSERVED plus proved cleanup; legacy
  acceptance aggregation rejects the entire new schema regardless of exit code.

- [x] **Step 1:** Add tests for outer/inner mixed/duplicate modes, debug combinations,
  Boolean or forged request, direct host inner entry, one-case/no-skill execution,
  unavailable isolation and no installed native launch during synthetic testing.
  Run to RED, then implement only the exclusive mode and dispatch.
- [x] **Step 2:** Add report tests for unknown keys/enums, forged cleanup/success,
  zero-exit incompatible schema, child process failure with success JSON,
  lost projection, multibyte byte accounting and optional summary pressure.
  Assert 16/3072 and 16384 bounds include disposal/newline and base cleanup
  records survive optional-detail omission. Implement the strict report seam.

  ```python
  self.assertEqual(report['schema'], 'p004b-post-enter-observation-v1')
  self.assertIs(report['acceptance'], False)
  self.assertFalse(offline.case_complete(report))
  self.assertLessEqual(len((json.dumps(report, sort_keys=True)+'\n').encode()), 16384)
  self.assertEqual(post_enter_exit_code(cleanup_failed_report), 2)
  ```

- [x] **Step 3:** Exercise actual synthetic child/PTY/namespace failures and cleanup
  ordering: malformed/truncated output, SDK/setup failure, write failure,
  timeout/cancellation, root escape/substitution, native/helper/namespace reap
  failure and deletion failure. Assert no raw content/export before cleanup,
  no fallback into `case_complete`, no retry, no second case or real provider.
- [x] **Step 4:** Add both new Python suites to the full gate and wiring tests;
  run all affected history/echo/display/observer/driver/CLI/offline/cancellation/
  report/wiring suites in the defined environment. Record real counts/skips;
  commit tested code/docs as `test: add isolated post-enter observation mode`.
- [x] **Step 5:** Obtain a fresh independent whole-change review on immutable
  committed source, with scope from planning baseline through all Task 1-5
  commits. Reviewer must inspect spec coverage, trust boundaries and actual
  tests without native/provider execution. Fix any findings with TDD, rerun
  affected suites and commit corrections. For the selected inline workflow,
  use one author fix pass and the complete gate, not a second reviewer dispatch.
- [x] **Step 6:** Export the exact reviewed commit to an owned isolated Linux
  directory using the established archive/content/type/mode verification route.
  Run `bash tests/validate-package.sh` there with both terminal-helper variables
  and the explicit Node PATH. Expect exit zero and `package validation passed`.
  Verify canonical source unchanged before/after; retain sanitized gate evidence
  outside Git and record exclusions honestly. Do not claim remote CI/Security.
- [x] **Step 7:** Update validation notes and spec/ADR/index/CHANGELOG status with
  exact reviewed/gated hashes, actual tests, skips and residual risks. Do not
  claim native feasibility or bump versions. Commit result-only documentation,
  verify source equivalence to reviewed/gated code, run document/content/release
  checks and `git diff --check`, then confirm clean worktree.
- [x] **Step 8:** Stop and present the final immutable commit, evidence and the
  new exact-scope grant needed for a later native observation. Do not run it,
  push, open PR, merge, release, refresh staging or mark the TODO complete.

## Self-Review and Handoff

Coverage: Task 1 owns independent case/history lifetime; Task 2 owns final-frame
handoff; Task 3 owns all-row/profile/summary semantics; Task 4 owns actual IO and
latest-output revalidation; Task 5 owns exclusive launch/disposal/reporting and
whole-change review/gate. The five Review Focus counterexamples are each pinned
to named tests. Interfaces and enum names are shared rather than redefined.

Execution choices are subagent-driven per task with fresh reviews, or native
inline implementation of all five tasks with a fresh final whole-change review.
Inline is recommended here because the lifecycle/handoff/driver interfaces are
tightly coupled and the native execution gate remains separately controlled.
The operator approved this plan and selected inline execution. All later
native/provider/browser execution remains separately gated.
