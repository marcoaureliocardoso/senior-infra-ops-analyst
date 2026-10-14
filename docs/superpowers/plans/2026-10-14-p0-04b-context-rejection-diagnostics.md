# P0-04B Context Rejection Diagnostics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Identify the actual offline owned-command rejection and acknowledged command/Enter bytes without content retention or weaker safety checks.

**Architecture:** A private journal tracks phase and concrete write acknowledgements
independently of validated echo progress. Actual rejecting boundaries freeze a
sealed observation; the outer driver projects it into the existing bounded failure
record. Observations never grant input, consent, acceptance or renewed lifetime.

**Tech Stack:** Existing Python unittest/mock, passive Node/xterm terminal helper, Linux PTY and Debian WSL. No new dependencies.

**Spec:** [Approved specification](../specs/2026-10-14-p0-04b-context-rejection-diagnostics-design.md).

## Global Constraints

- Written specification approved; this plan awaits operator review and execution-method selection. Planning does not authorize implementation or native execution.
- Source planning baseline: `d4ce6bb2b8218ce80cd1c6dc75ad6d6be9a9fca0`; operational source baseline: `ad7b080a2e85b1591422f1d890671b95c974a3df`.
- Reuse the existing `p0-04b-browser-automation` linked worktree; preserve operator changes and keep Git `safe.directory` command-local.
- Observe only the audited offline owned-command transition, from baseline assessment through history binding. Keep public driver signatures, passive/live behavior, reason codes and acceptance event schemas unchanged.
- Output only `phase`, `check`, `commandBytesWritten` (integer 0..8), `enterBytesWritten` (integer 0..1), nested under `contextCommandFailure` on the existing failure record.
- Copy the seven phases and 22 check codes exactly from the approved spec. Reject booleans as counts, extra fields, unknown values and malformed attachments.
- Preserve exact prefix/body/geometry, ordered ambiguity assessment, numeric freshness, original lifetime and one-shot submission. No extra authority checks, writes, retries, grace periods or version fallbacks for diagnosis.
- Keep 16 records and 3 KiB per phase, complete outer report 16 KiB including audit/disposal facts and newline; keep 25 seconds per dialogue, 165 seconds total and at most two offline cases.
- No real Claude/provider execution, operator credentials/configuration access, deleted-content reconstruction or expanded raw-frame capture in implementation verification.
- No retained cells, streams, prompts, nonce values, content hashes, exception messages or process/session identifiers. Existing debug eligibility and identity-checked disposal remain unchanged.
- Keep root/component versions and installed package behavior unchanged. All new documentation is English. No push, PR, merge, release or definitive TODO completion is authorized by this plan.

## Review Focus

1. An accepted Enter followed by a failed live check must retain count 1 and phase `SUBMIT_PENDING`; test in Task 3.
2. Invalid IO counts leave accounting unknown, not falsely zero or successful; test in Tasks 1 and 3.
3. A diagnostic callback failure must not prevent original revocation, exception propagation or cleanup; test in Tasks 2 and 3.
4. Nested catches and later invalidation must preserve the first exception-bound observation, never attribute an earlier failure to a later phase; test in Tasks 1 and 2.
5. Repeated dialogues and foreign exception attachments must not reuse a previous transition's journal, run binding or counters; test in Tasks 1 and 3.

## File Structure and Verification Routes

- Create `tests/terminal_context_diagnostics.py`: private journal, sealed attachment, closed value validation and pure projection; no IO or live validation.
- Create `tests/test-terminal-context-diagnostics.py`: pure registry/accounting/projection tests.
- Modify `tests/terminal_structural_diagnostics.py` and its existing test: atomic serialized observation validation and unchanged budgets.
- Modify `tests/terminal_context_echo.py` and its existing test: actual rejection labeling, pre-revocation phase capture and optional private journal binding.
- Modify `tests/headless_context_driver.py` and its existing test: actual-write accounting, controller rejection labeling and failure projection.
- Modify `tests/offline-terminal-resume-probe.py`, `tests/test-offline-terminal-resume-safety.py`, `tests/test-terminal-wiring.py`, `tests/validate-package.sh`: read-only namespace mount, aggregate/budget/packaging tests and full-gate inclusion.
- Modify ADR-010, architecture index, CHANGELOG, validation notes and this plan's/spec's status as actual work advances. Leave `terminal_input_challenge.py` and `terminal_context_debug.py` unchanged unless a demonstrated compatibility need is reviewed; run their regression suites.

