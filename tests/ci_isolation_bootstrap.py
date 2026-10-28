"""CI-only closed isolation lifecycle. Not a production browser capability."""
import hashlib
from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import re
import secrets
import shutil
import stat
import sys
import tempfile
import time
from ci_diagnostics import (diagnostic_summary, empty_diagnostics, record_cleanup,
                            record_failure, remember_failure, validate_diagnostics)

from ci_isolation_runtime import (
    BuildReceipt, OwnedRuntime, RuntimeSpec, _read_binary,
    load_runtime_spec, verify_installed_runtime,
)


def require_deadline(deadline):
    if (type(deadline) not in (float, int) or not math.isfinite(deadline)
            or time.monotonic() >= deadline):
        raise ValueError("CI_BOOTSTRAP_DEADLINE")


def provision_runtime(spec: RuntimeSpec, *, executor, deadline: float) -> OwnedRuntime:
    require_deadline(deadline)
    if type(spec) is not RuntimeSpec:
        raise ValueError("RUNTIME_SPEC_INVALID")
    prefix = executor.prefix_base / spec.source_sha256
    if prefix.exists() or prefix.is_symlink():
        raise ValueError("RUNTIME_PREFIX_COLLISION")
    executor.prepare_packages(deadline)
    require_deadline(deadline)
    candidate = executor.build_candidate(spec, deadline)
    data, _ = _read_binary(candidate, os.getuid())
    receipt = BuildReceipt(spec.source_sha256, hashlib.sha256(data).hexdigest(),
                           executor.template_sha256, spec.architecture,
                           spec.version, spec.build_options,
                           owner_nonce=getattr(executor, "nonce", ""))
    require_deadline(deadline)
    runtime = executor.install_candidate(candidate, prefix, receipt, deadline)
    try:
        require_deadline(deadline)
        verify_installed_runtime(runtime)
        executor.publish(runtime)
        return runtime
    except BaseException as error:
        remember_failure(executor, 'PREPARE', error)
        executor.cleanup_owned(runtime, deadline)
        raise


def cleanup_runtime(runtime: OwnedRuntime, *, executor, deadline: float) -> bool:
    try:
        require_deadline(deadline)
        return executor.cleanup_owned(runtime, deadline) is True
    except (OSError, ValueError):
        return False


@dataclass(frozen=True)
class PolicySnapshot:
    enforcing: bool
    restriction: int
    attachments: tuple[str, ...]


@dataclass(frozen=True)
class DenialEvidence:
    executable_identity: str
    time_window: tuple[float, float]
    profile: str
    capability: str
    correlated: bool


@dataclass(frozen=True)
class OwnedPolicy:
    parent_name: str
    child_name: str
    path: Path
    digest: str


@dataclass(frozen=True)
class DiagnosticResult:
    status: str
    reason: str
    evidence: DenialEvidence | None = None


def policy_is_needed(snapshot: PolicySnapshot, evidence: DenialEvidence) -> bool:
    return (type(snapshot) is PolicySnapshot and type(evidence) is DenialEvidence
            and snapshot.enforcing is True and type(snapshot.restriction) is int
            and snapshot.restriction == 1 and snapshot.attachments == ()
            and type(evidence.executable_identity) is str and bool(evidence.executable_identity)
            and type(evidence.time_window) is tuple and len(evidence.time_window) == 2
            and all(type(value) in (float, int) and math.isfinite(value) for value in evidence.time_window)
            and 0 <= evidence.time_window[0] < evidence.time_window[1]
            and evidence.time_window[1] - evidence.time_window[0] <= 120
            and evidence.profile == "unprivileged_userns" and evidence.capability == "net_admin"
            and evidence.correlated is True)


