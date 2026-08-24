#!/usr/bin/env python3
"""Canonical source and installed policy for the native command guard hook."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

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
LAUNCHER_RELATIVE_PATH = Path(
    "command-driven-operations/scripts/command-guard-launcher.sh"
)
SECURITY_CRITICAL_ARTIFACTS = (
    Path("command-driven-operations/scripts/command-guard-launcher.sh"),
    Path("command-driven-operations/scripts/configure-native-execution-boundary.mjs"),
    Path("command-driven-operations/scripts/main-session-settings.mjs"),
    Path("command-driven-operations/scripts/validate-ops-command.mjs"),
    Path("command-driven-operations/scripts/record-command-approval.mjs"),
    *tuple(
        Path("command-driven-operations/scripts/command-guard") / name
        for name in (
            "audit.mjs", "bash-lexer.mjs", "binding-store.mjs",
            "catalogue.mjs", "composition.mjs", "contract.mjs",
            "credential-flow.mjs", "limits.mjs", "policy.mjs",
            "powershell-lexer.mjs", "redaction.mjs", "response.mjs",
        )
    ),
)
CANONICAL_HOOK_BLOCK = """hooks:
  PreToolUse:
    - matcher: Bash
      hooks:
        - type: command
          command: "{{skills_dir}}/command-driven-operations/scripts/command-guard-launcher.sh"
          args:
            - pre
          timeout: 7
  PostToolUse:
    - matcher: Bash
      hooks:
        - type: command
          command: "{{skills_dir}}/command-driven-operations/scripts/command-guard-launcher.sh"
          args:
            - post
          timeout: 7
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
        "pre": {"matcher": "Bash", "arg": "pre", "timeout": 7},
        "post": {"matcher": "Bash", "arg": "post", "timeout": 7},
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
    posttool_count = len(
        re.findall(r"^\s*PostToolUse:\s*$", frontmatter, re.MULTILINE)
    )
    exact_count = text.count(CANONICAL_HOOK_BLOCK)

    if agent_id in ANALYTICAL_AGENTS:
        if pretool_count or posttool_count or re.search(
            r"^\s*-\s*matcher:\s*Bash\s*$", frontmatter, re.MULTILINE
        ):
            errors.append(f"analytical agent declares Bash hook: {agent_id}")
        return errors

    if agent_id not in EXECUTOR_AGENTS:
        return [f"unknown subagent command guard policy: {agent_id}"]

    if pretool_count == 0 or posttool_count == 0:
        errors.append(f"missing command guard hook: {agent_id}")
    if pretool_count != 1 or posttool_count != 1 or exact_count != 1:
        errors.append(f"executor must have exactly one command guard hook: {agent_id}")
    matcher = re.findall(
        r"^\s*-\s*matcher:\s*(.*?)\s*$", frontmatter, re.MULTILINE
    )
    if matcher and matcher != ["Bash", "Bash"]:
        errors.append(f"command guard matcher must be exactly Bash: {agent_id}")
    timeout = re.findall(
        r"^\s*(?:Pre|Post)ToolUse:\s*$.*?^\s*timeout:\s*(.*?)\s*$",
        frontmatter,
        re.MULTILINE | re.DOTALL,
    )
    if timeout and timeout != ["7", "7"]:
        errors.append(f"command guard timeout must be 7 seconds: {agent_id}")
    if pretool_count and exact_count != 1:
        errors.append(f"command guard hook must use canonical exec form: {agent_id}")
    return errors


def installed_command_guard_hook(
    text: str, installed_skills_dir: Path
) -> dict[str, object] | None:
    """Return installed lifecycle semantics when the exact block is present."""
    expected_blocks = {
        CANONICAL_HOOK_BLOCK.replace("{{skills_dir}}", str(installed_skills_dir)),
        CANONICAL_HOOK_BLOCK.replace(
            "{{skills_dir}}", installed_skills_dir.as_posix()
        ),
    }
    if not any(text.count(expected) == 1 for expected in expected_blocks):
        return None
    return {"pre": "Bash", "post": "Bash", "timeout": 7}


def installed_hook_errors(
    agent_id: str,
    source: str,
    installed: str,
    installed_skills_dir: Path,
) -> list[str]:
    """Return installed hook differences and unresolved validator paths."""
    errors: list[str] = []
    installed_hook = installed_command_guard_hook(installed, installed_skills_dir)
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
    expected_path = (installed_skills_dir / LAUNCHER_RELATIVE_PATH).resolve()
    if not expected_path.is_file():
        errors.append(f"installed launcher missing: {expected_path}")
    return errors


def installed_artifact_errors(installed_skills_dir: Path) -> list[str]:
    """Require installed security-critical artifacts to equal package source."""
    errors: list[str] = []
    source_skills = ROOT / "skills"
    for relative in SECURITY_CRITICAL_ARTIFACTS:
        source = source_skills / relative
        installed = installed_skills_dir / relative
        if not installed.is_file():
            errors.append(f"installed command guard artifact missing: {relative}")
        elif installed.read_bytes() != source.read_bytes():
            errors.append(f"installed command guard artifact differs: {relative}")
    return errors


def installed_corpus_errors(installed_skills_dir: Path) -> list[str]:
    """Execute the source review corpus against installed policy modules."""
    scripts = installed_skills_dir / "command-driven-operations" / "scripts"
    runner = ROOT / "tests" / "command-guard" / "run-installed-corpus.mjs"
    result = subprocess.run(
        ["node", str(runner), str(scripts)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return []
    detail = (result.stderr or result.stdout).strip().splitlines()[-1:]
    return [f"installed command guard corpus failed: {' '.join(detail)}"]
