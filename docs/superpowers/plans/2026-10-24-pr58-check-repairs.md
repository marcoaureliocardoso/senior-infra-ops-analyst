# PR 58 Check Repairs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair all five failing PR checks without weakening validation or changing native acceptance behavior.

**Architecture:** Correct the full-package job budgets and lint inputs in place. Repair link extraction and fixture filtering with executable offline regressions; retain public-link checks and existing reachability semantics. Keep changes on the existing PR branch.

**Tech Stack:** GitHub Actions YAML, Bash, Python standard library, ShellCheck, markdownlint, cSpell.

**Spec:** Operator-requested corrections to PR 58 at `06ddf5753925b9561f01d866e927af93a9def4c0`; CI run `40108945470` and Security run `40108945496`.

## Global Constraints

- Reuse the clean `p0-04b-browser-automation` worktree and branch; preserve operator changes if they appear.
- No merge, release, native Claude execution, provider request, credential access, or operator configuration change.
- Preserve harness operation and total limits, permission decisions, acceptance gates, pinned actions, and enforced lint rules.
- Keep version `0.15.0` unreleased; record corrections without claiming P0-04B acceptance.
- Keep deliverable text in English.
- The unavailable formal security scan is not a passing scan; public SDK lifecycle qualification remains outside this repair.

## Review Focus

1. Every full-package consumer needs sufficient job time; inspect CI, release validation, and scheduled full validation, not only the failing PR job.
2. A quoted JSON fixture must not append JSON fields to a URL; exercise the actual shell script with controlled Markdown and a network-boundary curl double.
3. Loopback fixtures must not cause network requests, while public URLs must still be checked and broken public URLs must fail.
4. Empty input and unusual URL characters must produce valid JSON with accurate counts, including a nonzero exit for broken links.
5. Lint corrections must preserve commands, identifiers, historical evidence, and nested-shell argument expansion rather than hide failures globally.

## Task 1: Repair job budgets and lint inputs

**Files:**

- Modify `.github/workflows/ci.yml`, `.github/workflows/release.yml`, and `.github/workflows/scheduled-maintenance.yml`.
- Modify `tests/live-browser-operations-smoke.sh`.
- Modify `tests/test-live-browser-operation-safety.py` only to remove the two assertions requiring dead metadata assignments; preserve actual authorization and timeout coverage.
- Modify only Markdown files reported by markdownlint/cSpell, plus `.cspell.json` for reviewed technical terms.

**Interfaces:** Existing workflow jobs, harness invocations, and lint configuration contracts remain unchanged.

- [ ] Reproduce the three ShellCheck diagnostics and Markdown/cSpell failures using the existing project configurations and inspect each affected text location.
- [ ] Set only the three full-package validation job budgets to 40 minutes. The measured immutable full gate took 1,461.331 seconds; 40 minutes leaves provisioning and runner-variance margin. Leave unrelated jobs and harness deadlines unchanged.
- [ ] Remove the two unused measurement constants and the corresponding static markers in `test_modes_authorization_and_bounds_are_explicit`. Preserve enforced six-invocation/40-turn authorization assertions. Add a single explanatory SC2016 suppression before the complete timeout-forgery command; preserve child-shell `$1` expansion and timeout-forgery behavior.
- [ ] Wrap excessive prose, separate fences, and quote literal underscores where required, without rewriting historical results or disabling lint rules.
- [ ] Correct actual spelling errors or awkward prose. Add only confirmed technical vocabulary to the dictionary; use narrowly scoped cSpell annotations for literal synthetic identifiers instead of globally accepting random strings.
- [ ] Run ShellCheck across all shell files, markdownlint across all Markdown, cSpell across all Markdown, workflow validation, and the existing timeout-provenance self-tests. Confirm the full-package consumers retain provisioning and fail-closed validation.
- [ ] Commit this independently reviewable correction set.

## Task 2: Repair external-link selection and reporting

**Files:**

- Modify `tests/validate-links.sh`.
- Create `tests/test-link-validation.py`.
- Modify `tests/validate-package.sh` to include the offline regression suite.

**Interfaces:** Preserve `bash tests/validate-links.sh [--json]`, its existing report keys, and public reachability/error exit semantics. Do not introduce dependencies or change public-link network behavior.

- [ ] Write executable regression tests that copy the real script into a temporary fixture repository and replace only curl/sleep at the process boundary. Assert checked URL arguments, report contents, and exit codes rather than source text.
- [ ] Cover quoted JSON URLs, IPv4 loopback fixtures including another address in `127.0.0.0/8`, localhost, existing placeholder-domain filtering, public success, public failure, an empty corpus, deduplication, and valid JSON for special URL characters.
- [ ] Run the suite and observe failures for malformed fixture extraction and loopback requests before modifying the script.
- [ ] Make the smallest extraction/filtering correction: terminate URLs at quote delimiters, skip loopback fixture hosts, and retain public URLs. Correct JSON escaping only as needed to satisfy the report contract.
- [ ] Run the regression suite, ShellCheck, and existing link-report consumer tests. Confirm broken public links still fail and fixture-only input causes no curl invocation.
- [ ] Wire the offline suite into the full package gate, then commit.

## Task 3: Verify and update the same PR

**Files:** `CHANGELOG.md` and `tests/validation-notes.md`, only for truthful repair and validation records.

**Interfaces:** Existing PR 58 head; no merge or release operation.

- [ ] Run focused regressions, all local lint checks, workflow validation, and the complete package gate through the established isolated Linux route. Record duration, failures, and cleanup verification.
- [ ] Run live public-link validation with the corrected script; report external/transient failures explicitly rather than silently suppress them.
- [ ] Obtain independent review of the repair diff; correct actionable findings and rerun affected checks.
- [ ] Record actual outcomes, inspect the final diff and clean worktree, and push the repair commits to the same PR branch.
- [ ] Verify fresh CI/Security conclusions for the pushed SHA. Do not mark blocked native acceptance as complete or merge the PR.

## Rollback

Revert only the repair commits if necessary. No operator settings, Git metadata, native artifacts, or credentials should require restoration.

## Planning Status

Operator confirmed direct execution. Repair commits and the single independent
review/fix pass are complete; final full-gate, live-link, and remote check results
are tracked in `tests/validation-notes.md`. No merge is authorized by this plan.