Run Python suites individually from PowerShell using this established prefix:

```powershell
wsl.exe -d Debian `
  --cd /mnt/c/projects/senior-infra-ops-analyst/senior-infra-ops-analyst/.worktrees/p0-04b-browser-automation `
  -- env -i HOME=/tmp `
  PATH=/home/marco/.local/opt/node-v24.17.0-linux-x64/bin:/usr/bin:/bin `
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 `
  P004B_TERMINAL_NODE=/home/marco/.local/opt/node-v24.17.0-linux-x64/bin/node `
  P004B_TERMINAL_MODULE_ROOT=/mnt/c/projects/senior-infra-ops-analyst/.review-runtime/p004b-terminal-state/node_modules `
  python3 tests/TEST_FILE.py
```

Substitute only the named test file from each task. These are detected workspace
dependency paths, not product version requirements; verify they exist before use.
Expected GREEN: unittest reports `OK`, zero failures and exit 0. Expected RED:
the newly named assertion/import fails for the absent behavior, not a missing
dependency. Use `git -c safe.directory=<absolute-worktree> ...` in PowerShell for
status, explicit-file staging and commits; never use Linux Git on this worktree.

### Task 1: Private accounting, frozen attachment and bounded collector

**Files:** Create the private module/unit test; modify structural collector/test.

**Interfaces:**
- `_create_context_journal(*, controller_owner, scope, state, transition_owner) -> ContextFailureJournal | None`: private pure factory for the already audited controller route; no scope issuance or live checks.
- Sealed `ContextFailureJournal` methods:
  `bind_run(run_owner) -> None`, `set_phase(phase: str) -> None`,
  `acknowledge(count: int, *, submission: bool, remaining: int) -> bool`,
  `freeze(error: BaseException, check: str) -> None`,
  `project(error: BaseException, *, controller_owner, scope, state, transition_owner) -> dict | None`,
  `finish() -> None`.
- `valid_context_failure(value) -> bool`: exact four-field serialized shape validation; no authority or provenance inference.
- Export immutable `PHASES`, `CHECKS` and `FAILURE_REASONS`: spec enums; failure reasons are the collector's existing `INPUT_PROBE_*` values plus `RUNTIME_REJECTED` and `TERMINAL_DEADLINE_EXCEEDED`.
- `TerminalDiagnostics.add(..., contextCommandFailure=...)`: optional new field, accepted only at `failure` with an allowed reason; existing call sites unaffected.

- [ ] Write `test_enter_ack_survives_freeze_and_projection` using a pure fixture `self.journal()` that returns a fresh journal and its four identity bindings:

```python
journal, bindings = self.journal()
journal.bind_run(object())
journal.set_phase('EDIT_PENDING')
self.assertTrue(journal.acknowledge(4, submission=False, remaining=8))
self.assertTrue(journal.acknowledge(4, submission=False, remaining=4))
journal.set_phase('SUBMIT_PENDING')
self.assertTrue(journal.acknowledge(1, submission=True, remaining=1))
error = InputProofError('INPUT_PROBE_REVOKED')
journal.freeze(error, 'NATIVE_LIFETIME')
self.assertEqual(journal.project(error, **bindings), {
    'phase': 'SUBMIT_PENDING', 'check': 'NATIVE_LIFETIME',
    'commandBytesWritten': 8, 'enterBytesWritten': 1})
