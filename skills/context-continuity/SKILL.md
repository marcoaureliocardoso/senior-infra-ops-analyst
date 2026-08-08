---
name: Context Continuity
description: Use for long Claude Code work, context pressure, compaction recovery, native task continuity, local preventive-compaction configuration, or context-cost measurement.
version: 1.0.0
last_updated: 2026-08-08
maintainer: Marco Aurelio Cardoso
triggers:
  - long task
  - context pressure
  - context compaction
  - task continuity
  - context measurement
---

# Context Continuity

Preserve the smallest operational ledger that can safely resume long work while Claude Code retains control of native compaction, task state, and context inspection.

<required>
1. Keep auto-compaction enabled and prefer a percentage threshold from 70 through 75; the package default is 72.
2. Use the native task list for long work and read it immediately after compaction.
3. Treat lost authorization proof and credential reuse as invalid after compaction.
4. Never retain transcript, prompt, compact summary, model output, tool payload, or secret as continuity evidence.
5. Use only numeric, boolean, bounded identifier, and reason-code evidence for context-cost measurement.
6. Apply `references/risk-levels.md` and the existing command authorization rules to every operational action after resumption.
</required>

## When to use

Use this skill for multi-step work, repeated skill or subagent loading, visible context pressure, compaction recovery, local preventive-compaction setup, or measurement of instructions, skills, subagents, MCPs, and tool search.

## Capability check

Resolve `SKILL_ROOT` to the installed `context-continuity` directory. Run check mode before applying settings:

```bash
node "${SKILL_ROOT}/scripts/configure-context-continuity.mjs" --check --scope project
```

Treat unavailable task tools, MCP tool search, context percentages, or provider window metadata as explicit capability results rather than successes.

## Configure

Apply project-local owned settings only after check mode reports no blocker:

```bash
node "${SKILL_ROOT}/scripts/configure-context-continuity.mjs" --apply --scope project
node "${SKILL_ROOT}/scripts/configure-context-continuity.mjs" --apply --scope project --status-line
```

The status line is opt-in. Remove only still-owned values with:

```bash
node "${SKILL_ROOT}/scripts/configure-context-continuity.mjs" --remove-owned --scope project
```

## During long work

- Maintain bounded native tasks with one active task when supported.
- Record objective, completion criteria, decisions, evidence locations, branch, commits, files, tests, blockers, risks, rollback, and next action.
- Inspect `/context` before broad skill, subagent, or MCP loading.
- Read large artifacts in bounded chunks and retain references instead of content copies.

## After compaction

Read the native task list, re-establish the current objective and next action, verify branch and operational state, and request fresh approval whenever current native state cannot prove authorization or credential reuse.

## Recovery

Use focused `/compact` instructions when one invariant needs emphasis. Use `/rewind`, `/clear`, or `/resume` only after identifying which task, context, authorization, and credential-reuse state the action invalidates.

## Context inventory

Measure content-free package and runtime metadata with:

```bash
node "${SKILL_ROOT}/scripts/context-inventory.mjs" --root PROJECT_ROOT
```

Never infer a token count or absolute context window from file bytes.

## Privacy

Hooks and retained evidence must exclude transcript paths, prompts, compact summaries, raw events, model content, tool arguments, tool results, raw commands, headers, credentials, secrets, and secret-derived identifiers.

## Limitations

Claude Code may compact earlier than the configured percentage. MCP tool search and task-tool names are runtime capabilities. `CLAUDE_CODE_AUTO_COMPACT_WINDOW` is not normal configuration and requires separate evidence of incorrect provider or gateway window reporting plus operator approval.

## Required references

- `references/risk-levels.md`
- `references/command-execution-protocol.md`
- `references/external-sources.md`
