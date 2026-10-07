# P0-04B headless terminal adapter implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair bounded P0-04B context observation without weakening readiness or authorization.
**Architecture:** A passive Node headless engine supplies private cell snapshots to a Python lifecycle adapter. Python owns readiness/auth/context decisions; only explicitly selected P0-04B context probes use the new engine.
**Tech Stack:** Existing POSIX Python/PTY harness, Node, test-only `@xterm/headless` lock, unittest and `node --test`.
**Spec:** `docs/superpowers/specs/2026-10-07-p0-04b-headless-terminal-adapter-design.md`, operator-approved at commit `03a1b4d6e86fe8be3d0dab982742be5a0e82ffac`.

## Global constraints

- Work in the existing clean `p0-04b-browser-automation` worktree; preserve operator changes. No production settings, credentials or provider requests.
- Only `dialogue=context` accepts explicit headless selection; other callers retain legacy defaults. Selected-path failure never falls back.
- Fixed test PTY geometry: 40 rows, 120 columns; headless scrollback: 1000 rows. No absolute context capacity or Claude/Nori/provider/model version pins.
- Existing 8 MiB capture budget; maximum 64 KiB decoded feed, 128 KiB IPC frame, 16 UTF-16 units per returned cell. Overflow fails closed, never clips into readiness.
- IPC timeout is `min(2 seconds, remaining monotonic probe budget)`. Existing 120-second workflow and 1800-second live-run limits are unchanged.
- Test-only dependency lock records `@xterm/headless` 6.0.0 initially. No addons, global install, probe-side npm/download or skillset/staging dependency.
- Provision only into a caller-selected, test-owned external directory using the lock, `--ignore-scripts --no-audit --no-fund` and isolated npm configuration.
- Raw text is permitted only in bounded private memory/pipes and existing approved disposable captures. Never emit/persist raw IPC, stderr, rows, prompts, identifiers, credentials or reply bytes.
- Discard all terminal-generated replies. No automatic retry, protocol forwarding, authenticated attempt, push, PR, merge, release or TODO completion.
- Preserve native command, claim binding/expiry/one-use rules, session routing, six-invocation/40-turn acceptance scope and cleanup-before-aggregate contract.
- Keep the existing 0.15.0 unreleased scope; document this as test-harness work, not a shipped runtime fix or completed acceptance.

## Review focus

1. Split UTF-8/VT sequences and queued writes must not expose an intermediate snapshot as parsed state (Task 1).
2. A timed-out helper, oversized unterminated frame or verbose stderr must not leak content or orphan a process (Task 2).
3. A stale empty history row plus unrelated status redraw must not create input freshness (Task 3).
4. An unsupported/missing module must block before native startup, approval consumption and live credential transport (Task 4).
5. Native version drift or passive device-attributes queries may leave real input unresolved; offline failure must stop without a paid retry (Task 5).

## Task 1: Passive state engine and locked test runtime

**Files:** Create `tests/terminal-state-adapter.mjs`, `tests/terminal-state-adapter.test.mjs`, `tests/terminal-runtime/package.json`, `tests/terminal-runtime/package-lock.json`.
**Interfaces:** Export `createStateEngine(moduleRoot: string): StateEngine`; methods `feed(bytes: Uint8Array): Promise<void>`, `snapshot(): TerminalSnapshot`, `close(): void`.
`TerminalSnapshot` fields: `active` (`normal|alternate`), `cursorX`, `cursorY`, `baseY`, `viewportY`, `rows` (40 arrays of 120 `{text:string,width:0|1|2}` cells), `replyCounts` (closed classes only).
Coordinates are cells, not string offsets; `cursorY` is relative to `baseY`. No normal/inactive-buffer text in snapshots.
**Wire interface:** Canonical LF-delimited JSON requests `{id,op}` or `{id,op,data}` for feed, with increasing positive safe-integer IDs; ops exactly `init|feed|snapshot|close`.
Feed `data` is canonical base64. Replies `{id,ok:true}` optionally include `snapshot`; failures `{id,ok:false,reason}` use a closed enum. No extra stdout/stderr content.
Validate exact fields, unique keys and canonical requests before parsing operations. Native output is data, never executable input.