def match_denial_records(raw, *, pids, window, binary):
    if (type(raw) is not bytes or len(raw) > 512 * 1024 or len(pids) > 128
            or not pids or not all(type(pid) is int and pid > 0 for pid in pids)
            or len(window) != 2 or not 0 < window[1] - window[0] <= 120):
        return False
    try:
        for line in raw.splitlines():
            record = json.loads(line)
            timestamp = int(record["__REALTIME_TIMESTAMP"]) / 1_000_000
            if not window[0] <= timestamp <= window[1]:
                continue
            message = record["MESSAGE"]
            if type(message) is not str or len(message) > 4096:
                continue
            quoted = re.findall(r'\b([a-z_]+)="([^"\x00-\x1f]*)"', message)
            fields = dict(quoted)
            matches = re.findall(r"\bpid=([0-9]+)\b", message)
            if len(quoted) != len(fields) or len(matches) != 1:
                continue
            if (int(matches[0]) in pids and fields.get("apparmor") == "DENIED"
                    and fields.get("operation") == "capable" and fields.get("comm") == "bwrap"
                    and fields.get("profile") == "unprivileged_userns"
                    and fields.get("capname") == "net_admin"
                    and fields.get("exe", binary) == binary):
                return True
    except (ValueError, KeyError, TypeError, UnicodeError):
        return False
    return False


def load_policy_template(manifest: Path) -> bytes:
    load_runtime_spec(manifest)
    record = json.loads(manifest.read_bytes())["policyTemplate"]
    root = Path(__file__).resolve().parents[1]
    path = root / record["path"]
    if path.is_symlink():
        raise ValueError("CI_POLICY_TEMPLATE_CHANGED")
    data = path.read_bytes()
    if len(data) > 16384 or hashlib.sha256(data).hexdigest() != record["sha256"]:
        raise ValueError("CI_POLICY_TEMPLATE_CHANGED")
    return data


def render_policy(template, binary, parent, child):
    if (type(template) is not bytes or len(template) > 16384
            or not binary.is_absolute() or ".." in binary.parts
            or not re.fullmatch(r"/[A-Za-z0-9_./-]+/[0-9a-f]{64}/bin/bwrap", str(binary))
            or not re.fullmatch(r"senior-infra-ci-[0-9a-f]{24}", parent)
            or child != parent + "-child"):
        raise ValueError("CI_POLICY_SCOPE_REJECTED")
    text = template.decode("ascii")
    if (text.count("@BINARY@") != 1 or text.count("@PARENT@") != 2
            or text.count("@CHILD@") != 3 or "abi <abi/4.0>," not in text
            or "audit deny capability," not in text or "include if exists" in text):
        raise ValueError("CI_POLICY_TEMPLATE_INVALID")
    text = text.replace("@BINARY@", str(binary)).replace("@PARENT@", parent).replace("@CHILD@", child)
    if "@" in text:
        raise ValueError("CI_POLICY_TEMPLATE_INVALID")
    return text.encode("ascii")


def policy_for_runtime(runtime, template):
    receipt = runtime.receipt
    if not re.fullmatch(r"[0-9a-f]{32}", receipt.owner_nonce):
        raise ValueError("CI_POLICY_OWNERSHIP_UNPROVEN")
    name = "senior-infra-ci-" + hashlib.sha256(
        (receipt.binary_sha256 + receipt.owner_nonce).encode("ascii")).hexdigest()[:24]
    child = name + "-child"
    rendered = render_policy(template, runtime.binary, name, child)
    return OwnedPolicy(name, child, Path("/etc/apparmor.d") / name,
                       hashlib.sha256(rendered).hexdigest())


def diagnose_namespace(runtime, *, executor, deadline):
    deadline = min(deadline, time.monotonic() + 120)
    try:
        require_deadline(deadline)
        verify_installed_runtime(runtime)
        if executor.namespace_probe(runtime, "full", min(deadline, time.monotonic() + 15)):
            return DiagnosticResult("SUPPORTED", "NAMESPACE_BASELINE_PASSED")
        executor.namespace_probe(runtime, "minimal", min(deadline, time.monotonic() + 15))
        evidence = executor.denial_evidence(runtime, deadline)
        snapshot = executor.snapshot_policy(runtime, deadline)
        if (evidence.executable_identity == runtime.receipt.binary_sha256
                and policy_is_needed(snapshot, evidence)):
            return DiagnosticResult("POLICY_NEEDED", "MATCHING_APPARMOR_DENIAL", evidence)
    except (OSError, ValueError) as error:
        remember_failure(executor, 'PREPARE', error)
    return DiagnosticResult("BLOCKED", "NAMESPACE_ATTRIBUTION_UNPROVEN")


