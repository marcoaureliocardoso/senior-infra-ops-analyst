# ADR-006: Canonical Nori package boundary

- Status: Accepted
- Date: 2026-08-13

## Context

The repository previously mixed registry metadata, asset inventories, and
local build files in the root manifest and in an ad hoc upload directory. That
made the package contract ambiguous, allowed the staged tree to drift from the
repository, and omitted the canonical `AGENTS.md` instruction source.

## Decision

### Canonical manifest

Root `nori.json` contains exactly `name`, `version`, `description`, `author`,
`license`, `dependencies`, `keywords`, and `repository`. It describes registry
identity, search metadata, and declared dependencies. It is not an asset
inventory. Legacy `tags`, root `type`, and embedded skills, references, or
subagents lists are rejected.

`AGENTS.md` is the sole canonical root instruction source. A root `CLAUDE.md`
is rejected because the Nori installer generates the agent-specific managed
form at installation time.

### Filesystem discovery

Skills are discovered from `skills/*/SKILL.md`, references from
`references/*.md`, and subagents from `subagents/*.md`. `skills.json` remains
the tier/version catalogue and must match the discovered skill directories.
Subagent frontmatter names must match their filenames.

### Staging allowlist

The upload staging root contains only `AGENTS.md`, `LICENSE`, `nori.json`,
`skills.json`, `references/`, `skills/`, `slashcommands/`, and `subagents/`.
The builder copies these sources into an atomic sibling temporary directory,
computes a deterministic path/size/SHA-256 inventory, and then installs the
completed tree. `--replace` requires the existing tree to match the complete
current canonical inventory. It preserves the unresolved caller path, rejects
linked or reparse ancestors, atomically moves the directory aside, revalidates
the moved object, and restores it if content arrived during the scan/copy
window. The staging directory is disposable output, never an editable source.

### Symlinks and reparse points

Symlinks and Windows reparse points are rejected in both source and staging.
Traversal outside the selected roots, sensitive filename patterns, special
files, and inventory mismatches fail closed.

### Isolated Nori validation

The live smoke detects current CLI capabilities instead of pinning a Nori
version. It uses temporary home, XDG, install, staging, and local profile paths;
links with a bare local name; switches the resulting `personal/` identity for
`claude-code`; and verifies exactly one managed instruction block, canonical
content, one generated skills section, preserved unmanaged content, and
cleanup. It also proves all 25 packaged skill identities, all 12 subagents, and
all 20 slash commands, while allowing only declared skill dependencies and the
runtime-owned `nori-info` helper beyond the packaged skill set. No operator
profile or preference is selected or modified.

## Enforcement points

- `scripts/nori_package.py` owns manifest validation, filesystem discovery,
  staging allowlisting, path safety, and deterministic inventories.
- `scripts/build_nori_staging.py` exposes build and check-only operations.
- `scripts/build_nori_archive.py` creates a fresh deterministic archive,
  verifies every archived digest, rejects source/staging overlap and linked or
  reparse output paths, and atomically installs the completed ZIP.
- `tests/validate-schema.py` and `tests/validate-content.py` consume the shared
  contract rather than maintaining parallel inventories.
- `make stage` validates first; `make package` archives only the staged tree.
- Deterministic mutation tests and the isolated live smoke enforce the same
  boundary in CI and local validation.

## External side effects

Building, checking, packaging, linking in the disposable smoke, and rendering
inventory evidence are local operations. They do not authenticate, upload,
publish, tag, release, or modify the operator's active Nori profile. An
authenticated Nori dry-run requires separate operator authorization. A real
upload requires its own later authorization and is outside this decision.

## Alternatives rejected

- Keeping asset arrays in `nori.json`: duplicates the filesystem and drifts.
- Treating generated `CLAUDE.md` as a repository source: reverses the Nori
  normalization boundary and risks duplicate managed content.
- Copying the repository wholesale: includes build, test, Git, or secret-prone
  material outside the registry package.
- Following links while staging: weakens containment and reproducibility.
- Updating an unknown destination destructively: could remove operator files.

## Validation evidence

Focused manifest, discovery, staging, CI-policy, and safety mutation suites
exercise missing, extra, malformed, linked, sensitive, and drifted content.
The real isolated Nori smoke on 2026-08-13 observed canonical content, one
managed block, one generated skills section, preserved unmanaged content, and
successful cleanup with the runtime-detected CLI.

## Consequences and limitations

New package assets must live under an allowlisted source root and satisfy its
filesystem contract. Root build and documentation files remain outside upload
staging. `--replace` is intentionally conservative: a stale or unknown
destination is never deleted. Use another destination or explicitly preserve
and remove the old tree outside the builder before regeneration.

The live smoke proves local link/switch normalization, not registry acceptance
or remote publication. Those remain separately authorized operations.

## Rollback

Revert the implementation commits and regenerate staging from the restored
repository contract. Existing staging is disposable and can be replaced only
after the builder confirms complete byte identity with the current canonical
source. Do not restore root `CLAUDE.md` or manifest inventory arrays without
a superseding ADR and corresponding regression changes.
