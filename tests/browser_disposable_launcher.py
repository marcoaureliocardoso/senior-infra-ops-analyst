#!/usr/bin/env python3
"""Test-only POSIX launcher boundary. The public CLI is credential-free preflight.

One child, no retries, no raw stream files; output is observations, not consent
or authenticated acceptance. Live credential transport is deliberately absent.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import selectors
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time

from browser_launch_diagnostics import MAX_INPUT_BYTES, MAX_LINE_BYTES, MAX_RECORDS, SUPPRESSED, reduce_line
from browser_operations_live import (
    _prepare_supervised_child, _SUPERVISOR_SIGNALS, _terminate_process_group,
    _unique_json_object, validate_aggregate,
)

PREFLIGHT_REASONS = frozenset((
    "PREFLIGHT_READY", "PREFLIGHT_ADAPTER_UNAVAILABLE", "PREFLIGHT_ADAPTER_CONFLICT",
))


def preflight_environment(source: dict[str, str]) -> dict[str, str]:
    """No inheritance of credentials, authorization, settings or startup hooks."""
    return {key: source[key] for key in (
        "HOME", "PATH", "P004B_BROWSER_NODE_MODULES", "P004B_PLAYWRIGHT_BROWSERS_PATH",
        "P004B_TERMINAL_NODE", "P004B_TERMINAL_MODULE_ROOT",
    ) if key in source}


def _reject_constant(_value: str):
    raise ValueError("nonfinite JSON")


class _Output:
    def __init__(self, max_records: int):
        self.records: list[dict] = []
        self.seen: set[str] = set()
        self.max_records = max_records
        self.aggregate: dict | None = None
        self.aggregate_count = 0
        self.aggregate_rejected = False

    def diagnostic(self, record: dict) -> None:
        key = json.dumps(record, sort_keys=True)
        if key not in self.seen:
            if len(self.records) >= self.max_records:
                raise _Limit("RECORD_LIMIT")
            self.seen.add(key)
            self.records.append(record)

    def line(self, channel: str, raw: bytes) -> None:
        payload = raw[:-1].removesuffix(b"\r") if raw.endswith(b"\n") else raw
        if channel == "stdout" and payload.lstrip().startswith(b"{"):
            self.aggregate_count += 1
            self.aggregate = None if self.aggregate_count > 1 else self.aggregate
            try:
                if self.aggregate_count != 1 or len(payload) > MAX_LINE_BYTES:
                    raise ValueError("ambiguous aggregate")
                value = json.loads(payload.decode("utf-8", errors="strict"),
                    object_pairs_hook=_unique_json_object, parse_constant=_reject_constant)
                validated = validate_aggregate(value)
                # Regex-bounded labels are not a content allowlist. Never forward
                # runtime strings or arbitrary reason codes from a valid schema.
                self.aggregate = {key: val for key, val in validated.items()
                                  if key not in {"observedRuntime", "reasonCode"}}
                self.aggregate["reasonCode"] = (
                    validated["reasonCode"] if validated["reasonCode"] in PREFLIGHT_REASONS
                    else "AGGREGATE_REASON_SUPPRESSED")
            except (ValueError, UnicodeError, RecursionError, TypeError):
                self.aggregate_rejected = True
                self.aggregate = None
            return
        self.diagnostic(reduce_line(raw))


class _Limit(Exception):
    pass


class _Frame:
    """At most payload+CR bytes retained; an oversized suffix is never reparsed."""
    def __init__(self, channel: str, output: _Output):
        self.channel, self.output = channel, output
        self.buffer = bytearray()
        self.discard = False

    def feed(self, chunk: bytes) -> None:
        # Only LF delimits lines; standalone CR remains untrusted payload.
        start = 0
        while start < len(chunk):
            end = chunk.find(b"\n", start)
            complete = end >= 0
            stop = end + 1 if complete else len(chunk)
            piece = chunk[start:stop]
            bound = MAX_LINE_BYTES + (2 if complete else 1)
            if not self.discard:
                if len(self.buffer) + len(piece) > bound:
                    self.discard = True
                    self.buffer.clear()
                else:
                    self.buffer.extend(piece)
            if complete:
                if self.discard:
                    self.output.diagnostic(dict(SUPPRESSED))
                else:
                    self.output.line(self.channel, bytes(self.buffer))
                self.buffer.clear()
                self.discard = False
            start = stop

    def finish(self) -> None:
        if self.discard:
            self.output.diagnostic(dict(SUPPRESSED))
        elif self.buffer:
            self.output.line(self.channel, bytes(self.buffer))
        self.buffer.clear()
        self.discard = False


def _remove_owned_root(root: Path, identity: os.stat_result) -> bool:
    try:
        current = root.lstat()
        if (not stat.S_ISDIR(current.st_mode) or current.st_ino != identity.st_ino
                or current.st_dev != identity.st_dev or current.st_uid != os.getuid()
                or not shutil.rmtree.avoids_symlink_attacks):
            return False
        shutil.rmtree(root)
    except FileNotFoundError:
        pass
    except OSError:
        return False
    return not root.exists() and not root.is_symlink()


def supervise(command: list[str], *, environment: dict[str, str], parent: Path,
              timeout: float, max_input: int = MAX_INPUT_BYTES,
              max_records: int = MAX_RECORDS) -> dict:
    """Internal supervisor for trusted synthetic/preflight callers, not consent.

    The caller owns command selection and any future fresh live authorization.
    This helper does not read settings, discover or load credentials, or retry.
    """
    result = {"reasonCode": "LAUNCH_FAILED", "exitCode": None,
              "launcherCleanup": "not-created", "diagnostics": [], "aggregateReported": None}
    if (os.name != "posix" or not command or not math.isfinite(timeout)
            or not 0 < timeout <= 1800 or type(max_input) is not int
            or not 1 <= max_input <= MAX_INPUT_BYTES or type(max_records) is not int
            or not 1 <= max_records <= MAX_RECORDS):
        result["reasonCode"] = "LAUNCH_ARGUMENTS_REJECTED"
        return result
    if not parent.is_absolute() or parent.is_symlink() or parent.resolve() != parent or not parent.is_dir():
        result["reasonCode"] = "LAUNCH_ARGUMENTS_REJECTED"
        return result
    root: Path | None = None
    process: subprocess.Popen | None = None
    output = _Output(max_records)
    previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, _SUPERVISOR_SIGNALS)
    try:
        root = Path(tempfile.mkdtemp(prefix="p004b-launch-", dir=parent))
        identity = root.lstat()
        child_env = {**environment, "TMPDIR": str(root), "PYTHONDONTWRITEBYTECODE": "1"}
        deadline = time.monotonic() + timeout
        process = subprocess.Popen(command, env=child_env, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True,
            close_fds=True, preexec_fn=lambda: _prepare_supervised_child(previous_mask))
        total = 0
        with selectors.DefaultSelector() as selector:
            for channel, stream in (("stdout", process.stdout), ("stderr", process.stderr)):
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ, _Frame(channel, output))
            while selector.get_map() or process.poll() is None:
                observed = signal.sigtimedwait(_SUPERVISOR_SIGNALS, 0)
                if observed is not None and observed.si_signo != signal.SIGALRM:
                    raise _Limit("INTERRUPTED")
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise _Limit("TIMEOUT")
                for key, _events in selector.select(min(.05, remaining)):
                    try:
                        chunk = os.read(key.fd, min(4096, max_input - total + 1))
                    except BlockingIOError:
                        continue
                    if not chunk:
                        key.data.finish()
                        selector.unregister(key.fileobj)
                        continue
                    total += len(chunk)
                    if total > max_input:
                        raise _Limit("OUTPUT_LIMIT")
                    key.data.feed(chunk)
            status = process.wait()
            result["exitCode"] = status if 0 <= status <= 255 else min(255, 128 + abs(status))
            if status != 0:
                result["reasonCode"] = "CHILD_FAILED"
            elif output.aggregate_rejected:
                result["reasonCode"] = "AGGREGATE_REJECTED"
            elif output.aggregate is None:
                result["reasonCode"] = "AGGREGATE_MISSING"
            else:
                result["reasonCode"] = "STREAM_COMPLETE"
                result["aggregateReported"] = output.aggregate
    except _Limit as error:
        result["reasonCode"] = str(error)  # Only the closed codes raised above.
    except (OSError, ValueError, subprocess.SubprocessError):
        result["reasonCode"] = "LAUNCH_FAILED"
    finally:
        if process is not None:
            _terminate_process_group(process)
            for stream in (process.stdout, process.stderr):
                if stream is not None:
                    stream.close()
        result["diagnostics"] = output.records
        if root is not None:
            result["launcherCleanup"] = "verified" if _remove_owned_root(root, identity) else "failed"
            if result["launcherCleanup"] != "verified":
                result["reasonCode"] = "LAUNCHER_CLEANUP_FAILED"
                result["aggregateReported"] = None
        while signal.sigpending().intersection(_SUPERVISOR_SIGNALS):
            signal.sigwait(signal.sigpending().intersection(_SUPERVISOR_SIGNALS))
        signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
    return result


def main(argv: list[str]) -> int:
    if argv == ["--preflight"]:
        root = Path(__file__).resolve().parents[1]
        result = supervise(["/bin/bash", str(root / "tests/live-browser-operations-smoke.sh"), "--preflight"],
            environment=preflight_environment(dict(os.environ)), parent=Path("/tmp"), timeout=120)
        status = 0 if result["reasonCode"] == "STREAM_COMPLETE" else 2
    else:
        result = {"reasonCode": "LIVE_AUTHORIZATION_REQUIRED" if "--run-live" in argv
                  else "LAUNCH_ARGUMENTS_REJECTED"}
        status = 2
    try:
        print(json.dumps(result, separators=(",", ":"), sort_keys=True))
    except (OSError, ValueError):
        return 2
    return status


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
