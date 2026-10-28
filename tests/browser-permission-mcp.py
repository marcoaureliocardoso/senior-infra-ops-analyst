#!/usr/bin/env python3
"""Single-use, test-only permission MCP for P0-04B acceptance."""
from __future__ import annotations

import json
import os
import re
import signal as process_signal
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


LABEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}$")
ORIGIN = re.compile(r"^http://127\.0\.0\.1:[1-9][0-9]{0,4}$")
MAX_MESSAGE_BYTES = 131_072
MAX_VERIFIER_OUTPUT_BYTES = 4_096
PROTOCOL_VERSION = "2025-06-18"


class Rejected(Exception):
    """A deliberately content-free rejection."""


def emit_result(identifier: object, result: dict[str, object]) -> None:
    print(json.dumps({"jsonrpc": "2.0", "id": identifier, "result": result}, separators=(",", ":")), flush=True)


def emit_error(identifier: object, code: int, message: str) -> None:
    print(json.dumps({
        "jsonrpc": "2.0", "id": identifier,
        "error": {"code": code, "message": message},
    }, separators=(",", ":")), flush=True)


def permission_result(permission: dict[str, object]) -> dict[str, object]:
    return {"content": [{"type": "text", "text": json.dumps(permission, separators=(",", ":"))}]}


def generic_deny() -> dict[str, object]:
    return permission_result({"behavior": "deny", "message": "P004B_PERMISSION_DENIED"})


def regular_absolute(path: Path) -> bool:
    try:
        metadata = path.lstat()
    except OSError:
        return False
    return path.is_absolute() and not stat.S_ISLNK(metadata.st_mode) and stat.S_ISREG(metadata.st_mode)


def validate_configuration(argv: list[str]) -> dict[str, object]:
    if os.name == "nt" or not hasattr(os, "O_NOFOLLOW") or len(argv) != 11:
        raise Rejected
    verifier, node, runner = map(Path, argv[:3])
    phase, decision, operation, session, nonce, origin = argv[3:9]
    claim, signal = map(Path, argv[9:11])
    if not all(regular_absolute(path) for path in (verifier, node, runner)):
        raise Rejected
    if (phase, decision) not in {("allow", "allow"), ("deny", "deny")}:
        raise Rejected
    if not all(LABEL.fullmatch(value) for value in (operation, session, nonce)):
        raise Rejected
    if not ORIGIN.fullmatch(origin):
        raise Rejected
    if not claim.is_absolute() or not signal.is_absolute() or claim == signal:
        raise Rejected
    if claim.parent.resolve() != signal.parent.resolve() or claim.parent.is_symlink():
        raise Rejected
    parent = claim.parent
    try:
        mode = parent.stat().st_mode
    except OSError as error:
        raise Rejected from error
    if not stat.S_ISDIR(mode) or mode & 0o077:
        raise Rejected
    return {
        "verifier": verifier, "node": node, "runner": runner,
        "phase": phase, "decision": decision, "operation": operation,
        "session": session, "nonce": nonce, "origin": origin,
        "claim": claim, "signal": signal,
    }


def claim_once(path: Path) -> bool:
    try:
        descriptor = os.open(
            path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600,
        )
    except OSError:
        return False
    try:
        os.write(descriptor, b"claimed\n")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return True