- [ ] **Step 1: Write failing state/protocol tests** in `tests/terminal-state-adapter.test.mjs`.
  - `alternate_restore`: active alternate/normal transitions preserve the saved normal cursor and cells.
  - `scroll_wrap_widths`: restricted scroll leaves outside rows intact; last-column wrap is delayed; CJK width=2/continuation=0 and combining content use real cells.
  - `split_sequences_and_write_ack`: all split points of UTF-8, CSI and ESC restore produce the same final snapshot as one feed; acknowledgement follows parsing.
  - `protocol_limits`: duplicate/unknown keys, invalid IDs/base64, feed >65536 bytes, frame >131072 bytes, capture >8388608 bytes and cell text >16 UTF-16 units return a closed failure, not truncated state.
  - `passive_replies`: DA/DSR/unknown reply counts are bounded; no reply bytes or other terminal effects escape the private protocol.
  Representative real-engine assertion sequence:
  ```js
  await engine.feed(Buffer.from('MAIN\x1b[?1049hALT'));
  assert.equal(engine.snapshot().active, 'alternate');
  await engine.feed(Buffer.from('\x1b[?1049l'));
  assert.equal(engine.snapshot().active, 'normal');
  assert.equal(engine.snapshot().cursorX, 4);
  ```
- [ ] **Step 2: Run red tests:** `node --test tests/terminal-state-adapter.test.mjs`; require failures for the missing interface, not missing host dependencies.
- [ ] **Step 3: Implement the exported interface and executable protocol** using public headless APIs, awaited write callbacks, fixed geometry/scrollback and logging disabled.
  Load only the explicit module root. No DOM, title/clipboard/window handler, networking or npm. Close is idempotent.
  Record the existing investigated dependency archive/integrity in a private test manifest/lock; use the retained external module for local tests through `P004B_TERMINAL_MODULE_ROOT`.
- [ ] **Step 4: Run green tests** with the real retained package, not a mocked renderer; every fixture must pass and public output must contain no private snapshot text.
- [ ] **Step 5: Commit** only the four Task 1 files: `test: add passive headless terminal state engine`.

## Task 2: Python private IPC and lifecycle boundary

**Files:** Create `tests/terminal_state_adapter.py`, `tests/test-terminal-state-adapter.py`.
**Interfaces:** Frozen `TerminalCell(text:str,width:int)` and `TerminalSnapshot` matching Task 1, represented as bounded tuples.
`TerminalState(node:Path,module_root:Path,deadline:float)` starts/initializes one trusted helper; `feed(data:bytes)->None`, `snapshot()->TerminalSnapshot`, `close()->None`.
`TerminalStateError.reason` is one of `TERMINAL_DEPENDENCY_UNAVAILABLE`, `TERMINAL_PROTOCOL_REJECTED`, `TERMINAL_DEADLINE_EXCEEDED`, `TERMINAL_CLEANUP_FAILED`.
`validate_terminal_runtime(node:Path,module_root:Path)->None` validates canonical paths, regular non-symlink package artifacts and lock-matching metadata without starting Claude or downloading anything.

- [ ] **Step 1: Write failing unittest cases**.
  - `test_round_trip_real_cells`: Task 1 engine yields correct immutable active viewport/cursor, including wide cells and NBSP.
  - `test_schema_rejects_hostile_child`: duplicate fields, unknown fields, nonfinite values, illegal widths/coordinates and wrong reply IDs fail before consuming state.
  - `test_timeout_stderr_and_unterminated_frame`: controllable fake helpers hang, flood stderr or exceed a frame; result is a closed reason, no raw diagnostics and all processes reaped.
  - `test_clean_environment_and_invalid_paths`: helper never inherits keys, `NODE_OPTIONS`/`NODE_PATH` or operator config; invalid/missing/symlinked modules fail before native effects.
  - `test_close_on_every_path`: success, exception, interruption and repeated close release pipes and process ownership; cleanup failure cannot become success.
  Assertions after a real engine wide-cell fixture:
  ```python
  self.assertEqual(snapshot.rows[0][0].width, 2)
  self.assertEqual(snapshot.rows[0][1].width, 0)
  self.assertEqual(snapshot.cursorX, 3)
  self.assertEqual(snapshot.active, "normal")
  ```
