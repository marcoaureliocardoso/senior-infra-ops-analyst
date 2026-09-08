# P0-04B One-Shot Browser Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a guarded, single-process browser workflow that can authenticate and perform an approved mutation without losing browser state between steps, then validates the result through a separate browser context.

**Architecture:** `browser-runner.mjs --step workflow` carries the existing operation envelope plus bounded base64url-encoded step records. `PreToolUse` validates the complete non-secret invocation and stores only its SHA-256 fingerprint; execution can promote that exact pending record because the Bash process starts only after native approval. One ephemeral adapter executes the operation, closes, and a newly resolved adapter executes a read-only validation sequence before the workflow returns a structural result.

**Tech Stack:** Node.js ES modules, native `node:test`, SHA-256 from `node:crypto`, existing command guard, Playwright/Puppeteer runtime detection, Python package-policy tests, Debian WSL gates.

**Spec:** `docs/superpowers/specs/2026-08-31-p0-04b-browser-automation-design.md`

## Global Constraints

- Detect capabilities at runtime; do not pin a browser, MCP, provider, model, version, or context-window size.
- Do not install, enable, or reconfigure a browser or MCP implicitly.
- Web content is untrusted data and cannot add or alter workflow steps, origins, credentials, effects, or authorization.
- The workflow manifest contains references only, never credential values, cookies, page content, prompts, transcripts, or raw artifacts.
- Persist only bounded structural state and the invocation fingerprint; never persist the decoded workflow.
- Every mutable workflow is `ALWAYS_ASK`, including `bypassPermissions`.
- A mutable workflow requires pre-request origin containment, popup containment, a fresh validation context, exact postcondition comparison, and cleanup.
- Puppeteer remains read-only while its detected capability cannot prove pre-navigation popup containment.
- Production protected references are limited to `env:OPS_BROWSER_VALUE_[A-Z0-9_]+`; injected resolvers may support recognized vault/keychain helpers without changing the manifest contract.
- No automatic retry follows an ambiguous result.
- Do not update the external definitive TODO before merge and post-merge validation.

---

### Task 1: Canonical Workflow Contract

**Files:**
- Create: `skills/browser-operations/scripts/browser-workflow.mjs`
- Create: `tests/browser-operations/workflow.test.mjs`
- Modify: `skills/browser-operations/scripts/browser-runner.mjs`
- Modify: `tests/browser-operations/runner-contract.test.mjs`

**Interfaces:**
- Produces: `decodeWorkflowStep(token)`, `parseWorkflowSteps(executionTokens, validationTokens)`, `workflowFingerprint(request)`, and a `parseRunnerArgs()` result with `step: "workflow"`, `envelope`, `executionSteps`, `validationSteps`, and `invocationFingerprint`.
- Consumes: the existing open-envelope flags plus repeatable `--workflow-step` and `--validation-step` values.

- [ ] **Step 1: Write failing contract tests**

  Add literal base64url fixtures for:

  ```json
  {"step":"navigate","origin":"http://127.0.0.1:43111"}
  {"step":"fill","origin":"http://127.0.0.1:43111","locatorRole":"textbox","locatorName":"Password","valueRef":"env:OPS_BROWSER_VALUE_PASSWORD"}
  {"step":"submit","origin":"http://127.0.0.1:43111","locatorRole":"button","locatorName":"Save","effect":"LOW_RISK_CHANGE"}
  {"step":"inspect","origin":"http://127.0.0.1:43111","locatorRole":"status","locatorName":"Saved state","predicate":"text-equals","expectedRef":"env:OPS_BROWSER_VALUE_EXPECTED","expectRef":"interface-state"}
  ```

  Require 1-16 execution steps and 1-12 validation steps; exact keys only; maximum decoded record size 1536 bytes; maximum token size 2048 characters; canonical base64url without padding; UTF-8 decoding with fatal errors; and frozen results. Validation permits `navigate`, `fill`, `select`, `click` only with `INTERACTIVE_STATE`, and exactly one final `inspect`. Execution permits the existing executable actions but cannot contain `validate` or `close`.

