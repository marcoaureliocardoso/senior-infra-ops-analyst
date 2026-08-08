# P0-04 Second Review Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close all six authorization gaps reproduced in the current review of
PR #25 while preserving bounded operational execution in `bypassPermissions`.

**Architecture:** Tighten the existing deterministic Node.js grammar at the
earliest parser boundary, then enforce client-specific closed schemas in the
catalogue. Every finding is represented by an executable fixture and direct
policy assertions.

**Tech Stack:** Node.js ESM, `node:test`, Bash validation harness, Markdown ADRs.

## Global Constraints
- Do not pin Claude Code, Nori, or the DeepSeek model version.
- Do not add a runtime dependency beyond the standard Node.js dependency.
- Unknown, ambiguous, dynamic, and unbounded forms deny in every mode.
- Destructive commands continue to ask in every mode.
- Credentials and raw commands never enter audit records or explanations.

---

### Task 1: PowerShell and environment execution controls
**Files:**
- Modify: `tests/command-guard/lexer.test.mjs`
- Modify: `tests/command-guard/security-regressions.test.mjs`
- Modify: `tests/command-guard/review-regression-fixtures.mjs`
- Modify: `skills/command-driven-operations/scripts/command-guard/powershell-lexer.mjs`
- Modify: `skills/command-driven-operations/scripts/command-guard/catalogue.mjs`

- [ ] Add literal expected-decision tests for nested PowerShell expressions and
  execution-control assignments, including quoted non-executable parentheses.
- [ ] Run the focused tests and confirm the unsafe commands are currently
  `allow` rather than `deny`.
- [ ] Reject unquoted dynamic PowerShell expression syntax and remove control
  variables from the catalogued assignment prefix.
- [ ] Run the focused tests and confirm every new assertion passes.

### Task 2: HTTP and SSH client schemas
**Files:**
- Modify: `tests/command-guard/security-regressions.test.mjs`
- Modify: `tests/command-guard/review-regression-fixtures.mjs`
- Modify: `skills/command-driven-operations/scripts/command-guard/catalogue.mjs`

- [ ] Add failing cases for curl file-backed separated, equals-attached, and
  compact values plus executable SSH options in split and attached form.
- [ ] Run the focused tests and observe the current autonomous decisions.
- [ ] Add one option-value parser, deny local HTTP request sources, and replace
  the SSH execution-option denylist with a closed literal allowlist.
- [ ] Run the focused tests and retain accepted literal HTTP bodies and ordinary
  SSH transport options.

### Task 3: Kubernetes sensitive and finite reads
**Files:**
- Modify: `tests/command-guard/security-regressions.test.mjs`
- Modify: `tests/command-guard/review-regression-fixtures.mjs`
- Modify: `skills/command-driven-operations/scripts/command-guard/catalogue.mjs`

- [ ] Add failing assertions for raw secret URIs, follow, watch, watch-only, and
  pagination-disabling forms.
- [ ] Run the focused tests and observe the current `allow` decisions.
- [ ] Deny raw endpoints and unbounded streaming/pagination options before risk
  classification.
- [ ] Run the focused tests and confirm finite tails and scoped gets still pass.

### Task 4: Architecture and review records
**Files:**
- Modify: `docs/architecture/ADR-004-native-command-guard.md`
- Modify: `docs/reviews/2026-07-26-pr-25-independent-review.md`
- Modify: `docs/reviews/README.md`
- Modify: `CHANGELOG.md`

- [ ] Record the tightened execution boundary and the six reproduced gaps.
- [ ] Change the independent-review verdict from merge authorization to
  remediation pending, preserving the historical evidence.
- [ ] Confirm version `0.11.0` remains consistent across package metadata.

### Task 5: Verification
**Files:**
- Verify: all changed production, test, and documentation files.

- [ ] Run the focused Node.js command-guard suite.
- [ ] Run `bash tests/validate-package.sh` and require exit code zero.
- [ ] Re-run every original reproduction directly against `analyzeCommand`.
- [ ] Inspect `git diff --check`, repository status, and the final diff for
  secret material or unrelated changes.
