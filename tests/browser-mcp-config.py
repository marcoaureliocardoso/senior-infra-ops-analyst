#!/usr/bin/env python3
"""Create minimal private MCP configs for the disposable P0-04B harness."""
from __future__ import annotations

import json
import os
import re
import stat
import sys
from pathlib import Path
from typing import Any


MAX_SOURCE_BYTES = 2 * 1024 * 1024
NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
LABEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/+@-]{0,95}$")


def load_source(path: Path) -> dict[str, Any]:
    if not path.is_absolute() or path.is_symlink():
        raise ValueError("unsafe MCP source")
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or not 2 <= metadata.st_size <= MAX_SOURCE_BYTES:
            raise ValueError("invalid MCP source")
        payload = os.read(descriptor, MAX_SOURCE_BYTES + 1)
        if len(payload) != metadata.st_size:
            raise ValueError("unstable MCP source")
    finally:
        os.close(descriptor)
    value = json.loads(payload.decode("utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("mcpServers"), dict):
        raise ValueError("invalid MCP source")
    return value


def write_private(path: Path, value: dict[str, Any]) -> None:
    if os.name == "nt" or not hasattr(os, "O_NOFOLLOW") or not path.is_absolute():
        raise ValueError("private MCP output requires POSIX")
    payload = (json.dumps(value, separators=(",", ":")) + "\n").encode("utf-8")
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    descriptor: int | None = None
    try:
        descriptor = os.open(
            temporary,
            os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW"),
            0o600,
        )
        remaining = memoryview(payload)
        while remaining:
            written = os.write(descriptor, remaining)
            if written <= 0:
                raise OSError("MCP config write made no progress")
            remaining = remaining[written:]
        os.fsync(descriptor)
    finally:
        if descriptor is not None:
            os.close(descriptor)
    try:
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def build(
    source: Path, tool: str, approval_output: Path, measurement_output: Path,
    fixture: Path, signal: Path, nonce: str,
) -> None:
    if not LABEL.fullmatch(nonce) or not fixture.is_absolute() or fixture.is_symlink():
        raise ValueError("invalid fixture binding")
    value = load_source(source)
    servers = value["mcpServers"]
    candidates: list[str] = []
    for name in servers:
        if not isinstance(name, str):
            raise ValueError("invalid approval server name")
        prefix = f"mcp__{name}__"
        suffix = tool[len(prefix):] if isinstance(tool, str) and tool.startswith(prefix) else ""
        if NAME.fullmatch(name) and NAME.fullmatch(suffix):
            candidates.append(name)
    if len(candidates) != 1 or candidates[0] == "p004b-context":
        raise ValueError("approval tool does not bind exactly one server")
    server = candidates[0]
    server_value = servers[server]
    if not isinstance(server_value, dict):
        raise ValueError("invalid approval server")
    approval = {"mcpServers": {server: server_value}}
    measurement = {"mcpServers": {
        server: server_value,
        "p004b-context": {
            "command": "python3",
            "args": [str(fixture), str(signal), nonce],
        },
    }}
    write_private(approval_output, approval)
    write_private(measurement_output, measurement)


def main() -> int:
    if len(sys.argv) != 8:
        return 2
    build(
        Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3]), Path(sys.argv[4]),
        Path(sys.argv[5]), Path(sys.argv[6]), sys.argv[7],
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
        print("private MCP configuration rejected", file=sys.stderr)
        raise SystemExit(2)
