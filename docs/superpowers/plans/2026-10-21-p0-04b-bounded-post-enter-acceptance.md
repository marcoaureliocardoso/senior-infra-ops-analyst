# P0-04B Bounded Post-Enter Acceptance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permit narrowly correlated post-Enter transients during audited offline
resumed acceptance without granting input until the existing display receipt
and independent nonce/clear/exit protocol justify the next bytes.

**Architecture:** Add an acceptance-only private pending binding to the existing
context-command lifecycle, not to the read-only observer. Compose transient,
history and numeric checks before producing the existing display witness.
Integrate a central phase-aware driver fence that never reopens generic input.
Task 3 also isolates the ordinary outer acceptance lifecycle under one
supervisor through parsing, reap, disposal and final checked result selection.

**Tech Stack:** Existing Python unittest, PTY/namespace fixtures, terminal-state
adapter and Node/xterm helper; Debian WSL package-validation route.

**Spec:** [Approved bounded-transition specification](../specs/2026-10-21-p0-04b-bounded-post-enter-acceptance-design.md).

Plan status: approved for native/inline execution on 2026-10-21; Tasks 1/2 complete,
Task 3 complete at `5a8fb7e` with 109 committed-source focused tests passed.
Independent review completed with one Important finding; the author fix passed
184 regressions and the complete immutable package gate at `950bd19`.
Native/provider/browser and remote acceptance gates remain unproved.
The operator approved the narrow written lifecycle amendment on 2026-10-21;
this Task 3 plan revision was subsequently approved for the same inline method.
Written specification approved on 2026-10-21; planning baseline `5bd1dd6`.
No native execution is authorized by this document or the inline method choice.

## Global Constraints

- CORRELATED_DISPLAY plus independent current-input proof, not NATIVE_RECOMPUTED.
- All HISTORY_COMMIT_V1 criteria, history inventory and later nonce/exit rules stay.
- Observation remains irreversibly read-only after Enter.
- No new public flag, environment switch, caller-provided exclusion or setting.
- Preserve 25 seconds per dialogue, 165 seconds overall including existing cleanup
  allowance, current SDK/request ceilings and original case order: at most text-turn
  then skill-turn, stopping at the first inconclusive case.
- Keep 16 non-submitted synthetic nonce characters, exact echo before one Ctrl+U,
  a newer empty frame, one consumed exit proof, guarded `/exit` bytes and natural exit0.
- Keep 16 records/3072 actual JSON bytes per phase and 16384 bytes for the complete
  outer report including disposal/newline.
- No new timing trace, menu text, row, nonce, prompt, transcript, history or content
  hash may be exported. Content-debug contracts are not broadened.
- No deadline renewal, automatic repeat, installation, runtime/provider/model/window
  pin or operator-state/credential access. No product version bump for test-only scope.
- Keep cancellation supervision through owned reap/disposal; cleanup failure dominates.
- Ordinary acceptance has one absolute 165-second deadline from entry, with
  its final five seconds reserved for bounded cleanup; no renewed timer after
  spawn, read, parse or disposal. No hard real-time cleanup guarantee is claimed.
- Existing native grants are consumed. A later native run requires fresh final-commit
  authorization explicitly covering resumed nonce/clear/exit; no native run in this plan.
- No push, PR, merge, release, staging refresh or definitive TODO completion.

## Review Focus

1. Reentrant writer callbacks at Enter acknowledgement, candidate creation or receipt
   binding must not exploit a small unfenced interval; test in Task 2.
2. A known transient before an unknown marker/authentication row must not hide the
   later rejection through short-circuit assessment; test in Task 1.
3. Incomplete numeric output carrying contradictory values must not become harmless
   absence or be repaired by later baseline restoration; test in Task 1.
4. A valid candidate followed by invalid already-buffered output must not bind a
   stale witness; test at policy level in Task 1 and PTY drain level in Task 2.
