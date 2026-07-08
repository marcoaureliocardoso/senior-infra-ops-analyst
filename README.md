# Senior Infrastructure Operations Analyst Skillset

This skillset personifies a Senior Infrastructure Operations Analyst with command-driven, safety-gated infrastructure operations.

## What changed in v0.2.1

The skillset is no longer only advisory. It now instructs the agent to actively execute safe read-only diagnostics when tool access exists, while stopping at explicit approval gates before any state-changing or disruptive operation.

Core additions and audit fixes:

- `command-driven-operations` skill
- command execution protocol
- risk classification model
- technology command references
- interpretation guides
- operational runbook template
- sensitivity/resource-impact modifiers for read-only commands
- corrected package root naming consistency
- safer TLS, log, packet-capture, AD, Kubernetes, and storage guidance

## Intended behavior

When the agent has terminal, SSH, PowerShell, API, or MCP/tool access:

1. Identify context and target.
2. Classify commands by risk.
3. Execute safe read-only commands directly.
4. Summarize observed output.
5. Interpret evidence.
6. Continue narrowing the diagnosis.
7. Stop before state-changing actions and request explicit approval.

When the agent does not have execution access:

1. Provide exact command sequence.
2. Explain risk.
3. Explain expected normal and abnormal signals.
4. Explain how to interpret outputs.
5. Mark approval-required steps clearly.

## Structure

```text
senior-infra-ops-analyst/
├── AGENTS.md
├── nori.json
├── skills/
├── references/
├── templates/
└── slashcommands/
```

## Important limitation

A skillset cannot magically grant shell or infrastructure access. It controls behavior when the host agent already has compatible tools. If the agent has no terminal/SSH/API/MCP access, it must not pretend to have run commands.
