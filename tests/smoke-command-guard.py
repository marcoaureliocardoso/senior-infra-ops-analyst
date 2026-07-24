#!/usr/bin/env python3
"""Test-only fail-closed command guard and subagent lifecycle recorder."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def permission_output(decision: str, reason: str) -> str:
    """Return the structured Claude Code PreToolUse decision."""
    return json.dumps(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": decision,
                "permissionDecisionReason": reason,
            }
        }
    )


def main() -> int:
    """Process one hook event, failing closed with Claude's blocking exit code."""
    try:
        event = json.load(sys.stdin)
        event_name = event.get("hook_event_name")
        agent_type = event.get("agent_type")
        record = {
            "hook_event_name": event_name,
            "agent_type": agent_type,
        }

        if event_name == "PreToolUse":
            tool_name = event.get("tool_name")
            tool_input = event.get("tool_input", {})
            command = (
                tool_input.get("command") if isinstance(tool_input, dict) else None
            )
            record.update({"tool_name": tool_name, "command": command})
        elif event_name == "SubagentStop":
            transcript = Path(str(event.get("agent_transcript_path", "")))
            assistant_turns = 0
            if transcript.is_file():
                for line in transcript.read_text(encoding="utf-8").splitlines():
                    if line.strip() and json.loads(line).get("type") == "assistant":
                        assistant_turns += 1
            record["assistant_turns"] = assistant_turns

        log_path = Path(os.environ["P0_03_HOOK_LOG"])
        with log_path.open("a", encoding="utf-8") as log:
            log.write(json.dumps(record, separators=(",", ":")) + "\n")

        if event_name != "PreToolUse":
            return 0

        allowed_commands = {
            "diagnostic-operator": "printf 'p0-03-smoke\\n'",
            "turn-cutoff-probe": "printf 'turn-cutoff\\n'",
        }
        expected = allowed_commands.get(str(agent_type))
        background = (
            tool_input.get("run_in_background", False)
            if isinstance(tool_input, dict)
            else True
        )
        if tool_name != "Bash" or command != expected or background:
            print(
                permission_output(
                    "deny",
                    "P0-03 smoke permits only its exact synthetic printf.",
                )
            )
            return 0

        print(permission_output("allow", "Exact synthetic smoke command."))
        return 0
    except Exception as error:
        print(
            f"P0-03 smoke guard failed closed ({type(error).__name__}).",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
