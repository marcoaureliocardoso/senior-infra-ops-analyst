# First-Class Subagents Design

## Context

The project currently stores its 12 Claude Code subagents as flat Markdown
files under `subagents/`. Current Nori upload behavior still accepts that
legacy representation, but extraction as independently versioned registry
components uses a directory package containing `SUBAGENT.md` and `nori.json`.
The operator selected first-class publication for all 12 subagents.
This decision supersedes only the flat subagent layout in ADR-006 and in the
canonical-manifest design; their root-manifest and staging-boundary decisions
remain in force.

## Decision

Each subagent becomes a canonical directory package:

```text
subagents/<subagent-id>/
├── SUBAGENT.md
└── nori.json
```

Every subagent manifest contains exactly these project-required fields:

- `name`: identical to the directory ID and the `SUBAGENT.md` frontmatter name;
- `version`: initial independent component version `1.0.0`;
- `type`: `subagent`;
- `description`: identical to the `SUBAGENT.md` frontmatter description.

Repository validation rejects flat `subagents/*.md`, directory packages without
either required file, invalid IDs or semantic versions, unexpected manifest
fields, manifest/frontmatter identity drift, and duplicate flat/directory
representations. Directory discovery is the only canonical source used by
content validation, package staging, context inventory, live-smoke fixtures,
and installed-artifact comparison.

## Runtime and installation boundary

The source and upload format is directory based. Claude Code's installed form
remains flat: Nori installs each canonical `SUBAGENT.md` as
`.claude/agents/<subagent-id>.md`. Tests must compare the installed flat file
with its canonical source by meaning and must not require a directory inside
`.claude/agents/`.

The root manifest does not declare the 12 local packages in
`dependencies.subagents` before publication. Current Nori upload synchronization
adds extracted or linked subagent versions to that map only after a successful
registry upload.
This prevents the source manifest from claiming registry dependencies that do
not yet exist.

## Cross-reference migration

Current executable consumers and current architecture documentation move from
`subagents/*.md` or `subagents/<id>.md` to
`subagents/*/SUBAGENT.md` or `subagents/<id>/SUBAGENT.md`. Historical review
records and superseded implementation plans retain their original paths because
they describe the repository state at the time of those records.

The Nori package smoke test must prove all of the following:

- staging contains exactly 12 directory-based subagent packages;
- every package has a valid first-class `nori.json`;
- the loader installs exactly 12 flat Claude Code agent files;
- every installed definition matches the corresponding canonical
  `SUBAGENT.md` after normalizing Nori's expected `{{skills_dir}}` resolution;
- skills, slash commands, root instructions, and operator-owned content remain
  unaffected.

## Versioning and publication

Each new subagent component starts at `1.0.0`, matching Nori's extraction
default and the project's existing first-class skill convention. The skillset
remains in the already-unreleased `0.12.0` package state; this migration is
recorded in that section of `CHANGELOG.md` without creating a tag or release.

Repository migration, tests, staging validation, and a dry-run-capable upload
check are in scope. A registry upload remains an external side effect and is
performed only after the final package has passed review and the operator has
confirmed the target and upload action.

## Acceptance criteria

- All 12 subagents use the canonical directory package and `type: subagent`.
- Manifest name, version, type, and description are validated against source.
- No active executable or current architecture reference expects a flat source
  subagent file.
- Canonical staging contains the 12 manifests and definitions without extra
  repository content.
- Isolated installation produces the expected 12 Claude Code agent files and
  preserves their runtime policies, resolved hooks, skill preloads, and command
  routing semantically.
- Focused tests, the complete package gate, diff hygiene, and independent review
  pass on the final commit.
