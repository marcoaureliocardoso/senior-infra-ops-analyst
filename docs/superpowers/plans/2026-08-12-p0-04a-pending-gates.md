# P0-04A Pending Acceptance and Merge Gates Implementation Plan

<!-- cspell:words Pendências atuais aceite PENDENTE -->

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish one consistent, evidence-backed list of the remaining P0-04A acceptance and merge gates.

**Architecture:** The definitive non-versioned roadmap carries the full current-state matrix, while ADR-005 and the validation notes carry architectural and evidence-specific views of the same five gates. PR #32 receives a concise checklist and remains draft; no behavior, acceptance criterion, merge state, or completion checkbox changes.

**Tech Stack:** Markdown, Git, GitHub CLI, existing Python document validators, markdownlint-cli2.

## Global Constraints

- Limit the list to P0-04A acceptance and merge work; exclude credential cleanup and unrelated operations.
- Record only `complete_pair=false` for the fourth run; never infer `no_pre` from deleted structural evidence.
- Treat sanitized structural classification as a diagnostic improvement, not a substitute for the required ordered real pair.
- Do not revise the acceptance criterion without explicit operator approval.
- Do not merge PR #32 or mark P0-04A complete.
- Do not retain transcript, prompt, summary, raw hook input, credential, or secret.

---

### Task 1: Consolidate the canonical pending-gate matrix

**Files:**
- Modify: `C:/projects/senior-infra-ops-analyst/TODO-AI-FIRST.md`
- Modify: `docs/architecture/ADR-005-context-continuity-and-preventive-compaction.md`
- Modify: `tests/validation-notes.md`

**Interfaces:**
- Consumes: the approved matrix in `docs/superpowers/specs/2026-08-12-p0-04a-pending-gates-design.md`.
- Produces: consistent roadmap, architectural, and evidence-specific statements of the five remaining gates.

- [ ] **Step 1: Add the full current-state matrix to the definitive roadmap**

Insert a `**Pendências atuais de aceite e merge:**` section after the P0-04A
acceptance criteria. Include exactly these five states and completion
conditions:

1. real ordered automatic pair still unobserved;
2. sanitized `complete_pair`, `pre_only`, or `no_pre` classification still
   unavailable after cleanup;
3. explicit operator decision required before any alternative acceptance;
4. independent review and CI/Security required on the exact final head;
5. merge to `main` required before changing P0-04A from `PENDENTE`.

Keep `## [ ] P0-04A`, `**Status:** PENDENTE`, every existing action checkbox,
and every existing mandatory-test checkbox unchanged.

- [ ] **Step 2: Add the architectural pending gates to ADR-005**

Add a `## Pending acceptance and merge gates` section before consequences.
State the same five gates, explicitly distinguishing the sanitized
classification improvement from the real ordered-pair acceptance result.

- [ ] **Step 3: Add the evidence-specific pending gates to validation notes**

Add a `### Remaining P0-04A acceptance and merge gates` section after the
fourth-run evidence. Preserve the observed `1000000`, 10%, 5%, 600 seconds,
approximately 855 seconds overall, `BLOCKED`, cleanup, and
`complete_pair=false` facts. Do not classify the result as `pre_only` or
`no_pre`.

- [ ] **Step 4: Run focused document validation**

Run:

```powershell
git diff --check
python tests/test-architecture-docs.py
python tests/validate-content.py
$env:npm_config_cache = Join-Path $env:TEMP 'p004a-markdownlint-cache'
npx --yes markdownlint-cli2@0.23.2 docs/architecture/ADR-005-context-continuity-and-preventive-compaction.md tests/validation-notes.md docs/superpowers/specs/2026-08-12-p0-04a-pending-gates-design.md docs/superpowers/plans/2026-08-12-p0-04a-pending-gates.md
```

Expected: clean diff, 7/7 architecture tests, content validation passed, and
zero markdownlint issues. Separately inspect the non-versioned roadmap to prove
that its P0-04A heading, status, and checkboxes remain open.

- [ ] **Step 5: Request independent read-only review**

Ask the reviewer to verify exact consistency across the roadmap, ADR, and
validation notes; absence of acceptance weakening; honest
`pre_only`/`no_pre` uncertainty; and unchanged completion state.

- [ ] **Step 6: Commit the versioned documentation**

Run:

```powershell
git add docs/architecture/ADR-005-context-continuity-and-preventive-compaction.md tests/validation-notes.md
git commit -m "docs(context): enumerate pending release gates"
```

Do not add `C:/projects/senior-infra-ops-analyst/TODO-AI-FIRST.md`; it is
deliberately outside the repository.

### Task 2: Publish and verify the exact PR state

**Files:**
- Modify externally: PR #32 description.

**Interfaces:**
- Consumes: the reviewed Task 1 matrix and resulting Git head.
- Produces: a draft PR checklist whose pending and completed states match the documentation and remote checks.

- [ ] **Step 1: Push the existing feature branch**

Push `agent/p0-04a-context-continuity` without force and confirm the remote head
equals the local head.

- [ ] **Step 2: Update the PR checklist**

Keep the PR draft. Add the five-gate checklist, leaving the real automatic pair,
alternative acceptance decision, final-head review/checks, merge, and roadmap
completion unchecked until their exact conditions are met. Mark the sanitized
classification item as an optional diagnostic improvement, never as evidence
that acceptance passed.

- [ ] **Step 3: Wait for CI and Security on the new head**

Use the GitHub workflow status for the exact commit. If a check fails, inspect
its logs before changing files; rerun only a proven transient external failure.

- [ ] **Step 4: Perform final local and remote verification**

Confirm:

- the worktree is clean and local/remote heads match;
- PR #32 is open, draft, unmerged, and targets `main`;
- the PR still shows the ordered automatic pair as pending;
- the roadmap still shows P0-04A as pending;
- CI and Security are successful on the exact final head.
