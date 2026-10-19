# P0-04B Correlated Context Display Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans for
> the recommended inline execution. Use superpowers:subagent-driven-development
> only if the operator explicitly selects delegation and resolves its additional
> review seats against the approved single-reviewer budget. Steps use checkbox
> (`- [ ]`) syntax for tracking.

**Goal:** Accept an audited offline resumed context display with equal numeric values only when the exact current command has a private HISTORY_COMMIT_V1 witness, while preserving independent nonce ownership and all operational limits.

**Architecture:** Share a pure canonical numeric parser without changing legacy
policy behavior. Keep the owned resumed-display coordinator and sealed witness
beside the existing command/history capability in `terminal_context_echo.py`;
both the primary binding and composed assessment use it. The driver and case
reducer separately require numeric observation, correlated display and
nonce/clear/exit evidence.

**Tech Stack:** Existing Python standard library, unittest, private Python capabilities, POSIX PTY/Bubblewrap and the existing locked xterm test helper. No new dependency, public flag or installed runtime requirement.

**Spec:** [Approved evidence specification](../specs/2026-10-19-p0-04b-correlated-context-display-design.md), approved by the operator after source `aee14a68bd420d59249639dae7e6be20aa5146f7`.

**Status:** Proposed implementation plan awaiting operator review and execution confirmation. No implementation or native execution is authorized by this document alone.

## Global Constraints

- The recommended profile certifies CORRELATED_DISPLAY, not NATIVE_RECOMPUTED.
- Apply the new profile only to the audited offline resumed dialogue with a valid private resumed-history view and completed fixed synthetic SDK witness.
- Initial dialogues, default policy callers, production/live/provider routes and browser operations retain their current contracts.
- No new public activation flag, operator setting, environment override, MCP grant or credential transport.
- Missing, ambiguous or conflicting evidence stays inconclusive; there is no fallback from failed resumed correlation to signature inequality or cursor-only eligibility.
- Candidate observations do not authorize input.
- No parser-observer production change is required by HISTORY_COMMIT_V1.
- Keep 25 seconds per context dialogue, 165 seconds overall, at most two cases, the existing SDK limits, stop-first-inconclusive, original cancellation/deadline and identity-checked cleanup.
- No extra Enter, Escape, Tab, clearing key or retry.
- Keep 16 diagnostic records and 3072 bytes per phase, and 16384 bytes for the complete outer report including final newline/disposal evidence.
- Root/component versions remain unchanged for the proposed test-only scope.
- No installed Claude, provider/browser activity or operator-state/credential access during synthetic implementation tests. The a7f5307 native grant is consumed.
- One independent read-only final review, author-owned TDD and immutable complete package gate; no push/PR/merge/release, staging refresh or definitive TODO completion in this plan.

## Review Focus

The five easy-to-miss cases below receive explicit tests in the owning tasks:

1. Decimal spelling and rounded used percentages: compare canonical free/buffer values, preserve existing parser decisions and rounding; Task 1 numeric tests.
2. New pure parser absent from the isolated mount: audit and synthetic workflow must import the exact read-only source without widening access; Task 1 namespace regression.
3. A candidate disappears during the final drain or writable wait: revoke before any nonce/remaining input and never rebind after restoration; Tasks 2 and 3.
4. Foreign or replayed capabilities and boolean frame counters: valid-looking data cannot mint authority or cross a command/run; Task 2 capability tests.
5. Four full phase reports including the new checkpoint: retain final disposal/newline within 16384 bytes, or fail closed without changing limits; Task 3 aggregation tests.

## File ownership and interfaces

- Pure numeric data: create `tests/terminal_context_sample.py` and
  `tests/test-terminal-context-sample.py`; modify `tests/terminal_input_policy.py`.
  One validation grammar, canonical numbers and snapshot geometry; data only.
- Owned resumed display: modify `tests/terminal_context_echo.py`; create
  `tests/test-terminal-context-display.py` and `tests/context_display_fixtures.py`.
  Exact invocation lifecycle, one coordinator, private witness and receipt continuity.
