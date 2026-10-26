"""Fixed Linux transport for the reviewed ephemeral hosted-runner bootstrap.

No production entry point accepts an executor, package name, command, URL,
binary override or policy path. This module is imported only by the closed CLI.
"""
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import signal
import stat
import subprocess
import tempfile
import time
import urllib.request

from ci_image_upgrade import (
    _valid_package, _valid_version, prepare_image_packages,
)
from ci_isolation_runtime import (
    BuildReceipt, OwnedRuntime, _read_binary, extract_verified_archive,
    verify_installed_runtime,
)


ROOT = Path(__file__).resolve().parents[1]
PREFIX_BASE = Path("/var/lib/senior-infra-ci")
CACHE_BASE = Path("/var/cache/senior-infra-ci")
DEPENDENCIES = frozenset({"gcc", "meson", "ninja-build", "pkgconf", "libcap-dev",
                          "libcap2-bin", "python3", "xz-utils", "ca-certificates"})


class LinuxExecutor:
    prefix_base = PREFIX_BASE
    owner_uid = 0

    def __init__(self, spec, workspace, nonce, template_sha256):
        self.spec, self.workspace, self.nonce = spec, workspace, nonce
        self.template_sha256 = template_sha256
        self.cache = CACHE_BASE / spec.source_sha256
        self.upgrade_decision = None
        self.runtime = None
        self.cache_owned = False
        self.probe_records = []
        self.owned_policy = None

    def command(self, argv, deadline, *, privileged=False, limit=512 * 1024):
        remaining = min(120, deadline - time.monotonic())
        private_binary = str(self.runtime.binary) if self.runtime else None
        if remaining <= 0 or not argv or not (str(argv[0]).startswith("/usr/") or str(argv[0]) == private_binary):
            raise ValueError("CI_COMMAND_SCOPE_REJECTED")
        argv = [str(arg) for arg in argv]
        if any("\x00" in arg or len(arg) > 4096 for arg in argv):
            raise ValueError("CI_COMMAND_SCOPE_REJECTED")
        env = {"PATH": (str(self.runtime.binary.parent) + ":" if self.runtime else "") + "/usr/bin:/bin",
               "LC_ALL": "C", "HOME": str(self.workspace),
               "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1",
               "DEBIAN_FRONTEND": "noninteractive", "NEEDRESTART_MODE": "l"}
        if privileged:
            # sudo env_reset must not strip the fixed package safety settings.
            # Re-establish only this closed environment after elevation; never
            # preserve caller-supplied variables or executable-resolution paths.
            settings = {**env, "PATH": "/usr/sbin:/usr/bin:/sbin:/bin"}
            argv = ["/usr/bin/sudo", "-n", "/usr/bin/env",
                    *(f"{key}={value}" for key, value in settings.items()),
                    "/usr/bin/timeout", "--kill-after=5s", f"{remaining:.3f}s", *argv]
        with tempfile.TemporaryFile(dir=self.workspace) as output:
            process = subprocess.Popen(argv, cwd=self.workspace, env=env,
                                       stdin=subprocess.DEVNULL, stdout=output,
                                       stderr=subprocess.STDOUT, start_new_session=True)
            try:
                while process.poll() is None:
                    if time.monotonic() >= deadline or output.tell() > limit:
                        raise ValueError("CI_COMMAND_BOUNDED_FAILURE")
                    time.sleep(0.05)
                if process.returncode or output.tell() > limit:
                    raise ValueError("CI_COMMAND_FAILED")
                output.seek(0)
                return output.read(limit + 1)
            finally:
                if process.poll() is None:
                    try:
                        os.killpg(process.pid, signal.SIGTERM)
                        process.wait(timeout=6)
                    except (ProcessLookupError, PermissionError, subprocess.TimeoutExpired):
                        try:
                            os.killpg(process.pid, signal.SIGKILL)
                        except (ProcessLookupError, PermissionError):
                            pass
                        process.wait(timeout=remaining + 6)

    def root_action(self, action, deadline, *args):
        return self.command(["/usr/bin/python3", "-I", "-B",
                             str(ROOT / "tests/ci_isolation_root.py"), action,
                             str(ROOT / "tests/ci-runtime-lock.json"), self.nonce,
                             *map(str, args)], deadline, privileged=True)

    def prepare_packages(self, deadline):
        self.root_action("cache-create", deadline)
        self.cache_owned = True
        self.upgrade_decision = prepare_image_packages(LinuxPackageAdapter(self), deadline=deadline)

    def build_candidate(self, spec, deadline):
        if platform.machine() != spec.architecture:
            raise ValueError("RUNTIME_ARCHITECTURE_UNSUPPORTED")
        # TLS and the exact URL are necessary but not sufficient: the local
        # reviewed size and digest, never a downloaded sidecar, are authoritative.
        request = urllib.request.Request(spec.source_url, headers={"User-Agent": "senior-infra-ci"})
        with urllib.request.urlopen(request, timeout=min(30, max(1, deadline - time.monotonic()))) as response:
            data = response.read(spec.source_size + 1)
        source = self.workspace / "source"
        extract_verified_archive(data, spec, source)
        build = self.workspace / "build"
        self.command(["/usr/bin/meson", "setup", str(build),
                      str(source / f"bubblewrap-{spec.version}"), *spec.build_options], deadline)
        self.command(["/usr/bin/ninja", "-C", str(build), "bwrap"], deadline)
        candidate = build / "bwrap"
        _read_binary(candidate, os.getuid())
        return candidate

    def install_candidate(self, candidate, prefix, receipt, deadline):
        # A small runner-owned request carries hashes only. The root worker
        # independently derives/validates every privileged target.
        request = self.workspace / "install-request.json"
        with request.open("x", encoding="ascii") as stream:
            json.dump(asdict(receipt), stream)
        result = self.root_action("runtime-install", deadline, candidate, request)
        record = json.loads(result)
        record["build_options"] = tuple(record["build_options"])
        record["prefix_identity"] = tuple(record["prefix_identity"])
        record["binary_identity"] = tuple(record["binary_identity"])
        self.runtime = OwnedRuntime(prefix, prefix / "bin/bwrap", BuildReceipt(**record))
        return self.runtime

    def publish(self, runtime):
        verify_installed_runtime(runtime)
        self.runtime = runtime  # CLI publishes PATH only after namespace diagnosis too.

    def cleanup_owned(self, runtime, deadline):
        return self.root_action("runtime-cleanup", deadline).strip() == b"CLEAN"

    def cleanup_cache(self, deadline):
        if not self.cache_owned:
            return True
        return self.root_action("cache-cleanup", deadline).strip() == b"CLEAN"

    @staticmethod
    def namespace_argv(runtime, kind):
        if kind not in ("full", "minimal"):
            raise ValueError("CI_PROBE_SCOPE_REJECTED")
        argv = [str(runtime.binary), "--die-with-parent", "--new-session", "--unshare-user"]
        if kind == "full":
            argv += ["--unshare-pid", "--unshare-ipc", "--unshare-uts"]
        return argv + ["--unshare-net", "--cap-drop", "ALL", "--ro-bind", "/usr", "/usr",
                       "--symlink", "usr/bin", "/bin", "--symlink", "usr/lib", "/lib",
                       "--symlink", "usr/lib64", "/lib64", "--proc", "/proc", "--dev", "/dev",
                       "--clearenv", "--setenv", "PATH", "/usr/bin:/bin", "/usr/bin/true"]

    def namespace_probe(self, runtime, kind, deadline):
        verify_installed_runtime(runtime)
        started = time.time()
        pids, labels = set(), set()
        with tempfile.TemporaryFile(dir=self.workspace) as output:
            process = subprocess.Popen(self.namespace_argv(runtime, kind), cwd=self.workspace,
                                       stdin=subprocess.DEVNULL, stdout=output, stderr=output,
                                       env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"}, start_new_session=True)
            try:
                while True:
                    # Inspect only this owned child and descendants linked from
                    # it. Never enumerate the host process table/operator state.
                    pending, seen = [process.pid], set()
                    while pending and len(seen) < 128:
                        pid = pending.pop()
                        if pid in seen:
                            continue
                        seen.add(pid)
                        base = Path("/proc") / str(pid)
                        try:
                            if os.readlink(base / "exe") == str(runtime.binary):
                                pids.add(pid)
                                labels.add((base / "attr/current").read_text()[:512].strip())
                            children = (base / f"task/{pid}/children").read_text().split()
                            pending.extend(int(value) for value in children if value.isdecimal())
                        except (OSError, ValueError):
                            pass
                    if process.poll() is not None:
                        break
                    if time.monotonic() >= deadline or output.tell() > 65536:
                        raise ValueError("CI_NAMESPACE_PROBE_BOUNDED_FAILURE")
                    time.sleep(0.001)
                return process.returncode == 0
            finally:
                if process.poll() is None:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    process.wait(timeout=5)
                self.probe_records.append((started, time.time(), tuple(sorted(pids)), tuple(sorted(labels))))

    def snapshot_policy(self, runtime, deadline):
        from ci_isolation_bootstrap import PolicySnapshot
        enabled = Path("/sys/module/apparmor/parameters/enabled").read_text().strip() == "Y"
        restriction = Path("/proc/sys/kernel/apparmor_restrict_unprivileged_userns").read_text().strip()
        if restriction not in ("0", "1"):
            raise ValueError("CI_POLICY_STATE_UNPROVEN")
        labels = {label for record in self.probe_records for label in record[3]}
        foreign = tuple(sorted(label for label in labels
                               if label not in ("unconfined", "unprivileged_userns (enforce)")))
        return PolicySnapshot(enabled, int(restriction), foreign)

    def denial_evidence(self, runtime, deadline):
        from ci_isolation_bootstrap import DenialEvidence
        records = self.probe_records[:2]
        if not records:
            raise ValueError("CI_POLICY_EVIDENCE_MISSING")
        pids = tuple(sorted({pid for record in records for pid in record[2]}))
        window = (records[0][0], records[-1][1])
        request = json.dumps({"pids": pids, "window": window}, separators=(",", ":"))
        response = json.loads(self.root_action("audit-read", deadline, request))
        return DenialEvidence(runtime.receipt.binary_sha256, window, "unprivileged_userns",
                              "net_admin", response == {"matched": True})

    def policy_template(self):
        from ci_isolation_bootstrap import load_policy_template
        return load_policy_template(ROOT / "tests/ci-runtime-lock.json")

    def load_policy(self, runtime, policy, deadline):
        self.root_action("policy-load", deadline)

    def remove_policy(self, policy, deadline):
        result = self.root_action("policy-cleanup", deadline).strip() == b"CLEAN"
        if result:
            self.owned_policy = None
        return result

    def verify_child_transition(self, runtime, policy, deadline):
        # The full child proof is implemented by the same fixed fixture used by
        # --verify, rather than trusting only a profile name or successful load.
        from ci_isolation_probe import verify_isolation
        return verify_isolation(runtime, executor=self, policy=policy, deadline=deadline) is True


def archive_package_identity(metadata):
    required = {"Package", "Version", "Architecture"}
    if (not required <= metadata.keys() or metadata.keys() - required - {"Multi-Arch"}
            or not _valid_package(metadata["Package"]) or ":" in metadata["Package"]
            or not _valid_version(metadata["Version"])
            or metadata["Architecture"] not in ("amd64", "all")
            or metadata.get("Multi-Arch", "no") not in ("no", "same", "foreign", "allowed")
            or metadata["Architecture"] == "all" and metadata.get("Multi-Arch") == "same"):
        raise ValueError("PACKAGE_ARCHIVE_UNPROVEN")
    return metadata["Package"] + (":amd64" if metadata.get("Multi-Arch") == "same" else "")


class LinuxPackageAdapter:
    requested = DEPENDENCIES

    def __init__(self, executor):
        self.executor = executor
        self.reboot_required = Path("/var/run/reboot-required").exists()
        self.frozen = {}
        self.security = self.security_snapshot()

    def options(self):
        return ["-o", f"Dir::State::lists={self.executor.cache}/lists",
                "-o", f"Dir::Cache::archives={self.executor.cache}/archives",
                "-o", "APT::Update::Error-Mode=any",
                "-o", "Acquire::AllowInsecureRepositories=false",
                "-o", "APT::Get::AllowUnauthenticated=false",
                "-o", "APT::Get::Always-Include-Phased-Updates=false"]

    def apt(self, extra, deadline):
        return self.executor.command(["/usr/bin/apt-get", *self.options(), *extra],
                                     deadline, privileged=True)

    def security_snapshot(self):
        result = [platform.release()]
        for path in ("/proc/sys/kernel/apparmor_restrict_unprivileged_userns",
                     "/sys/module/apparmor/parameters/enabled", "/proc/self/attr/current"):
            file = Path(path)
            result.append(file.read_bytes() if file.exists() else None)
        for path in ("/usr/bin/apt-get", "/usr/bin/dpkg", "/usr/bin/sudo", "/usr/bin/python3"):
            result.append(hashlib.sha256(Path(path).read_bytes()).digest())
        return tuple(result)

    def refresh(self, deadline):
        self.apt(["update", "--quiet"], deadline)

    def snapshot(self, deadline):
        raw = self.executor.command(
            ["/usr/bin/dpkg-query", "--show", "--showformat=${binary:Package}\t${Version}\t${db:Status-Status}\n"],
            deadline)
        records = {}
        for line in raw.decode("ascii").splitlines():
            parts = line.split("\t")
            if (len(parts) != 3 or not _valid_package(parts[0]) or not _valid_version(parts[1])
                    or parts[2] not in ("installed", "config-files") or parts[0] in records):
                raise ValueError("PACKAGE_STATE_UNPROVEN")
            records[parts[0]] = (parts[1], parts[2])
        return records

    def held_packages(self, deadline):
        raw = self.executor.command(["/usr/bin/apt-mark", "showhold"], deadline)
        names = raw.decode("ascii").splitlines()
        if not all(_valid_package(name) for name in names) or len(names) != len(set(names)):
            raise ValueError("PACKAGE_HOLDS_UNPROVEN")
        return frozenset(names)

    def arguments(self, kind):
        return (["upgrade"] if kind == "upgrade" else
                ["install", "--no-install-recommends", *sorted(self.requested)])

    def simulate(self, kind, deadline):
        return self.apt(["--simulate", *self.arguments(kind)], deadline).decode("ascii")

    @staticmethod
    def service_path(path):
        path = path.lstrip("./")
        return path.startswith(("etc/init/", "etc/init.d/", "lib/systemd/", "usr/lib/systemd/",
                                "usr/share/dbus-1/system-services/", "etc/systemd/"))

    def service_packages(self, proposal, deadline):
        services = set()
        for action in proposal.actions:
            if action.installed_version is not None:
                files = self.executor.command(["/usr/bin/dpkg-query", "--listfiles", action.package], deadline)
                if not files or any(self.service_path(line) for line in files.decode("ascii").splitlines()):
                    services.add(action.package)
            archive = self.frozen.get(action.package)
            if archive:
                listing = self.executor.command(["/usr/bin/dpkg-deb", "--contents", str(archive[0])], deadline)
                for line in listing.decode("utf-8").splitlines():
                    fields = line.split(maxsplit=5)
                    if len(fields) != 6:
                        raise ValueError("PACKAGE_OWNERSHIP_UNPROVEN")
                    if self.service_path(fields[5]):
                        services.add(action.package)
        return frozenset(services)

    def freeze(self, kind, proposal, deadline):
        self.apt(["--yes", "--download-only", "--no-remove", *self.arguments(kind)], deadline)
        total, found = 0, {}
        for path in (self.executor.cache / "archives").iterdir():
            if path.name in ("partial", "lock"):
                continue
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o22:
                raise ValueError("PACKAGE_CACHE_UNSAFE")
            total += info.st_size
            if total > 2 * 1024 ** 3 or path.suffix != ".deb":
                raise ValueError("PACKAGE_CACHE_TOO_LARGE")
            fields = self.executor.command(
                ["/usr/bin/dpkg-deb", "--field", str(path), "Package", "Version", "Architecture", "Multi-Arch"], deadline)
            records = [line.split(": ", 1) for line in fields.decode("ascii").splitlines()]
            if any(len(record) != 2 for record in records) or len({record[0] for record in records}) != len(records):
                raise ValueError("PACKAGE_ARCHIVE_UNPROVEN")
            metadata = dict(records)
            binary_package = archive_package_identity(metadata)
            name = metadata["Package"]
            if name in found:
                raise ValueError("PACKAGE_ARCHIVE_UNPROVEN")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            found[name] = (path, metadata["Version"], digest, binary_package)
        for action in proposal.actions:
            item = found.get(action.package.partition(":")[0])
            qualifier = action.package.partition(":")[2]
            if item is None or item[1] != action.candidate_version or qualifier not in ("", "amd64"):
                raise ValueError("PACKAGE_ARCHIVE_UNAVAILABLE")
            self.frozen[action.package] = item

    def apply(self, kind, proposal, deadline):
        for action in proposal.actions:
            path, version, digest, _ = self.frozen[action.package]
            if hashlib.sha256(path.read_bytes()).hexdigest() != digest or version != action.candidate_version:
                raise ValueError("PACKAGE_CACHE_CHANGED")
        self.apt(["--yes", "--no-download", "--no-remove", *self.arguments(kind)], deadline)

    def verify_changes(self, before, proposal, deadline):
        expected = dict(before)
        for action in proposal.actions:
            # Verified archive metadata determines dpkg's binary:Package identity
            # for BOTH new and existing packages; do not guess from before-state.
            key = self.frozen[action.package][3]
            if action.package.partition(":")[2] not in ("", "amd64"):
                raise ValueError("PACKAGE_POSTCONDITION_FAILED")
            if key != action.package:
                expected.pop(action.package, None)
            expected[key] = (action.candidate_version, "installed")
        if (self.snapshot(deadline) != expected or self.security_snapshot() != self.security
                or Path("/var/run/reboot-required").exists()):
            raise ValueError("PACKAGE_POSTCONDITION_FAILED")
