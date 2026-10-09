# P0-04B Pinned-Input Proof Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove current empty-input ownership after `/context` in an isolated offline TUI without requiring prompt relocation or weakening consent/freshness gates.

**Architecture:** Separate pure structural eligibility from a one-shot edit/echo/clear
protocol. A trusted offline issuer supplies a private instance-bound scope; only exact
echo followed by verified clearing produces a consumable `/exit` proof. Existing
passive/live routes remain unchanged and cannot activate this protocol.

**Tech Stack:** Python standard library, existing passive Python/Node terminal adapter, retained locked `@xterm/headless` test dependency, Debian WSL/Bubblewrap and unittest.

**Spec:** [Approved written specification](../specs/2026-10-09-p0-04b-pinned-input-proof-design.md), approved at commit `b3bf4207d9e115eaa7acee223f5714a3cdf8ae00`.

## Global Constraints

- Implement only after operator review of this plan and execution-method selection. No real Claude/provider/browser execution, installation, push, PR, merge or release is authorized by the plan.
- Reuse `.worktrees/p0-04b-browser-automation`; verify branch/HEAD and preserve the existing uncommitted `tests/validation-notes.md`. Never reset it or include unrelated operator changes in a task commit.
- All new deliverable text is English. Manual file edits use `apply_patch`; commands run through the established authorized host/explicit Debian route where the normal sandbox has setup/access failures.
- Offline only: loopback namespace, hidden operator state, dropped capabilities, disposable HOME/config/project, synthetic-key consent and empty MCP configuration. Human consent remains an external exact-commit execution gate, not an isolation boolean.
- Exactly 16 random ASCII hexadecimal characters; no Enter, CR/LF, paste, speculative Escape, double Escape or interrupt keys. One `Ctrl+U` (`0x15`) is permitted only for the exact owned echo.
- Eligible input is marker plus supported padding only. Visible `Try`/`ready` text, existing draft, history, menus/auth, unknown modal/format, invalid cells or ambiguous cursor block active editing.
- One challenge per context transition; only its own exact echo/clear may create proof. The only challenge-backed submission is the fixed `/exit`, never arbitrary text, another `/context`, `/clear`, tool input or a permission answer.
- Keep 25-second context and 165-second enclosing offline ceilings, two-case maximum, SDK `--max-turns 4`, existing four-message-per-case guard, existing IPC/capture limits and owned cleanup behavior. No deadline reset or operational grace period.
- Keep 16 records / 3 KiB compact JSON per diagnostic phase and 16 KiB outer report. No marker, cells, hashes, draft, identifiers, secret or arbitrary exception text in retained evidence; remove temporary captures/history/roots before reporting.
- Node terminal replies remain discarded. No global preferences, provider endpoints, packaged skills, Nori manifests, runtime/version pins or dependencies change. Preserve unreleased package/component versions for this test-only change.
- No automatic native retry, renderer fallback or promotion of a cleanup failure. Native/provider acceptance, remote CI/Security and definitive TODO completion remain separate pending gates.

## Review Focus

1. `Try` can be an actual draft with the cursor at its start, not a proved ghost hint: Task 1 must reject active edits without breaking passive suggestion support.
2. Echo can be split or followed by a transient auth/menu redraw: Tasks 2/3 must distinguish bounded partial echo from mismatch and latch observed revocation even after the heading disappears.
3. A PTY write can fail after emitting a prefix: Task 3 must stop without a second marker, speculative erasure or `/exit`, and reap the owned family.
4. An identical-looking frame can belong to another instance/transition or replay old output: Task 2 must require branded ownership and post-write PTY generations, not matching JSON or PID alone.
5. A deadline can expire during echo, clear or settling: Tasks 2/3 must fence every next write using the original deadline and leave only bounded cleanup permissible.

## File Map and Execution Setup

