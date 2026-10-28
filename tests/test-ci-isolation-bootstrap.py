"""Owned-tree and external transaction controls; no root or network calls."""
from dataclasses import replace
import hashlib
import importlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/ci-isolation"


class ReviewedTransportTests(unittest.TestCase):
    def test_service_metadata_preserves_non_ascii_filename_bytes(self):
        import ci_isolation_linux as linux
        from ci_image_upgrade import UpgradeAction, UpgradeProposal
        from types import SimpleNamespace
        proposal = UpgradeProposal((UpgradeAction('upgrade', 'fixture-package', '1.0', '1.1'),), 0)
        for archive in (False, True):
            for paths, expected in (
                ([b'/usr/share/doc/caf\xc3\xa9.txt'], frozenset()),
                ([b'/usr/share/doc/opaque-\xff.txt'], frozenset()),
                ([b'/usr/share/doc/caf\xc3\xa9.txt', b'/etc/systemd/system/opaque-\xff.service'],
                 frozenset({'fixture-package'})),
            ):
                with self.subTest(archive=archive, paths=len(paths), service=bool(expected)):
                    def command(argv, deadline):
                        if argv == ['/usr/bin/dpkg-query', '--listfiles', 'fixture-package']:
                            return b'\n'.join(paths) + b'\n'
                        self.assertEqual(argv, ['/usr/bin/dpkg-deb', '--contents', '/fixture.deb'])
                        return b'\n'.join(b'-rw-r--r-- root/root 0 2026-01-01 00:00 .' + p for p in paths) + b'\n'
                    adapter = object.__new__(linux.LinuxPackageAdapter)
                    adapter.executor = SimpleNamespace(command=command)
                    adapter.frozen = {'fixture-package': (Path('/fixture.deb'),)} if archive else {}
                    current = replace(proposal.actions[0], installed_version=None) if archive else proposal.actions[0]
                    self.assertEqual(adapter.service_packages(UpgradeProposal((current,), 0), 1), expected)

    def test_top_level_cleanup_checks_policy_even_without_completed_marker(self):
        import ci_isolation_bootstrap as bootstrap
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            nonce = "a" * 32
            workspace = root / ("senior-infra-ci-" + nonce)
            workspace.mkdir(mode=0o700)
            cache = root / "cache"
            cache.mkdir()
            prefix = root / "prefix" / ("0" * 64)
            prefix.mkdir(parents=True)
            target = root / "orphan-policy"
            target.write_bytes(b"unmarked policy")
            record = {"nonce": nonce, "workspaceIdentity": [workspace.stat().st_dev, workspace.stat().st_ino]}
            runtime = SimpleNamespace(prefix=prefix)
            policy = bootstrap.OwnedPolicy("parent", "child", target, "0" * 64)
            executor = SimpleNamespace(spec=SimpleNamespace(source_sha256="0" * 64),
                prefix_base=prefix.parent, cache=cache, workspace=workspace,
                policy_template=lambda: b"fixture", cleanup_owned=lambda *args: True,
                cleanup_cache=lambda *args: True,
                remove_policy=lambda *args: False)  # actual worker rejects an unmarked target
            with patch.object(bootstrap, "_runtime_from_disk", return_value=runtime), \
                    patch.object(bootstrap, "policy_for_runtime", return_value=policy):
                self.assertFalse(bootstrap._cleanup(executor, record, deadline=time.monotonic() + 5))
            self.assertTrue(target.exists())
            self.assertTrue(workspace.exists())

    def test_partial_policy_publication_is_owned_before_target_appears(self):
        import ci_isolation_root as worker
        from ci_isolation_bootstrap import OwnedPolicy
        self.assertTrue(hasattr(worker, "publish_owned_policy"), "transactional publication is absent")
        for boundary in ("before-marker", "before-link", "after-link", "complete"):
            with self.subTest(boundary=boundary), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                cache = root / "cache"
                cache.mkdir()
                data = b"synthetic policy data\n"
                policy = OwnedPolicy("synthetic-parent", "synthetic-child", root / "target",
                                     hashlib.sha256(data).hexdigest())
                real_link, real_marker = os.link, worker.store_policy_marker

                def link(*args, **kwargs):
                    if boundary == "before-link":
                        raise InterruptedError("synthetic cancellation")
                    real_link(*args, **kwargs)
                    if boundary == "after-link":
                        raise InterruptedError("synthetic cancellation")

                def marker(*args, **kwargs):
                    if boundary == "before-marker":
                        raise InterruptedError("synthetic cancellation")
                    return real_marker(*args, **kwargs)

                with patch.object(worker.os, "link", link), patch.object(worker, "store_policy_marker", marker):
                    if boundary == "complete":
                        worker.publish_owned_policy(policy, data, cache, "a" * 32)
                    else:
                        with self.assertRaises(InterruptedError):
                            worker.publish_owned_policy(policy, data, cache, "a" * 32)
                if policy.path.exists():
                    self.assertTrue((cache / "policy-owner.json").is_file())
                worker.cleanup_owned_policy(policy, cache, "a" * 32, owner_uid=os.getuid())
                self.assertFalse(policy.path.exists())
                self.assertFalse((cache / "policy-owner.json").exists())

    def test_unmarked_policy_target_cannot_be_reported_clean(self):
        import ci_isolation_root as worker
        from ci_isolation_bootstrap import OwnedPolicy
        self.assertTrue(hasattr(worker, "cleanup_owned_policy"), "owned cleanup is absent")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target"
            target.write_bytes(b"foreign")
            policy = OwnedPolicy("synthetic-parent", "synthetic-child", target, "0" * 64)
            with self.assertRaises(ValueError):
                worker.cleanup_owned_policy(policy, root, "a" * 32, owner_uid=os.getuid())
            self.assertEqual(target.read_bytes(), b"foreign")

    def test_partial_policy_load_failure_retains_ownership_until_both_names_are_absent(self):
        import ci_isolation_root as worker
        from ci_isolation_bootstrap import OwnedPolicy
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = b"synthetic policy\n"
            policy = OwnedPolicy("synthetic-parent", "synthetic-child", root / "target",
                                 hashlib.sha256(data).hexdigest())
            marker = worker.publish_owned_policy(policy, data, root, "a" * 32)
            worker.store_policy_marker(root, {**marker, "loadStarted": True})

            def still_loaded():
                raise ValueError("CI_POLICY_CLEANUP_FAILED")

            with self.assertRaisesRegex(ValueError, "CI_POLICY_CLEANUP_FAILED"):
                worker.cleanup_owned_policy(policy, root, "a" * 32, owner_uid=os.getuid(),
                    profiles=frozenset({"synthetic-child"}), remove=still_loaded)
            self.assertTrue(policy.path.exists())
            self.assertTrue((root / "policy-owner.json").exists())
            worker.cleanup_owned_policy(policy, root, "a" * 32, owner_uid=os.getuid(), remove=lambda: None)
            self.assertFalse(policy.path.exists())

    def test_policy_cleanup_rejects_substituted_inode_and_preserves_foreign_data(self):
        import ci_isolation_root as worker
        from ci_isolation_bootstrap import OwnedPolicy
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = b"synthetic policy\n"
            policy = OwnedPolicy("synthetic-parent", "synthetic-child", root / "target",
                                 hashlib.sha256(data).hexdigest())
            worker.publish_owned_policy(policy, data, root, "a" * 32)
            policy.path.unlink()
            policy.path.write_bytes(data)
            with self.assertRaises(ValueError):
                worker.cleanup_owned_policy(policy, root, "a" * 32, owner_uid=os.getuid())
            self.assertEqual(policy.path.read_bytes(), data)
            self.assertTrue((root / "policy-owner.json").exists())

    def test_new_and_existing_multiarch_packages_use_validated_archive_identity(self):
        import ci_isolation_linux as linux
        from ci_image_upgrade import UpgradeAction, UpgradeProposal
        # A native dpkg-query record for Multi-Arch: same is qualified even on
        # its first installation. Never derive the expected spelling from before.
        metadata = {"Package": "libcap-dev", "Version": "1.0", "Architecture": "amd64", "Multi-Arch": "same"}
        adapter = object.__new__(linux.LinuxPackageAdapter)
        adapter.security = ("fixed",)
        adapter.frozen = {"libcap-dev": (None, "1.0", "0" * 64, "libcap-dev:amd64")}
        adapter.executor = type("QueryFixture", (), {"command": lambda self, argv, deadline:
            b"libcap-dev:amd64\t1.0\tinstalled\n"})()
        for before in ({}, {"libcap-dev:amd64": ("0.9", "installed")}):
            action = UpgradeAction("upgrade" if before else "install", "libcap-dev",
                                   "0.9" if before else None, "1.0")
            proposal = UpgradeProposal((action,), 0)
            with patch.object(adapter, "security_snapshot", return_value=("fixed",)):
                adapter.verify_changes(before, proposal, time.monotonic() + 5)
        self.assertEqual(linux.archive_package_identity(metadata), "libcap-dev:amd64")
        for architecture, multiarch in (("arm64", "same"), ("amd64", "unknown"), ("all", "same")):
            with self.assertRaises(ValueError):
                linux.archive_package_identity({**metadata, "Architecture": architecture, "Multi-Arch": multiarch})
        self.assertEqual(linux.archive_package_identity({**metadata, "Multi-Arch": "foreign"}), "libcap-dev")

    def test_hosted_writable_opt_does_not_control_private_runtime_ancestors(self):
        import ci_isolation_linux as linux
        import ci_isolation_root as worker
        original = Path.lstat

        def hosted_lstat(path):
            info = original(path)
            if path == Path("/opt"):
                values = list(info)
                values[0] = (info.st_mode & ~0o777) | 0o777
                return os.stat_result(values)
            return info

        with patch.object(Path, "lstat", hosted_lstat):
            for module in (linux, worker):
                worker.protected_directory(module.PREFIX_BASE.parent)
                worker.protected_directory(module.CACHE_BASE.parent)

    def test_package_child_receives_fixed_environment_after_sudo_reset(self):
        import ci_isolation_linux as linux
        real_popen = subprocess.Popen

        def synthetic_sudo(argv, **kwargs):
            self.assertEqual(argv[:2], ["/usr/bin/sudo", "-n"])
            return real_popen([sys.executable, str(FIXTURES / "fake-sudo.py"), *argv[1:]], **kwargs)

        with tempfile.TemporaryDirectory() as directory:
            spec = importlib.import_module("ci_isolation_runtime").load_runtime_spec(ROOT / "tests/ci-runtime-lock.json")
            executor = linux.LinuxExecutor(spec, Path(directory), "a" * 32, "0" * 64)
            with patch.object(linux.subprocess, "Popen", synthetic_sudo):
                raw = executor.command(["/usr/bin/python3", "-c",
                    "import os,json; print(json.dumps(dict(os.environ)))"],
                    time.monotonic() + 5, privileged=True)
            env = json.loads(raw)
            self.assertEqual(env.get("DEBIAN_FRONTEND"), "noninteractive")
            self.assertEqual(env.get("NEEDRESTART_MODE"), "l")
            self.assertEqual(env.get("LC_ALL"), "C")
            self.assertEqual(env.get("HOME"), directory)
            # dpkg maintainer scripts require the fixed system sbin locations
            # (for example ldconfig); never use runner-controlled PATH entries.
            self.assertEqual(env.get("PATH"), "/usr/sbin:/usr/bin:/sbin:/bin")


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
        self.nonce = "a" * 32

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

    def test_normal_access_time_update_is_not_binary_substitution(self):
        runtime = self.execute()
        info = runtime.binary.stat()
        os.utime(runtime.binary, ns=(1, info.st_mtime_ns))
        self.assertIsNone(self.r.verify_installed_runtime(runtime))

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


