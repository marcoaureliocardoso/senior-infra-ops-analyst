# P0-04B Rejected Edit-Row Diagnostic Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Export one sanitized rejected edit row only under explicit offline development opt-in and after proven disposal, without changing input authority.

**Architecture:** A separate sealed first-failure observer records the actual
ordered evaluator's rejected row. The existing debug module prepares a bounded
memory-only candidate; only the outer launcher promotes it to public output after
owned child/root cleanup. Default and old-debug paths remain unchanged.

**Tech Stack:** Existing Python unittest/mock, selectors/os pipes, TerminalCancellation,
passive Node/xterm helper, controlled Python PTY peers and Debian WSL; no dependencies.

**Spec:** [Approved written specification](../specs/2026-10-15-p0-04b-rejected-edit-row-debug-design.md).

## Global Constraints

- Written spec and plan operator-approved; inline execution selected (2). Tasks 1-3 implemented; Task 4 verification/review is in progress. No new native execution has occurred.
- Planning baseline: `562ee10c620ec3fe6ec9b730bf3644c40dd6fe6d`. Last native commit: `19173557b54778fb944b8b764223b58738ee8688`; that one-shot grant is consumed.
- Reuse the verified linked `p0-04b-browser-automation` worktree; preserve operator changes. Use command-local Windows Git safe.directory, not WSL Git.
- New option `--debug-context-edit` is offline-only, off by default and mutually exclusive with `--debug-context`; no environment fallback or live/audit activation.
- Eligibility is exactly INPUT_PROBE_REVOKED, EDIT_PENDING / NORMALIZED_ELIGIBILITY / 8 command bytes / 0 Enter bytes, plus UNSUPPORTED_ROW / OTHER_CAPTURED_ROW / UNRECOGNIZED_SHAPE.
- The first failure alone may capture; preserve one ordered assessment, original anchor comparison, errors/events, Enter/Ctrl+U/exit bytes, lifetime, revocation and cleanup. No later reclassification/enrichment.
- Copy at most one row of 120 validated terminal cells; exported excerpt has exactly rowRelation and text, at most 4096 actual UTF-8 JSON bytes. Omit whole, never clip.
- No new raw-frame/excerpt file or content-bearing report temporary file. The new mode uses bounded memory-only IPC; old/default report transport is unchanged.
- Public debugContextEdit has status, untrustedData=true, chatCopyMayPersist=true, and excerpt only for READY. READY requires native/helper/namespace child reaping and absent case/outer roots, capture and history.
- Keep 16 records and 3072 bytes per structural phase; 16384 bytes for complete intermediate and final report, including final audit/disposal fields and newline. One extra read byte detects IPC overflow.
- Keep 25 seconds per dialogue, 165 seconds total, at most two synthetic cases, existing SDK/request ceilings and stop at first inconclusive. No retry.
- Preserve network isolation, hidden operator state, dropped capabilities, synthetic-only startup confirmation and disposable history. No operator credentials/configuration access.
- Reuse existing mounted modules; no dependency, module mount, Nori manifest, staging/archive inclusion, installed behavior, runtime/provider pin or production route change.
- Planning/implementation verification is synthetic only. No real Claude/provider/browser execution, deleted-content recovery, push, PR, merge, release or definitive TODO completion.
- Documentation is English. Sanitization is conservative, not a secrecy guarantee; a separately authorized chat/export copy may persist.

## Review Focus

1. First failure without a usable row must remain omitted even if a later failure looks eligible; Task 1 pins first-attempt latching and release.
2. The normalized row index must identify the same unchanged other row in the original snapshot, not merely an equal later frame; Tasks 1/2 pin identity and one ordered evaluation.
3. A peer can close its stdout but stay alive, or fill the pipe while blocked; Task 3 pins process/EOF independence, bounded drain and original deadline/cancellation.
4. Child-supplied cleanup flags or serialized identities cannot promote READY before actual parent-owned root removal; Task 3 pins promotion at the owned disposal receipt.
5. An omission or malformed candidate must not copy arbitrary text through other keys, exception strings or partial JSON; Tasks 1/3 pin closed output and whole-excerpt omission.

---

## Files and verification routes

Modify existing modules only:

