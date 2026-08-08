# P0-04 Fifth Review Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the remaining credential-binding, singleton-precedence, Docker transport, and raw/cooked redaction gaps found by the fifth independent review.

**Architecture:** Reject ambiguous command structure before authorization.
Distinct literal credential transports in one command deny, repeated allowed
environment assignments and Redis singleton selectors deny, Docker remote
selectors deny in every spelling, and token-aware raw spans cover the complete
shell token that forms a credential argument. The same stable fixtures run
against source and installed artifacts.

**Tech Stack:** JavaScript ESM, Node.js native test runner and coverage, Python validators, Bash/WSL package validation.

## Global Constraints

- Do not pin Claude Code, Nori, DeepSeek, or runtime versions.
- Preserve bounded executor operation in `bypassPermissions`.
- Destructive commands always ask; unknown or ambiguous commands deny.
- A new literal credential transport must never reuse another transport's approval.
- Policy, audit, and binding must describe the effective command target and identity.
- Secret fragments must not survive redaction, response, audit, state, or installed-form tests.

---

### Task 1: Add RED regressions

**Files:**
- Modify: `tests/command-guard/binding-store.test.mjs`
- Modify: `tests/command-guard/security-regressions.test.mjs`
- Modify: `tests/command-guard/credential-flow.test.mjs`
- Modify: `tests/command-guard/review-regression-fixtures.mjs`

- [x] Reproduce Authorization approval followed by a command containing Authorization plus a new Cookie and require `deny`.
- [x] Reproduce duplicate `AWS_PROFILE`, duplicate `OPS_CREDENTIAL_IDENTITY`, and duplicate Redis host selectors and require `deny`.
- [x] Reproduce Docker `-H <host>` in both permission modes and require `deny`.
- [x] Assert that concatenated quoted credential tokens are completely removed by `redactText`.
- [x] Execute targeted tests on the unfixed implementation and confirm failures match the review evidence.

### Task 2: Enforce one effective binding structure

**Files:**
- Modify: `skills/command-driven-operations/scripts/command-guard/catalogue.mjs`
- Modify: `skills/command-driven-operations/scripts/command-guard/credential-flow.mjs`
- Modify: `skills/command-driven-operations/scripts/command-guard/policy.mjs`
- Modify: `tests/command-guard/coverage-fixtures.mjs`

- [x] Reject repeated allowed environment assignment names before locating the executable.
- [x] Reject duplicate Redis host, port, database, password, and user selectors before deriving verb/domain.
- [x] Reject exact separated Docker `-H` as well as compact and equals spellings.
- [x] Add an operator-visible deny reason for multiple distinct literal credential transports.
- [x] Run targeted policy, binding, coverage-inventory, and security tests until green.

### Task 3: Redact complete raw tokens

**Files:**
- Modify: `skills/command-driven-operations/scripts/command-guard/redaction.mjs`
- Modify: `tests/command-guard/branches.test.mjs`
- Modify: `tests/command-guard/credential-flow.test.mjs`

- [x] Derive supplementary spans from Bash lexer raw-token boundaries for accepted curl and Redis credential options.
- [x] Cover separated, attached, equals, compact, mixed-quote, escaped, and malformed standalone redaction input.
- [x] Preserve exact transport kinds so distinct-transport denial remains deterministic.
- [x] Run credential, redaction, property, entrypoint, and binding lifecycle tests until green.

### Task 4: Document and verify

**Files:**
- Modify: `docs/architecture/ADR-004-native-command-guard.md`
- Modify: `docs/reviews/2026-07-26-pr-25-independent-review.md`
- Modify: `CHANGELOG.md`
- Modify if needed: `README.md`

- [x] Record the independent findings and implemented decisions without replacing historical verdicts.
- [x] Add stable installed-corpus fixture IDs for every executable regression.
- [x] Run the full Node coverage/mutation gate, package validators, host PowerShell syntax, and `git diff --check`.
- [x] Validate a temporary Nori-installed artifact without starting Claude or reading global credential files.
- [x] Inspect the final diff for secrets, generated files, unrelated edits, and version pins.
