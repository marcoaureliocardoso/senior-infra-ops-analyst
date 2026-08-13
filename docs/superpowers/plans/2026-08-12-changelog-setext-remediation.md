# Changelog Multiline Setext Remediation Plan

<!-- cspell:words CommonMark Setext multiline -->

> **For agentic workers:** REQUIRED SUB-SKILL: Use systematic debugging and
> test-driven development. Preserve red and green evidence in the task report.

**Goal:** Close the residual multiline Setext-heading bypass in the curated
changelog validator without broadening the historical or versioning scope.

**Root cause:** `markdown_heading_inventory()` recognizes a Setext version
heading only when a version-shaped line is immediately followed by its
underline. A CommonMark Setext heading can contain multiple contiguous content
lines before the underline, so the version-shaped first line is lost when the
scanner inspects only the final content line.

**Architecture:** Extend the existing fence-aware heading inventory to retain
or reconstruct the contiguous paragraph immediately preceding a Setext
underline. If the resulting real Setext heading starts with a semantic version,
record and reject it through the existing Setext error path. Do not introduce a
Markdown dependency, network access, or `.git` dependency.

## Global Constraints

- Keep package version 0.12.0 and all audited changelog facts unchanged.
- Do not create or move tags or GitHub Releases.
- Modify only `tests/test-release-history.py` and `tests/validate-content.py`.
- Preserve valid fenced-code behavior and the existing 23 mutation tests.
- Keep validation deterministic, network-free, and package-copy compatible.
- Use `apply_patch` for edits and follow red-green TDD.

### Task 1: Detect Multiline Version-Shaped Setext Headings

**Files:**

- Modify: `tests/test-release-history.py`
- Modify: `tests/validate-content.py`

- [ ] Add a mutation using this exact witness and observe it pass incorrectly
  before changing the validator:

```markdown
0.3.3 - 2026-07-08
continued
---
```

- [ ] Add boundary coverage proving a blank line ends the candidate paragraph,
  valid fenced examples remain ignored, and two- and three-line Setext version
  headings with 0-3 leading spaces fail closed.
- [ ] Implement the smallest fence-aware paragraph reconstruction needed to
  recognize the complete Setext heading and feed it to the existing version
  inventory. Do not add a general Markdown renderer.
- [ ] Run `python tests/test-release-history.py`,
  `python tests/validate-content.py`, and `git diff --check`.
- [ ] Run the complete package gate through the proven Debian WSL route.
- [ ] Self-review the exact two-file diff and commit as
  `fix: detect multiline Setext versions`.
