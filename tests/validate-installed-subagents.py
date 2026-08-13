#!/usr/bin/env python3
"""Compare Nori-installed Claude Code subagents with their source semantics."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from subagent_runtime_policy import (
    ROLE_POLICY,
    frontmatter_fields,
    frontmatter_skills,
    runtime_precedence_section,
    runtime_section,
)
from scripts.nori_package import subagent_definition_path
from command_guard_install_policy import (
    installed_artifact_errors,
    installed_corpus_errors,
    installed_hook_errors,
)
from context_continuity_install_policy import (
    installed_continuity_artifact_errors,
    installed_continuity_hook_errors,
)

FIELDS = ("maxTurns", "tools", "disallowedTools", "model")


def installed_subagent_errors(
    installed_dir: Path, installed_skills_dir: Path
) -> list[str]:
    """Return source-to-installed semantic differences."""
    errors: list[str] = []
    if not installed_dir.is_dir():
        return [f"installed agents directory not found: {installed_dir}"]

    errors.extend(installed_artifact_errors(installed_skills_dir))
    errors.extend(installed_continuity_artifact_errors(installed_skills_dir))
    if not errors:
        errors.extend(installed_corpus_errors(installed_skills_dir))

    for agent_id in sorted(ROLE_POLICY):
        source_path = subagent_definition_path(ROOT, agent_id)
        installed_path = installed_dir / f"{agent_id}.md"
        if not installed_path.exists():
            errors.append(f"missing installed subagent: {agent_id}")
            continue

        source = source_path.read_text(encoding="utf-8")
        installed = installed_path.read_text(encoding="utf-8")
        source_fields = frontmatter_fields(source)
        installed_fields = frontmatter_fields(installed)

        for field in FIELDS:
            if installed_fields[field] != source_fields[field]:
                errors.append(f"installed {field} differs: {agent_id}")
        if frontmatter_skills(installed) != frontmatter_skills(source):
            errors.append(f"installed skills differ: {agent_id}")
        if runtime_section(installed).strip() != runtime_section(source).strip():
            errors.append(f"installed runtime controls differ: {agent_id}")
        if runtime_precedence_section(installed).strip() != (
            runtime_precedence_section(source).strip()
        ):
            errors.append(f"installed runtime precedence differs: {agent_id}")
        errors.extend(
            installed_hook_errors(
                agent_id, source, installed, installed_skills_dir
            )
        )
        errors.extend(
            installed_continuity_hook_errors(
                agent_id, source, installed, installed_skills_dir
            )
        )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--installed-agents-dir",
        required=True,
        type=Path,
        help="Claude Code agents directory produced by Nori",
    )
    parser.add_argument(
        "--installed-skills-dir",
        required=True,
        type=Path,
        help="Claude Code skills directory produced by Nori",
    )
    args = parser.parse_args()
    errors = installed_subagent_errors(
        args.installed_agents_dir.resolve(), args.installed_skills_dir.resolve()
    )
    if errors:
        print("Installed subagent validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("installed subagent validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