- `tests/terminal_context_echo.py`: optional sealed rejected-row observer and exact decision-boundary capture.
- `tests/terminal_context_debug.py`: separate memory-only capture, sanitization, candidate validation, final promotion/size fitting. Old ContextDebugCapture stays separate.
- `tests/claude-pty-driver.py`, `tests/headless_context_driver.py`: explicit validated object forwarding, first failure preparation and unconditional release.
- `tests/offline-terminal-resume-probe.py`: option/mode forwarding, inner pending candidate, bounded outer IPC and post-disposal output.
- Tests: `test-terminal-context-echo.py`, `test-terminal-context-debug.py`, `test-headless-context-driver.py`, `test-offline-terminal-resume-safety.py`, `test-terminal-wiring.py`, plus existing cancellation/signals regressions.
- ADR-010, architecture README, CHANGELOG, validation notes, approved spec and this plan: implemented contracts and immutable evidence.

Use explicit scripts, not unittest discovery. Run from the worktree with:

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

These are verified test-dependency locations, not product pins; recheck presence.
GREEN requires unittest OK/exit 0 without warnings. RED must identify the named
missing behavior, not an environment/import/dependency error. The complete gate
replaces the Python command with `bash tests/validate-package.sh`; expected exit 0
and `package validation passed`. Inspect and record every capability/platform skip.

### Task 1: Sealed row provenance and memory-only sanitization

**Files:** Context echo/debug modules and their two existing unit suites.

**Interfaces:**
- In echo: `_create_edit_row_observer(*, controller_owner, scope, state, transition_owner, journal) -> EditRowObserver`.
- `EditRowObserver.bind_command(command_record) -> None` binds once to the actual registered private command record and its original run/deadline; copied/unregistered records and rebinds are rejected.
- `freeze(error, check, *, command_record, snapshot=None, assessment=None, rejected_index=None) -> None` latches the first attempt, including omissions.
- `project(error, *, controller_owner, scope, state, transition_owner, journal, snapshot) -> tuple[tuple[TerminalCell, ...], float] | None` validates the exact first error/record/snapshot and existing paired journal; returns only the rejected row and original deadline, with no live IO/evaluation.
- `finish() -> None` releases content-bearing private bindings on every path.
- In debug: `create_context_edit_debug(scope, state, root) -> ContextEditDebugCapture` and `validate_context_edit_debug(value, state, scope) -> None`, using existing namespace/scope/root ownership checks.
- Capture methods: `bind(*, controller_owner, transition_owner, journal) -> EditRowObserver`; `prepare(error, *, controller_owner, transition_owner, journal, snapshot) -> None`; `finish() -> None`; `pending_report() -> dict`.
- `pending_report()` emits a detached closed private candidate: status PREPARED plus excerpt, or a spec omission/NO_CAPTURE with no excerpt. It never emits public READY and requires absent case root. Public metadata is added only at final promotion.
- finish() releases raw row/snapshot/exception bindings; at most one sanitized pending candidate remains until pending_report() consumes it or an omission discards it. A second report cannot replay content.
- Share existing sensitive scanning/escaping helpers; no top-level echo-to-debug import cycle. The observer lives in echo; debug may import it as it already imports echo helpers.

- [x] Add `test_edit_row_first_failure_binding` using existing diagnostic_begin/diagnostic_edit fixtures. Bind the observer, freeze the exact eligible
  error and assert project returns the original other-row tuple and deadline; base-only journal projection remains four fields and paired enums unchanged.
- [x] Add `test_edit_row_missing_first_cannot_enrich`: freeze no detail, invalid detail or an earlier check, then a later eligible error; project stays None. Mutating copied metadata cannot change original evidence. finish makes projection impossible and releases references.
- [x] Add `test_edit_row_rejects_foreign_and_equal_replacement_snapshot`: wrong error/controller/scope/state/transition/journal/run/command record, copied
  attachment, equal-but-distinct snapshot, normalized current-row index and different row all return None. Count zero evaluator/clock/IO calls during
  projection.
