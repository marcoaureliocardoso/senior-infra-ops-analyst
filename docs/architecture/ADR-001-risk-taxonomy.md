# ADR-001 — Canonical operational risk taxonomy

- **Status:** Accepted
- **Date:** 2026-07-23
- **Decision owners:** Project maintainers

## Context

Operational instructions used overlapping labels, mixed action impact with contextual hazards, and could assign a low label to an approval that authorized a higher-impact action. An LLM receiving those contradictions could apply different gates to the same operation depending on which skill, reference, template, or subagent entered context.

## Decision

Every operational action receives exactly one base level based on its highest plausible impact: `SAFE_READ_ONLY`, `LOW_RISK_CHANGE`, `DISRUPTIVE_CHANGE`, or `DESTRUCTIVE`. Orthogonal conditions are represented only by the modifiers `SENSITIVE_OUTPUT`, `RESOURCE_INTENSIVE`, `ACTIVE_PROBE`, `PRIVILEGED`, `REMOTE_SESSION_RISK`, and `EXTERNAL_SIDE_EFFECT`.

Approval, validation, rollback, recovery evidence, and compensating-action requirements follow the canonical control matrix in `references/risk-levels.md`. An approval or external workflow action inherits the impact of what it authorizes and adds `EXTERNAL_SIDE_EFFECT`.

## Implemented architecture

- `AGENTS.md` states the global classification and approval contract.
- `references/risk-levels.md` is the normative vocabulary, algorithm, modifier model, and control matrix.
- `references/command-execution-protocol.md` applies that taxonomy at command boundaries.
- Skills, templates, examples, slash commands, and subagents reference the shared vocabulary instead of defining local risk levels.
- `tests/validate-content.py` performs context-aware extraction of explicit classifications across Markdown and script content.
- `tests/test-risk-taxonomy.py` supplies mutation fixtures for invalid and valid expressions.

## Enforcement points

- Core policy files must contain the complete canonical vocabulary.
- Deprecated `STATE_CHANGING` and abbreviated `DISRUPTIVE` tokens fail validation.
- Explicit classifications must contain exactly one base level plus zero or more known modifiers.
- Unknown, modifier-only, and mixed-base classifications fail package validation.
- Approval-gated changes require explicit operator approval and appropriate recovery controls.

## Alternatives rejected

- Local taxonomies per skill were rejected because they create contradictory behavior.
- Composite base labels were rejected because impact and context cannot be validated independently.
- A global uppercase-token regex was rejected because examples, prose, and scripts require context-aware parsing to avoid false positives.
- Prose-only review was rejected because drift must fail CI deterministically.

## Validation evidence

- Initial unification: commit `41d9e86`, release `0.8.0`.
- Two retroactive independent review cycles found Important gaps but no Critical finding.
- Hardening after review: PR `#23`, squash merge `0e72213`, release `0.9.1`.
- The final review reported no Critical or Important finding pending.
- Package validation includes 12 risk-taxonomy mutation tests plus content, schema, workflow, and PowerShell checks.

## Consequences and limitations

The LLM receives one stable decision model across all entry points, and invalid classifications fail before packaging. Static parsing is intentionally limited to explicit risk expressions; it does not prove that an arbitrary shell command was classified correctly at runtime. Command-semantic enforcement belongs to P0-04.

## Forward compatibility

The decision does not depend on a Claude Code, Nori, or model version. New risk concepts must be introduced as modifiers unless they represent a genuinely distinct base impact; vocabulary changes require validator and mutation-test updates.
