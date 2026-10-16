# P0-04B Correlated Command-Menu Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Admit at most one privately correlated offline pre-Enter command-menu row without weakening owned-input or later proof requirements.

**Architecture:** A pure cell-layout predicate remains separate from authority.
The existing private command record binds the baseline and one pre-Enter menu
observation; only that command can supply one exclusion to the shared ordered
assessment. Submission retires the observation, and all later proofs stay strict.

**Tech Stack:** Existing Python unittest/mock, controlled Python PTY peers,
passive Node/xterm adapter and Debian WSL; no new runtime or dependency.

**Spec:** [Approved correlated command-menu specification](../specs/2026-10-15-p0-04b-correlated-command-menu-design.md).

## Global Constraints

- Written spec and plan operator-approved; inline execution completed. All three tasks verified; 281 covering tests passed and candidate fb60e0d passed the immutable full gate and scoped independent review. Later result-only closeout is separate; no native run authorized.
- Planning baseline: `f2195cad1606aa3a21a5c13aed987fc115f38263`. Reuse the linked `p0-04b-browser-automation` worktree, preserve operator edits and use command-local Windows Git safe.directory; no WSL Git.
- Record exact HEAD after this plan is approved as the execution baseline; use that complete range for scoped review, with the approved plan/spec supplied separately. Never substitute main or HEAD~1.
- Audited offline scope only: isolated loopback network, hidden operator state, dropped capabilities, synthetic-only authentication and disposable HOME/config/project/history.
- Fixed `/context` only: eight acknowledged command bytes, full exact cursor-bound echo, newer frame, original geometry and zero Enter bytes before correlation. Partial echo gets no exception.
- One off-cursor selected row only: validated 120 cells, width one, ASCII display padding, one existing marker, exact token, at least two separating ASCII spaces and a nonempty printable description; no control/format characters or extra marker.
- Wording, absolute coordinates, runtime version, static offsets and color are not authority or recognition pins. Unsupported cells/layouts and ambiguous rows remain blocked.
- Strict default/live APIs and every other row remain checked. No public row-exclusion capability, new flag, environment activation, dependency, mount, Nori/staging or installed behavior change.
- Bind actual command/terminal/native/scope/run/transition/baseline/deadline/frame. No copied or serialized evidence can mint, replace or transfer the binding.
- Menu loss/change/movement/duplication/conflict revokes before Enter; restoration cannot recover. Retire at actual one-byte Enter acknowledgement. No menu exception in history, nonce, clear, proof or `/exit`.
- Preserve one Enter, latest concrete pre-Enter freshness barrier and fresh numeric proof afterward. Completion-only behavior yields inconclusive; no second Enter, Escape, Tab or alternate key.
- Keep 25 seconds per context dialogue, 165 seconds total, at most two cases, existing SDK/request ceilings and first-inconclusive stop; no retry, grace period or runtime/provider pin.
- Keep 16 records/3072 actual JSON bytes per structural phase and 16384 bytes per complete intermediate/final report. No description/cell/snapshot/hash/session-ID logging.
- Preserve old/debug-context-edit eligibility, first-failure provenance, memory-only IPC and disposal/lifetime-before-export. Do not persist or replay the chat-only native excerpt; new fixtures use synthetic descriptions.
- The e76cf95 native grant is consumed. No real Claude/provider/browser execution, operator credential/configuration read, push, PR, merge, release or definitive TODO completion is authorized here.
- Documentation is English. Root/component versions remain unchanged for test-only scope. Native acceptance, later `/exit` compatibility and external CI/Security are not established by synthetic tests.

## Review Focus

1. A matching completion from an earlier/resumed baseline must not become owned merely because the current command matches; Task 2 pins baseline/binding substitution and reuse.
2. One valid menu plus another unsupported marker must reject the actual other row, never export the excluded menu as the failure; Task 2 pins one assessment and debug provenance.
3. A menu can disappear during a writable wait and return before Enter; Task 2 pins every-frame irreversible revocation and zero late writes.
4. A description or pre-Enter grid can look numeric; Task 2 pins the latest actual submission barrier and requires a genuinely newer numeric observation.
5. Enter can complete without executing, or the menu can survive into nonce/exit; Task 2 pins one Enter, bounded inconclusive behavior and no transferred exclusion.

