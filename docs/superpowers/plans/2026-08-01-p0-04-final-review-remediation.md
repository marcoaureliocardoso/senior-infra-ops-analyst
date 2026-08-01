# P0-04 Final Review Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close RV61, RV64, and RV65 with stage-exact credential binding, complete SSH endpoint identity, and precise packet-capture sink parsing.

**Architecture:** Preserve lexical source intervals through composition, derive sensitive-stage ownership from those intervals, and require the owning stage to be the credential consumer. Parse SSH and capture options into canonical singleton selector groups so the policy and audit identity describe the effective operation rather than an incomplete spelling.

**Tech Stack:** ECMAScript modules, Node.js native test runner and coverage, property/finite-matrix fixtures, first-party mutation harness, Python repository validators, PowerShell launcher checks, Debian WSL packaging validation.

## Global Constraints

- Do not pin Claude Code, Nori, Node.js, or DeepSeek versions.
- Do not persist raw commands, source intervals, or credential values.
- Every deny remains operator-visible, actionable, and redacted.
- Every production behavior change follows an observed RED/GREEN cycle.
- Preserve the approved mode matrix: literal credentials ask on first use; bound reuse is limited to the exact non-secret domain; destructive actions always ask.

---

### Task 1: Stage-exact credential ownership

**Files:**
- Modify: `tests/command-guard/binding-store.test.mjs`
- Modify: `tests/command-guard/coverage.test.mjs`
- Modify: `skills/command-driven-operations/scripts/command-guard/composition.mjs`
- Modify: `skills/command-driven-operations/scripts/command-guard/credential-flow.mjs`

**Interfaces:**
- Consumes: lexer tokens with `{ start, end }` offsets and `composition.stages`.
- Produces: stages with `{ sourceStart, sourceEnd }`; credential metadata whose `stage` is the unique sensitive-span owner.

- [ ] **Step 1: Add focused tests for an authenticated first stage followed by another catalogued consumer, multi-stage literals, and unmappable spans**

Assert that the first command binds to its own HTTP origin, changed origins cannot reuse that binding, credentials in multiple stages deny, and direct unit input with a span outside every stage denies.

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `node --test --test-name-pattern="credential.*stage|literal spans" tests/command-guard/binding-store.test.mjs tests/command-guard/coverage.test.mjs`

Expected: the first-stage binding assertion exposes the last-stage domain bug and the ambiguity case is not denied.

- [ ] **Step 3: Preserve source intervals and resolve every literal span to one owning stage**

Track the first and last lexical offsets while composing a stage. In `classifyCredentials`, collect the unique owner of every detected span and leave the literal stage unresolved unless exactly one owner exists. In `credentialFlowErrors`, deny unresolved ownership and validate the executable of that exact stage against the consumer catalogue.

- [ ] **Step 4: Run the focused tests and verify GREEN**

Run the command from Step 2 and require zero failures.

### Task 2: Complete remote-transfer identity

**Files:**
- Modify: `tests/command-guard/security-regressions.test.mjs`
- Modify: `skills/command-driven-operations/scripts/command-guard/catalogue.mjs`

**Interfaces:**
- Consumes: literal `scp`/`sftp` argv and accepted SSH selector spellings.
- Produces: a remote-transfer result with canonical `ssh://user@host:port[?via=...]` environment.

- [ ] **Step 1: Add focused endpoint identity and duplicate-alias tests**

Use literal expectations for user, host, default/explicit port, and ProxyJump. Assert that `-l` versus operand user, `-P` versus `-o Port`, `-J` versus `-o ProxyJump`, repeated aliases, host-only operands, and dynamic values deny.

- [ ] **Step 2: Run only the remote-transfer test and verify RED**

Run: `node --test --test-name-pattern="remote transfer.*endpoint" tests/command-guard/security-regressions.test.mjs`

Expected: current environments omit selectors and duplicate aliases are accepted.

- [ ] **Step 3: Parse selector groups and build canonical endpoint identity**

Normalize supported `-o` names case-insensitively, reject non-whitelisted names, consume each singleton group once, combine it with the operand endpoint, require an explicit user, and emit the canonical environment. Preserve existing local-executor and opaque-config denials.

