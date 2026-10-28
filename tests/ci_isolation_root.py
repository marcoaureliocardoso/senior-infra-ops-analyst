"""Data-only privileged worker for the ephemeral CI bootstrap.

The privileged entry point never runs in package tests. Fixed targets come from the reviewed manifest,
not from a cleanup path, executable, package or command supplied by a caller.
"""
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time

# -I prevents operator/user import configuration; only reviewed sibling modules
# are added deliberately. The worker is reviewed checkout code, not a security
# boundary against a malicious workflow that already has password-free sudo.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from ci_isolation_runtime import (  # noqa: E402
    BuildReceipt, OwnedRuntime, install_owned_tree, load_runtime_spec, remove_owned_tree,
    verify_installed_runtime,
)
from ci_isolation_bootstrap import load_policy_template, match_denial_records, policy_for_runtime  # noqa: E402
from ci_worker_diagnostics import encode_failure  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
PREFIX_BASE = Path("/var/lib/senior-infra-ci")
CACHE_BASE = Path("/var/cache/senior-infra-ci")


def protected_directory(path, *, create=False):
    if create and not path.exists() and not path.is_symlink():
        path.mkdir(mode=0o755)
    for candidate in tuple(reversed(path.parents)) + (path,):
        info = candidate.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o22:
            raise ValueError("CI_ROOT_DIRECTORY_UNSAFE")


def read_record(path, *, owner_uid=0, limit=16384):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != owner_uid or info.st_size > limit or info.st_mode & 0o22:
            raise ValueError("CI_ROOT_RECORD_UNSAFE")
        return json.loads(os.read(fd, limit + 1))
    finally:
        os.close(fd)


def load_owned_runtime(spec, nonce):
    prefix = PREFIX_BASE / spec.source_sha256
    protected_directory(prefix)
    protected_directory(prefix / "bin")
    record = read_record(prefix / "receipt.json")
    if record.get("owner_nonce") != nonce:
        raise ValueError("CI_ROOT_OWNERSHIP_UNPROVEN")
    for key in ("build_options", "prefix_identity", "binary_identity"):
        record[key] = tuple(record[key])
    return OwnedRuntime(prefix, prefix / "bin/bwrap", BuildReceipt(**record))


def bounded_root_command(argv, cache, *, allow_failure=False, trace=None):
    audit_trace = trace is not None
    trace = {} if trace is None else trace
    trace['phase'] = 'AUDIT_JOURNAL_OPEN'
    with tempfile.TemporaryFile(dir=cache) as output:
        trace['phase'] = 'AUDIT_JOURNAL_SPAWN'
        process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=output, stderr=output,
                                   env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"},
                                   start_new_session=True)
        deadline = time.monotonic() + 15
        trace['phase'] = 'AUDIT_JOURNAL_WAIT'
        primary = None
        try:
            while process.poll() is None:
                if time.monotonic() >= deadline:
                    raise ValueError("CI_ROOT_COMMAND_TIMEOUT")
                if output.tell() > 512 * 1024:
                    raise ValueError("CI_ROOT_COMMAND_OUTPUT_LIMIT")
                time.sleep(0.01)
            if output.tell() > 512 * 1024:
                raise ValueError("CI_ROOT_COMMAND_OUTPUT_LIMIT")
            if process.returncode and not allow_failure:
                raise ValueError("CI_ROOT_COMMAND_FAILED")
            output.seek(0)
            return output.read(512 * 1024 + 1)
        except BaseException as error:
            primary = error
            raise
        finally:
            try:
                if process.poll() is None:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    process.wait(timeout=5)
            except (OSError, subprocess.SubprocessError):
                if not audit_trace or primary is None: raise
            finally:
                trace['commandReturnCode'] = process.returncode


def loaded_profiles():
    raw = Path("/sys/kernel/security/apparmor/profiles").read_bytes()
    if len(raw) > 512 * 1024:
        raise ValueError("CI_POLICY_STATE_UNPROVEN")
    return frozenset(line.rsplit(" (", 1)[0] for line in raw.decode("ascii").splitlines())


