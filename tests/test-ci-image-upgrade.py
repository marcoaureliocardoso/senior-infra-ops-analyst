"""Provider-free tests of closed CI package transaction policy."""
import importlib
from pathlib import Path
import unittest
import time


def upgrade(package="demo", old="1.0-1", new="1.1-1", held=0):
    return (f"1 upgraded, 0 newly installed, 0 to remove and {held} not upgraded.\n"
            f"Inst {package} [{old}] ({new} Ubuntu:24.04/noble-updates [amd64])\n"
            f"Conf {package} ({new} Ubuntu:24.04/noble-updates [amd64])\n")


INSTALL = ("0 upgraded, 1 newly installed, 0 to remove and 0 not upgraded.\n"
           "Inst build-demo (1.0 Ubuntu:24.04/noble [amd64])\n"
           "Conf build-demo (1.0 Ubuntu:24.04/noble [amd64])\n")


class ImageUpgradeTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(Path(__file__).with_name("ci_image_upgrade.py").is_file(),
                        "closed package transaction policy is not implemented")
        self.m = importlib.import_module("ci_image_upgrade")

    def decision(self, text, *, services=frozenset(), reboot=False, comparator=None):
        return self.m.assess_upgrade(
            self.m.parse_apt_simulation(text), reboot_required=reboot,
            service_packages=services,
            compare_versions=comparator or self.m.compare_debian_versions,
        )

    def test_safe_transaction_is_allowed(self):
        text = ("Reading package lists...\nBuilding dependency tree...\n"
                "Reading state information...\nCalculating upgrade...\n"
                "The following packages will be upgraded:\n  demo\n" + upgrade())
        result = self.decision(text)
        self.assertEqual((result.status, result.package_count), ("ALLOW", 1))
        proposal = self.m.parse_apt_simulation(text)
        self.assertEqual(proposal.actions[0].package, "demo")
        with self.assertRaises(AttributeError):
            proposal.held_count = 1

    def test_no_updates_is_not_an_upgrade(self):
        result = self.decision("0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.\n")
        self.assertEqual((result.status, result.package_count), ("UP_TO_DATE", 0))

    def test_first_unrecognized_line_reports_only_bounded_structural_scalars(self):
        cases = [('Inst demo (2 src) []', 'INST_SUFFIX', 20),
                 ('Conf demo (2 src) []', 'CONF_SUFFIX', 20),
                 ('Remv demo [1] []', 'REMV_SUFFIX', 16),
                 ('Inst unknown', 'INST_OTHER', 12),
                 ('Conf unknown', 'CONF_OTHER', 12),
                 ('Remv unknown', 'REMV_OTHER', 12),
                 ('0 upgraded, unexpected', 'SUMMARY_VARIANT', 22),
                 ('N: demo', 'NOTICE', 7), ('W: demo', 'WARNING', 7),
                 ('The following held packages will be changed:', 'HELD_CHANGE_HEADER', 44),
                 ('Unmodelled header:', 'HEADER', 18), ('Unmodelled text', 'OTHER', 15)]
        for line, kind, length in cases:
            with self.subTest(kind=kind):
                with self.assertRaises(ValueError) as caught:
                    self.m.parse_apt_simulation('\n' + line + '\nN: later\n')
                self.assertEqual(type(caught.exception), ValueError)
                self.assertEqual(caught.exception.args, ('APT_SIMULATION_UNRECOGNIZED', kind, 2, length))
                self.assertNotIn(line, repr(caught.exception.args))

    def test_rejection_position_and_length_remain_within_existing_input_bounds(self):
        with self.assertRaises(ValueError) as caught:
            self.m.parse_apt_simulation('\n' * 4095 + 'x')
        self.assertEqual(caught.exception.args, ('APT_SIMULATION_UNRECOGNIZED', 'OTHER', 4096, 1))
        with self.assertRaises(ValueError) as caught:
            self.m.parse_apt_simulation('x' * (512 * 1024))
        self.assertEqual(caught.exception.args, ('APT_SIMULATION_UNRECOGNIZED', 'OTHER', 1, 524288))

    def test_new_service_in_frozen_general_candidate_skips_and_continues_dependencies(self):
        class Adapter:
            requested = frozenset({'build-demo'})
            reboot_required = False
            def __init__(self, drift=None, unsafe_dependencies=False):
                self.frozen = set(); self.events = []; self.generation = 0
                self.drift, self.unsafe_dependencies = drift, unsafe_dependencies
            def refresh(self, deadline): self.events.append('refresh')
            def snapshot(self, deadline):
                return self.generation + (1 if self.drift == 'state' and 'upgrade' in self.frozen else 0)
            def held_packages(self, deadline):
                return frozenset({'changed-hold'}) if self.drift == 'holds' and self.frozen else frozenset()
            def simulate(self, kind, deadline):
                self.events.append('simulate-'+kind)
                text = upgrade() if kind == 'upgrade' else INSTALL
                return text.replace('1.1-1', '1.2-1') if self.drift == 'proposal' and kind in self.frozen else text
            def service_packages(self, proposal, deadline):
                if proposal.actions[0].package == 'demo':
                    return frozenset({'demo'}) if 'upgrade' in self.frozen else frozenset()
                return frozenset({'build-demo'}) if self.unsafe_dependencies and 'dependencies' in self.frozen else frozenset()
            def freeze(self, kind, proposal, deadline): self.frozen.add(kind); self.events.append('freeze-'+kind)
            def apply(self, kind, proposal, deadline): self.events.append('apply-'+kind); self.generation += 1
            def verify_changes(self, before, proposal, deadline):
                if self.generation != before + 1: raise ValueError('PACKAGE_POSTCONDITION_FAILED')
        adapter = Adapter()
        result = self.m.prepare_image_packages(adapter, deadline=time.monotonic()+5)
        self.assertEqual(result.status, 'SKIP_UNSAFE')
        self.assertIn('freeze-upgrade', adapter.events)
        self.assertNotIn('apply-upgrade', adapter.events)
        self.assertIn('apply-dependencies', adapter.events)
        for drift in ('state', 'holds', 'proposal'):
            adapter = Adapter(drift=drift)
            with self.subTest(drift=drift), self.assertRaisesRegex(ValueError, 'PACKAGE_PROPOSAL_DRIFT'):
                self.m.prepare_image_packages(adapter, deadline=time.monotonic()+5)
            self.assertFalse(any(e.startswith('apply-') for e in adapter.events))
        adapter = Adapter(unsafe_dependencies=True)
        with self.assertRaisesRegex(ValueError, 'PACKAGE_CANDIDATE_UNSAFE'):
            self.m.prepare_image_packages(adapter, deadline=time.monotonic()+5)
        self.assertNotIn('apply-dependencies', adapter.events)

    def test_general_upgrade_refuses_effects_outside_safe_scope(self):
        cases = [
            (upgrade(new="0.9-1"), frozenset(), False),
            (upgrade(held=1), frozenset(), False),
            (upgrade(), frozenset(), True),
            (upgrade(), frozenset({"demo"}), False),
            (INSTALL, frozenset(), False),
            ("0 upgraded, 0 newly installed, 1 to remove and 0 not upgraded.\n"
             "Remv demo [1.0]\n", frozenset(), False),
        ]
        for text, services, reboot in cases:
            with self.subTest(text=text.splitlines()[0], services=bool(services), reboot=reboot):
                self.assertEqual(self.decision(text, services=services, reboot=reboot).status,
                                 "SKIP_UNSAFE")

    def test_all_protected_package_families_remain_unmodified(self):
        for name in ("apt", "dpkg", "sudo", "apparmor", "systemd", "udev", "dbus",
                     "openssh-server", "libc6:amd64", "libc-bin", "linux-image-demo",
                     "grub-demo", "shim-demo", "initramfs-tools-core", "libpam-demo",
                     "libnss-demo", "libsystemd0", "snapd", "docker-ce", "moby-engine",
                     "containerd.io", "runc", "cloud-init", "walinuxagent"):
            with self.subTest(package=name):
                self.assertEqual(self.decision(upgrade(package=name)).status, "SKIP_UNSAFE")

    def test_new_explicit_build_dependency_is_not_a_general_upgrade(self):
        proposal = self.m.parse_apt_simulation(INSTALL)
        result = self.m.assess_dependency_install(
            proposal, requested=frozenset({"build-demo"}), service_packages=frozenset(),
            compare_versions=self.m.compare_debian_versions,
        )
        self.assertEqual(result.status, "ALLOW")
        for requested, services in ((frozenset({"missing-demo"}), frozenset()),
                                    (frozenset({"build-demo"}), frozenset({"build-demo"}))):
            self.assertEqual(self.m.assess_dependency_install(
                proposal, requested=requested, service_packages=services,
                compare_versions=self.m.compare_debian_versions,
            ).status, "BLOCKED")

    def test_protected_dependency_and_removal_cannot_enter_targeted_install(self):
        for text in (upgrade(package="apparmor"),
                     "0 upgraded, 0 newly installed, 1 to remove and 0 not upgraded.\nRemv demo [1.0]\n"):
            proposal = self.m.parse_apt_simulation(text)
            self.assertEqual(self.m.assess_dependency_install(
                proposal, requested=frozenset({proposal.actions[0].package}),
                service_packages=frozenset(), compare_versions=self.m.compare_debian_versions,
            ).status, "BLOCKED")

    def test_targeted_request_must_be_changed_or_explicitly_current(self):
        text = ("ready-demo is already the newest version (1.0).\n"
                "0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.\n")
        proposal = self.m.parse_apt_simulation(text)
        self.assertEqual(proposal.unchanged_packages, ("ready-demo",))
        for requested, status in ((frozenset({"ready-demo"}), "UP_TO_DATE"),
                                  (frozenset({"missing-demo"}), "BLOCKED")):
            self.assertEqual(self.m.assess_dependency_install(
                proposal, requested=requested, service_packages=frozenset(),
                compare_versions=self.m.compare_debian_versions,
            ).status, status)

    def test_malformed_or_ambiguous_simulations_are_rejected(self):
        base = upgrade()
        cases = ["", " ", base + "Exec unmodelled-command\n", base + base,
                 base.replace("1 upgraded", "2 upgraded"),
                 base.replace("Conf demo (1.1-1", "Conf demo (1.2-1"),
                 base + "Conf demo (1.1-1 Ubuntu [amd64])\n",
                 base.replace("Inst demo", "Inst --demo"),
                 base.replace("1.1-1", "--force"),
                 base.replace("1.1-1", "1:2:3"),
                 base.replace("Inst demo", "Inst demo;action"),
                 base + "\x00", "x" * (512 * 1024 + 1),
                 "Reading package lists...\n" * 4097]
        for index, text in enumerate(cases):
            with self.subTest(index=index), self.assertRaises(ValueError):
                self.m.parse_apt_simulation(text)

    def test_missing_configuration_confirmation_is_rejected(self):
        with self.assertRaises(ValueError):
            self.m.parse_apt_simulation(upgrade().split("Conf")[0])

    def test_standard_auxiliary_apt_lists_are_data_not_selected_actions(self):
        text = ("The following packages were automatically installed and are no longer required:\n"
                "  old-demo\nUse 'sudo apt autoremove' to remove them.\n"
                "The following additional packages will be installed:\n  build-demo\n"
                "Suggested packages:\n  doc-demo | doc-other\nRecommended packages:\n  optional-demo\n"
                "The following NEW packages will be installed:\n  build-demo\n" + INSTALL)
        proposal = self.m.parse_apt_simulation(text)
        self.assertEqual(tuple(action.package for action in proposal.actions), ("build-demo",))
        self.assertEqual(self.m.assess_dependency_install(proposal, requested=frozenset({"build-demo"}),
                         service_packages=frozenset(), compare_versions=self.m.compare_debian_versions).status, "ALLOW")
        with self.assertRaises(ValueError):
            self.m.parse_apt_simulation(text.replace("sudo apt autoremove", "sudo apt autoremove; unmodelled"))

    def test_deferred_phasing_and_kept_lists_share_the_pending_count(self):
        text = ("The following upgrades have been deferred due to phasing:\n  later-demo\n"
                "The following packages have been kept back:\n  held-demo\n"
                "0 upgraded, 0 newly installed, 0 to remove and 2 not upgraded.\n")
        self.assertEqual(self.decision(text).status, "SKIP_UNSAFE")

    def test_native_manual_mark_is_bounded_data_for_an_explicit_current_package(self):
        text = ("build-demo is already the newest version (1.0).\n"
                "build-demo set to manually installed.\n"
                "0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.\n")
        proposal = self.m.parse_apt_simulation(text)
        self.assertEqual(proposal.unchanged_packages, ("build-demo",))
        self.assertEqual(proposal.actions, ())
        for invalid in (text + "build-demo set to manually installed.\n",
                        text.replace("build-demo set", "unknown-demo set"),
                        text.replace("build-demo set", "--option set")):
            with self.assertRaises(ValueError):
                self.m.parse_apt_simulation(invalid)

    def test_native_mixed_phasing_notice_requires_both_complete_lists(self):
        text = ("The following upgrades have been deferred due to phasing:\n  later-demo\n"
                "The following packages have been kept back:\n  held-demo\n"
                "0 upgraded, 0 newly installed, 0 to remove and 2 not upgraded.\n"
                "N: Some packages may have been kept back due to phasing.\n")
        self.assertEqual(self.decision(text).status, "SKIP_UNSAFE")
        for invalid in (text + "N: Some packages may have been kept back due to phasing.\n",
                        text.replace("  later-demo\n", ""), text + "N: unmodelled notice\n"):
            with self.assertRaises(ValueError):
                self.m.parse_apt_simulation(invalid)

    def test_comparison_failures_and_invalid_fact_types_block(self):
        def unavailable(_left, _right):
            raise OSError("synthetic comparator failure")
        self.assertEqual(self.decision(upgrade(), comparator=unavailable).status, "BLOCKED")
        self.assertEqual(self.decision(upgrade(), comparator=lambda a, b: True).status, "BLOCKED")
        self.assertEqual(self.decision(upgrade(), services=None).status, "BLOCKED")
        self.assertEqual(self.decision(upgrade(), reboot=1).status, "BLOCKED")

    def test_debian_comparison_is_not_lexical_and_never_accepts_options(self):
        self.assertGreater(self.m.compare_debian_versions("2:0.1-1", "1:99.0-9"), 0)
        self.assertLess(self.m.compare_debian_versions("1.0~rc1", "1.0"), 0)
        self.assertEqual(self.m.compare_debian_versions("1.0-1", "1.0-1"), 0)
        for value in ("--help", "1;action", "", "1:2:3"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.m.compare_debian_versions(value, "1.0")


if __name__ == "__main__":
    unittest.main()
