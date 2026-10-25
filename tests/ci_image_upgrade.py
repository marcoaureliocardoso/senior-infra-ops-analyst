"""Closed, content-free decisions for ephemeral CI package transactions.

Parsing and policy are deliberately separate from privileged execution.  APT
output is data, never a command source or an authorization to install anything.
"""
from dataclasses import dataclass, replace
import re
import subprocess
import time
from typing import Callable


@dataclass(frozen=True)
class UpgradeAction:
    kind: str
    package: str
    installed_version: str | None
    candidate_version: str | None


@dataclass(frozen=True)
class UpgradeProposal:
    actions: tuple[UpgradeAction, ...]
    held_count: int
    unchanged_packages: tuple[str, ...] = ()


@dataclass(frozen=True)
class UpgradeDecision:
    status: str
    reason: str
    package_count: int


_PACKAGE = re.compile(r"[a-z0-9][a-z0-9+.-]*(?::[a-z0-9][a-z0-9-]*)?", re.ASCII)
_VERSION = re.compile(r"(?:[0-9]+:)?[0-9][A-Za-z0-9.+~\-]*", re.ASCII)
_SUMMARY = re.compile(
    r"(\d+) upgraded, (\d+) newly installed, (\d+) to remove and (\d+) not upgraded\.")
_INST = re.compile(r"Inst (\S+)(?: \[(\S+)\])? \((\S+) [^()\x00-\x1f]+\)")
_CONF = re.compile(r"Conf (\S+) \((\S+) [^()\x00-\x1f]+\)")
_REMV = re.compile(r"Remv (\S+) \[(\S+)\]")
_CURRENT = re.compile(r"(\S+) is already the newest version \((\S+)\)\.")
_HEADERS = {
    "The following packages will be upgraded:": "upgrade",
    "The following NEW packages will be installed:": "install",
    "The following packages will be REMOVED:": "remove",
    "The following packages have been kept back:": "held",
    "The following packages will be DOWNGRADED:": "upgrade",
    "The following upgrades have been deferred due to phasing:": "phased",
    "The following additional packages will be installed:": "additional",
    "Suggested packages:": "suggested",
    "Recommended packages:": "recommended",
    "The following package was automatically installed and is no longer required:": "auto",
    "The following packages were automatically installed and are no longer required:": "auto",
}
_BANNERS = frozenset(
    text + suffix for text in ("Reading package lists...", "Building dependency tree...",
                               "Reading state information...", "Calculating upgrade...")
    for suffix in ("", " Done"))
_PROTECTED = frozenset({"apt", "dpkg", "sudo", "apparmor", "systemd", "udev",
                        "dbus", "openssh-server", "libc6", "libc-bin", "runc",
                        "cloud-init", "walinuxagent"})
_PROTECTED_PREFIXES = ("linux-", "grub", "shim", "initramfs-tools", "libpam",
                       "libnss", "libsystemd", "snapd", "docker", "moby", "containerd")


def _valid_package(value):
    return type(value) is str and len(value) <= 128 and _PACKAGE.fullmatch(value) is not None


def _valid_version(value):
    return type(value) is str and len(value) <= 128 and _VERSION.fullmatch(value) is not None


