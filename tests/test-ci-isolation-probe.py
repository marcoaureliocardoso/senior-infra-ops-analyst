"""Closed proof controls and fixed no-provider namespace fixtures."""
from dataclasses import asdict
import importlib
from pathlib import Path
import shutil
import time
import types
import tempfile
import unittest


class IsolationProofTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(Path(__file__).with_name("ci_isolation_probe.py").is_file(),
                        "strong isolation proof is absent")
        self.m = importlib.import_module("ci_isolation_probe")

    def test_every_proof_condition_is_mandatory_and_boolean(self):
        valid = {key: True for key in ("namespace", "network", "mount", "process", "privilege", "policy", "cleanup")}
        self.assertEqual(asdict(self.m.validate_proof(valid)), valid)
        for key in valid:
            for value in (False, 1, None, "true"):
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    self.m.validate_proof(dict(valid, **{key: value}))
        for record in ({}, dict(valid, extra=True)):
            with self.assertRaises(ValueError):
                self.m.validate_proof(record)

    def test_real_fixed_probe_and_negative_controls(self):
        binary = shutil.which("bwrap")
        self.assertIsNotNone(binary, "required namespace runtime is missing")
        runtime = types.SimpleNamespace(binary=Path(binary))
        try:
            proof = self.m.run_isolation_proof(runtime, None, deadline=time.monotonic() + 30)
        except ValueError as error:
            self.fail((str(error), getattr(error, "fields", ())))
        self.assertTrue(all(asdict(proof).values()))
        # These internal test controls cannot be selected by the bootstrap CLI.
        for control in ("ipc", "uts", "pid", "net", "writable-readonly"):
            with self.subTest(control=control), self.assertRaises(ValueError) as raised:
                self.m._run_proof(Path(binary), None, deadline=time.monotonic() + 15,
                                  negative_control=control)
            self.assertEqual(str(raised.exception), "CI_ISOLATION_PROOF_REJECTED")
            self.assertIn("mount" if control == "writable-readonly" else "namespace", raised.exception.fields)

    def test_expired_proof_does_not_spawn(self):
        with self.assertRaises(ValueError):
            self.m._run_proof(Path("/does-not-exist"), None, deadline=time.monotonic() - 1)

    def test_policy_attestation_requires_the_exact_two_enforced_stack_components(self):
        parent = "senior-infra-ci-" + "a" * 24
        child = parent + "-child"
        names = [parent, child]
        self.assertTrue(hasattr(self.m, "policy_label_matches"), "exact label parser is absent")
        for label, expected in (
            (parent + "//&" + child + " (enforce)", True),
            (child + " (enforce)", False), (parent + " (enforce)", False),
            (parent + "//&" + child + "-foreign (enforce)", False),
            (parent + "//&" + child + "//&foreign (enforce)", False),
            (parent + "//&" + child + " (complain)", False),
            (parent + "//&" + parent + " (enforce)", False),
        ):
            with self.subTest(label=label):
                self.assertEqual(self.m.policy_label_matches(label, names), expected)

    def test_kernel_reject_sentinel_is_not_a_usable_ipv6_default_route(self):
        self.assertTrue(hasattr(self.m, "routes_are_isolated"), "route viability parser is absent")
        sentinel = "0" * 32 + " 00 " + "0" * 32 + " 00 " + "0" * 32 + " ffffffff 00000001 00000000 00200200 lo\n"
        self.assertTrue(self.m.routes_are_isolated("", sentinel))
        self.assertFalse(self.m.routes_are_isolated("", sentinel.replace("00200200", "00000001")))
        self.assertFalse(self.m.routes_are_isolated("", sentinel.replace(" lo", " eth0")))
        self.assertFalse(self.m.routes_are_isolated("", "malformed"))

    def test_timeout_reaps_owned_child_before_returning(self):
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / "synthetic-slow-child"
            binary.write_text("#!/usr/bin/python3\nimport time\ntime.sleep(5)\n", encoding="ascii")
            binary.chmod(0o755)
            start = time.monotonic()
            with self.assertRaisesRegex(ValueError, "^CI_ISOLATION_PROOF_BOUNDED_FAILURE$"):
                self.m._run_proof(binary, None, deadline=start + 0.2)
            self.assertLess(time.monotonic() - start, 2)


if __name__ == "__main__":
    unittest.main()
