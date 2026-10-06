#!/usr/bin/env python3
"""Provider-free tests for single-use acceptance-only startup approval."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

MODULE = Path(__file__).with_name("browser_startup_approval.py")
SCREEN = "Do you want to use this API key?\n  1. Yes\n❯ 2. No (recommended)\n"


class StartupApprovalTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(MODULE.is_file(), "startup approval implementation is missing")
        spec = importlib.util.spec_from_file_location("startup_approval", MODULE)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.temp = tempfile.TemporaryDirectory(prefix="p004b-approval-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.private = self.root / "startup-approval"
        self.private.mkdir(mode=0o700)
        self.config = self.root / "home" / ".claude"
        self.config.mkdir(parents=True, mode=0o700)
        self.binding = {"commit": "a" * 40, "runNonce": "p004b-" + "b" * 32,
                        "sessionId": "11111111-1111-4111-8111-111111111111",
                        "endpoint": "https://api.deepseek.com/anthropic",
                        "configDir": str(self.config), "executable": "/usr/bin/claude",
                        "probe": "main-before"}
        self.claim = self.private / "claim.json"
        self.write_claim()

    def write_claim(self, **changes):
        self.claim.write_text(json.dumps({**self.binding, "issuedAt": 1000,
                                         "expiresAt": 1120, **changes}), encoding="utf-8")
        self.claim.chmod(0o600)

    def load(self, **changes):
        return self.module.load_approval(self.claim, {**self.binding, **changes}, clock=lambda: 1001)

    def test_exact_binding_allows_one_semantic_selection_and_consumes_claim(self):
        approval = self.load()
        self.assertFalse(self.claim.exists())
        self.assertEqual(approval.selection(SCREEN), b"\x1b[A")
        self.assertIsNone(approval.selection(SCREEN))
        self.write_claim()
        with self.assertRaises(ValueError):
            self.load()

    def test_every_changed_binding_and_invalid_scope_is_rejected(self):
        for key in self.binding:
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    self.load(**{key: "different"})
        for changes in ({"probe": "main-after-use"}, {"expiresAt": 1001},
                        {"issuedAt": 1002}, {"expiresAt": 5000}, {"extra": True}):
            with self.subTest(changes=changes):
                self.write_claim(**changes)
                with self.assertRaises(ValueError):
                    self.load()

    def test_unknown_ambiguous_login_or_repeated_screen_cannot_be_approved(self):
        approval = self.load()
        for index, screen in enumerate(("Select login method:\n❯ 1. Continue", SCREEN.replace("1. Yes", "1. Continue"),
                                       SCREEN.replace("❯", ""), SCREEN + "3. Other\n")):
            with self.subTest(screen=screen):
                if index:
                    self.private = self.root / f"approval-{index}"
                    self.private.mkdir(mode=0o700)
                    self.claim = self.private / "claim.json"
                    self.write_claim()
                    approval = self.load()
                self.assertIsNone(approval.selection(screen))

    def test_read_unsafe_or_linked_claims_are_rejected(self):
        if os.name != "posix":
            self.skipTest("POSIX owner/mode boundary")
        self.claim.chmod(0o644)
        with self.assertRaises(ValueError):
            self.load()
        self.claim.unlink()
        target = self.root / "external"
        target.write_text("{}", encoding="utf-8")
        self.claim.symlink_to(target)
        with self.assertRaises(ValueError):
            self.load()
        self.assertEqual(target.read_text(), "{}")

    def test_native_unnumbered_block_does_not_use_stale_other_dialogue(self):
        approval = self.load()
        screen = ("Do you want to use this API key?\n\n  Yes\n❯ No (recommended)\n\n"
                  "❯ No, exit\n  Yes, I trust this folder\n")
        self.assertEqual(approval.selection(screen), b"\x1b[A")

    def test_non_string_binding_is_rejected_without_type_error(self):
        for key in self.binding:
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.load(**{key: None})

    def test_read_atime_change_does_not_invalidate_immutable_claim(self):
        actual_fstat = os.fstat
        calls = 0
        def changed_atime(descriptor):
            nonlocal calls
            info = actual_fstat(descriptor)
            calls += 1
            if calls == 2:
                values = {name: getattr(info, name) for name in dir(info) if name.startswith("st_")}
                values["st_atime"] += 1
                values["st_atime_ns"] += 1000000000
                return SimpleNamespace(**values)
            return info
        with mock.patch.object(self.module.os, "fstat", side_effect=changed_atime):
            self.assertEqual(self.load().selection(SCREEN), b"\x1b[A")

    def test_expiry_revocation_and_already_selected_yes(self):
        approval = self.module.StartupApproval(1120, lambda: 1119)
        self.assertEqual(approval.selection(SCREEN.replace("  1. Yes", "❯ 1. Yes").replace("❯ 2.", "  2.")), b"")
        approval = self.module.StartupApproval(1120, lambda: 1120)
        self.assertIsNone(approval.selection(SCREEN))
        approval = self.module.StartupApproval(1120, lambda: 1001)
        approval.revoke()
        self.assertIsNone(approval.selection(SCREEN))

    def test_duplicate_oversized_hardlinked_or_nonregular_claims_block(self):
        self.claim.write_text('{"commit":"a","commit":"b"}')
        with self.assertRaises(ValueError):
            self.load()
        self.claim.write_text(" " * 4097)
        with self.assertRaises(ValueError):
            self.load()
        self.write_claim()
        os.link(self.claim, self.private / "duplicate")
        with self.assertRaises(ValueError):
            self.load()
        self.claim.unlink()
        os.mkfifo(self.claim, 0o600)
        with self.assertRaises(ValueError):
            self.load()

    def test_unsafe_directory_and_outside_or_symlink_config_block(self):
        self.private.chmod(0o755)
        with self.assertRaises(ValueError):
            self.load()
        self.private.chmod(0o700)
        with self.assertRaises(ValueError):
            self.load(configDir="/tmp")
        linked = self.root / "linked-config"
        linked.symlink_to(self.config)
        with self.assertRaises(ValueError):
            self.load(configDir=str(linked))

    def test_mixed_login_and_api_selector_cannot_approve(self):
        for heading in ("Select login method", "How would you like to log in", "Claude Code requires authentication"):
            with self.subTest(heading=heading):
                approval = self.module.StartupApproval(1120, lambda: 1001)
                self.assertIsNone(approval.selection(SCREEN + "\n" + heading))


if __name__ == "__main__":
    unittest.main()
