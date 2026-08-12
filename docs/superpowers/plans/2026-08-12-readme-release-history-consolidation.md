# README Release-History Consolidation Implementation Plan

<!-- cspell:words classmethod pathlib pycache sandboxed -->

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `CHANGELOG.md` the single source of version history, shorten
`README.md`, and prevent duplicated release sections from returning.

**Architecture:** Add one deterministic documentation contract to the existing
content validator and cover it through a sandboxed mutation test. Then replace
the README's duplicated history with a contextual link and curate the few
missing facts and ordering correction into the changelog.

**Tech Stack:** Markdown, Python 3 `unittest`, the existing
`tests/validate-content.py` validator, Git Bash package validation.

## Global Constraints

- Keep package version 0.12.0; do not modify version metadata.
- Use `CHANGELOG.md` as the only version-by-version release-history source.
- Do not create `RELEASE-NOTES.md` or another release-history file.
- Preserve all accurate release facts unique to the current README.
- Do not preserve the inaccurate `9 parallel CI jobs` summary for 0.5.0.
- Keep the contextual changelog link where the README history is removed.
- Preserve the existing final `CHANGELOG` link in the README documentation list.
- Keep all delivered text in English.

---

## File Structure

- Modify `README.md`: replace sixteen duplicated version sections with one
  release-history pointer.
- Modify `CHANGELOG.md`: add two facts missing from its version entries, record
  the consolidation, and restore reverse version order around 0.5.1/0.5.0.
- Modify `tests/validate-content.py`: enforce the README release-history
  contract.
- Create `tests/test-release-history.py`: mutation tests for the contract.
- Modify `tests/validate-package.sh`: include the new regression suite in the
  complete package gate.

### Task 1: Consolidate and Guard Release History

**Files:**

- Modify: `README.md:276-412`
- Modify: `CHANGELOG.md:3-198`
- Modify: `tests/validate-content.py:596-607`
- Create: `tests/test-release-history.py`
- Modify: `tests/validate-package.sh:12-14`

**Interfaces:**

- Consumes: `tests/validate-content.py`'s existing `read(path)` and `err(message)`
  helpers and its process exit contract.
- Produces: a README contract requiring `## Release history`, the exact
  `[CHANGELOG.md](CHANGELOG.md)` relative link, and no heading beginning with
  `## What changed in v`.

- [ ] **Step 1: Write the failing mutation tests**

Create `tests/test-release-history.py` with this complete test harness:

```python
#!/usr/bin/env python3
"""Mutation tests for the README release-history contract."""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RELEASE_HEADING = "## Release history"
RELEASE_LINK = (
    "See [CHANGELOG.md](CHANGELOG.md) for version history and release notes."
)


class ReleaseHistoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tempdir = tempfile.TemporaryDirectory()
        cls.sandbox = Path(cls.tempdir.name) / "package"
        shutil.copytree(
            ROOT,
            cls.sandbox,
            ignore=shutil.ignore_patterns(
                ".git", ".worktrees", ".tmp", "__pycache__"
            ),
        )
        cls.readme = cls.sandbox / "README.md"
        cls.original = cls.readme.read_text(encoding="utf-8")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tempdir.cleanup()

    def tearDown(self) -> None:
        self.readme.write_text(self.original, encoding="utf-8")

    def run_validator(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "tests/validate-content.py"],
            cwd=self.sandbox,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_current_package_accepts_release_history_contract(self) -> None:
        result = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_legacy_version_heading_is_rejected(self) -> None:
        mutated = self.original.replace(
            RELEASE_HEADING,
            "## What changed in v9.9.9\n\n- Regression.\n\n" + RELEASE_HEADING,
            1,
        )
        self.readme.write_text(mutated, encoding="utf-8")
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("README.md duplicates release history", result.stdout)

    def test_missing_release_history_heading_is_rejected(self) -> None:
        self.readme.write_text(
            self.original.replace(RELEASE_HEADING, "## Releases", 1),
            encoding="utf-8",
        )
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("README.md missing release history heading", result.stdout)

    def test_missing_or_incorrect_changelog_link_is_rejected(self) -> None:
        self.readme.write_text(
            self.original.replace(
                RELEASE_LINK,
                "See [release notes](docs/releases.md) for version history.",
                1,
            ),
            encoding="utf-8",
        )
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("README.md missing canonical changelog link", result.stdout)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the focused test and verify the guard is absent**

Run:

```bash
python3 tests/test-release-history.py
```

Expected before implementation: FAIL because the legacy-heading mutation is
accepted by the current validator. The pristine test remains green.

- [ ] **Step 3: Add the deterministic validator contract**

Insert this block in `tests/validate-content.py` after the existing operator
documentation checks and before `if errors:`:

```python
readme_text = read('README.md')
release_history_heading = '## Release history'
release_history_link = (
    'See [CHANGELOG.md](CHANGELOG.md) for version history and release notes.'
)
if re.search(r'^## What changed in v', readme_text, re.MULTILINE):
    err('README.md duplicates release history; use CHANGELOG.md')
