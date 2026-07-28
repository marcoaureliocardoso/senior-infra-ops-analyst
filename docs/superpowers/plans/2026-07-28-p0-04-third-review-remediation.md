# P0-04 Third Review Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the four credential and destination binding gaps found in the latest PR #25 review.

**Architecture:** Keep the existing finite command catalogue and owner-only binding store. Move missing literal recognition into parser-aligned patterns, exclude the explicit identity marker, and fail closed on HTTP or Kubernetes route/trust overrides that the current domain record cannot represent.

**Tech Stack:** Node.js ESM, native `node:test`, Claude Code native hooks, Bash/WSL validation, Python package tests.

## Global Constraints

- Preserve the standard Claude Code plus Nori runtime with no daemon or proxy.
- Do not pin Claude Code, Nori, or DeepSeek versions.
- Every first literal credential use asks, including in `bypassPermissions`.
- Reuse requires exact session, domain, identity, transport, family, and target class.
- Unknown or unmodelled syntax fails closed without exposing raw commands or secrets.
- Production changes follow a witnessed red-green TDD cycle.

---

### Task 1: Credential classification and transport binding

**Files:**
- Modify: `tests/command-guard/credential-flow.test.mjs`
- Modify: `tests/command-guard/binding-store.test.mjs`
- Modify: `tests/command-guard/security-regressions.test.mjs`
- Modify: `skills/command-driven-operations/scripts/command-guard/redaction.mjs`

**Interfaces:**
- Consumes: `detectSensitiveSpans(text)` and `evaluateHook(raw, env)`.
- Produces: exact `AUTHORIZATION`, `COOKIE`, `BASIC_AUTH`, or `FLAG` metadata for accepted literal forms.

- [ ] **Step 1: Add failing real-behavior tests**

  Add literal cases for curl OAuth bearer, compact/equal basic auth, generic
  Authorization schemes, and Redis password forms. Assert first-use `ask`, no
  secret in serialized results, and identity-only input has no credential.
  Add a hook lifecycle test that approves Authorization and asserts Cookie
  still returns `ask`.

- [ ] **Step 2: Run the focused tests and observe the expected failures**

  Run:

  ```text
  node --test tests/command-guard/credential-flow.test.mjs tests/command-guard/binding-store.test.mjs tests/command-guard/security-regressions.test.mjs
  ```

  Expected: assertions show current `allow`, `credential: null`, or cross-
  transport reuse.

- [ ] **Step 3: Implement minimal parser-aligned literal recognition**

  Exclude `OPS_CREDENTIAL_IDENTITY` from variable credential acceptance. Add
  exact patterns for the accepted curl and Redis spellings without broadening
  benign lookalikes.

- [ ] **Step 4: Run the focused tests until green**

  Run the same Node test command and require zero failures.

### Task 2: HTTP and Kubernetes route closure

**Files:**
- Modify: `tests/command-guard/security-regressions.test.mjs`
- Modify: `tests/command-guard/review-regression-fixtures.mjs`
- Modify: `skills/command-driven-operations/scripts/command-guard/catalogue.mjs`

**Interfaces:**
- Consumes: `lookupFamily(stage)` and `analyzeCommand(event)`.
- Produces: fail-closed classification for unbound route, trust, credential, impersonation, and plugin options.

- [ ] **Step 1: Add failing route and trust regressions**

  Assert denial for curl resolve/proxy/insecure forms and kubectl server,
  token, client certificate, client key, CA, insecure TLS, impersonation,
  credential plugin, and config overrides. Include separated and equals forms,
  normal and bypass modes, plus accepted controls.

- [ ] **Step 2: Run focused tests and observe the expected failures**

  Run:

  ```text
  node --test tests/command-guard/security-regressions.test.mjs tests/command-guard/executable-fixtures.test.mjs
  ```

  Expected: current route-override commands return `allow` or `ask` instead of
  `deny`.

- [ ] **Step 3: Implement closed option handling**

  Remove unbound curl route/trust options from the accepted schema. Add a
  kubectl option validator that consumes every option and value, denies unknown
  or control-plane overrides, and leaves existing finite verb semantics intact.

- [ ] **Step 4: Run the focused tests until green**

  Run the same Node test command and require zero failures.

### Task 3: Documentation and full verification

**Files:**
- Modify: `docs/architecture/ADR-004-native-command-guard.md`
- Modify: `docs/reviews/2026-07-26-pr-25-independent-review.md`
- Modify: `CHANGELOG.md`
- Modify if required: `README.md`
- Modify if required: `references/command-execution-protocol.md`

**Interfaces:**
- Consumes: the final executable behavior and observed validation output.
- Produces: an accurate versioned architecture and review verdict.

- [ ] **Step 1: Update versioned decisions and verdict**

  Record parser-derived credential transport, fail-closed route overrides,
  closed kubectl options, reproductions, and the remaining independent-review
  requirement. Do not claim readiness before the complete gate passes.

- [ ] **Step 2: Provide a compatible Linux Node runtime**

  Inspect the WSL architecture and available version managers. Prefer a
  user-local official Node distribution over replacing Debian system packages.
  Confirm `node --help` exposes every coverage flag required by
  `tests/run-command-guard-tests.mjs`.

- [ ] **Step 3: Run complete verification**

  Execute `./tests/validate-package.sh` in WSL with the compatible runtime,
  then rerun the direct adversarial reproductions. Require exit zero and no
  dirty generated files.

- [ ] **Step 4: Review and publish the PR update**

  Inspect the complete diff, verify the worktree is clean after commit, push
  the existing PR branch, and confirm the published head and GitHub checks.