- [x] Add debug tests `test_edit_capture_closed_boundary_and_no_file`, `test_edit_capture_sensitive_scan_and_unicode`,
  `test_edit_capture_actual_byte_limits`, `test_edit_capture_observer_loss_omits`. Cover all spec tuple mismatches, audit/scope/root/expiry loss,
  malformed/wide/continuation cells, ordinary Unicode and inert control escaping, sensitive synthetic material anywhere in the snapshot, scan exceptions
  and exact 120-cell/4096-byte boundaries. Assert omission, never print protected fixtures or assertion payloads.
- [x] Assert the excerpt has exactly `{'rowRelation','text'}`, relation OTHER_CAPTURED_ROW, and no adjacent/cursor row, session ID, hash or exception text.
  Oversize omits the whole excerpt; first omission cannot later become PREPARED. Spy on file opens: new capture performs no write; old debug tests remain
  unchanged.
- [x] Run both suites to meaningful RED; implement the exact observer/capture interfaces with immutable private identities and first-attempt latching, keeping content separate from the enum journal. Unknown/inconsistent evidence is omitted.
- [x] Run both suites to GREEN plus `test-terminal-context-diagnostics.py`, `test-terminal-structural-diagnostics.py` and `test-terminal-input-policy.py`. Verify cleanup and no warnings.
- [x] Commit explicit Task 1 files: `test: add sealed memory-only edit-row diagnostic`.

### Task 2: Single-assessment boundary and selected-driver wiring

**Files:** Context echo, both drivers, offline launcher; echo/driver/offline/wiring tests.

**Interfaces:**
- Add keyword-only `context_edit_debug=None` to drive() and drive_context(); both debug objects together are invalid before native launch.
- Add private `_edit_row_observer=None` to begin_context_command(); bind it once to that command record. The controller creates it through capture.bind() with the real controller/journal/transition identities.
- Existing `_fail` freezes the row observer after the enum journal and before revocation. Non-normalized failures latch omission; normalized failure supplies the original snapshot, actual assessment and actual rejected index.
- Only when enabled, `_prefix` uses the existing `_empty_input_assessment(normalized)` tuple directly once to preserve its rejected index; disabled path
  keeps empty_input_assessment(). Both share the identical anchor comparison. Update call-count tests to count the underlying ordered evaluator, not only
  its public wrapper.
- Add `debug_context_edit=False` to run_offline_controls(), _namespace() and _controls(); exact bool validation and mutual exclusion. Inner new mode is `--inner-controls-edit-debug`; outer is `--run-offline --debug-context-edit`.
- _controls() creates the new capture per dialogue, forwards only that object, and puts its detached private candidate under `_pendingContextEdit` after case disposal. Do not expose public debugContextEdit here.
- Until Task 3 supplies the memory-only transport, _namespace() must block the new mode before child spawn. Never temporarily fall back to the existing content-bearing TemporaryFile route. Task 2 tests inner/driver wiring with controlled peers or mocks only.

- [x] Extend `run_pinned_probe(..., edit_debug=False)` without changing existing positional callers. Add a new redraw barrier before observe() so the selected row arrives in EDIT_PENDING (not the existing SUBMIT_PENDING fixture); do not rely on sleeps. Use Python peer only.
- [x] Add `test_edit_capture_single_real_assessment_above_below`: selected rows above/below input yield the original error/base/detail and one prepared
  row; assert one ordered evaluation with and without opt-in. Exact same command bytes, zero Enter, revocation and events; plain-description path retains
  original success workflow and no capture.
- [x] Add `test_edit_capture_release_and_observer_loss`: persistent failures in freeze/project/prepare/finish cannot mask operational failure or cleanup. Assert actual capture closure, both PTY FDs closed, native/helper leaders reaped and observer bindings released; no failing-collector retry.
- [x] Add `test_edit_capture_driver_validation_precedes_launch`: arbitrary objects, missing scope/state, legacy/non-context route and both debug objects fail before launch. Existing early `--debug-context` still reports OMITTED_PROVENANCE.
- [x] Add `test_edit_option_is_explicit_offline_only`: validate_mode accepts only the new exact outer combination in addition to old combinations; rejects
  audit/live/duplicate/mixed flags and environment-only activation before runtime launch. Test parser/main forwarding with mocked controls, never real
  Claude.
