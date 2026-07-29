# P0-04 Fourth Review Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate every independently reproduced authorization bypass in PR #25 while preserving bounded operational execution.

**Architecture:** Keep the native fail-closed guard and strengthen the parsing boundary rather than special-casing policy outcomes. Sensitive singleton options reject duplicate aliases, unmodelled route/trust/configuration controls deny before classification, remote HTTP origins must be literal, and raw lexical credential spellings are redacted before authorization. Source and Nori-installed artifacts execute the same regression corpus.

**Tech Stack:** JavaScript ESM on Node.js 24, native `node:test`, Python package/install validators, Bash/WSL validation.

## Global Constraints

- Do not pin Claude Code, Nori, or DeepSeek versions.
- Destructive commands always return native `ask`, including in `bypassPermissions`.
- Unknown, ambiguous, evasive, or unmodelled commands return `deny`.
- Literal credentials ask before first use and never appear in responses, audit, state, or retained artifacts.
- Preserve executor usefulness for explicit, bounded and catalogued operational commands.
- Verify source and installed-form behavior with real executable fixtures.

---

### Task 1: Reproduce every independent-review finding

**Files:**
- Modify: `tests/command-guard/security-regressions.test.mjs`
- Modify: `tests/command-guard/credential-flow.test.mjs`
- Modify: `tests/command-guard/review-regression-fixtures.mjs`

**Interfaces:**
- Consumes: `analyzeCommand(parseHookEvent(...))`
- Produces: executable regression cases for source and installed corpus

- [x] Add literal expectations for duplicate curl methods, duplicate Kubernetes context/namespace aliases, AWS route/trust overrides, Docker route/config overrides, and dynamic HTTP origins.
- [x] Add credential expectations for curl cookies and Redis compact quoted password spellings in both normal and bypass modes.
- [x] Register real fixture IDs for each independent-review case so installed-corpus validation executes them.
- [x] Run the targeted tests with Node 24 and confirm each new test fails for the reported unsafe decision, not because of test syntax.

### Task 2: Close option precedence and remote-route boundaries

**Files:**
- Modify: `skills/command-driven-operations/scripts/command-guard/catalogue.mjs`
- Test: `tests/command-guard/security-regressions.test.mjs`

**Interfaces:**
- Consumes: lexer-produced `stage.argv`
- Produces: `lookupFamily(stage)` result or `null` for denied/unmodelled forms

- [x] Add a parser helper that identifies duplicate singleton option groups across separate, inline and alias spellings.
- [x] Reject repeated curl method selectors and repeated Kubernetes context/namespace selectors before deriving risk or binding.
- [x] Reject AWS endpoint, certificate/trust, unsigned and debug overrides; bind `AWS_PROFILE` assignment when it is the selected provider profile.
- [x] Reject Docker host, connection and external-config overrides while retaining literal `--context` support.
- [x] Reject variables, globs and other dynamic syntax in HTTP URLs before URL parsing.
- [x] Run targeted security regressions and confirm they pass without breaking existing bounded reads.

### Task 3: Close lexical credential spellings

**Files:**
- Modify: `skills/command-driven-operations/scripts/command-guard/redaction.mjs`
- Test: `tests/command-guard/credential-flow.test.mjs`

**Interfaces:**
- Consumes: raw hook command text
- Produces: exact sensitive spans and credential transport metadata

- [x] Detect `curl -b`, `--cookie`, inline/equal and quoted cookie literals containing a name/value pair.
- [x] Detect Redis `-a"value"` and `-a'value'` compact quoted literals, in addition to existing separated/equal/compact forms.
- [x] Verify first use asks in every mode and serialized results never contain the literal.
- [x] Run credential, property and entrypoint tests under Node 24.

### Task 4: Prove installed equivalence and document the verdict

**Files:**
- Modify: `docs/reviews/2026-07-26-pr-25-independent-review.md`
- Modify if required: `docs/architecture/ADR-004-native-command-guard.md`
- Test: `tests/command-guard/run-installed-corpus.mjs`

**Interfaces:**
- Consumes: versioned review fixtures and Nori-installed scripts directory
- Produces: auditable closure record plus executable installed-form evidence

- [x] Record the fourth independent-review findings, root causes, remediation decisions, and verification status without rewriting earlier verdict history.
- [x] Update ADR-004 only if the strengthened singleton/route boundary is not already represented.
- [x] Build/install the package in an isolated temporary home and execute the entire review corpus against the installed artifact.
- [x] Run the full Node 24 coverage/mutation gate, package validators, content/schema checks, shell syntax, PowerShell syntax, and `git diff --check`.
- [x] Inspect the final diff and confirm no secrets, generated artifacts, unrelated changes, or version pins were introduced.