def arm_policy(runtime, evidence, *, executor, deadline):
    require_deadline(deadline)
    verify_installed_runtime(runtime)
    snapshot = executor.snapshot_policy(runtime, deadline)
    if (not policy_is_needed(snapshot, evidence)
            or evidence.executable_identity != runtime.receipt.binary_sha256):
        raise ValueError("CI_POLICY_EVIDENCE_REJECTED")
    template = executor.policy_template()
    if hashlib.sha256(template).hexdigest() != runtime.receipt.template_sha256:
        raise ValueError("CI_POLICY_TEMPLATE_CHANGED")
    policy = policy_for_runtime(runtime, template)
    executor.owned_policy = policy  # ownership intent exists before a partial load
    try:
        executor.load_policy(runtime, policy, deadline)
        require_deadline(deadline)
        if (not executor.namespace_probe(runtime, "full", min(deadline, time.monotonic() + 15))
                or not executor.verify_child_transition(runtime, policy, deadline)):
            raise ValueError("CI_POLICY_CHILD_UNPROVEN")
        return policy
    except BaseException as error:
        remember_failure(executor, 'PREPARE', error)
        if not cleanup_policy(policy, executor=executor, deadline=time.monotonic() + 30):
            raise ValueError("CI_POLICY_CLEANUP_FAILED") from None
        raise


def cleanup_policy(policy, *, executor, deadline):
    try:
        require_deadline(deadline)
        return executor.remove_policy(policy, deadline) is True
    except (OSError, ValueError):
        return False


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tests/ci-runtime-lock.json"
MANIFEST_SHA256 = "f478d3c0e4cfe227d689daa713ef2717ec852034cade0761bea2939c6b5704df"
_STATES = frozenset({"PREPARING", "PREPARED", "VERIFIED", "BLOCKED", "CLEANED"})
_REASONS = frozenset({"PREPARING", "PREPARE_PASSED", "VERIFY_PASSED", "PREPARE_BLOCKED",
                      "VERIFY_BLOCKED", "CLEANUP_FAILED", "CLEANUP_PASSED"})
_REPORT_KEYS = {"schemaVersion", "manifestSha256", "nonce", "workspaceIdentity", "state", "reason",
                "runId", "runAttempt", "githubSha", "binarySha256", "upgradeStatus", "upgradePackageCount",
                "policy", "proof", "cleanup", "diagnostics"}


def validate_manifest_argument(value):
    if value not in ("tests/ci-runtime-lock.json", str(MANIFEST)) or MANIFEST.is_symlink():
        raise ValueError("CI_MANIFEST_SCOPE_REJECTED")
    if hashlib.sha256(MANIFEST.read_bytes()).hexdigest() != MANIFEST_SHA256:
        raise ValueError("CI_MANIFEST_IDENTITY_CHANGED")
    load_runtime_spec(MANIFEST)
    return MANIFEST


def validate_report_path(path, runner_temp):
    path, runner_temp = Path(path), Path(runner_temp)
    if (not path.is_absolute() or not runner_temp.is_absolute() or ".." in path.parts
            or path.parent != runner_temp or runner_temp.resolve() != runner_temp
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,80}\.json", path.name)):
        raise ValueError("CI_REPORT_SCOPE_REJECTED")
    info = runner_temp.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o22:
        raise ValueError("CI_REPORT_DIRECTORY_UNSAFE")
    if path.exists() or path.is_symlink():
        info = path.lstat()
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_nlink != 1 or info.st_mode & 0o77):
            raise ValueError("CI_REPORT_FILE_UNSAFE")
    return path


def _hosted_environment():
    import platform
    if (os.geteuid() == 0 or platform.system() != "Linux" or platform.machine() != "x86_64"
            or os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted"
            or os.environ.get("RUNNER_OS") != "Linux"
            or os.environ.get("GITHUB_JOB") not in ("package-validate", "validate", "full-validation")):
        raise ValueError("CI_HOST_SCOPE_REJECTED")
    release = dict(line.split("=", 1) for line in Path("/etc/os-release").read_text().splitlines() if "=" in line)
    if release.get("ID", "").strip('"') != "ubuntu" or release.get("VERSION_ID", "").strip('"') != "24.04":
        raise ValueError("CI_HOST_SCOPE_REJECTED")
    for name in ("GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT"):
        if not re.fullmatch(r"[0-9]{1,24}", os.environ.get(name, "")):
            raise ValueError("CI_RUN_IDENTITY_UNPROVEN")
    if not re.fullmatch(r"[0-9a-f]{40}", os.environ.get("GITHUB_SHA", "")):
        raise ValueError("CI_RUN_IDENTITY_UNPROVEN")
    return Path(os.environ["RUNNER_TEMP"])