- Driver/report wiring: modify `tests/headless_context_driver.py`,
  `tests/terminal_context_diagnostics.py`, `tests/terminal_structural_diagnostics.py`
  and `tests/offline-terminal-resume-probe.py`. Await/consume display proof,
  frozen diagnostics, required aggregation checkpoint and read-only module mount.
- Regression/gate wiring: modify `tests/test-terminal-input-policy.py`,
  `tests/test-terminal-resume-history.py`, `tests/test-headless-context-driver.py`,
  `tests/test-terminal-context-diagnostics.py`, `tests/test-terminal-structural-diagnostics.py`,
  `tests/test-offline-terminal-resume-safety.py`, `tests/resume_history_fixtures.py`
  and `tests/validate-package.sh`. Unit/PTY/namespace/privacy/budget coverage and
  explicit full-gate discovery.
- Documentation: modify ADR-010, architecture index, CHANGELOG and
  `tests/validation-notes.md`. Distinguish implemented/reviewed/gated/native
  evidence and document narrow supersession.

Do not restructure unrelated history/cancellation code. `terminal_input_challenge.py`
should continue using its existing receipt-aware assessments; do not add a direct
display-to-InputOwnershipProof route. An unexpected need to broaden production,
history retirement, consent or retention is a scope/design escalation, not a fix.

## Execution routes and baseline

Workspace is the existing linked worktree
`C:\projects\senior-infra-ops-analyst\senior-infra-ops-analyst\.worktrees\p0-04b-browser-automation`.
Detect Git dir/common dir, branch and superproject again; reuse this isolation.
Use Windows Git with command-local `safe.directory`, not WSL Git or global trust.
Preserve operator edits; stop for overlapping unowned changes. No new worktree
or dependency installation is necessary unless the detected environment differs.

All `Run:` Python commands below execute from the source root in Debian WSL with
the clean environment below. These are synthetic tests, not the native harness
`--run-offline` command with installed Claude. Verify the paths exist rather than
pinning a Claude/provider/model version. Do not substitute a bare Windows bash.

```powershell
$taskWslArgs = @(
  '-d', 'Debian', '--cd',
  '/mnt/c/projects/senior-infra-ops-analyst/senior-infra-ops-analyst/.worktrees/p0-04b-browser-automation',
  '--', 'env', '-i', 'HOME=/tmp',
  'PATH=/home/marco/.local/opt/node-v24.17.0-linux-x64/bin:/usr/bin:/bin',
  'PYTHONNOUSERSITE=1', 'PYTHONDONTWRITEBYTECODE=1',
  'P004B_TERMINAL_NODE=/home/marco/.local/opt/node-v24.17.0-linux-x64/bin/node',
  'P004B_TERMINAL_MODULE_ROOT=/mnt/c/projects/senior-infra-ops-analyst/.review-runtime/p004b-terminal-state/node_modules'
)
# Append the exact Python/test arguments from each Run step:
wsl.exe @taskWslArgs python3 tests/test-terminal-context-sample.py
```

Use the authorized bounded WSL route if the restricted host returns E_ACCESSDENIED.
At execution start, record exact clean HEAD and compare runtime code with the
previous gated source `8f83c289e08fb854488da8abe4c94b9cb8436bc1`; subsequent source
through approved design contains documentation only. Run baseline echo,
resumed-history, diagnostics and offline-safety suites before editing behavior.
Unexpected failure is investigated, not called a flake or silently rerun green.

## Task 1: Pure canonical numeric observation with legacy compatibility

**Files:** Pure numeric unit and parser tests above; `tests/offline-terminal-resume-probe.py:268` read-only mount list, its safety test, and `tests/validate-package.sh:13` test discovery.

**Interfaces:**

- `ContextNumbers` is frozen data: `free: Decimal`, `buffer: Decimal | None`, `used: int`. It is not a capability and its public construction never establishes authority.
- `ContextSample` is frozen data: `numbers: ContextNumbers`, `geometry: tuple[str, int, int, tuple[int, ...]]`. Geometry is active buffer, baseY, viewportY and metric-row positions, not current input text or cursorX.
- `parse_context_values(text: str, allow_rendered_row_order: bool = False) -> ContextNumbers | None` owns the existing parser's extraction/validation grammar.
- `parse_context_percent(text: str, allow_rendered_row_order: bool = False) -> int | None` remains importable from `terminal_input_policy` and returns the same legacy result.
- `sample_context(snapshot: TerminalSnapshot) -> ContextSample | None` reads current cells with rendered-row-order support and no policy observation, IPC, IO or clock query.