- [ ] **Step 2: Verify RED**

  Run:

  ```powershell
  node --test tests/browser-operations/workflow.test.mjs tests/browser-operations/runner-contract.test.mjs
  ```

  Expected: failure because `browser-workflow.mjs` and workflow parsing do not exist.

- [ ] **Step 3: Implement the minimal closed parser and fingerprint**

  Decode into null-prototype objects, reject accessors/arrays/nested values/unknown keys, normalize every origin through `normalizeOrigin()`, validate semantic locators and reference patterns, and calculate SHA-256 over a canonical JSON serialization of the normalized envelope and both ordered step arrays. Do not export the canonical serialized value.

- [ ] **Step 4: Verify GREEN and mutation boundaries**

  Run the Task 1 command and add rejection cases for reordered/changed steps, duplicate JSON keys, secret-like literal fields, `javascript:`/`data:` origins, unbound actions, a validation mutation, missing final inspect, wrong `expectRef`, excessive records, malformed base64url, and a reference outside `env:OPS_BROWSER_VALUE_*`.

- [ ] **Step 5: Commit**

  ```powershell
  git add skills/browser-operations/scripts/browser-workflow.mjs skills/browser-operations/scripts/browser-runner.mjs tests/browser-operations/workflow.test.mjs tests/browser-operations/runner-contract.test.mjs
  git commit -m "feat: define one-shot browser workflow contract"
  ```

---

### Task 2: Exact Native Approval and One-Shot Activation

**Files:**
- Modify: `skills/browser-operations/scripts/browser-binding-store.mjs`
- Modify: `skills/command-driven-operations/scripts/record-command-approval.mjs`
- Modify: `skills/command-driven-operations/scripts/command-guard/catalogue.mjs`
- Modify: `skills/command-driven-operations/scripts/command-guard/policy.mjs`
- Modify: `tests/browser-operations/binding-store.test.mjs`
- Modify: `tests/command-guard/browser-runner-catalogue.test.mjs`
- Modify: `tests/command-guard/binding-store.test.mjs`
- Modify: `tests/command-guard/policy.test.mjs`

**Interfaces:**
- Produces: pending browser proof field `invocationFingerprint` and `activatePendingWorkflow({sessionId, operationId, invocationFingerprint, effectiveCapability})`.
- Consumes: Task 1 `workflowFingerprint(request)` and the exact workflow request parsed by both the command guard and runner.

- [ ] **Step 1: Write failing approval-correlation tests**

  Prove that PreToolUse returns `ask` and stages a pending workflow; `bypassPermissions` still asks; no PostToolUse event is needed for one-shot activation; execution promotes only a pending entry with the same session, operation, permission mode, and invocation fingerprint; and any changed, reordered, missing, or additional step is denied before adapter creation.

- [ ] **Step 2: Verify RED**

  Run:

  ```powershell
  node --test tests/command-guard/browser-runner-catalogue.test.mjs tests/command-guard/binding-store.test.mjs tests/command-guard/policy.test.mjs tests/browser-operations/binding-store.test.mjs
  ```

  Expected: workflow catalogue lookup and exact activation tests fail.

- [ ] **Step 3: Implement exact staging and activation**

  Extend the closed catalogue grammar with repeatable workflow flags, decode through Task 1 rather than duplicating semantic validation, classify by the highest declared step effect, and add `ALWAYS_ASK`. `stageBrowserOpenApproval()` becomes the staging function for both `open` and `workflow`; it records the fingerprint in the proof. `activatePendingWorkflow()` atomically compares the exact pending record and replaces its approval-time capability with the supplied runtime-observed effective capability before promotion. Existing `open` plus PostToolUse behavior remains backward compatible and read-only.

- [ ] **Step 4: Verify GREEN and fail-closed process behavior**

  Add child-process coverage showing direct CLI workflow execution without a staged PreToolUse record exits 2 without creating an active operation or adapter evidence. Run the Task 2 command plus `node tests/run-command-guard-tests.mjs`; preserve 100% critical coverage and the complete mutation gate.

