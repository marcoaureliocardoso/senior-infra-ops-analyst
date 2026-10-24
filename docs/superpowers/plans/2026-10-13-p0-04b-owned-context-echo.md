# P0-04B Owned Context Echo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Distinguish the isolated harness's proven context echo from current editable input without weakening default assessment or nonce ownership.

**Architecture:** A private command-edit state machine observes exact echo before its single Enter and binds at most one post-submission history receipt. One shared ordered assessment applies that narrow exception throughout nonce/clear/exit validation. Frozen rejection
observations support debugging but never create input authority.

**Tech Stack:** Existing Python PTY controller, passive Node/xterm terminal adapter and Debian WSL offline namespace. No new dependencies or version requirements.

**Spec:** [Owned context echo design](../specs/2026-10-13-p0-04b-owned-context-echo-design.md).

Status: approved inline local implementation complete. One independent review's findings were corrected by author TDD; matching complete package validation passed. No second review. Native acceptance remains pending; this document authorizes no native/provider execution.
Planning baseline: `566fa4d9159256e5da385c248048690e163c63a5`.

## Global Constraints

- Only the existing audited offline launcher may supply the private capability.
- No real provider or operator credential is read or used.
- Default pure policy APIs and their strict rejection order remain unchanged.
- Bind terminal, live native process, offline scope, run owner, transition and original monotonic deadline; no serialized, CLI or environment proof creation.
- Keep 25 seconds per context dialogue, 165 seconds per enclosing run and at most two cases; preserve existing SDK turn/request and IPC/capture limits.
- Keep diagnostics at 16 records and 3 KiB per phase; complete outer report at 16 KiB, including audit facts, disposal receipt and final newline.
- Keep optional debug at one temporary frame of 128 KiB and one sanitized recut of 4 KiB; raw capture/history/roots removed before aggregation.
- Exactly 16 random ASCII hexadecimal nonce characters, without submission; one guarded Ctrl+U only after exact echo; fixed `/exit` only after newer empty-frame proof.
- No automatic retry, operational grace period, passive recovery fallback, renderer/version pin, global settings change or dependency installation.
- No receipt or raw content in Git, staging, releases or durable diagnostics; chat copies of an explicitly authorized debug recut may persist.
- Fresh exact-final-commit native grant after matching tests/review/gate, including the new `/context` edit/echo/Enter sequence. Old grant consumed.
- Original provider/browser acceptance, remote CI/Security and main merge remain separate; do not mark the definitive unversioned TODO complete.

## Review Focus

1. Ordinary redraw or write acknowledgement must not replace a newer exact echo before Enter (Task 1).
2. A pre-existing `/resume` command echo must not acquire ownership when a new transition starts (Tasks 1 and 2).
3. Native autocomplete, late menu/auth output or short writes must not allow unproved Enter, clear or remaining exit bytes (Task 2).
4. A receipt-aware rejection after a different unowned row must not export the excluded historical row as its cause (Tasks 1 and 2).
5. Diagnostic expansion and namespace wiring must preserve final byte budgets, content disposal and default/live rejection (Task 3).

## Execution and command convention

Reuse the existing isolated `p0-04b-browser-automation` worktree after fresh HEAD/status checks. Follow its AGENTS.md, applicable skills and approved spec. Preserve operator changes and use command-local `safe.directory` for Windows Git; do not modify global Git configuration.

All `python3 tests/...` and `bash tests/validate-package.sh` commands below mean the same bounded invocation from PowerShell through Debian WSL:

```powershell
wsl.exe -d Debian `
  --cd /mnt/c/projects/senior-infra-ops-analyst/senior-infra-ops-analyst/.worktrees/p0-04b-browser-automation `
  -- env -i HOME=/tmp PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 `
  PATH=/home/marco/.local/opt/node-v24.17.0-linux-x64/bin:/usr/bin:/bin `
  P004B_TERMINAL_NODE=/home/marco/.local/opt/node-v24.17.0-linux-x64/bin/node `
  P004B_TERMINAL_MODULE_ROOT=/mnt/c/projects/senior-infra-ops-analyst/.review-runtime/p004b-terminal-state/node_modules `
  python3 tests/test-terminal-context-echo.py
```

