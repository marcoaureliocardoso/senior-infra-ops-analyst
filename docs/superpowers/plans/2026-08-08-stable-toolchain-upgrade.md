# Stable Toolchain Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the repository-managed CI stack and separately refresh the operator workstation to the stable releases verified on 2026-08-08.

**Architecture:** GitHub Actions workflows use immutable release SHAs, exact compatibility matrices, and fail-closed validators. Host tool updates remain external to the package and are reported as observed evidence, never written as Claude Code, Nori, DeepSeek, or skillset compatibility constraints.

**Tech Stack:** GitHub Actions, Bash, Python `unittest`, Node.js LTS, ShellCheck, PowerShell, Bubblewrap, GitHub CLI.

## Global Constraints

- Do not change, update, pin, or reconfigure Claude Code, Nori Skillsets, or DeepSeek.
- Retain `ubuntu-24.04` and `model: inherit`.
- Use Node.js `24.19.0` LTS rather than Node.js 26 Current for local validation.
- Test Python `3.12` and `3.14` in CI without declaring either as a skillset runtime requirement.
- Every external GitHub Action must use a full 40-character commit SHA and an adjacent release comment.
- ShellCheck must be exactly `0.11.0` and its official archive must pass SHA-256 verification with `8c3be12b05d5c177a04c29e3c78ce89ac86f1595681cab149b65b97c4e227198`.
- Increment package metadata from `0.11.0` to `0.11.1`.

---

### Task 1: Enforce immutable and current workflow dependencies

**Files:**
- Modify: `tests/test-ci-workflows.py`
- Modify: `tests/validate-ci-workflows.sh`
- Test: `tests/test-ci-workflows.py`

**Interfaces:**
- Consumes: workflow files under `.github/workflows/`.
- Produces: a validator contract that accepts only canonical YAML and immutable external Action SHAs.

- [ ] **Step 1: Add failing immutable-reference tests**

Add tests that copy the workflows into the temporary repository, replace one
40-character Action SHA with `v7`, and assert that validation fails with
`external action must use a full commit SHA`. Add mutations for a tag-only
reference, a short SHA, a non-hex 40-character reference, a quoted `uses` key,
an explicit mapping key, and an alias-derived key.

- [ ] **Step 2: Run the workflow regression tests and verify RED**

Run:

```bash
python3 -m unittest tests.test-ci-workflows -v
```

Expected: the new immutable-reference cases fail because the validator only
protects `actions/checkout` tags.

- [ ] **Step 3: Generalize the validator**

Move canonical YAML-key rejection to every workflow and inspect every external
`uses:` reference. Accept local `./` actions; otherwise require this form:

```text
owner/repository@0123456789abcdef0123456789abcdef01234567 # v1.2.3
```

Continue to reject anchors, aliases, explicit mapping keys, and YAML tags before
the `uses:` scan so alternate YAML representations cannot bypass the check.

- [ ] **Step 4: Run the workflow regression tests and verify GREEN**

Run:

```bash
python3 -m unittest tests.test-ci-workflows -v
bash tests/validate-ci-workflows.sh
```

Expected: all workflow mutation tests pass and the pristine workflow still
fails until Task 2 replaces its mutable Action references.

- [ ] **Step 5: Commit the validator contract**

```bash
git add tests/test-ci-workflows.py tests/validate-ci-workflows.sh
git commit -m "test: require immutable workflow actions"
```

### Task 2: Upgrade GitHub Actions and compatibility lanes

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `.github/workflows/security.yml`
- Modify: `.github/workflows/release.yml`
- Modify: `.github/workflows/scheduled-maintenance.yml`
- Modify: `.github/dependabot.yml`
- Modify: `tests/test-ci-workflows.py`
- Test: `tests/test-ci-workflows.py`

**Interfaces:**
- Consumes: the immutable-reference validator from Task 1.
- Produces: current SHA-pinned Actions, CodeQL v4, and Python 3.12/3.14 lanes.

- [ ] **Step 1: Add failing target-version tests**

Assert that the checked-in workflows contain these exact references:

