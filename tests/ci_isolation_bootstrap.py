"""CI-only closed isolation lifecycle. Not a production browser capability."""
import hashlib
from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import re
import time

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
    except BaseException:
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
    except (OSError, ValueError):
        pass
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
    except BaseException:
        if not cleanup_policy(policy, executor=executor, deadline=time.monotonic() + 30):
            raise ValueError("CI_POLICY_CLEANUP_FAILED") from None
        raise


def cleanup_policy(policy, *, executor, deadline):
    try:
        require_deadline(deadline)
        return executor.remove_policy(policy, deadline) is True
    except (OSError, ValueError):
        return False
