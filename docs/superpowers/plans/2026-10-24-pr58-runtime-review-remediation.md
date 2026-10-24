# PR 58 Runtime Review Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans for direct execution with one independent final review. Steps use checkbox syntax for tracking.

**Goal:** Correct the three reproduced review findings without weakening authorization,
independent validation, runtime evidence, or CI isolation.

**Architecture:** Narrow the existing validation grammar and keep negative postconditions
inconclusive unless non-application is independently proven. Latch reset and failed-hook
events in the existing legacy stream reducer. Preserve the current envelope/fingerprint,
original lifetime, protected references, cleanup, and separate native acceptance gates.

**Tech Stack:** Existing Node.js ES modules and Python standard-library tests; Debian WSL
for the package gate and GitHub Actions for exact-head checks.

**Spec:** The operator's request to fix all three confirmed review findings at
91cd9416adf5ce0d92deda312be817dc97169048; the independent-validation contract in
references/browser-operations.md and the existing same-session measurement contract.

## Design decisions and alternatives

The recommended small correction preserves the current manifest/evidence schemas.
Configuration-class inputs cannot prepare independent validation. Interactive
authentication remains explicitly origin-bound; it is not permission to configure
the service. A negative desired-state predicate cannot prove that no earlier effect
occurred. Without a separate complete baseline/non-application proof, retain
OUTCOME_UNKNOWN and require reconciliation.

Adding a new pre-state evidence protocol would be a larger API/design change and is
not needed to stop false success. Relabelling validation writes as reads, interpreting
not-met as no change, or discarding lifecycle failures would preserve the defects.

The hosted Bubblewrap failure is a separate platform-policy gate. This plan allows
read-only diagnosis but does not authorize a profile/sysctl change, elevated suite,
shared host network, test skip, alternative runner rollout, or automatic retry of
any native/provider attempt.

## Global constraints

- Reuse the isolated p0-04b-browser-automation branch; preserve operator changes.
- No merge, release, actual Claude/provider/browser run, credential/configuration access,
  or renewal of any consumed grant.
- Preserve native approval, exact-command fingerprint, original lifetime, six-invocation/
  40-turn acceptance limits, bounded evidence, and cleanup requirements.
- Keep the root 0.15.0 package unreleased; review affected component patch versions
  against the canonical Nori metadata before committing.
- Deliverable text stays English. Do not globally disable lint or security checks.
- Do not mark the definitive TODO or P0-04B complete.

## Review focus

1. Configuration fill/select on a service origin must never run in validation.
2. Valid authentication on an explicit auth origin must remain usable; unbound or
   service-only interactive preparation must not become an authentication bypass.
3. A completed first effect followed by failure must not become NOT_APPLIED merely
   because the final desired predicate is false.
4. Reset/hook failures before or after terminal success must latch rejection and
   cannot be restored by later success; legitimate successful hook events remain valid.
5. Exact-head hosted failure must remain visible; an older immutable local pass
   cannot qualify later changes or silently substitute for native acceptance.

## Task 1: Restore independent validation

**Files:** browser-workflow.mjs and browser-runner.mjs under
skills/browser-operations/scripts; workflow.test.mjs, runner-contract.test.mjs and
runner-lifetime.test.mjs under tests/browser-operations; affected policy docs.

**Interfaces:** Keep parseWorkflowSteps, parseRunnerArgs, executeBrowserWorkflow,
the current CLI flags, protected-reference grammar and serialized result shape.

- [ ] Add tests rejecting validation fill and select with configuration values,
  including exact service/auth origin cases; keep a positive authentication control.
- [ ] Add a runner regression reproducing zero execution writes followed by a
  validator autosave; require rejection before value resolution or dispatch.
- [ ] Add a partial-application regression: the first write succeeds, a later step
  fails, a read-only verifier returns not-met; require outcome-unknown and
  validationRequired=true, not WORKFLOW_NOT_APPLIED.
- [ ] Run the new tests against the original code and record the intended failures.
- [ ] Implement the narrow validation-input/origin checks. Remove unsupported
  non-application inference from a negative predicate; preserve separate outcomes
  already proven before any potentially state-changing dispatch.
- [ ] Update existing expectations that intentionally encoded the unsafe inference,
  without removing execution, ambiguity, cleanup or lifetime assertions.
- [ ] Run the complete browser-operation suites, affected guard/lifetime contracts
  and documentation checks; commit the independently testable fix.

## Task 2: Invalidate tainted legacy measurement streams

**Files:** tests/browser_operations_live.py and
tests/test-live-browser-operation-safety.py.

**Interfaces:** Preserve evaluate_measurement_stream and its bounded structural
sample fields; no raw stream, prompt, transcript or secret is retained.

- [ ] Add table-driven tests with the existing valid stream as control, then
  conversation_reset and failed hook events before/after the success terminal.
  Require terminalSuccess=false in every fault case, even after another success.
- [ ] Cover foreign/malformed hook identity and error fields, plus valid successful
  hook events. Derive accepted field forms from existing native/SDK contracts.
- [ ] Run the new cases and observe rejection tests fail against the original reducer.
- [ ] Latch recognized reset/error/hook failures through the complete stream; do not
  let later events restore a sample. Preserve exact tool counts and session checks.
- [ ] Exercise the builder boundary so rejected samples cannot become trusted
  measurements, then run the full provider-free harness safety suite; commit.

## Task 3: Verify, review and update the existing PR

**Files:** CHANGELOG.md, tests/validation-notes.md, affected component metadata and
the existing PR description when updating stale head/timeout information.

- [ ] Run focused regressions, all browser/guard suites, ShellCheck, Markdown,
  spelling, schema and workflow checks, plus the full immutable package gate
  through the established Linux route. Record source SHA, skips, duration and cleanup.
- [ ] Obtain one independent final review of the complete correction range and
  address blocking findings through a documented RED/GREEN pass.
- [ ] Record truthful outcomes and update affected component patch metadata only
  where required; do not create a tag or release.
- [ ] Push to PR 58 without merge and inspect fresh CI/Security for that exact head.
  Preserve the hosted namespace blocker if it still fails.
- [ ] Report the remaining runner-policy decision separately. Any security-policy
  adaptation requires explicit approval and its own bounded design; do not bypass it.

## Acceptance and rollback

All three review reproductions must fail closed after correction, positive controls
must pass, and no new protected-value output or native authority may be introduced.
Hosted CI and native qualification are independent gates and must be labelled honestly.
Rollback uses focused reversions of the remediation commits; no operator settings
or persistent external state should require restoration.

## Status

Plan prepared for confirmation. No runtime/test implementation, commit, push,
CI policy change, or native/provider execution has occurred under this plan.
