# P0-04B Approval Lifetime Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent effects and successful late-result claims from outliving the original browser approval.
**Architecture:** A branded immutable lifetime shares one fresh clock and stored deadline between runner and selected adapter. Owned binding consumption is independent of authorization time. Existing origin/effect checks remain separate.
**Tech Stack:** Existing Node ESM browser runner/adapters, locked file-backed bindings, `node:test`, injected synthetic runtimes/clocks; no new dependency.
**Spec:** `docs/superpowers/specs/2026-10-07-p0-04b-review-remediation-design.md`, written specification approved at commit `1084a400efd67d2b9208708270c61692cc5a594e`.

## Global Constraints

- Use the existing isolated worktree and preserve operator changes. Implement after the companion harness author-fix plan; this production plan has its own ledger/ranges.
- No provider request, actual operator credential/configuration access, native Claude repetition, production UI operation, installation, push, PR, merge, release or definitive TODO completion is authorized.
- Use the original immutable envelope/deadline for execution and validation. The later request describes bound steps; its parser-derived expiry cannot authorize or prolong them.
- At `now >= originalExpiresAt`, no new operational dispatch is authorized. Invalid or backward samples fail closed.
- Preserve existing numeric `dependencies.now` as a constant test clock; accept callable injection for tests; default to current `Date.now()` at every check.
- No CLI/environment clock override, global service, new browser provider, permission server or operational gateway.
- No `await` may sit between a final assertion and its direct call expression. Recheck after asynchronous completion; late results are inconclusive.
- Missing or unsupported lifetime enforcement blocks operational selection; no silent no-op guard or fallback. Cleanup/abort/disposal never need renewed authority.
- Preserve fingerprints across parser timestamps, effect/role/origin/identity/credential/native-decision boundaries, read-only legacy scope and existing budgets.
- Keep root `0.15.0` unreleased. Update only affected browser component metadata; no release or authenticated acceptance claim.
- Native fix verification is provider-free and synthetic; in-flight calls cannot be unsent or automatically rolled back.

## Review Focus

1. A copied/forged/async lifetime assertion must not be accepted as installed enforcement (Tasks 1 and 2).
2. Expiry during protected-value resolution or adapter-internal waits must block the later consumer, not just the next workflow step (Task 2).
3. Clock failure after a persistent effect must not turn into a clean pre-effect denial or validated result (Task 2).
4. Cleanup of an expired old operation must not consume a later operator grant sharing its ID (Task 1).
5. A late or failed completion/reconciliation write must not leave a successful validation claim, even when the adapter returned success (Task 2).

## Task 1: Immutable lifetime and owned binding consumption

**Files:** Create `skills/browser-operations/scripts/browser-operation-lifetime.mjs`, `tests/browser-operations/operation-lifetime.test.mjs`.
Modify `skills/browser-operations/scripts/browser-binding-store.mjs`, `tests/browser-operations/binding-store.test.mjs`, `tests/validate-package.sh`.

**Interfaces:** Produce:
- `BrowserLifetimeError extends Error` with closed `code` only.
- `createOperationClock(source:number|(()=>number)|undefined)->OperationClock`, a frozen object exposing `readNow():number`; default current time, nonnegative safe integers, nondecreasing samples.
- `createOperationLifetime(envelope,clock:OperationClock)->OperationLifetime`, frozen/branded, exposing immutable `expiresAt`, `assertLive():number`, `remainingMs():number`.
  Require the clock produced by `createOperationClock`; `assertLive` returns its sampled time or throws. Arbitrary duck-typed clocks/lifetime callbacks are not branded.
- `isOperationLifetime(value)->boolean` checks module-owned identity, not merely duck typing.
- `hasOperationLifetime(adapter,lifetime)->boolean` requires a genuine lifetime, exact read-only `adapter.operationLifetime` identity and `adapter.capabilities.operationLifetime === true`.
- `consumeOwnedOperation({sessionId,operationId,toolUseId,invocationFingerprint,expiresAt},env)->boolean`: physically consumes the exact original grant under the existing lock, even after expiry; different later grants remain untouched. Absence is idempotent success only
  when no ambiguous owned state remains.

Closed failure codes: `OPERATION_EXPIRED`, `OPERATION_CLOCK_UNPROVEN`, `APPROVAL_BINDING_INVALID`, `OPERATION_LIFETIME_UNPROVEN`. Do not emit clock samples, grant contents, secrets or arbitrary thrown messages.