Task 1 owns `terminal_input_policy.py` and its pure tests. Task 2 owns the new
`terminal_input_challenge.py`, protocol tests and the read-only original-deadline
view in `terminal_state_adapter.py`. Task 3 integrates the controller/driver,
offline issuer, diagnostics and wiring tests. Task 4 records evidence and updates
ADR/index/README/CHANGELOG. The Node adapter and distributed skill roots stay unchanged.

Use this PowerShell command prefix for every verification below. These are
execution instructions, not commands run while writing the plan:

```powershell
$p004bRoot = 'C:\projects\senior-infra-ops-analyst\senior-infra-ops-analyst\.worktrees\p0-04b-browser-automation'
$p004bWslRoot = '/mnt/c/projects/senior-infra-ops-analyst/senior-infra-ops-analyst/.worktrees/p0-04b-browser-automation'
$p004bWsl = @('-d','Debian','--cd',$p004bWslRoot,'--','env','-i','HOME=/home/marco',
  'PATH=/home/marco/.local/opt/node-v24.17.0-linux-x64/bin:/usr/bin:/bin',
  'PYTHONDONTWRITEBYTECODE=1',
  'P004B_TERMINAL_NODE=/home/marco/.local/opt/node-v24.17.0-linux-x64/bin/node',
  'P004B_TERMINAL_MODULE_ROOT=/mnt/c/projects/senior-infra-ops-analyst/.review-runtime/p004b-terminal-state/node_modules')
$p004bGit = @('-c',"safe.directory=$p004bRoot")
```

Do not use unittest discovery for hyphenated filenames. Run files explicitly.
Existing runtime paths are local verification inputs, not new package pins.
If unavailable, report the dependency/capability limitation; do not install implicitly.

### Task 1: Pure Empty-Input Eligibility

**Files:** Modify `tests/terminal_input_policy.py` (`TerminalInputPolicy`);
test `tests/test-terminal-input-policy.py`.

**Interfaces:** Produce frozen `InputAnchor(buffer: str, row: int, cursorX: int,
baseY: int, viewportY: int, markerX: int)` and
`TerminalInputPolicy.empty_input_anchor(snapshot: TerminalSnapshot) -> InputAnchor | None`.
The method is pure: no `_observe`, freshness mutation, IPC, proof or IO authority.
Existing `ready`, `context_percent` and diagnostic contracts remain unchanged.

- [x] **Step 1 — Write RED eligibility tests.** Reuse the file's existing `snapshot`
  fixture. Pin supported empty/NBSP cells and reject visible draft/suggestion,
  multiple/current-row/cursor errors, invisible padding, selector/auth/modal
  indicators and insufficient space for the marker. Include Review Focus 1.

```python
def test_active_anchor_rejects_suggestion_without_changing_passive_ready(self):
    current = snapshot(['❯ Try "fix tests"'], x=2)
    self.assertIsNone(self.policy.empty_input_anchor(current))
    self.assertTrue(self.policy.ready(current))

def test_active_anchor_does_not_observe_stale_input(self):
    current = snapshot(['❯\u00a0'], x=2)
    self.policy.mark_transition(current)
    self.assertEqual(self.policy.empty_input_anchor(current).row, 0)
    self.assertFalse(self.policy.ready(current))
```

- [x] **Step 2 — Observe RED.** Run `& wsl.exe @p004bWsl python3 tests/test-terminal-input-policy.py`; new assertions fail for absent eligibility while existing tests retain their result. Do not accept a typo/import crash as the RED behavior.
- [x] **Step 3 — Implement the exact pure interface.** Share structural predicates
  with existing policy where useful, keeping its fail-closed readiness order/reasons.
  Require an empty current supported candidate, all auth/menu/ambiguity negatives
  and `cursorX + 16 <= 120`. Do not broaden `_candidate` or treat arbitrary status
  as input freshness.
- [x] **Step 4 — Verify GREEN.** Repeat Step 2; expect `OK`, no failures, all old passive fixtures unchanged. Add explicit empty/draft/history/selector/wide-cell cases that would fail if the new method merely skipped freshness and returned any candidate.
- [x] **Step 5 — Commit this unit only.** Stage its two files with `git @p004bGit add -- ...`, check `git @p004bGit diff --cached --check`, then commit `test: separate empty input eligibility from freshness`.