- [ ] **Step 2: Run red:** `python3 tests/test-terminal-state-adapter.py`; verify the new interface is missing.
- [ ] **Step 3: Implement the signatures** with clean environment, private pipes, bounded framing/schema, monotonic deadlines and supervised termination/reaping.
  Use selectors/nonblocking I/O so deadlocks and stalled writes share the deadline. Child stderr is bounded and discarded, never forwarded.
- [ ] **Step 4: Run green:** Python suite plus Task 1 suite; assert real process cleanup and no shell execution/fallback.
- [ ] **Step 5: Commit** Task 2 files: `test: add bounded private terminal state transport`.

## Task 3: Cell-based readiness and consistent context observation

**Files:** Create `tests/terminal_input_policy.py`, `tests/test-terminal-input-policy.py`; modify `tests/claude-pty-driver.py`, `tests/test-claude-pty-driver.py`.
**Interfaces:** `TerminalInputPolicy.mark_transition(snapshot:TerminalSnapshot)->None`, `ready(snapshot:TerminalSnapshot)->bool`, `authentication(snapshot:TerminalSnapshot)->str|None`, `screen_text(snapshot:TerminalSnapshot)->str`, `context_percent(snapshot:TerminalSnapshot)->int|None`.
Keep input candidate/cursor/buffer state privately across freshness barriers; a global sequence or unrelated output revision is not freshness proof. `screen_text` normalizes rows with the existing Python `rstrip()` boundary.
Extend the existing `drive(command,capture_path,timeout_seconds,events_path=None,dialogue="manual",filler_path=None,compact_events_path=None,startup_approval=None)` signature with keyword-only `terminal_state:TerminalState|None=None` and unchanged `->int` result.
Legacy behavior remains the default. Headless selection is invalid outside `context`.

- [ ] **Step 1: Write failing policy and selected-driver tests**.
  - `test_current_input_forms`: empty ASCII/NBSP input, controlled `ready` and exact quoted `Try` suggestion pass only with the valid current cell-cursor relation.
  - `test_history_menu_auth_inactive_and_padding`: slash/SDK history, numbered/unnumbered menus, auth/theme/trust headings, off-viewport/inactive state, zero-width padding and ambiguous cursor fail.
  - `test_status_redraw_cannot_refresh_stale_input`: unchanged candidate/cursor/buffer after a barrier remains false despite unrelated output; a new supported input state can become true.
  - `test_settling_revokes_input`: redraw to menu/auth during settling blocks `/context`; fake PTY input ledger proves zero slash commands after rejection.
  - `test_context_exact_numeric_labels`: post-command complete labels parse unique 0..100 percentages; conflicting/partial/history-only values fail.
  - `test_legacy_defaults_unchanged`: existing P0-04A/shared-driver fixtures pass without installing or selecting the engine.
  Stale-input fixture assertions (the second snapshot changes only a status row):
  ```python
  policy.mark_transition(stale_input)
  self.assertFalse(policy.ready(status_redraw))
  self.assertTrue(policy.ready(fresh_supported_input))
  self.assertFalse(policy.ready(menu_after_settle))
  ```
- [ ] **Step 2: Run red:** `python3 tests/test-terminal-input-policy.py` and selected-driver additions in `tests/test-claude-pty-driver.py`.
- [ ] **Step 3: Implement the policy and driver integration**; use only active cell state for every selected auth/approval/menu/readiness/context observation.
  Feed one ordered stream into one persistent adapter. Preserve full state at barriers; do not replay an arbitrary suffix as a fresh blank terminal.
  Recheck readiness after settling and immediately before sending synthetic input. Record numeric context observations while visible; never accumulate raw row history.
  Ensure injected adapter lifecycle is closed on all drive exits, including prelaunch rejection.
- [ ] **Step 4: Run green:** both new suites, `python3 tests/test-claude-pty-driver.py`, `python3 tests/test-browser-startup-approval.py`, and `python3 tests/test-live-context-continuity-safety.py`.
- [ ] **Step 5: Commit** Task 3 files: `test: enforce current-cell readiness for context probes`.