def parse_apt_simulation(text: str) -> UpgradeProposal:
    """Accept a bounded, internally coherent C-locale simulation or fail closed."""
    if (type(text) is not str or not text or len(text.encode("utf-8")) > 512 * 1024
            or any(ord(char) < 32 and char not in "\n\t" for char in text)):
        raise ValueError("APT_SIMULATION_INVALID")
    lines = text.splitlines()
    if len(lines) > 4096:
        raise ValueError("APT_SIMULATION_INVALID")
    summary = None
    actions, configured, unchanged = {}, {}, []
    lists = {}
    list_kind = None
    advisory_seen = False
    for line in lines:
        if not line.strip():
            list_kind = None
            continue
        if line in _BANNERS:
            list_kind = None
            continue
        if line in _HEADERS:
            list_kind = _HEADERS[line]
            if list_kind in lists:
                raise ValueError("APT_SIMULATION_AMBIGUOUS")
            lists[list_kind] = []
            continue
        if line.startswith("  ") and list_kind:
            packages = line.split()
            if list_kind in ("suggested", "recommended"):
                packages = [name for name in packages if name != "|"]
            if not packages or not all(_valid_package(name) for name in packages):
                raise ValueError("APT_SIMULATION_INVALID")
            lists[list_kind].extend(packages)
            continue
        list_kind = None
        if line in {f"Use '{prefix}apt autoremove' to remove {pronoun}."
                    for prefix in ("", "sudo ") for pronoun in ("it", "them")}:
            # Recognized APT narrative only. NEVER return/execute its command.
            if advisory_seen or not lists.get("auto"):
                raise ValueError("APT_SIMULATION_AMBIGUOUS")
            advisory_seen = True
            continue
        if match := _SUMMARY.fullmatch(line):
            if summary is not None:
                raise ValueError("APT_SIMULATION_AMBIGUOUS")
            summary = tuple(int(number) for number in match.groups())
        elif match := _INST.fullmatch(line):
            name, old, new = match.groups()
            if (not _valid_package(name) or not _valid_version(new)
                    or old is not None and not _valid_version(old) or name in actions):
                raise ValueError("APT_SIMULATION_INVALID")
            actions[name] = UpgradeAction("upgrade" if old else "install", name, old, new)
        elif match := _CONF.fullmatch(line):
            name, version = match.groups()
            if not _valid_package(name) or not _valid_version(version) or name in configured:
                raise ValueError("APT_SIMULATION_INVALID")
            configured[name] = version
        elif match := _REMV.fullmatch(line):
            name, old = match.groups()
            if not _valid_package(name) or not _valid_version(old) or name in actions:
                raise ValueError("APT_SIMULATION_INVALID")
            actions[name] = UpgradeAction("remove", name, old, None)
        elif match := _CURRENT.fullmatch(line):
            name, version = match.groups()
            if not _valid_package(name) or not _valid_version(version) or name in unchanged:
                raise ValueError("APT_SIMULATION_INVALID")
            unchanged.append(name)
        else:
            raise ValueError("APT_SIMULATION_UNRECOGNIZED")
    if summary is None or set(unchanged) & set(actions):
        raise ValueError("APT_SIMULATION_AMBIGUOUS")
    expected = {name: action.candidate_version for name, action in actions.items()
                if action.kind != "remove"}
    counts = tuple(sum(action.kind == kind for action in actions.values())
                   for kind in ("upgrade", "install", "remove"))
    if configured != expected or counts != summary[:3]:
        raise ValueError("APT_SIMULATION_DRIFT")
    for kind, names in lists.items():
        expected_names = {name for name, action in actions.items() if action.kind == kind}
        if len(names) != len(set(names)):
            raise ValueError("APT_SIMULATION_DRIFT")
        if kind in ("upgrade", "install", "remove") and set(names) != expected_names:
            raise ValueError("APT_SIMULATION_DRIFT")
        if kind == "additional" and not set(names) <= set(expected):
            raise ValueError("APT_SIMULATION_DRIFT")
        if kind == "auto" and set(names) & set(actions):
            raise ValueError("APT_SIMULATION_DRIFT")
    pending = lists.get("held", []) + lists.get("phased", [])
    if pending and (len(pending) != len(set(pending)) or len(pending) != summary[3]):
        raise ValueError("APT_SIMULATION_DRIFT")
    return UpgradeProposal(tuple(actions.values()), summary[3], tuple(unchanged))


