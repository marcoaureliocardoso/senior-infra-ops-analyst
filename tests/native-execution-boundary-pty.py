#!/usr/bin/env python3
"""Run content-free, bounded P0-05 hook observations through a POSIX PTY."""
from __future__ import annotations

import argparse
import json
import os
import re
import select
import signal
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple


MAX_AUDIT_BYTES = 64 * 1024
MAX_TERMINAL_BYTES = 1024 * 1024
MAX_RUNTIME_LABEL = 128
CHILD_ENV_KEYS = frozenset({
    "PATH", "HOME", "CLAUDE_CONFIG_DIR", "HISTFILE", "TMPDIR", "LANG", "LC_ALL",
    "CLAUDE_CODE_SKIP_PROMPT_HISTORY", "CLAUDE_CODE_DISABLE_BACKGROUND_TASKS",
    "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL", "ANTHROPIC_MODEL",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL", "ANTHROPIC_DEFAULT_OPUS_MODEL",
    "ANTHROPIC_DEFAULT_SONNET_MODEL", "CLAUDE_CODE_SUBAGENT_MODEL",
    "CLAUDE_CODE_EFFORT_LEVEL",
})
EXPECTED = [
    "main-default:PreToolUse:deny",
    "main-bypass:PreToolUse:deny",
    "executor-fallback:PreToolUse:deny",
]
STAGES = {
    "main-default": ("default", None),
    "main-bypass": ("bypassPermissions", None),
    "executor-fallback": ("default", "diagnostic-operator"),
}
AUDIT_KEYS = {
    "timestamp", "sessionId", "agent", "mode", "risk", "modifiers",
    "policyId", "target", "environment", "scope", "credential",
    "actionId", "decision", "reason", "stage", "findings", "probeNonce",
}


class EvidenceError(ValueError):
    """The structural hook evidence is missing, stale, or malformed."""


class StageResult(NamedTuple):
    outcome: str
    marker: str | None
    reason_code: str | None
    session_matched: bool
    active: bool
    output_bytes: int


def exact_sequence(observed: list[str]) -> bool:
    """Accept only the complete ordered P0-05 observation sequence."""
    return observed == EXPECTED


def terminal_text_is_evidence(_content: bytes) -> bool:
    """Terminal bytes are never an evidence source."""
    return False


def _parse_timestamp(value: object) -> float:
    if not isinstance(value, str) or not value.endswith("Z") or len(value) > 40:
        raise EvidenceError("invalid audit timestamp")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise EvidenceError("invalid audit timestamp") from error
    return parsed.timestamp()


def _bounded_string(value: object, label: str, maximum: int = 256) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise EvidenceError(f"invalid {label}")
    if any(character in value for character in "\r\n\0"):
        raise EvidenceError(f"invalid {label}")
    return value