5. Cancellation or cleanup failure after the last checkpoint but before publication
   must suppress apparent success, including negative reports; test in Task 3.

## File Map and Boundaries

| File | Responsibility |
| --- | --- |
| `tests/terminal_context_echo.py` | Private pending provenance, composed assessment, witness/receipt lifecycle and irreversible release |
| `tests/headless_context_driver.py` | Prepare/acknowledge the acceptance binding, central write fence and checked protocol dispatch |
| `tests/claude-pty-driver.py` | Preserve wrapper routing and report/cancellation behavior; change only if fence wiring requires it |
| `tests/terminal_context_sample.py` | Reuse existing pure `context_numeric_conflict`; only clarify its observation-only docstring if reused |
| `tests/context_display_fixtures.py` | Opt-in acceptance-pending fixture and both synthetic case kinds |
| `tests/resume_history_fixtures.py` | Controlled PTY/namespace peers with deterministic observation barriers |
| `tests/test-terminal-context-display.py`, `tests/test-terminal-context-echo.py` | Pending, submission, provenance, candidate and retirement regressions |
| `tests/test-headless-context-driver.py`, `tests/test-claude-pty-driver.py` | Concrete input bytes, callback isolation, wrapper and drain regressions |
| `tests/test-offline-terminal-resume-safety.py` | Existing complete-case aggregator, bounded reporting and disposal regressions |
| `tests/offline-terminal-resume-probe.py` | Ordinary acceptance-owned outer supervision through parsing, reap, disposal and final checked return only |
| ADR-010/index, CHANGELOG, validation notes | Truthful implementation, review, gate and native-proof status |

`terminal_resume_history.py` and `terminal_input_challenge.py` retain their current
interfaces; do not add an observation-to-acceptance bridge. Use their existing
validators and dependents. The observer/report modules are regression targets,
not implementation units. Do not split the driver or add a generic terminal adapter.

## Execution Environment and Test Commands

Reuse the linked `p0-04b-browser-automation` worktree after verifying branch,
HEAD, Git/common directories and operator changes. Host Git uses command-local
`-c safe.directory=<absolute-worktree>`; never global configuration or reset.

Focused commands below mean this PowerShell launcher with the named suite:

```powershell
$acceptanceTestArgs = @(
  '-d', 'Debian', '--cd',
  '/mnt/c/projects/senior-infra-ops-analyst/senior-infra-ops-analyst/.worktrees/p0-04b-browser-automation',
  '--', 'env', '-i', 'HOME=/tmp',
  'PATH=/home/marco/.local/opt/node-v24.17.0-linux-x64/bin:/usr/bin:/bin',
  'PYTHONNOUSERSITE=1', 'PYTHONDONTWRITEBYTECODE=1',
  'P004B_TERMINAL_NODE=/home/marco/.local/opt/node-v24.17.0-linux-x64/bin/node',
  'P004B_TERMINAL_MODULE_ROOT=/mnt/c/projects/senior-infra-ops-analyst/.review-runtime/p004b-terminal-state/node_modules',
  '/usr/bin/python3', 'tests/test-terminal-context-display.py'
)
& wsl.exe @acceptanceTestArgs
```

These paths are existing test inputs, not product/version pins. Verify the helper
inputs read-only; do not install or inspect operator Claude settings. Synthetic
fixtures launch Python peers, never installed Claude. RED must be a behavioral
assertion failure, not missing setup/dependencies or a broken test import.
Every task's GREEN command must exit0 with unittest OK and no unexpected skips.
Use native task tracking if exposed; otherwise maintain this checklist accurately.

### Task 1: Acceptance-Owned Pending Classification and Witness Lifecycle

**Files:** Modify `tests/terminal_context_echo.py`,
`tests/context_display_fixtures.py`, `tests/test-terminal-context-display.py` and
`tests/test-terminal-context-echo.py`; reuse `context_numeric_conflict` from
`tests/terminal_context_sample.py` without changing legacy parsing.

**Interfaces:**

