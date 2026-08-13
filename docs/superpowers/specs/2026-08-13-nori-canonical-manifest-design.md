# Canonical Nori Manifest and Reproducible Staging Design

## Context

The repository is the linked development source for the
`personal/senior-infra-ops-analyst` Nori profile. Its current `nori.json`
duplicates inventories that Nori discovers from the filesystem and uses a
legacy shape for search terms and skill dependencies. The current local
validators encode that repository-specific shape, so applying the external
handoff literally would break the package gate even though the proposed
manifest is closer to the documented Nori contract.

The existing upload staging directory was assembled manually. It contains the
manifest, license, catalog, skills, references, slash commands, and subagents,
but omits `AGENTS.md`. The omission is not caused by Git, `.gitignore`, a
symlink, or the Nori 0.31 packaging filter. It is an incomplete manual
allowlist. A package without `AGENTS.md` can distribute individual assets while
omitting the shared operating, safety, authorization, continuity, and routing
instructions that make them a coherent skillset.

The repository has no tracked root `CLAUDE.md`. This is intentional:
`AGENTS.md` is the portable skillset source, while Nori installs its managed
content into the agent-specific destination, including `CLAUDE.md` for Claude
Code.

## Decision

Use one canonical, upload-ready package contract in the repository. Do not
maintain a richer repository manifest and rewrite it only in staging.

The repository will contain:

- one portable instruction source in root `AGENTS.md`;
- one canonical `nori.json` aligned with the documented Nori schema;
- filesystem-backed skills, references, slash commands, and subagents;
- `skills.json` as the version-selection catalog used by this project;
- deterministic validation and staging-generation code.

The staging directory is a disposable projection of those versioned sources.
Before a Nori command runs, every staged file must be byte-identical to its
repository source. A documented CLI migration during a real upload may mutate
the disposable staging copy, but that change is captured as evidence and is
never promoted automatically into the repository.

## Canonical Manifest Shape

The source `nori.json` retains the documented descriptive and identity fields:

- `name`;
- `version`;
- `description`;
- `author`;
- `license`;
- `repository`;
- `keywords`;
- `dependencies`.

The migration makes these exact semantic changes:

- rename `tags` to `keywords` without silently dropping or adding terms;
- represent `dependencies.skills` as
  `{ "read-the-damn-docs": "latest" }`;
- remove `type`, because Nori owns package-type normalization;
- remove `skills`, because Nori discovers `skills/*/SKILL.md`;
- remove `subagents`, because Nori discovers packaged subagent definitions;
- remove `references`, because references are package files reached from
  `AGENTS.md`, not registry inventory metadata;
- remove `homepage` and `bugs`, which are not part of the selected canonical
  contract.

The referenced files and subagent descriptions are not deleted. Their source
of truth moves from duplicated manifest entries to their filesystem artifacts.
The `skills.json` catalog remains and must agree with the discovered skill
directories.

The locally observed Nori 0.31 real-upload path may backfill `type` in the
staging directory after dry-run handling. This does not justify keeping the
field in the source manifest. Validation records any such normalization and
requires the repository source to remain unchanged.

## Package Boundary

The staging generator copies only this allowlist:

```text
AGENTS.md
LICENSE
nori.json
skills.json
references/
skills/
slashcommands/
subagents/
```

It excludes repository operations, tests, development documentation, release
history, local profile metadata, installed agent output, and generated state,
including:

```text
.git/
.worktrees/
.claude/
.github/
docs/
tests/
README.md
CHANGELOG.md
Makefile
profile.json
.nori-version
```

The generator does not use `.gitignore` as the package contract. It rejects
symlinks and reparse points, refuses unsafe or overly broad destinations, and
does not read or copy credentials, Nori authentication state, Claude settings,
or operator preferences.

## Components and Boundaries

### Manifest and content validation

Repository validators stop requiring the removed inventory fields. They derive
the package inventory from the filesystem and enforce these relationships:

- every `skills/*/SKILL.md` has a unique skill directory and a matching
  `skills.json` entry;
- every `skills.json` entry resolves to a packaged skill;
- references required by `AGENTS.md` exist under `references/`;
- every packaged subagent has valid metadata and a unique identity;
- every slash command is syntactically valid and references only available
  package assets;
- `AGENTS.md` exists, is non-empty, and contains the project identity and the
  required safety sections;
