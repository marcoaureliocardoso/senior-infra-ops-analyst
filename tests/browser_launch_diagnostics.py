#!/usr/bin/env python3
"""Content-free diagnostic reducer; never a runner or an acceptance verifier.

Only bounded bytes enter; only finite categories and bounded numbers leave.
No input, settings, credentials, files, network, or provider access is retained.
Reported stage/exit/cleanup are claims in output, not independent proof.
"""
from __future__ import annotations

import json
import re
import sys
from typing import BinaryIO, TextIO


MAX_LINE_BYTES = 4096
MAX_INPUT_BYTES = 1024 * 1024
MAX_RECORDS = 256
SUPPRESSED = {"category": "UNKNOWN", "reasonCode": "DIAGNOSTIC_SUPPRESSED"}
STAGES = frozenset((
    "STARTUP", "SELF_TEST", "RUNTIME", "INSTALL", "CONFIGURE", "FIXTURE_START",
    "CONTEXT_MAIN", "CONTEXT_ROLE", "MEASUREMENT_SKILL", "MEASUREMENT_SUBAGENT",
    "MEASUREMENT_DISCOVERY", "MEASUREMENT_USE", "WORKFLOW_ALLOW", "WORKFLOW_DENY",
    "FIXTURE_ALLOW", "FIXTURE_DENY", "SIDECAR", "AGGREGATE", "CLEANUP", "FINALIZE", "UNKNOWN",
))
PROBES = frozenset((
    "main-before", "main-after-skill", "main-after-subagent", "main-after-discovery",
    "main-after-use", *(f"role-{n}" for n in range(12)),
))
PTY_REASONS = frozenset(f"PTY_{stage}_FAILED" for stage in (
    "INITIAL_SCREEN", "THEME_SELECTION", "TRUST_SELECTION", "PROMPT_READY", "EXIT",
    "API_KEY_APPROVAL_REQUIRED", "LOGIN_REQUIRED",
    "CONTEXT_INSPECTED", "MOCK_RESPONSE", "MOCK_SECOND_RESPONSE", "CLEAR_OBSERVED",
    "CONTEXT_HEADER_MISSING", "CONTEXT_FREE_SPACE_MISSING", "CONTEXT_VALUES_INVALID",
    "CONTEXT_PROMPT_MISSING", "CONTEXT_FREE_VALUE_SEPARATED", "CONTEXT_FREE_VALUE_MISSING",
    "CONTEXT_RAW_PERCENT_PRESENT", "SKILL_ONE_INVOKED", "SKILL_ONE_CONTEXT", "SKILL_TWO_INVOKED",
    "SKILL_TWO_CONTEXT", "RESUME_TASKS", "REWIND_SELECTION", "REWIND_RESTORE_MODE", "REWIND_OBSERVED",
    "POST_REWIND_TASKS", "POST_REWIND_CONTEXT", "AUTOMATIC_TASK_CREATED", "AUTOMATIC_CONTEXT_INSPECTED",
    "AUTOMATIC_COMPACTION", "TASKS_CREATED", "MANUAL_COMPACTION", "POST_COMPACTION_TASKS",
    "MANUAL_UNFOCUSED_COMPACTION",
)) | {"PTY_EVIDENCE_REJECTED"}
STATUS_REASONS = frozenset((
    "STATUS_CONTEXT_MISSING", "STATUS_CONTEXT_AVAILABLE", "STATUS_CONTEXT_METADATA_UNAVAILABLE",
    "STATUS_CONTEXT_REJECTED",
))
CLAUDE_REJECTIONS = frozenset((
    "CLAUDE_EVIDENCE_REJECTED_INPUT", "CLAUDE_EVIDENCE_REJECTED_PARSER",
    "CLAUDE_EVIDENCE_REJECTED_ALLOWLIST", "CLAUDE_EVIDENCE_REJECTED_CLEANUP",
))
WORKFLOW_REASONS = frozenset((
    "CANARY_EXPOSED", "STREAM_INVALID", "STREAM_INCONCLUSIVE", "WORKFLOW_INCOMPLETE",
    "PERMISSION_INCONCLUSIVE", "DENY_STREAM_INCONCLUSIVE", "WORKFLOW_EVIDENCE_REJECTED",
))
SOURCES = frozenset((
    "ASSISTANT_TEXT", "ASSISTANT_THINKING", "ASSISTANT_TOOL_INPUT", "USER_INPUT", "TOOL_RESULT",
    "SYSTEM_METADATA", "TERMINAL_RESULT", "RAW_INVALID", "UNKNOWN", "MULTIPLE",
))
FINGERPRINT = re.compile(
    r"CLAUDE_FAILURE_EXIT_([1-9][0-9]{0,2})_STREAM_"
    r"(EMPTY|SYSTEM|ASSISTANT|RESULT|RESULT_ERROR|INVALID|OTHER)_TERMINAL_"
    r"(NONE|SUCCESS|MAX_TURNS|MAX_BUDGET|EXECUTION|STRUCTURED_RETRIES|UNKNOWN|INVALID)_"
    r"MODEL_ADVISORY_(PRESENT|ABSENT)_REASON_"
    r"(AUTH|RATE_LIMIT|PROVIDER_MODEL|TRANSPORT|CONTRACT|RUNTIME|PROCESS|TIMEOUT)"
)
# Exact repository-owned messages, mapped to closed codes, never forwarded.
STATIC = {
    "use --self-test, --preflight, or --run-live": ("STARTUP", "MODE_REJECTED"),
    "set P004B_LIVE_AUTHORIZED=1 and I_ACKNOWLEDGE_BOUNDED_SYNTHETIC_BROWSER_PROBES only after exact operator authorization": ("AUTHORIZATION", "LIVE_AUTHORIZATION_MISSING"),
    "I_ACKNOWLEDGE_BOUNDED_SYNTHETIC_BROWSER_PROBES is required": ("AUTHORIZATION", "LIVE_ACK_MISSING"),
    "external permission handlers and variable request counts are unsupported": ("AUTHORIZATION", "AUTHORIZATION_OVERRIDE_REJECTED"),
    "P004B_AUTHORIZED_TOP_LEVEL_INVOCATIONS must equal 6": ("AUTHORIZATION", "INVOCATION_LIMIT_REJECTED"),
    "P004B_AUTHORIZED_MAX_MODEL_TURNS must equal 40": ("AUTHORIZATION", "TURN_LIMIT_REJECTED"),
    "P004B_AUTHORIZED_PROVIDER_ENDPOINT is required": ("AUTHORIZATION", "ENDPOINT_AUTHORIZATION_MISSING"),
    "authorized provider endpoint must be a bounded HTTPS URL without credentials, query, or fragment": ("AUTHORIZATION", "ENDPOINT_AUTHORIZATION_REJECTED"),
    "configured provider endpoint does not match operator authorization": ("AUTHORIZATION", "ENDPOINT_MISMATCH"),
    "temporary directory escaped the verified prefix": ("STARTUP", "TEMPORARY_PATH_REJECTED"),
    "Node.js not found": ("RUNTIME", "NODE_MISSING"),
    "Node.js path is not canonical": ("RUNTIME", "NODE_PATH_REJECTED"),
    "existing browser runtime requires both module and browser cache paths": ("RUNTIME", "BROWSER_PATHS_INCOMPLETE"),
    "browser runtime package root must be an absolute regular directory": ("RUNTIME", "BROWSER_PACKAGE_ROOT_REJECTED"),
    "existing Playwright browser cache is unavailable": ("RUNTIME", "BROWSER_CACHE_UNAVAILABLE"),
    "source browser skill contains an untrusted node_modules directory": ("RUNTIME", "SOURCE_MODULES_REJECTED"),
    "source browser hook launcher not executable": ("RUNTIME", "SOURCE_HOOK_UNAVAILABLE"),
    "GUARD_UNPROVEN": ("GUARD", "GUARD_UNPROVEN"),
    "Claude Code CLI not found": ("RUNTIME", "CLAUDE_MISSING"),
    "Nori CLI not found": ("RUNTIME", "NORI_MISSING"),
    "Claude Code does not advertise --permission-prompt-tool": ("RUNTIME", "PERMISSION_CAPABILITY_MISSING"),
    "Claude Code does not advertise --include-hook-events": ("RUNTIME", "HOOK_CAPABILITY_MISSING"),
    "Nori linked profile layout is unrecognized": ("INSTALL", "PROFILE_LAYOUT_UNRECOGNIZED"),
    "installed browser skill contains an untrusted node_modules directory": ("INSTALL", "INSTALLED_MODULES_REJECTED"),
    "installed browser runtime differs from preflight capability": ("INSTALL", "INSTALLED_RUNTIME_MISMATCH"),
    "installed browser hook launcher not found or not executable": ("CONFIGURE", "BROWSER_HOOK_UNAVAILABLE"),
    "installed browser hook configurator not found": ("CONFIGURE", "BROWSER_CONFIGURATOR_UNAVAILABLE"),
    "installed command hook configurator not found": ("CONFIGURE", "COMMAND_CONFIGURATOR_UNAVAILABLE"),
    "installed command hook launcher not found or not executable": ("CONFIGURE", "COMMAND_HOOK_UNAVAILABLE"),
    "installed browser runner not found": ("CONFIGURE", "BROWSER_RUNNER_UNAVAILABLE"),
    "browser hook configuration was not installed exactly": ("CONFIGURE", "BROWSER_CONFIGURATION_REJECTED"),
    "command hook configuration was not installed exactly": ("CONFIGURE", "COMMAND_CONFIGURATION_REJECTED"),
    "project permission verifier import root already exists": ("CONFIGURE", "VERIFIER_IMPORT_ROOT_REJECTED"),
    "test-only permission handler entered a packaged or installed skill root": ("CONFIGURE", "PERMISSION_HANDLER_PACKAGED"),
    "loopback fixture exited during startup": ("FIXTURE", "FIXTURE_START_FAILED"),
    "workflow sessions collided": ("CONFIGURE", "WORKFLOW_SESSIONS_COLLIDED"),
    "phase-isolated permission MCP configuration could not be created": ("CONFIGURE", "PERMISSION_MCP_CONFIGURATION_REJECTED"),
    "total timeout reached during trusted measurement": ("BUDGET", "TOTAL_TIMEOUT"),
    "invalid context-probe session mode": ("CONTEXT", "CONTEXT_MODE_REJECTED"),
    "invalid trusted measurement stage": ("MEASUREMENT", "MEASUREMENT_STAGE_REJECTED"),
    "measurement MCP signal was not produced": ("MEASUREMENT", "MCP_SIGNAL_MISSING"),
    "invalid workflow phase": ("WORKFLOW_REQUEST", "WORKFLOW_PHASE_REJECTED"),
    "refusing unsafe disposable session-store cleanup": ("SIDECAR", "SESSION_CLEANUP_REJECTED"),
    "disposable Claude session store retained": ("SIDECAR", "SESSION_STORE_RETAINED"),
    "raw prompt, stream, PTY, or transcript retained before sidecar construction": ("SIDECAR", "RAW_EVIDENCE_RETAINED"),
    "synthetic canary retained in disposable output": ("SIDECAR", "CANARY_RETAINED"),
}


