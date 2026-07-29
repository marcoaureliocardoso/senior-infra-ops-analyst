# P0-04 Redis Binding Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close Redis trust and approval-domain bypasses with a closed CLI schema and canonical non-secret binding.

**Architecture:** Validate the complete Redis option grammar before verb classification, then derive one canonical environment from transport, host, port, database, and user. Existing generic audit and binding layers consume that environment, while unknown route/trust behavior denies.

**Tech Stack:** JavaScript ESM, Node.js native test runner and coverage, Python validators, Bash/WSL package validation.

## Global Constraints

- Do not pin Claude Code, Nori, DeepSeek, or runtime versions.
- Preserve plain TCP and system-trust TLS Redis operation.
- Preserve useful non-destructive autonomy in `bypassPermissions`.
- Destructive commands always ask; unknown, ambiguous, or unbound commands deny.
- Store no credential value, hash, raw command, or secret-derived identifier.

---

### Task 1: Witness the Redis bypasses RED

**Files:**
- Modify: `tests/command-guard/binding-store.test.mjs`
- Modify: `tests/command-guard/security-regressions.test.mjs`
- Modify: `tests/command-guard/review-regression-fixtures.mjs`

**Interfaces:**
- Consumes: `evaluateHook`, `evaluateApprovalHook`, and `analyzeCommand`.
- Produces: executable expectations for TLS trust and canonical Redis scope.

- [x] Add a lifecycle test that approves `--tls` and requires a later `--tls --insecure` call to deny.
- [x] Add lifecycle transitions for port, database, and user and require a new `ask` for each.
- [x] Add direct policy cases for unknown and route/trust-changing Redis options in both modes.
- [x] Add stable source-to-installed fixtures for the reproduced bypasses.
- [x] Run the targeted tests and witness failures caused by the current permissive parser and host-only binding.

### Task 2: Close the Redis grammar and binding domain

**Files:**
- Modify: `skills/command-driven-operations/scripts/command-guard/catalogue.mjs`
- Modify: `tests/command-guard/branches.test.mjs`
- Modify: `tests/command-guard/security-regressions.test.mjs`

**Interfaces:**
- Consumes: Redis `stage.argv`, `option`, `repeatedOptionGroup`, and `result`.
- Produces: a REDIS result whose `environment` is `redis+<transport>://<user>@<host>:<port>/<db>` and contains no secret.

- [x] Implement a closed Redis option validator for `-h/--host`, `-p/--port`, `-n/--db`, `-a/--pass`, `--user`, and `--tls`.
- [x] Reject compact route selectors, repeated singleton groups, missing values, unknown flags, URI/socket/cluster behavior, insecure/trust/client-certificate/SNI controls, and special modes.
- [x] Validate literal host/user plus bounded numeric port and database values.
- [x] Derive explicit defaults and the canonical non-secret environment.
- [x] Run targeted policy and binding tests until green.

### Task 3: Document and verify installed behavior

**Files:**
- Modify: `docs/architecture/ADR-004-native-command-guard.md`
- Modify: `docs/reviews/2026-07-26-pr-25-independent-review.md`
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `tests/command-guard/coverage-fixtures.mjs` if the finite inventory changes.

**Interfaces:**
- Consumes: final Redis behavior and stable review fixtures.
- Produces: versioned decision/evidence and source-to-installed validation.

- [x] Record the independent verdict and local remediation without overwriting historical findings.
- [x] Update the ADR, README, and Changelog with the closed schema and canonical binding.
- [x] Run the complete coverage/mutation and package gates with capability-qualified Node.
- [x] Validate host PowerShell syntax and a temporary Nori-installed artifact without starting Claude.
- [x] Run `git diff --check`, secret/version-pin scans, and inspect the final status.
