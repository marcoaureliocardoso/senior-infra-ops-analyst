"""CI-only closed isolation lifecycle. Not a production browser capability."""
import hashlib
import math
import os
import time

from ci_isolation_runtime import (
    BuildReceipt, OwnedRuntime, RuntimeSpec, _read_binary,
    verify_installed_runtime,
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