The paths locate already retained test dependencies, not package compatibility pins. Check their availability without launching Claude. If unavailable, report the missing dependency; do not install, change provider settings or run native probes automatically. Hyphenated test
files run directly, not through unittest discovery.

## File boundaries

- New `tests/terminal_context_echo.py`: sealed command lifecycle, immutable receipt, receipt-aware assessment and non-authoritative rejection projection.
- `tests/terminal_input_policy.py`: one pure ordered evaluator shared by default and validated history exclusion; no IO.
- `tests/terminal_input_challenge.py`: existing scope registry and nonce/clear/consume protocol; no new execution route.
- `tests/headless_context_driver.py`: checked actual writes and exact transition integration.
- `tests/terminal_context_debug.py`: unchanged privacy gates, recut from the actual rejected row.
- `tests/offline-terminal-resume-probe.py`: source mount wiring only, unchanged case/namespace/run contracts.
- Unit, fake-PTY, wiring/safety and package tests; ADR-010, its index, CHANGELOG, spec status and validation notes.

### Task 1: Correlated command receipt and shared ordered assessment

**Files:** Create `tests/terminal_context_echo.py` and `tests/test-terminal-context-echo.py`. Modify `tests/terminal_input_policy.py`, the scope accessor in `tests/terminal_input_challenge.py`, and `tests/test-terminal-input-policy.py`.

**Interfaces consumed:** Existing `OfflineProbeScope`, `TerminalState`, `TerminalSnapshot`, `TerminalInputPolicy`, `InputAnchor`, `EmptyInputAssessment`, `InputProofError` and original scope deadline/run-owner metadata.

**Interfaces produced:**

- Policy private `_empty_input_assessment(snapshot: TerminalSnapshot, excluded_row: int | None = None) -> tuple[EmptyInputAssessment, int | None]`. Second item is the actual unsupported-row index, otherwise None. Public APIs continue returning their existing types/fields and call
  this with no exclusion.
- Scope private `_context_scope_binding(scope: OfflineProbeScope, terminal: TerminalState, *, allow_claimed: bool = False) -> tuple[object, float]`: run owner and original deadline. Audit/identity/lifetime checks; never resets a scope or releases its claim.
- `begin_context_command(scope, state, native_owner, transition_owner, policy, baseline, frame) -> OwnedContextCommand`. Exact object bindings, private seal/registry and at most one beginning per scope. Local imports avoid a challenge/echo import cycle.
- `OwnedContextCommand.type_bytes(snapshot, frame) -> bytes`: once-only fixed `b'/context'`; `check_edit(snapshot, frame, written: int) -> None`: validates owned prefix with 0 <= written <= 8.
- `OwnedContextCommand.observe(snapshot, frame) -> str`: closed phases `ELIGIBLE`, `EDIT_PENDING`, `COMMAND_ECHO_MATCHED`, `SUBMIT_PENDING`, `CONTEXT_PENDING`, `RECEIPT_READY`, `REVOKED`.
- `OwnedContextCommand.submit_bytes(snapshot, frame) -> bytes`: once-only `b'\r'`, rechecks full echo and sets the numeric barrier with `policy.mark_transition(snapshot)` before Enter can be written.
- `OwnedContextCommand.submission_written(count: int) -> None`: exactly count == 1 moves SUBMIT_PENDING to CONTEXT_PENDING; no acknowledgement alone creates history ownership.
- `OwnedContextCommand.bind_history(snapshot, frame) -> ContextEchoReceipt | None`: requires a newer fresh numeric observation; one new exact supported off-cursor `/context` echo returns a sealed immutable receipt; no echo returns None and keeps strict assessment. Ambiguity
  fails, never yields a permissive None.