---

## Files and verification route

Task 1 modifies only `tests/terminal_input_policy.py` and its existing unit suite.
Task 2 modifies `tests/terminal_context_echo.py`, one private signature projection
in `tests/terminal_input_policy.py`, and existing echo, selected-driver,
debug, offline-safety and wiring suites as required by changed fixture expectations.
Driver/challenge/launcher production logic is not expected to need modification;
any necessary adjustment must preserve their existing signatures and all authority
boundaries, not create another route. No new module/mount is required.
Task 3 owns ADR-010/index, CHANGELOG, validation notes and spec/plan status.

Run explicit scripts, not unittest discovery. The common prefix from this worktree is:

```powershell
wsl.exe -d Debian `
  --cd /mnt/c/projects/senior-infra-ops-analyst/senior-infra-ops-analyst/.worktrees/p0-04b-browser-automation `
  -- env -i HOME=/tmp `
  PATH=/home/marco/.local/opt/node-v24.17.0-linux-x64/bin:/usr/bin:/bin `
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 `
  P004B_TERMINAL_NODE=/home/marco/.local/opt/node-v24.17.0-linux-x64/bin/node `
  P004B_TERMINAL_MODULE_ROOT=/mnt/c/projects/senior-infra-ops-analyst/.review-runtime/p004b-terminal-state/node_modules `
  python3 tests/test-terminal-input-policy.py
