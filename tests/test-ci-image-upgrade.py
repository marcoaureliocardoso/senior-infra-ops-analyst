"""Provider-free tests of closed CI package transaction policy."""
import importlib
from pathlib import Path
import unittest


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