- [ ] **Step 1: Write clock/lifetime RED tests.** Use expiry `1000`, callable time initially `999`: `assertLive() === 999`, `remainingMs() === 1`; at `1000`, assert `OPERATION_EXPIRED`. For `NaN`, infinity, negative, fractional, Boolean, string, Promise-producing and
  backward clocks, assert `OPERATION_CLOCK_UNPROVEN`. Numeric `999` remains a valid constant clock. Assert a forged or copied lifetime fails `isOperationLifetime` and cannot pass adapter eligibility.
- [ ] **Step 2: Run RED.** Run `node --test tests/browser-operations/operation-lifetime.test.mjs`; expected missing module/interfaces before any implementation.
- [ ] **Step 3: Implement the exact lifetime API** in the new focused module; do not spread clock state across runner helper functions. Branding/frozen objects prevent a replaced assertion being mistaken for the invocation's lifetime.
- [ ] **Step 4: Write binding RED tests.** Stage and activate a grant at T0, consume it after expiry, then read state at the original fixture time: pending/active/calls for that grant must be absent. Stage a different tool approval under the same operation ID before old
  cleanup; assert it survives. Assert inconsistent `entry.expiresAt` versus `entry.envelope.expiresAt` is rejected. Cover malformed/linked state and failed writes with existing safe-file fixtures.
- [ ] **Step 5: Run binding RED.** Run `node --test tests/browser-operations/binding-store.test.mjs`; expected the new consumption interface is missing or expired physical records remain under the old path.
- [ ] **Step 6: Implement owned consumption.** Reuse validated bounded raw-state parsing/atomic writes/locks, keeping the ordinary current-time expiry-filtered API unchanged. Never use old time to authorize a call. `stageBrowserCall` tags newly staged call records with
  `approvalToolUseId` from the active grant; consumption removes only calls correlated to that original grant. Ambiguous older untagged calls cannot justify deleting a newer grant or claiming complete cleanup. Keep existing state version/limits and reject inconsistent grant
  expiry.
- [ ] **Step 7: Run GREEN and regression.** Run both suites plus `node --test tests/browser-operations/workflow.test.mjs`. Expected zero failures and unchanged timestamp-independent fingerprints. Add the new lifetime suite to the package gate; run the full package command
  from the companion plan, expected exit `0` and `package validation passed`.
- [ ] **Step 8: Commit:** `fix: preserve browser approval lifetime and owned consumption`.

## Task 2: Complete runner and adapter dispatch enforcement

**Files:** Modify `skills/browser-operations/scripts/browser-runner.mjs`, `skills/browser-operations/scripts/browser-adapters/common.mjs`, `skills/browser-operations/scripts/browser-adapters/playwright.mjs`, `skills/browser-operations/scripts/browser-adapters/puppeteer.mjs`,
`skills/browser-operations/scripts/browser-adapters/index.mjs`.
Create `tests/browser-operations/runner-lifetime.test.mjs`, `tests/browser-operations/lifetime-helpers.mjs`.
Extend `tests/browser-operations/runner-contract.test.mjs`, `tests/browser-operations/adapters.test.mjs`, `tests/browser-operations/real-browser.test.mjs`, `tests/validate-package.sh` as necessary for the shared factory seam.

**Interfaces:** Consume Task 1's exact API. Factory `options.operationLifetime` carries the branded lifetime; built-in adapters expose that same immutable object and the installed-enforcement capability. Existing discovery labels remain; discovery `ACTIVE` without installed
lifetime is not operational authority.
Public `executeBrowserWorkflow(request,dependencies={})` and `executeRunnerStep(request,dependencies={})` signatures remain; `dependencies.now` may now be numeric or callable. Share the same internal `OperationClock` when one public entrypoint delegates to the other.
Keep `authorizeRunnerStep(request,envelope,capability,now:number)` numeric and synchronous. Add internal `authorizeLiveStep(request,envelope,capability,lifetime)->authorization`: use `lifetime.assertLive()` as the same sample passed into that existing policy.

- [ ] **Step 1: Write adapter RED tests.** Construct adapters using the real Task 1 lifetime and existing in-memory runtime doubles. Advance time inside link `getAttribute`, inspect navigation and screenshot acquisition. Assert no later click/read/capture, closed expiry
  error and cleanup still executed. Trigger delayed interception at expiry: zero `continue`, `fetch` or `fulfill` dispatches; abort and response disposal remain allowed. Without a genuine installed lifetime, assert operational eligibility is false even if a capability flag
  says true.
