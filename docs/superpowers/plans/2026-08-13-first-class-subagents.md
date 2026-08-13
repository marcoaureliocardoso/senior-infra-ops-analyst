# First-Class Subagents Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish all 12 project subagents as canonical, independently versioned Nori components without breaking discovery, installation, runtime policy, or cross-references.

**Architecture:** Replace each flat definition with `subagents/<id>/SUBAGENT.md` plus a strict `nori.json` of type `subagent`. Centralize canonical discovery and definition-path resolution in `scripts/nori_package.py`; every executable consumer uses that seam, while Nori installation continues to flatten definitions into Claude Code's `.claude/agents/` directory.

**Tech Stack:** Python 3 standard library, Node.js ESM, Bash, Markdown/YAML frontmatter, JSON, Nori CLI package conventions.

## Global Constraints

- All 12 components use `type: "subagent"` and initial version `1.0.0`.
- Manifest `name` and `description` match directory ID and frontmatter exactly.
- Root `dependencies.subagents` is not synthesized before successful registry synchronization.
- Historical reviews and superseded plans remain historically accurate.
- No registry upload, tag, or release occurs without separate operator confirmation.
- Tests are written and observed failing before implementation changes.

---

### Task 1: Canonical discovery and manifest contract

**Files:**
- Modify: `tests/test-nori-package-contract.py`
- Modify: `tests/test-content-discovery.py`
- Modify: `scripts/nori_package.py`

**Interfaces:**
- Produces: `subagent_definition_path(root: Path, subagent_id: str) -> Path`
- Produces: `discover_subagent_ids(root: Path) -> tuple[str, ...]` for directory packages only.
- Produces: repository-inventory errors for malformed or legacy subagent packages.

- [x] **Step 1: Write failing contract tests**

Add controlled filesystem cases proving canonical discovery, flat-file rejection,
missing `SUBAGENT.md`, missing/invalid `nori.json`, wrong `name`, wrong `type`,
invalid `version`, unexpected fields, and description/frontmatter drift.

- [x] **Step 2: Run the focused tests and observe RED**

Run:

```bash
python3 tests/test-nori-package-contract.py
python3 tests/test-content-discovery.py
```

Expected: failures show that discovery still expects flat Markdown and does not
validate first-class subagent manifests.

- [x] **Step 3: Implement the canonical discovery seam**

Update `scripts/nori_package.py` so only directories containing both
`SUBAGENT.md` and a valid `nori.json` are discovered. Validate the exact
project-required manifest shape and compare its identity and description with
frontmatter.

- [x] **Step 4: Run focused tests and observe GREEN**

Run both commands from Step 2. Expected: all cases pass with no warnings.

### Task 2: Migrate definitions and executable consumers

**Files:**
- Move: `subagents/*.md` to `subagents/<id>/SUBAGENT.md`
- Create: `subagents/<id>/nori.json` for all 12 IDs
- Modify: `tests/validate-content.py`
- Modify: `tests/test-subagent-frontmatter.py`
- Modify: `tests/test-command-guard-install-policy.py`
- Modify: `tests/test-context-continuity-install-policy.py`
- Modify: `tests/validate-installed-subagents.py`
- Modify: `tests/live-command-guard-smoke.sh`
- Modify: `skills/context-continuity/scripts/context-inventory.mjs`
- Modify: `tests/context-continuity/inventory.test.mjs`

**Interfaces:**
- Consumes: canonical discovery and `subagent_definition_path` from Task 1.
- Produces: unchanged subagent IDs, frontmatter semantics, hooks, policies, and inventory measurements under the new source paths.

- [x] **Step 1: Change consumer tests to the canonical layout**

Make tests resolve `subagents/<id>/SUBAGENT.md`, assert all 12 component
manifests, and prove the context inventory reads directory definitions.

- [x] **Step 2: Run consumer tests and observe RED**

Run the Python policy/frontmatter/content suites and Node inventory suite.
Expected: canonical files or manifests are missing and the existing inventory
does not discover directory packages.

- [x] **Step 3: Move all 12 definitions and create manifests**

Preserve every definition byte. Create a manifest with literal `name`,
`version`, `type`, and the exact frontmatter `description` for each component.