- Add `_prepare_acceptance_pending(command: OwnedContextCommand, snapshot: TerminalSnapshot,
  frame: int, *, controller_owner: object) -> None`. Prepare while ELIGIBLE under
  the original audited acceptance view, before command IO; reject observation
  purpose, missing SDK/view, foreign owner or repeated preparation.
- Add `_acknowledge_acceptance_edit(command: OwnedContextCommand, count: int, *,
  remaining: int, controller_owner: object) -> None`. Consume actual positive
  integer IO counts, never bool, for exactly eight body bytes; no journal-derived
  authority. The driver is its only production caller; fixtures simulate IO.
- Keep a private non-copyable `_AcceptancePending` decision distinct from
  `EmptyInputAssessment`; never give it an anchor, receipt, percent or serialized
  representation. `_assess_resumed_context(command, snapshot, frame)` may return
  this internal decision as well as its existing tuple/None results.
- Preserve `OwnedContextCommand.observe(snapshot, frame) -> str`,
  `context_display_percent(snapshot, frame) -> int | None` and
  `bind_history(snapshot, frame) -> ContextEchoReceipt | None`. Only the original
  command's coordinator-facing observation/readiness path may consume pending
  as wait/None. Premature binding or generic composition must fail closed.
- Update `DisplayCase.__init__(*, history_rows=None, baseline_free='81',
  baseline_buffer='3', case_kind='text-turn', acceptance_pending=False)`;
  `submit(*, extra=())` simulates acknowledgements only when explicitly opted in.
  Keep the existing strict fixture default to prove unprepared callers unchanged.

- [x] **Step 1: Write RED tests for pending and full candidate recognition.**
  Add `test_acceptance_pending_keeps_known_menu_and_echo_non_writable`: for both
  kinds, prepare, acknowledge8, prove full echo and Enter1, consume a snapshot
  retaining exact menu/echo, assert readiness None, no witness/receipt and live
  original identities; then remove transients and add a new commit at20, assert
  used16 for free81/buffer3 or used17 for free80/buffer3 and a one-shot receipt.
  Add `test_direct_final_needs_no_transient_or_delay` with the same assertions.
  Add `test_pending_is_not_empty_input_or_bind_authority`: premature binding and
  generic `_compose_input_assessment` reject and cannot later recover.

  Representative equal-value assertions (with existing `replace`/`echo` imports):

  ```python
  with DisplayCase(case_kind=kind, acceptance_pending=True) as c:
      menu = (8, '❯ /context  Synthetic completion')
      c.submit(extra=(menu,))
      waiting = replace(c.snapshot(extra=(menu, (37, '❯ /context'))), cursorX=10)
      self.assertIsNone(c.observe(waiting, 3))
      self.assertNotIn('display_witness', echo._COMMANDS[c.command])
      current = c.snapshot(commit=20)
      self.assertEqual(c.observe(current, 4), 16)
      self.assertIsNotNone(c.command.bind_history(current, 4))
  ```

- [x] **Step 2: Run `tests/test-terminal-context-display.py`; confirm those RED
  assertions fail because the new transition is absent, not because setup fails.**
- [x] **Step 3: Implement the private binding and composed transition.**
  Extend the existing tracker/owner registries. Refresh provenance on every
  consumed pre-Enter observation, including SUBMIT_PENDING writable waits;
  finalize at actual Enter acknowledgement with body8/full echo/Enter1 proved.
  Copy only private read-only menu facts before irreversibly releasing editing
  capability. Preserve exact menu cells, original input row/cursor, inventory,
  pinned/retired rows, helper/case/deadline/geometry and monotonic frame guards.
  Assess all remaining rows in one ordered pass; normalize only the exact owned
  input echo for assessment, never for candidate empty-input proof. Apply
  `context_numeric_conflict(snapshot)` before treating sample None as absence;
  retain cross-frame distinct-sample conflicts. Idempotent same-frame checks
  must not manufacture movement, renewed evidence or duplicate authority.
  Create/validate the existing witness only for the full actual profile; release
  pending raw references permanently on binding, failure, invalidation or closure.