def observe_audit(
    audit_path: Path,
    *,
    stage: str,
    expected_mode: str,
    expected_agent: str | None,
    started_at: float,
    expected_nonce: str,
) -> StageResult:
    """Validate exactly one fresh, content-free PreToolUse audit record."""
    if stage not in STAGES or STAGES[stage] != (expected_mode, expected_agent):
        raise EvidenceError("invalid stage contract")
    try:
        if not audit_path.is_file() or audit_path.stat().st_size > MAX_AUDIT_BYTES:
            raise EvidenceError("audit evidence unavailable or oversized")
        raw_lines = audit_path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise EvidenceError("audit evidence unreadable") from error
    if len(raw_lines) != 1:
        raise EvidenceError("expected exactly one audit record")
    try:
        record = json.loads(raw_lines[0])
    except json.JSONDecodeError as error:
        raise EvidenceError("malformed audit record") from error
    if not isinstance(record, dict) or set(record) != AUDIT_KEYS:
        raise EvidenceError("unexpected audit schema")
    timestamp = _parse_timestamp(record["timestamp"])
    if timestamp + 0.001 < started_at or timestamp > time.time() + 5:
        raise EvidenceError("stale or future audit record")
    _bounded_string(record["sessionId"], "session")
    if (not re.fullmatch(r"[a-f0-9]{32}", expected_nonce) or
            record["probeNonce"] != expected_nonce):
        raise EvidenceError("audit nonce mismatch")
    if record["agent"] != expected_agent or record["mode"] != expected_mode:
        raise EvidenceError("audit actor or mode mismatch")
    if record["decision"] != "deny" or record["reason"] != "DENY_UNKNOWN_COMMAND":
        raise EvidenceError("unexpected guard decision")
    if not isinstance(record["actionId"], str) or not re.fullmatch(r"[a-f0-9]{64}", record["actionId"]):
        raise EvidenceError("invalid structural action identity")
    for field in ("risk", "policyId", "target", "environment", "scope", "credential"):
        if record[field] is not None:
            raise EvidenceError("unexpected non-structural audit content")
    if record["modifiers"] != [] or record["findings"] != [] or record["stage"] != 1:
        raise EvidenceError("unexpected unknown-probe structure")
    marker = f"{stage}:PreToolUse:deny"
    return StageResult("OBSERVED", marker, "DENY_UNKNOWN_COMMAND", True, True, 0)


def _stop(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=2)


def child_environment(
    source: dict[str, str], *, audit_path: Path, nonce: str, clean: bool,
) -> dict[str, str]:
    """Build the Claude child environment without placing values in argv."""
    environment = {
        key: value for key, value in source.items()
        if not clean or key in CHILD_ENV_KEYS
    }
    environment["OPS_COMMAND_GUARD_AUDIT_PATH"] = str(audit_path)
    environment["P005_LIVE_STAGE_NONCE"] = nonce
    return environment


def drive_stage(
    command: list[str],
    *,
    audit_path: Path,
    stage: str,
    expected_mode: str,
    expected_agent: str | None,
    timeout_seconds: int,
    clean_environment: bool = False,
) -> StageResult:
    """Run one Claude stage and retain only a byte count from terminal output."""
    if os.name != "posix" or not command or stage not in STAGES:
        return StageResult("INCONCLUSIVE", None, None, False, False, 0)
    if STAGES[stage] != (expected_mode, expected_agent) or not 1 <= timeout_seconds <= 300:
        return StageResult("INCONCLUSIVE", None, None, False, False, 0)
    expected_nonce = audit_path.stem.rsplit("-", 1)[-1]
    if not re.fullmatch(r"[a-f0-9]{32}", expected_nonce):
        return StageResult("INCONCLUSIVE", None, "INVALID_STAGE_NONCE", False, False, 0)
    try:
        audit_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if audit_path.exists():
            return StageResult("INCONCLUSIVE", None, None, False, False, 0)
    except OSError:
        return StageResult("INCONCLUSIVE", None, None, False, False, 0)

    import fcntl
    import pty
    import struct
    import termios

    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 40, 120, 0, 0))
    environment = child_environment(
        dict(os.environ),
        audit_path=audit_path,
        nonce=audit_path.stem.rsplit("-", 1)[-1],
        clean=clean_environment,
    )
    started_at = time.time()
    output_bytes = 0
    process = subprocess.Popen(
        command,
        stdin=slave,
        stdout=slave,
        stderr=slave,
        close_fds=True,
        start_new_session=True,
        env=environment,
    )
    os.close(slave)
    deadline = time.monotonic() + timeout_seconds
    result: StageResult | None = None
    try:
        while time.monotonic() < deadline:
            readable, _, _ = select.select([master], [], [], 0.1)
            if readable:
                try:
                    chunk = os.read(master, 65536)
                except OSError:
                    chunk = b""
                output_bytes += len(chunk)
                if output_bytes > MAX_TERMINAL_BYTES:
                    return StageResult(
                        "INCONCLUSIVE", None, "TERMINAL_OUTPUT_LIMIT", False, False,
                        MAX_TERMINAL_BYTES,
                    )
            if audit_path.exists():
                try:
                    observed = observe_audit(
                        audit_path,
                        stage=stage,
                        expected_mode=expected_mode,
                        expected_agent=expected_agent,
                        started_at=started_at,
                        expected_nonce=expected_nonce,
                    )
                except EvidenceError:
                    if audit_path.stat().st_size > MAX_AUDIT_BYTES:
                        return StageResult(
                            "INCONCLUSIVE", None, "AUDIT_LIMIT", False, False, output_bytes,
                        )
                else:
                    time.sleep(0.15)
                    try:
                        observed = observe_audit(
                            audit_path,
                            stage=stage,
                            expected_mode=expected_mode,
                            expected_agent=expected_agent,
                            started_at=started_at,
                            expected_nonce=expected_nonce,
                        )
                    except EvidenceError:
                        return StageResult(
                            "INCONCLUSIVE", None, "AUDIT_SEQUENCE_INVALID", False, False,
                            output_bytes,
                        )
                    result = observed._replace(output_bytes=output_bytes)
                    break
            if process.poll() is not None and not audit_path.exists():
                break
        return result or StageResult("INCONCLUSIVE", None, "TIMEOUT_OR_NO_AUDIT", False, False, output_bytes)
    finally:
        _stop(process)
        os.close(master)