### Task 2: Private Scope, Echo/Clear Protocol and Consumable Proof

**Files:** Create `tests/terminal_input_challenge.py` and
`tests/test-terminal-input-challenge.py`; modify `tests/terminal_state_adapter.py`
and `tests/test-terminal-state-adapter.py`; register the new suite in `tests/validate-package.sh`.

**Interfaces:** Consume Task 1 and expose `TerminalState.operation_deadline: float`
as a read-only view of its original deadline, without new IPC or timer mutation.
In the challenge module define these interfaces:

- `audit_offline_namespace() -> dict[str, bool]`: actual loopback/hidden-state/capability checks currently owned by `_audit`; return only its existing three booleans or raise a closed rejection. Never read credential/config contents.
- `create_offline_probe_issuer() -> OfflineProbeIssuer`: perform the actual audit internally, not accept caller-supplied booleans/dictionaries. Return a private branded issuer only when the audit succeeds.
- `OfflineProbeIssuer.issue_scope(terminal: TerminalState, run_owner: object) -> OfflineProbeScope`: bind identity and original deadline; refuse repeat issuance for that terminal. Construction/serialization alone cannot forge a valid scope.
- `NonceInputChallenge(scope: OfflineProbeScope, native_owner: object, transition_owner: object, policy: TerminalInputPolicy, initial: TerminalSnapshot, frame: int)`:
  consume the scope once, validate the empty anchor and bind both additional owner
  identities. No IO or automatic timer extension in construction.
- `type_bytes(snapshot: TerminalSnapshot, frame: int) -> bytes`, `observe(snapshot: TerminalSnapshot, frame: int) -> str`, `clear_bytes(snapshot: TerminalSnapshot, frame: int) -> bytes`.
- `ownership_proof() -> InputOwnershipProof`; `consume_exit(proof: InputOwnershipProof, snapshot: TerminalSnapshot, frame: int, native_owner: object, transition_owner: object) -> bool`; `invalidate(reason: str) -> None`.

Use `InputProofError(RuntimeError)` with closed `.reason` and no raw payload.
Its allowlist is `INPUT_PROBE_SCOPE_REJECTED`, `INPUT_PROBE_INELIGIBLE`,
`INPUT_PROBE_ECHO_REJECTED`, `INPUT_PROBE_CLEAR_REJECTED`, `INPUT_PROBE_REVOKED`,
`INPUT_PROBE_DEADLINE`, `INPUT_PROBE_STATE_REJECTED`, `INPUT_PROBE_IO_FAILED`.
Unknown errors map to `INPUT_PROBE_STATE_REJECTED`. Successful phase strings are
`ELIGIBLE`, `ECHO_PENDING`, `ECHO_MATCHED`, `CLEAR_PENDING`, `PROVEN`, `CONSUMED`;
invalidation is terminal `REVOKED`. Invalid/reused proof consumption returns false.
Only the exact issued proof object is consumable, not a reconstructed/copy object.

`frame` counts successfully parsed PTY feeds, not snapshot calls. Each method
samples the internal monotonic clock; callers cannot supply a stale timestamp.
Expose only closed phase/reason state, never marker/owner details in `repr` or diagnostics.

- [x] **Step 1 — Write RED unit/protocol tests.** Add a complete 40x120 cell fixture
  locally in the new test file (including valid reply-count fields). Use real
  policy/snapshots and a narrowly mocked OS-audit boundary only for unit isolation;
  separately require actual namespace verification in Task 3. Assert the state
  machine behavior, not mocks. Include Review Focus 2/4/5.

Test-local `fixture_challenge()` returns the real protocol, two opaque owner
objects and its empty snapshot, using a real passive `TerminalState` and the
real issuer with only actual-OS facts replaced by bounded synthetic facts.
`echo_frame(marker: bytes) -> TerminalSnapshot` places that marker on the same
row 37 and advances the cursor by its byte length. These helpers live in the
test class; neither is an exported production API. All resources are disposed.