- [ ] **Step 2: Run RED.** Run `node --test tests/browser-operations/adapters.test.mjs`. Expected expiry tests still dispatch the prohibited next call or lack installed lifetime identity. These are fake browser APIs, not browser execution.
- [ ] **Step 3: Implement adapter enforcement.** Validate optional factory lifetime with Task 1's brand; absence may support standalone diagnostics but cannot advertise installed enforcement. Check immediately before each page/locator/reference/artifact/network dispatch and
  after each await. Materialize an upload separately, then recheck before browser upload. Preserve origin/popup/redirect controls and failure propagation. Refresh supported runtime action/navigation timeouts to `min(existing ceiling, lifetime.remainingMs())`; never use `0`
  as an unlimited timeout. Late results throw a closed lifetime failure; close/abort/disposal bypass lifetime checks.
- [ ] **Step 4: Run adapter GREEN.** Run the adapter and lifetime suites. Expected all expiry negatives and existing origin/artifact/read-only controls pass. Audit every adapter's direct action and intercepted-request path; no async assertion or ignored closed reason is
  permitted.
- [ ] **Step 5: Write runner RED tests.** Reuse a test-only helper that stages actual PreToolUse fixture approval and builds strict adapters with the supplied lifetime. It must record exact effect/reference/close calls, not silently accept arbitrary inputs. Test literals:

```javascript
assert.equal(result.reasonCode, 'OPERATION_EXPIRED');
assert.equal(calls.includes('execution:submit'), false);
assert.equal(calls.includes('validation:verify'), false);
assert.equal(readPendingOperation(session, operation, env, originalTime), null);
assert.equal(readActiveOperation(session, operation, env, originalTime), null);
```

Stage at T0 and reparse later; expire at the original deadline while the reparsed envelope is still future. Parameterize expiry during discovery, execution open, fill/select value resolution, execution close, validation discovery/open/preparation and final expected-value
resolution. After a prior persistent action assert `status === 'outcome-unknown'` and `validationRequired === true`, no later effects/expired validation, exact cleanup. Late successful `verify` must not produce `WORKFLOW_VALIDATED`. Repeat applicable cases through
`executeRunnerStep`, including its independent validator. Assert completion/reconciliation failure cannot produce success.
- [ ] **Step 6: Run RED.** Run `node --test tests/browser-operations/runner-lifetime.test.mjs`. Expected original-deadline/callback wiring or pre-consumer call assertions fail on the old frozen/reparsed runner. Tests must differentiate an early runner rejection from a fake
  adapter protecting a late dispatch itself.
- [ ] **Step 7: Integrate the runner.** Capture the exact stored grant before async discovery; validate matching expiry copies and construct its lifetime once. Recheck at activation and every runner dispatch boundary, including before/after protected reference resolution,
  startup, sensitive verification and completion. Pass lifetime through factory options and require installed identity before use. Use stored envelope, not request expiry. Always close acquired adapters, clear temporary references and consume only the owned one-shot
  correlation using Task 1's API. Propagate the four closed lifetime reasons without logging raw errors.
- [ ] **Step 8: Preserve outcome semantics.** Track possibly persistent dispatch separately from merely attempted checks. Pre-effect expiry is denied; expiry/clock failure after possible persistence or a late result is inconclusive. Do not call validation/compensation with
  expired authority or ignore false completion/reconciliation writes. Legacy remains read-only and shares the fresh-check/late-result boundary, without acquiring one-shot auth/mutation privileges.
- [ ] **Step 9: Update strict test callers.** Existing injected adapter factories and fake adapters must install the exact supplied lifetime. Update provider-free fixtures/real-browser test definitions for this seam without running the real-browser matrix. Do not replace a
  missing guard with a constant no-op callback. Existing numeric-clock controls remain positive controls.
- [ ] **Step 10: Run GREEN and full regression.** Run each focused suite explicitly: `node --test tests/browser-operations/runner-lifetime.test.mjs`, `node --test tests/browser-operations/runner-contract.test.mjs`,
  `node --test tests/browser-operations/adapters.test.mjs`, `node --test tests/browser-operations/binding-store.test.mjs`, `node --test tests/browser-operations/operation-lifetime.test.mjs`.
  Add runner-lifetime to the gate, then run the full package command with no real-browser opt-in. Expected zero failures and `package validation passed`; capability skips are reported, not acceptance. No actual UI/native/provider probe is run.
