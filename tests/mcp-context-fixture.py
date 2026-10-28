#!/usr/bin/env python3
"""Minimal content-free stdio MCP server for disposable live validation."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def emit(identifier: object, result: dict[str, object]) -> None:
    print(json.dumps({"jsonrpc": "2.0", "id": identifier, "result": result}, separators=(",", ":")), flush=True)


def update_signal(signal: Path, **updates: object) -> None:
    state: dict[str, object] = {}
    try:
        current = json.loads(signal.read_text(encoding="utf-8"))
        if isinstance(current, dict) and set(current).issubset({
            "connected", "toolsListed", "visibleToolCount", "called",
            "callCount", "runNonce",
        }):
            state = current
    except (OSError, UnicodeError, json.JSONDecodeError):
        pass
    for key, value in updates.items():
        if key in {"connected", "toolsListed", "called"} and state.get(key) is True:
            continue
        state[key] = value
    signal.write_text(json.dumps(state, separators=(",", ":")) + "\n", encoding="utf-8")


def main() -> int:
    if len(sys.argv) != 3:
        return 2
    signal = Path(sys.argv[1])
    expected_nonce = sys.argv[2]
    initialized = False
    listed = False
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
            update_signal(signal, connected=True, toolsListed=False)
            initialized = True
            emit(identifier, {
                "protocolVersion": "2025-06-18",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "p004b-context-fixture", "version": "1"},
            })
        elif method == "tools/list" and identifier is not None:
            if not initialized:
                print(json.dumps({
                    "jsonrpc": "2.0", "id": identifier,
                    "error": {"code": -32002, "message": "not initialized"},
                }, separators=(",", ":")), flush=True)
                continue
            update_signal(signal, toolsListed=True, visibleToolCount=1)
            listed = True
            emit(identifier, {"tools": [{
                "name": "context_fixture_ping",
                "description": "Returns a fixed context-fixture acknowledgement.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"nonce": {"type": "string", "const": expected_nonce}},
                    "required": ["nonce"],
                    "additionalProperties": False,
                },
            }]})
        elif method == "tools/call" and identifier is not None:
            params = message.get("params")
            if (initialized and listed and isinstance(params, dict)
                    and params.get("name") == "context_fixture_ping"
                    and params.get("arguments") == {"nonce": expected_nonce}):
                current: dict[str, object] = {}
                try:
                    loaded = json.loads(signal.read_text(encoding="utf-8"))
                    if isinstance(loaded, dict):
                        current = loaded
                except (OSError, UnicodeError, json.JSONDecodeError):
                    pass
                count = current.get("callCount", 0)
                if not isinstance(count, int) or isinstance(count, bool) or count < 0:
                    count = 0
                update_signal(
                    signal, called=True, callCount=count + 1,
                    runNonce=expected_nonce,
                )
                emit(identifier, {"content": [{"type": "text", "text": "context fixture ok"}]})
            else:
                print(json.dumps({
                    "jsonrpc": "2.0", "id": identifier,
                    "error": {"code": -32602, "message": "invalid tool"},
                }, separators=(",", ":")), flush=True)
        elif method == "ping" and identifier is not None:
            emit(identifier, {})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