journal.set_phase('REVOKED')
journal.freeze(error, 'SCOPE_BINDING')
self.assertEqual(journal.project(error, **bindings)['check'], 'NATIVE_LIFETIME')
```

- [ ] Write `test_invalid_ack_suppresses_projection`: fresh journal per count
  `True`, `0`, `-1`, `9`, `1.0`, `None`;
  `acknowledge(..., submission=False, remaining=8)` returns False, later freeze
  projects None. Invalid accounting is latched; a later valid count cannot repair it.
- [ ] Write `test_forged_foreign_closed_or_replaced_attachment_omitted`: unsealed
  constructor, copied attachment to another exception, foreign binding/journal,
  changed run binding, invalid phase/check and finished journal never project
  trusted data. Mutating a returned dict cannot mutate a later projection.
  A different exception does not acquire the first observation.
- [ ] Write `test_projection_has_no_live_effects`: patch clock, polling, helper IPC
  and cancellation methods to raise if called; valid frozen projection still
  succeeds. `repr` and exception string do not expose journal payload or content.
- [ ] Write collector tests `test_context_failure_atomic_closed_shape`,
  `test_context_failure_event_binding`, `test_context_failure_budget_and_detached_report`:
  exact keys only, invalid enums/types/ranges rejected with no partial record,
  non-failure/non-compatible reasons rejected; 100 records stay <=16 and <=3072
  bytes and explicitly truncate. Mutating input/report leaves the retained object unchanged.
- [ ] Run `test-terminal-context-diagnostics.py` and `test-terminal-structural-diagnostics.py`; retain named RED evidence.
- [ ] Implement the interfaces. Use private registration and identity-bound sealed
  attachment; freeze scalar data once, independent of later journal state.
  `bind_run` receives the existing scope accessor's result, never calls it again.
  Invalid observational state disables projection, not operational execution.
  `finish` releases private bindings and disables future projection after the collector has copied the result.
- [ ] Run both suites to GREEN; check no mutable/serialized handle can become input authority, and no module stores terminal content or performs IO.
- [ ] Commit explicit Task 1 files: `test: add sealed context failure accounting and collection`.

### Task 2: Label actual owned-command rejection boundaries

**Files:** Modify context component/test. Consume Task 1 journal and enums.

**Interfaces:** Add keyword-only `_diagnostic_journal=None` to private
`begin_context_command(scope, state, native_owner, transition_owner, policy,
baseline, frame, *, _diagnostic_journal=None)`. Keep public controller/wrapper
signatures and every existing command method signature unchanged. Store the
optional observer privately; no receipt or input capability follows from it.

- [ ] Add fixture `diagnostic_begin(baseline=None)` to the existing `ContextEchoTests`:
  create a fresh controller binding, journal and transition binding, call the private
  optional parameter, return `(command, journal, bindings)`. Existing no-observer
  fixtures remain valid. Tests explicitly acknowledge modeled writes before
  calling `check_edit`/`submission_written`.
- [ ] Write `test_first_failing_predicate_is_frozen_before_revocation` with isolated fixtures per variant:

```python
cases = (
    ('prefix-padding-repaint', 'PREFIX_CELLS'),
    ('tail-after-cursor', 'TRAILING_CELLS'),
    ('extra-control-row', 'NORMALIZED_ELIGIBILITY'),
    ('close-menu', 'FORBIDDEN_UI'),
    ('native-owner-loss', 'NATIVE_LIFETIME'),
)
# For each named synthetic frame, acknowledge 8 command bytes, then observe it.
# Assert reason INPUT_PROBE_REVOKED, command.phase == 'REVOKED', and:
self.assertEqual(observation['phase'], 'EDIT_PENDING')
self.assertEqual(observation['check'], expected_check)
self.assertEqual(observation['commandBytesWritten'], 8)
self.assertEqual(observation['enterBytesWritten'], 0)
```

- [ ] Add `test_actual_renderer_padding_preserved_or_repainted`: feed the existing
  passive helper alternate buffer with NBSP prefix, then fixed command using
  preserved NBSP versus ASCII-space repaint. Preserved case reaches
  `COMMAND_ECHO_MATCHED` without observation; repaint yields `PREFIX_CELLS`.
  No renderer cells enter diagnostics.
- [ ] Add `test_rejection_code_matrix_and_short_circuit_order`: actual boundary
  tests for baseline eligibility, binding/helper loss, deadline/backward clock,
  real `TerminalCancelled`, frame/phase/progress bounds, geometry, cursor range,
  command width/text, regression, incomplete submission, stale numeric
  signature/frame, duplicate history and history eligibility. A two-fault fixture
  reports only the first existing failing predicate. Combined scope rejection
  remains `SCOPE_BINDING`; arbitrary RuntimeError from an accessor is not guessed as cancellation.
- [ ] Add `test_optional_observer_failure_preserves_original_revocation`: inject
  failure in freeze/phase binding and assert the same original exception/reason,
  command revocation and no restored authority. No-observer tests keep their exact existing results.
- [ ] Run `test-terminal-context-echo.py` to meaningful RED for new observation assertions.
- [ ] Label the existing predicates without changing evaluation order or adding
  checks. Bind the run result from the already executed accessor, mirror successful
  phase changes, freeze before revocation. Catch observer errors locally without
  suppressing the original operational failure. Do not instrument later
  receipt/nonce validation after this transition has finished.
- [ ] Run context-echo, journal, input-policy and input-challenge suites to GREEN.
- [ ] Commit explicit Task 2 files: `test: attribute owned context rejection at its source`.

### Task 3: Concrete writer integration and offline transport

**Files:** Modify driver/test, offline launcher/safety test, wiring test and full-gate script.

**Interfaces:** Driver creates the private journal only after its existing audited
scope validation, with one controller identity and the existing transition.
Pass it to Task 2's private begin interface. Extend only the nested `diagnose`
helper with optional `context_command_failure=None`; forward the pure projection
under the collector's exact camel-case field. Public signatures stay unchanged.

- [ ] Extend existing `run_pinned_probe` synthetic fixture with modes
  `prefix-padding-repaint`, `post-command-write-failure`, `post-enter-live-loss`,
  `blocking-command-write`, `invalid-command-write-count`, and `diagnostic-loss`.
  Filter actual PTY writes separately from helper IPC. Keep raw synthetic fixture
  input task-local and disposed; report only assertions/closed results.
- [ ] Add `test_partial_command_failure_reports_only_accepted_bytes` and `test_enter_ack_failure_has_no_completed_submission_checkpoint`:

```python
report = self.run_pinned_probe('partial-command-fault')
failure = next(row for row in report['records'] if row['point'] == 'failure')
self.assertEqual(failure['contextCommandFailure'], {
    'phase': 'EDIT_PENDING', 'check': 'IO_WRITE',
    'commandBytesWritten': 4, 'enterBytesWritten': 0})