- no root `CLAUDE.md` is used as a substitute for the canonical source.

### Staging generation

One versioned command creates a fresh staging tree from the allowlist and then
validates it. It emits a deterministic inventory containing relative path,
byte size, and SHA-256 for review. The inventory is evidence only and is not
included in the upload package.

The operation validates the resolved destination before replacing an existing
staging tree. It may replace only the explicitly supplied staging directory;
it must refuse the repository root, workspace root, home directory, filesystem
root, or any destination containing unexpected files outside its managed
boundary.

### Nori integration validation

CLI validation uses an isolated install target and a temporary profile name. It
must not relink `personal/senior-infra-ops-analyst`, overwrite the operator's
global `CLAUDE.md`, or read authentication material into logs.

The integration smoke test verifies that Nori:

1. parses the staged skillset and discovers its assets;
2. reads staged `AGENTS.md` as the configuration source;
3. installs that content inside one managed block at the Claude-specific
   `CLAUDE.md` destination;
4. appends the generated skills catalog without losing the canonical content;
5. preserves unmanaged destination content outside the managed block.

`upload --dry-run` is an authenticated external interaction and is run only
after explicit operator authorization. It is not treated as proof of all
real-upload migrations because the observed CLI returns before its backfill
and rename operations.

## Test Strategy

Implementation follows test-driven development. Mutation cases must first
demonstrate failures for:

- missing or empty `AGENTS.md`;
- a root `CLAUDE.md` accepted in place of `AGENTS.md`;
- legacy `tags` or array-shaped skill dependencies;
- reintroduction of removed inventory fields;
- a missing, extra, or duplicated skill catalog entry;
- a referenced file missing from the package;
- an invalid or duplicated subagent;
- an unexpected staged file;
- a symlink or reparse point anywhere in the staged tree;
- a staged file whose bytes differ from the repository source;
- an unsafe staging destination;
- an installed Claude file that omits, duplicates, or alters the managed
  canonical instructions.

Focused schema and content tests run before the complete package gate. The
final local gate runs under the repository's proven Debian WSL route. GitHub CI
and Security must pass on the exact final commit before merge.

## Versioning and Publication

Manifest correction and reproducible packaging are repository changes, but
they do not themselves authorize registry publication, tag creation, or a
GitHub Release. Before selecting the final version, the workflow checks the
registry for whether `0.12.0` is already published and reconciles that result
with `.nori-version`, the changelog's unpublished package state, and the Git
tag history.

Any required version bump updates all version-bearing repository files in one
reviewed change. Upload, tag, and release remain separate external-side-effect
gates requiring explicit operator authorization.

## Failure Handling and Rollback

- A contract or content mismatch fails before staging is generated.
- A staging mismatch fails before any Nori link, install, or upload action.
- A CLI-created staging mutation is reported with a sanitized diff.
- The active Nori profile and operator configuration are never used as a test
  destination.
- Rollback removes only the validated disposable staging directory and the
  isolated worktree or branch. It does not rewrite operator configuration.
- The pre-existing untracked handoff remains untouched until its validated
  findings are deliberately incorporated into versioned documentation.

## Non-Goals

- Publishing the skillset to a personal or public registry.
- Logging in to Nori or changing the active linked profile.
- Creating a Git tag or GitHub Release.
- Packaging tests, repository documentation, CI workflows, or release notes.
- Maintaining a checked-in Claude-specific copy of the shared instructions.
- Changing skill, command, reference, or subagent behavior unrelated to package
  conformance.

## Acceptance Criteria

- The repository has one canonical, documented `nori.json` contract.
- `AGENTS.md` is required in every generated package and remains the only
  checked-in root instruction source.
- Manifest inventory duplication is removed without weakening filesystem and
  cross-file validation.
- The staging tree is reproducible from a versioned allowlist and contains no
  unexpected file, symlink, reparse point, credential, or local preference.
- Every pre-CLI staged file is byte-identical to its repository source.
- An isolated Nori installation produces a Claude managed block containing the
  complete canonical instructions plus the generated skill catalog.
- The active profile and operator files remain unchanged.
- Focused tests, mutation tests, the complete Debian WSL package gate, and
  GitHub CI and Security pass on the final commit.
- Independent review finds no Critical or Important issue.
- Registry upload, tag creation, and release remain blocked until separately
  authorized.