def store_policy_marker(cache, marker):
    pending = cache / "policy-owner.pending"
    with pending.open("x", encoding="ascii") as stream:
        json.dump(marker, stream)
        stream.flush()
        os.fsync(stream.fileno())
    pending.chmod(0o600)
    os.replace(pending, cache / "policy-owner.json")


def publish_owned_policy(policy, data, cache, nonce):
    if hashlib.sha256(data).hexdigest() != policy.digest:
        raise ValueError("CI_POLICY_TEMPLATE_CHANGED")
    pending = cache / "policy-pending"
    with pending.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    pending.chmod(0o644)
    info = pending.lstat()
    marker = {"nonce": nonce, "digest": policy.digest,
              "identity": [info.st_dev, info.st_ino], "loadStarted": False}
    # Ownership intent exists BEFORE any file becomes visible to AppArmor.
    # link is exclusive: it cannot overwrite/adopt a foreign target.
    store_policy_marker(cache, marker)
    os.link(pending, policy.path, follow_symlinks=False)
    return marker


def cleanup_owned_policy(policy, cache, nonce, *, owner_uid=0, profiles=frozenset(), remove=None):
    names = {policy.parent_name, policy.child_name}
    marker_path = cache / "policy-owner.json"
    if not marker_path.exists():
        if marker_path.is_symlink() or names & profiles or policy.path.exists() or policy.path.is_symlink():
            raise ValueError("CI_POLICY_CLEANUP_OWNERSHIP_UNPROVEN")
        return
    marker = read_record(marker_path, owner_uid=owner_uid)
    if (type(marker) is not dict or set(marker) != {"nonce", "digest", "identity", "loadStarted"}
            or marker["nonce"] != nonce or marker["digest"] != policy.digest
            or type(marker["loadStarted"]) is not bool or type(marker["identity"]) is not list
            or len(marker["identity"]) != 2
            or not all(type(value) is int and value >= 0 for value in marker["identity"])):
        raise ValueError("CI_POLICY_CLEANUP_OWNERSHIP_UNPROVEN")
    pending = cache / "policy-pending"
    # The retained private inode is authoritative even if publication failed.
    for path in (pending, policy.path):
        if not path.exists() and not path.is_symlink() and path == policy.path:
            continue
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            info = os.fstat(fd)
            data = os.read(fd, 16385)
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != owner_uid or info.st_mode & 0o22
                    or info.st_nlink not in (1, 2) or info.st_size > 16384
                    or marker["identity"] != [info.st_dev, info.st_ino]
                    or hashlib.sha256(data).hexdigest() != policy.digest):
                raise ValueError("CI_POLICY_CLEANUP_OWNERSHIP_UNPROVEN")
        finally:
            os.close(fd)
    if not marker["loadStarted"]:
        if names & profiles:
            raise ValueError("CI_POLICY_CLEANUP_OWNERSHIP_UNPROVEN")
    else:
        if remove is None or not policy.path.exists():
            raise ValueError("CI_POLICY_CLEANUP_OWNERSHIP_UNPROVEN")
        # Actual caller removes both exact owned names and proves their absence.
        remove()
    if policy.path.exists():
        policy.path.unlink()
    pending.unlink()
    marker_path.unlink()


