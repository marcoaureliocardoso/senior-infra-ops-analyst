#!/usr/bin/env python3
"""Compare Nori-installed Claude Code subagents with their source semantics."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from subagent_runtime_policy import (
    ROLE_POLICY,
    frontmatter_fields,
    frontmatter_skills,
    runtime_precedence_section,
    runtime_section,
)


ROOT = Path(__file__).resolve().parents[1]
FIELDS = ("maxTurns", "tools", "disallowedTools", "model")


def installed_subagent_errors(installed_dir: Path) -> list[str]:
    """Return source-to-installed semantic differences."""
    errors: list[str] = []
    if not installed_dir.is_dir():
        return [f"installed agents directory not found: {installed_dir}"]

    for agent_id in sorted(ROLE_POLICY):
        source_path = ROOT / "subagents" / f"{agent_id}.md"
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

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--installed-agents-dir",
        required=True,
        type=Path,
        help="Claude Code agents directory produced by Nori",
    )
    args = parser.parse_args()
    errors = installed_subagent_errors(args.installed_agents_dir.resolve())
    if errors:
        print("Installed subagent validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("installed subagent validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
