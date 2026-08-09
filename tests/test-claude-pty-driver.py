#!/usr/bin/env python3
"""Behavior tests for the condition-driven Claude Code PTY controller."""
from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "tests" / "claude-pty-driver.py"


def load_driver():
    if not DRIVER.is_file():
        raise AssertionError("Claude PTY driver is missing")
    spec = importlib.util.spec_from_file_location("claude_pty_driver", DRIVER)
    if spec is None or spec.loader is None:
        raise AssertionError("Claude PTY driver cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ClaudePtyDriverTests(unittest.TestCase):
    def test_driver_exists(self) -> None:
        self.assertTrue(DRIVER.is_file())

    @unittest.skipUnless(os.name == "posix", "PTY behavior requires POSIX")
    def test_conditioned_dialogue_completes_with_carriage_return_keys(self) -> None:
        driver = load_driver()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fake = root / "fake_tui.py"
            capture = root / "capture.pty"
            events = root / "events.jsonl"
            fake.write_text(textwrap.dedent(r'''
                import fcntl, os, select, struct, sys, termios, time, tty
                tty.setraw(sys.stdin.fileno())
                rows, columns, _, _ = struct.unpack(
                    "HHHH",
                    fcntl.ioctl(sys.stdin.fileno(), termios.TIOCGWINSZ, bytes(8)),
                )
                assert rows >= 24 and columns >= 80
                theme = b"Choose the text \x1b[1mstyle\x1b[0m that looks best with your terminal"
                trust = b"Yes, I \x1b[32mtrust\x1b[0m this folder"
                os.write(sys.stdout.fileno(), b"Welcome")
                time.sleep(0.2)
                os.write(sys.stdout.fileno(), b" " + theme)
                def line():
                    value = bytearray()
                    started = None
                    while True:
                        character = os.read(sys.stdin.fileno(), 1)
                        if character == b"\r":
                            if value:
                                assert time.monotonic() - started >= 0.05
                            return value.decode()
                        if started is None:
                            started = time.monotonic()
                        value.extend(character)
                assert line() == ""
                os.write(sys.stdout.fileno(), theme)
                assert line() == ""
                os.write(sys.stdout.fileno(), theme + b" " + trust)
                assert line() == ""
                os.write(sys.stdout.fileno(), trust)
                assert line() == ""
                os.write(sys.stdout.fileno(), theme + b" Welcome back")
                if select.select([sys.stdin.fileno()], [], [], 0.8)[0]:
                    raise SystemExit("unexpected extra startup key")
                os.write(sys.stdout.fileno(), b"ctx --")
                time.sleep(0.8)
                if select.select([sys.stdin.fileno()], [], [], 0)[0]:
                    os.read(sys.stdin.fileno(), 4096)
                os.write(sys.stdout.fileno(), b"ready")
                first = line()
                assert "P004A_TASK_A" in first and "P004A_TASK_B" in first
                assert "P004A_TASKS_CREATED" not in first
                assert "joined by underscores" in first
                os.write(sys.stdout.fileno(), first.encode())
                os.write(sys.stdout.fileno(), b"P004A_TASK_A P004A_TASK_B P004A_TASKS_CREATED")
                assert line() == "/context"
                os.write(sys.stdout.fileno(), b"context usage 42%")
                assert line().startswith("/compact ")
                os.write(sys.stdout.fileno(), b"context compacted after compact")
                final = line()
                assert "task list" in final.lower()
                assert "P004A_POST_COMPACT_OK" not in final
                assert "joined by underscores" in final
                os.write(sys.stdout.fileno(), final.encode())
                os.write(sys.stdout.fileno(), b"P004A_TASK_A P004A_TASK_B P004A_POST_COMPACT_OK")
                assert line() == "/exit"
                time.sleep(30)
            '''), encoding="utf-8")
            result = driver.drive(
                [sys.executable, str(fake)], capture, timeout_seconds=10,
                events_path=events,
            )
            self.assertEqual(result, 0)
            retained = capture.read_text(encoding="utf-8")
            self.assertIn("context compacted", retained)
            event_text = events.read_text(encoding="utf-8")
            self.assertIn('"stage": "post_compaction_tasks"', event_text)
            self.assertIn('"outcome": "passed"', event_text)
            self.assertNotIn("P004A_TASK", event_text)

    @unittest.skipUnless(os.name == "posix", "PTY behavior requires POSIX")
    def test_driver_times_out_without_claiming_success(self) -> None:
        driver = load_driver()
        with tempfile.TemporaryDirectory() as directory:
            capture = Path(directory) / "capture.pty"
            events = Path(directory) / "events.jsonl"
            result = driver.drive(
                [sys.executable, "-c", "import time; time.sleep(30)"],
                capture,
                timeout_seconds=1,
                events_path=events,
            )
            self.assertNotEqual(result, 0)
            self.assertIn('"outcome": "failed"', events.read_text(encoding="utf-8"))

    @unittest.skipUnless(os.name == "posix", "PTY behavior requires POSIX")
    def test_automatic_dialogue_uses_filler_and_observes_compaction(self) -> None:
        driver = load_driver()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fake = root / "fake_auto_tui.py"
            capture = root / "capture.pty"
            events = root / "events.jsonl"
            filler = root / "filler.prompt"
            filler.write_text(" probe" * 100, encoding="utf-8")
            fake.write_text(textwrap.dedent(r'''
                import json, os, select, sys, termios, time, tty
                from pathlib import Path
                tty.setraw(sys.stdin.fileno())
                os.write(sys.stdout.fileno(), b"ctx -- ready")
                def line():
                    value = bytearray(); started = None
                    while True:
                        character = os.read(sys.stdin.fileno(), 1)
                        if character == b"\r":
                            if value: assert time.monotonic() - started >= 0.05
                            return value.decode()
                        if started is None: started = time.monotonic()
                        value.extend(character)
                first = line()
                assert "P004A_AUTO" in first and "probe" in first
                assert "\n" not in first
                assert "P004A_READY_DONE" not in first
                assert "joined by underscores" in first
                os.write(sys.stdout.fileno(), first.encode())
                os.write(sys.stdout.fileno(), b"P004A_AUTO P004A_READY_DONE ctx --")
                time.sleep(0.8)
                if select.select([sys.stdin.fileno()], [], [], 0)[0]:
                    raise SystemExit("post-compaction request arrived before prompt settled")
                os.write(sys.stdout.fileno(), b"ctx -- idle")
                second = line()
                assert "P004A_SECOND_TURN" not in second
                assert "joined by underscores" in second
                os.write(sys.stdout.fileno(), b"P004A_SECOND_TURN ctx --")
                third = line()
                assert "task list" in third.lower()
                assert "P004A_AUTO_CHECK_OK" not in third
                assert "joined by underscores" in third
                Path(sys.argv[1]).write_text(json.dumps({
                    "kind": "compact", "phase": "PreCompact", "trigger": "auto",
                }) + "\n", encoding="utf-8")
                os.write(sys.stdout.fileno(), b"P004A_AUTO P004A_AUTO_CHECK_OK ctx --")
                assert line() == "/exit"
            '''), encoding="utf-8")
            compact_events = root / "compact-events.jsonl"
            result = driver.drive(
                [sys.executable, str(fake), str(compact_events)], capture, timeout_seconds=10,
                events_path=events, dialogue="automatic", filler_path=filler,
                compact_events_path=compact_events,
            )
            self.assertEqual(result, 0)
            event_text = events.read_text(encoding="utf-8")
            self.assertIn('"stage": "automatic_compaction"', event_text)
            self.assertNotIn("P004A_AUTO", event_text)


if __name__ == "__main__":
    unittest.main()