- [x] Add `test_edit_transport_unavailable_blocks_before_spawn`: until the Task 3 transport is present, new-mode namespace entry returns bounded
  OFFLINE_PROBE_BLOCKED without launching a child or opening a report file. Task 3 replaces this temporary closed gate with real bounded pipe tests, not a
  file fallback.
- [x] Add `test_edit_pending_is_not_acceptance_or_cross_dialogue`: forged debug READY cannot satisfy case_complete, earlier pending rows do not cross dialogue/case boundaries, and normal structural output has no strings from the excerpt.
- [x] Run echo/debug/selected-driver/offline-safety/wiring suites to meaningful RED. Implement only the explicit wiring and boundary changes above. Capture preparation occurs in the existing failure path before resources close; finish/release is unconditional in finally.
- [x] Run those suites plus journal/collector, input policy/challenge, cancellation and headless-signals to GREEN. Record actual counts and selected-driver runtime, not inferred totals.
- [x] Commit explicit Task 2 files: `test: wire explicit offline rejected-row capture`.

### Task 3: Bounded pipe and post-disposal publication

**Files:** Offline launcher, debug module, offline-safety/debug/wiring tests.

**Interfaces:**
- In launcher: `_read_edit_namespace(command, *, cancellation, deadline) -> tuple[int, bytes]` spawns exactly one owned child with stdout=PIPE,
  stderr=DEVNULL, stdin=DEVNULL and existing clean env. It drains only that pipe, bounded to 16385 bytes, using selectors/nonblocking reads and the
  original cancellation/deadline.
- The helper never returns content until child exit/reaping and EOF are proven; EOF alone is not completion. Timeout, overflow, cancellation or malformed transport discards bytes and runs existing owned cleanup. No retry, descendant sweep outside that ownership or unbounded communicate().
- In debug: `finalize_edit_report(report, pending, *, disposal_proven: bool) -> dict`. Consumes only the exact private candidate from the launched child's
  dedicated pipe; strict closed shape/status/type/size validation rejects extras/nulls/content on omissions. It removes all private fields and adds public
  debugContextEdit per spec only after parent-owned disposal is proven.
- `disposal_proven` is a trusted in-process receipt derived from actual owned namespace-child cleanup and finalize_owned() success, plus validated native/helper/case disposal facts. It is not a CLI input or a child-supplied disposableRootAbsent boolean.
- Validate the new-mode report's known outer/case/stage/diagnostic shapes and strip no arbitrary field into public output; malformed data returns bounded content-free blocked/omitted output. Do not reflect unvalidated input/error text.
- Measure complete intermediate/final JSON with the actual launcher encoding plus newline and final audit/disposal fields; omit the whole optional excerpt before blocking an otherwise oversized base. Old/default TemporaryFile route and old fit_debug_report() stay unchanged.

- [x] Add `test_edit_pipe_never_uses_report_tempfile`: intercept child options and TemporaryFile/open writes; only the new mode uses a pipe, no content file; old/default modes retain their existing transport. Spy on child count: exactly one.
- [x] Add `test_edit_pipe_eof_and_exit_are_independent`: controlled Python children close stdout then wait, exit after partial JSON, and leave a descendant
  holding stdout. Assert no premature success, finite original deadline, no leaked owned child/descriptor. Use barriers/pipes, not sleep assumptions.
- [x] Add `test_edit_pipe_overflow_backpressure_and_cancel`: controlled peers emit exactly 16384/16385 bytes, fragmented Unicode/JSON and larger blocked
  output; cancel during drain. Assert at most 16385 retained bytes, discarded incomplete/oversized content, no retry, deadline not reset and owned cleanup
  after every outcome.
- [x] Add `test_edit_promotion_requires_parent_disposal`: child claims cleanup/READY or inserts serialized identity fields; actual root remains, cleanup
  raises or namespace child is not reaped. No excerpt escapes. Normal finalization checks the real root identity and only then promotes PREPARED to READY
  with both public booleans true.
- [x] Add `test_edit_candidate_closed_shapes_and_report_budget`: reject arbitrary keys, wrong status/types, PREPARED without excerpt, omission with text,
  nulls, duplicate JSON keys and malformed UTF-8; report no payload. Four maximal structural phases plus maximal excerpt either fit <=16384 or omit only
  the entire excerpt. Structural failure/cleanup facts are preserved.