def policy_action(action, spec, nonce, cache):
    runtime = load_owned_runtime(spec, nonce)
    verify_installed_runtime(runtime, check_version=False)
    template = load_policy_template(ROOT / "tests/ci-runtime-lock.json")
    if hashlib.sha256(template).hexdigest() != runtime.receipt.template_sha256:
        raise ValueError("CI_POLICY_TEMPLATE_CHANGED")
    policy = policy_for_runtime(runtime, template)
    names = {policy.parent_name, policy.child_name}
    protected_directory(policy.path.parent)
    abi = Path("/etc/apparmor.d/abi/4.0")
    if abi.is_symlink() or abi.stat().st_uid != 0 or abi.stat().st_mode & 0o22:
        raise ValueError("CI_POLICY_ABI_UNSUPPORTED")
    parser = Path("/usr/sbin/apparmor_parser")
    if parser.is_symlink() or parser.stat().st_uid != 0 or parser.stat().st_mode & 0o6022:
        raise ValueError("CI_POLICY_PARSER_UNSAFE")
    marker_path = cache / "policy-owner.json"
    if action == "policy-load":
        if names & loaded_profiles() or policy.path.exists() or policy.path.is_symlink() or marker_path.exists():
            raise ValueError("CI_POLICY_FOREIGN_ATTACHMENT")
        from ci_isolation_bootstrap import render_policy
        # Preserve a root-owned verified template copy before loading any policy.
        template_copy = cache / "policy-template"
        with template_copy.open("xb") as stream:
            stream.write(template)
        template_copy.chmod(0o644)
        if hashlib.sha256(template_copy.read_bytes()).hexdigest() != runtime.receipt.template_sha256:
            raise ValueError("CI_POLICY_TEMPLATE_CHANGED")
        data = render_policy(template_copy.read_bytes(), runtime.binary, policy.parent_name, policy.child_name)
        marker = publish_owned_policy(policy, data, cache, nonce)
        # Atomic phase transition precedes the first possible kernel side effect.
        store_policy_marker(cache, {**marker, "loadStarted": True})
        bounded_root_command([str(parser), "--add", "--skip-cache", str(policy.path)], cache)
        if not names <= loaded_profiles():
            raise ValueError("CI_POLICY_LOAD_UNPROVEN")
    else:
        def remove():
            # A partial load can leave either half. Parser status alone is not
            # success: BOTH exact owned names must independently be absent.
            bounded_root_command([str(parser), "--remove", "--skip-cache", str(policy.path)],
                                 cache, allow_failure=True)
            if names & loaded_profiles():
                raise ValueError("CI_POLICY_CLEANUP_FAILED")

        cleanup_owned_policy(policy, cache, nonce, profiles=loaded_profiles(), remove=remove)
        print("CLEAN")