## Task 4: P0-04B wiring, explicit provisioning and failure diagnostics

**Files:** Modify `tests/browser-context-driver.py`, `tests/live-browser-operations-smoke.sh`, `tests/browser_disposable_launcher.py`, `tests/browser_operations_live.py`, `tests/browser_launch_diagnostics.py`, `tests/validate-package.sh`.
Modify their existing scope/safety/diagnostic tests, `tests/test-ci-workflows.py`, `tests/test-nori-staging.py` and `.github/workflows/{ci,release,scheduled-maintenance}.yml`.
Create `tests/provision-terminal-runtime.py`, `tests/test-terminal-runtime-provisioning.py`.
**Interfaces:** CLI driver options exactly `--terminal-engine headless --terminal-node ABS --terminal-module-root ABS` before `--`; the native command after `--` is unchanged.
Caller test configuration: `P004B_TERMINAL_NODE` and `P004B_TERMINAL_MODULE_ROOT`; public credential-free preflight forwards only these extra trusted path fields.
Provisioner CLI: `--target ABS --npm ABS`; only an absent/new test-owned target may be populated. Never overwrite the retained directory or existing operator files.
Provisioner returns a closed status and selected module root; it copies the Task 1 manifest/lock and uses clean npm configs/HOME/cache with disabled scripts. No credentials or global npm configuration.
**Diagnostics:** Add closed failed stages `terminal_preflight`, `terminal_state`, `terminal_cleanup` to existing reducers; map to Task 2 closed reasons without raw fields.

- [ ] **Step 1: Write failing wiring/provisioning tests**.
  - `test_missing_runtime_precedes_claim_and_credentials`: native executable, approval loader and credential consumer call counts remain zero on invalid runtime; claim remains present.
  - `test_one_helper_before_claim`: dedicated startup path initializes its adapter before consuming the claim and passes that same object to drive; resumed/role probes never inherit the one-use approval.
  - `test_no_fallback_or_native_command_drift`: every P0-04B context call selects headless; unknown mode fails; native args/session binding/budgets remain identical.
  - `test_provisioning_is_locked_isolated_external`: exact disabled-script flags and lock use; existing/symlinked/in-checkout targets reject; child env has no npm tokens/operator configs.
  - `test_gate_requires_preprovisioned_runtime`: package tests fail closed if missing; gate itself never installs/downloads. Every CI full-package job has explicit credential-free provisioning first.
  - `test_diagnostics_and_staging`: only closed stages/reasons survive; raw helper stderr/snapshots are suppressed; neither adapters nor npm artifacts enter Nori staging.
  Missing-runtime fixture assertions:
  ```python
  native.assert_not_called()
  approval_loader.assert_not_called()
  credential_consumer.assert_not_called()
  self.assertTrue(claim.exists())
  ```
- [ ] **Step 2: Run red** on the new provisioning suite and affected existing suites before wiring changes.
- [ ] **Step 3: Implement wiring/provisioning** using Task 2 APIs. Initialize adapter before claim consumption; preserve idempotent cleanup if scope validation subsequently fails.
  Add a credential-free runtime capability preflight before the external authorized caller transports any live credential. No public live CLI or new approval grant.
  Add Task 1..3 tests to the package gate. Provision an external runner-temp runtime in all three package-validation workflows and export canonical test paths; do not add unrelated actions/version upgrades.
- [ ] **Step 4: Run green** on the new suite plus `test-browser-context-driver.py`, `test-live-browser-operation-safety.py`, `test-browser-disposable-launcher.py`, `test-browser-launch-diagnostics.py`, `test-ci-workflows.py`, `test-nori-staging.py`.
- [ ] **Step 5: Commit** wiring/provisioning files: `test: wire explicit headless context runtime into acceptance harness`.

## Task 5: Isolated native regression, documentation and final gate

