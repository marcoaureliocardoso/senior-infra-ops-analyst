#!/usr/bin/env python3
"""Create closed, phase-isolated MCP configs for disposable P0-04B tests."""
from __future__ import annotations

import json
import os
import re
import stat
import sys
from pathlib import Path
from urllib.parse import urlsplit


LABEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/+-]{0,95}$")
OUTPUT_NAMES = ("empty-mcp.json", "measurement-mcp.json", "allow-mcp.json", "deny-mcp.json")


def regular_canonical(path: Path) -> bool:
    try:
        metadata = path.lstat()
        resolved = path.resolve(strict=True)
    except OSError:
        return False
    return (
        path.is_absolute()
        and resolved == path
        and not stat.S_ISLNK(metadata.st_mode)
        and stat.S_ISREG(metadata.st_mode)
    )


def loopback_origin(value: str) -> bool:
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except (TypeError, ValueError):
        return False
    return (
        parsed.scheme == "http"
        and parsed.hostname == "127.0.0.1"
        and port is not None
        and 1 <= port <= 65_535
        and not parsed.username
        and not parsed.password
        and parsed.path == ""
        and parsed.query == ""
        and parsed.fragment == ""
        and value == f"http://127.0.0.1:{port}"
    )


def private_output_directory(path: Path) -> bool:
    try:
        metadata = path.lstat()
        resolved = path.resolve(strict=True)
    except OSError:
        return False
    return (
        os.name != "nt"
        and hasattr(os, "O_NOFOLLOW")
        and path.is_absolute()
        and resolved == path
        and not stat.S_ISLNK(metadata.st_mode)
        and stat.S_ISDIR(metadata.st_mode)
        and metadata.st_mode & 0o077 == 0
    )


def absent_output(path: Path, output_dir: Path) -> bool:
    if not path.is_absolute() or path.parent != output_dir:
        return False
    try:
        path.lstat()
    except FileNotFoundError:
        return True
    except OSError:
        return False
    return False


def write_private(path: Path, value: dict[str, object]) -> None:
    payload = (json.dumps(value, separators=(",", ":")) + "\n").encode("utf-8")
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    descriptor: int | None = None
    try:
        descriptor = os.open(
            temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600,
        )
        remaining = memoryview(payload)
        while remaining:
            count = os.write(descriptor, remaining)
            if count <= 0:
                raise OSError("private write made no progress")
            remaining = remaining[count:]
        os.fsync(descriptor)
    finally:
        if descriptor is not None:
            os.close(descriptor)
    try:
        os.link(temporary, path, follow_symlinks=False)
        os.chmod(path, 0o600, follow_symlinks=False)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def permission_server(
    handler: Path, verifier: Path, node: Path, runner: Path,
    phase: str, operation: str, session: str, nonce: str, origin: str,
    claim: Path, signal: Path,
) -> dict[str, object]:
    return {
        "command": sys.executable,
        "args": [
            str(handler), str(verifier), str(node), str(runner), phase, phase,
            operation, session, nonce, origin, str(claim), str(signal),
        ],
    }


def build(
    handler: Path, verifier: Path, node: Path, runner: Path,
    fixture: Path, output_dir: Path, fixture_signal: Path,
    nonce: str, origin: str, allow_session: str, deny_session: str,
) -> None:
    inputs = (handler, verifier, node, runner, fixture)
    if not all(regular_canonical(path) for path in inputs):
        raise ValueError("invalid executable input")
    if not private_output_directory(output_dir):
        raise ValueError("invalid output directory")
    if not LABEL.fullmatch(nonce) or not loopback_origin(origin):
        raise ValueError("invalid run binding")
    if not LABEL.fullmatch(allow_session) or not LABEL.fullmatch(deny_session) or allow_session == deny_session:
        raise ValueError("invalid session binding")

    outputs = {name: output_dir / name for name in OUTPUT_NAMES}
    allow_claim = output_dir / "allow.claim"
    allow_signal = output_dir / "allow.signal.json"
    deny_claim = output_dir / "deny.claim"
    deny_signal = output_dir / "deny.signal.json"
    disposable = (fixture_signal, allow_claim, allow_signal, deny_claim, deny_signal)
    if not all(absent_output(path, output_dir) for path in (*outputs.values(), *disposable)):
        raise ValueError("output already exists or escapes root")

    allow_operation = f"{nonce}-allow-operation"
    deny_operation = f"{nonce}-deny-operation"
    if not LABEL.fullmatch(allow_operation) or not LABEL.fullmatch(deny_operation):
        raise ValueError("invalid operation binding")
    values: dict[str, dict[str, object]] = {
        "empty-mcp.json": {"mcpServers": {}},
        "measurement-mcp.json": {"mcpServers": {
            "p004b-context": {
                "command": sys.executable,
                "args": [str(fixture), str(fixture_signal), nonce],
            },
        }},
        "allow-mcp.json": {"mcpServers": {
            "p004b-permission": permission_server(
                handler, verifier, node, runner, "allow", allow_operation,
                allow_session, nonce, origin, allow_claim, allow_signal,
            ),
        }},
        "deny-mcp.json": {"mcpServers": {
            "p004b-permission": permission_server(
                handler, verifier, node, runner, "deny", deny_operation,
                deny_session, nonce, origin, deny_claim, deny_signal,
            ),
        }},
    }
    for name in OUTPUT_NAMES:
        write_private(outputs[name], values[name])


def main() -> int:
    if len(sys.argv) != 12:
        return 2
    build(
        Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]),
        Path(sys.argv[5]), Path(sys.argv[6]), Path(sys.argv[7]), sys.argv[8],
        sys.argv[9], sys.argv[10], sys.argv[11],
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
        print("private MCP configuration rejected", file=sys.stderr)
        raise SystemExit(2)