- [ ] **Step 11: Commit:** `fix: enforce original approval deadlines at browser dispatch`.

## Task 3: Versioned contract, scoped security review and delivery evidence

**Files:** Modify `skills/browser-operations/nori.json`, `skills/browser-operations/SKILL.md`, `references/browser-operations.md`, `docs/architecture/ADR-010-browser-automation-boundary.md`, `docs/architecture/README.md`, `README.md`, `docs.md`, `CHANGELOG.md`,
`tests/validation-notes.md`.
Extend `tests/test-nori-package-contract.py`, `tests/test-subagent-frontmatter.py`, `tests/test-architecture-docs.py`, `tests/test-release-history.py` only where their actual component/contract expectations need the change.
**Interfaces:** Consume verified behavior from Tasks 1/2; retain existing root package version and all installed policy/credential ownership boundaries.

- [ ] **Step 1: Update metadata coherently.** Browser Nori component `1.0.0 -> 1.0.1`, skill metadata `0.1.0 -> 0.1.1`, and `last_updated` to implementation date. Root `0.15.0` remains unreleased. Keep canonical browser instructions consistent with the
  original-deadline/late-result contract; use `writing-skills` if changing skill instructions, without inventing authority for model-backed tests.
- [ ] **Step 2: Document enforced behavior**, installed lifetime capability, cleanup-only allowance, unknown after possible persistence, original binding consumption and inability to unsend in-flight calls. Link the approved spec and both plans from ADR-010/index. Preserve
  historical evidence and record three review findings addressed only after their actual regression proofs.
- [ ] **Step 3: Run focused/documentation GREEN.** Run lifetime/runner/binding/adapters suites, `python3 tests/validate-content.py`, `python3 tests/test-nori-package-contract.py`, `python3 tests/test-architecture-docs.py`, `python3 tests/test-release-history.py`.
  Run `git diff --check` separately. Expected zero failures and coherent root/component metadata; test-only terminal modules remain excluded from staging.
- [ ] **Step 4: Perform the required security candidate review.** Use `codex-security:fix-finding` and its artifact-storage rules. The fresh read-only pre-patch investigation at `01414cb` already traced the unchanged source; reconcile that evidence with the current candidate
  before review. Launch one fresh bypass/regression reviewer with only finding, authorized scope, repository/policy and candidate diff. Review the complete remediation range/direct callers, not all historical branch work; no edits, nested agents, provider/native reruns or
  asserted test success in the review prompt.
- [ ] **Step 5: Re-grade concrete findings and finish one fix pass.** For confirmed in-scope material bypass/regression findings, reproduce RED then fix GREEN. Preserve a written ruling for declined findings and deferred minors. No second review cycle; no unrelated redesign.
  If essential compatibility evidence is unavailable, report the security fix as blocked, not verified.
- [ ] **Step 6: Run final full verification.** Use the exact WSL package command from the companion plan with retained explicit terminal paths and no browser/live opt-in. Expected exit `0` and `package validation passed`. Verify no unrelated changes, cleanup proof, original
  trigger rejection and legitimate numeric-clock workflows; include actual skips and remaining uncertainty in the handoff.
- [ ] **Step 7: Commit:** `docs: record browser lifetime enforcement and review evidence`. Final result includes immutable commit, verified counts, original/alternate trigger RED-to-GREEN, legitimate controls, review scope and explicit remaining native/CI/Security/merge
  gates. Do not claim the entire P0-04B complete.

## Execution decision and remaining gates

Preserve the already selected Native implementation method; execute both plans
in order after operator plan review. Focused RED/GREEN checks use explicit files;
each independently completed task requires its package regression before its
completion claim. Use isolated plan ledgers; record BASE/ranges and rulings.

This is a new scoped production security correction, not an authorization to
repeat the old whole-branch review or paid acceptance. The one scoped candidate
review above fulfills this spec's additional security review; the harness plan
is the existing reviewed author fix pass. If a workflow skill would request
another broad branch review, present that conflict before dispatching extra work.

The known native offline control remains inconclusive; its repeat requires a
separate grant. The authenticated six-invocation/40-turn acceptance requires a
new final-commit-bound authorization after native prerequisites. Hosted
CI/Security, external delivery, merge and definitive TODO completion remain
unperformed and separate. See [the harness plan](2026-10-07-p0-04b-harness-review-fixes.md).
