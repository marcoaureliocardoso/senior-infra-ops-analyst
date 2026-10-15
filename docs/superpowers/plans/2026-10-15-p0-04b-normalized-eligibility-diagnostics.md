# P0-04B Normalized Eligibility Diagnostics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve the actual normalized eligibility rejection subreason without content retention or changed operational decisions.

**Architecture:** Freeze an optional closed-enum sibling alongside the existing
four-field observation. One assessment supplies both the unchanged anchor decision
and its detail; one sealed projection transports both to the existing collector.

**Tech Stack:** Existing Python unittest/mock, passive Node/xterm adapter, controlled Python PTY peers and Debian WSL; no new dependencies.

**Spec:** [Approved specification](../specs/2026-10-15-p0-04b-normalized-eligibility-diagnostics-design.md).

## Global Constraints

- Written spec and plan operator-approved; inline execution (2) selected, with one final independent reviewer. Native execution remains separately gated.
- Planning baseline: `810e742e3c2eec5d5536442353f7ce676c4d4fc6`; last native source: `d86543d946a714557ba3289718d9cc772afcc9a2`. Its grant is consumed.
- Reuse the existing `p0-04b-browser-automation` linked worktree after verifying isolation and preserving operator changes. Use command-local Git safe.directory.
- Preserve exactly four `contextCommandFailure` fields, original operational reasons, acceptance events, input bytes, evaluation order, scope/lifetime checks and cleanup.
- Add `normalizedInputFailure` only on `failure` with `INPUT_PROBE_REVOKED` and valid base observation check `NORMALIZED_ELIGIBILITY`.
- Reuse the nine reason, three relation and five cause enums in the spec. UNSUPPORTED_ROW requires exactly three keys; other reasons require exactly one key. Reject nulls, unknown values and extra fields.
- One normalized assessment only; no later recomputation, extra IO, poll, clock read, authority check, key, retry or renewed lifetime.
- Keep 16 records and 3072 exported JSON bytes per phase; keep 16384 bytes for the complete outer report, including disposal/audit and newline.
- Keep 25 seconds per dialogue, 165 seconds total, at most two cases, stop at first inconclusive and existing SDK/request ceilings.
- No real Claude/provider/browser run, operator credentials/configuration access, deleted-content reconstruction or expanded raw-debug capture in implementation verification.
- Preserve installed package behavior, existing read-only mounts and staging/archive scope; no dependencies, activation flags, CLI changes, manifest/version changes or provider/runtime pins.
- Documentation is English. No push, PR, merge, release or definitive TODO completion is authorized by this plan.

## Review Focus

1. A first failure without detail must not acquire a later, plausible detail; Task 1 pins first-freeze retention for both fields.
2. A different non-null anchor is ANCHOR_CHANGED, while malformed absent-anchor detail stays unknown; Task 2 tests the actual comparison and invalid assessments.
3. An optional diagnostic failure must not suppress the original revocation or cleanup; Tasks 2/3 inject preparation, projection and persistent collector failures.
4. Source-derived suggestion descriptions can set contextFresh while general readiness is READY; Tasks 2/3 prove neither permits Enter or numeric acceptance.
5. A valid sibling copied to a foreign exception/run or emitted without the matching base must not survive; Tasks 1/3 test provenance, serialization coupling and dialogue isolation.

---

## Files and verification routes

No new product module is required. Modify:

- `tests/terminal_context_diagnostics.py` and `tests/test-terminal-context-diagnostics.py`: closed detail, immutable paired attachment and pure projection.
- `tests/terminal_structural_diagnostics.py` and `tests/test-terminal-structural-diagnostics.py`: sibling coupling, atomic copies and unchanged budgets.
- `tests/terminal_context_echo.py` and `tests/test-terminal-context-echo.py`: actual assessment capture, unchanged decision and ordered rejection.
- `tests/headless_context_driver.py` and `tests/test-headless-context-driver.py`: transport, controlled-peer input and cleanup parity.
- `tests/test-offline-terminal-resume-safety.py` and `tests/test-terminal-wiring.py`: maximal envelopes and unchanged packaging/isolation.
- ADR-010, architecture index, CHANGELOG, validation notes, spec status and this plan: enforced behavior and observed evidence only.

Use explicit scripts, not unittest discovery, because filenames are hyphenated.
Run each named suite from PowerShell with this established prefix:

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

