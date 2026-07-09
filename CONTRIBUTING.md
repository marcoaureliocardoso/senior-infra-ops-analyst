# Contributing

Before proposing a change:

1. Keep operational instructions evidence-based and approval-gated.
2. Use shared risk vocabulary from `references/risk-levels.md`.
3. Do not add commands that expose secrets, personal data, or broad inventories without modifiers and safety notes.
4. Run `bash tests/validate-package.sh` locally before committing. This validates content integrity, manifest structure, CI workflow quality, and permission hygiene.
5. Add or update templates when a skill requires a structured output.
6. Prefer official vendor documentation and standards in `references/external-sources.md`.

## Validation

The project has a multi-layer validation pipeline:

| Layer | Command | What it checks |
|-------|---------|---------------|
| Content | `bash tests/validate-package.sh` | Manifest integrity, skill metadata, template quality, cross-references, permission hygiene |
| Schema | `python3 tests/validate-schema.py` | `nori.json` structural integrity, semver, no TBD placeholders |
| CI | `bash tests/validate-ci-workflows.sh` | Workflow permissions, concurrency, pinned versions, hash-pinned actions |
| Links | `bash tests/validate-links.sh` | External URL reachability across all markdown files |
| Links JSON | `bash tests/validate-links.sh --json` | Machine-readable link report for CI automation |

CI runs all validators on every PR and push to main. See `.github/workflows/ci.yml`.

## Document conventions

This project follows **AI-first document conventions** — formatting is optimized for LLM consumption, not human readability. See `AGENTS.md` for the full rationale. Key points:

- Blank lines between headings and lists are intentionally omitted (MD032 disabled)
- Bare URLs are preferred over `[text](url)` links (MD034 disabled)
- Markdownlint rules that conflict with token efficiency are disabled in `.markdownlint.json`

A change is not ready if it introduces a second diagnostic order, a local risk taxonomy, an empty template, or unvalidated helper script behavior.
