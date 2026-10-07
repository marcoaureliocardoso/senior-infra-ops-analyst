# P0-04B Harness Review Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the two test-only material review findings without claiming native acceptance.
**Architecture:** Separate input-candidate freshness from unrelated cursor visits. One scoped cancellation token owns selected signal handling, IPC/PTY checkpoints and disposal of the exact child family.
**Tech Stack:** Existing POSIX Python/PTY, passive Node terminal helper, unittest; no new dependency.
**Spec:** `docs/superpowers/specs/2026-10-07-p0-04b-review-remediation-design.md`, written specification approved at commit `1084a400efd67d2b9208708270c61692cc5a594e`.

## Global Constraints

- Use the existing `p0-04b-browser-automation` isolated worktree; preserve operator changes. Baseline `1084a400efd67d2b9208708270c61692cc5a594e`.
- No provider request, actual operator credential/configuration access, native Claude repetition, production UI operation, installation, push, PR, merge, release or definitive TODO completion is authorized.
- Unsupported or ambiguous states continue to block. Do not broaden chevron/Unicode matching or forward terminal-generated replies.
- Other shared-driver dialogues retain their default routing/behavior. Preserve startup claim one-use/revocation and private root disposal.
- The first signal requests cancellation; subsequent managed signals cannot interrupt the bounded cleanup of the same owned family.
- Do not promise cleanup after SIGKILL, host failure or an unresponsive interpreter that cannot reach a checkpoint.
- Preserve existing 40x120 cells, 1000-row scrollback, 8 MiB capture, 64 KiB feed, 128 KiB IPC frame, two-second IPC ceiling and caller monotonic deadline.
- Retained dependencies remain externally owned. No implicit module discovery, download or reinstall.
- This is the author fix pass following the existing independent review, not a new native experiment. Production expiry is the separate companion plan linked below.

## Review Focus

1. An unrelated split redraw through a marker-looking status/menu row must not refresh historical input (Task 1).
2. Cancellation between child creation and handle publication must not lose process ownership (Task 2).
3. A second signal while the helper/native group is being reaped must not interrupt cleanup (Task 2).
4. Cancellation before the startup claim is consumed must not create a native/key decision (Task 2).
5. Directory absence or a helper leader's exit must not substitute for proof that owned descendants stopped (Tasks 2 and 3).

## Task 1: Input-candidate freshness regression

**Files:** Modify `tests/terminal_input_policy.py`; test `tests/test-terminal-input-policy.py` and `tests/test-headless-context-driver.py`.
**Interfaces:** Keep `TerminalInputPolicy.mark_transition(snapshot)->None`, `ready(snapshot)->bool`, `authentication(snapshot)->str|None` and `context_percent(snapshot)->int|None` unchanged. Consumers still receive immutable `TerminalSnapshot` cells.

- [ ] **Step 1: Write the failing split-redraw tests.** Add `test_split_status_cursor_visit_cannot_refresh_stale_input`, using the existing `snapshot` fixture:

```python
old = snapshot(['status', '❯ '], x=2, y=1)
policy.mark_transition(old)
assert policy.ready(snapshot(['new status', '❯ '], x=10, y=0)) is False
assert policy.ready(snapshot(['new status', '❯ '], x=2, y=1)) is False
```

Also test repeated status visits, a controlled marker-looking menu row and return to the identical old candidate. Assert `False` after every final restoration; do not compute expectations from policy helpers.
- [ ] **Step 2: Run RED.** Run `python3 tests/test-terminal-input-policy.py`. Expected: the new final-restoration assertion fails with `True`; existing legitimate controls remain green.
- [ ] **Step 3: Correct candidate observation.** In `_observe(snapshot)->None`, distinguish relevant input/controlled command-echo changes from transient visits to unrelated rows. Keep the barrier's evidence until a supported input transition occurs; no global redraw
  sequence latch. Preserve startup from an empty state and legitimate controlled echo-to-empty transitions.
- [ ] **Step 4: Add the driver-boundary assertion.** Extend the controlled PTY fixture so only status/cursor redraw follows a transition. Assert result `2`, no further slash input in the fixture-owned input ledger and owned helper closure. Run it RED against the uncorrected
  freshness condition by a temporary narrow mutation, then restore the fix.