```python
# Fixture helpers in this test module build scoped real protocol instances;
# the marker is deterministic only in these synthetic tests.
def test_exact_echo_clear_mints_one_exit_proof(self):
    challenge, owner, transition, empty = self.fixture_challenge()
    marker = challenge.type_bytes(empty, 1)
    self.assertEqual(len(marker), 16)
    self.assertRegex(marker.decode('ascii'), r'^[0-9a-f]{16}$')
    self.assertEqual(challenge.observe(self.echo_frame(marker), 2), 'ECHO_MATCHED')
    self.assertEqual(challenge.clear_bytes(self.echo_frame(marker), 2), b'\x15')
    self.assertEqual(challenge.observe(empty, 3), 'PROVEN')
    proof = challenge.ownership_proof()
    self.assertTrue(challenge.consume_exit(proof, empty, 3, owner, transition))
    self.assertFalse(challenge.consume_exit(proof, empty, 3, owner, transition))
```

- [x] **Step 2 — Observe RED.** Run `& wsl.exe @p004bWsl python3 tests/test-terminal-input-challenge.py` and the new deadline-view test; absent interfaces must fail explicitly, not silently skip or execute Claude.
- [x] **Step 3 — Implement the exact interfaces/state machine.** Generate
  `secrets.token_hex(8)` internally. Require strictly post-write feed generations
  for echo and clear, exact anchored cells/cursor, bounded partial prefix handling
  and current auth/menu checks. Clear only the owned complete marker using one
  `0x15`. Preserve original deadline; wrong type/brand/owner/frame, lost ownership
  or observed forbidden transition becomes terminal failure. Proof construction/
  consumption is sealed and single-use; erase the marker reference after completion/
  revocation. Do not set passive freshness merely because the protocol exists.
- [x] **Step 4 — Verify protocol GREEN and transport regressions.** Run Step 2 plus
  `python3 tests/test-terminal-state-adapter.py` and
  `python3 tests/test-terminal-input-policy.py` through the prefix. Pin literal
  rejection outcomes for missing/extra/wrong-row/inactive-buffer echo, old-frame
  clear, dictionary forgery, replay, substituted instance/transition, invalid
  deadline and expiry at each phase. An auth/menu frame followed by a valid-looking
  frame must remain revoked. Assert public error/repr/report outputs contain no
  marker or raw cells.
- [x] **Step 5 — Commit this unit only.** Stage the module, its tests, adapter/tests and suite registration; cached whitespace check; commit `test: add isolated one-shot input ownership protocol`.

### Task 3: Offline Controller Integration and Content-Free Diagnostics

**Files:** Modify `tests/headless_context_driver.py`, `tests/claude-pty-driver.py`,
`tests/offline-terminal-resume-probe.py`, `tests/terminal_structural_diagnostics.py`,
`tests/test-headless-context-driver.py`, `tests/test-offline-terminal-resume-safety.py`,
`tests/test-terminal-structural-diagnostics.py` and `tests/test-terminal-wiring.py`.
`tests/browser-context-driver.py` keeps no activation option; its existing tests
must prove that live startup cannot receive a scope from CLI/environment input.

**Interfaces:** Consume Task 2. Add keyword-only `input_probe_scope: OfflineProbeScope | None = None`
to shared `drive` and selected `drive_context` forwarding. Non-headless/non-context
requests with a scope reject before native startup. `_audit()` delegates to the
shared actual namespace audit; each offline context phase issues a fresh scope
from an audited issuer with a private `run_owner = object()`. No new CLI flag,
environment switch or paid-wrapper activation is added.

- [x] **Step 1 — Write RED real-component integration tests.** Extend the current
  Python fake UI to keep input at alternate row 37, render numeric context above
  it, echo typed marker at that same input, clear on `0x15`, and exit naturally
  only on `/exit\r`. Use real PTY/helper/policy/protocol; monkeypatch only the
  issuer's OS-audit boundary for this fake-UI test. Launch the fake with a clean
  explicit environment, no provider/key/config variables and no actual Claude
  path. Add the ledger assertions below and negative variants for Review Focus 2/3/5.