- [x] **Step 4: Add RED/GREEN adversarial subtests.**
  Add `test_transient_plus_later_unknown_or_auth_row_rejects`;
  `test_transient_disappearance_is_monotonic` (menu/echo movement, mutation,
  duplication, unsupported width, draft and reappearance);
  `test_incomplete_numeric_conflicts_survive_restoration` (duplicate free/buffer,
  out-of-range and total>100);
  `test_candidate_loss_during_revalidation_is_terminal`;
  `test_inventory_pinned_and_retired_cells_never_become_commit`;
  `test_preparation_and_acknowledgements_are_owned_one_shot` (bool/partial/wrong
  counts, stale/copy/foreign bindings, every owner/lifetime/cancellation loss);
  `test_pending_exclusions_end_before_nonce_and_exit` (transient return rejects).
  Assert REVOKED/rejected view and absence of a usable receipt after each fatal
  case; completion-only/input-clear-only/numeric-only output cannot mint one.
  Include forged/replayed witnesses and observation request/summary/tombstone
  substitution: no path may produce acceptance or restore a revoked capability.
- [x] **Step 5: Run both modified suites plus `test-terminal-resume-history.py`,
  `test-terminal-input-challenge.py`, `test-terminal-context-sample.py`,
  `test-terminal-history-rejection.py` and `test-terminal-post-enter-observation.py`.
  Confirm GREEN; initial/non-resumed and unprepared strict routes unchanged.**
- [x] **Step 6: Commit only Task 1 files as
  `test: add owned passive acceptance transition`.**

### Task 2: Central Write Fence and Guarded Protocol Integration

**Files:** Modify `tests/headless_context_driver.py`,
`tests/resume_history_fixtures.py`, `tests/test-headless-context-driver.py` and
`tests/test-claude-pty-driver.py`; modify `tests/claude-pty-driver.py` only if needed
to preserve the existing private routing/cancellation contract.

**Interfaces:**

- Consume Task 1 preparation/acknowledgement helpers, original command readiness
  and receipt APIs; no CLI flag or second resume offer.
- Retain `drive_context(...)` and wrapper `drive(...)` signatures. Prepare only
  an audited resumed acceptance command, never an observational/content-debug
  invocation, and feed actual command IO acknowledgements into Task 1.
- Extend local `write_terminal(data, *, direct=False, _dispatch=None) -> int`:
  after Enter, generic direct/whole writes are forbidden permanently. A private
  one-shot dispatch record can authorize only the exact next independently
  checked protocol chunk, not open the writer generally.
- Add local `write_probe_chunk(payload: bytes, phase: str) -> int`. It creates
  and consumes that dispatch immediately at IO, checking original probe/receipt/
  view/controller/native identities, frame, phase and exact pending bytes.
  No callback or await between final checks and one-shot dispatch consumption;
  reentry and reused/mismatched records reject. Keep these records driver-local.
- Keep `owned_write(payload, phase)` responsible for partial counts, writable
  waits and revalidation after every pump/await. The observer's `input_sealed`
  path remains unconditional and must never enter `write_probe_chunk`.

- [x] **Step 1: Write `test_acceptance_waits_passively_then_proves_input` using
  `ResumedHistoryDriverTests.run_owned` and deterministic peer barriers.**
  For text/skill, equal/changed numbers, direct-final and exact transient paths,
  assert zero bytes after Enter until current-profile proof; final input matches
  `rb'^/context\r[0-9a-f]{16}\x15/exit\r$'`, result0, one context-display checkpoint
  before nonce, exact echo, newer empty frame, natural exit and reaped helpers.
  Never rely only on sleeps to establish that an intermediate frame was consumed.
- [x] **Step 2: Run `tests/test-headless-context-driver.py -k acceptance`; confirm
  RED from existing strict rejection/missing fence behavior.**