- [ ] **Step 4: Run the focused test and verify GREEN**

Run the command from Step 2 and require zero failures.

### Task 3: Packet stdout and alias uniqueness

**Files:**
- Modify: `tests/command-guard/security-regressions.test.mjs`
- Modify: `skills/command-driven-operations/scripts/command-guard/catalogue.mjs`

**Interfaces:**
- Consumes: literal bounded `tcpdump`/`tshark` argv.
- Produces: `stdout:pcap` read classification or canonical file-write classification; duplicate semantic selectors return no catalogue match.

- [ ] **Step 1: Add focused stdout and duplicate-alias tests**

Assert both clients and both permission modes ask for `-w -`, return `SAFE_READ_ONLY`, omit `FILE_WRITE`, and target `eth0 -> stdout:pcap`. Assert duplicate snapshot-length, interface, count, and sink aliases deny.

- [ ] **Step 2: Run only the packet-capture test and verify RED**

Run: `node --test --test-name-pattern="packet capture.*stdout" tests/command-guard/security-regressions.test.mjs`

Expected: current code returns a file target for `-` and accepts at least the duplicate snapshot-length aliases.

- [ ] **Step 3: Group aliases and classify stdout before path resolution**

Reject a second semantic selector regardless of spelling. Branch on sink `-` before calling `resolveOutputPath`; emit the approved read-only modifiers and target while preserving existing file sink handling.

- [ ] **Step 4: Run the focused test and verify GREEN**

Run the command from Step 2 and require zero failures.

### Task 4: Finite inventories, mutations, and documentation

**Files:**
- Modify: `tests/command-guard/review-regression-fixtures.mjs`
- Modify: `tests/command-guard/coverage-fixtures.mjs`
- Modify: `tests/command-guard/mutations.mjs`
- Modify: `tests/command-guard/mutation-witnesses.mjs`
- Modify: `skills/command-driven-operations/scripts/command-guard/policy.mjs`
- Modify: `docs/reviews/2026-07-26-pr-25-independent-review.md`
- Modify: `docs/architecture/ADR-004-native-command-guard.md`
- Modify: `README.md`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes: the three implemented invariants and the finite predicate/fixture ledgers.
- Produces: executable review evidence, mutation protection, and operator/architecture documentation.

- [ ] **Step 1: Add real RV fixtures and security predicate IDs**

Add executed fixtures for first-stage credential ownership, complete SSH endpoint identity, capture stdout, and duplicate aliases. Register predicates whose witnesses assert observable decisions and identities.

- [ ] **Step 2: Add mutations and witnesses**

Create mutations that restore last-stage credential ownership, omit an SSH endpoint selector, treat capture stdout as a file, and disable alias uniqueness. Each pristine witness must pass and each corresponding mutant must fail.

- [ ] **Step 3: Update documentation without changing the package version**

Record the final review verdict and fixes, add the stage/SSH/capture invariants to ADR-004, summarize them in README and CHANGELOG, and retain version `0.11.0`.

### Task 5: Complete verification and publication

**Files:**
- Review: every file changed by Tasks 1-4.

**Interfaces:**
- Consumes: complete implementation and documentation diff.
- Produces: reproducible validation evidence and an updated PR #25 branch.

- [ ] **Step 1: Run the complete command-guard gate**

Run: `node tests/run-command-guard-tests.mjs`

Require all unit/property/finite-matrix tests, 100% critical line/branch/function coverage, all mutation witnesses, and secret-artifact scans to pass.

- [ ] **Step 2: Run repository and packaging validators**

Run the Python validators referenced by CI, PowerShell syntax checks, the Debian WSL `tests/validate-package.sh`, and the repository spell-check command from `.github/workflows`.

- [ ] **Step 3: Inspect the complete diff and repository status**

Confirm there are no raw credentials, unrelated changes, version pins, untracked artifacts, or undocumented behavior changes.

- [ ] **Step 4: Commit and push the branch**

Commit with a security-remediation message and push `agent/p0-04-command-guard` to update PR #25.

- [ ] **Step 5: Request an independent review**

Review the pushed diff against this design, record any findings, and do not merge while actionable findings remain.