def write_signal(path: Path, value: dict[str, object]) -> None:
    try:
        path.lstat()
    except FileNotFoundError:
        pass
    else:
        raise Rejected
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
                raise Rejected
            remaining = remaining[count:]
        os.fsync(descriptor)
    finally:
        if descriptor is not None:
            os.close(descriptor)
    try:
        os.replace(temporary, path)
        os.chmod(path, 0o600, follow_symlinks=False)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def run_verifier(configuration: dict[str, object], arguments: object) -> dict[str, object] | None:
    payload = json.dumps(arguments, separators=(",", ":")).encode("utf-8")
    if len(payload) > MAX_MESSAGE_BYTES:
        return None
    command = [
        str(configuration["node"]), str(configuration["verifier"]),
        str(configuration["phase"]), str(configuration["runner"]),
        str(configuration["operation"]), str(configuration["session"]),
        str(configuration["nonce"]), str(configuration["origin"]),
        str(configuration["decision"]),
    ]
    with tempfile.TemporaryFile() as output:
        process = subprocess.Popen(
            command, stdin=subprocess.PIPE, stdout=output, stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        try:
            process.communicate(payload, timeout=5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, process_signal.SIGKILL)
            except OSError:
                process.kill()
            process.wait(timeout=5)
            return None
        if process.returncode != 0:
            return None
        output.seek(0)
        encoded = output.read(MAX_VERIFIER_OUTPUT_BYTES + 1)
    if len(encoded) > MAX_VERIFIER_OUTPUT_BYTES or encoded.count(b"\n") != 1:
        return None
    try:
        value = json.loads(encoded)
    except (UnicodeError, json.JSONDecodeError):
        return None
    expected_keys = {
        "verified", "reasonCode", "phase", "decision", "invocationFingerprint",
        "operationId", "expectedEffect", "executionSteps", "validationSteps",
    }
    if not isinstance(value, dict) or set(value) != expected_keys:
        return None
    return value


def exact_verification(value: dict[str, object] | None, configuration: dict[str, object]) -> bool:
    expected_execution_steps = 8 if configuration["phase"] == "allow" else 7
    return bool(
        value
        and value["verified"] is True
        and value["reasonCode"] == "P004B_PERMISSION_EXACT"
        and value["phase"] == configuration["phase"]
        and value["decision"] == configuration["decision"]
        and value["operationId"] == configuration["operation"]
        and value["expectedEffect"] == "LOW_RISK_CHANGE"
        and value["executionSteps"] == expected_execution_steps
        and value["validationSteps"] == 7
        and isinstance(value["invocationFingerprint"], str)
        and re.fullmatch(r"[0-9a-f]{64}", value["invocationFingerprint"])
    )


def handle_call(configuration: dict[str, object], params: object) -> dict[str, object]:
    if not isinstance(params, dict) or set(params) != {"name", "arguments"} or params.get("name") != "approval_prompt":
        return generic_deny()
    arguments = params.get("arguments")
    if not claim_once(configuration["claim"]):
        return generic_deny()
    verified = run_verifier(configuration, arguments)
    if not exact_verification(verified, configuration):
        return generic_deny()
    if not isinstance(arguments, dict) or not isinstance(arguments.get("input"), dict):
        return generic_deny()
    signal = {
        "schemaVersion": 1,
        "runNonce": configuration["nonce"],
        "phase": configuration["phase"],
        "decision": configuration["decision"],
        "callCount": 1,
        "invocationFingerprint": verified["invocationFingerprint"],
        "verified": True,
        "inputUnchanged": True,
    }
    try:
        write_signal(configuration["signal"], signal)
    except (OSError, Rejected):
        return generic_deny()
    if configuration["decision"] == "allow":
        return permission_result({"behavior": "allow", "updatedInput": arguments["input"]})
    return permission_result({"behavior": "deny", "message": "P004B_SYNTHETIC_DENY"})


def serve(configuration: dict[str, object]) -> int:
    initialized = False
    listed = False
    for raw in sys.stdin.buffer:
        if len(raw) > MAX_MESSAGE_BYTES:
            continue
        try:
            message = json.loads(raw)
        except (UnicodeError, json.JSONDecodeError):
            continue
        if not isinstance(message, dict):
            continue
        method = message.get("method")
        identifier = message.get("id")
        if method == "initialize" and identifier is not None:
            initialized = True
            emit_result(identifier, {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "p004b-permission", "version": "1"},
            })
        elif method == "tools/list" and identifier is not None:
            if not initialized:
                emit_error(identifier, -32002, "not initialized")
                continue
            listed = True
            emit_result(identifier, {"tools": [{
                "name": "approval_prompt",
                "description": "Returns one deterministic P0-04B test permission decision.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "tool_name": {"type": "string", "const": "Bash"},
                        "input": {"type": "object"},
                    },
                    "required": ["tool_name", "input"],
                    "additionalProperties": False,
                },
            }]})
        elif method == "tools/call" and identifier is not None:
            if not initialized or not listed:
                emit_error(identifier, -32002, "tool lifecycle incomplete")
                continue
            emit_result(identifier, handle_call(configuration, message.get("params")))
        elif method == "ping" and identifier is not None:
            emit_result(identifier, {})
    return 0


def main() -> int:
    try:
        configuration = validate_configuration(sys.argv[1:])
    except Rejected:
        print("P004B permission MCP rejected", file=sys.stderr)
        return 2
    return serve(configuration)


if __name__ == "__main__":
    raise SystemExit(main())
