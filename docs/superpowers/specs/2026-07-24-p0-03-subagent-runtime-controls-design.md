# P0-03 Subagent Runtime Controls Design

**Status:** Approved
**Date:** 2026-07-24
**Scope:** P0-03 — limit duration and tools by subagent role

## Context

The project is an AI-first operational skillset consumed by an LLM through
Claude Code and distributed by Nori. Runtime controls must therefore use
native Claude Code subagent fields that survive Nori installation rather than
depend only on prose. Runtime and model versions are observed during testing,
not fixed as project requirements. Subagents continue to use `model: inherit`.

P0-03 must reduce excessive loops, prevent silent capability expansion, and
preserve a useful handoff when work cannot be completed within the role's
budget. It also establishes versioned architectural decision records for
P0-01, P0-02, and P0-03.

## Goals

- Give all 12 subagents an enforced `maxTurns` value appropriate to the role.
- Make `tools` an explicit least-privilege allowlist for every role.
- Deny direct file mutation through `Write` and `Edit`.
- Remove and explicitly deny `Bash` for analytical and coordination roles.
- Preserve evidence collection only where it is part of the role.
- Require each subagent to explain why every allowed tool is necessary.
- Stop voluntarily before the hard limit and return a structured handoff.
- Reject missing, malformed, unknown, or role-incompatible runtime controls.
- Inspect the Nori-installed artifact and run an opt-in live smoke test through
  Claude Code with the operator-configured model.
- Document the decisions and implemented architecture of P0-01, P0-02, and
  P0-03 in indexed, versioned ADRs.

## Non-goals

- Do not pin Claude Code, Nori, or a DeepSeek model/version.
- Do not implement a parallel runtime or model API integration.
- Do not claim that `maxTurns` is a wall-clock timeout.
- Do not guarantee a handoff after an abrupt runtime cutoff; handoff is a
  cooperative early-stop contract with a hard `maxTurns` backstop.
- Do not implement command-level Bash enforcement. That belongs to P0-04 and
  its native `PreToolUse` hook.
- Do not grant `Write`, `Edit`, MCP tools, or future tools by inheritance.

## Decision

Use an allowlist-first design. Each subagent declares `tools`, `maxTurns`,
`disallowedTools`, `model: inherit`, and its preloaded `skills` in native
Claude Code frontmatter. The explicit allowlist denies unlisted built-in, MCP,
and future tools by default. `disallowedTools` records critical denials as
defense in depth.

Each subagent body contains a concise `## Runtime controls` section. It states
the operational budget, reserves the final two turns for handoff, justifies
every allowed tool, restricts web queries from containing internal data, and
defines the incomplete-work handoff.

## Role policy

| Subagent | `maxTurns` | Allowed tools | Explicitly denied |
|---|---:|---|---|
| `incident-commander` | 20 | Read, Grep, Glob, TodoWrite, Skill | Write, Edit, Bash |
| `diagnostic-operator` | 16 | Read, Grep, Glob, Bash, WebFetch, WebSearch, Skill | Write, Edit |
| `change-manager` | 10 | Read, Grep, Glob, WebFetch, WebSearch, Skill | Write, Edit, Bash |
| `rca-facilitator` | 12 | Read, Grep, Glob, WebFetch, WebSearch, Skill | Write, Edit, Bash |
| `observability-sre` | 14 | Read, Grep, Glob, Bash, WebFetch, WebSearch, Skill | Write, Edit |
| `security-operations-reviewer` | 10 | Read, Grep, Glob, WebFetch, WebSearch, Skill | Write, Edit, Bash |
| `cloud-platform-operator` | 16 | Read, Grep, Glob, Bash, WebFetch, WebSearch, Skill | Write, Edit |
| `kubernetes-operator` | 16 | Read, Grep, Glob, Bash, WebFetch, WebSearch, Skill | Write, Edit |
| `database-operator` | 16 | Read, Grep, Glob, Bash, WebFetch, WebSearch, Skill | Write, Edit |
| `network-edge-operator` | 16 | Read, Grep, Glob, Bash, WebFetch, WebSearch, Skill | Write, Edit |
| `release-cicd-operator` | 14 | Read, Grep, Glob, Bash, WebFetch, WebSearch, Skill | Write, Edit |
| `audit-evidence-collector` | 12 | Read, Grep, Glob, Bash, WebFetch, WebSearch, Skill | Write, Edit |

### Tool rationale

- `Read`, `Grep`, and `Glob` inspect local instructions, evidence, and
  artifacts without granting mutation.
- `Skill` preserves on-demand access to project knowledge outside the
  role-specific startup preload.