- [ ] **1.1 Write `test_decimal_identity_and_legacy_rounding` and `test_sample_is_pure_and_not_authority`.** Use hand-derived assertions, including:

```python
a = parse_context_values("Context Usage\nFree space: 81%\nAutocompact buffer: 3%", True)
b = parse_context_values("Context Usage\nFree space: 81.0%\nAutocompact buffer: 3.00%", True)
assert (a.free, a.buffer, a.used) == (Decimal('81'), Decimal('3'), 16)
assert a == b
c = parse_context_values("Context Usage\nFree space: 80%\nAutocompact buffer: 4%", True)
assert c.used == 16 and c != a
```

Also test conflicting duplicate values, missing buffer numbers when its label is
present, percentages outside 0..100, permitted missing buffer, non-rendered row
order behavior and geometry movement. Verify representative Decimal/rounding
boundaries against literal results characterized on the baseline, not a second
implementation of production logic. Canonical identity uses Decimal values;
legacy used-percent calculation preserves the existing float-and-round result.
Characterized baseline assertions for free 81.5, 80.5 and 81.5001 with buffer 3
are used percentages 16, 16 and 15, respectively; pin these literal results.

- [ ] **1.2 Run:** `python3 tests/test-terminal-context-sample.py`. Expect the new API/behavior to be absent before implementation, not a fixture/syntax error. Run `python3 tests/test-terminal-input-policy.py` as baseline compatibility control.
- [ ] **1.3 Implement the pure module and legacy re-export.** Move the existing parser grammar into the new module rather than adding a competing parser. Do not change sticky policy freshness or default validation behavior. Derive canonical numbers from the same validated matches.
- [ ] **1.4 Add `test_numeric_module_is_read_only_mounted_and_importable`.**
  Exercise the actual namespace audit and existing Python fake workflow; assert
  unchanged audit facts, one owned launch, disposal and exact `--ro-bind`
  source/destination. No host operator mount and no installed Claude. Add the
  module to the mount list and the new test script to the package gate.
- [ ] **1.5 Run:** sample, input-policy and offline-terminal-resume-safety suites. Expect exit 0 with exact counts/skip reasons recorded. Commit only this tested deliverable: `test: share pure context number observations`.

## Task 2: One owned resumed-display coordinator and sealed witness

**Files:** Owned resumed-display unit above; `tests/test-terminal-resume-history.py:297` integration and `tests/test-terminal-context-echo.py` legacy controls.

**Interfaces:**

- `ContextDisplayWitness(_Sealed)` and private weak registry live in `terminal_context_echo.py`. No public constructor, serialized representation, arbitrary row-index parameter or transferable permission token.
- `_observe_resumed_display(command: OwnedContextCommand, snapshot: TerminalSnapshot, frame: int) -> None` updates pre-Enter inventory/latest barrier or post-Enter numeric conflict tracking after original live/phase checks.
- `_assess_resumed_context(command: OwnedContextCommand, snapshot: TerminalSnapshot, frame: int) -> tuple[EmptyInputAssessment, int | None, ContextRejectionObservation | None] | None` is the sole candidate evaluator; None means not yet proven while awaiting display, never permission to proceed.
- `OwnedContextCommand.context_display_percent(self, snapshot: TerminalSnapshot, frame: int) -> int | None` exposes only candidate readiness/current used percentage to the resumed driver, never the witness. Non-resumed commands reject this call without changing their legacy route.
- `_validate_resumed_display(command: OwnedContextCommand, snapshot: TerminalSnapshot, frame: int) -> None` validates the consumed witness/sample during existing receipt/nonce/exit assessments; invalidity revokes with the existing InputProofError mechanism.
- Keep `bind_history(snapshot, frame)` and the existing four-part receipt registry tuple compatible. Store witness association under the original command, not as caller-supplied receipt metadata.

