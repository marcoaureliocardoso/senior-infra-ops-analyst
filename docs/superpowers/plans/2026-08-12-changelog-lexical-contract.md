# Changelog Lexical Version Contract Plan

<!-- cspell:words blockquote blockquotes CommonMark prerelease Setext -->

> **For agentic workers:** REQUIRED SUB-SKILL: Use systematic debugging and
> test-driven development. Preserve red and green evidence in the task report.

**Goal:** Replace fragile partial CommonMark interpretation with a small,
conservative lexical contract for version-bearing changelog lines.

**Architecture:** Retain the existing strict fenced-code state. For each line
outside a valid fence, derive its first meaningful content after the limited
leading indentation and repeated block-container prefixes used by blockquotes
and list items. A line whose meaningful content begins directly with a complete
SemVer, or with ATX markers followed by a complete SemVer, is version-bearing.
Every version-bearing line must be an unindented root-level canonical `###`
heading consumed exactly once by the audited unpublished or tagged ledger.
All other version-bearing forms fail closed.

This is intentionally not a Markdown parser. It does not decide whether an
arbitrary sequence renders as a heading. It enforces the narrower project rule
that version numbers may begin a non-fenced changelog line only in the approved
canonical ledger headings.

## Global Constraints

- Keep package version 0.12.0 and every changelog fact/date unchanged.
- Do not create or move Git tags or GitHub Releases.
- Modify only `tests/test-release-history.py` and `tests/validate-content.py`.
- Keep validation deterministic, network-free, and independent of `.git`.
- Preserve exact fence opening/closing behavior, including invalid backtick
  info-string and unclosed-fence rejection.
- Use one reusable full SemVer expression supporting prerelease and build
  metadata and rejecting leading-zero numeric core identifiers.
- Do not add a Markdown parser dependency or reconstruct Setext paragraphs.
- Use `apply_patch` and red-green TDD.

### Task 1: Replace Partial Markdown Parsing with the Lexical Contract

**Files:**

- Modify: `tests/test-release-history.py`
- Modify: `tests/validate-content.py`

## Required Behavior

Outside valid fences, reject all noncanonical version-bearing lines, including:

```markdown
0.3.3 - 2026-07-08
### 0.3.3-rc.1 - 2026-07-08
### 0.3.3+build.7 - 2026-07-08
> ### 0.3.3 - 2026-07-08
- ### 0.3.3 - 2026-07-08
1. 0.3.3 - 2026-07-08
> - ### 0.3.3 - 2026-07-08
```

Accept all audited root-level canonical headings exactly as they exist. Ignore
version-bearing examples inside valid backtick and tilde fences. Permit prose
whose first meaningful token is not SemVer, for example:

```markdown
Version 0.3.4 introduced new validation.
- Version 0.3.4 remains documented here.
```

## Scanner Contract

- Preserve the existing strict fence state and unclosed-fence error.
- Outside fences, inventory exact unindented root ATX headings used for the two
  taxonomies and the audited version ledgers.
- Separately normalize only block-container prefixes for version-bearing-line
  detection: up to three leading spaces, repeated blockquote markers, and one
  unordered or ordered list marker per nesting layer, with required separator
  whitespace where CommonMark requires it.
- After container normalization, detect either direct SemVer or one through six
  ATX markers plus whitespace followed by SemVer.
- A detected line is accepted only if its original raw form is the exact
  canonical root `###` heading parsed into the correct taxonomy ledger.
- Remove Setext paragraph buffering and all logic that attempts to combine
  adjacent Markdown blocks.

## TDD and Verification

- [ ] Add failing mutations for blockquote, unordered-list, ordered-list,
  nested-container, prerelease, and build-metadata witnesses.
- [ ] Change the previous paragraph-boundary acceptance tests to reflect the
  approved strict rule: direct version-leading prose outside fences is rejected;
  `Version ...` prose remains accepted.
- [ ] Observe the new focused tests fail for the expected missing lexical
  detection before changing production validation.
- [ ] Implement the smallest lexical scanner and remove the Setext paragraph
  reconstruction.
- [ ] Run all release-history tests, content validation, and `git diff --check`.
- [ ] Run the complete Debian WSL package gate.
- [ ] Self-review the exact two-file diff and commit as
  `fix: enforce lexical changelog versions`.