- [x] **Step 3: Wire preparation before body IO, acknowledge actual edit writes,
  and activate the driver fence at Enter's actual acknowledgement before any
  later callback/pump dispatch.**
  Keep the acceptance fence distinct from irreversible observation sealing;
  `pump` must still validate the live acceptance command, not dereference an
  observer merely because input is fenced. Use Task 1's single composed result,
  drain available output under original limits, revalidate the latest candidate,
  bind the receipt and construct the existing challenge. Route only guarded
  nonce/clear/exit chunks through `write_probe_chunk`; all startup keys,
  terminal-generated responses and generic callbacks stay forbidden after Enter.
- [x] **Step 4: Add RED/GREEN fence and output-order tests.**
  Add `test_acceptance_blocks_raw_and_whole_callbacks_at_every_boundary` for
  actual Enter acknowledgement, passive pending, candidate, binding and nonce
  phases; call both writer forms with b'X', extra Enter/Escape/Tab/Ctrl+U and
  `/exit`, assert failure before IO and no later success. Include a callback
  after receipt binding, a reused/mismatched dispatch, partial IO counts,
  BlockingIOError and auth/history loss during writable waits.
  Add `test_acceptance_drain_cannot_skip_fatal_intermediate_frame`: a valid
  candidate then consumed conflicting/moved/menu frame and restoration rejects
  without nonce. Add delayed/fragmented/native-exit/helper/protocol/cancellation
  and terminal-response peers; every consumed fatal frame must remain fatal.
  Add `test_exit_menu_does_not_reactivate_pending` and assert no escape/second key.
- [x] **Step 5: Run the full headless/wrapper suites, Task 1 suites and existing
  `test-terminal-post-enter-observation.py`/`test-post-enter-observation-report.py`.
  Confirm the observer still receives exactly `/context\r`, never nonce/clear/exit
  or acceptance checkpoints; initial/default/non-resumed/debug paths unchanged.**
- [x] **Step 6: Commit only Task 2 files as
  `test: fence resumed acceptance writes through input proof`.**

### Task 3: Complete-Case Reporting, Disposal and Status Documentation

**Files:** Extend `tests/test-offline-terminal-resume-safety.py` and controlled
namespace peers in `tests/resume_history_fixtures.py`; update
`tests/offline-terminal-resume-probe.py` only for the approved outer lifecycle;
update
`docs/architecture/ADR-010-browser-automation-boundary.md`,
`docs/architecture/README.md`, `CHANGELOG.md` and `tests/validation-notes.md`.
Do not relax `offline-terminal-resume-probe.py` acceptance predicates.

**Interfaces:** Consume existing `case_complete(case) -> bool`,
`run_cases(run_case) -> dict` and namespace fixture routing. Output remains the
existing acceptance schema/checkpoints, not the observational report schema.
No new retained chronology, diagnostic enum or authority-bearing JSON.
Produce private `_acceptance_namespace_report(command: list[str], root: Path,
identity: os.stat_result, *, deadline: float) -> dict` in the existing probe.
It consumes the already-built namespace command, original root identity and
absolute deadline; returns the existing bounded standard report after cleanup.
Consume unchanged `TerminalCancellation`, `finalize_owned(root, identity,
report) -> dict`, `_failed(...)` and `_bounded_standard_report(...)` contracts.
Do not modify `case_complete`, `run_cases` or the generic cancellation API.

- [x] **Step 1: Write `test_transient_acceptance_preserves_complete_case_contract`.**
  Run only controlled synthetic peers through the existing isolated namespace
  fixture. Assert text then conditional skill ordering, all required display,
  nonce/clear/natural-exit and four cleanup facts; incomplete first case prevents
  the second. A pending/candidate-only or observation-schema result fails
  `case_complete` even with child exit0. Record already-GREEN unchanged-contract
  checks as characterization, not invented RED; every necessary behavior fix
  still requires its own reproduced failing assertion before implementation.