```text
actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97 # v7.0.0
github/codeql-action/init@5595ccaf912efad79be6eef63a5619ff05969be3 # v4
github/codeql-action/analyze@5595ccaf912efad79be6eef63a5619ff05969be3 # v4
actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a # v7.0.1
softprops/action-gh-release@3d0d9888cb7fd7b750713d6e236d1fcb99157228 # v3.0.2
DavidAnson/markdownlint-cli2-action@21c1be1b93ad9ed58fa840aacc3f279cde2a72ff # v24.2.0
streetsidesoftware/cspell-action@de2a73e963e7443969755b648a1008f77033c5b2 # v8.4.0
```

Add Python-matrix cases that reject missing 3.12, missing 3.14, extra versions,
hard-coded `python-version`, a decoy matrix in another job, `include`/`exclude`,
and conditional or `continue-on-error` controls on the schema job or setup step.

- [ ] **Step 2: Run the new tests and verify RED**

Run:

```bash
python3 -m unittest tests.test-ci-workflows -v
```

Expected: failures identify the existing Action versions and single Python 3.12 lane.

- [ ] **Step 3: Replace all Action references**

Apply the exact SHA/comment pairs above to all workflow occurrences. Update the
CodeQL mutation fixtures from literal `@v3` strings to the v4 SHA so the
existing matrix and fail-closed tests continue exercising the real workflow.

- [ ] **Step 4: Add the Python compatibility matrix**

Change `nori-schema` to:

```yaml
strategy:
  fail-fast: false
  matrix:
    python-version: ['3.12', '3.14']
```

Wire `actions/setup-python` directly with
`python-version: ${{ matrix.python-version }}`. Keep both the job and setup step
unconditional and fail-closed.

- [ ] **Step 5: Increase Dependabot cadence**

Change only the `github-actions` interval from `monthly` to `weekly`; retain the
pip entry for future dependency manifests.

- [ ] **Step 6: Run workflow tests and verify GREEN**

Run:

```bash
python3 -m unittest tests.test-ci-workflows -v
bash tests/validate-ci-workflows.sh
```

Expected: zero failures.

- [ ] **Step 7: Commit Action and matrix upgrades**

```bash
git add .github tests/test-ci-workflows.py
git commit -m "ci: upgrade stable workflow toolchain"
```

### Task 3: Provision checksum-verified ShellCheck 0.11.0

**Files:**
- Modify: `.github/workflows/security.yml`
- Modify: `tests/test-ci-workflows.py`
- Modify: `tests/validate-ci-workflows.sh`
- Test: `tests/test-ci-workflows.py`

**Interfaces:**
- Consumes: the official `shellcheck-v0.11.0.linux.x86_64.tar.xz` release asset.
- Produces: a verified `shellcheck` executable on `GITHUB_PATH` before analysis.

- [ ] **Step 1: Add failing ShellCheck supply-chain tests**

Require the security workflow to contain the official HTTPS release URL, exact
lowercase SHA-256 digest, `sha256sum --check`, extraction under `RUNNER_TEMP`, a
`GITHUB_PATH` update, and a version assertion for `0.11.0`. Add mutations for a
changed version, changed digest, non-GitHub origin, missing checksum command,
missing version assertion, and executing ShellCheck before provisioning.

- [ ] **Step 2: Run the tests and verify RED**

Run:

```bash
python3 -m unittest tests.test-ci-workflows -v
```

Expected: ShellCheck provisioning cases fail against the runner-provided binary.

- [ ] **Step 3: Add fail-closed provisioning to `security.yml`**

Insert a step before analysis that performs the equivalent of:

```bash
archive="$RUNNER_TEMP/shellcheck-v0.11.0.linux.x86_64.tar.xz"
curl --fail --location --silent --show-error \
  https://github.com/koalaman/shellcheck/releases/download/v0.11.0/shellcheck-v0.11.0.linux.x86_64.tar.xz \
  --output "$archive"
echo "8c3be12b05d5c177a04c29e3c78ce89ac86f1595681cab149b65b97c4e227198  $archive" | sha256sum --check --strict
tar -xJf "$archive" -C "$RUNNER_TEMP"
echo "$RUNNER_TEMP/shellcheck-v0.11.0" >> "$GITHUB_PATH"
```