class NamespaceEvidenceTests(unittest.TestCase):
    def executor(self, directory):
        import ci_isolation_linux as linux
        executor = linux.LinuxExecutor(SimpleNamespace(source_sha256='a' * 64),
                                       Path(directory), 'b' * 32, 'c' * 64)
        runtime = SimpleNamespace(binary=Path('/verified/private/bin/bwrap'),
                                  receipt=SimpleNamespace(binary_sha256='d' * 64))
        return linux, executor, runtime

    def test_fast_exit_preserves_launched_pid_without_proc_observation(self):
        with tempfile.TemporaryDirectory() as directory:
            linux, executor, runtime = self.executor(directory)
            process = SimpleNamespace(pid=4321, returncode=1, poll=lambda: 1)
            with patch.object(linux, 'verify_installed_runtime'), \
                    patch.object(linux.subprocess, 'Popen', return_value=process), \
                    patch.object(linux.os, 'readlink', side_effect=FileNotFoundError):
                self.assertFalse(executor.namespace_probe(runtime, 'full', time.monotonic() + 5))
            self.assertEqual(executor.probe_records[0][2:], ((4321,), ()))

    def test_audit_rejects_missing_invalid_or_excessive_pid_identity_before_reader(self):
        for pids in ((), (True,), (0,), (-1,), ('4321',), tuple(range(1, 130))):
            with self.subTest(count=len(pids)), tempfile.TemporaryDirectory() as directory:
                _, executor, runtime = self.executor(directory)
                executor.probe_records = [(1.0, 2.0, pids, ())]
                def unexpected_reader(*args):
                    self.fail('invalid process identity reached the privileged reader')
                executor.root_action = unexpected_reader
                with self.assertRaisesRegex(ValueError, '^CI_POLICY_EVIDENCE_MISSING$'):
                    executor.denial_evidence(runtime, time.monotonic() + 5)

    def test_audit_response_requires_one_exact_boolean_field(self):
        samples = (b'not-json', b'{"matched":1}', b'{"matched":null}', b'{}',
                   b'{"matched":true,"matched":false}', b'{"matched":false,"matched":true}',
                   b'{"matched":true,"extra":"private"}', b'[["matched",true]]', b'[]',
                   b' ' * 129, b'\xff')
        for sample in samples:
            with self.subTest(length=len(sample)), tempfile.TemporaryDirectory() as directory:
                _, executor, runtime = self.executor(directory)
                executor.probe_records = [(1.0, 2.0, (4321,), ())]
                executor.root_action = lambda *args: sample
                with self.assertRaisesRegex(ValueError, '^CI_POLICY_EVIDENCE_REJECTED$'):
                    executor.denial_evidence(runtime, time.monotonic() + 5)

    def test_audit_boolean_keeps_pid_window_and_binary_correlation(self):
        for matched in (False, True):
            with self.subTest(matched=matched), tempfile.TemporaryDirectory() as directory:
                _, executor, runtime = self.executor(directory)
                executor.probe_records = [(1.0, 2.0, (4321,), ()), (2.0, 3.0, (4322,), ())]
                def reader(action, deadline, request):
                    self.assertEqual(action, 'audit-read')
                    self.assertEqual(json.loads(request), {'pids': [4321, 4322], 'window': [1.0, 3.0]})
                    return json.dumps({'matched': matched}).encode('ascii')
                executor.root_action = reader
                evidence = executor.denial_evidence(runtime, time.monotonic() + 5)
                self.assertIs(evidence.correlated, matched)
                self.assertEqual(evidence.executable_identity, 'd' * 64)
                self.assertEqual(evidence.time_window, (1.0, 3.0))