- `TodoWrite` is limited to the incident commander for multi-track incident
  coordination.
- `Bash` is limited to roles whose responsibility includes evidence
  collection from command-line or provider tools. Direct mutation remains
  prohibited by policy and is not deterministically command-filtered until
  P0-04.
- `WebSearch` and `WebFetch` are available where current official third-party
  documentation may be required. Prompts, URLs, and query strings must not
  contain secrets, internal topology, private identifiers, or sensitive
  operational evidence.

The change manager becomes a separation-of-duties role: it plans, reviews,
coordinates approval, and validates evidence, but delegates execution to an
appropriate operator. The RCA facilitator and security reviewer analyze
provided evidence and delegate additional command collection. The incident
commander coordinates diagnostic and mitigation tracks without shell access.

## Turn and handoff contract

The frontmatter value is the hard runtime backstop. Each subagent receives an
operational budget of `maxTurns - 2` and reserves the final two turns for
closing or handoff. A subagent that cannot complete within that budget must
stop voluntarily instead of starting another diagnostic branch.

An incomplete-work handoff contains:

- objective and current status;
- completed actions;
- observed evidence and source;
- leading hypotheses and uncertainty;
- pending work and why it remains;
- required tools, access, approvals, or owner;
- next safest action;
- risk classification and applicable modifiers.

The live test evaluates this contract by invariants rather than exact wording.
A hard `maxTurns` cutoff proves termination but does not by itself prove that
the model had time to format a handoff.

## Enforcement and validation

### Static contract tests

Extend content validation and mutation tests to assert:

- all 12 agents declare one positive integer `maxTurns`;
- the value is within the approved role band;
- `tools` exactly matches the role policy;
- every tool is known and justified in `## Runtime controls`;
- `disallowedTools` contains the role's critical denials;
- analytical roles cannot declare `Bash`;
- `model` remains `inherit`;
- the handoff contract is present;
- missing, zero, non-numeric, out-of-range, unknown, duplicated, or
  role-incompatible values fail closed.

### Installed artifact inspection

Use the currently available Nori CLI in an isolated temporary installation.
Do not encode its observed version into project constraints. Compare all 12
installed agent definitions with the source and confirm preservation of:

- `maxTurns`;
- `tools`;
- `disallowedTools`;
- `model: inherit`;
- `skills`;
- runtime-control instructions.

The inspection must fail if any agent or field is missing, transformed into a
broader permission set, or differs from source semantics.

### Live Claude Code smoke test

Provide an opt-in test script that:

- discovers the available Claude Code and Nori commands instead of requiring
  fixed versions;
- records observed runtime, installer, and configured model identifiers with
  credentials redacted;
- installs into a temporary location;
- runs only synthetic prompts in a temporary directory;
- verifies an analytical role does not receive Bash;
- verifies an executor uses only a benign, read-only shell command;
- verifies cooperative early stop produces the handoff invariants;
- uses a temporary low-turn fixture to verify the hard cutoff;
- never targets real infrastructure or includes sensitive data;
- is excluded from normal CI because it consumes API capacity.

If the runtime or credentials are unavailable, the script reports a blocked
precondition rather than reporting a pass.

## Documentation architecture

Create an index and three versioned decision records:

- `docs/architecture/README.md`;
- `docs/architecture/ADR-001-risk-taxonomy.md`;
- `docs/architecture/ADR-002-subagent-skill-preload.md`;
- `docs/architecture/ADR-003-subagent-runtime-controls.md`.

Each ADR records context, decision, rejected alternatives, architecture,
enforcement points, validation evidence, consequences, limitations, and
forward-compatibility constraints. README and `docs.md` link to the index.
The external TODO requires an indexed, versioned ADR for every implemented
solution and is updated with final evidence after integration.

## Release impact

P0-03 changes enforced agent behavior and adds a documented runtime-control
contract. Release metadata advances from `0.9.1` to `0.10.0`. README,
`docs.md`, `CHANGELOG.md`, `nori.json`, `.nori-version`, and applicable
per-skill metadata remain internally consistent. No runtime or model version
is made a package requirement.

## Residual risks

- `Bash` is an inherently broad capability and can mutate state. P0-03 limits
  which roles receive it; P0-04 must enforce command semantics with native
  `PreToolUse`.
- Web tools can disclose query content to external services. Prompt-level
  minimization is required, but a deterministic external-data guard is outside
  this item.
- A model can miscount its cooperative budget. The hard limit still prevents
  an unbounded loop, but useful handoff quality is behavioral and must be
  measured.
- Nori may evolve its translation format. Installed-artifact inspection checks
  semantics rather than requiring a fixed installer version or byte-identical
  files.
