"""Owned-tree and external transaction controls; no root or network calls."""
from dataclasses import replace
import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/ci-isolation"


class FixtureExecutor:
    """Test-only transport; real child processes implement package/build effects."""
    def __init__(self, directory, mode="valid"):
        self.directory, self.mode = directory, mode
        self.prefix_base = directory / "opt"
        self.prefix_base.mkdir()
        self.owner_uid = os.getuid()
        self.template_sha256 = "0" * 64
        self.state = directory / "state.json"
        self.state.write_text(json.dumps({"generation": 0, "events": []}), encoding="ascii")
        (directory / "foreign").write_bytes(b"foreign fixture")
        self.published = False

    def external(self, tool, *args):
        result = subprocess.run([sys.executable, str(FIXTURES / tool), *map(str, args)],
                                stdin=subprocess.DEVNULL, capture_output=True, timeout=5,
                                env={"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"})
        if result.returncode:
            raise ValueError("FIXTURE_TOOL_FAILED")
        return result.stdout.decode("ascii")

    def prepare_packages(self, deadline):
        from ci_image_upgrade import prepare_image_packages
        return prepare_image_packages(FixturePackageAdapter(self), deadline=deadline)

    def build_candidate(self, spec, deadline):
        self.external("fake-build.py", self.directory, self.mode)
        return self.directory / "candidate"

    def install_candidate(self, candidate, prefix, receipt, deadline):
        from ci_isolation_runtime import install_owned_tree
        result = install_owned_tree(candidate, prefix, receipt, owner_uid=self.owner_uid)
        if self.mode == "substitute":
            (prefix / "bin/bwrap").unlink()
            (prefix / "bin/bwrap").symlink_to(self.directory / "foreign")
        return result

    def publish(self, runtime):
        self.published = True

    def cleanup_owned(self, runtime, deadline):
        from ci_isolation_runtime import remove_owned_tree
        return remove_owned_tree(runtime, owner_uid=self.owner_uid)


class FixturePackageAdapter:
    requested = frozenset({"build-demo"})
    reboot_required = False

    def __init__(self, executor):
        self.executor = executor

    def refresh(self, deadline):
        self.executor.external("fake-package.py", self.executor.state, "refresh", self.executor.mode)

    def snapshot(self, deadline):
        return json.loads(self.executor.state.read_text())["generation"]

    def held_packages(self, deadline):
        return frozenset()

    def simulate(self, kind, deadline):
        result = self.executor.external("fake-package.py", self.executor.state,
                                      "simulate" if kind == "upgrade" else "simulate-dependencies",
                                      self.executor.mode)
        if self.executor.mode == "drift" and "freeze" in json.loads(self.executor.state.read_text())["events"]:
            return result.replace("1.1", "1.2")
        return result

    def service_packages(self, proposal, deadline):
        return frozenset()

    def freeze(self, kind, proposal, deadline):
        self.executor.external("fake-package.py", self.executor.state, "freeze", self.executor.mode)

    def apply(self, kind, proposal, deadline):
        self.executor.external("fake-package.py", self.executor.state,
                               "apply" if kind == "upgrade" else "dependencies", self.executor.mode)

    def verify_changes(self, before, proposal, deadline):
        expected = before + bool(proposal.actions)
        if self.snapshot(deadline) != expected:
            raise ValueError("PACKAGE_POSTCONDITION_FAILED")


class ProvisioningTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT / "tests/ci_isolation_bootstrap.py").is_file(),
                        "owned provisioning is not implemented")
        self.m = importlib.import_module("ci_isolation_bootstrap")
        self.r = importlib.import_module("ci_isolation_runtime")
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.spec = self.r.load_runtime_spec(ROOT / "tests/ci-runtime-lock.json")

    def execute(self, mode="valid"):
        self.executor = FixtureExecutor(self.directory, mode)
        return self.m.provision_runtime(self.spec, executor=self.executor,
                                        deadline=time.monotonic() + 20)

    def test_verified_tree_publishes_and_owned_cleanup_removes_only_itself(self):
        runtime = self.execute()
        self.assertTrue(self.executor.published)
        self.assertIsNone(self.r.verify_installed_runtime(runtime))
        self.assertTrue(self.m.cleanup_runtime(runtime, executor=self.executor,
                                              deadline=time.monotonic() + 5))
        self.assertFalse(runtime.prefix.exists())
        self.assertEqual((self.directory / "foreign").read_bytes(), b"foreign fixture")

    def test_symlink_candidate_never_installs(self):
        with self.assertRaises(ValueError):
            self.execute("symlink")
        self.assertFalse(self.executor.published)
        self.assertFalse((self.executor.prefix_base / self.spec.source_sha256).exists())
        self.assertEqual((self.directory / "foreign").read_bytes(), b"foreign fixture")

    def test_prefix_substitution_before_publish_is_rejected(self):
        with self.assertRaises(ValueError):
            self.execute("substitute")
        self.assertFalse(self.executor.published)
        self.assertEqual((self.directory / "foreign").read_bytes(), b"foreign fixture")

    def test_failed_upgrade_cannot_continue_to_build(self):
        with self.assertRaises(ValueError):
            self.execute("partial-failure")
        self.assertFalse((self.directory / "build-started").exists())
        self.assertFalse(self.executor.published)
        state = json.loads(self.executor.state.read_text())
        self.assertEqual(state["generation"], 1)
        self.assertEqual(state["events"], ["refresh", "simulate", "freeze", "simulate", "apply"])

    def test_skipped_general_upgrade_still_provisions_dependencies(self):
        runtime = self.execute("skip-unsafe")
        self.assertTrue(self.executor.published)
        events = json.loads(self.executor.state.read_text())["events"]
        self.assertIn("simulate-dependencies", events)
        self.assertNotIn("apply", events)
        self.assertTrue(self.m.cleanup_runtime(runtime, executor=self.executor,
                                              deadline=time.monotonic() + 5))

    def test_untrusted_or_failed_package_results_never_build(self):
        for mode in ("index-failure", "malformed"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                executor = FixtureExecutor(Path(directory), mode)
                with self.assertRaises(ValueError):
                    self.m.provision_runtime(self.spec, executor=executor,
                                             deadline=time.monotonic() + 10)
                self.assertFalse((Path(directory) / "build-started").exists())
                self.assertFalse(executor.published)

    def test_bad_builds_and_modes_cannot_publish(self):
        for mode in ("build-failure", "writable", "setuid"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                executor = FixtureExecutor(Path(directory), mode)
                with self.assertRaises(ValueError):
                    self.m.provision_runtime(self.spec, executor=executor,
                                             deadline=time.monotonic() + 10)
                self.assertFalse(executor.published)
                self.assertFalse((executor.prefix_base / self.spec.source_sha256).exists())

    def test_existing_prefix_is_not_adopted_or_deleted(self):
        executor = FixtureExecutor(self.directory)
        prefix = executor.prefix_base / self.spec.source_sha256
        prefix.mkdir()
        (prefix / "foreign").write_bytes(b"owned elsewhere")
        with self.assertRaises(ValueError):
            self.m.provision_runtime(self.spec, executor=executor, deadline=time.monotonic() + 10)
        self.assertEqual((prefix / "foreign").read_bytes(), b"owned elsewhere")
        self.assertFalse(executor.published)

    def test_digest_version_ownership_and_capability_drift_are_rejected(self):
        runtime = self.execute()
        runtime.binary.write_bytes(b"#!/bin/sh\nprintf 'bubblewrap 0.9.0\\n'\n")
        with self.assertRaises(ValueError):
            self.r.verify_installed_runtime(runtime)
        for mutation in (replace(runtime.receipt, binary_sha256="0" * 64),
                         replace(runtime.receipt, owner_uid=runtime.receipt.owner_uid + 1),
                         replace(runtime.receipt, version="0.9.0")):
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                self.r.verify_installed_runtime(replace(runtime, receipt=mutation))
        # No permission to add real file capabilities is needed to test xattr refusal.
        self.assertFalse(self.r.file_metadata_is_safe(mode=0o100755, uid=0, owner_uid=0,
                                                      capabilities=b"synthetic"))
        self.assertFalse(self.executor.cleanup_owned(runtime, time.monotonic() + 5))

    def test_expired_deadline_never_starts_packages(self):
        executor = FixtureExecutor(self.directory)
        with self.assertRaises(ValueError):
            self.m.provision_runtime(self.spec, executor=executor, deadline=time.monotonic() - 1)
        self.assertEqual(json.loads(executor.state.read_text())["events"], [])

    def test_resolver_drift_never_applies_or_builds(self):
        with self.assertRaises(ValueError):
            self.execute("drift")
        self.assertNotIn("apply", json.loads(self.executor.state.read_text())["events"])
        self.assertFalse((self.directory / "build-started").exists())

    def test_unrelated_deferred_updates_do_not_block_safe_dependencies(self):
        runtime = self.execute("deferred")
        self.assertTrue(self.executor.published)
        self.assertTrue(self.m.cleanup_runtime(runtime, executor=self.executor,
                                              deadline=time.monotonic() + 5))

    def test_timeout_after_install_prevents_publication(self):
        executor = FixtureExecutor(self.directory)
        original = executor.install_candidate
        def delayed(*args):
            result = original(*args)
            time.sleep(0.1)
            return result
        executor.install_candidate = delayed
        with self.assertRaises(ValueError):
            self.m.provision_runtime(self.spec, executor=executor,
                                     deadline=time.monotonic() + 0.01)
        self.assertFalse(executor.published)

    def test_linux_command_transport_does_not_accept_unknown_program(self):
        self.assertTrue((ROOT / "tests/ci_isolation_linux.py").is_file())
        linux = importlib.import_module("ci_isolation_linux")
        transport = linux.LinuxExecutor(self.spec, self.directory, "a" * 32, "0" * 64)
        for command in (("relative",), ("/bin/sh", "-c", "true"), ("/usr/bin/python3", "bad\x00arg")):
            with self.subTest(command=command), self.assertRaises(ValueError):
                transport.command(command, time.monotonic() + 1)


if __name__ == "__main__":
    unittest.main()
