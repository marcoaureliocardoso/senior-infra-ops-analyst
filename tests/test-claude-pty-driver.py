#!/usr/bin/env python3
"""Behavior tests for the condition-driven Claude Code PTY controller."""
from __future__ import annotations

import importlib.util
import json
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

    def test_structural_compaction_sequence_rejects_orphans_and_duplicates(self) -> None:
        driver = load_driver()
        self.assertTrue(hasattr(driver, "compaction_pairs_observed"))
        with tempfile.TemporaryDirectory() as directory:
            compact_events = Path(directory) / "compact-events.jsonl"

            def write(phases: list[str]) -> None:
                compact_events.write_text("\n".join(json.dumps({
                    "kind": "compact", "phase": phase, "trigger": "manual",
                }) for phase in phases) + "\n", encoding="utf-8")

            write(["PreCompact", "PostCompact"])
            self.assertTrue(driver.compaction_pairs_observed(compact_events, "manual", 1))
            write(["PostCompact", "PreCompact", "PostCompact"])
            self.assertFalse(driver.compaction_pairs_observed(compact_events, "manual", 1))
            write(["PreCompact", "PreCompact", "PostCompact"])
            self.assertFalse(driver.compaction_pairs_observed(compact_events, "manual", 1))
            write(["PreCompact", "PostCompact", "PreCompact", "PostCompact"])
            self.assertTrue(driver.compaction_pairs_observed(compact_events, "manual", 2))
            write(["PreCompact", "PreCompact", "PostCompact", "PreCompact", "PostCompact"])
            self.assertFalse(driver.compaction_pairs_observed(compact_events, "manual", 2))

    def test_manual_dialogue_requires_structural_compaction_events(self) -> None:
        driver = load_driver()
        self.assertTrue(hasattr(driver, "drive_request_valid"))
        compact_events = Path("compact-events.jsonl")
        self.assertFalse(driver.drive_request_valid(
            ["claude"], 600, "manual", None, None,
        ))
        self.assertTrue(driver.drive_request_valid(
            ["claude"], 600, "manual", None, compact_events,
        ))

    @unittest.skipUnless(os.name == "posix", "PTY behavior requires POSIX")
    def test_conditioned_dialogue_waits_for_ordered_manual_compaction_hooks(self) -> None:
        driver = load_driver()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fake = root / "fake_tui.py"
            capture = root / "capture.pty"
            events = root / "events.jsonl"
            compact_events = root / "compact-events.jsonl"
            fake.write_text(textwrap.dedent(r'''
                import fcntl, json, os, select, struct, sys, termios, time, tty
                from pathlib import Path
                tty.setraw(sys.stdin.fileno())
                compact_events = Path(sys.argv[1])
                def compact(phase):
                    with compact_events.open("a", encoding="utf-8") as stream:
                        stream.write(json.dumps({
                            "kind": "compact", "phase": phase, "trigger": "manual",
                        }) + "\n")
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
                compact("PreCompact")
                compact("PostCompact")
                os.write(sys.stdout.fileno(), b"context compacted after compact")
                final = line()
                assert "task list" in final.lower()
                assert "P004A_POST_COMPACT_OK" not in final
                assert "joined by underscores" in final
                os.write(sys.stdout.fileno(), final.encode())
                os.write(sys.stdout.fileno(), b"P004A_TASK_A P004A_TASK_B P004A_POST_COMPACT_OK")
                assert line() == "/compact"
                compact("PreCompact")
                os.write(sys.stdout.fileno(), b"compact compact")
                if select.select([sys.stdin.fileno()], [], [], 1.2)[0]:
                    raise SystemExit("driver exited before PostCompact")
                compact("PostCompact")
                assert line() == "/exit"
            '''), encoding="utf-8")
            result = driver.drive(
                [sys.executable, str(fake), str(compact_events)], capture,
                timeout_seconds=10, events_path=events,
                compact_events_path=compact_events,
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
            root = Path(directory)
            capture = root / "capture.pty"
            events = root / "events.jsonl"
            result = driver.drive(
                [sys.executable, "-c", "import time; time.sleep(30)"],
                capture,
                timeout_seconds=1,
                events_path=events,
                compact_events_path=root / "compact-events.jsonl",
            )
            self.assertNotEqual(result, 0)
            self.assertIn('"outcome": "failed"', events.read_text(encoding="utf-8"))

    @unittest.skipUnless(os.name == "posix", "PTY behavior requires POSIX")
    def test_context_dialogue_uses_native_context_without_model_prompt(self) -> None:
        driver = load_driver()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fake = root / "fake_context_tui.py"
            capture = root / "capture.pty"
            events = root / "events.jsonl"
            fake.write_text(textwrap.dedent(r'''
                import os, sys, tty
                tty.setraw(sys.stdin.fileno())
                os.write(sys.stdout.fileno(), "❯ ready".encode())
                def line():
                    value = bytearray()
                    while True:
                        character = os.read(sys.stdin.fileno(), 1)
                        if character == b"\r": return value.decode()
                        value.extend(character)
                assert line() == "/context"
                os.write(sys.stdout.fileno(), b"native context usage 7%")
                assert line() == "/exit"
            '''), encoding="utf-8")
            result = driver.drive(
                [sys.executable, str(fake)], capture, timeout_seconds=10,
                events_path=events, dialogue="context",
            )
            self.assertEqual(result, 0)
            event_text = events.read_text(encoding="utf-8")
            self.assertIn('"stage": "context_inspected"', event_text)
            self.assertIn('"percent": 7', event_text)

    @unittest.skipUnless(os.name == "posix", "PTY behavior requires POSIX")
    def test_resume_dialogue_exercises_rewind_and_preserves_tasks(self) -> None:
        driver = load_driver()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fake = root / "fake_resume_tui.py"
            capture = root / "capture.pty"
            events = root / "events.jsonl"
            fake.write_text(textwrap.dedent(r'''
                import os, sys, tty
                tty.setraw(sys.stdin.fileno())
                os.write(sys.stdout.fileno(), "❯ ready".encode())
                def line():
                    value = bytearray()
                    while True:
                        character = os.read(sys.stdin.fileno(), 1)
                        if character == b"\r": return value.decode()
                        value.extend(character)
                first = line()
                assert "task list" in first.lower() and "P004A_RESUME_OK" not in first
                os.write(sys.stdout.fileno(), b"P004A_TASK_A P004A_TASK_B P004A_RESUME_OK")
                assert line() == "/rewind"
                os.write(sys.stdout.fileno(), b"rewind selection Esc to cancel")
                assert line() == ""
                os.write(sys.stdout.fileno(), b"Restore code and conversation")
                assert line() == ""
                os.write(sys.stdout.fileno(), b"ctx -- returned")
                final = line()
                assert "task list" in final.lower() and "P004A_AFTER_REWIND_OK" not in final
                os.write(sys.stdout.fileno(), b"P004A_TASK_A P004A_TASK_B P004A_AFTER_REWIND_OK")
                assert line() == "/context"
                os.write(sys.stdout.fileno(), b"native context 9%")
                assert line() == "/exit"
            '''), encoding="utf-8")
            result = driver.drive(
                [sys.executable, str(fake)], capture, timeout_seconds=10,
                events_path=events, dialogue="resume",
            )
            self.assertEqual(result, 0)
            event_text = events.read_text(encoding="utf-8")
            self.assertIn('"stage": "resume_tasks"', event_text)
            self.assertIn('"stage": "rewind_selection"', event_text)
            self.assertIn('"stage": "rewind_restore_mode"', event_text)
            self.assertIn('"stage": "rewind_observed"', event_text)
            self.assertIn('"stage": "post_rewind_tasks"', event_text)
            self.assertIn('"stage": "post_rewind_context"', event_text)
            self.assertIn('"percent": 9', event_text)

    @unittest.skipUnless(os.name == "posix", "PTY behavior requires POSIX")
    def test_clear_dialogue_is_isolated_and_rechecks_context(self) -> None:
        driver = load_driver()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fake = root / "fake_clear_tui.py"
            capture = root / "capture.pty"
            events = root / "events.jsonl"
            fake.write_text(textwrap.dedent(r'''
                import os, sys, tty
                tty.setraw(sys.stdin.fileno())
                os.write(sys.stdout.fileno(), b"ctx -- ready")
                def line():
                    value = bytearray()
                    while True:
                        character = os.read(sys.stdin.fileno(), 1)
                        if character == b"\r": return value.decode()
                        value.extend(character)
                assert line() == "/clear"
                os.write(sys.stdout.fileno(), b"ctx -- cleared")
                assert line() == "/context"
                os.write(sys.stdout.fileno(), b"native context 2%")
                assert line() == "/exit"
            '''), encoding="utf-8")
            result = driver.drive(
                [sys.executable, str(fake)], capture, timeout_seconds=10,
                events_path=events, dialogue="clear",
            )
            self.assertEqual(result, 0)
            event_text = events.read_text(encoding="utf-8")
            self.assertIn('"stage": "clear_observed"', event_text)
            self.assertIn('"stage": "context_inspected"', event_text)

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
                assert line() == "/context"
                os.write(sys.stdout.fileno(), b"native context 7% ctx --")
                second = line()
                assert "P004A_SECOND_TURN" not in second
                assert "joined by underscores" in second
                os.write(sys.stdout.fileno(), b"P004A_SECOND_TURN ctx --")
                third = line()
                assert "task list" in third.lower()
                assert "P004A_AUTO_CHECK_OK" not in third
                assert "joined by underscores" in third
                Path(sys.argv[1]).write_text("\n".join(json.dumps({
                    "kind": "compact", "phase": phase, "trigger": "auto",
                }) for phase in ("PreCompact", "PostCompact")) + "\n", encoding="utf-8")
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
            self.assertIn('"stage": "automatic_context_inspected"', event_text)
            self.assertIn('"percent": 7', event_text)
            self.assertIn('"stage": "automatic_compaction"', event_text)
            self.assertNotIn("P004A_AUTO", event_text)

    @unittest.skipUnless(os.name == "posix", "PTY behavior requires POSIX")
    def test_skill_dialogue_invokes_twice_measures_context_and_exercises_large_output(self) -> None:
        driver = load_driver()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fake = root / "fake_skill_tui.py"
            capture = root / "capture.pty"
            events = root / "events.jsonl"
            fake.write_text(textwrap.dedent(r'''
                import os, sys, tty
                tty.setraw(sys.stdin.fileno())
                os.write(sys.stdout.fileno(), b"ctx -- ready")
                def line():
                    value = bytearray()
                    while True:
                        character = os.read(sys.stdin.fileno(), 1)
                        if character == b"\r": return value.decode()
                        value.extend(character)
                first = line()
                assert first.startswith("/context-continuity ")
                assert "P004A_SKILL_ONE_OK" not in first
                assert "P004A, SKILL, ONE" in first
                os.write(sys.stdout.fileno(), b"P004A_SKILL_ONE_OK ctx --")
                assert line() == "/context"
                os.write(sys.stdout.fileno(), b"native context 6%")
                second = line()
                assert second.startswith("/context-continuity ")
                assert "128 short numbered lines" in second
                assert "P004A_SKILL_TWO_OK" not in second
                os.write(sys.stdout.fileno(), b"numbered output " + b"x" * 2048 + b" P004A_SKILL_TWO_OK ctx --")
                assert line() == "/context"
                os.write(sys.stdout.fileno(), b"native context 8%")
                assert line() == "/exit"
            '''), encoding="utf-8")
            result = driver.drive(
                [sys.executable, str(fake)], capture, timeout_seconds=10,
                events_path=events, dialogue="skill",
            )
            self.assertEqual(result, 0)
            event_text = events.read_text(encoding="utf-8")
            self.assertIn('"stage": "skill_one_context"', event_text)
            self.assertIn('"percent": 6', event_text)
            self.assertIn('"stage": "skill_two_context"', event_text)
            self.assertIn('"percent": 8', event_text)
            self.assertIn('"outputBytes":', event_text)
            self.assertNotIn("P004A_SKILL", event_text)

    @unittest.skipUnless(os.name == "posix", "PTY behavior requires POSIX")
    def test_mock_window_dialogue_requires_a_response_before_context_measurement(self) -> None:
        driver = load_driver()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fake = root / "fake_mock_tui.py"
            events = root / "events.jsonl"
            fake.write_text(textwrap.dedent(r'''
                import os, sys, tty
                tty.setraw(sys.stdin.fileno())
                os.write(sys.stdout.fileno(), b"ctx -- ready")
                def line():
                    value = bytearray()
                    while True:
                        character = os.read(sys.stdin.fileno(), 1)
                        if character == b"\r": return value.decode()
                        value.extend(character)
                prompt = line()
                assert "P004A_MOCK_OK" not in prompt and "P004A, MOCK" in prompt
                os.write(sys.stdout.fileno(), b"P004A_MOCK_OK")
                prompt = line()
                assert "Reply again" in prompt and "P004A_MOCK_OK" not in prompt
                os.write(sys.stdout.fileno(), b"P004A_MOCK_OK")
                assert line() == "/context"
                os.write(sys.stdout.fileno(), b"context [100k] 9%")
                assert line() == "/exit"
            '''), encoding="utf-8")
            result = driver.drive(
                [sys.executable, str(fake)], root / "capture.pty", 10,
                events_path=events, dialogue="mock-window",
            )
            self.assertEqual(result, 0)
            text = events.read_text(encoding="utf-8")
            self.assertIn('"stage": "mock_response"', text)
            self.assertIn('"stage": "mock_second_response"', text)
            self.assertIn('"percent": 9', text)


if __name__ == "__main__":
    unittest.main()
