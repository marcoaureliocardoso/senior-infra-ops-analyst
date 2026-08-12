# Changelog History Curation Implementation Plan

<!-- cspell:words classmethod parseable pathlib pycache sandboxed -->

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development to implement this plan with task and
> whole-branch reviews.

**Goal:** Make `CHANGELOG.md` truthfully distinguish unpublished package
states from tagged versions while preserving all accurate historical facts.

**Architecture:** Extend the existing content validator with a deterministic,
network-free changelog ledger. Mutation tests exercise the contract in a
copied package without `.git`. Then restructure the changelog and align the
README terminology with that contract.

**Tech Stack:** Markdown, Python 3 `unittest`, the existing
`tests/validate-content.py` validator, and the existing package gate.

## Global Constraints

- Keep package version 0.12.0 and do not change version metadata.
- Do not create or move any Git tag or GitHub Release.
- Do not require network access or a `.git` directory during validation.
- Preserve every accurate existing changelog fact.
- Keep all delivered text in English.
- Use Git tag creator dates for tagged-version headings.
- Treat exactly 0.12.0, 0.11.1, 0.11.0, 0.9.1, 0.9.0, and 0.8.0 as
  unpublished package states.
- Treat exactly 0.10.0, 0.7.0, 0.6.1, 0.6.0, 0.5.1, 0.5.0, 0.4.4, 0.4.3,
  0.4.2, 0.4.1, 0.4.0, 0.3.4, 0.3.2, 0.3.1, and 0.2.1 as tagged versions.
- Fold 0.3.0 facts into 0.3.1 and 0.3.3 facts into 0.3.4; neither fictional
  version heading may remain.

---

## File Structure

- Modify `tests/test-release-history.py`: add changelog mutation coverage.
- Modify `tests/validate-content.py`: enforce the two-tier audited ledger.
- Modify `CHANGELOG.md`: apply the curated historical taxonomy.
- Modify `README.md`: rename and clarify the canonical history pointer.

### Task 1: Implement and Validate the Curated Changelog Ledger

**Files:**

- Modify: `tests/test-release-history.py`
- Modify: `tests/validate-content.py`
- Modify: `CHANGELOG.md`
- Modify: `README.md`

**Interfaces:**

- `tests/validate-content.py` remains a command-line validator that prints
  specific errors and exits nonzero when the package violates the contract.
- `tests/test-release-history.py` continues to validate copied package content
  through the command-line validator, without `.git` or network access.
- README canonical text becomes:

```markdown
## Version history

See [CHANGELOG.md](CHANGELOG.md) for unpublished package states, tagged
versions, and release notes.
```

- Changelog top-level taxonomy becomes:

```markdown
## Unreleased package states

### 0.12.0 (unreleased) - declared 2026-08-08; updated through 2026-08-12

## Tagged versions

### 0.10.0 - 2026-07-27
```

- Every version is a level-three heading under its taxonomy. Existing
  `Added` and `Changed` headings within 0.4.0 become level four.

- [ ] **Step 1: Add failing changelog contract tests**

Extend the sandbox fixture to preserve and restore `README.md`, `CHANGELOG.md`,
and `nori.json`. Keep the four README tests, updating them for the exact new
heading and link. Add mutations proving that validation rejects:

1. the current 0.12.0 package state represented as a tagged version;
2. an inserted fictional 0.3.3 tagged-version heading;
3. an omitted 0.2.1 tagged-version heading;
4. 0.10.0 dated 2026-07-24 rather than 2026-07-27;
5. `nori.json` current version diverging from the first unpublished state;
6. tagged headings placed out of strict reverse semantic-version order.

Run:

```bash
python3 tests/test-release-history.py
```

Expected before implementation: FAIL because the current pristine changelog
does not have the approved two-tier structure.

- [ ] **Step 2: Add the deterministic changelog validator**

In `tests/validate-content.py`, parse only level-three version headings within
the exact `## Unreleased package states` and `## Tagged versions` sections.
Compare parsed headings to these exact audited records:

