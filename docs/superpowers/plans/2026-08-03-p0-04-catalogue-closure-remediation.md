# P0-04 Catalogue Closure Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close RV-76 through RV-79 by requiring complete parsing of Git push, operational log streams, GitHub CLI reads, and Kubernetes cluster dumps.

**Architecture:** Replace prefix recognition with small closed parsers that consume every supported token and return canonical risk, target, environment, and modifiers. Preserve the existing policy matrix and package interfaces while extending executable fixtures and mutation evidence.

**Tech Stack:** ECMAScript modules, Node.js native test runner and coverage, first-party fixture and mutation gates, Python repository validators, Git Bash/WSL package validation.

## Global Constraints

- Do not pin Claude Code, Nori, Node.js, or DeepSeek versions.
- Do not add dependencies or persist raw commands or credentials.
- Unknown, repeated, conflicting, dynamic, or unconsumed options deny.
- Every production behavior change follows an observed RED/GREEN cycle.
- Preserve version `0.11.0` because the PR remains unreleased.

---

### Task 1: Closed Git push parser

**Files:**
- Modify: `tests/command-guard/security-regressions.test.mjs`
- Modify: `skills/command-driven-operations/scripts/command-guard/catalogue.mjs`

**Interfaces:**
- Consumes: literal `git push` argv after the executable.
- Produces: `{ risk, target, environment }` for one repository and bounded refspecs, or `null` for an unmodelled invocation.

- [ ] **Step 1: Write failing behavioral tests**

Add literal assertions that `--repo` and positional repository forms bind the
same environment; `--exec`, `--receive-pack`, duplicate/conflicting repository
selectors, server push-options, local-hook bypass, external `*::` helper
transports using `::`, unknown or case-altered `scheme://` remote helpers, missing repositories,
unknown options, and malformed refspecs deny in both modes. Assert force,
deletion, mirror, prune, `+refspec`, and `:destination` remain destructive.

- [ ] **Step 2: Verify RED**

Run:

```bash
node --test --test-name-pattern="Git push.*closed" tests/command-guard/security-regressions.test.mjs
```

Expected: the override reproduction returns `allow` in `bypassPermissions` and
its recorded environment is `local` rather than the selected repository.

- [ ] **Step 3: Implement the minimal closed parser**

Add `parseGitPush(words)` beside `parseGitBranch`. Consume `--repo` in separated
and attached forms, reject remote-program and opaque server options, validate
one repository plus one to `LIMITS.fanOut` refspecs, and return a destructive
risk whenever a destructive flag or refspec is present. Route only the `push`
verb through this parser in `gitCiFamily`.

- [ ] **Step 4: Verify GREEN**

Run the Step 2 command and require zero failures.

### Task 2: Finite log grammars

**Files:**
- Modify: `tests/command-guard/security-regressions.test.mjs`
- Modify: `skills/command-driven-operations/scripts/command-guard/catalogue.mjs`

**Interfaces:**
- Consumes: `journalctl` argv or a Docker/Podman/Nerdctl/CRI `logs` argv.
- Produces: one finite read or existing destructive journal action; enabled follow and unconsumed options return `null`.

- [ ] **Step 1: Write failing stream and option-consumption tests**

Assert all separated, attached, short, long, and client-specific follow forms
deny. Assert finite documented timestamp/since/until forms pass, duplicate
tails and unknown options deny, and destructive journal maintenance keeps its
classification.

- [ ] **Step 2: Verify RED**

Run:

```bash
node --test --test-name-pattern="log grammars.*finite" tests/command-guard/security-regressions.test.mjs
```

Expected: Docker, Podman, and journal follow reproductions return `allow`.

- [ ] **Step 3: Implement closed journal and container-log parsers**

Add `parseJournalctl(words)` and `parseContainerLogs(words, client)`. Track
semantic option groups, consume every accepted arity, enforce the existing row
bound, require one container target, reject follow and unknown controls, and
return canonical targets and modifiers to `lookupFamily` without discarding the
container target during integration.

- [ ] **Step 4: Verify GREEN**

Run the Step 2 command and require zero failures.

### Task 3: Closed GitHub read schemas and Kubernetes dump denial

