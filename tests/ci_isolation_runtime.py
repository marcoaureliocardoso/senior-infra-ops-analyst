"""Verified source identity for a CI-private, non-setuid Bubblewrap build."""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re


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