```python
# Inspect the owned ledger only inside its disposable synthetic fixture.
self.assertEqual(ledger[0], b'/context\r')
self.assertRegex(ledger[1], rb'^[0-9a-f]{16}$')
self.assertEqual(ledger[2:], [b'\x15', b'/exit\r'])
self.assertEqual(result, 0)
self.assertNotIn(b'\x1b', b''.join(ledger))
```

- [x] **Step 2 — Observe RED.** Run `python3 tests/test-headless-context-driver.py` through the prefix; the pinned-input success must fail with the old behavior. Negative tests must distinguish zero edits from a partially written marker; no fake ledger is retained outside its temporary root.
- [x] **Step 3 — Implement the selected active controller.** Count `frame` after
  each successful feed/snapshot; feed every subsequent frame to the current
  challenge so transient auth/menu invalidation latches. Create
  `transition_owner = object()` at the owned `/context` transition. Require
  completed/revoked startup consent and fresh valid numeric context before
  constructing the challenge. The active branch never uses blind Escape or fallback.
- [x] **Step 4 — Fence concrete writes.** Drain pending output, check cancellation/
  deadline and phase-specific predicates before marker and clear. Handle partial
  PTY writes against the same deadline; if any prefix was sent before IO failure,
  invalidate and terminate without another edit. Do not use an unbounded write
  loop for challenge-backed `/exit`; recheck the original deadline immediately
  before each remaining write. Keep passive callers' existing IO behavior unchanged.
- [x] **Step 5 — Integrate proof-backed `/exit` only.** Preserve settle intervals,
  drain and current-state checks. The private proof can override only the missing-
  freshness branch for that fixed command, after successful clear; all other
  predicates must still pass. Invalidate on new owner/transition, auth/menu,
  malformed state, cancellation, timeout or child exit. Failure must retain
  result 2 and failed proof events, not become successful exit evidence.
- [x] **Step 6 — Wire offline scope and bounded diagnostics.** Mount the new
  challenge module in the existing namespace list. Create the issuer after actual
  `_audit` success; mint each phase's scope with its own original `TerminalState`
  deadline. Recheck isolation at issuance; preserve `_audit`'s existing ValueError/
  closed blocked outcome on rejection. Preserve acceptance, prompts, limits,
  counts and stop-on-first-inconclusive. Add closed points `input_probe_started`,
  `input_probe_echo`, `input_probe_cleared` and Task 2's closed error codes; map
  typed errors explicitly in the driver, never arbitrary exception text. No raw
  marker/echo, IDs or new acceptance fields; keep all diagnostic bounds/fault isolation.
- [x] **Step 7 — Verify GREEN and hostile cases.** Run the four touched test files
  explicitly (`test-headless-context-driver.py`, `test-offline-terminal-resume-safety.py`,
  `test-terminal-structural-diagnostics.py`, `test-terminal-wiring.py`) plus Task 2's
  suite. Assert no edit before scope/startup/numeric/empty gates; no clear after
  wrong echo/auth; no Enter before proven clear; zero repeated marker/clear after
  failure; no `/exit` after expired settle, transient auth or partial write failure.
  Test forged dictionaries/environment activation rejection before startup. Test
  four maximal phase reports still fit 16 KiB and cannot be parsed as PTY proof events.
- [x] **Step 8 — Verify the actual namespace seam without Claude.** Run
  `python3 tests/test-offline-terminal-resume-safety.py` through the prefix,
  extending its audit-only Bubblewrap fixture to exercise the real issuer with a
  private test-owned terminal owner, no Claude binary mount and no credentials/
  config access. Assert the factory rejects a host/non-isolated namespace and
  actual valid isolation issues one non-serializable scope. An unavailable
  namespace is a skip/blocked capability, not native acceptance.
