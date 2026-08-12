#!/usr/bin/env python3
"""Minimal content-free stdio MCP server for disposable live validation."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def emit(identifier: object, result: dict[str, object]) -> None:
    print(json.dumps({"jsonrpc": "2.0", "id": identifier, "result": result}, separators=(",", ":")), flush=True)


def main() -> int:
    if len(sys.argv) != 2:
        return 2
    signal = Path(sys.argv[1])
    for raw in sys.stdin:
        try:
            message = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(message, dict):
            continue
        method = message.get("method")
        identifier = message.get("id")
        if method == "initialize" and identifier is not None:
            signal.write_text(
                json.dumps({"connected": True, "toolsListed": False}, separators=(",", ":")) + "\n",
                encoding="utf-8",
            )
            emit(identifier, {
                "protocolVersion": "2025-06-18",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "p004a-context-fixture", "version": "1"},
            })
        elif method == "tools/list" and identifier is not None:
            signal.write_text(
                json.dumps({"connected": True, "toolsListed": True, "visibleToolCount": 1}, separators=(",", ":")) + "\n",
                encoding="utf-8",
            )
            emit(identifier, {"tools": [{
                "name": "context_fixture_ping",
                "description": "Returns a fixed context-fixture acknowledgement.",
                "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
            }]})
        elif method == "tools/call" and identifier is not None:
            emit(identifier, {"content": [{"type": "text", "text": "context fixture ok"}]})
        elif method == "ping" and identifier is not None:
            emit(identifier, {})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
