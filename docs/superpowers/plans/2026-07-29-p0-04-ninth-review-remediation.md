# P0-04 Ninth Review Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the eight PR #25 authorization defects without weakening the native fail-closed command guard or pinning any runtime.

**Architecture:** Preserve the public policy result and native hook response while adding closed client parsers and a credential-consumer binding projection. Aggregate risk remains composition-wide; credential scope comes only from the one accepted consumer stage.

**Tech Stack:** ECMAScript modules, Node.js native tests and coverage, deterministic mutation witnesses, Python repository validators, Bash launcher, Debian/WSL, and Nori installed-artifact validation.

## Global Constraints

- Implement `docs/superpowers/specs/2026-07-29-p0-04-ninth-review-remediation-design.md`.
- Do not pin Claude Code, Nori, DeepSeek, Node.js, or any model/runtime version.
- Unknown, incomplete, repeated, dynamic, opaque, or unconsumed syntax fails closed.
- Destructive actions ask in every mode; local-file and external effects retain mandatory confirmation.
- Never persist or emit raw commands, credentials, request bodies, or secret-derived identifiers.
- Add tests before production changes and observe the expected RED for every defect.

---

### Task 1: Bind credentials to the actual consumer stage

**Files:**
- Modify: `tests/command-guard/binding-store.test.mjs`
- Modify: `tests/command-guard/security-regressions.test.mjs`
- Modify: `skills/command-driven-operations/scripts/command-guard/policy.mjs`
- Modify: `skills/command-driven-operations/scripts/command-guard/binding-store.mjs`

**Interfaces:**
- `analyzeCommand()` produces `credentialBinding: { domain, family, targetClass } | null`.
- `bindingFromResult()` consumes only `result.credentialBinding` for scope.

- [ ] Add a lifecycle test that approves `kubectl change ; authenticated curl api-a` and asserts `kubectl change ; authenticated curl api-b` still asks.
- [ ] Run the focused binding tests and observe the second call incorrectly return `allow`.
- [ ] Track the exact credential consumer during stage analysis and derive the non-secret binding projection from it.
- [ ] Reject literal credential compositions without exactly one supported consumer.
- [ ] Run binding and credential-flow tests until green.

### Task 2: Close opaque and multi-source command parsers

**Files:**
- Modify: `tests/command-guard/security-regressions.test.mjs`
- Modify: `skills/command-driven-operations/scripts/command-guard/catalogue.mjs`

**Interfaces:**
- Private parsers return a fully consumed invocation object or `null`.

- [ ] Add failing tests for repeated/extra `mongosh --eval`, `--file`, and positional scripts.
- [ ] Add failing tests for `ip -batch` and `ip -b` command files.
- [ ] Add failing tests for `scp` execution/config overrides and `sftp` batch files.
- [ ] Add failing tests for `tcpdump -w`, `-z`, and unsupported opaque inputs.
- [ ] Run only the new regression names and observe each unsafe form receive `allow` or an insufficient `ask`.
- [ ] Implement separate closed parsers for MongoDB, ip, scp, sftp, tcpdump, and tshark.
- [ ] Run the focused security and branch suites until green.

### Task 3: Correct nested container, Git sink, and dmesg effects

**Files:**
- Modify: `tests/command-guard/security-regressions.test.mjs`
- Modify: `tests/command-guard/policy.test.mjs`
- Modify: `skills/command-driven-operations/scripts/command-guard/catalogue.mjs`

**Interfaces:**
- `parseCtrInvocation(words)` derives the nested image verb and complete operands.
- Git read parsers return canonical file effects through the existing output-path resolver.

- [ ] Add failing tests for `ctr images pull`, import, and removal risk.
- [ ] Add failing tests for `git diff --output` plus dynamic and external-diff forms.
- [ ] Add failing tests for dmesg clear/read-clear and console-control actions in both permission modes.
- [ ] Run the focused tests and record the current SAFE_READ_ONLY outcomes.
- [ ] Split `ctr` from Docker-compatible parsing and classify its exact nested verbs.
- [ ] Close Git read options; model supported output sinks and deny execution hooks.
- [ ] Parse dmesg actions before read selectors and apply destructive/disruptive risks.
- [ ] Run catalogue, policy, output-path, and security suites until green.

### Task 4: Register stable fixtures and mutation witnesses

**Files:**
- Modify: `tests/command-guard/review-regression-fixtures.mjs`
- Modify: `tests/command-guard/coverage-fixtures.mjs`
- Modify: `tests/command-guard/mutations.mjs`
- Modify: `tests/command-guard/mutation-witnesses.mjs`
- Modify: `skills/command-driven-operations/scripts/command-guard/policy.mjs`

**Interfaces:**
- Every new security predicate has one exact source mutation and one matching witness.
- Review fixtures execute against source and installed scripts.

- [ ] Add one stable fixture per reproduced defect with literal expected decision, risk, target, and modifiers.
- [ ] Run fixture-ledger tests and observe missing execution/inventory failures where applicable.
- [ ] Register security predicate IDs for consumer binding and each parser/effect closure.
- [ ] Add one-site mutations, then run registry tests and observe missing witness failures.
- [ ] Add semantic witnesses and verify pristine success plus mutant-specific assertion failure.
- [ ] Run installed-corpus and mutation suites until green.

### Task 5: Update architecture and execute final verification

**Files:**
- Modify: `docs/architecture/ADR-004-native-command-guard.md`
- Modify: `docs/reviews/2026-07-26-pr-25-independent-review.md`
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: this plan and its paired design specification.

**Interfaces:**
- Documentation records observed evidence as observations, never requirements.

- [ ] Record the ninth review findings and dispositions in the review log.
- [ ] Amend ADR-004 with consumer-stage binding and the closed client grammars.
- [ ] Update README and the existing `0.11.0` changelog entry without changing version.
- [ ] Run `node tests/run-command-guard-tests.mjs` and record exact totals.
- [ ] Run all Python, PowerShell, WSL, package, and installed-artifact gates used by PR #25.
- [ ] Run `git diff --check`, inspect every changed file, and verify no artifacts or unchecked plan boxes remain.
- [ ] Request a fresh independent read-only review before merge.