`context_display_fixtures.py` provides test-only `DisplayCase` wrapping real
`CaseFixture.complete_initial()`, validated fixed SDK sample, fresh terminal and
resumed view. `submit()` models 8+1 concrete acknowledgements without claiming
native IO; `observe(rows, frame)` passes prescribed cell fixtures through the
real command observer. Expose `command`, `view`, `journal`, `bindings` and original
owners for negative controls. No product methods added solely for tests.

- [ ] **2.1 Write `test_equal_values_need_new_owned_commit` and `test_text_change_without_commit_is_not_evidence`.** Start with baseline 81/3, retained SDK history and a submitted owned command. Use separate fresh cases:

```python
assert command.context_display_percent(old_grid_without_new_history, 3) is None
assert command.context_display_percent(same_numbers_with_new_history_at_20, 4) == 16
receipt = command.bind_history(same_numbers_with_new_history_at_20, 4)
assert receipt is not None and command.phase == 'RECEIPT_READY'
assert resume_view_decision(view) == 'VALID'
```

Heading changes, numeric row reorder or cursor noise without the new commit must
not create a witness. A complete legitimate changed-value display must also use
the new witness; never fall back to inequality when correlation fails.

- [ ] **2.2 Write `test_conflicting_sample_cannot_restore_baseline` and
  `test_candidate_loss_is_irreversible`.** Observe 80/3 after Enter and then return
  to 81/3 with a new row: reject and revoke view/command. Baseline repeats before
  a legitimate 80/3 commit are not themselves conflicts. After a candidate,
  disappearance/movement/duplication or sample change must revoke; restoration
  cannot rebind.
- [ ] **2.3 Write `test_witness_cannot_cross_command_or_be_forged`.** Assert public
  construction, dictionary/copy/replayed attachment, foreign
  scope/controller/native/helper/run, expired/backwards deadline and bool/stale
  frame are rejected. Pre-existing/pinned/retired/menu-bound/current-input rows
  cannot become the new row. A witness does not construct InputOwnershipProof
  or waive nonce eligibility.
- [ ] **2.4 Run:** `python3 tests/test-terminal-context-display.py`. Record expected RED for each new behavior before implementation; negative controls already green remain documented controls.
- [ ] **2.5 Implement the coordinator in the existing capability module.** Bind
  tracker state at the original resumed command, refresh pre-Enter
  inventory/baseline during guarded observations, arm AWAIT_DISPLAY only after
  actual Enter acknowledgement, and issue CANDIDATE only after current sample +
  exactly one new row + one ordered composed input assessment. Pending absence
  returns None; conflicts revoke. Candidate consumes once inside bind_history.
  The primary binding and CONTEXT_PENDING composer branch delegate to this
  coordinator; no recursion through the composer back into itself and no
  duplicate ordered assessment of one decision. Canonical number values, not
  heading/order or pre-candidate metric-row movement, seed the numeric conflict
  guard. Candidate geometry is pinned when the witness is issued. All existing
  invalidation/cleanup paths revoke and release the associated witness as well
  as the command/view.
- [ ] **2.6 Revalidate through `validate_context_history`.** Preserve old-history
  exclusions/retirement and the existing nonce/exit normalization. Numeric
  geometry excludes controlled input cursor/text changes; numeric/history/owner
  changes do not become permitted normalization. Keep initial/default behavior
  and readable legacy diagnostics unchanged. Old resumed zero-history acceptance
  fixtures must become explicit unsupported/pending controls with separate valid
  new-history positives; never remove a regression merely to make the suite green.
- [ ] **2.7 Run:** display, context-echo, resumed-history and input-challenge
  suites. Add the display test script to `validate-package.sh` and verify
  per-decision assessment count with the existing real evaluator plus a justified
  counting spy. Commit: `test: bind resumed context displays to owned history commits`.

## Task 3: Driver, closed diagnostics and isolated aggregation

**Files:** Driver/report wiring and related tests in the ownership map; `tests/resume_history_fixtures.py` for controlled Python CLI profiles.

**Interfaces:**

