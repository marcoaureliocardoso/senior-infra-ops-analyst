# ADR-007 — First-class Nori subagent packages

- **Status:** Accepted
- **Date:** 2026-08-13
- **Scope:** Source, upload, and installed representation of all 12 subagents

## Context

The repository stored subagents as `subagents/<name>.md`. Nori continues to
support that legacy form, but its current first-class subagent lifecycle uses a
directory containing `SUBAGENT.md` and `nori.json`. During upload, choosing
extraction for a flat definition causes Nori to restructure the source tree.
Keeping the legacy form therefore delayed the canonical representation until an
external upload and left individual version, identity, and description metadata
implicit.

## Decision

Store every project subagent as:

```text
subagents/<name>/
├── SUBAGENT.md
└── nori.json
```

Every component manifest contains exactly `name`, `version`, `type`, and
`description`. The initial version is `1.0.0`, `type` is `subagent`, and name
and description must match the directory and frontmatter exactly. Flat source
definitions are rejected.

The repository does not synthesize root `dependencies.subagents` before
publication. Nori owns that registry-dependency synchronization after a
successful upload of extracted or linked subagents.

## Source and installed boundaries

`subagents/<name>/SUBAGENT.md` is the canonical source consumed by validators,
package staging, context inventory, and semantic comparison. For Claude Code,
Nori installs the definition as `.claude/agents/<name>.md`. The installed flat
format is a runtime projection, not a second source representation.

## Enforcement points

- `scripts/nori_package.py` discovers directory packages, resolves canonical
  definitions, validates exact manifest fields, and rejects legacy flat files.
- `tests/validate-content.py` uses canonical discovery for frontmatter, skill
  preload, command routing, hooks, and runtime-policy checks.
- `skills/context-continuity/scripts/context-inventory.mjs` measures only
  directory-based subagents with matching first-class manifests.
- `tests/validate-installed-subagents.py` compares installed flat definitions
  with the canonical `SUBAGENT.md` sources after normalizing Nori's expected
  `{{skills_dir}}` resolution.
- Staging, archive, and isolated Nori smoke tests require 12 manifests, 12
  canonical definitions, no legacy source files, and semantically equivalent
  installed content.

## Compatibility

Subagent IDs, frontmatter, tools, hooks, skill preloads, `maxTurns`, command
routing, and installed filenames do not change. Only the repository/upload
representation changes. Historical reviews and superseded implementation plans
retain their original path statements as evidence of the state they evaluated.

## Consequences

- Each subagent can participate in Nori's independent version, conflict, and
  registry lifecycle.
- Upload no longer needs to perform a destructive flat-to-directory migration.
- Twelve additional manifests become part of canonical staging and archives.
- Component versions must be maintained deliberately when definitions change.

## Validation

Acceptance requires strict manifest mutation tests, source-policy regression
tests, content validation, context inventory tests, staging and archive checks,
an isolated Nori install that proves the flattening boundary, the complete
package gate, and independent review of the final commit.

## Rollback

Rollback requires a superseding ADR because returning to flat files removes the
first-class component boundary. If registry publication has already occurred,
rollback must also account for published component versions and root dependency
state rather than only moving files.