def _claude_reason(code: str) -> bool:
    if code in CLAUDE_REJECTIONS:
        return True
    match = FINGERPRINT.fullmatch(code)
    return bool(match and int(match[1]) <= 255
                and (match[5] != "TIMEOUT" or match[1] == "124"))


def reduce_line(raw: bytes) -> dict:
    """Classify one line without echoing arbitrary labels, paths or content."""
    if not isinstance(raw, bytes):
        return dict(SUPPRESSED)
    if raw.endswith(b"\n"):
        raw = raw[:-1].removesuffix(b"\r")
    if len(raw) > MAX_LINE_BYTES:
        return dict(SUPPRESSED)
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeError:
        return dict(SUPPRESSED)
    if any(ord(char) < 32 or ord(char) == 127 for char in text):
        return dict(SUPPRESSED)
    if text.startswith("Warning: Detected unsettled top-level await at "):
        return {"category": "RUNTIME_WARNING", "reasonCode": "UNSETTLED_TOP_LEVEL_AWAIT"}
    if not text.startswith("BLOCKED: "):
        return dict(SUPPRESSED)
    message = text[9:]
    if message in STATIC:
        category, reason = STATIC[message]
        return {"category": category, "reasonCode": reason}
    match = re.fullmatch(r"trusted (context probe|status context|PTY context) failed: ([a-z0-9-]+) \(([A-Z0-9_]+)\)", message)
    if match and match[2] in PROBES:
        allowed = {"context probe": PTY_REASONS, "status context": STATUS_REASONS,
                   "PTY context": {"PTY_CONTEXT_EVIDENCE_REJECTED"}}[match[1]]
        if match[3] in allowed:
            return {"category": "CONTEXT", "reasonCode": match[3], "probe": match[2]}
    match = re.fullmatch(r"trusted measurement stage failed: (skill|subagent|discovery|use) \(([A-Z0-9_]+)\)", message)
    if match and _claude_reason(match[2]):
        return {"category": "MEASUREMENT", "reasonCode": match[2], "measurement": match[1]}
    match = re.fullmatch(r"(allow|deny) workflow request was inconclusive \(([A-Z0-9_]+)\)", message)
    if match and _claude_reason(match[2]):
        return {"category": "WORKFLOW_REQUEST", "reasonCode": match[2], "phase": match[1]}
    match = re.fullmatch(r"(allow|deny) workflow evidence rejected \(([A-Z_]+)(?:; source=([A-Z_]+))?; cleanup=verified\)", message)
    if match and match[2] in WORKFLOW_REASONS and (
        match[3] is None or (match[2] == "CANARY_EXPOSED" and match[3] in SOURCES)
    ):
        result = {"category": "WORKFLOW_EVIDENCE", "reasonCode": match[2],
                  "phase": match[1], "cleanupReported": "verified"}
        if match[3] is not None:
            result["sourceCategory"] = match[3]
        return result
    match = re.fullmatch(r"(unexpected harness exit|harness cleanup failed) \(stage=([A-Z_]+), exit=([0-9]{1,3}), cleanup=(verified|failed)\)", message)
    if match and match[2] in STAGES and 1 <= int(match[3]) <= 255 and (
        (match[1] == "unexpected harness exit" and match[4] == "verified")
        or (match[1] == "harness cleanup failed" and match[4] == "failed")
    ):
        return {"category": "HARNESS", "reasonCode": "UNEXPECTED_EXIT" if match[1] == "unexpected harness exit" else "CLEANUP_FAILED",
                "stageReported": match[2], "exitReported": int(match[3]), "cleanupReported": match[4]}
    match = re.fullmatch(r"browser capability state is not executable: (available_unrecognized|conflict|guard_unproven|outcome_unknown|human_challenge|unavailable)", message)
    if match:
        return {"category": "CAPABILITY", "reasonCode": "CAPABILITY_NOT_EXECUTABLE", "capabilityReported": match[1].upper()}
    return dict(SUPPRESSED)


