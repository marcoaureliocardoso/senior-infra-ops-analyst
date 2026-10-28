"""Fixed synthetic isolation attestation. No Claude, provider or operator data."""
from dataclasses import asdict, dataclass
import errno
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import time

from ci_privilege_status import validate_privilege_status


NAMESPACES = ("user", "mnt", "pid", "ipc", "uts", "net")


@dataclass(frozen=True)
class IsolationProof:
    namespace: bool
    network: bool
    mount: bool
    process: bool
    privilege: bool
    policy: bool
    cleanup: bool


def validate_proof(record):
    expected = {"namespace", "network", "mount", "process", "privilege", "policy", "cleanup"}
    if type(record) is not dict or set(record) != expected or any(value is not True for value in record.values()):
        error = ValueError("CI_ISOLATION_PROOF_REJECTED")
        error.fields = (tuple(sorted(key for key in expected if record[key] is not True))
                        if type(record) is dict and set(record) == expected else ("schema",))
        raise error
    return IsolationProof(**record)


def _read(path, limit=65536):
    with Path(path).open("rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ValueError("CI_ISOLATION_PROOF_REJECTED")
    return data


def _privilege_recovery_denied():
    import ctypes
    libc = ctypes.CDLL(None, use_errno=True)
    class Header(ctypes.Structure):
        _fields_ = [("version", ctypes.c_uint32), ("pid", ctypes.c_int)]
    class Data(ctypes.Structure):
        _fields_ = [("effective", ctypes.c_uint32), ("permitted", ctypes.c_uint32),
                    ("inheritable", ctypes.c_uint32)]
    data = (Data * 2)()
    data[0].effective = data[0].permitted = (1 << 21) | (1 << 12)
    header = Header(0x20080522, 0)
    denied = libc.capset(ctypes.byref(header), ctypes.byref(data)) == -1 and ctypes.get_errno() == errno.EPERM
    # This attempts to recover useful authority in the ORIGINAL sandbox mount
    # namespace. It says nothing about harmless descendant-local userns caps.
    mounted = libc.mount(None, b"/proof/readonly", None, 32 | 4096, None)
    return denied and mounted == -1 and ctypes.get_errno() == errno.EPERM


def routes_are_isolated(routes4, routes6):
    try:
        for line in routes4.splitlines():
            fields = line.split()
            if len(fields) < 8 or fields[0] != "lo" or fields[1] == "00000000":
                return False
        for line in routes6.splitlines():
            fields = line.split()
            if len(fields) != 10 or fields[-1] != "lo":
                return False
            if fields[0] == "0" * 32 and fields[1] == "00" and not int(fields[8], 16) & 0x200:
                return False  # RTF_REJECT sentinel cannot forward a packet.
        return True
    except (ValueError, TypeError):
        return False


def _network_proof(isolated):
    if not isolated or {name for _, name in socket.if_nameindex()} != {"lo"}:
        return False
    import fcntl  # Linux child only; portable input-audit imports never need it.
    import struct
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server:
        flags = fcntl.ioctl(server.fileno(), 0x8913, struct.pack("16sH14s", b"lo", 0, b""))
        if not struct.unpack("16sH14s", flags)[1] & 1:
            return False
        routes = "\n".join(_read("/proc/net/route", 16384).decode("ascii").splitlines()[1:])
        routes6 = _read("/proc/net/ipv6_route", 16384).decode("ascii")
        if not routes_are_isolated(routes, routes6):
            return False
        server.settimeout(1)
        server.bind(("127.0.0.1", 0))
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client:
            client.settimeout(1)
            client.sendto(b"CI", server.getsockname())
            payload, peer = server.recvfrom(3)
            return payload == b"CI" and peer[0] == "127.0.0.1"


def policy_label_matches(label, names):
    if (type(label) is not str or len(label) > 4096 or type(names) not in (list, tuple)
            or len(names) != 2 or not all(type(name) is str for name in names)
            or names[1] != names[0] + "-child" or not label.endswith(" (enforce)")):
        return False
    components = label[:-len(" (enforce)")].split("//&")
    return len(components) == 2 and set(components) == set(names)


def inner_proof():
    config = json.loads(_read("/proof/config.json", 4096))
    namespaces = {name: os.readlink(f"/proc/self/ns/{name}") for name in NAMESPACES}
    distinct = {name: namespaces[name] != config["namespaces"][name] for name in NAMESPACES}
    result = {"namespace": all(distinct.values()), "network": False, "mount": False,
              "process": False, "privilege": False, "policy": False, "cleanup": False}
    result["network"] = _network_proof(distinct["net"])
    readonly = False
    try:
        with Path("/proof/readonly").open("ab") as stream:
            stream.write(b"CI_WRITE_CONTROL")
    except OSError as error:
        readonly = error.errno in (errno.EROFS, errno.EACCES, errno.EPERM)
    work = Path("/work/owned-write")
    with work.open("xb") as stream:
        stream.write(b"CI_WORK")
    writable = work.read_bytes() == b"CI_WORK"
    work.unlink()
    hidden = (not Path(config["hostMarker"]).exists() and not Path("/mnt/c").exists()
              and not any(Path("/home").iterdir()) and not any(Path("/root").iterdir()))
    result["mount"] = readonly and writable and hidden
    host_stat = Path(f'/proc/{config["hostPid"]}/stat')
    result["process"] = distinct["pid"] and not host_stat.exists()
    try:
        validate_privilege_status(_read("/proc/self/status").decode())
        result["privilege"] = _privilege_recovery_denied()
    except ValueError:
        pass
    names = config["policyNames"]
    label = _read("/proc/self/attr/current", 4096).decode().strip() if names else ""
    result["policy"] = names is None or policy_label_matches(label, names)
    print(json.dumps(result, separators=(",", ":")))


def _run_proof(binary, policy, *, deadline, negative_control=None):
    if time.monotonic() >= deadline:
        raise ValueError("CI_ISOLATION_PROOF_DEADLINE")
    if negative_control not in (None, "ipc", "uts", "pid", "net", "writable-readonly"):
        raise ValueError("CI_ISOLATION_PROOF_REJECTED")
    record = None
    marker = None
    child = None
    with tempfile.TemporaryDirectory(prefix="senior-infra-isolation-") as directory:
        root = Path(directory)
        try:
            (root / "work").mkdir()
            readonly = root / "readonly"
            readonly.write_bytes(b"CI_READONLY")
            host_marker = root / "host-marker"
            host_marker.write_bytes(b"CI_HOST")
            marker = subprocess.Popen(["/usr/bin/python3", "-I", "-B", "-c",
                                       "import time; time.sleep(60)"], stdin=subprocess.DEVNULL,
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                      env={"PATH": "/usr/bin:/bin"}, start_new_session=True)
            config = {"namespaces": {name: os.readlink(f"/proc/self/ns/{name}") for name in NAMESPACES},
                      "hostMarker": str(host_marker), "hostPid": marker.pid,
                      "policyNames": [policy.parent_name, policy.child_name] if policy else None}
            (root / "config.json").write_text(json.dumps(config), encoding="ascii")
            argv = [str(binary), "--die-with-parent", "--new-session", "--unshare-user"]
            for name in ("pid", "ipc", "uts", "net"):
                if name != negative_control:
                    argv += ["--unshare-" + name]
            argv += ["--cap-drop", "ALL", "--ro-bind", "/usr", "/usr",
                     "--symlink", "usr/bin", "/bin", "--symlink", "usr/lib", "/lib",
                     "--symlink", "usr/lib64", "/lib64", "--proc", "/proc", "--dev", "/dev"]
            for path in ("/home", "/root", "/mnt", "/tmp", "/proof"):
                argv += ["--dir", path]
            argv += ["--bind", str(root / "work"), "/work", "--chdir", "/work",
                     "--bind" if negative_control == "writable-readonly" else "--ro-bind",
                     str(readonly), "/proof/readonly", "--ro-bind", str(root / "config.json"), "/proof/config.json"]
            for name in ("ci_isolation_probe.py", "ci_privilege_status.py"):
                argv += ["--ro-bind", str(Path(__file__).with_name(name)), "/proof/" + name]
            argv += ["--clearenv", "--setenv", "PATH", "/usr/bin:/bin", "--setenv", "PYTHONDONTWRITEBYTECODE", "1",
                     "/usr/bin/python3", "-B", "/proof/ci_isolation_probe.py", "--inner"]
            with tempfile.TemporaryFile(dir=root) as output, tempfile.TemporaryFile(dir=root) as errors:
                child = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=output, stderr=errors,
                                         env={"PATH": "/usr/bin:/bin"}, start_new_session=True)
                while child.poll() is None:
                    if (time.monotonic() >= deadline or output.tell() > 4096 or errors.tell() > 65536):
                        raise ValueError("CI_ISOLATION_PROOF_BOUNDED_FAILURE")
                    time.sleep(0.01)
                if child.returncode or output.tell() > 4096:
                    raise ValueError("CI_ISOLATION_PROOF_CHILD_FAILED")
                output.seek(0)
                record = json.loads(output.read(4097))
        finally:
            for process in (child, marker):
                if process is None:
                    continue
                if process.poll() is None:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                process.wait(timeout=5)
    # Publication is strictly after child reaping AND fixture disposal.
    if root.exists() or record is None or time.monotonic() >= deadline:
        raise ValueError("CI_ISOLATION_PROOF_CLEANUP_FAILED")
    record["cleanup"] = True
    return validate_proof(record)


def run_isolation_proof(runtime, policy, *, deadline):
    return _run_proof(runtime.binary, policy, deadline=min(deadline, time.monotonic() + 30))


def verify_isolation(runtime, *, executor, policy, deadline):
    return all(asdict(run_isolation_proof(runtime, policy, deadline=deadline)).values())


if __name__ == "__main__":
    if sys.argv[1:] != ["--inner"]:
        raise SystemExit(2)
    try:
        inner_proof()
    except (OSError, ValueError, KeyError, TypeError):
        raise SystemExit(1) from None