- [ ] **Step 5: Run GREEN and regression.** Run `python3 tests/test-terminal-input-policy.py` and `python3 tests/test-headless-context-driver.py`. Expected: all new negatives and existing supported NBSP/current-input/natural-exit controls pass. Run the complete package
  command below; expected exit `0` and `package validation passed`.
- [ ] **Step 6: Commit** only this task's source/tests: `fix: reject stale input after split status redraws`.

## Task 2: Scoped cancellation and exact child ownership

**Files:** Create `tests/terminal_cancellation.py`, `tests/test-terminal-cancellation.py`, `tests/test-headless-driver-signals.py`.
Modify `tests/terminal_state_adapter.py`, `tests/headless_context_driver.py`, `tests/claude-pty-driver.py`, `tests/browser-context-driver.py`, `tests/offline-terminal-resume-probe.py`, `tests/validate-package.sh`.
Modify `tests/terminal-runtime-preflight.py` as another CLI owner that starts the selected helper before native startup.
Extend `tests/test-terminal-state-adapter.py`, `tests/test-terminal-wiring.py`, `tests/test-offline-terminal-resume-safety.py` as needed for their direct boundaries.

**Interfaces:** Produce `TerminalCancelled(RuntimeError)` with fixed non-content message and the `TerminalCancellation` context manager:
`requested:bool`, `check()->None`, `publish_child(process)->None`, `cleanup()` context manager.
The managed handler records cancellation only; `check` raises at owned safe checkpoints. Publish exact owned children immediately after creation, before the next check.
Inside `cleanup`, checks do not unwind disposal. Context exit verifies owned-family termination and restores previous handlers; unavailable ownership proof cannot report success.
Extend `TerminalState(node,module_root,deadline,*,cancellation:TerminalCancellation|None=None)` compatibly and expose `check_cancelled()->None`. Existing callers without a token remain valid provider-free unit callers; selected CLI owners supply it before construction.
Extend `prepare_approval(claim,commit,nonce,source_root,command,*,cancellation=None)` compatibly, checking after source reads and immediately before the one-use claim is consumed.

- [ ] **Step 1: Write token tests.** Assert SIGTERM/SIGHUP request cancellation without an asynchronous exception during handle publication; the next `check` raises `TerminalCancelled`. Assert handler restoration on success/exception, repeated signals during `cleanup`, and a
  non-main-thread/unsupported-platform scope rejecting before any child effect.
- [ ] **Step 2: Run RED.** Run `python3 tests/test-terminal-cancellation.py`. Expected: missing cancellation interface; no native executable is used.
- [ ] **Step 3: Implement the scoped token.** Use supported Python signal APIs only, with first-request state and explicit safe checkpoints. No lock or process cleanup inside the signal handler. Install before any selected helper/native creation; leave other dialogue routes
  unchanged.
- [ ] **Step 4: Write real synthetic CLI signal tests.** Spawn the selected public CLI and a test wrapper around the dedicated entrypoint with a fixture-only approval preparer. Use an actual terminal helper and a Python fake UI that creates an owned TERM-ignoring descendant.
  Parameterize SIGTERM/SIGHUP, startup/IPC/PTY wait and repeated-signal cleanup. Assert nonzero dialogue exit, no successful acceptance event, and no live owned helper/native/descendant process. Test fixtures always kill/reap their own RED leaks in `finally`.
  Include a descendant with its own new session; group-leader termination alone must not pass. Cancel during the preparer's synthetic source read and assert the real fixture claim remains unconsumed.
- [ ] **Step 5: Run RED before wiring.** Run `python3 tests/test-headless-driver-signals.py`. Expected: at least the detached native group remains alive under the old signal route. Use only controlled PID/group handles, never a global process scan or kill pattern.
- [ ] **Step 6: Wire ownership and checkpoints.** Pass the token into selected `TerminalState` construction. Publish process handles before checking cancellation; check bounded IPC/PTY loops and before claim preparation/input. Always enter cancellation-resistant cleanup and
  terminate/reap exact owned groups, even after leader exit. Revocation/consumption never becomes renewable consent. Reuse current fixed failure messages/stages; no signal payload or raw screen diagnostics.
  Recheck immediately before claim consumption after any source-read waits. Use established bounded supervision/observation primitives for descendants creating other groups; retain exact process identity, never signal an unrelated actor, and fail closed without ownership proof.
  Apply the same selected-helper ownership to the credential-free terminal preflight CLI; a cancelled preflight must not leave its helper alive or report readiness.