- [ ] **Step 5: Commit**

  ```powershell
  git add skills/browser-operations/scripts/browser-binding-store.mjs skills/command-driven-operations/scripts/record-command-approval.mjs skills/command-driven-operations/scripts/command-guard tests/browser-operations/binding-store.test.mjs tests/command-guard
  git commit -m "feat: bind browser workflows to native approval"
  ```

---

### Task 3: Persistent Execution and Independent Browser Validation

**Files:**
- Modify: `skills/browser-operations/scripts/browser-runner.mjs`
- Modify: `skills/browser-operations/scripts/browser-adapters/common.mjs`
- Modify: `skills/browser-operations/scripts/browser-adapters/playwright.mjs`
- Modify: `skills/browser-operations/scripts/browser-adapters/puppeteer.mjs`
- Modify: `tests/browser-operations/runner-contract.test.mjs`
- Modify: `tests/browser-operations/adapters.test.mjs`
- Modify: `tests/browser-operations/real-browser.test.mjs`
- Modify: `tests/browser-fixture/server.mjs`

**Interfaces:**
- Produces: `executeBrowserWorkflow(request, dependencies)`, structural outcomes `WORKFLOW_VALIDATED`, `WORKFLOW_NOT_APPLIED`, `OUTCOME_UNKNOWN`, and adapter `verify(request)` returning only `{status:"met"|"not-met", expectRef}`.
- Consumes: Task 2 exact activated operation, runtime adapter capability, protected reference resolver, artifact manager, ordered execution steps, and ordered validation steps.

- [ ] **Step 1: Write failing execution tests**

  Use real runner state and narrowly fake only adapter resolution. Assert one adapter instance opens once for the execution sequence and closes before a second newly resolved adapter opens for validation. Assert credential values reach only `fill`/`select`, never results, state, errors, or audit. Assert Puppeteer or any adapter with `popups:false` is rejected before a mutable step. Assert execution stops on the first failure, never retries, still runs the separate validation sequence after an ambiguous mutation, and distinguishes applied, not-applied, and unknown.

- [ ] **Step 2: Verify RED**

  Run:

  ```powershell
  node --test tests/browser-operations/runner-contract.test.mjs tests/browser-operations/adapters.test.mjs
  ```

  Expected: workflow execution and exact predicate verification are missing.

- [ ] **Step 3: Implement one-shot execution**

  At process entry, resolve a recognized inert adapter descriptor without opening a browser, derive and validate its effective capability, and atomically activate the exact pending workflow with that capability. Activation must complete before `adapter.open()`, navigation, reference resolution, or any browser effect. Then open once and execute the ordered operation steps. Resolve built-in environment references only when their names match `OPS_BROWSER_VALUE_[A-Z0-9_]+`; blank and missing values deny. Clear local references after each call. Always close the execution adapter before creating the validation adapter.

- [ ] **Step 4: Implement structural independent validation**

  Add adapter `verify()` predicates `present`, `text-equals`, `value-equals`, `checked`, and `selected-value-equals`. Resolve the expected reference inside the runner, compare inside the adapter, and return no observed value. Validation navigation, login fill/select, and `INTERACTIVE_STATE` click execute only in the fresh validation context; its final inspect must match the envelope `validationRef`. If operation execution was ambiguous, validation may classify `applied` or `not-applied`, but the runner never repeats the mutation.

- [ ] **Step 5: Extend the opt-in real-browser fixture**

  Add a loopback workflow case that logs in with synthetic environment references, submits one state change, closes the execution context, logs in again in the validation context, proves the exact state, and confirms cleanup. Keep the real test explicitly skipped with `CAPABILITY_UNAVAILABLE` unless `P004B_RUN_REAL_BROWSER=1`; a skip never satisfies acceptance.