if not re.search(r'^## Release history$', readme_text, re.MULTILINE):
    err('README.md missing release history heading')
if release_history_link not in readme_text:
    err('README.md missing canonical changelog link')
```

- [ ] **Step 4: Replace the duplicated README sections**

Replace everything from `## What changed in v0.12.0` through the line before
`## Slash commands` with exactly:

```markdown
## Release history

See [CHANGELOG.md](CHANGELOG.md) for version history and release notes.

```

Keep `## Slash commands` and all later README content unchanged.

- [ ] **Step 5: Curate the changelog**

Add these exact bullets to their corresponding release sections:

```markdown
## 0.12.0 - 2026-08-08

- Consolidated version history in `CHANGELOG.md` and replaced duplicated README release sections with a canonical link.

## 0.11.1 - 2026-08-08

- Migrated CodeQL from v3 to v4 while preserving the exact Python and JavaScript/TypeScript analysis matrix.

## 0.9.1 - 2026-07-23

- Kept runtime selection portable without pinning Claude Code, Nori, or model versions.
```

Move the complete `## 0.5.1 - 2026-07-09` section, including every existing
bullet, so it appears immediately before `## 0.5.0 - 2026-07-09`. Do not alter
the text inside either moved section.

- [ ] **Step 6: Wire the regression suite into the package gate**

In `tests/validate-package.sh`, add the new suite immediately after content
validation:

```bash
python3 tests/validate-content.py
python3 tests/test-release-history.py
python3 tests/test-risk-taxonomy.py
```

- [ ] **Step 7: Run focused tests and documentation checks**

Run:

```bash
python3 tests/test-release-history.py
python3 tests/validate-content.py
npx --no-install markdownlint-cli2 README.md CHANGELOG.md \
  docs/superpowers/specs/2026-08-12-readme-release-history-consolidation-design.md \
  docs/superpowers/plans/2026-08-12-readme-release-history-consolidation.md
npx --no-install cspell README.md CHANGELOG.md \
  docs/superpowers/specs/2026-08-12-readme-release-history-consolidation-design.md \
  docs/superpowers/plans/2026-08-12-readme-release-history-consolidation.md \
  tests/test-release-history.py
```

Expected: four release-history tests pass, content validation passes, and both
documentation tools report zero issues.

- [ ] **Step 8: Run the complete package gate**

Run from Git Bash with its POSIX utility paths available:

```bash
export PATH="/usr/bin:/bin:$PATH"
bash tests/validate-package.sh
```

Expected: `package validation passed`, the command-guard security and mutation
gates pass, and all Python/Node suites report zero failures. Platform-specific
skips remain allowed when reported explicitly by their existing tests.

- [ ] **Step 9: Review the exact release-history diff**

Run:

```bash
git diff --check
git diff -- README.md CHANGELOG.md tests/validate-content.py \
  tests/test-release-history.py tests/validate-package.sh
rg -n '^## What changed in v|^## Release history|CHANGELOG.md' README.md
rg -n '^## 0\.(12\.0|11\.1|9\.1|5\.1|5\.0)' CHANGELOG.md
```

Expected: no `What changed` heading remains; the canonical release-history
heading and link appear once; 0.5.1 precedes 0.5.0; no unrelated file appears
in the implementation diff.

- [ ] **Step 10: Commit the implementation**

```bash
git add README.md CHANGELOG.md tests/validate-content.py \
  tests/test-release-history.py tests/validate-package.sh
git diff --cached --check
git commit -m "docs: consolidate release history in changelog"
```
