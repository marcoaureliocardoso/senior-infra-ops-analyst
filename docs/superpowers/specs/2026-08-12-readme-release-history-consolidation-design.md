# README Release-History Consolidation Design

## Context

`README.md` contains sixteen `What changed in v*` sections covering versions
0.4.1 through 0.12.0. They occupy about 137 lines and duplicate the more
complete release history already maintained in `CHANGELOG.md`.

The operator approved a curated consolidation into the existing changelog. No
new release-notes file will be introduced.

## Decision

Make `CHANGELOG.md` the single source of truth for version history and release
notes. Replace all consecutive `What changed in v*` sections in `README.md`
with this short section in the same location:

```markdown
## Release history

See [CHANGELOG.md](CHANGELOG.md) for version history and release notes.
```

Keep the existing `CHANGELOG` entry in the README's final documentation links.
The contextual link above is intentional because it replaces the removed
history where readers encounter it.

## Curated Reconciliation

Do not copy the README summaries verbatim into the changelog. The changelog
already contains the same information in greater detail for almost every
version. Preserve only facts that are explicit in the README but not explicit
in the corresponding changelog entry:

- For 0.11.1, record that the CodeQL v3-to-v4 migration preserved the exact
  Python and JavaScript/TypeScript matrix.
- For 0.9.1, record that runtime selection remained portable without pinning
  Claude Code, Nori, or model versions.

Do not preserve the README's `9 parallel CI jobs` wording for 0.5.0. Its list
names only eight checks, while the changelog already provides the precise
workflow and job breakdown. The more specific changelog record remains
authoritative.

Move the 0.5.1 changelog section before 0.5.0 so all versions remain in reverse
semantic-version order. Preserve every bullet and release date during the
move.

Add one 0.12.0 changelog bullet noting that release history was consolidated
into the changelog and the README was shortened.

## Validation Contract

Extend deterministic content validation so future changes cannot restore the
duplication unnoticed:

- reject any `## What changed in v` heading in `README.md`;
- require the `## Release history` heading and the exact relative
  `[CHANGELOG.md](CHANGELOG.md)` link;
- add mutation-style unit coverage showing that a legacy version heading or a
  missing/incorrect link fails validation.

Run the complete package validation gate after implementation. Markdown lint,
spell checking, internal-link validation, content validation, schema checks,
and the existing safety suites must remain green.

## Versioning

Keep package version 0.12.0. It is still unreleased, and this documentation
consolidation belongs to the existing release rather than a new patch release.
No package manifest or version metadata changes are required.

## Acceptance Criteria

- `README.md` contains no version-by-version `What changed` sections.
- The replacement release-history section links directly to `CHANGELOG.md`.
- No accurate release fact unique to the README is lost.
- `CHANGELOG.md` is in reverse semantic-version order around 0.5.1 and 0.5.0.
- Deterministic validation prevents the duplicated README history from
  returning.
- Package version remains 0.12.0 and the complete package gate passes.