# post-enter-live-loss: actual writer accepts Enter, then the existing poll fails.
self.assertEqual(failure_after_enter['contextCommandFailure'], {
    'phase': 'SUBMIT_PENDING', 'check': 'NATIVE_LIFETIME',
    'commandBytesWritten': 8, 'enterBytesWritten': 1})
self.assertNotIn('context_sent', points_after_enter)
self.assertEqual(actual_input_after_enter, b'/context\r')
```

- [ ] Add `test_post_write_failure_retains_ack_before_validation`: force a supported
  failure immediately after a successful 8-byte write; expect count 8 despite
  unadvanced validated command progress, no Enter, original failure and reaped leaders.
- [ ] Add `test_blocking_invalid_and_diagnostic_failure_do_not_change_input`:
  BlockingIOError adds zero before subsequent accepted bytes; invalid count
  suppresses observation and retains IO failure; injected observer errors retain
  original event stream/input/cleanup. No recovery keys or repeated edits are sent.
- [ ] Add `test_controller_boundary_phase_and_first_failure`: actual
  menu/auth/cancellation/deadline paths freeze before invalidation; nested catches
  do not replace a component observation. Later nonce/exit failures carry no stale
  command observation. A second dialogue starts with fresh bindings and zero counters.
- [ ] Add safety/wiring tests: read-only mount contains
  `terminal_context_diagnostics.py`, audit-only mode never mounts/launches Claude,
  module remains absent from Nori staging/archive, new unit suite is in
  `validate-package.sh`, serialized diagnostics cannot satisfy PTY acceptance,
  default/live/CLI interfaces unchanged.
- [ ] Extend complete-envelope test using four maximal diagnostic phases plus
  existing 4096-byte debug allowance and disposal/audit facts; JSON plus newline
  <=16384 bytes. Invalid or overflow evidence never becomes success. Existing
  raw-debug tests still produce `OMITTED_PROVENANCE` for early command rejection.
- [ ] Run selected driver, offline safety and wiring tests to RED, retaining named failures.
- [ ] Integrate actual-byte accounting immediately after count validation and
  before command state callbacks. Label actual controller checks without new
  polls/clock reads; outer exception handling only projects frozen data. Disable
  further command observation after history binding; finish the journal after
  failure projection and before returning, including cleanup failures. Preserve all existing revocation and cleanup paths.
- [ ] Mount the private module read-only beside existing context modules; include its unit suite in the full gate. Keep acceptance events separate from diagnostics.
- [ ] Run journal, collector, context-echo, selected-driver, context-debug, offline-safety, wiring, cancellation and headless-signals suites to GREEN. No actual Claude/provider invocation.
- [ ] Commit explicit Task 3 files: `test: wire bounded context rejection evidence to offline reports`.

### Task 4: Architectural record, immutable verification and handoff

**Files:** `docs/architecture/ADR-010-browser-automation-boundary.md`,
`docs/architecture/README.md`, `CHANGELOG.md`, `tests/validation-notes.md`,
approved spec status and this plan's checkboxes/status.

**Interfaces:** No runtime changes. Record enforced behavior and evidence only;
retain all native/provider/remote CI/Security/merge gates as pending.

- [ ] Add an English ADR-010 subsection and index links to this spec/plan, the four-field observer, exact writer accounting, rejected alternatives, privacy/authority limits and rollback. State that ad7b080's native cause is still unknown.
- [ ] Add a factual unreleased CHANGELOG entry and validation notes listing RED/GREEN suites and actual counts. Update spec status to approved/local implementation as applicable. Do not claim independent review/full gate/native acceptance before observing their outcomes.
- [ ] Run `python3 tests/validate-content.py` and `python3 tests/test-architecture-docs.py` through the route above; expected `content validation passed`, unittest `OK`, exit 0. Verify links, whitespace, line lengths <=300 and unchanged versions/staging scope.
- [ ] Commit explicit Task 4 files: `docs: record content-free context rejection observation`. Verify clean worktree and capture the immutable candidate hash.
- [ ] Run the complete package gate on that candidate, using the same WSL/env prefix with `bash tests/validate-package.sh` instead of `python3 tests/TEST_FILE.py`. Expected exit 0 and final `package validation passed`; record all skips and do not convert them to actual runtime/browser proof.
- [ ] Obtain the selected workflow's independent code review of the implementation
  range on the same immutable candidate. Focus on first-failure provenance,
  post-write acknowledgements, exception/phase binding, diagnostic-loss safety,
  unchanged ownership and content-free budgets. If review is unavailable, stop with that gate pending.
- [ ] Correct reportable findings through author TDD under the chosen execution workflow; any source correction requires a new immutable candidate and a fresh complete gate. Do not launch another native attempt as remediation or verification.
- [ ] Record actual gate/review outcomes in result-only validation notes and plan status. Verify any documentation-only follow-up with content/architecture checks and explicitly distinguish final HEAD from the reviewed/tested source candidate; source must remain unchanged.
- [ ] Hand off final commits, worktree state, synthetic/full-gate/review evidence and pending native/provider/CI/Security gates. Request a fresh final-commit native grant only if the operator chooses that next action; no automatic repetition, push, PR or merge.

## Self-Review and Execution Selection

Spec coverage: Task 1 covers closed atomic provenance/accounting and budgets;
Task 2 covers actual check ordering and pre-revocation phase; Task 3 covers IO,
controller failures, isolation, transport and unchanged defaults; Task 4 covers
indexed architecture, immutable verification, independent review and next gates.
All five review-focus risks have named test steps. Private API names and serialized
field names agree across tasks. No native acceptance is substituted by fixtures.

Recommended execution: **Native/inline**, implementing the four tasks in this
session and requesting one fresh final independent reviewer. The tasks depend
closely on the same journal interfaces, while the review targets their integrated
provenance and IO behavior. Subagent-driven execution remains available if the
operator prefers separate implementation/review per task.

Implementation starts only after the operator reviews this plan and selects or
confirms the execution method. The previous native execution grant remains
consumed regardless of plan approval.
