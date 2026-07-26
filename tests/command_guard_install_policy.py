#!/usr/bin/env python3
"""Canonical source and installed policy for the native command guard hook."""
from __future__ import annotations

import re
from pathlib import Path


EXECUTOR_AGENTS = (
    "audit-evidence-collector",
    "cloud-platform-operator",
    "database-operator",
    "diagnostic-operator",
    "kubernetes-operator",
    "network-edge-operator",
    "observability-sre",
    "release-cicd-operator",
)
ANALYTICAL_AGENTS = (
    "change-manager",
    "incident-commander",
    "rca-facilitator",
    "security-operations-reviewer",
)
VALIDATOR_RELATIVE_PATH = Path(
    "command-driven-operations/scripts/validate-ops-command.mjs"
)
CANONICAL_HOOK_BLOCK = """hooks:
  PreToolUse:
    - matcher: Bash
      hooks:
        - type: command
          command: node
          args:
            - "{{skills_dir}}/command-driven-operations/scripts/validate-ops-command.mjs"
          timeout: 5
"""


def _frontmatter_bounds(text: str) -> tuple[int, int] | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    return (4, end) if end >= 0 else None


def insert_command_guard_hook(text: str) -> str:
    """Insert the canonical hook before the closing frontmatter delimiter."""
    bounds = _frontmatter_bounds(text)
    if bounds is None:
        return text
    _, end = bounds
    prefix = text[: end + 1]
    if not prefix.endswith("\n"):
        prefix += "\n"
    return prefix + CANONICAL_HOOK_BLOCK + text[end + 1 :]


def remove_command_guard_hook(text: str) -> str:
    """Remove one canonical hook block from a fixture."""
    return text.replace(CANONICAL_HOOK_BLOCK, "", 1)


def source_command_guard_hook(text: str) -> dict[str, object] | None:
    """Return canonical source hook semantics when the exact block is present."""
    if text.count(CANONICAL_HOOK_BLOCK) != 1:
        return None
    return {
        "matcher": "Bash",
        "type": "command",
        "command": "node",
        "args": (
            "{{skills_dir}}/command-driven-operations/scripts/validate-ops-command.mjs",
        ),
        "timeout": 5,
    }


def source_hook_errors(agent_id: str, text: str) -> list[str]:
    """Return native command-guard hook policy violations for one source agent."""
    errors: list[str] = []
    frontmatter_bounds = _frontmatter_bounds(text)
    frontmatter = (
        text[frontmatter_bounds[0] : frontmatter_bounds[1]]
        if frontmatter_bounds
        else ""
    )
    pretool_count = len(
        re.findall(r"^\s*PreToolUse:\s*$", frontmatter, re.MULTILINE)
    )
    exact_count = text.count(CANONICAL_HOOK_BLOCK)

    if agent_id in ANALYTICAL_AGENTS:
        if pretool_count or re.search(
            r"^\s*-\s*matcher:\s*Bash\s*$", frontmatter, re.MULTILINE
        ):
            errors.append(f"analytical agent declares Bash hook: {agent_id}")
        return errors

    if agent_id not in EXECUTOR_AGENTS:
        return [f"unknown subagent command guard policy: {agent_id}"]

    if pretool_count == 0:
        errors.append(f"missing command guard hook: {agent_id}")
    if pretool_count != 1 or exact_count != 1:
        errors.append(f"executor must have exactly one command guard hook: {agent_id}")
    matcher = re.findall(
        r"^\s*-\s*matcher:\s*(.*?)\s*$", frontmatter, re.MULTILINE
    )
    if matcher and matcher != ["Bash"]:
        errors.append(f"command guard matcher must be exactly Bash: {agent_id}")
    timeout = re.findall(r"^\s*timeout:\s*(.*?)\s*$", frontmatter, re.MULTILINE)
    if timeout and timeout != ["5"]:
        errors.append(f"command guard timeout must be 5 seconds: {agent_id}")
    if pretool_count and exact_count != 1:
        errors.append(f"command guard hook must use canonical exec form: {agent_id}")
    return errors


def installed_command_guard_hook(text: str) -> dict[str, object] | None:
    """Parse one installed canonical-shape command guard hook."""
    bounds = _frontmatter_bounds(text)
    if bounds is None:
        return None
    frontmatter = text[bounds[0] : bounds[1]]
    pattern = re.compile(
        r"^hooks:\s*\n"
        r"  PreToolUse:\s*\n"
        r"    - matcher:\s*(.*?)\s*\n"
        r"      hooks:\s*\n"
        r"        - type:\s*(.*?)\s*\n"
        r"          command:\s*(.*?)\s*\n"
        r"          args:\s*\n"
        r"            - [\"']?(.*?)[\"']?\s*\n"
        r"          timeout:\s*(.*?)\s*$",
        re.MULTILINE,
    )
    matches = list(pattern.finditer(frontmatter))
    if len(matches) != 1:
        return None
    match = matches[0]
    return {
        "matcher": match.group(1),
        "type": match.group(2),
        "command": match.group(3),
        "args": (match.group(4),),
        "timeout": match.group(5),
    }


def installed_hook_errors(
    agent_id: str,
    source: str,
    installed: str,
    installed_skills_dir: Path,
) -> list[str]:
    """Return installed hook differences and unresolved validator paths."""
    errors: list[str] = []
    installed_hook = installed_command_guard_hook(installed)
    if agent_id in ANALYTICAL_AGENTS:
        if installed_hook is not None or re.search(
            r"^\s*PreToolUse:\s*$", installed, re.MULTILINE
        ):
            errors.append(f"analytical agent declares Bash hook: {agent_id}")
        return errors
    if agent_id not in EXECUTOR_AGENTS:
        return [f"unknown installed command guard policy: {agent_id}"]
    if source_command_guard_hook(source) is None:
        errors.append(f"source command guard hook invalid: {agent_id}")
    if installed_hook is None:
        errors.append(f"installed hook differs: {agent_id}")
        return errors
    for field, expected in {
        "matcher": "Bash",
        "type": "command",
        "command": "node",
        "timeout": "5",
    }.items():
        if installed_hook[field] != expected:
            errors.append(f"installed hook differs: {field} — {agent_id}")
    expected_path = (installed_skills_dir / VALIDATOR_RELATIVE_PATH).resolve()
    installed_arg = str(installed_hook["args"][0])
    if "{{skills_dir}}" in installed_arg:
        errors.append(f"installed validator path differs: {agent_id}")
    else:
        candidate = Path(installed_arg).resolve()
        if candidate != expected_path:
            errors.append(f"installed validator path differs: {agent_id}")
    if not expected_path.is_file():
        errors.append(f"installed validator missing: {expected_path}")
    return errors