def main(argv, *, trace=None):
    trace = {} if trace is None else trace
    trace['phase'] = 'ROOT_SCOPE'
    if (os.geteuid() != 0 or len(argv) < 3 or argv[0] not in
            {"cache-create", "cache-cleanup", "runtime-install", "runtime-cleanup",
             "audit-read", "policy-load", "policy-cleanup"}
            or Path(argv[1]) != ROOT / "tests/ci-runtime-lock.json"
            or not re.fullmatch(r"[0-9a-f]{32}", argv[2])):
        raise ValueError("CI_ROOT_SCOPE_REJECTED")
    action, _, nonce, *extra = argv
    expected_count = 2 if action == "runtime-install" else 1 if action == "audit-read" else 0
    if len(extra) != expected_count:
        raise ValueError("CI_ROOT_SCOPE_REJECTED")
    trace['phase'] = 'ROOT_MANIFEST'
    spec = load_runtime_spec(Path(argv[1]))
    cache = CACHE_BASE / spec.source_sha256
    trace['phase'] = 'ROOT_DIRECTORIES'
    protected_directory(PREFIX_BASE.parent)
    protected_directory(CACHE_BASE.parent)
    if action == "cache-create":
        protected_directory(CACHE_BASE, create=True)
        cache.mkdir(mode=0o755)  # exclusive; collisions never become ownership
        marker = {"nonce": nonce, "source": spec.source_sha256,
                  "identity": [cache.stat().st_dev, cache.stat().st_ino]}
        with (cache / "owner.json").open("x", encoding="ascii") as stream:
            json.dump(marker, stream)
        for relative in ("lists", "archives", "lists/partial", "archives/partial"):
            (cache / relative).mkdir(mode=0o755)
        apt_uid = pwd.getpwnam("_apt").pw_uid
        for relative in ("lists/partial", "archives/partial"):
            os.chown(cache / relative, apt_uid, 0)
        return
    trace['phase'] = 'ROOT_CACHE'
    protected_directory(cache)
    marker = read_record(cache / "owner.json")
    if (marker != {"nonce": nonce, "source": spec.source_sha256,
                   "identity": [cache.stat().st_dev, cache.stat().st_ino]}):
        raise ValueError("CI_ROOT_OWNERSHIP_UNPROVEN")
    if action == "cache-cleanup":
        # The absolute target was derived from the fixed digest, matched against
        # its root-owned inode/nonce marker and all ancestors checked above.
        if (cache.parent != CACHE_BASE or cache.name != spec.source_sha256
                or (cache / "policy-owner.json").exists()):
            raise ValueError("CI_ROOT_SCOPE_REJECTED")
        shutil.rmtree(cache)  # Python's fd-based, symlink-attack-resistant removal
        print("CLEAN")
    elif action in ("policy-load", "policy-cleanup"):
        policy_action(action, spec, nonce, cache)
    elif action == "audit-read":
        trace['phase'] = 'AUDIT_RUNTIME_LOAD'
        runtime = load_owned_runtime(spec, nonce)
        trace['phase'] = 'AUDIT_RUNTIME_VERIFY'
        verify_installed_runtime(runtime, check_version=False)
        trace['phase'] = 'AUDIT_REQUEST'
        request = json.loads(extra[0])
        if type(request) is not dict or set(request) != {"pids", "window"}:
            raise ValueError("CI_AUDIT_SCOPE_REJECTED")
        pids, window = request["pids"], request["window"]
        if (type(pids) is not list or len(pids) > 128 or not pids
                or not all(type(pid) is int and pid > 0 for pid in pids)
                or type(window) is not list or len(window) != 2
                or not all(type(value) in (int, float) for value in window)
                or not 0 < window[1] - window[0] <= 120 or not 0 <= time.time() - window[1] <= 120):
            raise ValueError("CI_AUDIT_SCOPE_REJECTED")
        raw = bounded_root_command(["/usr/bin/journalctl", "--dmesg", "--no-pager", "--output=json",
                                    "--since", f"@{window[0]:.6f}", "--until", f"@{window[1]:.6f}"], cache, trace=trace)
        trace['phase'] = 'AUDIT_MATCH'
        matched = match_denial_records(raw, pids=tuple(pids), window=tuple(window), binary=str(runtime.binary))
        print(json.dumps({"matched": matched}))
    elif action == "runtime-cleanup":
        runtime = load_owned_runtime(spec, nonce)
        if not remove_owned_tree(runtime):
            raise ValueError("CI_ROOT_CLEANUP_FAILED")
        print("CLEAN")
    elif action == "runtime-install":
        candidate, request = map(Path, extra)
        uid = int(os.environ["SUDO_UID"])
        if uid <= 0 or candidate.is_symlink() or candidate.parent.name != "build":
            raise ValueError("CI_ROOT_SOURCE_REJECTED")
        workspace = candidate.parent.parent
        if (workspace.is_symlink() or workspace.stat().st_uid != uid
                or workspace.stat().st_mode & 0o77 or request != workspace / "install-request.json"):
            raise ValueError("CI_ROOT_SOURCE_REJECTED")
        record = read_record(request, owner_uid=uid)
        record["build_options"] = tuple(record["build_options"])
        record["prefix_identity"] = tuple(record["prefix_identity"])
        record["binary_identity"] = tuple(record["binary_identity"])
        receipt = BuildReceipt(**record)
        if (receipt.source_sha256 != spec.source_sha256 or receipt.version != spec.version
                or receipt.architecture != spec.architecture or receipt.build_options != spec.build_options
                or receipt.owner_nonce != nonce or not re.fullmatch(r"[0-9a-f]{64}", receipt.binary_sha256)):
            raise ValueError("CI_ROOT_RECEIPT_REJECTED")
        protected_directory(PREFIX_BASE, create=True)
        runtime = install_owned_tree(candidate, PREFIX_BASE / spec.source_sha256,
                                     receipt, candidate_uid=uid)
        print(json.dumps(asdict(runtime.receipt), separators=(",", ":")))


def cli(argv):
    trace = {'phase': 'ROOT_SCOPE', 'commandReturnCode': None}
    try:
        main(argv, trace=trace)
        return 0
    except Exception as error:
        if argv and argv[0] == 'audit-read':
            print(encode_failure(trace, error))
        else:
            print('CI_ROOT_OPERATION_BLOCKED')
        return 1


if __name__ == "__main__":
    raise SystemExit(cli(sys.argv[1:]))
