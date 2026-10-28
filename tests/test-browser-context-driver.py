#!/usr/bin/env python3
"""Provider-free scope tests for the acceptance-only startup entrypoint."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "tests/browser-context-driver.py"


class BrowserContextDriverTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(MODULE.is_file(), "dedicated context driver is missing")
        spec = importlib.util.spec_from_file_location("browser_context_driver", MODULE)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.temp = tempfile.TemporaryDirectory(prefix="p004b-context-scope-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = self.root / "home/.claude"
        self.config.mkdir(parents=True, mode=0o700)
        self.private = self.root / "startup-approval"
        self.private.mkdir(mode=0o700)
        self.mcp = self.root / "empty-mcp.json"
        self.mcp.write_text('{"mcpServers":{}}')
        self.claim = self.private / "claim.json"
        self.commit = "a" * 40
        self.nonce = "p004b-" + "b" * 32
        self.session = "11111111-1111-4111-8111-111111111111"
        self.executable = str(Path(sys.executable).resolve())
        self.command = [self.executable, "--session-id", self.session, "--strict-mcp-config", "--mcp-config", str(self.mcp)]
        self.env = {"ANTHROPIC_BASE_URL": "https://api.deepseek.com/anthropic", "CLAUDE_CONFIG_DIR": str(self.config)}
        self.claim.write_text(json.dumps({"commit": self.commit, "runNonce": self.nonce,
            "sessionId": self.session, "endpoint": self.env["ANTHROPIC_BASE_URL"],
            "configDir": str(self.config), "executable": self.executable, "probe": "main-before",
            "issuedAt": int(time.time()), "expiresAt": int(time.time()) + 120}))
        self.claim.chmod(0o600)

    def approve(self, command=None, **env):
        with mock.patch.dict(os.environ, {**self.env, **env}, clear=True), \
                mock.patch.object(self.module, "source_head", return_value=self.commit):
            return self.module.prepare_approval(self.claim, self.commit, self.nonce, ROOT,
                                                 command or self.command)

    def test_exact_native_scope_consumes_claim(self):
        self.assertIsNotNone(self.approve())
        self.assertFalse(self.claim.exists())
        with self.assertRaises(ValueError):
            self.approve()

    def test_resume_agent_extra_flags_endpoint_and_config_changes_block(self):
        for command in (self.command + ["--agent", "diagnostic-operator"],
                        self.command[:1] + ["--resume"] + self.command[2:],
                        self.command + ["--permission-mode", "bypassPermissions"],
                        self.command + ["--session-id", self.session]):
            with self.subTest(command=command), self.assertRaises(ValueError):
                self.approve(command)
        for env in ({"ANTHROPIC_BASE_URL": "https://other.example/anthropic"},
                    {"CLAUDE_CONFIG_DIR": "/tmp"}):
            with self.subTest(env=env), self.assertRaises(ValueError):
                self.approve(**env)
        self.assertTrue(self.claim.exists())

    def test_real_git_head_rejects_tracked_and_untracked_changes(self):
        repo = self.root / "repo"
        repo.mkdir()
        def git(*args):
            return subprocess.run(["git", "-C", str(repo), *args], check=True,
                                  capture_output=True, text=True).stdout.strip()
        git("init", "-q")
        tracked = repo / "tracked"
        tracked.write_text("synthetic")
        git("add", "tracked")
        git("-c", "user.name=Synthetic", "-c", "user.email=synthetic@example.invalid",
            "commit", "-qm", "synthetic")
        self.assertEqual(self.module.source_head(repo), git("rev-parse", "HEAD"))
        tracked.write_text("changed")
        with self.assertRaises(ValueError):
            self.module.source_head(repo)
        tracked.write_text("synthetic")
        (repo / "untracked").write_text("synthetic")
        with self.assertRaises(ValueError):
            self.module.source_head(repo)

    def test_wrong_source_commit_blocks_before_claim_consumption(self):
        with mock.patch.dict(os.environ, self.env, clear=True), \
                mock.patch.object(self.module, "source_head", return_value="c" * 40), self.assertRaises(ValueError):
            self.module.prepare_approval(self.claim, self.commit, self.nonce, ROOT, self.command)
        self.assertTrue(self.claim.exists())

    def test_another_clean_checkout_cannot_supply_running_driver_binding(self):
        with mock.patch.dict(os.environ, self.env, clear=True), \
                mock.patch.object(self.module, "source_head", return_value=self.commit), self.assertRaises(ValueError):
            self.module.prepare_approval(self.claim, self.commit, self.nonce, self.root, self.command)
        self.assertTrue(self.claim.exists())

    @unittest.skipUnless(Path("/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe").is_file()
                         and Path("/mnt/c/Program Files/Git/cmd/git.exe").is_file(), "WSL Windows bridge unavailable")
    def test_wsl_git_bridge_explicitly_forwards_only_git_isolation_variables(self):
        repo = self.root / "linked"
        repo.mkdir()
        (repo / ".git").write_text("gitdir: C:/synthetic/.git/worktrees/probe\n")
        calls = []
        def run(command, **options):
            calls.append((command, options))
            value = "C:\\synthetic\\linked\n" if command[0] == "wslpath" else self.commit if "rev-parse" in command else ""
            return subprocess.CompletedProcess(command, 0, value.encode(), b"")
        with mock.patch.object(self.module.subprocess, "run", side_effect=run):
            self.assertEqual(self.module.source_head(repo), self.commit)
        git_calls = [(command, options) for command, options in calls if command[0].endswith("git.exe")]
        self.assertEqual(len(git_calls), 2)
        env = git_calls[0][1]["env"]
        self.assertEqual(env["WSLENV"], "GIT_CONFIG_NOSYSTEM:GIT_CONFIG_GLOBAL")
        for command, options in git_calls:
            self.assertIn("core.fsmonitor=false", command)
            self.assertIn("--no-optional-locks", command)
            self.assertEqual(options["env"], env)
        result = subprocess.run(["/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe",
            "-NoLogo", "-NoProfile", "-NonInteractive", "-Command",
            "[Console]::WriteLine(($env:GIT_CONFIG_NOSYSTEM -eq '1') -and ($env:GIT_CONFIG_GLOBAL -eq 'NUL'))"],
            env=env, capture_output=True, timeout=15, check=True)
        self.assertEqual(result.stdout.strip(), b"True")


if __name__ == "__main__":
    unittest.main()