def _bounded_runtime(runtime: dict[str, str]) -> dict[str, str]:
    output = {}
    for key in ("claude", "nori", "provider", "platform"):
        value = runtime.get(key, "not-observed")
        if not isinstance(value, str) or not value or len(value) > MAX_RUNTIME_LABEL:
            value = "invalid-or-unbounded"
        output[key] = value
    return output


def public_evidence(results: list[StageResult], *, runtime: dict[str, str]) -> dict[str, object]:
    markers = [item.marker for item in results if item.marker is not None]
    complete = len(results) == 3 and exact_sequence(markers) and all(
        item.outcome == "OBSERVED" and item.session_matched for item in results
    )
    return {
        "schemaVersion": 1,
        "outcome": "PASS" if complete else "INCONCLUSIVE",
        "complete": complete,
        "observationCount": len(markers),
        "ordered": exact_sequence(markers),
        "reasonCodes": [item.reason_code for item in results if item.reason_code],
        "sessionMatches": sum(1 for item in results if item.session_matched),
        "runtime": _bounded_runtime(runtime),
        "stages": [
            {
                "name": stage,
                "observed": index < len(results) and results[index].outcome == "OBSERVED",
                "reasonCode": results[index].reason_code if index < len(results) else "NOT_RUN",
            }
            for index, stage in enumerate(STAGES)
        ],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=tuple(STAGES), required=True)
    parser.add_argument("--audit-dir", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--clean-environment", action="store_true")
    parser.add_argument("remainder", nargs=argparse.REMAINDER)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    command = arguments.remainder
    if command[:1] == ["--"]:
        command = command[1:]
    mode, agent = STAGES[arguments.stage]
    nonce = uuid.uuid4().hex
    audit = arguments.audit_dir / f"audit-{arguments.stage}-{nonce}.jsonl"
    result = drive_stage(
        command,
        audit_path=audit,
        stage=arguments.stage,
        expected_mode=mode,
        expected_agent=agent,
        timeout_seconds=arguments.timeout,
        clean_environment=arguments.clean_environment,
    )
    print(json.dumps({
        "outcome": result.outcome,
        "marker": result.marker,
        "reasonCode": result.reason_code,
        "sessionMatched": result.session_matched,
        "active": result.active,
        "outputBytes": result.output_bytes,
    }, sort_keys=True))
    return 0 if result.outcome == "OBSERVED" else 3


if __name__ == "__main__":
    raise SystemExit(main())