- [x] **Step 4: Update executable consumers**

Route Python validators through the canonical helper. Make the Node inventory
iterate subagent directories and read `SUBAGENT.md`. Update the command-guard
smoke fixture to flatten canonical definitions into its isolated installed
agents directory.

- [x] **Step 5: Run consumer tests and observe GREEN**

Run all focused suites from Step 2 and `python3 tests/validate-content.py`.
Expected: 12 definitions are discovered with unchanged policies and metrics.

### Task 3: Package and installed-runtime proof

**Files:**
- Modify: `tests/live-nori-package-smoke.sh`
- Modify: `tests/test-live-nori-package-safety.py`
- Modify: `tests/test-nori-staging.py`
- Modify: `tests/test-nori-archive.py`

**Interfaces:**
- Consumes: canonical package tree from Tasks 1 and 2.
- Produces: isolated loader proof that canonical directories install as flat Claude Code agent files.

- [x] **Step 1: Add failing package-smoke assertions**

Require exactly 12 staged subagent directories, exactly 12 valid manifests,
zero flat source definitions, and installed content semantically equal to each
canonical `SUBAGENT.md` after normalizing Nori's `{{skills_dir}}` resolution.

- [x] **Step 2: Run self-test and observe RED**

Run `bash tests/live-nori-package-smoke.sh --self-test`. Expected: the fake
loader or source inventory still assumes flat definitions.

- [x] **Step 3: Update the isolated fake loader and verification**

Copy each `SUBAGENT.md` to `.claude/agents/<id>.md`; validate manifest type,
version, name, description, and normalized installed semantics before declaring
the install complete.

- [x] **Step 4: Run focused package tests and observe GREEN**

Run package-contract, staging, archive, live-safety, and live-smoke self-tests.
Expected: all canonical-source and installed-runtime assertions pass.

### Task 4: Current documentation and release-state coherence

**Files:**
- Modify: `README.md`
- Modify: `docs.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/architecture/ADR-002-subagent-skill-preload.md`
- Modify: `docs/architecture/ADR-003-subagent-runtime-controls.md`
- Modify: `docs/architecture/ADR-004-native-command-guard.md`
- Modify: `docs/architecture/ADR-006-canonical-nori-package.md`
- Modify: `docs/architecture/README.md` only if a new ADR is needed after review

**Interfaces:**
- Consumes: final canonical layout and installation behavior.
- Produces: one consistent current-source path and an honest unreleased-package record.

- [x] **Step 1: Update active documentation**

Describe the directory package, individual `1.0.0` manifests, installed flat
boundary, and current Nori upload semantics. Replace active `subagents/*.md`
path claims without rewriting historical evidence.

- [x] **Step 2: Record the change in the existing 0.12.0 unreleased state**

Add one concise `CHANGELOG.md` bullet. Do not create a tag or claim publication.

- [x] **Step 3: Run documentation and content validation**

Run architecture tests, content validation, markdownlint, cspell, and diff
whitespace checks. Expected: zero failures.

### Task 5: Complete validation and review

**Files:**
- Modify: `tests/validation-notes.md` with actual observed evidence

**Interfaces:**
- Consumes: all preceding tasks.
- Produces: final reviewable commit and evidence for an operator-authorized registry upload.

- [x] **Step 1: Run the complete package gate in Debian WSL**

Run `bash tests/validate-package.sh` using the repository's compatible Node
runtime. Expected: exit 0 and no test failures.

- [x] **Step 2: Build and validate fresh canonical staging**

Use `scripts/build_nori_staging.py` in a temporary directory; verify all 12
subagent manifests and definitions are present and no legacy flat definitions
exist.

- [x] **Step 3: Append factual validation evidence**

Record commands, observed tool versions, counts, and limitations. Do not claim a
registry upload that was not performed.

- [x] **Step 4: Review the complete diff and run hygiene checks**

Inspect renames, manifest/frontmatter equality, executable paths, and
`git diff --check`; confirm no secrets or unrelated changes.

- [ ] **Step 5: Commit and request independent review**

Commit the coherent migration, then obtain a read-only review over the exact
base-to-head range. Fix every Critical or Important finding and rerun the full
gate before offering publication or integration options.
