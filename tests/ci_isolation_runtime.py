"""Verified source identity for a CI-private, non-setuid Bubblewrap build."""
from dataclasses import asdict, dataclass, replace
import errno
import hashlib
import io
import json
import os
from pathlib import Path
from pathlib import PurePosixPath
import re
import stat
import subprocess
import tarfile


@dataclass(frozen=True)
class RuntimeSpec:
    version: str
    source_url: str
    source_sha256: str
    source_size: int
    source_commit: str
    architecture: str
    build_options: tuple[str, ...]


_OPTIONS = ("-Dman=disabled", "-Dselinux=disabled", "--wrap-mode=nodownload")
_SOURCE_KEYS = {"version", "sourceUrl", "sourceSha256", "sourceSize", "sourceCommit",
                "architecture", "buildOptions"}
_AA_COMMIT = "72229df83059480f4e9fb1488624201bdbd61755"
_AA_PATH = "profiles/apparmor/profiles/extras/bwrap-userns-restrict"


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("RUNTIME_MANIFEST_AMBIGUOUS")
        result[key] = value
    return result


def load_runtime_spec(path: Path) -> RuntimeSpec:
    try:
        with path.open("rb") as stream:
            raw = stream.read(16385)
        if len(raw) > 16384:
            raise ValueError("RUNTIME_MANIFEST_INVALID")
        record = json.loads(raw, object_pairs_hook=_unique_object)
        if (type(record) is not dict or set(record) != {"schemaVersion", "bubblewrap", "apparmorSource"}
                or type(record["schemaVersion"]) is not int or record["schemaVersion"] != 1):
            raise ValueError("RUNTIME_MANIFEST_INVALID")
        source, policy = record["bubblewrap"], record["apparmorSource"]
        if (type(source) is not dict or set(source) != _SOURCE_KEYS
                or type(policy) is not dict or set(policy) != {"commit", "path", "url"}
                or policy != {"commit": _AA_COMMIT, "path": _AA_PATH,
                              "url": f"https://gitlab.com/apparmor/apparmor/-/raw/{_AA_COMMIT}/{_AA_PATH}"}):
            raise ValueError("RUNTIME_PROVENANCE_INVALID")
        version = source["version"]
        if (type(version) is not str or not re.fullmatch(r"[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}", version)
                or tuple(map(int, version.split("."))) < (0, 12, 0)
                or source["sourceUrl"] != f"https://github.com/containers/bubblewrap/releases/download/v{version}/bubblewrap-{version}.tar.xz"
                or source["architecture"] != "x86_64"
                or type(source["sourceSize"]) is not int or not 0 < source["sourceSize"] <= 100_000_000
                or type(source["sourceSha256"]) is not str
                or not re.fullmatch(r"[0-9a-f]{64}", source["sourceSha256"])
                or type(source["sourceCommit"]) is not str
                or not re.fullmatch(r"[0-9a-f]{40}", source["sourceCommit"])
                or source["buildOptions"] != list(_OPTIONS)):
            raise ValueError("RUNTIME_PROVENANCE_INVALID")
        return RuntimeSpec(version, source["sourceUrl"], source["sourceSha256"],
                           source["sourceSize"], source["sourceCommit"],
                           source["architecture"], _OPTIONS)
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, OverflowError) as error:
        raise ValueError("RUNTIME_MANIFEST_INVALID") from error


def verify_archive(data: bytes, spec: RuntimeSpec) -> None:
    if (type(data) is not bytes or type(spec) is not RuntimeSpec
            or len(data) != spec.source_size
            or hashlib.sha256(data).hexdigest() != spec.source_sha256):
        raise ValueError("RUNTIME_ARCHIVE_IDENTITY_MISMATCH")