```python
expected_unreleased = [
    ('0.12.0', '2026-08-08', '2026-08-12'),
    ('0.11.1', '2026-08-08', None),
    ('0.11.0', '2026-07-26', None),
    ('0.9.1', '2026-07-23', None),
    ('0.9.0', '2026-07-23', None),
    ('0.8.0', '2026-07-23', None),
]
expected_tagged = [
    ('0.10.0', '2026-07-27'),
    ('0.7.0', '2026-07-20'),
    ('0.6.1', '2026-07-20'),
    ('0.6.0', '2026-07-11'),
    ('0.5.1', '2026-07-09'),
    ('0.5.0', '2026-07-09'),
    ('0.4.4', '2026-07-08'),
    ('0.4.3', '2026-07-08'),
    ('0.4.2', '2026-07-08'),
    ('0.4.1', '2026-07-08'),
    ('0.4.0', '2026-07-08'),
    ('0.3.4', '2026-07-08'),
    ('0.3.2', '2026-07-08'),
    ('0.3.1', '2026-07-08'),
    ('0.2.1', '2026-07-08'),
]
```

Also enforce:

- each taxonomy heading occurs exactly once and in the approved order;
- the first unpublished version equals `nori.json`'s current version;
- tagged versions are unique and strictly descending by numeric semantic
  version;
- no level-two version heading remains;
- README has no `What changed` or `Release history` heading and contains the
  exact `Version history` heading and canonical link text.

Use distinct error strings for unpublished-ledger drift, tagged-ledger drift,
current-version mismatch, semantic-order drift, and README contract failures.

- [ ] **Step 3: Run the focused test and confirm the intended red state**

Run:

```bash
python3 tests/test-release-history.py
```

Expected: the pristine package test fails on the missing two-tier changelog,
demonstrating that the new validator is active before documentation changes.

- [ ] **Step 4: Curate `CHANGELOG.md`**

Add a short opening paragraph explaining the two classifications. Move the
complete 0.12.0, 0.11.1, 0.11.0, 0.9.1, 0.9.0, and 0.8.0 entries under
`## Unreleased package states`, using the exact headings represented by
`expected_unreleased`.

Move every tagged entry under `## Tagged versions`, use the exact headings and
dates represented by `expected_tagged`, and demote the nested 0.4.0 `Added` and
`Changed` headings to level four.

Create the 0.2.1 entry with only facts supported by its tagged manifest:

```markdown
- Established the original nine-skill infrastructure operations package for
  diagnostics, incidents, change management, RCA, observability, automation
  safety, runbooks, and capacity and risk review.
- Registered the initial Linux, Windows Server, network, pfSense, DNS/DHCP,
  Active Directory, VMware, Kubernetes/K3s, storage/backup, command-execution,
  risk, and interpretation references.
```

Merge every 0.3.0 bullet into 0.3.1 and every 0.3.3 bullet into 0.3.4 without
dropping the pre-existing 0.3.1 or 0.3.4 bullets. Remove the 0.3.0 and 0.3.3
headings.

- [ ] **Step 5: Align `README.md`**

Replace the current release-history heading and sentence with the exact
`Version history` interface above. Do not alter the final documentation-list
link to `CHANGELOG.md`.

- [ ] **Step 6: Run focused tests and documentation checks**

Run:

```bash
python3 tests/test-release-history.py
python3 tests/validate-content.py
git diff --check
```

Expected: all release-history mutations pass, content validation passes, and
the diff check is clean.

- [ ] **Step 7: Run the complete package gate**

Run through the project's proven Debian WSL route:

```bash
bash tests/validate-package.sh
```

Expected: `package validation passed`, with only existing explicitly reported
platform skips.

- [ ] **Step 8: Review and commit the integrated change**

Verify that the diff is limited to the four task files, no version metadata
changed, every expected heading appears once, and 0.3.0/0.3.3 headings are
absent. Commit with:

```bash
git commit -m "docs: curate truthful changelog history"
```
