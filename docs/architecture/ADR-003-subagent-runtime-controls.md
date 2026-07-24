# ADR-003 — Bounded, least-privilege subagent runtime

**Status:** Accepted  
**Date:** 2026-07-24  
**Decision owners:** Project maintainers

## Context

Subagents had broad and mostly uniform tool access with no native turn boundary. Prose could request restraint but could not prevent silent capability expansion or unbounded agentic loops. The project runs as an AI-first skillset through Claude Code and Nori, so the control boundary must use native fields that survive installation.

## Decision

Every subagent declares an exclusive `tools` allowlist, defense-in-depth `disallowedTools`, an exact role-specific `maxTurns`, `model: inherit`, and its existing focused `skills` preload. `Write` and `Edit` are denied to all roles. `Bash` is denied to incident coordination, change management, RCA, and security review; execution or additional evidence collection is delegated to an operator.

Roles reserve their final two turns for closure or a structured incomplete-work handoff. `maxTurns` is a hard agentic-turn backstop, not a wall-clock timeout and not a guarantee that an abrupt cutoff can format a handoff.

## Implemented architecture

- `subagents/*.md` enforce the approved role matrix in Claude Code frontmatter.
- Each `## Runtime controls` section justifies every allowed tool, states the cooperative budget, restricts sensitive web queries, and defines eight handoff fields.
- `tests/subagent_runtime_policy.py` centralizes exact role policy, known tools, parsing, and validation.
- `tests/test-subagent-frontmatter.py` provides positive and mutation coverage.
- `tests/validate-installed-subagents.py` compares source and Nori-installed semantics for all 12 agents.
- `tests/live-subagent-runtime-smoke.sh` supplies opt-in analytical, executor, handoff, and cutoff behavioral probes using synthetic inputs.
- `nori.json` declares `type: skillset`, required for local/Git-backed Nori activation.

## Enforcement points

- Missing, zero, non-numeric, duplicated, out-of-band, or noncanonical `maxTurns` fails validation.
- Unknown, duplicated, or role-incompatible tools fail validation.
- Critical denials must exactly match the role policy.
- Every allowed tool needs a rationale and every handoff field must be present.
- Operational budget must equal `maxTurns - 2`.
- Nori-installed `maxTurns`, tools, denials, model, skills, and runtime instructions must match source semantics.

## Alternatives rejected

- Prose-only limits were rejected because they cannot bound the runtime.
- Tool inheritance or denylist-only policy was rejected because current, MCP, or future tools could expand capabilities silently.
- Removing `Bash` from all roles was rejected because evidence collection is a core responsibility of diagnostic operators.
- Command-level Bash parsing was deferred rather than approximated here; deterministic command semantics belong to the native `PreToolUse` architecture in P0-04.
- A parallel model runtime was rejected in favor of Claude Code and Nori.

## Validation evidence

- Static package validation passes 19 frontmatter tests, 5 installed-artifact tests, 3 schema tests, 12 risk tests, content validation, schema validation, CI workflow checks, Bash syntax, and PowerShell syntax.
- A real isolated Nori activation using observed Nori `0.31.0` and Node.js `v26.5.0` registered all 12 subagents and passed semantic installed-artifact comparison.
- The live-smoke parser self-test passes without API consumption.
- The host security policy blocked the LLM behavioral probes because they could send workspace content to an external service. This is recorded as blocked validation, not as a pass.

## Consequences and limitations

Analytical roles have materially smaller capability sets, all agent loops are bounded, and drift fails packaging. `Bash` remains a broad capability for evidence-collecting roles and can express mutations; P0-04 must enforce command semantics with `PreToolUse`.
Web query minimization is an instruction-level control until a deterministic external-data guard exists. Cooperative handoff quality remains model behavior and requires the opt-in live probe.

## Forward compatibility

No Claude Code, Nori, or model name/version is a project requirement. Tests discover commands and record observed identifiers. `model: inherit` preserves operator choice, and installed validation compares semantics so translation-format evolution does not fail on harmless textual changes.