def reduce_stream(source: BinaryIO, target: TextIO) -> int:
    """Bound reads/output; discard entire overlong lines, never parse suffixes.

    Exit 0 means filtering finished, NOT that the harness passed. Limits return
    2 and require the caller to treat diagnostic coverage as incomplete. The
    caller owns process timeout/termination and independent cleanup validation.
    """
    seen: set[str] = set()
    total = 0
    discarding = False

    def emit(record: dict) -> bool:
        encoded = json.dumps(record, separators=(",", ":"))
        if encoded in seen:
            return True
        if len(seen) >= MAX_RECORDS:
            target.write('{"category":"FILTER","reasonCode":"OUTPUT_LIMIT"}\n')
            return False
        seen.add(encoded)
        target.write(encoded + "\n")
        return True

    while True:
        # Space for both CR and LF, while preserving the payload bound.
        raw = source.readline(min(MAX_LINE_BYTES + 2, MAX_INPUT_BYTES - total + 1))
        if not raw:
            return 0
        total += len(raw)
        if total > MAX_INPUT_BYTES:
            target.write('{"category":"FILTER","reasonCode":"INPUT_LIMIT"}\n')
            return 2
        end_of_line = raw.endswith(b"\n")
        if discarding:
            discarding = not end_of_line
            continue
        if len(raw) > MAX_LINE_BYTES and not end_of_line:
            discarding = True
            record = dict(SUPPRESSED)
        else:
            record = reduce_line(raw)
        if not emit(record):
            return 2


def main() -> int:
    if len(sys.argv) != 1:
        print('{"category":"FILTER","reasonCode":"ARGUMENTS_REJECTED"}')
        return 2
    try:
        return reduce_stream(sys.stdin.buffer, sys.stdout)
    except (OSError, UnicodeError, ValueError):
        try:
            print('{"category":"FILTER","reasonCode":"IO_REJECTED"}')
        except (OSError, UnicodeError, ValueError):
            pass
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