- Resumed driver polls `context_command.context_display_percent(snapshot, frame)` and consumes via existing bind_history after the final drain. Initial/default waits keep `policy.context_percent(snapshot)`.
- The observer point `context_display` uses CHECKPOINT with `structural=False`; no new raw payload. `context_numeric` remains observation, not final acceptance. Resumed passed `context_inspected` follows successful binding/current numeric validation.
- Add closed checks `DISPLAY_WITNESS_UNPROVEN`, `DISPLAY_WITNESS_AMBIGUOUS`, `CONTEXT_SAMPLE_UNSTABLE`; use existing operational error reasons and four diagnostic keys. Retain old checks for older records/non-profile callers.
- `case_complete(case: dict) -> bool` additionally requires exactly one ordered `context_display` checkpoint in the after phase, before nonce start. Before-phase proof remains unchanged. Diagnostics alone still cannot turn a failed child/workflow into success.

Direct bind while still awaiting evidence rejects with DISPLAY_WITNESS_UNPROVEN.
Readiness may return None until the original deadline; do not freeze a terminal
failure merely because the next frame has not arrived. Deadline, cancellation
and lifetime failures retain their existing precedence/reason rather than being
rewritten as missing display evidence.

- [ ] **3.1 Add controlled Python PTY profiles and real assertion tests.** Extend
  the existing fixture utility to render a baseline grid during resumed startup,
  exact command echo, one Enter, then equal or changed numbers with one new
  current history row. Include completion-only, no-history and conflicting-sample
  profiles. Assert actual writes:

```python
assert sent[:9] == b'/context\r'
if success:
    assert len(sent[9:25]) == 16 and all(c in b'0123456789abcdef' for c in sent[9:25])
    assert sent[25:] == b'\x15/exit\r'
else:
    assert sent == b'/context\r'  # unproved display: no nonce or retry
```

Use read/write barriers instead of sleep-based success assumptions. Numeric-only
observations must not emit passed context_inspected. Verify current command/view
is revoked after failed profiles and all owned processes/descriptors are closed.

- [ ] **3.2 Add `test_candidate_loss_on_drain_revokes_before_nonce`.** Inject loss
  at the actual final drain/writable boundary, then restore. Assert no nonce or
  remaining input, original reason/frozen first failure and unconditional cleanup.
  Cover cancellation, owner/helper loss, late authentication/modal and optional
  collector failure without changing authority. Equivalent valid numeric byte
  chunkings produce the same interpretation; intermediate history-loss profiles
  remain rejected rather than coalesced into success.
- [ ] **3.3 Add reducer/collector regressions.** Missing, duplicate or late
  context_display, numeric-only evidence, forged new fields/labels, bool counters,
  nonzero child claiming success and resumed-vs-before checkpoint confusion must
  reject. Four maximal phase reports with the new point must remain within
  3072 bytes per phase and 16384 including disposal/newline; no limit increase
  or raw content. Required witness producer loss blocks even when the optional
  diagnostic collector is unavailable. Optional collector loss does not change
  the driver's owned input decisions; the outer reducer may still withhold
  success when required serialized proof is unavailable. Never manufacture a
  checkpoint to reconcile those distinct outcomes.
- [ ] **3.4 Run:** headless-context-driver, terminal-context-diagnostics, terminal-structural-diagnostics and offline-terminal-resume-safety tests; record expected RED before implementing the driver/collector/reducer change.
- [ ] **3.5 Implement the interfaces above and integrate them atomically.** Keep
  final drain/revalidation before binding and nonce typing, retain old failure
  provenance through the actual rejection, and keep no-signature-fallback on the
  resumed route. The context_display checkpoint must reflect an actual consumed
  private witness, not merely the presence of a row in JSON.
- [ ] **3.6 Run those complete suites plus terminal-wiring and context-debug.**
  The actual isolated Python fake text-turn/skill-turn workflow must complete,
  and fail-closed peers must stop without retry with disposal proved. No installed
  Claude or real provider. Commit:
  `test: require correlated display evidence in resumed offline workflows`.

## Task 4: Documentation, independent review and immutable package gate

**Files:** ADR-010, architecture index, CHANGELOG, validation notes, approved spec/plan status and any author-owned fixes required by actual findings.