def extract_verified_archive(data, spec, destination):
    verify_archive(data, spec)
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:xz") as archive:
            members = archive.getmembers()
            names = set()
            total = 0
            if not members or len(members) > 2048:
                raise ValueError("RUNTIME_ARCHIVE_UNSAFE")
            for member in members:
                path = PurePosixPath(member.name)
                if (not member.name or path.is_absolute() or ".." in path.parts
                        or "\\" in member.name or path.parts[0] != f"bubblewrap-{spec.version}"
                        or not (member.isfile() or member.isdir()) or member.name in names
                        or member.mode & 0o7000 or member.size > 8 * 1024 * 1024):
                    raise ValueError("RUNTIME_ARCHIVE_UNSAFE")
                names.add(member.name)
                total += member.size
            if total > 32 * 1024 * 1024:
                raise ValueError("RUNTIME_ARCHIVE_UNSAFE")
            destination.mkdir(mode=0o700)  # exclusive owned destination, after validation
            for member in members:
                target = destination / member.name
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True, mode=0o700)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                    with archive.extractfile(member) as source, target.open("xb") as output:
                        output.write(source.read(member.size + 1))
                    target.chmod(0o755 if member.mode & 0o111 else 0o644)
    except (OSError, tarfile.TarError, EOFError):
        raise ValueError("RUNTIME_ARCHIVE_UNSAFE") from None


@dataclass(frozen=True)
class BuildReceipt:
    source_sha256: str
    binary_sha256: str
    template_sha256: str
    architecture: str
    version: str
    build_options: tuple[str, ...]
    owner_uid: int = 0
    prefix_identity: tuple[int, int] = (0, 0)
    binary_identity: tuple[int, int] = (0, 0)
    owner_nonce: str = ""


@dataclass(frozen=True)
class OwnedRuntime:
    prefix: Path
    binary: Path
    receipt: BuildReceipt


def file_metadata_is_safe(*, mode, uid, owner_uid, capabilities):
    return (stat.S_ISREG(mode) and not mode & 0o6022 and uid == owner_uid
            and type(capabilities) is bytes and capabilities == b"")


def _capabilities(fd):
    try:
        return os.getxattr(fd, "security.capability")
    except OSError as error:
        if error.errno not in (errno.ENODATA, errno.ENOTSUP):
            raise ValueError("RUNTIME_CAPABILITIES_UNPROVEN") from None
        return b""


def _identity(info):
    return info.st_dev, info.st_ino


def _read_binary(path, owner_uid):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            info = os.fstat(fd)
            if (not file_metadata_is_safe(mode=info.st_mode, uid=info.st_uid,
                                         owner_uid=owner_uid, capabilities=_capabilities(fd))
                    or info.st_nlink != 1 or not info.st_mode & 0o111
                    or not 0 < info.st_size <= 8 * 1024 * 1024):
                raise ValueError("RUNTIME_BINARY_UNSAFE")
            data = os.read(fd, info.st_size + 1)
            if len(data) != info.st_size or os.fstat(fd) != info:
                raise ValueError("RUNTIME_BINARY_CHANGED")
            if owner_uid == 0 and not data.startswith(b"\x7fELF"):
                raise ValueError("RUNTIME_BINARY_UNSAFE")
            return data, info
        finally:
            os.close(fd)
    except OSError:
        raise ValueError("RUNTIME_BINARY_UNSAFE") from None


def _safe_directories(prefix, owner_uid):
    # Non-root owners are only used by in-process synthetic tests. Production
    # validates the entire root-owned chain, not merely the leaf directory.
    paths = (prefix.parent, prefix, prefix / "bin")
    if owner_uid == 0:
        paths = tuple(reversed(prefix.parents)) + (prefix, prefix / "bin")
    for path in paths:
        info = path.lstat()
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid != owner_uid
                or info.st_mode & 0o22):
            raise ValueError("RUNTIME_DIRECTORY_UNSAFE")