**Files:** Create `tests/offline-terminal-resume-probe.py`, `tests/test-offline-terminal-resume-safety.py`.
Modify `tests/validate-package.sh`, `tests/validation-notes.md`, `tests/browser-launch-diagnostics.md`,
`docs/architecture/ADR-010-browser-automation-boundary.md`, `docs/architecture/README.md`,
`CHANGELOG.md` and `README.md` as needed for accurate harness instructions.
**Interfaces:** Offline-only probe CLI takes canonical source, resolved Claude/Node executable and module-root paths. No live/authenticated mode, real settings loader or credential transport.
`run_offline_controls(*,source:Path,claude:Path,node:Path,module_root:Path)->dict` returns closed booleans/counts/stages plus a regex-validated observed runtime version, only after all private roots are removed.

- [ ] **Step 1: Write failing safety tests**.
  - `test_loopback_namespace_only`: Bubblewrap availability/isolation must be proven before native startup; no `/mnt/c`, host HOME/settings or external route in child.
  - `test_private_cleanup_before_report`: no raw stream/history/screen survives reporting; cleanup failure suppresses a successful aggregate.
  - `test_no_paid_repeat_or_protocol_forwarding`: no provider URL/real credential reader/live mode; one text and one real-Skill control, no retry on failure and no terminal reply forwarded.
  - `test_acceptance_requires_operational_context`: snapshot/SDK exit zero alone fails; both resumed native context inspections and natural exits are required, plus correlated Skill success for the Skill case.
  Successful aggregate assertions for each case:
  ```python
  self.assertEqual(case["beforeExit"], 0)
  self.assertEqual(case["afterExit"], 0)
  self.assertTrue(case["contextInspected"])
  self.assertTrue(case["naturalExit"])
  self.assertTrue(case["caseRootAbsent"])
  ```
- [ ] **Step 2: Run red:** `python3 tests/test-offline-terminal-resume-safety.py`.
- [ ] **Step 3: Implement the offline control** using the established namespace/mock route and Tasks 1..4 adapters.
  Run fixed synthetic text and Skill Messages responses on loopback, maximum four Messages requests per case, bounded 1 MiB bodies, no content/header logging.
  Observe native version without pinning/updating; phases bounded to 25 seconds, total 165 seconds. Synthetic onboarding/key/history stay in owned disposable roots; source/skill/runtime mounts are read-only.
  Report `initial context -> SDK same session -> resumed context -> natural exit -> cleanup` results, not raw prompts/screens or an inferred paid cause.
- [ ] **Step 4: Run safety green and one complete native offline comparison** with the actual observed Claude runtime; no operator configuration or provider credential.
  Stop on inconclusive/failed controls. Do not forward DA replies, widen readiness or substitute a passive snapshot for operational acceptance.
- [ ] **Step 5: Record actual evidence and update architecture/help**. Link spec/plan from ADR-010 and its index; explain local test provisioning, test-only ownership, normalization, rollback and remaining gates.
  Keep CHANGELOG/README wording within unreleased 0.15.0 and only report outcomes actually observed. Leave the definitive unversioned TODO incomplete.
- [ ] **Step 6: Run full gate and final independent review**. Require `package validation passed`, clean content/staging/workflow checks and no unresolved material review finding.
  Review the complete branch, including negative input/IPC/cleanup cases and unchanged authorization boundary. Review never authorizes a paid retry or merge.
- [ ] **Step 7: Commit** completed evidence/documentation: `test: validate isolated headless SDK resume context path`.
  If native acceptance fails, commit truthful evidence only and return the limitation instead of claiming the task complete.

## Verification and handoff

POSIX test commands above run inside the selected WSL Debian runtime. For local full validation use the known Node PATH followed by `bash tests/validate-package.sh`; PowerShell invokes it through `wsl.exe -d Debian --cd <translated-worktree> -- env ...`, never bare bash.
Use the retained canonical module directory and resolved installed Node path for local tests; do not reinstall or search operator caches automatically. CI uses its explicit provisioned paths.

After implementation/offline gates, return exact final commit, test counts,
review limitations, cleanup results and remaining P0-04B gates. A subsequent
authenticated run requires a new final-commit-bound operator grant. CI/Security,
push/PR/merge and TODO completion are separate, not inferred from this plan.

## Execution decision

Plan awaiting operator review and execution-method selection. Recommended:
native implementation in this session with TDD for each task and one final
independent whole-branch review, because the five tasks share ordered state/
lifecycle interfaces and should not be implemented concurrently.