- `OwnedContextCommand.invalidate(reason: str) -> None`: terminal revocation, with no reconstruction or re-binding.
- `validate_context_history(receipt, policy, snapshot, *, scope, state, native_owner, transition_owner, frame) -> int`: validates exact live bindings, original deadline, monotonic frame/time, bound input location and unchanged history; returns only the validated history-row index.
- `assess_context_input(policy, snapshot, *, receipt, scope, state, native_owner, transition_owner, frame) -> tuple[EmptyInputAssessment, ContextRejectionObservation | None]`: strict default for receipt None; otherwise validated exclusion followed by the same pure evaluator. The
  observation is sealed, immutable, bound to this exact snapshot/assessment/selected row and not serializable authority.
- `attach_context_rejection(error: InputProofError, observation: ContextRejectionObservation | None) -> InputProofError`; `context_rejection_projection(error, snapshot, policy) -> tuple[bool, int | None]`. Boolean marks a receipt-aware observation; invalid or mismatched
  observation returns (True, None), never a default fallback. Valid selected row returns (True, index); ordinary errors return (False, None).

All input types above are the existing in-process types, not dictionaries. Receipt/observation repr hides raw fields. Existing reason codes suffice: SCOPE_REJECTED for scope/host forgery, STATE_REJECTED for phase/frame/count misuse, REVOKED for lost
echo/history/owner/auth/menu/helper, DEADLINE for expired/backward clock, INELIGIBLE plus existing metadata for structural assessment, IO_FAILED for failed concrete writes; all use the existing `INPUT_PROBE_` prefix.

`bind_history` is once-only even when it returns None. Receipt geometry pins the input row/marker and buffer/viewport, not a constant cursor column during owned typing; command/nonce/exit checks validate their own exact cursor advancement. None never discards a previously bound
receipt after failure. Default no-receipt consumers keep their existing behavior and test seams.

- [x] **Step 1: Write unit tests before implementation.** Use synthetic cell fixtures and audited-scope test seams only; no Claude/provider/browser. Define fixture helpers `self.begin()` as the factory call and `self.assess(snapshot, receipt, frame)` as the assessment call using
  that fixture's bindings.

```python
def test_exact_command_echo_submission_then_owned_history(self):
    command = self.begin()
    self.assertEqual(command.type_bytes(self.empty, 1), b'/context')
    self.assertEqual(command.observe(self.command_echo, 2), 'COMMAND_ECHO_MATCHED')
    self.assertEqual(command.submit_bytes(self.command_echo, 2), b'\r')
    command.submission_written(1)
    receipt = command.bind_history(self.numeric_history, 3)
    self.assertIs(type(receipt), ContextEchoReceipt)
    assessment, rejection = self.assess(self.numeric_history, receipt, 3)
    self.assertEqual(assessment.anchor.row, 37)
    self.assertIsNone(rejection)
    self.assertIsNone(self.policy.empty_input_anchor(self.numeric_history))
```

The positive fixture uses rejecting history row 10, cursor row 37/column 2 and numeric 16%; these are fixture values only. Add another positive fixture at different valid coordinates to prove no row pin. `self.command_echo` must put all eight fixed characters in the original
anchor at a newer frame; `self.numeric_history` contains a genuinely new context signature and exactly one new off-cursor echo.

Add assertions in named tests:

- `test_partial_echo_cannot_submit_until_complete`: proper partial echo can progress, but Enter is rejected until all eight characters are verified in a newer frame.
- `test_write_ack_or_stale_grid_cannot_bind_history`: ack alone and unchanged context signatures never yield a receipt.
- `test_preexisting_resume_echo_and_duplicate_rows_rejected`: baseline containing history is ineligible; duplicate/new unowned marker after submit remains rejected.
- `test_receipt_constructor_serialized_host_foreign_or_replayed_rejected`: private construction, dict/flag, host audit, changed terminal/native/run/transition/policy, second begin or reused receipt cannot validate.
- `test_history_change_disappearance_or_geometry_change_revokes`: changed cells, disappearance, movement, viewport/buffer change and cursor-location loss revoke instead of re-binding.
- `test_shared_assessment_preserves_default_order_and_actual_rejection`: all old default outcomes/types stay identical; owned history plus a different unsupported row rejects that actual row with its original relation/cause.
- `test_rejection_projection_is_snapshot_bound_and_non_authoritative`: wrong snapshot or forged projection is (True, None); frozen diagnostics cannot create a receipt or input proof.
- `test_expiry_backward_clock_cancellation_helper_or_native_loss`: each lifetime failure denies the next action, including a check after an intervening wait.

- [x] **Step 2: Run `python3 tests/test-terminal-context-echo.py`.** Observe expected missing-module/interface assertion failure; never label an environment error as the intended RED.
- [x] **Step 3: Implement the interfaces above.** Keep the shared evaluator's ordering/types, classify only the validated exact historical row specially, and leave actual snapshots untouched. Private state records do not widen scope or default APIs.
- [x] **Step 4: Run the new unit file plus `tests/test-terminal-input-policy.py` and `tests/test-terminal-input-challenge.py` directly.** Expected: all pass, with no native launch. Check no raw-cell/nonce repr or durable records.
- [x] **Step 5: Commit only Task 1 files** as `test: add correlated offline context echo receipt` after fresh diff checks.

### Task 2: Integrate the receipt across actual edit/proof/exit and observation

**Files:** Modify `tests/headless_context_driver.py`, `tests/terminal_input_challenge.py`, `tests/terminal_context_debug.py`, `tests/test-headless-context-driver.py`, `tests/test-terminal-input-challenge.py` and `tests/test-terminal-context-debug.py`.

**Interfaces consumed:** All Task 1 interfaces, existing pump/frame/deadline/cancellation, StartupApproval, TerminalDiagnostics and passive terminal state. No new selected-driver flag or public proof parameter.

**Interfaces produced:**

- `NonceInputChallenge.__init__(scope, native_owner, transition_owner, policy, initial, frame, *, context_receipt=None)`: backward-compatible None; validated receipt path applies `assess_context_input` consistently in construction, pre-type, normalized echo, clear, PROVEN and consume checks.
- `exit_input_owned(policy, snapshot, anchor, original_row, written, *, context_receipt=None, scope=None, state=None, native_owner=None, transition_owner=None, frame=None) -> bool`: legacy default unchanged; receipt path validates bindings on every partial exit write before shared assessment.
- Existing `drive_context` signature unchanged. Audited active scope selects the new command protocol; passive/default branches retain their original command send and barriers. Observer capture/report signatures remain unchanged.
- Rejected assessments construct the existing InputProofError and attach the exact sealed observation. Normalized working snapshots cannot be substituted for the actual source snapshot: if identity/provenance is unavailable, debug omits content rather than reconstructing it.

- [x] **Step 1: Add fake-PTY tests that initially fail.** Extend the controlled fixture to echo each owned command prefix without Enter, receive exactly one Enter only after complete echo, then show numeric context and its one historical row. Keep distinct modes that
  intentionally omit/forge command echo; do not make a fixture fabricate provenance silently.

```python
def test_owned_context_history_allows_nonce_clear_and_natural_exit(self):
    data, events, diagnostics = self.run_owned_echo_case('success')
    self.assertEqual(data[:9], b'/context\r')
    self.assertRegex(data[9:25], rb'^[0-9a-f]{16}$')
    self.assertEqual(data[25:], b'\x15/exit\r')
    self.assertEqual(events[-1]['outcome'], 'passed')
    self.assertFalse(diagnostics['rejected'])
    self.assertFalse(diagnostics['truncated'])
```