def verify_installed_runtime(runtime: OwnedRuntime, *, check_version=True) -> None:
    try:
        receipt = runtime.receipt
        if (type(runtime) is not OwnedRuntime or type(receipt) is not BuildReceipt
                or runtime.prefix.name != receipt.source_sha256
                or runtime.binary != runtime.prefix / "bin/bwrap"
                or receipt.architecture != "x86_64" or receipt.build_options != _OPTIONS
                or receipt.version != "0.12.0"):
            raise ValueError("RUNTIME_RECEIPT_INVALID")
        _safe_directories(runtime.prefix, receipt.owner_uid)
        data, info = _read_binary(runtime.binary, receipt.owner_uid)
        if (_identity(runtime.prefix.lstat()) != receipt.prefix_identity
                or _identity(info) != receipt.binary_identity
                or hashlib.sha256(data).hexdigest() != receipt.binary_sha256):
            raise ValueError("RUNTIME_IDENTITY_CHANGED")
        path = runtime.prefix / "receipt.json"
        if path.is_symlink() or path.stat().st_uid != receipt.owner_uid or path.stat().st_mode & 0o22:
            raise ValueError("RUNTIME_RECEIPT_INVALID")
        expected = json.loads(json.dumps(asdict(receipt)))
        if json.loads(path.read_bytes()) != expected:
            raise ValueError("RUNTIME_RECEIPT_CHANGED")
        # Identity is rechecked after the bounded, fixed version invocation.
        if check_version:
            result = subprocess.run([str(runtime.binary), "--version"], stdin=subprocess.DEVNULL,
                                    capture_output=True, timeout=5, check=False,
                                    env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"})
            if result.returncode or result.stdout != f"bubblewrap {receipt.version}\n".encode() or result.stderr:
                raise ValueError("RUNTIME_VERSION_MISMATCH")
        again, after = _read_binary(runtime.binary, receipt.owner_uid)
        if info != after or data != again:
            raise ValueError("RUNTIME_IDENTITY_CHANGED")
    except (OSError, subprocess.SubprocessError, UnicodeError, json.JSONDecodeError, AttributeError):
        raise ValueError("RUNTIME_VERIFICATION_FAILED") from None


def install_owned_tree(candidate, prefix, receipt, *, owner_uid=0, candidate_uid=None):
    """Copy bounded verified data into an exclusive prefix; never adopt a tree."""
    data, _ = _read_binary(candidate, os.getuid() if candidate_uid is None else candidate_uid)
    if hashlib.sha256(data).hexdigest() != receipt.binary_sha256:
        raise ValueError("RUNTIME_CANDIDATE_CHANGED")
    parent_info = prefix.parent.lstat()
    if (not stat.S_ISDIR(parent_info.st_mode) or parent_info.st_uid != owner_uid
            or parent_info.st_mode & 0o22 or prefix.name != receipt.source_sha256):
        raise ValueError("RUNTIME_DIRECTORY_UNSAFE")
    try:
        prefix.mkdir(mode=0o755)
    except FileExistsError:
        raise ValueError("RUNTIME_PREFIX_COLLISION") from None
    prefix_info = prefix.lstat()
    created = []
    try:
        (prefix / "bin").mkdir(mode=0o755)
        binary = prefix / "bin/bwrap"
        with binary.open("xb") as stream:
            stream.write(data)
        binary.chmod(0o755)
        created.append(binary)
        receipt = replace(receipt, owner_uid=owner_uid,
                          prefix_identity=_identity(prefix_info),
                          binary_identity=_identity(binary.lstat()))
        receipt_path = prefix / "receipt.json"
        with receipt_path.open("x", encoding="ascii") as stream:
            json.dump(asdict(receipt), stream, separators=(",", ":"))
        receipt_path.chmod(0o644)
        created.append(receipt_path)
        runtime = OwnedRuntime(prefix, binary, receipt)
        # The privileged installer copies data only. The runner performs the
        # executable version check before any publication or namespace probe.
        if os.geteuid() != 0:
            verify_installed_runtime(runtime)
        return runtime
    except BaseException:
        # No recursive deletion: only leaves created in this exclusive tree.
        if prefix.lstat() == prefix_info or _identity(prefix.lstat()) == _identity(prefix_info):
            for path in reversed(created):
                if path.is_file() and not path.is_symlink():
                    path.unlink()
            if (prefix / "bin").is_dir() and not (prefix / "bin").is_symlink():
                (prefix / "bin").rmdir()
            prefix.rmdir()
        raise


def remove_owned_tree(runtime, *, owner_uid=0):
    try:
        if runtime.receipt.owner_uid != owner_uid:
            return False
        verify_installed_runtime(runtime, check_version=os.geteuid() != 0)
        if set(runtime.prefix.iterdir()) != {runtime.prefix / "bin", runtime.prefix / "receipt.json"}:
            return False
        if set((runtime.prefix / "bin").iterdir()) != {runtime.binary}:
            return False
        runtime.binary.unlink()
        (runtime.prefix / "receipt.json").unlink()
        (runtime.prefix / "bin").rmdir()
        runtime.prefix.rmdir()
        return True
    except (OSError, ValueError):
        return False