def compare_debian_versions(left: str, right: str) -> int:
    if not _valid_version(left) or not _valid_version(right):
        raise ValueError("DEBIAN_VERSION_INVALID")
    try:
        for relation, answer in (("lt", -1), ("gt", 1)):
            result = subprocess.run(
                ["/usr/bin/dpkg", "--compare-versions", left, relation, right],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"}, timeout=5, check=False)
            if result.returncode == 0:
                return answer
            if result.returncode != 1:
                raise ValueError("DEBIAN_COMPARATOR_UNAVAILABLE")
    except (OSError, subprocess.SubprocessError) as from_error:
        raise ValueError("DEBIAN_COMPARATOR_UNAVAILABLE") from from_error
    return 0


def _assess(proposal, services, compare_versions, *, dependency, requested, reboot):
    blocked = UpgradeDecision("BLOCKED", "PACKAGE_FACTS_UNPROVEN", 0)
    if (type(proposal) is not UpgradeProposal or type(proposal.actions) is not tuple
            or type(proposal.held_count) is not int or proposal.held_count < 0
            or type(proposal.unchanged_packages) is not tuple
            or type(services) is not frozenset or not all(_valid_package(x) for x in services)
            or type(reboot) is not bool or not callable(compare_versions)
            or type(requested) is not frozenset or not all(_valid_package(x) for x in requested)):
        return blocked
    known = set(proposal.unchanged_packages)
    if not all(_valid_package(name) for name in known) or len(known) != len(proposal.unchanged_packages):
        return blocked
    unsafe = reboot or proposal.held_count > 0
    for action in proposal.actions:
        if (type(action) is not UpgradeAction or not _valid_package(action.package)
                or action.package in known or action.kind not in ("install", "upgrade", "remove")
                or (action.kind != "install" and not _valid_version(action.installed_version))
                or (action.kind != "remove" and not _valid_version(action.candidate_version))
                or (action.kind == "install" and action.installed_version is not None)
                or (action.kind == "remove" and action.candidate_version is not None)):
            return blocked
        known.add(action.package)
        base = action.package.partition(":")[0]
        unsafe |= (action.kind == "remove" or (action.kind == "install" and not dependency)
                   or base in _PROTECTED or base.startswith(_PROTECTED_PREFIXES)
                   or action.package in services or base in services)
        if action.kind == "upgrade":
            try:
                order = compare_versions(action.candidate_version, action.installed_version)
            except Exception:
                return blocked
            if type(order) is not int or order not in (-1, 0, 1):
                return blocked
            unsafe |= order <= 0
    if dependency and (not requested or not requested <= known):
        return blocked
    if unsafe:
        return UpgradeDecision("BLOCKED" if dependency else "SKIP_UNSAFE",
                               "PACKAGE_EFFECT_OUTSIDE_SCOPE", len(proposal.actions))
    return UpgradeDecision("ALLOW" if proposal.actions else "UP_TO_DATE",
                           "PACKAGE_PROPOSAL_SAFE", len(proposal.actions))


def assess_upgrade(proposal, *, reboot_required: bool, service_packages: frozenset[str],
                   compare_versions: Callable[[str, str], int]) -> UpgradeDecision:
    return _assess(proposal, service_packages, compare_versions,
                   dependency=False, requested=frozenset(), reboot=reboot_required)


def assess_dependency_install(proposal, *, requested: frozenset[str],
                              service_packages: frozenset[str], compare_versions) -> UpgradeDecision:
    return _assess(proposal, service_packages, compare_versions,
                   dependency=True, requested=requested, reboot=False)


def prepare_image_packages(adapter, *, deadline):
    """Run fixed stages. A skipped general upgrade is not a failed transaction.

    The private adapter freezes signed lists/archives, performs bounded metadata
    inspection and verifies the installed state. No adapter comes from CLI data.
    """
    deadline = min(deadline, time.monotonic() + 600)

    def check():
        if time.monotonic() >= deadline:
            raise ValueError("PACKAGE_PROVISIONING_DEADLINE")

    check()
    adapter.refresh(deadline)
    general = None
    for kind in ("upgrade", "dependencies"):
        check()
        before = adapter.snapshot(deadline)
        proposal = parse_apt_simulation(adapter.simulate(kind, deadline))
        services = adapter.service_packages(proposal, deadline)
        held = adapter.held_packages(deadline)
        if type(held) is not frozenset or not all(_valid_package(name) for name in held):
            raise ValueError("PACKAGE_HOLDS_UNPROVEN")
        if any(action.package in held or action.package.partition(":")[0] in held
               for action in proposal.actions):
            if kind == "dependencies":
                raise ValueError("PACKAGE_HOLD_CHANGE_REJECTED")
            general = UpgradeDecision("SKIP_UNSAFE", "PACKAGE_HOLD_CHANGE_REJECTED", len(proposal.actions))
            continue

        def decide():
            if kind == "upgrade":
                return assess_upgrade(proposal, reboot_required=adapter.reboot_required,
                                      service_packages=services,
                                      compare_versions=compare_debian_versions)
            # APT's "not upgraded" is not synonymous with an explicit dpkg hold.
            # Unrelated pending updates must not prevent safe build dependencies.
            return assess_dependency_install(replace(proposal, held_count=0), requested=adapter.requested,
                                             service_packages=services,
                                             compare_versions=compare_debian_versions)

        decision = decide()
        if kind == "upgrade":
            general = decision
        if decision.status == "BLOCKED":
            raise ValueError("PACKAGE_PROPOSAL_BLOCKED")
        if decision.status in ("UP_TO_DATE", "SKIP_UNSAFE"):
            if adapter.snapshot(deadline) != before:
                raise ValueError("PACKAGE_STATE_CHANGED")
            continue
        if len(proposal.actions) > 500:
            raise ValueError("PACKAGE_PROPOSAL_TOO_LARGE")
        adapter.freeze(kind, proposal, deadline)
        # Candidate archives are now present: check candidate service metadata as
        # well as the installed files checked before downloading anything.
        services = adapter.service_packages(proposal, deadline)
        if decide().status != "ALLOW":
            raise ValueError("PACKAGE_CANDIDATE_UNSAFE")
        if (parse_apt_simulation(adapter.simulate(kind, deadline)) != proposal
                or adapter.snapshot(deadline) != before or adapter.held_packages(deadline) != held):
            raise ValueError("PACKAGE_PROPOSAL_DRIFT")
        check()
        adapter.apply(kind, proposal, deadline)
        adapter.verify_changes(before, proposal, deadline)
        check()
    return general