Define `run_owned_echo_case(mode)` in this test file; it returns captured synthetic input bytes, existing proof-event records and closed diagnostics from the actual selected driver. It launches only a Python test UI and the passive helper, not Claude.

Keep strict history rejection in default-policy tests. A unique post-submission command echo following every newly proved predicate is now the positive case, not an unowned-history negative. Define active negative history fixtures by an actually failed predicate: history already
in the baseline, missing pre-submit echo, duplicate echo, or an additional different unowned marker. An old fake UI that waits for Enter without echoing cannot serve as a valid command-ownership fixture.

Pin additional assertions by mode:

- `missing-command-echo`, `wrong-command-echo`, `autocomplete-marker`: no Enter, nonce, Ctrl+U or exit; one failure and both leaders reaped.
- `partial-command-write`: bounded prefix progress can complete; an injected write error denies the remaining bytes and submission.
- `menu-before-submit`, `auth-before-submit`, `late-writable-menu`: no Enter after the observed transition, even if the UI later erases it.
- `unowned-history`, `duplicate-history`, `resume-history`: no nonce; receipt shape/appearance alone is insufficient.
- `history-mutated-during-nonce`, `auth-after-echo`, `menu-before-clear`, `expired-before-proof`, `partial-exit-menu`: no later clear/exit bytes after authority loss; no receipt-dropping fallback.
- `wrong-echo-row`, `nonce-in-history`, `uncleared`: never consume InputOwnershipProof; preserve existing nonce duplicate/anchor checks.
- `different-rejected-row-debug`: actual unknown row is selected, not the excluded owned echo; excerpt withheld until root disposal. Wrong-source or normalized-only provenance gives OMITTED_PROVENANCE, with no content or permission.

Extend challenge tests to exercise the same valid receipt through every check and to revoke it at each phase. Extend debug tests to preserve current sensitive omission, 128/4-KiB bounds, exclusive private file, cleanup and complete-envelope budget. No marker, receipt or raw cells enter diagnostics.

- [x] **Step 2: Run the three changed test files directly.** Observe RED in the new interfaces/owned-echo path before integration, not by weakening an old negative fixture.
- [x] **Step 3: Integrate the defined interfaces.** Drain/recheck before and after writable waits; call `check_edit` for each actual command prefix write, wait for complete echo, use `submit_bytes`, immediately record its actual one-byte write via `submission_written`, then wait
  for fresh numeric output and bind history. Do not reset the numeric barrier after context output has already been parsed.
- [x] **Step 4: Propagate the same receipt through all nonce/clear/consumption/exit checks.** Invalidate command/receipt in the existing failure/finally path. Keep original startup consent/revocation, key selection, namespace boundaries, cleanup, proof events and checkpoint
  names; do not add redundant structural records.
- [x] **Step 5: Update debug projection.** A valid attached projection selects its actual rejecting row and recomputes only the frozen pure classification; an invalid attached projection omits content without strict-default fallback. Ordinary errors retain existing strict capture
  behavior. Projection cannot validate/revive operational authority.
- [x] **Step 6: Run the three affected files plus Task 1 tests, policy, diagnostics, terminal wiring, cancellation and headless-signal tests directly.** Expected: all pass; no real Claude/provider/browser. Validate no extra bytes after each failure and unchanged public/default contracts.
- [x] **Step 7: Commit only Task 2 files** as `test: enforce owned context echo across input proof` after fresh diff checks.

### Task 3: Offline wiring, package evidence and delivery boundaries

**Files:** Modify `tests/offline-terminal-resume-probe.py`, `tests/validate-package.sh`, `tests/test-offline-terminal-resume-safety.py`, `tests/test-terminal-wiring.py`, `CHANGELOG.md`, `tests/validation-notes.md`, indexed ADR-010, its index and spec/plan status. Root README only
if concise guidance is materially needed; no historical release-section expansion.

