#!/usr/bin/env python3
"""Canonical runtime policy for Claude Code subagents."""
from __future__ import annotations

import re

COMMON = ("Read", "Grep", "Glob")
WEB = ("WebFetch", "WebSearch")
EXECUTOR = (*COMMON, "Bash", *WEB, "Skill")
ANALYST = (*COMMON, *WEB, "Skill")

ROLE_POLICY = {
    "incident-commander": {
        "max_turns": 20,
        "turn_range": (12, 20),
        "tools": (*COMMON, "TodoWrite", "Skill"),
        "denied": ("Write", "Edit", "Bash"),
    },
    "diagnostic-operator": {
        "max_turns": 16,
        "turn_range": (12, 16),
        "tools": EXECUTOR,
        "denied": ("Write", "Edit"),
    },
    "change-manager": {
        "max_turns": 10,
        "turn_range": (8, 12),
        "tools": ANALYST,
        "denied": ("Write", "Edit", "Bash"),
    },
    "rca-facilitator": {
        "max_turns": 12,
        "turn_range": (8, 12),
        "tools": ANALYST,
        "denied": ("Write", "Edit", "Bash"),
    },
    "observability-sre": {
        "max_turns": 14,
        "turn_range": (12, 16),
        "tools": EXECUTOR,
        "denied": ("Write", "Edit"),
    },
    "security-operations-reviewer": {
        "max_turns": 10,
        "turn_range": (8, 12),
        "tools": ANALYST,
        "denied": ("Write", "Edit", "Bash"),
    },
    "cloud-platform-operator": {
        "max_turns": 16,
        "turn_range": (12, 16),
        "tools": EXECUTOR,
        "denied": ("Write", "Edit"),
    },
    "kubernetes-operator": {
        "max_turns": 16,
        "turn_range": (12, 16),
        "tools": EXECUTOR,
        "denied": ("Write", "Edit"),
    },
    "database-operator": {
        "max_turns": 16,
        "turn_range": (12, 16),
        "tools": EXECUTOR,
        "denied": ("Write", "Edit"),
    },
    "network-edge-operator": {
        "max_turns": 16,
        "turn_range": (12, 16),
        "tools": EXECUTOR,
        "denied": ("Write", "Edit"),
    },
    "release-cicd-operator": {
        "max_turns": 14,
        "turn_range": (12, 16),
        "tools": EXECUTOR,
        "denied": ("Write", "Edit"),
    },
    "audit-evidence-collector": {
        "max_turns": 12,
        "turn_range": (8, 12),
        "tools": EXECUTOR,
        "denied": ("Write", "Edit"),
    },
}

KNOWN_TOOLS = {
    "Read",
    "Grep",
    "Glob",
    "Bash",
    "TodoWrite",
    "WebFetch",
    "WebSearch",
    "Skill",
}

HANDOFF_FIELDS = (
    "Objective and current status",
    "Completed actions",
    "Observed evidence and source",
    "Leading hypotheses and uncertainty",
    "Pending work and why it remains",
    "Required tools, access, approvals, or owner",
    "Next safest action",
    "Risk classification and applicable modifiers",
)


def _frontmatter(text: str) -> str:
    if not text.startswith("---\n"):
        return ""
    parts = text.split("---", 2)
    return parts[1] if len(parts) == 3 else ""


def _csv_matches(frontmatter: str, field: str) -> list[tuple[str, ...]]:
    values = re.findall(
        rf"^{re.escape(field)}:\s*(.*?)\s*$", frontmatter, re.MULTILINE
    )
    return [
        tuple(part.strip() for part in value.split(",") if part.strip())
        for value in values
    ]