class PolicyFixtureExecutor(FixtureExecutor):
    def snapshot_policy(self, runtime, deadline):
        from ci_isolation_bootstrap import PolicySnapshot
        return PolicySnapshot(True, 1, ("foreign",) if self.mode == "foreign" else ())

    def namespace_probe(self, runtime, kind, deadline):
        self.external("fake-policy.py", self.state, "probe-" + kind, self.mode)
        return self.mode == "supported" or json.loads(self.state.read_text()).get("policy", False)

    def denial_evidence(self, runtime, deadline):
        from ci_isolation_bootstrap import DenialEvidence
        return DenialEvidence(runtime.receipt.binary_sha256, (1.0, 2.0),
                              "unprivileged_userns", "net_admin", self.mode != "unrelated")

    def load_policy(self, runtime, policy, deadline):
        self.external("fake-policy.py", self.state, "policy-load", self.mode)
        if self.mode == "cancel-load":
            raise KeyboardInterrupt

    def remove_policy(self, policy, deadline):
        self.external("fake-policy.py", self.state, "policy-remove", self.mode)
        return True

    def policy_template(self):
        from ci_isolation_bootstrap import load_policy_template
        return load_policy_template(ROOT / "tests/ci-runtime-lock.json")

    def verify_child_transition(self, runtime, policy, deadline):
        return self.mode not in ("transition-failure", "cleanup-failure")


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.m = importlib.import_module("ci_isolation_bootstrap")
        self.assertTrue(hasattr(self.m, "policy_is_needed"), "conditional policy gate is absent")

    def test_uncorrelated_denial_cannot_request_policy(self):
        snapshot = self.m.PolicySnapshot(True, 1, ())
        evidence = self.m.DenialEvidence("verified-binary", (1, 2),
                                         "unprivileged_userns", "net_admin", False)
        self.assertFalse(self.m.policy_is_needed(snapshot, evidence))
        self.assertTrue(self.m.policy_is_needed(snapshot, replace(evidence, correlated=True)))
        for mutation in (replace(snapshot, enforcing=False), replace(snapshot, restriction=0),
                         replace(snapshot, attachments=("foreign",))):
            self.assertFalse(self.m.policy_is_needed(mutation, replace(evidence, correlated=True)))

    def test_successful_baseline_never_loads_policy(self):
        with tempfile.TemporaryDirectory() as directory:
            executor, runtime = self.runtime(Path(directory), "supported")
            result = self.m.diagnose_namespace(runtime, executor=executor, deadline=time.monotonic() + 10)
            self.assertEqual(result.status, "SUPPORTED")
            self.assertNotIn("policy-load", json.loads(executor.state.read_text())["events"])

    def runtime(self, directory, mode):
        import ci_isolation_runtime
        executor = PolicyFixtureExecutor(directory, mode)
        executor.template_sha256 = hashlib.sha256(executor.policy_template()).hexdigest()
        spec = ci_isolation_runtime.load_runtime_spec(ROOT / "tests/ci-runtime-lock.json")
        runtime = self.m.provision_runtime(spec, executor=executor, deadline=time.monotonic() + 15)
        return executor, runtime

    def test_matching_denial_loads_owned_policy_then_retests_once(self):
        with tempfile.TemporaryDirectory() as directory:
            executor, runtime = self.runtime(Path(directory), "matching")
            result = self.m.diagnose_namespace(runtime, executor=executor, deadline=time.monotonic() + 10)
            self.assertEqual(result.status, "POLICY_NEEDED")
            policy = self.m.arm_policy(runtime, result.evidence, executor=executor, deadline=time.monotonic() + 10)
            events = json.loads(executor.state.read_text())["events"]
            self.assertEqual([event for event in events if event.startswith("probe-")],
                             ["probe-full", "probe-minimal", "probe-full"])
            self.assertTrue(self.m.cleanup_policy(policy, executor=executor, deadline=time.monotonic() + 5))

    def test_missing_attribution_or_foreign_attachment_never_loads(self):
        for mode in ("unrelated", "foreign"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                executor, runtime = self.runtime(Path(directory), mode)
                result = self.m.diagnose_namespace(runtime, executor=executor, deadline=time.monotonic() + 10)
                self.assertEqual(result.status, "BLOCKED")
                self.assertNotIn("policy-load", json.loads(executor.state.read_text())["events"])

    def test_load_or_transition_failure_removes_partial_owned_policy(self):
        for mode in ("load-failure", "transition-failure"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                executor, runtime = self.runtime(Path(directory), mode)
                result = self.m.diagnose_namespace(runtime, executor=executor, deadline=time.monotonic() + 10)
                with self.assertRaises(ValueError) as raised:
                    self.m.arm_policy(runtime, result.evidence, executor=executor, deadline=time.monotonic() + 10)
                self.assertIn(str(raised.exception), ("FIXTURE_TOOL_FAILED", "CI_POLICY_CHILD_UNPROVEN"))
                state = json.loads(executor.state.read_text())
                self.assertFalse(state["policy"])
                self.assertIn("policy-remove", state["events"])

    def test_template_drift_and_broad_binary_path_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            executor, runtime = self.runtime(Path(directory), "matching")
            executor.policy_template = lambda: b"unconfined,"
            evidence = executor.denial_evidence(runtime, time.monotonic() + 5)
            with self.assertRaises(ValueError):
                self.m.arm_policy(runtime, evidence, executor=executor, deadline=time.monotonic() + 10)
            self.assertNotIn("policy-load", json.loads(executor.state.read_text())["events"])
            with self.assertRaises(ValueError):
                self.m.render_policy(b"@BINARY@", runtime.binary.parent / "*", "parent", "child")

    def test_audit_record_must_match_owned_pid_window_and_executable(self):
        self.assertTrue(hasattr(self.m, "match_denial_records"), "audit correlation is absent")
        binary = "/opt/senior-infra-ci/" + "a" * 64 + "/bin/bwrap"
        message = ('apparmor="DENIED" operation="capable" profile="unprivileged_userns" '
                   f'pid=123 comm="bwrap" exe="{binary}" capability=12 capname="net_admin"')
        record = {"MESSAGE": message, "__REALTIME_TIMESTAMP": "1500000"}
        self.assertTrue(self.m.match_denial_records(json.dumps(record).encode(),
                                                   pids=(123,), window=(1., 2.), binary=binary))
        for mutated in (dict(record, MESSAGE=message.replace("pid=123", "pid=124")),
                        dict(record, MESSAGE=message.replace(binary, "/usr/bin/bwrap")),
                        dict(record, MESSAGE=message.replace("net_admin", "unrelated")),
                        dict(record, __REALTIME_TIMESTAMP="3000000")):
            self.assertFalse(self.m.match_denial_records(json.dumps(mutated).encode(),
                                                        pids=(123,), window=(1., 2.), binary=binary))

    def test_load_cancellation_cleans_only_owned_policy_and_reraises(self):
        with tempfile.TemporaryDirectory() as directory:
            executor, runtime = self.runtime(Path(directory), "cancel-load")
            result = self.m.diagnose_namespace(runtime, executor=executor, deadline=time.monotonic() + 10)
            with self.assertRaises(KeyboardInterrupt):
                self.m.arm_policy(runtime, result.evidence, executor=executor, deadline=time.monotonic() + 10)
            self.assertFalse(json.loads(executor.state.read_text())["policy"])

    def test_cleanup_failure_dominates_transition_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            executor, runtime = self.runtime(Path(directory), "cleanup-failure")
            result = self.m.diagnose_namespace(runtime, executor=executor, deadline=time.monotonic() + 10)
            with self.assertRaisesRegex(ValueError, "^CI_POLICY_CLEANUP_FAILED$"):
                self.m.arm_policy(runtime, result.evidence, executor=executor, deadline=time.monotonic() + 10)


if __name__ == "__main__":
    unittest.main()
