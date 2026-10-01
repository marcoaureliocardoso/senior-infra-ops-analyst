#!/usr/bin/env python3
"""Provider-free process-boundary tests: all child programs are synthetic."""
import copy
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
MODULE = Path(__file__).with_name("browser_disposable_launcher.py")
AGGREGATE = {
    "status": "inconclusive", "reasonCode": "PREFLIGHT_READY",
    "observedRuntime": {"claude": "configured-claude", "provider": "unavailable",
                        "model": "observed-at-runtime", "adapter": "playwright"},
    "capabilityState": "AVAILABLE_RECOGNIZED", "guardProof": "exact-deny",
    "routeClass": "legacy-read-only-multi-command",
    "workflow": {"executionSteps": 0, "validationSteps": 0,
                 "authentication": "not-observed", "mutation": "not-observed",
                 "validation": "not-observed", "outcome": "NOT_OBSERVED"},
    "roleCount": 0, "toolCalls": 0, "hookEvents": 0,
    "context": {"before": 0, "afterSkill": 0, "afterSubagent": 0,
                "afterDiscovery": 0, "afterUse": 0, "toolSearchMode": "unavailable"},
    "cleanup": "verified", "permission": {"mode": "synthetic-deterministic",
        "allow": "not-observed", "deny": "not-observed", "callCount": 0},
}


