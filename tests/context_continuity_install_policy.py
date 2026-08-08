#!/usr/bin/env python3
"""Canonical source and installed policy for compact lifecycle hooks."""
from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AGENTS = (
    "audit-evidence-collector",
    "change-manager",
    "cloud-platform-operator",
    "database-operator",
    "diagnostic-operator",
    "incident-commander",
    "kubernetes-operator",
    "network-edge-operator",
    "observability-sre",
    "rca-facilitator",
    "release-cicd-operator",
    "security-operations-reviewer",
)
LAUNCHER_RELATIVE_PATH = Path(
    "context-continuity/scripts/compact-hook-launcher.sh"
)
CONTINUITY_ARTIFACTS = (
    LAUNCHER_RELATIVE_PATH,
    Path("context-continuity/scripts/compact-hook.mjs"),
    Path("context-continuity/scripts/context-statusline.mjs"),
    Path("context-continuity/scripts/settings.mjs"),
    Path("context-continuity/scripts/configure-context-continuity.mjs"),
)
CANONICAL_CONTINUITY_HOOKS = '''  PreCompact:
    - hooks:
        - type: command
          command: "{{skills_dir}}/context-continuity/scripts/compact-hook-launcher.sh"
          args:
            - pre
          timeout: 5
  PostCompact:
    - hooks:
        - type: command
          command: "{{skills_dir}}/context-continuity/scripts/compact-hook-launcher.sh"
          args:
            - post
          timeout: 5
'''


def _frontmatter(text: str) -> str:
    if not text.startswith("---\n"):
        return ""
    end = text.find("\n---\n", 4)
    return text[4:end] if end >= 0 else ""


def source_continuity_hook_errors(agent_id: str, text: str) -> list[str]:
    """Require the exact non-blocking compact hook pair in every source role."""
    if agent_id not in AGENTS:
        return [f"unknown subagent continuity policy: {agent_id}"]
    frontmatter = _frontmatter(text)
    errors: list[str] = []
    pre_count = len(re.findall(r"^\s*PreCompact:\s*$", frontmatter, re.MULTILINE))
    post_count = len(re.findall(r"^\s*PostCompact:\s*$", frontmatter, re.MULTILINE))
    if pre_count != 1 or post_count != 1:
        errors.append(f"continuity hook phase count must be one each: {agent_id}")
    if text.count(CANONICAL_CONTINUITY_HOOKS) != 1:
        errors.append(f"subagent must use canonical continuity hooks: {agent_id}")
    return errors


def installed_continuity_hook_errors(
    agent_id: str,
    source: str,
    installed: str,
    installed_skills_dir: Path,
) -> list[str]:
    """Require Nori's resolved path and exact installed compact hook semantics."""
    if agent_id not in AGENTS:
        return [f"unknown installed continuity policy: {agent_id}"]
    errors = source_continuity_hook_errors(agent_id, source)
    expected = {
        CANONICAL_CONTINUITY_HOOKS.replace(
            "{{skills_dir}}", str(installed_skills_dir)
        ),
        CANONICAL_CONTINUITY_HOOKS.replace(
            "{{skills_dir}}", installed_skills_dir.as_posix()
        ),
    }
    if not any(installed.count(block) == 1 for block in expected):
        errors.append(f"installed continuity hook differs: {agent_id}")
    launcher = (installed_skills_dir / LAUNCHER_RELATIVE_PATH).resolve()
    if not launcher.is_file():
        errors.append(f"installed continuity launcher missing: {launcher}")
    return errors


def installed_continuity_artifact_errors(installed_skills_dir: Path) -> list[str]:
    """Require installed continuity scripts to be byte-equal to package source."""
    errors: list[str] = []
    for relative in CONTINUITY_ARTIFACTS:
        source = ROOT / "skills" / relative
        installed = installed_skills_dir / relative
        if not installed.is_file():
            errors.append(f"installed continuity artifact missing: {relative}")
        elif installed.read_bytes() != source.read_bytes():
            errors.append(f"installed continuity artifact differs: {relative}")
    return errors