**Interfaces consumed:** Existing namespace audit and offline controls, Task 1/2 implementation, closed diagnostics and unchanged run_cases/case_complete/finalize_owned contracts.
**Interfaces produced:** Read-only namespace mount of `terminal_context_echo.py`; new direct unit test wired into the package gate. No flags, schemas, live activation or installed artifacts added. Documentation names the actual implemented/verified state without claiming native acceptance.

- [x] **Step 1: Add failing wiring/safety assertions.** `test_offline_namespace_mounts_owned_echo_module` checks the exact owned source mount; `test_no_live_or_serialized_receipt_activation` proves existing default/live interfaces reject activation;
  `test_owned_echo_source_excluded_from_nori_staging` keeps all test-only files outside packaged roots. `test_owned_echo_failure_stops_first_case_and_disposes` uses a controlled fixture, proves no SDK/second case/retry after failure and owned raw/root removal.
  `test_owned_echo_complete_report_stays_bounded` includes audit facts/receipt/newline at 16 KiB and diagnostics at 16/3 KiB.
- [x] **Step 2: Run offline-safety and wiring test files.** Observe the intended RED, without mounting or launching Claude. Actual namespace audit uses its existing audit-only path and passive helper; unavailable capability stays an explicit skip/block, not a native pass.
- [x] **Step 3: Add the read-only module mount and direct test invocation.** Preserve case order, synthetic prompts, configured SDK limits, runtime detection, unknown-capability rejection and all cancellation/signal/disposal behavior.
- [x] **Step 4: Run Task 3 tests, `tests/test-nori-staging.py`, `tests/validate-content.py` and `tests/test-architecture-docs.py`.** Expected: green assertions and unchanged package selection. Record skips and absent capabilities honestly.
- [x] **Step 5: Update documentation and commit Task 3 source/docs.** Keep root 0.15.0 unreleased and component versions unchanged unless distribution actually changes. Record synthetic evidence, residual native risks and rollback as a unit; do not mark the definitive TODO
  complete. Commit as `test: wire owned context echo into offline validation`.
- [x] **Step 6: Freeze an immutable candidate diff and request one independent scoped review.** Verify base/head/diff identity; follow requesting-code-review. The reviewer must cover receipt forgery/replay/lifetime, all concrete write boundaries, default/live behavior, debug
  provenance, cleanup and budgets. Document source-only or execution limits; no review result creates native authority.
- [x] **Step 7: Run `bash tests/validate-package.sh` through the defined WSL environment on the frozen candidate.** Require complete exit 0 and `package validation passed`, including schema/local workflow checks. Recheck candidate hash. If source changes to fix a finding, obtain
  matching validation/review; do not present prior-candidate results as fresh evidence.
- [x] **Step 8: Record final author-observed results and review rulings in validation notes.** Validate result-only docs with content/architecture tests and diff checks before their local commit. Verify clean worktree and final full SHA. No push, PR, merge or release unless separately authorized.
- [x] **Step 9: Stop and report the native acceptance gate.** Request a fresh exact-final-commit grant including `/context` edit/echo/single Enter, unsubmitted nonce and guarded Ctrl+U, synthetic-key consent, disposable history, chosen debug export, 25/165-second limits and no
  automatic repeat. Do not run it as part of this implementation plan.

## Plan self-review and operator handoff

All spec boundaries map to Task 1 proof/assessment, Task 2 concrete IO/observation or Task 3 isolation/package evidence. Review Focus cases are pinned in their owning tasks; default APIs retain types, private rejection provenance does not grant IO, and named interfaces agree
across tasks. No unrelated browser/provider subsystem is included.

Written-plan approval and execution-method selection are required before Task 1. Native implementation is recommended because tasks share a tightly coupled proof contract; it means the assistant implements here with TDD and one final independent reviewer, not permission to run
the native Claude experiment. Subagent-driven execution remains an alternative with a fresh implementer/reviewer per task and whole-branch review.