```

These are test-runtime locations, not product pins; verify they still exist.
Every `python3 tests/...` command below uses this exact clean prefix, changing
only the final script/arguments. Full-gate command replaces Python with
`bash tests/validate-package.sh`. Expected: exit 0 and `package validation passed`.
Read every result, warning and skip. RED must expose the named missing behavior,
not an import/dependency error. GREEN requires unittest OK/exit 0 without warnings.

### Task 1: Pure bounded completion-row classification

**Files:** Modify `tests/terminal_input_policy.py`; test `tests/test-terminal-input-policy.py`.

**Interfaces:**
- Produce `TerminalInputPolicy._context_completion_row(row: tuple[TerminalCell, ...]) -> bool` as a private static pure predicate.
- Import TerminalCell from the existing adapter if required. No caller invokes this predicate from default assessment yet; classification never supplies an exclusion or mutates policy freshness.
- Require exactly 120 TerminalCell entries of width one. Interpret empty width-one display cells as spaces, as the existing row renderer does; fixed marker/token characters must occupy their individual cells.
- Match leading ASCII padding, `❯`, one or more display spaces, exact `/context`, two or more display spaces, then a nonempty printable description and trailing display padding.
- Reject another marker, control/format characters, tab/NBSP/other unsupported whitespace, malformed entries, wide/continuation cells, token suffixes and a single-space continuation. Description wording may vary; no English literal.

- [x] Add `test_context_completion_row_grammar` with table fixtures generated by the existing snapshot builder: leading
  padding 0/2, separator 2/7, synthetic Latin/printable width-one Unicode descriptions and empty-cell padding pass. Bare
  token, `/contextX`, `/exit`, empty description, one-space continuation and extra marker fail.

  Core assertions:
  `self.assertTrue(self.policy._context_completion_row(snapshot(['❯ /context  Synthetic A']).rows[0]))`;
  `self.assertFalse(self.policy._context_completion_row(snapshot(['❯ /context Synthetic A']).rows[0]))`.
- [x] Add `test_context_completion_row_cells_and_purity`: lengths 119/121, non-tuple/malformed cells, width 0/2,
  compressed multi-letter token cell, invisible/control/unsupported-space fixtures fail without printing their payload.
  Ordinary combining text in a valid description remains data. Spy on `_observe`/IO; zero calls and unchanged policy
  diagnostics.
- [x] Add `test_completion_shape_alone_keeps_strict_assessment`: a valid off-cursor shape plus one empty cursor row still yields UNSUPPORTED_ROW through the unchanged default API. No receipt, readiness or numeric proof follows from True.
- [x] Run `python3 tests/test-terminal-input-policy.py`. Expected RED: missing private predicate; the strict characterization already passes.
- [x] Implement the exact private predicate, with bounded cell-position/token checks before description classification. Do not change `_candidate_evaluation`, `_empty_input_assessment`, `_readiness` or context parsing.
- [x] Run `python3 tests/test-terminal-input-policy.py`, `python3 tests/test-terminal-input-challenge.py` and `python3 tests/test-terminal-context-echo.py`. Expected GREEN/exit 0, original rejection order unchanged, no warnings.
- [x] Commit explicit Task 1 files: `test: classify bounded context completion rows`.

### Task 2: Command-bound exception and complete controlled-peer coverage

**Files:** Modify `tests/terminal_context_echo.py` and the private signature projection in `tests/terminal_input_policy.py`; tests in `test-terminal-context-echo.py`, `test-headless-context-driver.py`, and affected debug/offline/wiring suites.

**Interfaces:**
- Consume Task 1's pure predicate. Keep `begin_context_command`, OwnedContextCommand methods and all driver/challenge/launcher public signatures unchanged.
- Add private command-record `_menu_origin` and `_menu_selection` fields. Origin is an immutable tuple of weak owner reference, original baseline, scope, state, native, transition, run, deadline, original anchor and baseline frame; selection starts None.
- Add private weak-key `_MENU_BINDINGS`, keyed by the existing OwnedContextCommand, storing the same immutable `(origin,
  selection)` references. It checks original evidence identity, not phases or permissions; the existing command record
  remains the only state machine. Origin/selection copies or substitutions fail by identity.
- Produce `_correlated_menu_row(record: dict, snapshot: TerminalSnapshot) -> int | None`. Validate the owner weak reference resolves to the actual `_COMMANDS` record and origin bindings remain identical; current frame comes from existing `_live` validation, never serialized metadata.
- Only EDIT_PENDING/COMMAND_ECHO_MATCHED/SUBMIT_PENDING with written=count=8, zero acknowledged Enter and frame newer than write/baseline may first correlate. Before that, ordinary strict assessment applies; no partial-echo rescue.
- A sole new matching off-cursor row binds `(index, original_row_tuple, first_snapshot, first_frame)` in
  `_menu_selection`. Validate unchanged row/index/buffer/viewport and current owned-input anchor on every later
  pre-Enter call. Genuine newer captures revalidate; they cannot replace the original bound baseline/evidence.
- Return the validated index, or None when no menu has ever been correlated. Missing/invalid origin or loss of an
  existing selection on an actual command irreversibly fails INPUT_PROBE_REVOKED/NORMALIZED_ELIGIBILITY before
  assessment, with no fabricated normalized sibling. A foreign/copied record raises INPUT_PROBE_SCOPE_REJECTED without
  touching the real owner's state or journal.
- In `_prefix`, retain all existing geometry/prefix/command/trailing-cell checks first. Resolve the private menu
  exclusion, then invoke the existing ordered assessment once with it on the same normalized current input row. Preserve
  the actual resulting rejected index for optional observations; no reclassification/retry.
- Use the existing `policy._empty_input_assessment(normalized, excluded_row=index)` for a validated exclusion. Keep the
  ordinary no-exclusion wrapper path compatible; count the underlying evaluator, not only its public wrapper. Validate
  record row identity against the origin baseline's anchored row before excluding anything.
- Produce `_release_command_menu(record: dict) -> None`: remove the actual owner's `_MENU_BINDINGS` entry and raw
  baseline/selection fields, without affecting journal/debug evidence or another owner's binding. Resolve ownership by
  `_COMMANDS` record identity, including malformed-origin cleanup. Call after existing first-failure freezing in
  `_fail`, on invalidate, on propagated scope/lifetime/cancellation loss and after successful actual Enter
  acknowledgement. No subsequent phase may remint the fields.
- Keep history/nonce/clear/proof/exit strict. No new receipt type, public exclusion argument, diagnostic schema or input key; existing phase guards prevent post-Enter use.
- Extract the existing signature comprehension unchanged into a private static helper
  `TerminalInputPolicy._context_signature_rows(rows:
  tuple[tuple[TerminalCell, ...], ...]) -> tuple[str, ...]`; `_context_signature(snapshot)` delegates with all rows,
  preserving its signature/default result and parsing/freshness behavior.
- Produce `_preenter_context_signature(record: dict, snapshot: TerminalSnapshot) -> tuple[str, ...]`, called only
  immediately after `_prefix` succeeds on that same snapshot. Project signature rows without the validated current menu,
  otherwise with every row. It is pure metadata projection, not input exclusion or numeric acceptance.
- Use that projection for `submit_signature` in both `submit_bytes` and every SUBMIT_PENDING observation. Preserve raw
  `policy.mark_transition(snapshot)` and actual frame barrier. Menu disappearance alone must not make an unchanged
  pre-Enter grid appear new. Post-Enter assessments still use actual snapshots and no menu exception; history/numeric
  gates remain required.

- [x] Add `test_correlated_completion_full_echo_above_below` using existing `frame`, `begin`, `diagnostic_edit` helpers.
  Distinct row positions/descriptions pass only under the actual owned command with all eight cells echoed; assert
  COMMAND_ECHO_MATCHED, one ordered assessment with exactly that exclusion, unchanged source snapshot and one `b'\r'`
  from submit. Default policy still rejects the same row.

  Core assertions using the existing fixture:

  ```python
  command, journal, bindings = self.diagnostic_edit()
  current = frame('❯\u00a0/context', 10, history=((8, '❯ /context  Synthetic A'),))
  self.assertEqual(command.observe(current, 2), 'COMMAND_ECHO_MATCHED')
  self.assertEqual(command.submit_bytes(current, 2), b'\r')
  self.assertIsNone(self.policy.empty_input_anchor(current))
  ```
- [x] Add `test_correlated_completion_origin_and_baseline` covering pre-existing/resume marker, wrong/missing scope or
  origin, copied record, swapped terminal/native/run/transition/deadline/anchor, equal replacement baseline/selection
  and foreign dialogue. Assert terminal rejection/no Enter, no receipt/proof creation and no copied diagnostic
  capability; a copied-record attempt must not revoke the real owner.
- [x] Add `test_correlated_completion_partial_or_wrong_echo` for 0/4/7 acknowledged or echoed bytes, wrong prefix/trailing argument, cursor/buffer/viewport mismatch and wrong target. Assert original guard order, no exception from a shape match and no extra write.
- [x] Add `test_correlated_completion_loss_is_irreversible`: after a valid selection, remove/change/move/duplicate it,
  inject auth/selection conflict or expire/cancel/lose the native; restore the original frame and attempt submit. Both
  attempts remain rejected; no fresh binding or fallback and original deadline unchanged.
- [x] Add `test_correlated_completion_other_rejection_provenance`: one valid excluded menu and a second invalid marker
  produce one actual ordered rejection for the other index. With debug on/off, base/detail/first failure are identical;
  projection exports only the actual rejecting row or omission, never the menu. Observer/collector loss cannot alter
  authority, error or cleanup.
- [x] Add `test_correlated_completion_retired_after_enter`: actual one-byte acknowledgement clears menu-origin/selection
  content. A persistent or restored menu fails history binding, nonce/clear/proof and exit checks; no exclusion is
  inferred from it or a prior transition. Invalidate/failure also release the bindings. Healthy no-menu and existing
  history receipt flows still pass.
- [x] Adjust existing negative fixtures that would now be valid. Keep `normalized-suggestion-*` and `edit-suggestion-*`
  rejection-purpose cases deliberately unsupported (single-space separator with a synthetic description), preserving
  their phase/check/8/0/detail and old debug tests. Update
  `test_normalized_suggestion_detail_uses_actual_single_assessment` accordingly. Do not delete assertions or disable the
  new recognizer in those fixtures.
- [x] Extend existing `run_pinned_probe(mode=..., edit_debug=False)` without changing its public signature. Add
  `completion-above`, `completion-below`, `completion-accept-only`, `completion-loss-restore`,
  `completion-pre-enter-grid`, `completion-post-enter-new-grid`, `completion-persists-after-enter` and `completion-exit-menu` modes with synthetic
  descriptions only.
- [x] Add `test_correlated_completion_selected_driver_success` and `test_correlated_completion_only_accepts_once`. Use
  the existing read-select/menu-request barriers for full-echo arrival; no sleep-based race assumption. Successful peers
  clear the menu only after reading the one Enter, then emit a fresh numeric grid. Assert exact input `b'/context\r' +
  16 hex bytes + b'\x15/exit\r'`, NO_CAPTURE and unchanged natural-exit events. The accept-only peer consumes one Enter,
  emits no numeric grid and yields bounded inconclusive with exactly `b'/context\r'`, no nonce or extra key.
- [x] Add `test_correlated_completion_writable_loss_and_restore`: place loss and restoration behind the existing
  writable-wait barrier. Assert every consumed frame revokes and peer input stops before Enter.
- [x] Add `test_correlated_completion_pre_enter_numeric_not_proof`: a numeric-looking menu description or grid before
  concrete Enter cannot satisfy the post-Enter barrier. In the negative peer, remove only the menu and retain the
  identical old grid; reject with one Enter. In the positive peer, emit a changed numeric grid after Enter and require
  proof before nonce. Assert signature projection is pure, default signature output unchanged, and the latest concrete
  pre-Enter frame/barrier retained.
- [x] Add `test_correlated_completion_no_post_enter_or_exit_transfer`: persistent menu after Enter and a later `/exit` completion remain rejected under the original phase/proof rules. Assert no second submission or extra exit bytes after loss. Do not extend menu classification to those phases.
- [x] Update `run_pinned_probe` success/early-prefix expectations and existing normalized/edit diagnostic expectations
  for the new/retargeted modes. Preserve PTY FD/capture closure, both leader reap, revoked command/probe,
  first-inconclusive stop and no content in structural output. Add clear assertions for completion-only/post-Enter
  failures rather than the helper's former unconditional nonce expectation.
- [x] Run `python3 tests/test-terminal-context-echo.py`, `python3 tests/test-headless-context-driver.py`,
  `python3 tests/test-offline-terminal-resume-safety.py`, `python3 tests/test-terminal-context-debug.py` and
  `python3 tests/test-terminal-wiring.py` to meaningful RED before implementation. Expected: new
  valid-menu tests reject at NORMALIZED_ELIGIBILITY; lifecycle tests expose absent origin/selection handling. Pure
  malformed/default negative cases remain strict. Keep peer fixtures deterministic so RED is not a timeout caused by a
  missing barrier.
- [x] Implement only the private record/helper integration above. First-failure evidence freezes before release;
  lifecycle loss may reject before the ordered assessor (zero calls), while every decision reaching that assessor calls
  it exactly once. Finish the new peer behavior/expectations, not by adding a second Enter or relaxing production code.
- [x] Run the complete covering set: `test-terminal-input-policy.py`, `test-terminal-input-challenge.py`,
  `test-terminal-context-echo.py`, `test-terminal-context-diagnostics.py`, `test-terminal-structural-diagnostics.py`,
  `test-terminal-context-debug.py`, `test-headless-context-driver.py`, `test-offline-terminal-resume-safety.py`,
  `test-terminal-wiring.py`, `test-terminal-cancellation.py`, `test-headless-driver-signals.py`, each with `python3
  tests/` and the clean prefix. Expected GREEN/exit 0 without warnings, leaked children/descriptors, changed default
  output or broadened raw retention. Record observed counts/timings, not predicted totals.
- [x] Commit only Task 2's required source/test changes: `test: correlate owned pre-enter command completions`.

### Task 3: Indexed decisions, immutable gates and bounded handoff

**Files:** ADR-010, architecture README, CHANGELOG, validation notes and spec/plan statuses.

**Interfaces:** Documentation records implemented controls and actual evidence, not new authority.

- [x] Update ADR-010/index with exact offline/pre-Enter correlation, pure grammar versus independent ownership, irreversible lifetime, alternatives, residual layout/Enter/exit risks and rollback. No universal renderer compatibility or same-process sandbox claim.
- [x] Update unreleased CHANGELOG and validation notes with actual RED/GREEN and byte/provenance/cleanup results. Preserve the consumed e76cf95 attempt as inconclusive; do not copy its chat excerpt. Keep package/component versions unchanged and mark only observed local implementation status.
- [x] Run `python3 tests/validate-content.py` and `python3 tests/test-architecture-docs.py` through the clean prefix;
  run command-local Windows Git `diff --check`. Expected: content validation passed, unittest OK, no whitespace errors,
  source/package boundary unchanged. Verify no implementation delta in installed policy, manifests, staging or runtime
  mounts.
- [x] Commit explicit documentation, verify tracked tree clean and capture the immutable candidate hash.
- [x] Run the full `bash tests/validate-package.sh` via the clean prefix on that candidate. Expected: exit 0 and
  `package validation passed`. Retain a unique test-owned external log, exact source hash and every platform/capability
  skip. Confirm HEAD/tracked tree unchanged through completion. Local workflow checks are not remote CI/Security.
- [x] Obtain scoped independent review from the recorded plan-approved execution baseline through that candidate and
  inspect unchanged interacting callers. Supply this approved spec/plan, Review Focus and actual TDD evidence. This
  verdict covers the complete new refinement, not all inherited branch history; author full-gate evidence remains
  separate.
- [x] Re-grade/resolve review findings under the chosen execution method. Any source correction requires author RED→GREEN, covering suites and a new immutable full gate. Review does not authorize native execution; preserve all execution rulings and deferred findings with residual costs.
- [x] Close result-only documentation separately, distinguishing reviewed/gated source from later HEAD. Verify a documentation-only delta and rerun content/architecture checks; complete the task ledger under the chosen workflow. Do not rerun native acceptance as a verification shortcut.
- [x] Hand off commits, clean/dirty state, test/review/skips, remaining native/Enter/exit/provider/browser/remote gates and the consumed grant. Preserve branch/worktree. No push, PR, merge, release or definitive TODO completion; another native attempt needs fresh final-commit authorization.

## Self-review and execution handoff

Coverage: Task 1 fixes only bounded pure classification. Task 2 owns every new
authority/lifetime interaction and the impacted old diagnostic fixtures together,
so its deliverable can pass the existing selected-driver suite independently.
Task 3 records architecture and immutable evidence without claiming acceptance.
All five Review Focus cases have named Task 2 tests. Helper/record names are
defined once above; no later task relies on an unspecified public capability.

The selected grammar is deliberately narrower than a general menu parser. A
shape match cannot exempt a row without the original owned command; default/live
and all post-Enter phases still reject. Ordinary newer snapshots revalidate
unchanged evidence but cannot remint a lost binding. No raw native excerpt is
used as a fixture or persisted in a planning artifact.

The operator selected inline execution with one final fresh independent reviewer.
Tasks 1–3 are complete locally; exact immutable gate/review evidence, skips and all rulings are recorded in tests/validation-notes.md.
There are three deliverables,
and the command-state/driver tests form one tightly coupled authority boundary.
The plan makes that boundary explicit while TDD and the immutable full gate cover
it. Approval of this plan/method does not authorize a native attempt.