- [ ] **Step 7: Cover the offline launcher without Claude.** Replace its blocking parent wait with a cancellable owned-child wait preserving the 165-second ceiling and 16 KiB private report bound. Mount the new helper read-only in the existing namespace allowlist. Synthetic
  namespace-child signal tests must prove child termination and root absence before a closed failure report; `_controls` is never invoked by these tests. Preserve `--die-with-parent`, no-egress audit and no retry.
- [ ] **Step 8: Run GREEN.** Run the new cancellation/signals suites and existing terminal-state, selected-driver, terminal-wiring, browser-startup-approval, browser-context-driver and offline-safety suites by explicit filenames. Expected: zero failures, no real native
  invocation, and unchanged one-use/legacy controls. Add the two new suites to `validate-package.sh`; run the complete package command, expected exit `0` and `package validation passed`.
- [ ] **Step 9: Commit:** `fix: clean selected terminal process families on cancellation`.

## Task 3: Document the author fix pass and reconcile gates

**Files:** Modify `tests/validation-notes.md`, `tests/browser-launch-diagnostics.md`, `CHANGELOG.md`, `docs/architecture/ADR-010-browser-automation-boundary.md`, `docs/architecture/README.md`.
**Interfaces:** Consume Task 1/2 behavior and verified results only; preserve root `0.15.0` unreleased and current closed acceptance schema.

- [ ] **Step 1: Record exact RED-to-GREEN evidence**, signal families/checkpoints, real fixture process cleanup and actual skips. Mark only the two harness review findings addressed, not native SDK/resume acceptance or the companion production finding.
- [ ] **Step 2: Update help/ADR links and CHANGELOG** with the enforced selected-path behavior and explicit SIGKILL/in-flight-runtime limits. Keep historical observations intact; do not overwrite operator preference guidance or fabricate a cause for the stopped native control.
- [ ] **Step 3: Run final verification.** Run the complete package command and `git diff --check`. Expected: exit `0`, `package validation passed` and no whitespace errors. On Windows, AST-only syntax validation may supplement the WSL PowerShell skip without executing
  scripts or changing ExecutionPolicy.
- [ ] **Step 4: Commit:** `docs: record terminal review fixes and remaining acceptance gates`.

## Verification route and handoff

Run all POSIX commands above through Debian WSL with explicit retained runtime paths:

```powershell
wsl.exe -d Debian `
  --cd /mnt/c/projects/senior-infra-ops-analyst/senior-infra-ops-analyst/.worktrees/p0-04b-browser-automation `
  -- env -i HOME=/home/marco `
  PATH=/home/marco/.local/opt/node-v24.17.0-linux-x64/bin:/usr/bin:/bin `
  PYTHONDONTWRITEBYTECODE=1 `
  P004B_TERMINAL_NODE=/home/marco/.local/opt/node-v24.17.0-linux-x64/bin/node `
  P004B_TERMINAL_MODULE_ROOT=/mnt/c/projects/senior-infra-ops-analyst/.review-runtime/p004b-terminal-state/node_modules `
  bash tests/validate-package.sh
```

The long command is exact execution configuration, not a project runtime pin.
Use authorized host execution when WSL is sandbox-blocked; do not retry bare
PowerShell `bash`. Substitute the explicit Python test command for the final
`bash tests/validate-package.sh` when running focused suites. Keep long logs in
this plan's own execution workspace; never read/delete a sibling plan's ledger.

Preserve the already selected Native implementation method. This plan completes
the author fix pass of the previously reviewed terminal plan; its whole-branch
review is not repeated. The companion plan requires one fresh scoped security
candidate review, which may check these corrected integration boundaries without
reopening all historical branch work.

Return commits, actual counts, signal/process cleanup evidence, skips and any
unresolved material finding. Native offline and authenticated acceptance,
hosted CI/Security and merge remain separate and unexecuted. Continue with
[the approval-lifetime plan](2026-10-07-p0-04b-approval-lifetime-remediation.md)
only after both written plans are reviewed and approved.