**Interfaces:** Exact source range starts at the approved plan commit, ends at
the frozen implementation candidate. Review is read-only; no reviewer subagents,
source mutation or native/provider execution. Gate consumes a Windows Git archive
of the exact corrected commit in a native Linux export, not DrvFs permission bits.

- [ ] **4.1 Update English documentation to describe actual local behavior.**
  Narrowly supersede the resumed different-signature rule with HISTORY_COMMIT_V1;
  retain non-profile controls. Record CORRELATED_DISPLAY rather than
  NATIVE_RECOMPUTED, cached-output limitation, unsupported zero-history/partial-layout
  cases, original bounds and consumed grant. Root/component versions unchanged;
  README changes only if its public summary would otherwise be false. Do not mark
  native/browser/provider/remote acceptance or TODO complete.
- [ ] **4.2 Run all affected suites and document exact RED/GREEN, counts, skips
  and provenance.** Run `python3 tests/validate-content.py`,
  `python3 tests/test-architecture-docs.py`, `python3 tests/test-release-history.py`
  and `git diff --check`. Commit the tested candidate and verify clean exact HEAD.
- [ ] **4.3 Request one independent final reviewer.** Use requesting-code-review
  with a clean fork and exact immutable base..head, approved spec/plan, explicit
  invariants and synthetic-only commands. Require Critical/Important/Minor
  findings and a Declined-to-judge list. Reviewer checks all changed runtime roots
  and task interfaces, not only textual plan compliance. Author rules on
  exclusions. Do not call source review native acceptance or merge authority.
- [ ] **4.4 Fix valid findings with author-owned RED/GREEN tests.** No fresh review
  seat by default. If scope expands or an important requirement cannot be
  satisfied, stop and obtain the needed decision. Freeze corrected source for
  its gate; do not replace a failed gate by unexplained reruns.
- [ ] **4.5 Run the complete immutable package gate.** Use Windows `git archive`
  for the exact source SHA; record archive SHA256. Extract with original modes
  into a bounded native Linux temporary directory, verify every versioned
  path/type/mode/hash before and after, and execute `bash tests/validate-package.sh`
  in the clean WSL environment. The existing external
  `p004b-offline-failure-diagnostics-gate.sh` and `p004b-verify-git-export.py` provide
  the established route; read/validate their exact inputs before reuse. Do not
  assert that runtime-created non-source files make the entire directory
  unchanged. Do not hardcode the old 539 source-member count after adding files.
- [ ] **4.6 Inspect the entire verdict and exclusions.** Expect exit 0 and
  `package validation passed`; record actual source hash/count, UTC times and log
  location. Existing opt-in real-browser/platform/Git-Bash/PowerShell omissions
  must be named when observed, not converted to passed native tests. Local
  schema/workflow checks are not remote CI/Security.
- [ ] **4.7 Record gate/review results in a docs-only closeout.** Fresh
  content/architecture/release-history checks, local commit, clean final worktree.
  Preserve earlier failed/inconclusive evidence and consumed markers. Report local
  implementation complete only if all required local work passed.
- [ ] **4.8 Stop for the next authorization boundary.** Native support remains
  unproven. Propose, but do not execute, one new exact-final-commit offline attempt
  with the original up-to-two-case/25-second/165-second scope, loopback isolation,
  no real provider/operator state/debug content/retry and cleanup before
  aggregation. Provider/browser acceptance and external delivery need their own
  remaining gates and authority.

## Coverage and handoff

Task 1 covers pure data/precision/geometry and namespace import; Task 2 covers
profile/state/private authority and both guard sites; Task 3 covers concrete IO,
observation ordering, aggregation/privacy/bounds; Task 4 covers documentation,
review, immutable complete verification, rollback/evidence and next authorization.
All five Review Focus entries have owning tests above. No native receipt hook,
parser renderer profile or internal recomputation claim is left for an implementer
to invent. Unknown native compatibility remains an explicit later gate.

Recommended execution: the current author implements these tightly coupled
interfaces inline with TDD, then one fresh independent reviewer examines the
whole range. This matches the approved single-reviewer specification and avoids
independent implementers changing shared command/composer state concurrently.
The operator must review this plan and confirm execution before Task 1 begins.