- [x] **Step 2: Add `test_success_is_suppressed_until_final_disposal`: inject
  cancellation/expiry after the last checkpoint and cleanup failure for positive
  and negative outcomes; assert no success and cleanup-failure dominance.
  Add `test_report_pressure_does_not_erase_required_proof`: optional diagnostic
  loss cannot bypass failure, missing mandatory proof fails, phase records<=16,
  actual encoded phase bytes<=3072 and outer bytes including newline<=16384;
  no raw content/nonce/history/trace/hash in retained results.**
- [x] **Step 3a: Reproduce the preserved lifecycle RED before source changes.**
  Run `tests/test-offline-terminal-resume-safety.py -k success_is_suppressed`.
  Expect six failing parse/dispose x SIGTERM/SIGHUP/expiry subcases, not a setup
  error. Keep the valid fixed text/skill envelopes and dedicated subprocess
  supervisor; no native client or provider. Step 1 and report pressure already
  passed as characterization; do not relabel them as failing behavior tests.
- [x] **Step 3b: Add boundary regressions before implementing the helper.**
  Add `test_acceptance_lifecycle_checks_read_and_teardown`: inject latched
  cancellation and simulated expiry after capture read and during supervisor
  teardown; expect interrupted/blocked, never passed, and actual owned-root
  removal. Extend the existing parse/dispose signal tests to assert those exact
  closed reasons and no post-terminal continuation, not merely "not passed".
  Add `test_acceptance_cleanup_failure_dominates_every_outcome`: complete,
  incomplete, invalid JSON, nonzero child, cancelled and expired inputs with
  simulated reap/disposal failure must return OFFLINE_CLEANUP_FAILED and cannot
  claim unproved cleanup. Use only owned synthetic fixture roots; the parent
  removes deliberately retained test residue. Record each actual RED/GREEN.
  Add `test_acceptance_deadline_is_not_renewed` with a controlled monotonic
  clock: preparation consumes the original budget, execution stops at its
  original cutoff and post-disposal expiry blocks success. Add
  `test_acceptance_mode_routing_is_unchanged`: only standard acceptance reaches
  the planned helper; audit, debug-context, debug-context-edit and
  observe-post-enter use their original routes. An absent helper is expected
  RED until Step 3c, not evidence of mode coverage.
- [x] **Step 3c: Implement `_acceptance_namespace_report` and ordinary routing.**
  In `_namespace`, establish the ordinary acceptance deadline before preparation
  and route only its existing standard mode to the helper. Audit, debug and
  read-only observer retain their current routes, schemas and helpers. The
  helper keeps one `TerminalCancellation` active before spawn through bounded
  capture, parse/classification and report fitting. Stop child work at
  `deadline - 5`; check liveness/deadline across phase boundaries. Close capture
  handles, reap the owned cohort, then call `finalize_owned` under the same
  owner's cleanup deferral. Every entered error path must attempt that cleanup.
  Select the bounded result under supervision and check the latched request and
  original deadline again after teardown, immediately before return. Never
  replace a known cleanup failure with interrupted/blocked/success. A late
  cancellation/expiry must replace a passed result, not just annotate it.
  Use existing structural diagnostics/reasons only; keep valid nonzero-child
  diagnostics without trusting child success, and keep the full encoded report
  including disposal/newline <=16384 bytes. No duplicate reap/disposal in the
  caller, observation capability reuse, generic cancellation changes or new
  input authority. If this private boundary cannot meet the approved amendment,
  stop for scope review rather than refactor other modes.
- [x] **Step 3d: Run the lifecycle regressions and compatibility checks.**
  Run the offline suite with `-k acceptance`, then `-k success_is_suppressed`;
  expect exit0/OK, including the original-budget and mode-routing tests written
  in Step 3b. Retain malformed/oversize/nonzero-child tests,
  missing mandatory proof rejection and first-inconclusive case stopping.