def runtime_section(text: str) -> str:
    """Return the body of the Runtime controls section."""
    match = re.search(
        r"^## Runtime controls\s*\n(.*?)(?=^## |\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    return match.group(1) if match else ""


def frontmatter_fields(text: str) -> dict[str, object]:
    """Parse fields whose installed semantics must remain stable."""
    frontmatter = _frontmatter(text)
    max_matches = re.findall(
        r"^maxTurns:\s*(.*?)\s*$", frontmatter, re.MULTILINE
    )
    tool_matches = _csv_matches(frontmatter, "tools")
    denied_matches = _csv_matches(frontmatter, "disallowedTools")
    model_matches = re.findall(
        r"^model:\s*(.*?)\s*$", frontmatter, re.MULTILINE
    )
    return {
        "maxTurns": max_matches[0] if len(max_matches) == 1 else None,
        "maxTurnsCount": len(max_matches),
        "tools": tool_matches[0] if len(tool_matches) == 1 else None,
        "toolsCount": len(tool_matches),
        "disallowedTools": (
            denied_matches[0] if len(denied_matches) == 1 else None
        ),
        "disallowedToolsCount": len(denied_matches),
        "model": model_matches[0] if len(model_matches) == 1 else None,
        "modelCount": len(model_matches),
    }


def frontmatter_skills(text: str) -> tuple[str, ...]:
    """Return the ordered native Claude Code skills preload."""
    frontmatter = _frontmatter(text)
    match = re.search(
        r"^skills:\s*\n((?:[ \t]+-[^\n]*\n?)+)",
        frontmatter,
        re.MULTILINE,
    )
    if not match:
        return ()
    return tuple(
        item.strip()
        for item in re.findall(r"^[ \t]+-\s*([a-z0-9-]+)\s*$", match.group(1), re.MULTILINE)
    )


def runtime_control_errors(agent_id: str, text: str) -> list[str]:
    """Return all runtime-policy violations for one registered subagent."""
    policy = ROLE_POLICY[agent_id]
    fields = frontmatter_fields(text)
    errors: list[str] = []

    raw_turns = fields["maxTurns"]
    if fields["maxTurnsCount"] > 1:
        errors.append(f"subagent has duplicate maxTurns: {agent_id}")
        turns = None
    elif raw_turns is None:
        errors.append(f"subagent missing maxTurns: {agent_id}")
        turns = None
    elif not re.fullmatch(r"[1-9]\d*", str(raw_turns)):
        errors.append(f"subagent has invalid maxTurns: {agent_id}")
        turns = None
    else:
        turns = int(str(raw_turns))
        minimum, maximum = policy["turn_range"]
        if not minimum <= turns <= maximum:
            errors.append(f"subagent maxTurns outside role range: {agent_id}")
        elif turns != policy["max_turns"]:
            errors.append(f"subagent maxTurns differs from role policy: {agent_id}")

    tools = fields["tools"]
    if fields["toolsCount"] > 1:
        errors.append(f"subagent has duplicate tools field: {agent_id}")
    if tools is not None:
        duplicates = sorted({tool for tool in tools if tools.count(tool) > 1})
        if duplicates:
            errors.append(f"subagent has duplicate tools: {duplicates} — {agent_id}")
        unknown = sorted(set(tools) - KNOWN_TOOLS)
        if unknown:
            errors.append(f"subagent declares unknown tools: {unknown} — {agent_id}")
        if tools != policy["tools"]:
            errors.append(f"subagent tools differ from role policy: {agent_id}")

    denied = fields["disallowedTools"]
    if fields["disallowedToolsCount"] > 1:
        errors.append(f"subagent has duplicate disallowedTools field: {agent_id}")
    if denied is not None:
        duplicates = sorted({tool for tool in denied if denied.count(tool) > 1})
        if duplicates:
            errors.append(
                f"subagent has duplicate disallowedTools: {duplicates} — {agent_id}"
            )
    if denied != policy["denied"]:
        errors.append(
            f"subagent disallowedTools differ from role policy: {agent_id}"
        )

    if fields["modelCount"] != 1 or fields["model"] != "inherit":
        errors.append(f"subagent model must be exactly inherit: {agent_id}")

    section = runtime_section(text)
    if not section:
        errors.append(f"subagent lacks Runtime controls section: {agent_id}")
        return errors
    for tool in policy["tools"]:
        if f"`{tool}`" not in section:
            errors.append(f"subagent missing tool rationale for {tool}: {agent_id}")
    for field in HANDOFF_FIELDS:
        if field not in section:
            errors.append(f"subagent missing handoff field: {field} — {agent_id}")
    if turns is not None and f"Operational budget: {turns - 2} turns" not in section:
        errors.append(f"subagent runtime budget does not match maxTurns: {agent_id}")
    return errors