The paths identify existing test dependencies, not product version requirements;
verify their presence before execution. GREEN means unittest OK/exit 0, without
warnings. RED must be the newly named missing behavior, not a dependency failure.
The full gate uses this prefix with `bash tests/validate-package.sh` replacing
`python3 tests/TEST_FILE.py`. Expect exit 0 and `package validation passed`.
Use local Windows Git for explicit-file staging/commits, never WSL Git.

### Task 1: Closed sibling contract and paired sealed observation

**Files:** Journal, collector and their two existing unit suites.

**Interfaces:**
- Add `valid_normalized_input_failure(value) -> bool` in the journal module; reuse policy enum constants.
- Extend `ContextFailureJournal.freeze(error, check, *, normalized_input_failure=None) -> None`; preserve positional callers.
- Add `ContextFailureJournal.project_fields(error, *, controller_owner, scope, state, transition_owner) -> dict | None`.
  The dict contains `context_command_failure` and optional `normalized_input_failure`, matching driver keyword names. Invalid base returns None.
- Keep `project(error, *, controller_owner, scope, state, transition_owner) -> dict | None` unchanged: exactly the original four serialized fields.
- Collector `add(..., normalizedInputFailure=...)` accepts the sibling only with the spec's matching point/reason/base check; existing callers are unchanged.

- [x] Write `test_normalized_detail_closed_shapes`: all nine reason codes pass with their specified key shapes; all relation/cause combinations pass only under UNSUPPORTED_ROW. Assert False for missing/partial pairs, unknown/ELIGIBLE reasons, nulls, booleans, extra keys and non-dicts.
- [x] Write `test_paired_projection_is_frozen_and_base_contract_unchanged` using the existing `journal()` fixture:

```python
journal, bindings = self.journal()
journal.set_phase('EDIT_PENDING')
journal.acknowledge(8, submission=False, remaining=8)
detail = {'reason':'UNSUPPORTED_ROW','rowRelation':'OTHER_CAPTURED_ROW','rowCause':'UNRECOGNIZED_SHAPE'}
error = InputProofError('INPUT_PROBE_REVOKED')
journal.freeze(error, 'NORMALIZED_ELIGIBILITY', normalized_input_failure=detail)
fields = journal.project_fields(error, **bindings)
self.assertEqual(fields['normalized_input_failure'], detail)
self.assertEqual(fields['context_command_failure'], journal.project(error, **bindings))
self.assertEqual(len(journal.project(error, **bindings)), 4)
```

- [x] Add `test_detail_loss_does_not_destroy_valid_base_or_enrich_later`: malformed optional detail, incompatible check/error reason and a second freeze omit detail but retain the original valid base; later valid detail cannot enrich it. Mutating input/projection cannot change stored scalars.
- [x] Extend existing foreign/replaced/closed attachment and changed-run tests to `project_fields`; assert None for both-field projection on invalid provenance. Extend no-live-effects test to assert no clocks, polls, IPC or scope checks during paired projection.
- [x] Add collector tests `test_normalized_sibling_requires_exact_failure_binding`, `test_normalized_sibling_is_atomic_and_detached`, `test_normalized_sibling_uses_actual_export_budget`: malformed records append nothing and set rejected; 100 maximal records remain <=16 and <=3072 actual default JSON bytes with truncation.
- [x] Run journal and collector suites to meaningful RED.
- [x] Implement closed validation and immutable scalar freezing. Detail is eligible only for NORMALIZED_ELIGIBILITY with the original error reason INPUT_PROBE_REVOKED. Invalid optional detail is omitted; valid base is preserved. Preserve first-attempt latching and release all private bindings in finish().
- [x] Implement paired projection through one shared provenance validation; base-only projection preserves its old result. Do not call live accessors or retain mutable assessment objects.
- [x] Implement independent atomic collector validation/copying, without changing existing error/byte-limit behavior. Run both suites to GREEN and inspect pristine output.
- [x] Commit explicit Task 1 files: `test: add sealed normalized eligibility detail contract`.

### Task 2: Capture the actual normalized assessment once

**Files:** Context component and its existing test suite.

**Interfaces:**
- Consume Task 1 `freeze(..., normalized_input_failure=None)`.
- Add private `_normalized_failure_detail(assessment, expected_anchor) -> dict | None` in the context module. It accepts the existing EmptyInputAssessment/InputAnchor types, copies only closed scalar enums and returns ANCHOR_CHANGED for an actual different non-null anchor.
- Extend private `_diagnostic(record, method, *args, **kwargs)` forwarding and `_fail(record, reason, check=None, *, normalized_input_failure=None)`; preserve all current callers and operational error semantics.