- [x] **Step 4: Run `tests/test-offline-terminal-resume-safety.py`,
  `tests/test-post-enter-observation-report.py`, `tests/test-terminal-cancellation.py`
  and `tests/test-headless-driver-signals.py`; confirm GREEN without installed
  Claude, provider, credentials or operator-state access.**
- [x] **Step 5: Update ADR/index, CHANGELOG and validation notes with actual
  implementation scope and exact fresh results/exclusions. Keep native acceptance
  explicitly unproved; do not reclassify the successful observation. Run content,
  architecture and release-history checks; commit as
  `test: verify bounded acceptance reports and disposal`.**

## Whole-Change Review and Immutable Gate

- [x] Self-check every spec requirement against Tasks 1-3; record any untested
  platform path rather than assuming support. Verify executable-source diff,
  unchanged runtime/Nori/provider/production/version policies and clean status.
- [x] Request one fresh independent whole-change review using the applicable
  review skill after the selected execution workflow's task gates. Review the
  cumulative immutable commit range and this spec/plan; assess authority, all
  writer paths, intermediate observations, witness retirement and cleanup.
  Reviewer suggestions are not permission to expand the approved design.
- [x] Resolve validated findings with author-owned RED/GREEN tests. Record
  review/fix commits and whether corrections were independently re-reviewed;
  do not mislabel author verification as a fresh independent review.
- [x] Run the complete immutable package gate on corrected committed source.
  Use the launcher environment above, replacing its final two arguments with
  `/bin/bash`, `tests/validate-package.sh`. Confirm exit0 and literal
  `package validation passed`; keep original per-test guards and exclusions.
  Verify canonical contents/types/modes unchanged before/after, capture exact
  commit and structural results and distinguish skips from tested behavior.
- [x] Record gate outcome truthfully. If that produces a docs-only commit,
  rerun documentation checks and prove executable-source equivalence to the
  gated commit. No behavioral change can inherit the previous gate.
- [x] Hand off the final commit and remaining acceptance gates. A native run
  requires a separate fresh one-shot authorization; no attempt, grant renewal
  or retry occurs automatically. Browser/provider, remote CI/Security and merge
  acceptance remain separate from this offline implementation.

## Rollback and Operator Review

Rollback removes the acceptance-only passive transition and its driver fence
integration together, retaining strict original history/menu/nonce controls
and the independent read-only observer. Do not rewrite historical evidence,
delete consumed markers or restore an old grant.

Self-review maps activation/provenance/transients/numeric/witness requirements
to Task 1, write isolation and independent input proof to Task 2, and reporting,
bounds/disposal to Task 3 plus the immutable gate. Each Review Focus item has
a named owning test. Private pending results are never input assessments;
private dispatch records authorize one checked chunk, not a generic writer.

The operator selected native/inline execution. Task 1 (`57a8381`, 182 tests) and
Task 2 (`d1c8911`, 315 tests including shared regressions) are complete locally.
Task 3's namespace contract and pressure checks passed; its final-publication
lifetime test reproduced six failures. The ordinary outer `_namespace` ends
its cancellation supervisor before parsing/disposal and does not recheck expiry
there. This unchanged preexisting path is outside Tasks 1/2's implementation
units. The operator approved the narrow lifecycle amendment after the original
design-review stop and then approved Steps 3a-3d for inline implementation.
The acceptance-only outer helper is implemented locally and the preserved RED
tests now pass. Final report selection stays supervised; cleanup/teardown
failure dominates every result. The corrected full task gate passed 109 tests;
the separate committed-source completion command also passed. One independent
whole-change review identified a numeric-token guard defect. The author TDD
fix preserves legacy parsing and rejects signed/oversized conflicts irreversibly;
its corrected-source 184-test regression group passed. The immutable package
gate passed at `950bd19` (exit0, 554 canonical files verified before/after).
No second review or renewed native grant. Native acceptance remains unproved. See
`tests/validation-notes.md` for exact outcomes and scope.