**Files:**
- Modify: `tests/command-guard/security-regressions.test.mjs`
- Modify: `tests/command-guard/branches.test.mjs`
- Modify: `skills/command-driven-operations/scripts/command-guard/catalogue.mjs`

**Interfaces:**
- Consumes: the eight supported `gh` read subcommands and `kubectl cluster-info` argv.
- Produces: bounded GitHub read results, sensitive run-log confirmation, or `null`; plain cluster info remains safe and dump denies.

- [ ] **Step 1: Write failing GH and Kubernetes behavior tests**

Assert watch, excessive limits, unknown options, implicit repository selection,
duplicate repository/limit selectors, and missing option values deny. Assert
`run view --log` asks with sensitive/resource modifiers. Change the existing
dump positive assertion to a plain `cluster-info` positive and add denial for
the real positional `cluster-info dump` subcommand in kubectl and k3s.

- [ ] **Step 2: Verify RED**

Run:

```bash
node --test --test-name-pattern="GitHub read.*closed|cluster info.*dump" tests/command-guard/security-regressions.test.mjs tests/command-guard/branches.test.mjs
```

Expected: the three GitHub reproductions and Kubernetes dump are still
authorized as narrow reads.

- [ ] **Step 3: Implement verb-specific schemas**

Add `parseGhRead(words)` with one closed schema per supported noun/verb, require
an explicit repository domain, and use its returned modifiers in `gitCiFamily`.
Reject positional operands after `cluster-info` so the `dump` subcommand cannot
inherit summary authorization.

- [ ] **Step 4: Verify GREEN**

Run the Step 2 command and require zero failures.

### Task 4: Executable evidence and documentation

**Files:**
- Modify: `tests/command-guard/review-regression-fixtures.mjs`
- Modify: `tests/command-guard/coverage-fixtures.mjs`
- Modify: `tests/command-guard/mutations.mjs`
- Modify: `tests/command-guard/mutation-witnesses.mjs`
- Modify: `docs/reviews/2026-07-26-pr-25-independent-review.md`
- Modify: `docs/architecture/ADR-004-native-command-guard.md`
- Modify: `README.md`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes: the four closed-parser invariants.
- Produces: RV-76 through RV-79 installed fixtures, exact mutation witnesses, and aligned operator/architecture documentation.

- [ ] **Step 1: Add stable review fixtures**

Add real policy-entrypoint fixtures for the Git override, every follow client,
GitHub watch/log/limit behavior, and Kubernetes dump. Use literal decisions and
forbidden-text assertions rather than source-text checks.

- [ ] **Step 2: Add four one-site mutations and typed witnesses**

Register dedicated mutations for Git override/helper rejection and destination
binding, log follow/target behavior, GitHub option/repository/log boundaries,
and the real Kubernetes dump subcommand. Each pristine witness must pass and
only its matching mutant may satisfy the failing witness.

- [ ] **Step 3: Update documentation without a version bump**

Record the review verdict and remediation in the ledger, add the catalogue
closure invariant to ADR-004, and summarize the behavior in README and
CHANGELOG while preserving version `0.11.0`.

### Task 5: Complete validation and PR update

**Files:**
- Review: all files changed in Tasks 1-4.

**Interfaces:**
- Consumes: complete remediation diff.
- Produces: verified branch update and a new independent merge verdict.

- [ ] **Step 1: Run the complete deterministic gate**

Run `node tests/run-command-guard-tests.mjs` and require all tests, 100 percent
critical line/branch/function coverage, pristine witnesses, and all mutations.

- [ ] **Step 2: Run repository and package validators**

Run the Python validators, shell self-tests, Markdown/CSpell checks,
`git diff --check`, and the Debian/WSL package gate used by this branch.

- [ ] **Step 3: Inspect security and compatibility invariants**

Confirm the delta contains no real credential, raw-command persistence,
dependency addition, unrelated edit, or Claude Code/Nori/Node/model pin.

- [ ] **Step 4: Commit, push, and update PR #25**

Commit the implementation, push `agent/p0-04-command-guard`, refresh PR
validation evidence, and request one independent read-only review. Do not merge
while any actionable finding remains.