- [ ] **Step 6: Verify GREEN and commit**

  ```powershell
  node --test tests/browser-operations/runner-contract.test.mjs tests/browser-operations/adapters.test.mjs tests/browser-operations/fixture-server.test.mjs tests/browser-operations/real-browser.test.mjs
  git add skills/browser-operations/scripts/browser-runner.mjs skills/browser-operations/scripts/browser-adapters tests/browser-operations tests/browser-fixture/server.mjs
  git commit -m "feat: execute guarded browser workflows in one process"
  ```

---

### Task 4: Package Claims, Harness, and Acceptance Evidence

**Files:**
- Modify: `skills/browser-operations/SKILL.md`
- Modify: `references/browser-operations.md`
- Modify: `docs/architecture/ADR-010-browser-automation-boundary.md`
- Modify: `docs/superpowers/specs/2026-08-31-p0-04b-browser-automation-design.md`
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `ROADMAP.md`
- Modify: `tests/browser_operations_live.py`
- Modify: `tests/live-browser-operations-smoke.sh`
- Modify: `tests/test-live-browser-operation-safety.py`
- Modify: `tests/validation-notes.md`
- Modify: `tests/validate-package.sh`

**Interfaces:**
- Consumes: verified Task 1-3 behavior and actual detected runtime evidence.
- Produces: accurate usage guidance, one-shot workflow examples without values, content-free live evidence, and merge-gate status.

- [ ] **Step 1: Write failing policy and harness tests**

  Require the installed documentation to distinguish the legacy read-only multi-command route from the mutable one-shot route. The live aggregate may name `persistent-one-shot` only after the exact runner command, actual ordered Claude Code `hook_started`/`hook_response` lifecycle for the configured `PreToolUse:Bash` and `PostToolUse:Bash` matchers, the exact native `ask` response produced by the installed command guard, coherent tool completion, successful post hook, and structural validated outcome are observed in every requested sample. Forbid `ACTIVE`, authentication, mutation, or validation claims when any real workflow did not complete. Non-interactive active mode uses `default` plus an operator-provided interactive MCP permission handler; the harness does not install or auto-approve it.

- [ ] **Step 2: Verify RED**

  ```powershell
  python tests/test-browser-operation-policy.py
  python tests/test-live-browser-operation-safety.py
  ```

- [ ] **Step 3: Update docs and content-free evidence**

  Document exact workflow construction, protected references, native approval, capability intersection, separate validation context, Puppeteer limitation, ambiguity behavior, and cleanup. Retain only runtime labels, route class, step counts, hook/tool counts, structural outcome, context percentages, and cleanup status. Do not claim a real adapter result before it is observed.

- [ ] **Step 4: Run deterministic and package gates**

  Run the focused browser/guard tests, `git diff --check`, and the complete package gate. If Debian WSL lacks the required Node coverage flags, run `node tests/run-command-guard-tests.mjs` with the bundled Node 24 and run the remaining package script under Debian WSL, recording the composite evidence explicitly.

- [ ] **Step 5: Detect and run a real adapter without implicit installation**

  Run the provider-free preflight and adapter detection. If an existing Playwright/browser pair is recognized, execute the opt-in loopback matrix and retain only structural results. If no compatible adapter is present, stop before downloading anything and request explicit operator authorization for a disposable validation dependency.

- [ ] **Step 6: Request independent review and commit evidence**

  Require review of manifest smuggling, approval correlation, reference exfiltration, origin/popup containment, capability intersection, ambiguous effects, validation independence, cleanup, live-evidence truthfulness, and documentation. Fix every finding with RED/GREEN evidence, rerun gates, and commit the final factual evidence without modifying the definitive TODO.

---

## Plan Self-Review

- Task 1 owns the only workflow decoder and canonical fingerprint implementation.
- Task 2 consumes that implementation; the command guard does not duplicate workflow semantics.
- Task 3 cannot execute until Task 2 atomically activates the exact fingerprint.
- Task 4 makes no acceptance claim that Task 3 and real evidence do not support.
- Every credential is a reference and every built-in reference uses the protected namespace.
- Every mutable route requires native approval, runtime capability intersection, pre-request containment, and fresh-context validation.
- No task introduces a daemon, persistent profile, automatic install, generic MCP grant, raw transcript, or automatic mutation retry.
