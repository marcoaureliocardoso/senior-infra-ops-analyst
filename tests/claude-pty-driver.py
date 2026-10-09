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


def _without_csi(data: bytes) -> bytes:
    return re.sub(rb"\x1b\[[0-?]*[ -/]*[@-~]", b"", data)


def _folded_letters(data: bytes) -> bytes:
    return bytes(value for value in _without_csi(data).lower() if 97 <= value <= 122)


def terminal_screen_text(
    data: bytes, rows: int = 40, columns: int = 120,
    observed_rows: list[str] | None = None,
) -> str:
    """Render the small ANSI subset emitted by the bounded Claude TUI probe."""
    screen = [[" "] * columns for _ in range(rows)]
    row = column = 0
    saved = (0, 0)
    text = data.decode("utf-8", errors="ignore")
    index = 0

    def parameters(raw: str) -> list[int]:
        raw = raw.lstrip("?<=>")
        values = raw.split(";") if raw else []
        return [int(value) if value.isdigit() else 0 for value in values]

    def amount(values: list[int], default: int = 1) -> int:
        return values[0] if values and values[0] > 0 else default

    def scroll_up(count: int = 1) -> None:
        nonlocal row
        for _ in range(min(count, rows)):
            screen.pop(0)
            screen.append([" "] * columns)
        row = max(0, row - count)

    def observe_current_row() -> None:
        if observed_rows is None or len(observed_rows) >= 128:
            return
        line = "".join(screen[row]).rstrip()
        if (any(label in line for label in (
                "Context Usage", "Free space", "Compact buffer",
                "Autocompact buffer",
            )) and line not in observed_rows):
            observed_rows.append(line)

    while index < len(text):
        character = text[index]
        if character == "\x1b":
            if index + 1 < len(text) and text[index + 1] == "[":
                end = index + 2
                while end < len(text) and not "@" <= text[end] <= "~":
                    end += 1
                if end >= len(text):
                    break
                values = parameters(text[index + 2:end])
                command = text[end]
                if command in {"H", "f"}:
                    row = max(0, min(rows - 1, (values[0] if values else 1) - 1))
                    column = max(0, min(
                        columns - 1,
                        (values[1] if len(values) > 1 and values[1] else 1) - 1,
                    ))
                elif command == "A":
                    row = max(0, row - amount(values))
                elif command == "B":
                    row = min(rows - 1, row + amount(values))
                elif command == "C":
                    column = min(columns - 1, column + amount(values))
                elif command == "D":
                    column = max(0, column - amount(values))
                elif command == "E":
                    row = min(rows - 1, row + amount(values)); column = 0
                elif command == "F":
                    row = max(0, row - amount(values)); column = 0
                elif command == "G":
                    column = max(0, min(columns - 1, amount(values) - 1))
                elif command == "d":
                    row = max(0, min(rows - 1, amount(values) - 1))
                elif command == "J":
                    mode = values[0] if values else 0
                    if mode == 0:
                        # ED 0/default clears from the cursor down, not headings above it.
                        screen[row][column:] = [" "] * (columns - column)
                        for below in range(row + 1, rows):
                            screen[below] = [" "] * columns
                    elif mode in {2, 3}:
                        screen = [[" "] * columns for _ in range(rows)]
                        row = column = 0
                elif command == "K":
                    mode = values[0] if values else 0
                    if mode == 0:
                        screen[row][column:] = [" "] * (columns - column)
                    elif mode == 1:
                        screen[row][:column + 1] = [" "] * (column + 1)
                    elif mode == 2:
                        screen[row] = [" "] * columns
                elif command == "s":
                    saved = (row, column)
                elif command == "u":
                    row, column = saved
                elif command == "S":
                    scroll_up(amount(values))
                elif command == "T":
                    count = min(amount(values), rows)
                    for _ in range(count):
                        screen.pop()
                        screen.insert(0, [" "] * columns)
                    row = min(rows - 1, row + count)
                index = end + 1
                continue
            if index + 1 < len(text) and text[index + 1] == "]":
                end = index + 2
                while end < len(text):
                    if text[end] == "\a":
                        end += 1
                        break
                    if text[end:end + 2] == "\x1b\\":
                        end += 2
                        break
                    end += 1
                index = end
                continue
            index += 2
            continue
        if character == "\r":
            column = 0
        elif character == "\n":
            row += 1
            if row >= rows:
                scroll_up()
                row = rows - 1
        elif character == "\b":
            column = max(0, column - 1)
        elif character == "\t":
            column = min(columns - 1, ((column // 8) + 1) * 8)
        elif character >= " ":
            screen[row][column] = character
            observe_current_row()
            column += 1
            if column >= columns:
                column = 0
                row += 1
                if row >= rows:
                    scroll_up()
                    row = rows - 1
        index += 1
    return "\n".join("".join(line).rstrip() for line in screen)


def startup_authentication_stage(data: bytes) -> str | None:
    """Recognize auth UI on the visible startup screen, never approve it."""
    screen = terminal_screen_text(data)
    folded = _folded_letters(screen.encode("utf-8"))
    if b"doyouwanttousethisapikey" in folded:
        return "api_key_approval_required"
    if any(label in folded for label in (
        b"selectloginmethod", b"howwouldyouliketologin",
        b"claudecoderequiresauthentication",
    )):
        return "login_required"
    return None


def _context_percent_from_text(
    text: str, allow_rendered_row_order: bool = False,
) -> int | None:
    from terminal_input_policy import parse_context_percent
    return parse_context_percent(text, allow_rendered_row_order)


def context_usage_percent(data: bytes) -> int | None:
    """Return used percent only from the exact native /context labels."""
    observed_rows: list[str] = []
    final_screen = terminal_screen_text(data, observed_rows=observed_rows)
    percentage = _context_percent_from_text(
        "\n".join(observed_rows), allow_rendered_row_order=True,
    )
    if percentage is not None:
        return percentage
    percentage = _context_percent_from_text(
        final_screen, allow_rendered_row_order=True,
    )
    if percentage is not None:
        return percentage
    return None


def context_structure_stage(data: bytes) -> str:
    """Reduce native /context output to one allowlisted structural stage."""
    folded = _folded_letters(data)
    if b"contextusage" not in folded:
        return "context_header_missing"
    if b"freespace" not in folded:
        return "context_free_space_missing"
    if context_usage_percent(data) is None:
        text = _without_csi(data).decode("utf-8", errors="ignore")
        near_free = re.search(
            r"Free space[^\r\n%]{0,160}?\d{1,3}(?:\.\d+)?%",
            text,
            flags=re.IGNORECASE,
        )
        if near_free is None:
            separated_free = re.search(
                r"Free space[\s\S]{0,2048}?\d{1,3}(?:\.\d+)?%",
                text,
                flags=re.IGNORECASE,
            )
            if separated_free:
                return "context_free_value_separated"
            if re.search(r"(?<!\d)\d{1,3}(?:\.\d+)?%", text):
                return "context_raw_percent_present"
            return "context_free_value_missing"
        return "context_values_invalid"
    if "❯".encode("utf-8") not in data:
        return "context_prompt_missing"
    return "context_inspected"


def write_all(file_descriptor: int, payload: bytes, writer=os.write) -> None:
    """Write every byte to a PTY even when the operating system accepts a prefix."""
    remaining = memoryview(payload)
    while remaining:
        written = writer(file_descriptor, remaining)
        if not isinstance(written, int) or written <= 0 or written > len(remaining):
            raise OSError("PTY write made no bounded progress")
        remaining = remaining[written:]


def drive_request_valid(
    command: list[str], timeout_seconds: int, dialogue: str,
    filler_path: Path | None, compact_events_path: Path | None,
) -> bool:
    if not command or not 1 <= timeout_seconds <= 600:
        return False
    if dialogue not in {"manual", "automatic", "context", "resume", "clear", "skill", "mock-window"}:
        return False
    if dialogue == "manual" and compact_events_path is None:
        return False
    if dialogue == "automatic" and (filler_path is None or compact_events_path is None):
        return False
    return True


def compaction_pairs_observed(
    compact_events_path: Path | None, trigger: str, expected_pairs: int,
) -> bool:
    if compact_events_path is None or expected_pairs < 1:
        return False
    try:
        if not compact_events_path.is_file() or compact_events_path.stat().st_size > 64 * 1024:
            return False
        phases = []
        for line in compact_events_path.read_text(encoding="utf-8").splitlines():
            event = json.loads(line)
            if isinstance(event, dict) and event.get("kind") == "compact" and event.get("trigger") == trigger:
                phases.append(event.get("phase"))
        return phases == ["PreCompact", "PostCompact"] * expected_pairs
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False


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
    startup_approval=None,
    *, terminal_state=None, terminal_diagnostics=None,
) -> int:
    """Run the fixed continuity dialogue and retain only the temporary PTY capture."""
    if terminal_state is not None:
        if os.name != 'posix' or dialogue != 'context' or not drive_request_valid(
                command,timeout_seconds,dialogue,filler_path,compact_events_path):
            try: terminal_state.close()
            except RuntimeError: pass
            return 2
        from headless_context_driver import drive_context
        return drive_context(command,capture_path,timeout_seconds,events_path,startup_approval,
                             terminal_state,writer=write_all,diagnostics=terminal_diagnostics)
    if (startup_approval is not None and dialogue != "context") or os.name != "posix" or not drive_request_valid(
        command, timeout_seconds, dialogue, filler_path, compact_events_path,
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
    context_probe_offset: int | None = None
    startup_open = True
    startup_prompt_offset = 0

    def pump(wait: float = 0.2) -> bool:
        nonlocal current_stage
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
        if not startup_open:
            authentication = startup_authentication_stage(bytes(retained))
            if authentication is not None:
                current_stage = authentication
                raise RuntimeError("authentication appeared after startup")
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
            write_all(master, line.encode("utf-8"))
            time.sleep(0.1)
        write_all(master, b"\r")

    def folded_letters(data: bytes) -> bytes:
        return _folded_letters(data)

    def require_startup_auth_clear(data: bytes) -> None:
        nonlocal current_stage, startup_prompt_offset
        stage = startup_authentication_stage(data)
        if stage is not None:
            previous_stage = current_stage
            current_stage = stage
            if stage == "api_key_approval_required" and startup_open and startup_approval is not None:
                # Recognition may occur before the selector is fully drawn.
                settle(0.6)
                screen = terminal_screen_text(bytes(retained))
                selection = startup_approval.selection(screen)
                if selection is not None:
                    startup_prompt_offset = len(retained)
                    if selection:
                        write_all(master, selection)
                        time.sleep(0.1)
                    send("")
                    wait_for(lambda value: startup_authentication_stage(value) is None,
                             "approved API-key selector transition")
                    settle()
                    if startup_authentication_stage(bytes(retained)) is not None:
                        raise RuntimeError("startup authentication reappeared")
                    record("api_key_approval", "passed")
                    current_stage = previous_stage
                    return
            raise RuntimeError("startup authentication requires an independent decision")

    def prompt_ready(data: bytes) -> bool:
        # Keep the caller's post-transition boundary even while an unused
        # approval object exists. Auth handling can append a new prompt.
        observation_offset = len(retained) - len(data)
        require_startup_auth_clear(data)
        if startup_approval is not None:
            data = bytes(retained[max(observation_offset, startup_prompt_offset):])
        if dialogue == "context":
            screen = terminal_screen_text(data)
            folded = folded_letters(screen.encode("utf-8"))
            current_folded = folded_letters(terminal_screen_text(bytes(retained)).encode("utf-8"))
            if (b"choosethetextstylethatlooksbestwithyourterminal" in folded
                    or b"yesitrustthisfolder" in folded
                    or b"choosethetextstylethatlooksbestwithyourterminal" in current_folded
                    or b"yesitrustthisfolder" in current_folded
                    or re.search(r"(?m)^\s*❯\s*\d+[.)]", screen)):
                return False
            # Empty input, the controlled readiness fixture, or the native
            # quoted input suggestion. Arbitrary unnumbered menu options
            # (including partial redraws with no heading) are not prompts.
            return bool(re.search(r'(?m)^\s*❯[ \t]*(?:$|ready[ \t]*$|Try[ \t]+"[^"\r\n]+"[ \t]*$)', screen))
        return (
            b"ctx" in folded_letters(data)
            or "❯".encode("utf-8") in data
            or (dialogue == "resume" and TASK_A in data and TASK_B in data)
        )

    def advance_startup(
        predicate, label: str, selection: bytes = b""
    ) -> None:
        for attempt in range(4):
            require_startup_auth_clear(bytes(retained))
            if selection and attempt == 0:
                write_all(master, selection)
                time.sleep(0.1)
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
            return 2 if dialogue == "context" else 0
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
            require_startup_auth_clear(bytes(retained))
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
                    b"\x1b[A",
                )
                record(current_stage, "passed")
                startup_offset = previous_length

            current_stage = "prompt_ready"
            wait_for(
                lambda data: prompt_ready(data[startup_offset:]),
                "interactive prompt readiness",
            )
            settle(1.0)
            require_startup_auth_clear(bytes(retained))
            if dialogue == "context" and not prompt_ready(bytes(retained[startup_offset:])):
                raise RuntimeError("interactive prompt changed before readiness settled")
            record(current_stage, "passed")
            startup_open = False
            if startup_approval is not None:
                startup_approval.revoke()

            if dialogue == "context":
                current_stage = "context_inspected"
                context_offset = len(retained)
                context_probe_offset = context_offset
                # Aggregate percentages do not require the viewport-sensitive per-item expansion.
                send("/context")
                wait_for(
                    lambda data: context_usage_percent(data[context_offset:]) is not None,
                    "native context inspection",
                )
                context_output = bytes(retained[context_offset:])
                percentage = context_usage_percent(context_output)
                if percentage is None:
                    raise RuntimeError("native context percentage unavailable")
                if "❯".encode("utf-8") not in context_output:
                    prompt_offset = len(retained)
                    write_all(master, b"\x1b")
                    wait_for(
                        lambda data: "❯".encode("utf-8") in data[prompt_offset:],
                        "native context dismissal",
                    )
                record(current_stage, "passed", percentage)
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
                        and compaction_pairs_observed(compact_events_path, "auto", 1)
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
            context_output = bytes(retained[context_offset:])
            percentages = [
                int(value) for value in re.findall(rb"(?<!\d)(\d{1,3})%", context_output)
                if 0 <= int(value) <= 100
            ]
            if not percentages:
                raise RuntimeError("context percentage unavailable")
            record(current_stage, "passed", percentages[-1])

            current_stage = "manual_compaction"
            compact_offset = len(retained)
            send("/compact Preserve task identifiers and immediate next action")
            wait_for(
                lambda data: (
                    data[compact_offset:].lower().count(b"compact") >= 2
                    and compaction_pairs_observed(compact_events_path, "manual", 1)
                ),
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
                lambda data: (
                    data[unfocused_offset:].lower().count(b"compact") >= 2
                    and compaction_pairs_observed(compact_events_path, "manual", 2)
                ),
                "unfocused manual compaction",
            )
            record(current_stage, "passed")
            return finish()
    except (OSError, RuntimeError, TimeoutError):
        if (dialogue == "context" and current_stage == "context_inspected"
                and context_probe_offset is not None):
            current_stage = context_structure_stage(
                bytes(retained[context_probe_offset:])
            )
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
    parser.add_argument("--terminal-engine", choices=("legacy", "headless"), default="legacy")
    parser.add_argument("--terminal-node", type=Path)
    parser.add_argument("--terminal-module-root", type=Path)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if args.terminal_engine == "headless":
        from terminal_cancellation import TerminalCancellation
        cancellation = TerminalCancellation()
        try:
            with cancellation:
                result = _run_selected_args(args, command, cancellation)
            return 2 if cancellation.requested else result
        except RuntimeError:
            print("BLOCKED: test terminal runtime unavailable", file=sys.stderr)
            return 2
    return _run_selected_args(args, command)


def _run_selected_args(args, command, cancellation=None):
    terminal = None
    from terminal_state_adapter import TerminalState, TerminalStateError
    if args.terminal_engine == "headless":
        try:
            if args.dialogue != "context": raise TerminalStateError("TERMINAL_DEPENDENCY_UNAVAILABLE")
            terminal = TerminalState(args.terminal_node, args.terminal_module_root, time.monotonic() + args.timeout,
                                     cancellation=cancellation)
        except TerminalStateError:
            print("BLOCKED: test terminal runtime unavailable", file=sys.stderr)
            return 2
    elif args.terminal_node is not None or args.terminal_module_root is not None:
        print("BLOCKED: test terminal runtime unavailable", file=sys.stderr)
        return 2
    try:
        result = drive(
            command, args.capture, args.timeout, args.events,
            dialogue=args.dialogue, filler_path=args.filler,
            compact_events_path=args.compact_events, terminal_state=terminal,
        )
    finally:
        if terminal is not None:
            try: terminal.close()
            except TerminalStateError:
                result = 2
    if result != 0:
        print("Claude PTY dialogue did not complete.", file=sys.stderr)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