- [x] Add `test_normalized_suggestion_detail_uses_actual_single_assessment`: use existing diagnostic_edit()/frame() fixtures with a selected command-like description on another row, above and below input, without numeric labels. Assert `INPUT_PROBE_REVOKED`, phase REVOKED and base `EDIT_PENDING/NORMALIZED_ELIGIBILITY/8/0`; paired detail equals UNSUPPORTED_ROW/OTHER_CAPTURED_ROW/UNRECOGNIZED_SHAPE.
- [x] In that test, wrap `policy.empty_input_assessment` only around the rejecting `observe` call; assert call_count==1 and capture its returned assessment. Assert its general normalized readiness can be READY without permitting submission. Do not reclassify a newer snapshot to generate observation.

```python
command, journal, bindings = self.diagnostic_edit()
snapshot = frame('❯\u00a0/context', 10,
    history=((34, '❯ /context   Visualize current context usage as a colored grid'),))
with mock.patch.object(self.policy, 'empty_input_assessment',
        wraps=self.policy.empty_input_assessment) as assess:
    with self.assertRaises(challenge.InputProofError) as caught:
        command.observe(snapshot, 2)
self.assertEqual(assess.call_count, 1)
self.assertEqual(caught.exception.reason, 'INPUT_PROBE_REVOKED')
self.assertEqual(command.phase, 'REVOKED')
self.assertEqual(journal.project_fields(caught.exception, **bindings)['normalized_input_failure'], {
    'reason':'UNSUPPORTED_ROW','rowRelation':'OTHER_CAPTURED_ROW','rowCause':'UNRECOGNIZED_SHAPE'})
```

- [x] Add `test_description_freshness_is_not_numeric_or_input_authority`: the command description can make contextFresh true while context_percent is None; removing the selector leaves a valid exact command echo, with no failure detail. No terminal content enters the observation.
- [x] Add `test_normalized_reason_matrix_and_anchor_comparison`: pure fixtures exercise real supported row causes; controlled EmptyInputAssessment returns cover all remaining enum branches. A different non-null anchor yields exactly `{'reason':'ANCHOR_CHANGED'}`; absent anchor with unknown/ELIGIBLE/inconsistent detail remains revoked with base only.
- [x] Add `test_preceding_fault_wins_without_normalized_detail`: simultaneous prefix and foreign-row faults retain PREFIX_CELLS with no sibling. Existing forbidden UI, geometry and lifetime failures retain their existing precedence and check.
- [x] Add `test_detail_preparation_or_freeze_failure_preserves_original_rejection`: inject helper/projection preparation and freeze errors separately; assert same reason, irreversible revocation and no new authority. A helper failure must still call the original rejecting path, not replace it with its own exception.
- [x] Run context-echo suite to meaningful RED.
- [x] Replace only `_prefix`'s current anchor-only assessment call with one ordered assessment call and the identical anchor comparison. Prepare optional enums best-effort only on rejection; freeze before revocation. Do not instrument later nonce/exit checks or change policy classification.
- [x] Run context-echo, journal, collector, input-policy and input-challenge suites to GREEN; verify no extra IO/clock/scope calls and unchanged no-observer behavior.
- [x] Commit explicit Task 2 files: `test: preserve normalized rejection detail at its decision`.

### Task 3: Driver transport, bounded envelope and cleanup parity

**Files:** Selected driver/test, offline safety test and wiring test.

**Interfaces:**
- Consume Task 1 `project_fields(...)` once in the original driver's catch.
- Extend only nested `diagnose(..., normalized_input_failure=None)`; map it to `normalizedInputFailure` on the existing failure record.
- Keep drive(), CLI, proof-event schema, owned writes, scope and offline launcher interfaces unchanged.
- Extend private test `run_pinned_probe` modes with `normalized-suggestion-above`, `normalized-suggestion-below`, `normalized-plain-description`, `normalized-observer-loss`.

- [x] Add `test_normalized_detail_reaches_report_without_enter`: synchronize each selected-menu-like peer redraw at the existing writable-wait barriers; do not rely on sleep timing. Assert these report facts and actual controlled-peer input:

```python
report = self.run_pinned_probe('normalized-suggestion-above')
failure = next(row for row in report['records'] if row['point']=='failure')
self.assertEqual(failure['reasonCode'], 'INPUT_PROBE_REVOKED')
self.assertEqual(failure['normalizedInputFailure'], {
    'reason':'UNSUPPORTED_ROW','rowRelation':'OTHER_CAPTURED_ROW','rowCause':'UNRECOGNIZED_SHAPE'})
self.assertEqual((self.root/'probe-input').read_bytes(), b'/context')
self.assertNotIn('context_sent', [row['point'] for row in report['records']])
```

