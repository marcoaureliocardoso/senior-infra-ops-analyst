#!/usr/bin/env python3
"""Drive a bounded Claude Code TUI using conditioned carriage-return input."""
from __future__ import annotations

import argparse
import json
import os
import re
import select
import subprocess
import sys
import time
from pathlib import Path


MAX_CAPTURE_BYTES = 8 * 1024 * 1024
TASK_A = b"P004A_TASK_A"
TASK_B = b"P004A_TASK_B"
AUTO_TASK = b"P004A_AUTO"


def _stop(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=2)


def drive(
    command: list[str],
    capture_path: Path,
    timeout_seconds: int,
    events_path: Path | None = None,
    dialogue: str = "manual",
    filler_path: Path | None = None,
    compact_events_path: Path | None = None,
) -> int:
    """Run the fixed continuity dialogue and retain only the temporary PTY capture."""
    if (
        os.name != "posix" or not command or not 1 <= timeout_seconds <= 600
        or dialogue not in {"manual", "automatic", "context", "resume", "clear", "skill", "mock-window"}
        or (
            dialogue == "automatic"
            and (filler_path is None or compact_events_path is None)
        )
    ):
        return 2
    filler = ""
    if dialogue == "automatic" or (dialogue == "mock-window" and filler_path is not None):
        try:
            if filler_path is None or not 1 <= filler_path.stat().st_size <= 1_000_000:
                return 2
            filler = filler_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            return 2

    def automatic_compaction_observed() -> bool:
        if compact_events_path is None:
            return False
        try:
            if not compact_events_path.is_file() or compact_events_path.stat().st_size > 64 * 1024:
                return False
            phases = []
            for line in compact_events_path.read_text(encoding="utf-8").splitlines():
                event = json.loads(line)
                if isinstance(event, dict) and event.get("kind") == "compact" and event.get("trigger") == "auto":
                    phases.append(event.get("phase"))
            if phases[-2:] == ["PreCompact", "PostCompact"]:
                return True
        except (OSError, UnicodeError, json.JSONDecodeError):
            return False
        return False
    import fcntl
    import pty
    import struct
    import termios

    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 40, 120, 0, 0))
    capture_path.parent.mkdir(parents=True, exist_ok=True)
    if events_path is not None:
        events_path.parent.mkdir(parents=True, exist_ok=True)
        events_path.write_text("", encoding="utf-8")

    def record(stage: str, outcome: str, percent: int | None = None,
               output_bytes: int | None = None) -> None:
        if events_path is None:
            return
        with events_path.open("a", encoding="utf-8") as stream:
            event = {
                "kind": "pty-driver",
                "stage": stage,
                "outcome": outcome,
            }
            if percent is not None and 0 <= percent <= 100:
                event["percent"] = percent
            if output_bytes is not None and 0 <= output_bytes <= MAX_CAPTURE_BYTES:
                event["outputBytes"] = output_bytes
            stream.write(json.dumps(event, sort_keys=True) + "\n")

    process = subprocess.Popen(
        command,
        stdin=slave,
        stdout=slave,
        stderr=slave,
        close_fds=True,
        start_new_session=True,
    )
    os.close(slave)
    deadline = time.monotonic() + timeout_seconds
    retained = bytearray()
    current_stage = "initial_screen"

    def pump(wait: float = 0.2) -> bool:
        if len(retained) > MAX_CAPTURE_BYTES:
            raise RuntimeError("PTY capture exceeds limit")
        readable, _, _ = select.select([master], [], [], wait)
        if not readable:
            return False
        try:
            chunk = os.read(master, 65536)
        except OSError:
            return False
        if not chunk:
            return False
        retained.extend(chunk)
        capture.write(chunk)
        capture.flush()
        return True

    def wait_for(predicate, label: str) -> None:
        while time.monotonic() < deadline:
            pump()
            if predicate(bytes(retained)):
                return
            if process.poll() is not None:
                raise RuntimeError(f"PTY process exited before {label}")
        raise TimeoutError(f"PTY timed out before {label}")

    def settle(quiet_seconds: float = 0.4) -> None:
        quiet_deadline = time.monotonic() + quiet_seconds
        while time.monotonic() < deadline:
            if pump(min(0.1, max(0.0, quiet_deadline - time.monotonic()))):
                quiet_deadline = time.monotonic() + quiet_seconds
            elif time.monotonic() >= quiet_deadline:
                return
        raise TimeoutError("PTY timed out while settling the screen")

    def send(line: str) -> None:
        if line:
            os.write(master, line.encode("utf-8"))
            time.sleep(0.1)
        os.write(master, b"\r")

    def folded_letters(data: bytes) -> bytes:
        without_csi = re.sub(rb"\x1b\[[0-?]*[ -/]*[@-~]", b"", data)
        return bytes(value for value in without_csi.lower() if 97 <= value <= 122)

    def prompt_ready(data: bytes) -> bool:
        return (
            b"ctx" in folded_letters(data)
            or "❯".encode("utf-8") in data
            or (dialogue == "resume" and TASK_A in data and TASK_B in data)
        )

    def advance_startup(predicate, label: str) -> None:
        for _ in range(4):
            send("")
            attempt_deadline = min(deadline, time.monotonic() + 1.5)
            while time.monotonic() < attempt_deadline:
                pump(0.1)
                if predicate(bytes(retained)):
                    settle()
                    return
        raise TimeoutError(f"PTY timed out before {label}")

    def finish() -> int:
        nonlocal current_stage
        current_stage = "exit"
        settle(0.8)
        send("/exit")
        try:
            process.wait(timeout=min(8.0, max(0.2, deadline - time.monotonic())))
        except subprocess.TimeoutExpired:
            _stop(process)
            record(current_stage, "forced")
            return 0
        if process.returncode == 0:
            record(current_stage, "passed")
            return 0
        record(current_stage, "failed")
        return 2

    try:
        with capture_path.open("wb", buffering=0) as capture:
            wait_for(lambda data: len(data) > 0, "initial screen")
            settle()
            record("initial_screen", "passed")
            startup_offset = 0
            theme_prompt = b"choosethetextstylethatlooksbestwithyourterminal"
            trust_prompt = b"yesitrustthisfolder"
            screen = folded_letters(bytes(retained))
            if theme_prompt in screen:
                current_stage = "theme_selection"
                previous_length = len(retained)
                advance_startup(
                    lambda data, size=previous_length: (
                        trust_prompt in folded_letters(data[size:])
                        or prompt_ready(data[size:])
                    ),
                    "theme screen transition",
                )
                record(current_stage, "passed")
                startup_offset = previous_length

            screen = folded_letters(bytes(retained[startup_offset:]))
            if trust_prompt in screen:
                current_stage = "trust_selection"
                previous_length = len(retained)
                advance_startup(
                    lambda data, size=previous_length: prompt_ready(data[size:]),
                    "trust screen transition",
                )
                record(current_stage, "passed")
                startup_offset = previous_length

            current_stage = "prompt_ready"
            wait_for(
                lambda data: prompt_ready(data[startup_offset:]),
                "interactive prompt readiness",
            )
            settle(1.0)
            record(current_stage, "passed")

            if dialogue == "context":
                current_stage = "context_inspected"
                context_offset = len(retained)
                send("/context")
                wait_for(
                    lambda data: b"%" in data[context_offset:],
                    "native context inspection",
                )
                percentages = [
                    int(value) for value in re.findall(rb"(?<!\d)(\d{1,3})%", bytes(retained[context_offset:]))
                    if 0 <= int(value) <= 100
                ]
                if not percentages:
                    raise RuntimeError("native context percentage unavailable")
                record(current_stage, "passed", percentages[-1])
                return finish()

            if dialogue == "mock-window":
                current_stage = "mock_response"
                response_offset = len(retained)
                send("Reply with the three segments P004A, MOCK, and OK joined by underscores. " + filler)
                wait_for(lambda data: b"P004A_MOCK_OK" in data[response_offset:], "mock model response")
                record(current_stage, "passed")
                current_stage = "mock_second_response"
                second_offset = len(retained)
                send("Reply again with the three segments P004A, MOCK, and OK joined by underscores.")
                wait_for(lambda data: b"P004A_MOCK_OK" in data[second_offset:], "second mock model response")
                record(current_stage, "passed")
                current_stage = "context_inspected"
                context_offset = len(retained)
                send("/context")
                wait_for(lambda data: b"%" in data[context_offset:], "mock context inspection")
                percentages = [int(value) for value in re.findall(
                    rb"(?<!\d)(\d{1,3})%", bytes(retained[context_offset:])
                ) if 0 <= int(value) <= 100]
                if not percentages:
                    raise RuntimeError("mock context percentage unavailable")
                record(current_stage, "passed", percentages[-1])
                return finish()

            if dialogue == "clear":
                current_stage = "clear_observed"
                clear_offset = len(retained)
                send("/clear")
                wait_for(
                    lambda data: prompt_ready(data[clear_offset:]),
                    "isolated clear completion",
                )
                record(current_stage, "passed")
                current_stage = "context_inspected"
                context_offset = len(retained)
                send("/context")
                wait_for(lambda data: b"%" in data[context_offset:], "post-clear context inspection")
                record(current_stage, "passed")
                return finish()

            if dialogue == "skill":
                for ordinal, marker in (("one", b"P004A_SKILL_ONE_OK"), ("two", b"P004A_SKILL_TWO_OK")):
                    current_stage = f"skill_{ordinal}_invoked"
                    skill_offset = len(retained)
                    suffix = (
                        "Do not explain. Reply with exactly the four segments P004A, SKILL, "
                        "ONE, and OK joined by underscores, and nothing else."
                        if ordinal == "one" else
                        "Produce exactly 128 short numbered lines. The mandatory final line "
                        "is the four segments P004A, SKILL, TWO, and OK joined by underscores. "
                        "Do not omit or alter that final line."
                    )
                    send(f"/context-continuity {suffix}")
                    wait_for(lambda data, start=skill_offset, expected=marker: expected in data[start:],
                             f"context-continuity skill invocation {ordinal}")
                    settle(3.0)
                    output_bytes = len(retained) - skill_offset
                    if ordinal == "two" and output_bytes < 1024:
                        raise RuntimeError("bounded large output was not observed")
                    record(current_stage, "passed", output_bytes=output_bytes)
                    current_stage = f"skill_{ordinal}_context"
                    context_offset = len(retained)
                    send("/context")
                    wait_for(lambda data, start=context_offset: b"%" in data[start:],
                             f"post-skill context inspection {ordinal}")
                    percentages = [
                        int(value) for value in re.findall(
                            rb"(?<!\d)(\d{1,3})%", bytes(retained[context_offset:])
                        ) if 0 <= int(value) <= 100
                    ]
                    if not percentages:
                        raise RuntimeError("post-skill context percentage unavailable")
                    record(current_stage, "passed", percentages[-1])
                return finish()

            if dialogue == "resume":
                current_stage = "resume_tasks"
                resume_offset = len(retained)
                send(
                    "Read the native task list and report both identifiers. End with the three "
                    "segments P004A, RESUME, and OK joined by underscores."
                )
                wait_for(
                    lambda data: (
                        TASK_A in data[resume_offset:]
                        and TASK_B in data[resume_offset:]
                        and b"P004A_RESUME_OK" in data[resume_offset:]
                    ),
                    "resumed native task list",
                )
                record(current_stage, "passed")
                current_stage = "rewind_selection"
                rewind_offset = len(retained)
                send("/rewind")
                wait_for(
                    lambda data: b"esctocancel" in folded_letters(data[rewind_offset:]),
                    "rewind selection",
                )
                record(current_stage, "passed")
                current_stage = "rewind_restore_mode"
                restore_offset = len(retained)
                send("")
                settle(3.0)
                restore_mode_present = b"restore" in folded_letters(retained[restore_offset:])
                record(current_stage, "passed" if restore_mode_present else "not-present")
                if restore_mode_present:
                    send("")
                    settle(3.0)
                current_stage = "rewind_observed"
                record(current_stage, "passed")
                current_stage = "post_rewind_tasks"
                post_rewind_offset = len(retained)
                send(
                    "Read the native task list and report both identifiers. End with the four "
                    "segments P004A, AFTER, REWIND, and OK joined by underscores."
                )
                wait_for(
                    lambda data: (
                        TASK_A in data[post_rewind_offset:]
                        and TASK_B in data[post_rewind_offset:]
                        and b"P004A_AFTER_REWIND_OK" in data[post_rewind_offset:]
                    ),
                    "post-rewind native task list",
                )
                record(current_stage, "passed")
                current_stage = "post_rewind_context"
                context_offset = len(retained)
                send("/context")
                wait_for(
                    lambda data: b"%" in data[context_offset:],
                    "post-rewind context inspection",
                )
                percentages = [
                    int(value) for value in re.findall(
                        rb"(?<!\d)(\d{1,3})%", bytes(retained[context_offset:])
                    ) if 0 <= int(value) <= 100
                ]
                if not percentages:
                    raise RuntimeError("post-rewind context percentage unavailable")
                record(current_stage, "passed", percentages[-1])
                return finish()

            if dialogue == "automatic":
                automatic_offset = len(retained)
                current_stage = "automatic_task_created"
                send(
                    "Create native task P004A_AUTO and retain it. Then reply with the three "
                    "segments P004A, READY, and DONE joined by underscores, and nothing else. "
                    + filler
                )
                wait_for(
                    lambda data: (
                        AUTO_TASK in data[automatic_offset:]
                        and b"P004A_READY_DONE" in data[automatic_offset:]
                    ),
                    "automatic task creation",
                )
                settle(1.0)
                record(current_stage, "passed")
                current_stage = "automatic_context_inspected"
                context_offset = len(retained)
                send("/context")
                wait_for(
                    lambda data: b"%" in data[context_offset:],
                    "automatic probe context inspection",
                )
                percentages = [
                    int(value) for value in re.findall(
                        rb"(?<!\d)(\d{1,3})%", bytes(retained[context_offset:])
                    ) if 0 <= int(value) <= 100
                ]
                if not percentages:
                    raise RuntimeError("automatic probe context percentage unavailable")
                record(current_stage, "passed", percentages[-1])
                current_stage = "automatic_compaction"
                boundary_offset = len(retained)
                send(
                    "Continue without changing the native task. Reply with the three segments "
                    "P004A, SECOND, and TURN joined by underscores, and nothing else."
                )
                wait_for(
                    lambda data: b"P004A_SECOND_TURN" in data[boundary_offset:],
                    "automatic compaction boundary turn",
                )
                settle(1.0)
                final_offset = len(retained)
                send(
                    "Read the native task list and report P004A_AUTO. End with the four segments "
                    "P004A, AUTO, CHECK, and OK joined by underscores."
                )
                wait_for(
                    lambda data: (
                        AUTO_TASK in data[final_offset:]
                        and b"P004A_AUTO_CHECK_OK" in data[final_offset:]
                        and automatic_compaction_observed()
                    ),
                    "automatic compaction and post-compaction task list",
                )
                record(current_stage, "passed")
                return finish()

            current_stage = "tasks_created"
            send(
                "Create native tasks named P004A_TASK_A and P004A_TASK_B. Complete only "
                "P004A_TASK_A. Then reply with the three segments P004A, TASKS, and CREATED "
                "joined by underscores, and nothing else."
            )
            wait_for(
                lambda data: b"P004A_TASKS_CREATED" in data,
                "native task creation",
            )
            record(current_stage, "passed")

            current_stage = "context_inspected"
            context_offset = len(retained)
            send("/context")
            wait_for(
                lambda data: b"%" in data[context_offset:],
                "context inspection",
            )
            record(current_stage, "passed")

            current_stage = "manual_compaction"
            compact_offset = len(retained)
            send("/compact Preserve task identifiers and immediate next action")
            wait_for(
                lambda data: data[compact_offset:].lower().count(b"compact") >= 2,
                "manual compaction",
            )
            record(current_stage, "passed")

            current_stage = "post_compaction_tasks"
            final_offset = len(retained)
            send(
                "Read the native task list and report both task identifiers. End with the four "
                "segments P004A, POST, COMPACT, and OK joined by underscores."
            )
            wait_for(
                lambda data: (
                    TASK_A in data[final_offset:]
                    and TASK_B in data[final_offset:]
                    and b"P004A_POST_COMPACT_OK" in data[final_offset:]
                ),
                "post-compaction task list",
            )
            record(current_stage, "passed")

            current_stage = "manual_unfocused_compaction"
            unfocused_offset = len(retained)
            send("/compact")
            wait_for(
                lambda data: data[unfocused_offset:].lower().count(b"compact") >= 2,
                "unfocused manual compaction",
            )
            record(current_stage, "passed")
            return finish()
    except (OSError, RuntimeError, TimeoutError):
        record(current_stage, "failed")
        _stop(process)
        return 2
    finally:
        try:
            os.close(master)
        except OSError:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", required=True, type=Path)
    parser.add_argument("--events", type=Path)
    parser.add_argument(
        "--dialogue",
        choices=("manual", "automatic", "context", "resume", "clear", "skill", "mock-window"),
        default="manual",
    )
    parser.add_argument("--filler", type=Path)
    parser.add_argument("--compact-events", type=Path)
    parser.add_argument("--timeout", required=True, type=int)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    result = drive(
        command, args.capture, args.timeout, args.events,
        dialogue=args.dialogue, filler_path=args.filler,
        compact_events_path=args.compact_events,
    )
    if result != 0:
        print("Claude PTY dialogue did not complete.", file=sys.stderr)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