- [x] **Step 9 — Commit this integrated unit only.** Stage its explicit implementation/tests, cached whitespace check, commit `test: wire pinned input proof into offline context controls`. Keep the pre-existing notes edit out of this commit.

### Task 4: Final Verification, Architecture Record and Authorization Handoff

**Files:** Modify `docs/architecture/ADR-010-browser-automation-boundary.md`,
`docs/architecture/README.md`, `README.md`, `CHANGELOG.md`, `tests/validation-notes.md`
and this plan's completion checkboxes. No metadata/version change is needed
unless an actual packaging change is discovered and separately justified.

**Interfaces:** Consume Task 3's frozen candidate and existing package/architecture
validators; produce factual evidence, rollback guidance and exact final commit.
No execution grant is produced by documentation or tests.

- [x] **Step 1 — Record the new enforced boundary.** Update indexed ADR-010 with
  active offline selection, eligibility versus proof, one-shot bindings, no Enter,
  guarded clear, residual shortcut risk, failure/cleanup and rollback. Link spec/
  plan from the existing ADR index. Add a concise README reference and unreleased
  CHANGELOG entry without claiming native/provider acceptance. Preserve the entire
  prior notes edit while adding actual RED/GREEN and final evidence.
- [x] **Step 2 — Run focused verification on frozen code.** Run policy, protocol,
  transport, selected driver, offline safety, wiring, structural diagnostics,
  cancellation and signal suites explicitly through the prefix. Expect `OK`, zero
  failures; record named skips/limitations and mutation-sensitive negatives. Do
  not run `--run-offline`, installed Claude `--version`, smoke `--run-live` or provider requests.
- [x] **Step 3 — Run the complete package gate.** Run
  `& wsl.exe @p004bWsl bash tests/validate-package.sh`; expect exit 0 and
  `package validation passed`, including schema/local workflow validation and
  staging contracts. Preserve bounded progress updates; use a test-owned log if
  output is large. Self-tests/fakes are not native acceptance. WSL PowerShell/
  optional skips remain explicit.
- [x] **Step 4 — Obtain the method-selected independent review.** Provide spec,
  plan, immutable candidate range/patch and actual results. Review must be read-only,
  not invoke Claude/provider, and explicitly state declined-to-judge boundaries.
  Fix reportable findings with RED/GREEN, then rerun relevant suites and the complete
  package gate on unchanged final code; a pre-fix gate is not final verification.
- [x] **Step 5 — Validate documentation and commit.** Run
  `python3 tests/validate-content.py` and `python3 tests/test-architecture-docs.py`
  through the prefix, plus `git @p004bGit diff --check`. Review the notes diff for
  overlap before staging only this task's owned files; commit
  `docs: record isolated input proof validation and residual gates`. Confirm final
  HEAD and status, identifying any preserved unrelated edits.
- [x] **Step 6 — Stop at the execution gate.** Report implementation/review/package
  evidence and propose a new exact-final-commit offline grant explicitly covering
  one unsubmitted marker/clear per context phase, synthetic-key consent, disposable
  history/raw cleanup, structural-only retention, two cases, 165 seconds and no retry.
  Wait for that grant; neither plan approval nor old grants authorize the experiment.

## Plan Self-Review and Handoff

Coverage: eligibility/privacy/unknown states are Tasks 1/2; ownership/frame/deadline
and revocation are Task 2; real IO, isolation, consent, default routing, bounded
diagnostics and disposal are Task 3; existing package/staging/ADR/version/evidence
and review/authorization gates are Task 4. The five Review Focus cases are pinned
to their owning test steps. All task interfaces use the same names and types;
the plan leaves native acceptance and future authenticated activation unclaimed.

Status: operator-approved Native execution completed; source and corrected package gates passed. Native experiment authorization remains pending.
Method selected: Native inline implementation with one fresh final reviewer.
The single Important/P2 was corrected with three RED/GREEN regressions and a
fresh complete package run. No second review or native/provider experiment was
performed. Preserve this branch/worktree until the independent native and
remote delivery gates are explicitly satisfied.