At the start of the analysis step, assert `shellcheck --version` reports
`version: 0.11.0` before scanning scripts.

- [ ] **Step 4: Run tests and verify GREEN**

Run:

```bash
python3 -m unittest tests.test-ci-workflows -v
bash tests/validate-ci-workflows.sh
```

Expected: zero failures.

- [ ] **Step 5: Commit ShellCheck provisioning**

```bash
git add .github/workflows/security.yml tests/test-ci-workflows.py tests/validate-ci-workflows.sh
git commit -m "ci: verify ShellCheck 0.11.0"
```

### Task 4: Align version metadata and documentation

**Files:**
- Modify: `nori.json`
- Modify: `.nori-version`
- Modify: `README.md`
- Modify: `docs.md`
- Modify: `CHANGELOG.md`
- Test: `tests/test-schema-validation.py`
- Test: `tests/validate-schema.py`

**Interfaces:**
- Consumes: completed workflow implementation and verified target versions.
- Produces: truthful version `0.11.1` metadata and release documentation.

- [ ] **Step 1: Confirm existing version tests fail after a partial bump**

Change only `nori.json` to `0.11.1`, run schema tests, and confirm they fail on
cross-file version consistency. This is the RED proof for the coordinated bump.

- [ ] **Step 2: Update all public version surfaces**

Set `nori.json`, `.nori-version`, README, and docs metadata to `0.11.1`. Add a
`0.11.1 - 2026-08-08` changelog entry listing the Action upgrades, Python
matrix, ShellCheck verification, immutable pins, Dependabot cadence, and the
unchanged AI runtime scope.

- [ ] **Step 3: Correct the inaccurate historical entry**

In the 0.6.1 entry, remove the claim that `actions/setup-python` reached v6.3.0
and CodeQL reached v4 at that time. Retain only upgrades present in that release.

- [ ] **Step 4: Run metadata and content tests**

Run:

```bash
python3 tests/validate-schema.py
python3 tests/validate-content.py
python3 -m unittest tests.test-schema-validation -v
git diff --check
```

Expected: zero failures and no whitespace errors.

- [ ] **Step 5: Commit metadata and documentation**

```bash
git add nori.json .nori-version README.md docs.md CHANGELOG.md
git commit -m "chore: release stable toolchain update"
```

### Task 5: Verify, publish, and refresh the operator workstation

**Files:**
- Verify only: entire repository
- External state: WSL and Windows package installations

**Interfaces:**
- Consumes: Tasks 1 through 4.
- Produces: a draft pull request and an evidence-only local tool inventory.

- [ ] **Step 1: Run the full repository gate in WSL**

Run:

```bash
bash tests/validate-package.sh
```

Expected: all Python and Node tests pass, command-guard coverage is 100%, the
mutation threshold passes, and workflow validation passes.

- [ ] **Step 2: Review scope and history**

Run:

```bash
git status --short
git diff --check main...HEAD
git log --oneline main..HEAD
```

Expected: only the approved toolchain, tests, version, and documentation changes.

- [ ] **Step 3: Push and open a draft pull request**

Push `agent/upgrade-stable-toolchain` to `origin` and open a draft PR against
`main` describing the targets, RED/GREEN evidence, and excluded AI components.

- [ ] **Step 4: Observe GitHub-hosted checks**

Wait for CI and Security checks. If scheduled or release-only paths are not
exercised by the PR, dispatch the safe workflow-dispatch paths or document why a
tag-triggered release cannot be executed before merge.

- [ ] **Step 5: Update local tools through trusted package channels**

Update Node.js to 24.19.0 LTS using the existing NVM installation, Python to
3.14.7 through its existing trusted installer/package manager, PowerShell to
7.6.4, Bubblewrap to 0.11.2, and GitHub CLI to 2.97.0. Do not use these updates
to modify Claude Code, Nori Skillsets, DeepSeek, or their configuration.

- [ ] **Step 6: Record final observed versions**

Run each tool's version command and include the outputs in the handoff. A local
package-manager limitation is reported as a blocker for that tool, not bypassed
with an untrusted installer.
