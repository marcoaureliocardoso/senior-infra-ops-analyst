"""Data-only privileged worker for the ephemeral CI bootstrap.

Never invoked by package tests. Fixed targets come from the reviewed manifest,
not from a cleanup path, executable, package or command supplied by a caller.
"""
from dataclasses import asdict
import json
import os
from pathlib import Path
import pwd
import re
import shutil
import stat
import sys

# -I prevents operator/user import configuration; only reviewed sibling modules
# are added deliberately. The worker is reviewed checkout code, not a security
# boundary against a malicious workflow that already has password-free sudo.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from ci_isolation_runtime import (  # noqa: E402
    BuildReceipt, OwnedRuntime, install_owned_tree, load_runtime_spec, remove_owned_tree,
)


ROOT = Path(__file__).resolve().parents[1]
PREFIX_BASE = Path("/opt/senior-infra-ci")
CACHE_BASE = Path("/opt/senior-infra-ci-cache")


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
    record = read_record(prefix / "receipt.json")
    if record.get("owner_nonce") != nonce:
        raise ValueError("CI_ROOT_OWNERSHIP_UNPROVEN")
    for key in ("build_options", "prefix_identity", "binary_identity"):
        record[key] = tuple(record[key])
    return OwnedRuntime(prefix, prefix / "bin/bwrap", BuildReceipt(**record))


def main(argv):
    if (os.geteuid() != 0 or len(argv) < 3 or argv[0] not in
            {"cache-create", "cache-cleanup", "runtime-install", "runtime-cleanup"}
            or Path(argv[1]) != ROOT / "tests/ci-runtime-lock.json"
            or not re.fullmatch(r"[0-9a-f]{32}", argv[2])):
        raise ValueError("CI_ROOT_SCOPE_REJECTED")
    action, _, nonce, *extra = argv
    expected_count = 2 if action == "runtime-install" else 0
    if len(extra) != expected_count:
        raise ValueError("CI_ROOT_SCOPE_REJECTED")
    spec = load_runtime_spec(Path(argv[1]))
    cache = CACHE_BASE / spec.source_sha256
    protected_directory(Path("/opt"))
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
    protected_directory(cache)
    marker = read_record(cache / "owner.json")
    if (marker != {"nonce": nonce, "source": spec.source_sha256,
                   "identity": [cache.stat().st_dev, cache.stat().st_ino]}):
        raise ValueError("CI_ROOT_OWNERSHIP_UNPROVEN")
    if action == "cache-cleanup":
        # The absolute target was derived from the fixed digest, matched against
        # its root-owned inode/nonce marker and all ancestors checked above.
        if cache.parent != CACHE_BASE or cache.name != spec.source_sha256:
            raise ValueError("CI_ROOT_SCOPE_REJECTED")
        shutil.rmtree(cache)  # Python's fd-based, symlink-attack-resistant removal
        print("CLEAN")
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


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except (ValueError, OSError, KeyError, TypeError):
        print("CI_ROOT_OPERATION_BLOCKED")
        raise SystemExit(1) from None