@unittest.skipUnless(os.name == "posix", "POSIX pipe and process-group boundary")
class DisposableLauncherTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(MODULE.is_file(), "disposable launcher integration is missing")
        import browser_disposable_launcher
        self.launcher = browser_disposable_launcher
        self.parent = tempfile.TemporaryDirectory(prefix="p004b-launcher-test-")
        self.addCleanup(self.parent.cleanup)

    def run_child(self, code, *, timeout=3, **limits):
        result = self.launcher.supervise(
            [sys.executable, "-c", code], environment={"PATH": os.defpath},
            parent=Path(self.parent.name), timeout=timeout, **limits)
        self.assertEqual(list(Path(self.parent.name).iterdir()), [])
        self.assertEqual(result["launcherCleanup"], "verified")
        self.assertNotIn("secret", json.dumps(result).lower())
        return result

    def test_fragmented_diagnostic_and_final_aggregate_have_separate_channels(self):
        payload = json.dumps(AGGREGATE).encode()
        result = self.run_child(
            "import os,time; "
            "os.write(2,b'BLOCKED: trusted context probe failed: main-'); "
            "time.sleep(.03); os.write(2,b'before (PTY_PROMPT_READY_FAILED)\\r\\n'); "
            f"payload={payload!r}; "
            "[os.write(1,payload[n:n+7]) for n in range(0,len(payload),7)]")
        self.assertEqual(result["reasonCode"], "STREAM_COMPLETE")
        self.assertEqual(result["exitCode"], 0)
        self.assertEqual(result["diagnostics"], [{"category": "CONTEXT",
            "reasonCode": "PTY_PROMPT_READY_FAILED", "probe": "main-before"}])
        self.assertEqual(result["aggregateReported"]["reasonCode"], "PREFLIGHT_READY")
        self.assertNotIn("observedRuntime", result["aggregateReported"])

    def test_both_streams_are_drained_without_deadlock(self):
        result = self.run_child(
            "import os; [os.write(fd,b'secret\\n'*1000) for _ in range(12) for fd in (1,2)]")
        self.assertEqual(result["reasonCode"], "AGGREGATE_MISSING")
        self.assertEqual(len(result["diagnostics"]), 1)

    def test_overlong_line_discards_recognizable_suffix(self):
        result = self.run_child(
            "import os; os.write(2,b'secret'*1000+"
            "b'BLOCKED: Node.js not found\\n'); os.write(2,b'BLOCKED: Node.js not found\\n')")
        self.assertEqual(len(result["diagnostics"]), 2)
        self.assertEqual(result["diagnostics"][0]["category"], "UNKNOWN")
        self.assertNotEqual(result["diagnostics"][1]["category"], "UNKNOWN")

    def test_total_output_budget_terminates_child_and_removes_owned_state(self):
        result = self.run_child(
            "import os,pathlib,time; pathlib.Path(os.environ['TMPDIR'],'raw').write_text('secret'); "
            "os.write(1,b'x'*10000); time.sleep(30)", max_input=8192)
        self.assertEqual(result["reasonCode"], "OUTPUT_LIMIT")
        self.assertIsNone(result["aggregateReported"])

    def test_distinct_record_budget_is_bounded(self):
        result = self.run_child(
            "import os; os.write(2,b'BLOCKED: Node.js not found\\nBLOCKED: GUARD_UNPROVEN\\n')",
            max_records=1)
        self.assertEqual(result["reasonCode"], "RECORD_LIMIT")
        self.assertEqual(len(result["diagnostics"]), 1)

    def test_silent_timeout_and_closed_pipe_timeout_are_bounded(self):
        for code in ("import time; time.sleep(30)",
                     "import os,time; os.close(1); os.close(2); time.sleep(30)"):
            with self.subTest(code=code):
                started = time.monotonic()
                result = self.run_child(code, timeout=.12)
                self.assertEqual(result["reasonCode"], "TIMEOUT")
                self.assertLess(time.monotonic()-started, 3)

    def test_parent_exit_does_not_leave_descendant_holding_pipes(self):
        for ignore_term in (False, True):
            with self.subTest(ignore_term=ignore_term):
                ready = Path(self.parent.name) / "descendant-pid"
                code = ("import os,time,signal; from pathlib import Path; pid=os.fork();\n"
                        "if pid==0:\n"
                        f" signal.signal(signal.SIGTERM,signal.{'SIG_IGN' if ignore_term else 'SIG_DFL'})\n"
                        f" Path({str(ready)!r}).write_text(str(os.getpid()))\n"
                        " time.sleep(30)\n"
                        "else: os._exit(0)\n")
                result = self.launcher.supervise([sys.executable, "-c", code],
                    environment={}, parent=Path(self.parent.name), timeout=.3)
                self.assertTrue(ready.is_file())
                descendant = int(ready.read_text(encoding="ascii"))

                def running():
                    try:
                        # An unreaped zombie has terminated; kill(pid, 0) alone
                        # cannot distinguish that from a live orphan under WSL.
                        state = Path(f"/proc/{descendant}/stat").read_text().rsplit(")", 1)[1].split()[0]
                        return state not in {"Z", "X"}
                    except FileNotFoundError:
                        return False

                try:
                    deadline = time.monotonic()+2
                    while running() and time.monotonic() < deadline:
                        time.sleep(.01)
                    self.assertFalse(running(), "synthetic descendant survived supervisor cleanup")
                    self.assertEqual(result["reasonCode"], "TIMEOUT")
                    self.assertEqual(result["launcherCleanup"], "verified")
                finally:
                    if running():
                        os.kill(descendant, signal.SIGKILL)
                    ready.unlink()
                self.assertEqual(list(Path(self.parent.name).iterdir()), [])

    def test_duplicate_keys_nonfinite_and_invalid_utf8_cannot_supply_aggregate(self):
        payloads = (b'{"status":"pass","status":"fail"}', b'{"status":NaN}', b'{"status":"\xff"}')
        for payload in payloads:
            with self.subTest(payload=payload):
                result = self.run_child(f"import os; os.write(1,{payload!r})")
                self.assertEqual(result["reasonCode"], "AGGREGATE_REJECTED")
                self.assertIsNone(result["aggregateReported"])

    def test_duplicate_final_aggregate_is_rejected_even_when_identical(self):
        payload = (json.dumps(AGGREGATE)+"\n")*2
        result = self.run_child(f"print({payload!r},end='')")
        self.assertEqual(result["reasonCode"], "AGGREGATE_REJECTED")
        self.assertIsNone(result["aggregateReported"])

    def test_aggregate_on_stderr_is_not_an_aggregate(self):
        result = self.run_child(f"import os; os.write(2,{json.dumps(AGGREGATE).encode()!r})")
        self.assertEqual(result["reasonCode"], "AGGREGATE_MISSING")

    def test_nonzero_exit_invalidates_otherwise_valid_aggregate(self):
        result = self.run_child(f"import sys; print({json.dumps(AGGREGATE)!r}); sys.exit(7)")
        self.assertEqual(result["reasonCode"], "CHILD_FAILED")
        self.assertEqual(result["exitCode"], 7)
        self.assertIsNone(result["aggregateReported"])

    def test_valid_schema_cannot_leak_arbitrary_runtime_or_reason_labels(self):
        value = copy.deepcopy(AGGREGATE)
        value["reasonCode"] = "SECRET"
        value["observedRuntime"] = dict.fromkeys(value["observedRuntime"], "secret")
        result = self.run_child(f"print({json.dumps(value)!r})")
        self.assertEqual(result["aggregateReported"]["reasonCode"], "AGGREGATE_REASON_SUPPRESSED")

    def test_launch_error_is_closed_and_cleans_root(self):
        result = self.launcher.supervise(
            ["/nonexistent/secret"], environment={}, parent=Path(self.parent.name), timeout=1)
        self.assertEqual(result["reasonCode"], "LAUNCH_FAILED")
        self.assertEqual(result["launcherCleanup"], "verified")
        self.assertNotIn("secret", json.dumps(result))
        self.assertEqual(list(Path(self.parent.name).iterdir()), [])

    def test_pending_cleanup_and_incoherent_passing_claims_are_rejected(self):
        for field, replacement in (("cleanup", "pending"), ("status", "pass")):
            value = {**AGGREGATE, field: replacement}
            result = self.run_child(f"print({json.dumps(value)!r})")
            self.assertEqual(result["reasonCode"], "AGGREGATE_REJECTED")

    def test_symlink_in_owned_root_does_not_remove_external_target(self):
        with tempfile.TemporaryDirectory(prefix="p004b-outside-test-") as outside:
            target = Path(outside) / "keep"
            target.write_text("synthetic", encoding="ascii")
            result = self.run_child(
                "import os,pathlib; "
                f"pathlib.Path(os.environ['TMPDIR'],'link').symlink_to({outside!r},target_is_directory=True)")
            self.assertEqual(result["launcherCleanup"], "verified")
            self.assertEqual(target.read_text(encoding="ascii"), "synthetic")

    def test_replaced_owned_root_is_not_followed_or_claimed_clean(self):
        with tempfile.TemporaryDirectory(prefix="p004b-outside-test-") as outside:
            result = self.launcher.supervise([sys.executable, "-c",
                "import os,pathlib; root=pathlib.Path(os.environ['TMPDIR']); root.rmdir(); "
                f"root.symlink_to({outside!r},target_is_directory=True)"],
                environment={"PATH": os.defpath}, parent=Path(self.parent.name), timeout=3)
            self.assertEqual(result["reasonCode"], "LAUNCHER_CLEANUP_FAILED")
            self.assertEqual(result["launcherCleanup"], "failed")
            remaining = list(Path(self.parent.name).iterdir())
            self.assertEqual(len(remaining), 1)
            self.assertTrue(remaining[0].is_symlink())
            remaining[0].unlink()
            self.assertTrue(Path(outside).is_dir())

    def test_signal_interrupt_terminates_child_before_root_cleanup(self):
        ready = Path(self.parent.name) / "ready"
        child = ("import os,pathlib,time; "
                 f"pathlib.Path({str(ready)!r}).write_text(str(os.getpid())); time.sleep(30)")
        runner = ("import sys,json; from pathlib import Path; "
                  f"sys.path.insert(0,{str(MODULE.parent)!r}); "
                  "from browser_disposable_launcher import supervise; "
                  f"print(json.dumps(supervise([sys.executable,'-c',{child!r}],"
                  f"environment={{}},parent=Path({self.parent.name!r}),timeout=10)))")
        process = subprocess.Popen([sys.executable, "-c", runner], stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, env={"PATH": os.defpath, "PYTHONDONTWRITEBYTECODE": "1"})
        try:
            deadline = time.monotonic()+3
            while not ready.exists() and time.monotonic() < deadline:
                time.sleep(.01)
            self.assertTrue(ready.is_file(), "synthetic child did not become ready")
            child_pid = int(ready.read_text(encoding="ascii"))
            process.send_signal(signal.SIGTERM)
            stdout, stderr = process.communicate(timeout=4)
            self.assertEqual(stderr, b"")
            result = json.loads(stdout)
            self.assertEqual(result["reasonCode"], "INTERRUPTED")
            self.assertEqual(result["launcherCleanup"], "verified")
            with self.assertRaises(ProcessLookupError):
                os.kill(child_pid, 0)
            ready.unlink()
            self.assertEqual(list(Path(self.parent.name).iterdir()), [])
        finally:
            if process.poll() is None:
                process.kill()
            process.wait()

    def test_cli_refuses_live_even_with_authorization_shaped_environment(self):
        result = subprocess.run([sys.executable, str(MODULE), "--run-live"],
            env={"PATH": os.defpath, "P004B_LIVE_AUTHORIZED": "1",
                 "ANTHROPIC_API_KEY": "secret"}, capture_output=True, timeout=3)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["reasonCode"], "LIVE_AUTHORIZATION_REQUIRED")
        self.assertEqual(result.stderr, b"")

    def test_preflight_environment_drops_credentials_and_behavior_overrides(self):
        env = self.launcher.preflight_environment({
            "HOME": "/home/operator", "PATH": "/usr/bin:/bin",
            "ANTHROPIC_API_KEY": "secret", "ANTHROPIC_AUTH_TOKEN": "secret",
            "ANTHROPIC_BASE_URL": "https://secret", "CLAUDE_BIN": "/tmp/secret",
            "NODE_OPTIONS": "secret", "BASH_ENV": "/tmp/secret", "TMPDIR": "/tmp/secret",
            "P004B_LIVE_AUTHORIZED": "1", "CLAUDE_SETTINGS_SOURCE": "/tmp/secret",
            "P004B_BROWSER_NODE_MODULES": "/opt/modules",
            "P004B_PLAYWRIGHT_BROWSERS_PATH": "/opt/browsers"})
        self.assertEqual(set(env), {"HOME", "PATH", "P004B_BROWSER_NODE_MODULES",
                                   "P004B_PLAYWRIGHT_BROWSERS_PATH"})


if __name__ == "__main__":
    unittest.main()