def _read_report(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        if info.st_size > 4096:
            raise ValueError("CI_REPORT_INVALID")
        record = json.loads(os.read(fd, 4097))
    finally:
        os.close(fd)
    if (type(record) is not dict or set(record) != _REPORT_KEYS or record["schemaVersion"] != 3
            or record["manifestSha256"] != MANIFEST_SHA256
            or type(record["nonce"]) is not str or not re.fullmatch(r"[0-9a-f]{32}", record["nonce"])
            or record["state"] not in _STATES or record["reason"] not in _REASONS
            or record["runId"] != os.environ.get("GITHUB_RUN_ID")
            or record["runAttempt"] != os.environ.get("GITHUB_RUN_ATTEMPT")
            or record["githubSha"] != os.environ.get("GITHUB_SHA")
            or type(record["policy"]) is not bool or type(record["cleanup"]) is not bool):
        raise ValueError("CI_REPORT_INVALID")
    validate_diagnostics(record['diagnostics'])
    return record


def _save_report(path, record, *, create=False):
    validate_diagnostics(record['diagnostics'])
    data = json.dumps(record, separators=(",", ":"), sort_keys=True).encode("ascii")
    if len(data) > 4096:
        raise ValueError("CI_REPORT_TOO_LARGE")
    if create:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
        return
    # The old record must remain this invocation's owned, bounded aggregate.
    if _read_report(path)["nonce"] != record["nonce"]:
        raise ValueError("CI_REPORT_IDENTITY_CHANGED")
    fd, temporary = tempfile.mkstemp(prefix="ci-report-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if Path(temporary).exists():
            Path(temporary).unlink()


def _workspace(record, runner_temp):
    path = runner_temp / ("senior-infra-ci-" + record["nonce"])
    info = path.lstat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o77
            or [info.st_dev, info.st_ino] != record["workspaceIdentity"]):
        raise ValueError("CI_WORKSPACE_IDENTITY_CHANGED")
    return path


def _runtime_from_disk(spec, nonce):
    from ci_isolation_root import load_owned_runtime
    runtime = load_owned_runtime(spec, nonce)
    verify_installed_runtime(runtime)
    return runtime


def _executor(record, runner_temp):
    from ci_isolation_linux import LinuxExecutor
    template = load_policy_template(MANIFEST)
    spec = load_runtime_spec(MANIFEST)
    executor = LinuxExecutor(spec, _workspace(record, runner_temp), record["nonce"],
                             hashlib.sha256(template).hexdigest())
    return executor


def _cleanup(executor, record, *, deadline):
    spec, nonce = executor.spec, record["nonce"]
    prefix = executor.prefix_base / spec.source_sha256
    try:
        if (prefix.exists() or prefix.is_symlink()
                or (executor.cache / "policy-owner.json").exists()):
            runtime = _runtime_from_disk(spec, nonce)
            policy = policy_for_runtime(runtime, executor.policy_template())
            if not cleanup_policy(policy, executor=executor, deadline=deadline):
                return False
        if prefix.exists() or prefix.is_symlink():
            runtime = _runtime_from_disk(spec, nonce)
            if not cleanup_runtime(runtime, executor=executor, deadline=deadline):
                return False
        if executor.cache.exists() or executor.cache.is_symlink():
            executor.cache_owned = True  # root worker still verifies inode/nonce
            if not executor.cleanup_cache(deadline):
                return False
        workspace = _workspace(record, executor.workspace.parent)
        # Exact resolved, inode-checked owned leaf. Never a workspace/repo root.
        if workspace.parent != executor.workspace.parent or workspace.name != "senior-infra-ci-" + nonce:
            return False
        executor.stage = 'CLEANUP_WORKSPACE'
        shutil.rmtree(workspace)
        return not workspace.exists() and time.monotonic() < deadline
    except (OSError, ValueError, KeyError, TypeError):
        return False


def _publish_github_path(runtime, runner_temp):
    path = Path(os.environ["GITHUB_PATH"])
    if not path.is_absolute() or not path.resolve().is_relative_to(runner_temp) or path.is_symlink():
        raise ValueError("CI_PATH_PUBLICATION_REJECTED")
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o22:
            raise ValueError("CI_PATH_PUBLICATION_REJECTED")
        verify_installed_runtime(runtime)
        os.write(fd, (str(runtime.binary.parent) + "\n").encode("ascii"))
    finally:
        os.close(fd)


def prepare_cli(report_path, runner_temp):
    nonce = secrets.token_hex(16)
    workspace = runner_temp / ("senior-infra-ci-" + nonce)
    workspace.mkdir(mode=0o700)
    info = workspace.stat()
    record = {"schemaVersion": 3, "manifestSha256": MANIFEST_SHA256, "nonce": nonce,
              "workspaceIdentity": [info.st_dev, info.st_ino], "state": "PREPARING", "reason": "PREPARING",
              "runId": os.environ["GITHUB_RUN_ID"], "runAttempt": os.environ["GITHUB_RUN_ATTEMPT"],
              "githubSha": os.environ["GITHUB_SHA"], "binarySha256": "", "upgradeStatus": None,
              "upgradePackageCount": 0, "policy": False, "proof": None, "cleanup": False,
              "diagnostics": empty_diagnostics()}
    try:
        _save_report(report_path, record, create=True)
    except BaseException:
        workspace.rmdir()
        raise
    executor = None
    try:
        executor = _executor(record, runner_temp)
        deadline = time.monotonic() + 600
        runtime = provision_runtime(executor.spec, executor=executor, deadline=deadline)
        diagnostic = diagnose_namespace(runtime, executor=executor, deadline=deadline)
        if diagnostic.status == "POLICY_NEEDED":
            arm_policy(runtime, diagnostic.evidence, executor=executor, deadline=deadline)
            record["policy"] = True
        elif diagnostic.status != "SUPPORTED":
            raise ValueError("CI_NAMESPACE_UNPROVEN")
        record.update(state="PREPARED", reason="PREPARE_PASSED", binarySha256=runtime.receipt.binary_sha256,
                      upgradeStatus=executor.upgrade_decision.status,
                      upgradePackageCount=executor.upgrade_decision.package_count)
        _save_report(report_path, record)
        executor.stage = 'PUBLISH_PATH'
        _publish_github_path(runtime, runner_temp)
    except BaseException as error:
        record_failure(record, 'PREPARE', error, executor)
        record.update(state="BLOCKED", reason="PREPARE_BLOCKED")
        record["cleanup"] = executor is not None and _cleanup(executor, record, deadline=time.monotonic() + 90)
        record_cleanup(record, record['cleanup'], executor)
        if not record["cleanup"]:
            record["reason"] = "CLEANUP_FAILED"
        _save_report(report_path, record)
        raise


def verify_cli(report_path, runner_temp):
    from dataclasses import asdict
    from ci_isolation_probe import run_isolation_proof
    record = _read_report(report_path)
    if record["state"] != "PREPARED" or record["cleanup"]:
        raise ValueError("CI_PREPARE_NOT_PROVEN")
    executor = None
    try:
        executor = _executor(record, runner_temp)
        deadline = time.monotonic() + 120
        executor.stage = 'VERIFY_RUNTIME'
        runtime = _runtime_from_disk(executor.spec, record["nonce"])
        if runtime.receipt.binary_sha256 != record["binarySha256"]:
            raise ValueError("CI_RUNTIME_IDENTITY_CHANGED")
        executor.runtime = runtime
        policy = policy_for_runtime(runtime, executor.policy_template()) if record["policy"] else None
        executor.stage = 'VERIFY_PROOF'
        proof = run_isolation_proof(runtime, policy, deadline=deadline)
        # Mandatory existing helper audit remains distinct from the stronger
        # structural child fixture. Neither path mounts or invokes Claude.
        executor.stage = 'VERIFY_REAL_AUDIT'
        output = executor.command(["/usr/bin/python3", "-B", str(ROOT / "tests/offline-terminal-resume-probe.py"),
                                   "--audit-isolation", "--source", str(ROOT), "--node", os.environ["P004B_TERMINAL_NODE"],
                                   "--module-root", os.environ["P004B_TERMINAL_MODULE_ROOT"]], deadline, limit=4096)
        if json.loads(output) != {"networkIsolated": True, "operatorStateHidden": True,
                                 "capabilitiesDropped": True, "disposableRootAbsent": True}:
            raise ValueError("CI_REAL_AUDIT_UNPROVEN")
        verify_installed_runtime(runtime)
        record.update(state="VERIFIED", reason="VERIFY_PASSED", proof=asdict(proof))
        _save_report(report_path, record)
    except BaseException as error:
        record_failure(record, 'VERIFY', error, executor)
        record.update(state="BLOCKED", reason="VERIFY_BLOCKED", proof=None)
        _save_report(report_path, record)
        raise


def cleanup_cli(report_path, runner_temp):
    record = _read_report(report_path)
    if record["cleanup"]:
        return
    try:
        executor = _executor(record, runner_temp)
    except BaseException as error:
        record_failure(record, 'CLEANUP', error)
        record_cleanup(record, False, None)
        record.update(state='BLOCKED', reason='CLEANUP_FAILED')
        _save_report(report_path, record)
        raise
    success = _cleanup(executor, record, deadline=time.monotonic() + 90)
    record_cleanup(record, success, executor)
    if not success:
        record_failure(record, 'CLEANUP', ValueError('CLEANUP_UNPROVEN'), executor)
    record.update(state="CLEANED" if success else "BLOCKED", cleanup=success,
                  reason="CLEANUP_PASSED" if success else "CLEANUP_FAILED")
    _save_report(report_path, record)
    if not success:
        raise ValueError("CI_CLEANUP_UNPROVEN")


def require_frozen_ci_runtime():
    if os.environ.get("GITHUB_ACTIONS") != "true":
        return  # portable/local package validation uses its mandatory real audit
    runner_temp = _hosted_environment()
    validate_manifest_argument("tests/ci-runtime-lock.json")
    path = validate_report_path(Path(os.environ["CI_ISOLATION_REPORT"]), runner_temp)
    record = _read_report(path)
    from ci_isolation_probe import validate_proof
    if record["state"] != "VERIFIED" or record["cleanup"]:
        raise ValueError("CI_REQUIRED_PROOF_ABSENT")
    validate_proof(record["proof"])
    runtime = _runtime_from_disk(load_runtime_spec(MANIFEST), record["nonce"])
    selected = shutil.which("bwrap")
    if selected != str(runtime.binary) or runtime.receipt.binary_sha256 != record["binarySha256"]:
        raise ValueError("CI_SELECTED_BINARY_CHANGED")


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(add_help=False)
    modes = parser.add_mutually_exclusive_group(required=True)
    for name in ("prepare", "verify", "cleanup"):
        modes.add_argument("--" + name, action="store_true")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args(argv)
    report = None
    try:
        runner_temp = _hosted_environment()  # BEFORE any persistent/privileged action
        validate_manifest_argument(args.manifest)
        report = validate_report_path(Path(args.report), runner_temp)
        if args.prepare:
            prepare_cli(report, runner_temp)
        elif args.verify:
            verify_cli(report, runner_temp)
        else:
            cleanup_cli(report, runner_temp)
        print(diagnostic_summary(_read_report(report)))
        print("CI_BOOTSTRAP_PASSED")
        return 0
    except (OSError, ValueError, KeyError, TypeError, KeyboardInterrupt):
        if report is not None:
            try: print(diagnostic_summary(_read_report(report)))
            except (OSError, ValueError, KeyError, TypeError): pass
        print("CI_BOOTSTRAP_BLOCKED")
        return 1


if __name__ == "__main__":
    # Transport methods lazily import the typed records from the canonical
    # module. Avoid a second class/brand universe when entered as a script.
    sys.modules["ci_isolation_bootstrap"] = sys.modules[__name__]
    raise SystemExit(main())
