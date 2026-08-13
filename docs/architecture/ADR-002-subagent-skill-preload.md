# ADR-002 — Focused native skill preload for subagents

- **Status:** Accepted
- **Date:** 2026-07-23
- **Decision owners:** Project maintainers

## Context

The 12 subagents originally documented primary skills only in their bodies. Loading that knowledge depended on probabilistic discovery, while loading all 24 skills into every role would increase startup context and reduce role discrimination.

## Decision

Each subagent declares its documented primary skills through native Claude Code `skills` frontmatter. The ordered preload must match the `## Primary skills` section exactly. The `Skill` tool remains allowed so non-primary project procedures can be discovered on demand. Every subagent keeps `model: inherit`.

## Implemented architecture

- `subagents/*/SUBAGENT.md` contain 37 role-to-skill preload links, with two to four primary skills per role; ADR-007 defines their first-class package boundary.
- `nori.json` remains the canonical catalog of available package skills.
- `tests/validate-content.py` extracts the complete frontmatter list, validates syntax and registration, rejects duplicates, and compares it with documented primary skills.
- `tests/test-subagent-frontmatter.py` mutates installed-format source definitions to prove malformed input fails closed.
- `tests/validate-package.sh` executes the regression suite in normal package validation.

## Enforcement points

- Missing or unterminated frontmatter fails validation.
- Missing, empty, malformed, duplicated, or unregistered skill entries fail validation.
- Preload order and contents must equal the documented primary-skill list.
- `Skill` must remain in the role tool allowlist for on-demand access.
- `model` must remain `inherit`.

## Alternatives rejected

- Full-catalog preload was rejected because it expands context for every role and weakens specialization.
- Documentation-only primary skills were rejected because discovery is not deterministic.
- Dynamic `Skill` discovery alone was rejected because essential role knowledge might not be loaded before the first decision.
- A custom runtime loader was rejected in favor of native Claude Code and Nori mechanisms.

## Validation evidence

- Implementation: PR `#22`, squash merge `7dca0e0`, release `0.9.0`.
- Independent review exposed fail-open parsing cases; the final architecture validates closing delimiters and the entire ordered list.
- CI and Security checks passed for the integrated change.
- The original regression suite covered valid, malformed, unknown, duplicate, empty, and unterminated definitions; P0-03 later extended the same suite.

## Consequences and limitations

Primary knowledge is present at startup without loading the full catalog. A missing third-party dependency can still affect a skill outside this package; installed-artifact validation and Nori dependency resolution remain necessary. Preload controls knowledge availability, not tool authorization.

## Forward compatibility

The architecture uses native fields and semantic validation rather than a fixed Claude Code, Nori, or model version. If Nori changes translation format, installed artifacts are compared by meaning instead of byte identity.