- [x] Add `test_edit_publication_is_after_full_disposal`: controlled-peer integration prepares one non-sensitive row, disposes case and outer roots, then
  publishes; record actual ordering. Fault at each disposal stage yields only content-free omission. No public stdout/log/frame/excerpt file contains
  candidate text before disposal; internal pipe alone may carry it.
- [x] Run offline/debug/wiring tests to meaningful RED. Implement the new-mode pipe/finalization branch only, keeping original authority/reporting paths unchanged. Parsing and optional report errors are best-effort omissions, not operational retries.
- [x] Run offline/debug/wiring, selected-driver, journal/collector/echo and cancellation/signals suites to GREEN. Check no ResourceWarnings, deadlocks, surviving descriptors or changed default output.
- [x] Commit explicit Task 3 files: `test: publish edit-row diagnostics after owned disposal`.

### Task 4: Indexed decisions, immutable gates and handoff

**Files:** ADR-010, architecture README, CHANGELOG, validation notes, spec and plan statuses.

**Interfaces:** Documentation describes implemented controls and evidence, not new authority.

- [ ] Document the separate opt-in boundary, exact tuple, sealed provenance, 120-cell/4096-byte minimization, memory-only IPC, disposal-before-export, alternatives, residual disclosure risk and rollback in ADR-010/index.
- [ ] Record actual RED/GREEN and command counts; update unreleased CHANGELOG without a manifest/version bump unless scope changed. Preserve 1917355 as consumed inconclusive evidence, not a successful acceptance test.
- [ ] Run `python3 tests/validate-content.py` and `python3 tests/test-architecture-docs.py` with the explicit prefix. Expected: content validation passed and unittest OK/exit 0. Check whitespace, links, <=300-character lines, test-only mounts/staging scope and unchanged production policy.
- [ ] Commit the explicit documentation files and verify clean tracked tree. Capture an immutable implementation candidate.
- [ ] Run complete `bash tests/validate-package.sh` on that candidate. Expected: exit 0 and package validation passed. Retain exact source hash, command/log, exit and all platform/capability skips. Local workflow checks are not remote CI/Security.
- [ ] Obtain scoped independent review from this plan's recorded implementation baseline through the immutable candidate, plus unchanged interacting
  callers, using the written spec, Review Focus and actual test evidence. This is the complete new refinement, not a fresh verdict on all inherited branch
  changes. Keep full-gate evidence separate from reviewer observations.
- [ ] Resolve findings under the chosen execution method with author TDD; any source correction requires a new immutable candidate and fresh full gate. No native attempt is an automatic fix/verification step.
- [ ] Close result-only documentation separately, distinguish final HEAD from tested/reviewed source, verify docs-only delta and rerun content/architecture checks. Record every execution ruling and residual cost.
- [ ] Hand off commits, clean/dirty state, tests/review, residual disclosure risk and pending native/provider/browser/remote gates. Preserve branch/worktree; no push, PR, merge, release or definitive TODO completion.

## Self-review and execution handoff

Spec coverage: Task 1 owns exact first-row provenance, sanitization and byte limits;
Task 2 owns one ordered decision, explicit option/routing, no-authority parity and
release; Task 3 owns IPC, deadline/cancellation, post-disposal promotion and actual
outer caps; Task 4 owns indexed architecture and immutable evidence. All five
Review Focus cases have named tests. Public camel-case output and private pending
payload are separate; neither can authorize input. No new module mount is needed.

The observer and capture interfaces carry the actual controller/journal/transition
identities; a pending serialized candidate cannot recreate them. PREPARED exists
only inside the owned IPC path, while READY is parent-generated after disposal.
The default and old-debug contracts, including first-inconclusive stop, stay fixed.

The operator selected inline execution with one final fresh independent reviewer.
Tasks 1-3 are committed at 30e5a20, 3c1af40 and 6426fbf with their full covering
suites repeated at task completion. Task 4 records the immutable full gate and
review separately in validation notes. The method does not authorize a native
run or a persistent chat excerpt; the earlier 1917355 grant remains consumed.
