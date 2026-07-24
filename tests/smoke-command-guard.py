#!/usr/bin/env python3
"""Test-only fail-closed command guard and subagent lifecycle recorder."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


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
    command = tool_input.get("command") if isinstance(tool_input, dict) else None
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
    raise SystemExit(0)

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
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": (
                        "P0-03 smoke permits only its exact synthetic printf."
                    ),
                }
            }
        )
    )
    raise SystemExit(0)

print(
    json.dumps(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "permissionDecisionReason": "Exact synthetic smoke command.",
            }
        }
    )
)