- [x] Repeat below input. The plain-description mode completes the existing controlled success workflow and emits no sibling. Ensure a numeric panel is still required after Enter; contextFresh from description is insufficient.
- [x] Add `test_normalized_projection_loss_keeps_original_cleanup`: missing/raising/malformed paired projection, preparation failure and persistent collector RuntimeError/LookupError preserve original events, written bytes and revocation. Assert actual capture closure, both PTY FDs closed and both leaders reaped using existing cleanup helpers.
- [x] Add `test_normalized_detail_cannot_cross_dialogue_or_attach_late`: fresh dialogue has fresh counters/bindings; later nonce/clear/exit failures and successful records carry no normalized sibling from a prior command.
- [x] Extend `test_early_command_debug_keeps_original_omission_contract` for normalized rejection: debug stays OMITTED_PROVENANCE and no cells, description, marker or nonce is serialized.
- [x] Extend the existing maximal four-phase offline envelope with maximal paired fields and the existing 4096-byte debug allowance; assert each actual serialized phase<=3072 and full JSON+newline<=16384. Preserve disposal failure blocking and unchanged aggregation proof requirements.
- [x] Extend wiring assertions: no installed/staging/archive inclusion or new mount, flag or dependency; paired diagnostics cannot satisfy PTY acceptance. Run selected-driver/offline-safety/wiring tests to RED.
- [x] Integrate one pure paired projection into the catch; only known diagnose keyword names may be forwarded. Invalid/missing envelopes must not raise while handling the operational exception. Preserve best-effort producer reporting and never retry an unavailable collector.
- [x] Run journal, collector, context-echo, selected-driver, context-debug, offline-safety, wiring, cancellation and headless-signals suites to GREEN. Record actual counts/runtimes; no real Claude/provider execution.
- [x] Commit explicit Task 3 files: `test: transport bounded normalized eligibility diagnostics`.

### Task 4: Indexed architecture, immutable gates and handoff

**Files:** `docs/architecture/ADR-010-browser-automation-boundary.md`, architecture
README, CHANGELOG, `tests/validation-notes.md`, approved spec status and this plan.

**Interfaces:** Document enforced contracts and evidence only; runtime is unchanged.

- [x] Record additive sibling, single assessment, paired sealed provenance, alternatives, privacy, budgets and rollback in ADR-010 and its index; distinguish the autocomplete hypothesis from a proven native cause.
- [x] Add a factual unreleased CHANGELOG entry and actual RED/GREEN results to validation notes. Update spec/plan statuses only as observed; preserve all historical evidence and pending gates.
- [x] Run `validate-content.py` and `test-architecture-docs.py` with the explicit prefix; expect content validation passed and unittest OK/exit 0. Check whitespace, links, <=300-character lines, unchanged manifests and test-only diff scope.
- [x] Commit explicit documentation files, verify tracked worktree clean and capture the immutable implementation candidate.
- [ ] Run the complete package gate on that candidate. Record exact hash/log/exit and all capability/platform skips; local workflow validation is not remote CI/Security or native/provider/browser acceptance.
- [ ] Obtain scoped independent review of this plan's full implementation range on that immutable candidate, including unchanged interacting callers. Supply the spec, Review Focus, test evidence and any execution rulings. If unavailable, retain that gate pending.
- [ ] Handle findings under the selected execution workflow with author TDD. Any source correction requires a fresh immutable candidate and full package gate. Never launch a native attempt as automatic remediation or verification.
- [ ] Record actual outcomes in result-only docs; verify any post-gate documentation-only delta separately and distinguish final HEAD from reviewed/tested source hashes.
- [ ] Hand off commits, clean/dirty state, test/review evidence, residual risks and pending native/provider/browser/remote CI/Security gates. Preserve worktree/branch; no automatic push, PR, merge or native retry.

## Self-review and execution handoff

Coverage: Tasks 1/2 own shape, provenance, actual assessment and first-failure
requirements; Task 3 owns transport, parity, caps, disposal and packaging; Task 4
owns indexed decisions, review and immutable evidence. All five review-focus
conditions have named tests. No generic READY or contextFresh result replaces
input ownership or numeric context proof. Signatures and camel/snake-case field
names are consistent across task interfaces.

Selected execution: inline, with one final fresh independent reviewer. Tasks 1-3
are implemented with TDD; 181 covering tests passed, including the completion run
on committed source. Architectural evidence is being finalized before the
immutable candidate's complete package gate and independent review. Native,
provider/browser, remote CI/Security and integration gates remain pending.
