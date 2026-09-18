#!/usr/bin/env python3
"""Content-free parser for the opt-in P0-04B runtime harness."""
from __future__ import annotations

import json
import os
import re
import secrets
import shlex
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any


AGGREGATE_FIELDS = {
    "status", "reasonCode", "observedRuntime", "capabilityState", "guardProof",
    "routeClass", "workflow", "roleCount", "toolCalls", "hookEvents", "context",
    "cleanup", "permission",
}
RUNTIME_FIELDS = {"claude", "provider", "model", "adapter"}
WORKFLOW_FIELDS = {
    "executionSteps", "validationSteps", "authentication", "mutation",
    "validation", "outcome",
}
CONTEXT_FIELDS = {
    "before", "afterSkill", "afterSubagent", "afterDiscovery", "afterUse",
    "toolSearchMode",
}
LABEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/+@-]{0,95}$")
CODE = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
CAPABILITY_STATES = {
    "ACTIVE", "AVAILABLE_RECOGNIZED", "AVAILABLE_UNRECOGNIZED", "UNAVAILABLE",
    "CONFLICT", "GUARD_UNPROVEN", "OUTCOME_UNKNOWN", "HUMAN_CHALLENGE",
}
TOOL_SEARCH_MODES = {"available-used", "available-unused", "unavailable"}
ROUTE_CLASSES = {
    "legacy-read-only-multi-command", "workflow-incomplete", "persistent-one-shot",
    "workflow-denied",
}
OBSERVATION_STATES = {"completed", "not-observed"}
WORKFLOW_OUTCOMES = {
    "WORKFLOW_VALIDATED", "WORKFLOW_NOT_APPLIED", "OUTCOME_UNKNOWN", "NOT_OBSERVED",
}
WORKFLOW_EVIDENCE_FIELDS = {
    "operationId", "sessionId", "invocationFingerprint", "expectedEffect", "executionSteps", "validationSteps", "authenticationRequested",
    "mutationRequested", "validationRequested",
}
PERMISSION_FIELDS = {"mode", "allow", "deny", "callCount"}
PERMISSION_SIGNAL_FIELDS = {
    "schemaVersion", "runNonce", "phase", "decision", "callCount",
    "invocationFingerprint", "verified", "inputUnchanged",
}
FIXTURE_OBSERVATION_FIELDS = {"enabled", "revision"}
SHELL_CONTROL = re.compile(r"[\r\n\0;&|<>`]|\$\(")
EXPECTED_ASK_REASON = (
    "ASK_SENSITIVE_OPERATION: stage 1 "
    "BROWSER_PROTECTED_RUNNER/LOW_RISK_CHANGE. Operator confirmation is required "
    "before execution. Sensitive values are redacted."
)
TRUSTED_MEASUREMENT_FIELDS = {
    "schemaVersion", "runNonce", "workflowSessionIds", "roleProbes",
    "contextStages", "toolSearch", "mcp",
}
ROLE_PROBE_FIELDS = {"role", "sessionId", "contextObserved"}
CONTEXT_STAGE_FIELDS = {"stage", "sessionId", "usedPercentage"}
TOOL_SEARCH_FIELDS = {"sessionId", "mode", "discovered", "used"}
MCP_FIELDS = {
    "sessionId", "connected", "toolsListed", "visibleToolCount",
    "discoveryObserved", "useObserved",
}
EXPECTED_ROLES = (
    "audit-evidence-collector", "change-manager", "cloud-platform-operator",
    "database-operator", "diagnostic-operator", "incident-commander",
    "kubernetes-operator", "network-edge-operator", "observability-sre",
    "rca-facilitator", "release-cicd-operator", "security-operations-reviewer",
)
EXPECTED_CONTEXT_STAGES = (
    "before", "afterSkill", "afterSubagent", "afterDiscovery", "afterUse",
)
MAX_TRUSTED_MEASUREMENT_BYTES = 32 * 1024
MEASUREMENT_SAMPLE_FIELDS = {
    "sessionId", "terminalSuccess", "skillCalls", "subagentCalls",
    "toolSearchAvailable", "toolSearchCalls", "mcpCalls", "unexpectedToolCalls",
}
MEASUREMENT_STAGES = {"skill", "subagent", "discovery", "use"}
MEASUREMENT_MCP_FIELDS = {
    "connected", "toolsListed", "visibleToolCount", "called", "callCount",
    "runNonce",
}
MEASUREMENT_SOURCE_FIELDS = {
    "runNonce", "workflowSessionIds", "roleProbes", "contextStages",
    "stageSamples", "mcpSignal",
}
PTY_EVENT_FIELDS = {"kind", "stage", "outcome", "percent", "outputBytes"}
PTY_STAGES = {
    "initial_screen", "theme_selection", "trust_selection", "prompt_ready", "exit",
    "context_inspected", "mock_response", "mock_second_response", "clear_observed",
    "context_header_missing", "context_free_space_missing",
    "context_values_invalid", "context_prompt_missing",
    "context_free_value_separated", "context_free_value_missing",
    "context_raw_percent_present",
    "skill_one_invoked", "skill_one_context", "skill_two_invoked", "skill_two_context",
    "resume_tasks", "rewind_selection", "rewind_restore_mode", "rewind_observed",
    "post_rewind_tasks", "post_rewind_context", "automatic_task_created",
    "automatic_context_inspected", "automatic_compaction", "tasks_created",
    "manual_compaction", "post_compaction_tasks", "manual_unfocused_compaction",
}
PTY_OUTCOMES = {"passed", "failed", "forced", "not-present"}
MAX_PTY_EVENT_BYTES = 64 * 1024


def _exact(value: Any, fields: set[str], name: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError(f"invalid {name} fields")
    return value


def _label(value: Any) -> str:
    if not isinstance(value, str) or not LABEL.fullmatch(value):
        raise ValueError("invalid observed label")
    return value


def _load_pty_events(path: Path) -> list[dict[str, Any]]:
    if path.is_symlink() or not path.is_file():
        raise ValueError("invalid PTY event file")
    size = path.stat().st_size
    if not 0 < size <= MAX_PTY_EVENT_BYTES:
        raise ValueError("invalid PTY event size")
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        value = json.loads(line)
        if (not isinstance(value, dict)
                or not {"kind", "stage", "outcome"} <= set(value) <= PTY_EVENT_FIELDS
                or value["kind"] != "pty-driver"
                or value["stage"] not in PTY_STAGES
                or value["outcome"] not in PTY_OUTCOMES):
            raise ValueError("invalid PTY event")
        for field in ("percent", "outputBytes"):
            if field in value and (type(value[field]) is not int or value[field] < 0):
                raise ValueError("invalid PTY numeric field")
        events.append(value)
        if len(events) > 128:
            raise ValueError("too many PTY events")
    return events


def pty_failure_reason(path: Path) -> str:
    """Reduce private PTY events to one allowlisted content-free failure code."""
    rejected = "PTY_EVIDENCE_REJECTED"
    try:
        events = _load_pty_events(path)
        if not events or events[-1]["outcome"] != "failed":
            return rejected
        reason = f"PTY_{events[-1]['stage'].upper()}_FAILED"
        return reason if CODE.fullmatch(reason) else rejected
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
        return rejected


def pty_context_observation(
    path: Path, session_id: str, output_stage: str,
) -> dict[str, Any]:
    """Accept only the content-free event shape of one completed /context dialogue."""
    _label(session_id)
    if output_stage not in EXPECTED_CONTEXT_STAGES:
        raise ValueError("invalid output context stage")
    events = _load_pty_events(path)
    if len(events) < 4 or any(event["outcome"] == "failed" for event in events):
        raise ValueError("incomplete PTY context dialogue")
    prefix = events[:-2]
    prefix_stages = [event["stage"] for event in prefix]
    allowed_prefix = [
        "initial_screen", "theme_selection", "trust_selection", "prompt_ready",
    ]
    if (not prefix_stages or prefix_stages[0] != "initial_screen"
            or prefix_stages[-1] != "prompt_ready"
            or len(prefix_stages) != len(set(prefix_stages))
            or prefix_stages != [stage for stage in allowed_prefix if stage in prefix_stages]
            or any(set(event) != {"kind", "stage", "outcome"}
                   or event["outcome"] != "passed" for event in prefix)):
        raise ValueError("invalid PTY context prefix")
    context_event, exit_event = events[-2:]
    if (set(context_event) != {"kind", "stage", "outcome", "percent"}
            or context_event["stage"] != "context_inspected"
            or context_event["outcome"] != "passed"
            or type(context_event["percent"]) is not int
            or not 0 <= context_event["percent"] <= 100
            or set(exit_event) != {"kind", "stage", "outcome"}
            or exit_event["stage"] != "exit"
            or exit_event["outcome"] != "passed"):
        raise ValueError("invalid PTY context completion")
    return {
        "stage": output_stage, "sessionId": session_id,
        "usedPercentage": context_event["percent"],
    }


def validate_trusted_measurement(
    value: Any, expected_nonce: str, expected_workflow_sessions: set[str],
) -> dict[str, Any]:
    measurement = _exact(value, TRUSTED_MEASUREMENT_FIELDS, "trusted measurement")
    if type(measurement["schemaVersion"]) is not int or measurement["schemaVersion"] != 1:
        raise ValueError("invalid trusted measurement version")
    if _label(measurement["runNonce"]) != _label(expected_nonce):
        raise ValueError("trusted measurement nonce mismatch")
    workflow_sessions = measurement["workflowSessionIds"]
    if (not isinstance(workflow_sessions, list)
            or not 1 <= len(workflow_sessions) <= 13
            or any(_label(item) != item for item in workflow_sessions)
            or len(set(workflow_sessions)) != len(workflow_sessions)
            or set(workflow_sessions) != expected_workflow_sessions):
        raise ValueError("trusted measurement workflow sessions mismatch")

    role_probes = measurement["roleProbes"]
    if not isinstance(role_probes, list) or len(role_probes) != len(EXPECTED_ROLES):
        raise ValueError("invalid trusted role probes")
    observed_roles: list[str] = []
    role_sessions: list[str] = []
    for item in role_probes:
        probe = _exact(item, ROLE_PROBE_FIELDS, "trusted role probe")
        observed_roles.append(_label(probe["role"]))
        role_sessions.append(_label(probe["sessionId"]))
        if probe["contextObserved"] is not True:
            raise ValueError("trusted role context not observed")
    if tuple(observed_roles) != EXPECTED_ROLES or len(set(role_sessions)) != len(role_sessions):
        raise ValueError("trusted role coverage mismatch")

    context_stages = measurement["contextStages"]
    if not isinstance(context_stages, list) or len(context_stages) != 5:
        raise ValueError("invalid trusted context stages")
    observed_stages: list[str] = []
    context_sessions: list[str] = []
    for item in context_stages:
        stage = _exact(item, CONTEXT_STAGE_FIELDS, "trusted context stage")
        observed_stages.append(stage["stage"])
        context_sessions.append(_label(stage["sessionId"]))
        percent = stage["usedPercentage"]
        if (not isinstance(percent, int) or isinstance(percent, bool)
                or not 0 <= percent <= 100):
            raise ValueError("invalid trusted context percentage")
    if tuple(observed_stages) != EXPECTED_CONTEXT_STAGES or len(set(context_sessions)) != 1:
        raise ValueError("trusted context sequence mismatch")
    context_session = context_sessions[0]

    tool_search = _exact(measurement["toolSearch"], TOOL_SEARCH_FIELDS, "tool search")
    if _label(tool_search["sessionId"]) != context_session:
        raise ValueError("tool search session mismatch")
    if tool_search["mode"] not in TOOL_SEARCH_MODES:
        raise ValueError("invalid tool search mode")
    if type(tool_search["discovered"]) is not bool or type(tool_search["used"]) is not bool:
        raise ValueError("invalid tool search observation")
    expected_search = {
        "available-used": (True, True),
        "available-unused": (True, False),
        "unavailable": (False, False),
    }[tool_search["mode"]]
    if (tool_search["discovered"], tool_search["used"]) != expected_search:
        raise ValueError("incoherent tool search observation")

    mcp = _exact(measurement["mcp"], MCP_FIELDS, "mcp measurement")
    if _label(mcp["sessionId"]) != context_session:
        raise ValueError("mcp session mismatch")
    for field in ("connected", "toolsListed", "discoveryObserved", "useObserved"):
        if mcp[field] is not True:
            raise ValueError("incomplete mcp observation")
    if (not isinstance(mcp["visibleToolCount"], int)
            or isinstance(mcp["visibleToolCount"], bool)
            or not 1 <= mcp["visibleToolCount"] <= 4096):
        raise ValueError("invalid mcp tool count")
    return measurement


def _load_private_json(path: Path, maximum_bytes: int) -> Any | None:
    if os.name == "nt" or not hasattr(os, "O_NOFOLLOW"):
        return None
    descriptor: int | None = None
    try:
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
        flags |= getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        metadata = os.fstat(descriptor)
        if (not stat.S_ISREG(metadata.st_mode)
                or not 1 <= metadata.st_size <= maximum_bytes):
            return None
        if os.name != "nt" and stat.S_IMODE(metadata.st_mode) & 0o077:
            return None
        chunks: list[bytes] = []
        remaining = maximum_bytes + 1
        while remaining > 0:
            chunk = os.read(descriptor, remaining)
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        payload = b"".join(chunks)
        if len(payload) != metadata.st_size or len(payload) > maximum_bytes:
            return None
        return json.loads(payload.decode("utf-8"))
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
        return None
    finally:
        if descriptor is not None:
            os.close(descriptor)


def load_trusted_measurement(
    path: Path, expected_nonce: str, expected_workflow_sessions: set[str],
) -> dict[str, Any] | None:
    value = _load_private_json(path, MAX_TRUSTED_MEASUREMENT_BYTES)
    if value is None:
        return None
    try:
        return validate_trusted_measurement(
            value, expected_nonce, expected_workflow_sessions,
        )
    except ValueError:
        return None


def evaluate_measurement_stream(
    path: Path, expected_session: str, expected_stage: str, run_nonce: str,
) -> dict[str, Any]:
    _label(expected_session)
    _label(run_nonce)
    expected_calls: dict[str, tuple[str, dict[str, str], str]] = {
        "skill": (
            "Skill", {"skill": "context-continuity"}, "skillCalls",
        ),
        "subagent": (
            "Agent", {
                "description": "P004B_SUBAGENT_ACK",
                "prompt": "P004B_SUBAGENT_ACK",
                "subagent_type": "diagnostic-operator",
            }, "subagentCalls",
        ),
        "discovery": (
            "ToolSearch",
            {"query": "select:mcp__p004b-context__context_fixture_ping"},
            "toolSearchCalls",
        ),
        "use": (
            "mcp__p004b-context__context_fixture_ping",
            {"nonce": run_nonce}, "mcpCalls",
        ),
    }
    if expected_stage not in expected_calls:
        raise ValueError("invalid measurement stage")
    expected_name, expected_input, expected_count = expected_calls[expected_stage]
    empty = {
        "sessionId": expected_session, "terminalSuccess": False,
        "skillCalls": 0, "subagentCalls": 0,
        "toolSearchAvailable": False, "toolSearchCalls": 0,
        "mcpCalls": 0, "unexpectedToolCalls": 0,
    }
    try:
        if (not path.is_file() or path.stat().st_size > 5_000_000
                or path.stat().st_size < 1):
            return empty
        init_seen = False
        terminal_seen = False
        malformed = False
        tools: set[str] = set()
        calls: dict[str, bool] = {}
        call_counts = {
            "skillCalls": 0, "subagentCalls": 0, "toolSearchCalls": 0,
            "mcpCalls": 0, "unexpectedToolCalls": 0,
        }
        with path.open("r", encoding="utf-8") as stream:
            for line in stream:
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    malformed = True
                    continue
                if not isinstance(event, dict):
                    malformed = True
                    continue
                event_type = event.get("type")
                session_id = event.get("session_id")
                if event_type == "system" and event.get("subtype") == "init":
                    advertised = event.get("tools")
                    if (init_seen or session_id != expected_session
                            or not isinstance(advertised, list)
                            or len(advertised) > 4096
                            or any(not isinstance(name, str) or not LABEL.fullmatch(name)
                                   for name in advertised)):
                        malformed = True
                    else:
                        init_seen = True
                        tools.update(advertised)
                elif event_type in {"assistant", "user"}:
                    message = event.get("message")
                    content = message.get("content") if isinstance(message, dict) else None
                    if not isinstance(content, list) or len(content) > 64:
                        malformed = True
                        continue
                    tool_blocks = [
                        block for block in content
                        if isinstance(block, dict)
                        and block.get("type") in {"tool_use", "tool_result"}
                    ]
                    if tool_blocks and session_id != expected_session:
                        malformed = True
                    for block in tool_blocks:
                        if terminal_seen or event.get("parent_tool_use_id") is not None:
                            malformed = True
                        if block.get("type") == "tool_use":
                            name = block.get("name")
                            identifier = block.get("id")
                            tool_input = block.get("input")
                            if (not isinstance(name, str) or not LABEL.fullmatch(name)
                                    or not isinstance(identifier, str)
                                    or not LABEL.fullmatch(identifier)
                                    or identifier in calls):
                                malformed = True
                                continue
                            if name != expected_name or tool_input != expected_input:
                                call_counts["unexpectedToolCalls"] += 1
                                malformed = True
                                continue
                            call_counts[expected_count] += 1
                            calls[identifier] = False
                        else:
                            identifier = block.get("tool_use_id")
                            is_error = block.get("is_error")
                            if (not isinstance(identifier, str)
                                    or not LABEL.fullmatch(identifier)
                                    or identifier not in calls or calls.get(identifier) is True
                                    or (is_error is not None and is_error is not False)):
                                malformed = True
                                continue
                            calls[identifier] = True
                elif event_type == "result":
                    if (terminal_seen or session_id != expected_session
                            or event.get("subtype") != "success"
                            or event.get("is_error") is not False
                            or not calls or not all(calls.values())):
                        malformed = True
                    else:
                        terminal_seen = True
        if malformed or not init_seen or not terminal_seen:
            return empty
        return {
            "sessionId": expected_session, "terminalSuccess": True,
            "skillCalls": call_counts["skillCalls"],
            "subagentCalls": call_counts["subagentCalls"],
            "toolSearchAvailable": "ToolSearch" in tools,
            "toolSearchCalls": call_counts["toolSearchCalls"],
            "mcpCalls": call_counts["mcpCalls"],
            "unexpectedToolCalls": call_counts["unexpectedToolCalls"],
        }
    except (OSError, UnicodeError):
        return empty


def status_context_observation(
    path: Path, run_nonce: str, session_id: str, output_stage: str,
) -> dict[str, Any]:
    _label(run_nonce)
    _label(session_id)
    if output_stage not in EXPECTED_CONTEXT_STAGES:
        raise ValueError("invalid output context stage")
    if not path.is_file() or not 1 <= path.stat().st_size <= 64 * 1024:
        raise ValueError("invalid status event file")
    observations: list[tuple[int, int]] = []
    with path.open("r", encoding="utf-8") as stream:
        for line in stream:
            event = json.loads(line)
            if isinstance(event, dict) and event.get("kind") == "status-context-unavailable":
                event = _exact(event, {
                    "kind", "reasonCode", "runNonce", "stage",
                }, "status context unavailable event")
                if (observations
                        or event["reasonCode"] != "NATIVE_FIELDS_NOT_SUPPLIED"
                        or event["runNonce"] != run_nonce
                        or event["stage"] != output_stage):
                    raise ValueError("invalid status context unavailable event")
                continue
            event = _exact(event, {
                "kind", "percent", "windowTokens", "runNonce", "stage",
            }, "status context event")
            percent = event["percent"]
            window = event["windowTokens"]
            if (event["kind"] != "status-context"
                    or event["runNonce"] != run_nonce
                    or event["stage"] != output_stage
                    or not isinstance(percent, int) or isinstance(percent, bool)
                    or not 0 <= percent <= 100
                    or not isinstance(window, int) or isinstance(window, bool)
                    or not 0 < window <= 10_000_000):
                raise ValueError("invalid status context event")
            observations.append((percent, window))
    if not observations or len({window for _, window in observations}) != 1:
        raise ValueError("native status context not observed coherently")
    return {
        "stage": output_stage, "sessionId": session_id,
        "usedPercentage": observations[-1][0],
    }


def status_context_failure_reason(
    path: Path, run_nonce: str, session_id: str, output_stage: str,
) -> str:
    """Reduce status-line collection state to one content-free reason code."""
    try:
        if path.is_symlink():
            return "STATUS_CONTEXT_REJECTED"
        if not path.is_file() or path.stat().st_size == 0:
            return "STATUS_CONTEXT_MISSING"
        try:
            status_context_observation(path, run_nonce, session_id, output_stage)
            return "STATUS_CONTEXT_AVAILABLE"
        except ValueError:
            pass
        lines = path.read_text(encoding="utf-8").splitlines()
        if lines and all(json.loads(line) == {
                "kind": "status-context-unavailable",
                "reasonCode": "NATIVE_FIELDS_NOT_SUPPLIED",
                "runNonce": run_nonce,
                "stage": output_stage,
            } for line in lines):
            return "STATUS_CONTEXT_METADATA_UNAVAILABLE"
        return "STATUS_CONTEXT_REJECTED"
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
        return "STATUS_CONTEXT_REJECTED"


def build_trusted_measurement(
    run_nonce: str, workflow_sessions: list[str], role_probes: Any,
    context_stages: Any, stage_samples: Any, mcp_signal: Any,
) -> dict[str, Any]:
    if not isinstance(stage_samples, dict) or set(stage_samples) != MEASUREMENT_STAGES:
        raise ValueError("invalid measurement stage set")
    normalized: dict[str, dict[str, Any]] = {}
    for stage, value in stage_samples.items():
        sample = _exact(value, MEASUREMENT_SAMPLE_FIELDS, f"{stage} measurement")
        _label(sample["sessionId"])
        if type(sample["terminalSuccess"]) is not bool or type(sample["toolSearchAvailable"]) is not bool:
            raise ValueError("invalid measurement boolean")
        for field in MEASUREMENT_SAMPLE_FIELDS - {
            "sessionId", "terminalSuccess", "toolSearchAvailable",
        }:
            if (not isinstance(sample[field], int) or isinstance(sample[field], bool)
                    or not 0 <= sample[field] <= 64):
                raise ValueError("invalid measurement call count")
        if sample["terminalSuccess"] is not True:
            raise ValueError("measurement stage did not complete")
        normalized[stage] = sample
    context_sessions = {
        item.get("sessionId") for item in context_stages if isinstance(item, dict)
    } if isinstance(context_stages, list) else set()
    if (len(context_sessions) != 1
            or any(sample["sessionId"] not in context_sessions for sample in normalized.values())):
        raise ValueError("measurement stages are not same-session")
    expected_calls = {
        "skill": {"skillCalls": 1},
        "subagent": {"subagentCalls": 1},
        "use": {"mcpCalls": 1},
    }
    count_fields = {
        "skillCalls", "subagentCalls", "toolSearchCalls", "mcpCalls",
        "unexpectedToolCalls",
    }
    for stage, requirements in expected_calls.items():
        for field in count_fields:
            expected = requirements.get(field, 0)
            if normalized[stage][field] != expected:
                raise ValueError(f"unexpected {stage} tool calls")
    available = normalized["discovery"]["toolSearchAvailable"]
    search_calls = normalized["discovery"]["toolSearchCalls"]
    searched = search_calls == 1
    if (search_calls != (1 if available else 0)
            or any(normalized["discovery"][field] != 0 for field in count_fields - {"toolSearchCalls"})):
        raise ValueError("tool search measurement is incoherent")
    mcp = _exact(mcp_signal, MEASUREMENT_MCP_FIELDS, "measurement mcp signal")
    if any(mcp[field] is not True for field in ("connected", "toolsListed", "called")):
        raise ValueError("mcp lifecycle incomplete")
    if (not isinstance(mcp["visibleToolCount"], int)
            or isinstance(mcp["visibleToolCount"], bool)
            or not 1 <= mcp["visibleToolCount"] <= 4096):
        raise ValueError("invalid measurement mcp tool count")
    if (mcp["callCount"] != 1 or mcp["runNonce"] != run_nonce):
        raise ValueError("measurement mcp call is not uniquely nonce-bound")
    tool_mode = (
        "available-used" if searched else
        "available-unused" if available else
        "unavailable"
    )
    context_session = next(iter(context_sessions))
    result = {
        "schemaVersion": 1,
        "runNonce": run_nonce,
        "workflowSessionIds": workflow_sessions,
        "roleProbes": role_probes,
        "contextStages": context_stages,
        "toolSearch": {
            "sessionId": context_session, "mode": tool_mode,
            "discovered": available, "used": searched,
        },
        "mcp": {
            "sessionId": context_session, "connected": True,
            "toolsListed": True, "visibleToolCount": mcp["visibleToolCount"],
            "discoveryObserved": True, "useObserved": True,
        },
    }
    return validate_trusted_measurement(result, run_nonce, set(workflow_sessions))


def build_trusted_measurement_from_source(value: Any) -> dict[str, Any]:
    source = _exact(value, MEASUREMENT_SOURCE_FIELDS, "measurement source")
    return build_trusted_measurement(
        source["runNonce"], source["workflowSessionIds"], source["roleProbes"],
        source["contextStages"], source["stageSamples"], source["mcpSignal"],
    )


def write_private_measurement(path: Path, value: dict[str, Any]) -> None:
    if os.name == "nt" or not hasattr(os, "O_NOFOLLOW") or not path.is_absolute():
        raise ValueError("private measurement output requires POSIX absolute path")
    payload = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    if not 1 <= len(payload) <= MAX_TRUSTED_MEASUREMENT_BYTES:
        raise ValueError("invalid private measurement size")
    temporary = path.with_name(f".{path.name}.{secrets.token_hex(12)}.tmp")
    descriptor: int | None = None
    try:
        descriptor = os.open(
            temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW"),
            0o600,
        )
        remaining = memoryview(payload)
        while remaining:
            written = os.write(descriptor, remaining)
            if written <= 0:
                raise OSError("private measurement write made no progress")
            remaining = remaining[written:]
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = None
        os.replace(temporary, path)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def validate_aggregate(value: Any, *, allow_pending_cleanup: bool = False) -> dict[str, Any]:
    result = _exact(value, AGGREGATE_FIELDS, "aggregate")
    if result["status"] not in {"pass", "fail", "inconclusive"}:
        raise ValueError("invalid aggregate status")
    if not isinstance(result["reasonCode"], str) or not CODE.fullmatch(result["reasonCode"]):
        raise ValueError("invalid reason code")
    runtime = _exact(result["observedRuntime"], RUNTIME_FIELDS, "runtime")
    for observed in runtime.values():
        _label(observed)
    if result["capabilityState"] not in CAPABILITY_STATES:
        raise ValueError("invalid capability state")
    if result["guardProof"] not in {
        "exact-deny", "exact-bound-read", "exact-native-approval",
    }:
        raise ValueError("invalid guard proof")
    if result["routeClass"] not in ROUTE_CLASSES:
        raise ValueError("invalid route class")
    workflow = _exact(result["workflow"], WORKFLOW_FIELDS, "workflow")
    for field, maximum in (("executionSteps", 208), ("validationSteps", 156)):
        if (not isinstance(workflow[field], int) or isinstance(workflow[field], bool)
                or not 0 <= workflow[field] <= maximum):
            raise ValueError("invalid workflow step count")
    for field in ("authentication", "mutation", "validation"):
        if workflow[field] not in OBSERVATION_STATES:
            raise ValueError("invalid workflow observation")
    if workflow["outcome"] not in WORKFLOW_OUTCOMES:
        raise ValueError("invalid workflow outcome")
    permission = _exact(result["permission"], PERMISSION_FIELDS, "permission")
    if (permission["mode"] != "synthetic-deterministic"
            or permission["allow"] not in {"completed", "not-observed"}
            or permission["deny"] not in {"completed", "not-observed"}
            or not isinstance(permission["callCount"], int)
            or isinstance(permission["callCount"], bool)
            or not 0 <= permission["callCount"] <= 2):
        raise ValueError("invalid permission evidence")
    expected_permission_calls = sum(
        permission[field] == "completed" for field in ("allow", "deny")
    )
    if permission["callCount"] != expected_permission_calls:
        raise ValueError("incoherent permission call count")
    if (not isinstance(result["roleCount"], int) or isinstance(result["roleCount"], bool)
            or not 0 <= result["roleCount"] <= 12):
        raise ValueError("invalid role count")
    if result["status"] == "pass" and result["roleCount"] != 12:
        raise ValueError("active result lacks all role observations")
    for field in ("toolCalls", "hookEvents"):
        if not isinstance(result[field], int) or isinstance(result[field], bool) or result[field] < 0:
            raise ValueError(f"invalid {field}")
    completed = all(workflow[field] == "completed" for field in (
        "authentication", "mutation", "validation",
    ))
    if result["status"] == "pass" and (
        result["capabilityState"] != "ACTIVE"
        or result["routeClass"] != "persistent-one-shot"
        or result["guardProof"] != "exact-native-approval"
        or workflow["executionSteps"] < 1
        or workflow["validationSteps"] < 1
        or workflow["outcome"] != "WORKFLOW_VALIDATED"
        or not completed
        or result["toolCalls"] < 4
        or result["hookEvents"] < 3
        or permission != {
            "mode": "synthetic-deterministic", "allow": "completed",
            "deny": "completed", "callCount": 2,
        }
    ):
        raise ValueError("passing result lacks active runtime proof")
    if result["capabilityState"] == "ACTIVE" and result["status"] != "pass":
        raise ValueError("active result lacks completed workflow")
    if (result["routeClass"] == "persistent-one-shot" or completed
            or "completed" in {workflow["authentication"], workflow["mutation"], workflow["validation"]}) and (
        result["guardProof"] != "exact-native-approval"
        or workflow["outcome"] != "WORKFLOW_VALIDATED"
        or not completed
    ):
        raise ValueError("workflow completion claim lacks observed proof")
    if result["routeClass"] == "legacy-read-only-multi-command" and (
        workflow["executionSteps"] != 0 or workflow["validationSteps"] != 0
        or workflow["outcome"] != "NOT_OBSERVED" or completed
    ):
        raise ValueError("legacy route contains workflow claims")
    context = _exact(result["context"], CONTEXT_FIELDS, "context")
    for field in CONTEXT_FIELDS - {"toolSearchMode"}:
        if not isinstance(context[field], int) or isinstance(context[field], bool) or not 0 <= context[field] <= 100:
            raise ValueError("invalid context percentage")
    if context["toolSearchMode"] not in TOOL_SEARCH_MODES:
        raise ValueError("invalid tool search mode")
    if result["cleanup"] != "verified" and not (
        allow_pending_cleanup and result["cleanup"] == "pending"
    ):
        raise ValueError("cleanup is not verified")
    return result


def _stream_records(event: dict[str, Any]):
    records = [event]
    wrapped = event.get("event")
    if event.get("type") == "stream" and isinstance(wrapped, dict):
        records.append(wrapped)
    for record in records:
        provenance = {
            "sessionId": record.get("session_id"),
            "parentToolUseId": record.get("parent_tool_use_id"),
        }
        yield record, provenance
        message = record.get("message")
        if record.get("type") in {"assistant", "user"} and isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, list) and len(content) <= 64:
                for block in content:
                    if (isinstance(block, dict)
                            and block.get("type") in {"tool_use", "tool_result"}):
                        yield block, provenance


def _workflow_command(command: Any) -> dict[str, Any] | None:
    if not isinstance(command, str) or not 1 <= len(command) <= 65536:
        return None
    if SHELL_CONTROL.search(command):
        return None
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        return None
    if len(tokens) < 6 or tokens[0] != "node":
        return None
    runner = Path(tokens[1])
    expected_runner = Path(os.environ.get(
        "P004B_EXPECTED_RUNNER_PATH",
        Path(__file__).resolve().parents[1]
        / "skills" / "browser-operations" / "scripts" / "browser-runner.mjs",
    ))
    if not runner.is_absolute() or not expected_runner.is_absolute():
        return None
    if os.path.normcase(str(runner.resolve())) != os.path.normcase(str(expected_runner.resolve())):
        return None
    args = tokens[2:]
    if len(args) % 2 or any(
        not isinstance(args[index], str) or not args[index].startswith("--")
        for index in range(0, len(args), 2)
    ):
        return None
    node_bin = os.environ.get("P004B_EVIDENCE_NODE_BIN") or shutil.which("node")
    helper = Path(__file__).with_name("browser-workflow-evidence.mjs")
    if not node_bin or not helper.is_file():
        return None
    try:
        completed = subprocess.run(
            [node_bin, str(helper), *args], capture_output=True, text=True,
            timeout=5, check=False,
        )
        if (completed.returncode != 0 or completed.stderr
                or len(completed.stdout) > 4096):
            return None
        observed = _exact(json.loads(completed.stdout), WORKFLOW_EVIDENCE_FIELDS, "workflow evidence")
    except (OSError, subprocess.SubprocessError, ValueError, json.JSONDecodeError):
        return None
    if (not isinstance(observed["operationId"], str)
            or not LABEL.fullmatch(observed["operationId"])):
        return None
    if (not isinstance(observed["sessionId"], str)
            or not LABEL.fullmatch(observed["sessionId"])
            or not isinstance(observed["invocationFingerprint"], str)
            or not re.fullmatch(r"[0-9a-f]{64}", observed["invocationFingerprint"])):
        return None
    if observed["expectedEffect"] not in {
        "PUBLIC_READ", "SENSITIVE_READ", "INTERACTIVE_STATE", "LOW_RISK_CHANGE",
        "DISRUPTIVE_CHANGE", "DESTRUCTIVE_CHANGE",
    }:
        return None
    for field, maximum in (("executionSteps", 16), ("validationSteps", 12)):
        if (not isinstance(observed[field], int) or isinstance(observed[field], bool)
                or not 1 <= observed[field] <= maximum):
            return None
    if any(not isinstance(observed[field], bool) for field in (
        "authenticationRequested", "mutationRequested", "validationRequested",
    )):
        return None
    return observed


def _workflow_result(content: Any, operation_id: str, expected_effect: str) -> str | None:
    candidates: list[str] = []
    if isinstance(content, str) and len(content) <= 4096:
        candidates.append(content)
    elif isinstance(content, list) and len(content) <= 8:
        candidates.extend(
            block["text"] for block in content
            if isinstance(block, dict) and block.get("type") == "text"
            and isinstance(block.get("text"), str) and len(block["text"]) <= 4096
        )
    if len(candidates) != 1:
        return None
    try:
        value = json.loads(candidates[0])
    except json.JSONDecodeError:
        return None
    if (not isinstance(value, dict)
            or set(value) != {
                "status", "reasonCode", "operationId", "step", "effect",
                "validationRequired", "observation",
            }
            or value.get("operationId") != operation_id
            or value.get("step") != "workflow"
            or value.get("effect") != expected_effect
            or value.get("observation") is not None):
        return None
    coherent = {
        "WORKFLOW_VALIDATED": ("ok", False),
        "WORKFLOW_NOT_APPLIED": ("ok", False),
        "OUTCOME_UNKNOWN": ("outcome-unknown", True),
    }
    expected = coherent.get(value.get("reasonCode"))
    if expected is None or (value.get("status"), value.get("validationRequired")) != expected:
        return None
    return value["reasonCode"]


def evaluate_stream(path: Path, canary: str) -> dict[str, Any]:
    if not path.is_file() or path.stat().st_size > 5_000_000:
        return {"status": "inconclusive", "reasonCode": "STREAM_INVALID", "toolCalls": 0}
    tool_calls = 0
    bash_tool_uses = 0
    result_seen = False
    terminal_count = 0
    canary_seen = False
    malformed = False
    hook_events = 0
    workflow_calls: dict[str, dict[str, Any]] = {}
    active_call_id: str | None = None
    hook_starts: dict[str, dict[str, str]] = {}
    completed_hook_ids: set[str] = set()
    orphan_expected_hook = False

    def hook_name_matches(value: Any, event: Any) -> bool:
        return (
            event in {"PreToolUse", "PostToolUse", "PostToolUseFailure"}
            and value == f"{event}:Bash"
        )

    def invalidate_active() -> None:
        if active_call_id in workflow_calls:
            workflow_calls[active_call_id]["invalid"] = True

    def record_identity(provenance: dict[str, Any]) -> tuple[str, str | None] | None:
        session_id = provenance.get("sessionId")
        parent_tool_use_id = provenance.get("parentToolUseId")
        if (not isinstance(session_id, str) or not LABEL.fullmatch(session_id)
                or (parent_tool_use_id is not None
                    and (not isinstance(parent_tool_use_id, str)
                         or not LABEL.fullmatch(parent_tool_use_id)))):
            return None
        return session_id, parent_tool_use_id

    def pre_decision(value: dict[str, Any]) -> str | None:
        stdout = value.get("stdout")
        if (not isinstance(stdout, str) or len(stdout) > 4096
                or value.get("output") != stdout or value.get("stderr") != ""):
            return None
        try:
            parsed = _exact(json.loads(stdout), {"hookSpecificOutput"}, "hook response")
            hook = _exact(parsed["hookSpecificOutput"], {
                "hookEventName", "permissionDecision", "permissionDecisionReason",
            }, "hook decision")
        except (ValueError, json.JSONDecodeError):
            return None
        reason = hook.get("permissionDecisionReason")
        if (hook.get("hookEventName") != "PreToolUse"
                or reason != EXPECTED_ASK_REASON):
            return None
        decision = hook.get("permissionDecision")
        return decision if decision in {"allow", "ask", "deny"} else None

    with path.open("r", encoding="utf-8") as stream:
        for line in stream:
            if canary and canary in line:
                canary_seen = True
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                malformed = True
                continue
            if not isinstance(event, dict):
                malformed = True
                continue
            for value, provenance in _stream_records(event):
                event_type = value.get("type")
                if event_type in {"tool_use", "tool_result"}:
                    tool_calls += 1
                if event_type == "result":
                    terminal_count += 1
                    terminal_valid = (
                        terminal_count == 1
                        and value.get("subtype") == "success"
                        and value.get("is_error") is False
                        and active_call_id in workflow_calls
                        and workflow_calls[active_call_id]["phase"] == "post-success"
                        and value.get("session_id")
                        == workflow_calls[active_call_id].get("sessionId")
                    )
                    if terminal_valid:
                        result_seen = True
                    else:
                        malformed = True
                        invalidate_active()
                tool_use_id = value.get("id") if event_type == "tool_use" else value.get("tool_use_id")
                if event_type == "tool_use" and value.get("name") == "Bash":
                    bash_tool_uses += 1
                    if active_call_id is not None:
                        invalidate_active()
                    tool_input = value.get("input")
                    observation = _workflow_command(
                        tool_input.get("command") if isinstance(tool_input, dict) else None
                    )
                    identity = record_identity(provenance)
                    if (observation is not None and isinstance(tool_use_id, str)
                            and LABEL.fullmatch(tool_use_id)):
                        if tool_use_id in workflow_calls:
                            workflow_calls[tool_use_id]["invalid"] = True
                        else:
                            workflow_calls[tool_use_id] = {
                                **observation, "phase": "tool-use",
                                "invalid": (
                                    orphan_expected_hook or bash_tool_uses != 1
                                    or identity is None
                                    or observation["sessionId"] != (identity[0] if identity else None)
                                ),
                                "outcome": "NOT_OBSERVED",
                                "toolSessionId": identity[0] if identity else None,
                                "parentToolUseId": identity[1] if identity else None,
                            }
                            active_call_id = tool_use_id
                elif event_type == "tool_use":
                    malformed = True
                    invalidate_active()

                if (event_type == "tool_result" and isinstance(tool_use_id, str)
                        and tool_use_id in workflow_calls):
                    call = workflow_calls[tool_use_id]
                    outcome = _workflow_result(
                        value.get("content"), call["operationId"], call["expectedEffect"],
                    )
                    identity = record_identity(provenance)
                    if (call["phase"] != "pre-approved" or outcome is None
                            or identity != (
                                call["toolSessionId"], call["parentToolUseId"],
                            )):
                        call["invalid"] = True
                    else:
                        call["phase"] = "tool-result"
                        call["outcome"] = outcome
                elif event_type == "tool_result":
                    malformed = True
                    invalidate_active()

                if (event_type == "system" and value.get("subtype") == "hook_started"
                        and hook_name_matches(value.get("hook_name"), value.get("hook_event"))
                        and value.get("hook_event") in {
                            "PreToolUse", "PostToolUse", "PostToolUseFailure",
                        }):
                    hook_id = value.get("hook_id")
                    hook_event = value.get("hook_event")
                    session_id = value.get("session_id")
                    if (not isinstance(hook_id, str) or not LABEL.fullmatch(hook_id)
                            or not isinstance(session_id, str) or not LABEL.fullmatch(session_id)
                            or hook_id in hook_starts or hook_id in completed_hook_ids):
                        invalidate_active()
                        orphan_expected_hook = active_call_id is None
                    elif active_call_id is None:
                        orphan_expected_hook = True
                    else:
                        call = workflow_calls[active_call_id]
                        required_phase = "tool-use" if hook_event == "PreToolUse" else "tool-result"
                        if (call["phase"] != required_phase
                                or hook_event == "PostToolUseFailure"
                                or session_id != call.get("toolSessionId")
                                or (hook_event == "PostToolUse"
                                    and call.get("sessionId") != session_id)):
                            call["invalid"] = True
                        else:
                            call["phase"] = (
                                "pre-started" if hook_event == "PreToolUse" else "post-started"
                            )
                            hook_starts[hook_id] = {
                                "callId": active_call_id, "event": hook_event,
                                "name": value["hook_name"], "sessionId": session_id,
                            }

                if (event_type == "system" and value.get("subtype") == "hook_response"
                        and hook_name_matches(value.get("hook_name"), value.get("hook_event"))
                        and value.get("hook_event") in {
                            "PreToolUse", "PostToolUse", "PostToolUseFailure",
                        }):
                    hook_events += 1
                    hook_id = value.get("hook_id")
                    started = hook_starts.pop(hook_id, None) if isinstance(hook_id, str) else None
                    if started is None:
                        invalidate_active()
                        orphan_expected_hook = active_call_id is None
                        continue
                    completed_hook_ids.add(hook_id)
                    call = workflow_calls[started["callId"]]
                    response_matches = (
                        value.get("hook_name") == started["name"]
                        and value.get("hook_event") == started["event"]
                        and value.get("session_id") == started["sessionId"]
                        and value.get("outcome") == "success"
                        and value.get("exit_code") in {None, 0}
                    )
                    if not response_matches:
                        call["invalid"] = True
                        continue
                    if started["event"] == "PreToolUse":
                        if call["phase"] != "pre-started" or pre_decision(value) != "ask":
                            call["invalid"] = True
                        else:
                            call["phase"] = "pre-approved"
                            call["sessionId"] = started["sessionId"]
                    elif started["event"] == "PostToolUse":
                        if (call["phase"] != "post-started"
                                or any(value.get(field) != "" for field in (
                                    "stdout", "stderr", "output",
                                ))):
                            call["invalid"] = True
                        else:
                            call["phase"] = "post-success"
                    else:
                        call["invalid"] = True
    workflow_observation = {
        "routeClass": "legacy-read-only-multi-command",
        "guardProof": "exact-deny",
        "workflowExecutionSteps": 0,
        "workflowValidationSteps": 0,
        "workflowAuthentication": "not-observed",
        "workflowMutation": "not-observed",
        "workflowValidation": "not-observed",
        "workflowOutcome": "NOT_OBSERVED",
        "operationId": None,
        "invocationFingerprint": None,
    }
    if workflow_calls:
        observed = next(iter(workflow_calls.values()))
        outcome = observed["outcome"]
        complete = (
            len(workflow_calls) == 1
            and bash_tool_uses == 1
            and not hook_starts
            and not observed["invalid"]
            and observed["phase"] == "post-success"
            and outcome == "WORKFLOW_VALIDATED"
            and observed["authenticationRequested"]
            and observed["mutationRequested"]
            and observed["validationRequested"]
        )
        workflow_observation = {
            "routeClass": "persistent-one-shot" if complete else "workflow-incomplete",
            "guardProof": "exact-native-approval" if complete else "exact-deny",
            "workflowExecutionSteps": observed["executionSteps"],
            "workflowValidationSteps": observed["validationSteps"],
            "workflowAuthentication": "completed" if complete else "not-observed",
            "workflowMutation": "completed" if complete else "not-observed",
            "workflowValidation": "completed" if complete else "not-observed",
            "workflowOutcome": outcome,
            "operationId": observed["operationId"],
            "invocationFingerprint": observed["invocationFingerprint"],
        }
    workflow_session_ids = []
    if workflow_observation["routeClass"] == "persistent-one-shot":
        session_id = next(iter(workflow_calls.values())).get("sessionId")
        if isinstance(session_id, str) and LABEL.fullmatch(session_id):
            workflow_session_ids = [session_id]
    if canary_seen:
        return {"status": "fail", "reasonCode": "CANARY_EXPOSED", "toolCalls": tool_calls, "hookEvents": hook_events, "roleLabels": [], "contextPercentages": [], "workflowSessionIds": [], **workflow_observation}
    if malformed or not result_seen:
        if workflow_observation["routeClass"] == "persistent-one-shot":
            workflow_observation.update({
                "routeClass": "workflow-incomplete", "guardProof": "exact-deny",
                "workflowAuthentication": "not-observed",
                "workflowMutation": "not-observed",
                "workflowValidation": "not-observed",
            })
        return {"status": "inconclusive", "reasonCode": "STREAM_INCONCLUSIVE", "toolCalls": tool_calls, "hookEvents": hook_events, "roleLabels": [], "contextPercentages": [], "workflowSessionIds": [], **workflow_observation}
    return {"status": "pass", "reasonCode": "STRUCTURAL_RESULT", "toolCalls": tool_calls, "hookEvents": hook_events, "roleLabels": [], "contextPercentages": [], "workflowSessionIds": workflow_session_ids, **workflow_observation}


def load_permission_signal(
    path: Path, expected_phase: str, expected_nonce: str,
    expected_fingerprint: str,
) -> dict[str, Any] | None:
    value = _load_private_json(path, 4096)
    if value is None:
        return None
    try:
        signal = _exact(value, PERMISSION_SIGNAL_FIELDS, "permission signal")
        if (signal["schemaVersion"] != 1 or isinstance(signal["schemaVersion"], bool)
                or signal["runNonce"] != _label(expected_nonce)
                or signal["phase"] != expected_phase
                or signal["decision"] != expected_phase
                or signal["callCount"] != 1 or isinstance(signal["callCount"], bool)
                or signal["invocationFingerprint"] != expected_fingerprint
                or not re.fullmatch(r"[0-9a-f]{64}", expected_fingerprint)
                or signal["verified"] is not True
                or signal["inputUnchanged"] is not True):
            return None
        return signal
    except ValueError:
        return None


def _invalid_permission_sample(sample: dict[str, Any]) -> dict[str, Any]:
    return {
        **sample,
        "status": "inconclusive",
        "reasonCode": "PERMISSION_INCONCLUSIVE",
        "routeClass": "workflow-incomplete",
        "guardProof": "exact-deny",
        "workflowAuthentication": "not-observed",
        "workflowMutation": "not-observed",
        "workflowValidation": "not-observed",
        "workflowSessionIds": [],
        "permissionPhase": None,
        "permissionDecision": None,
        "permissionCallCount": 0,
    }


def evaluate_allowed_stream(
    path: Path, canary: str, signal_path: Path,
    expected_nonce: str, expected_session: str,
) -> dict[str, Any]:
    sample = evaluate_stream(path, canary)
    fingerprint = sample.get("invocationFingerprint")
    if (sample.get("status") != "pass"
            or sample.get("routeClass") != "persistent-one-shot"
            or sample.get("workflowSessionIds") != [_label(expected_session)]
            or not isinstance(fingerprint, str)
            or load_permission_signal(
                signal_path, "allow", expected_nonce, fingerprint,
            ) is None):
        return _invalid_permission_sample(sample)
    return {
        **sample,
        "permissionPhase": "allow",
        "permissionDecision": "allow",
        "permissionCallCount": 1,
    }


def _permission_pre_decision(value: dict[str, Any]) -> str | None:
    stdout = value.get("stdout")
    if (not isinstance(stdout, str) or len(stdout) > 4096
            or value.get("output") != stdout or value.get("stderr") != ""):
        return None
    try:
        parsed = _exact(json.loads(stdout), {"hookSpecificOutput"}, "hook response")
        hook = _exact(parsed["hookSpecificOutput"], {
            "hookEventName", "permissionDecision", "permissionDecisionReason",
        }, "hook decision")
    except (ValueError, json.JSONDecodeError):
        return None
    if (hook.get("hookEventName") != "PreToolUse"
            or hook.get("permissionDecisionReason") != EXPECTED_ASK_REASON):
        return None
    decision = hook.get("permissionDecision")
    return decision if decision in {"allow", "ask", "deny"} else None


def evaluate_denied_stream(
    path: Path, canary: str, signal_path: Path,
    expected_nonce: str, expected_session: str,
) -> dict[str, Any]:
    empty = {
        "status": "inconclusive", "reasonCode": "DENY_STREAM_INCONCLUSIVE",
        "toolCalls": 0, "hookEvents": 0, "roleLabels": [],
        "contextPercentages": [], "workflowSessionIds": [],
        "routeClass": "workflow-incomplete", "guardProof": "exact-deny",
        "workflowExecutionSteps": 0, "workflowValidationSteps": 0,
        "workflowAuthentication": "not-observed", "workflowMutation": "not-observed",
        "workflowValidation": "not-observed", "workflowOutcome": "NOT_OBSERVED",
        "operationId": None, "invocationFingerprint": None,
        "permissionPhase": None, "permissionDecision": None, "permissionCallCount": 0,
    }
    try:
        _label(expected_session)
        _label(expected_nonce)
        if not path.is_file() or not 1 <= path.stat().st_size <= 5_000_000:
            return empty
        state = "before"
        call_id = None
        hook_id = None
        observation = None
        tool_calls = 0
        hook_events = 0
        malformed = False
        with path.open("r", encoding="utf-8") as stream:
            for line in stream:
                if canary and canary in line:
                    return {**empty, "status": "fail", "reasonCode": "CANARY_EXPOSED"}
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    malformed = True
                    continue
                if not isinstance(event, dict):
                    malformed = True
                    continue
                for value, provenance in _stream_records(event):
                    event_type = value.get("type")
                    if event_type == "system" and value.get("subtype") == "init" and state == "before":
                        continue
                    if event_type == "tool_use":
                        tool_calls += 1
                        identity = (provenance.get("sessionId"), provenance.get("parentToolUseId"))
                        tool_input = value.get("input")
                        parsed = _workflow_command(
                            tool_input.get("command") if isinstance(tool_input, dict) else None
                        )
                        if (state != "before" or value.get("name") != "Bash"
                                or not isinstance(value.get("id"), str)
                                or not LABEL.fullmatch(value["id"])
                                or identity != (expected_session, None)
                                or parsed is None or parsed["sessionId"] != expected_session):
                            malformed = True
                        else:
                            call_id = value["id"]
                            observation = parsed
                            state = "tool-use"
                    elif event_type == "system" and value.get("subtype") == "hook_started":
                        if (state != "tool-use" or value.get("hook_event") != "PreToolUse"
                                or value.get("hook_name") != "PreToolUse:Bash"
                                or value.get("session_id") != expected_session
                                or not isinstance(value.get("hook_id"), str)
                                or not LABEL.fullmatch(value["hook_id"])):
                            malformed = True
                        else:
                            hook_id = value["hook_id"]
                            state = "pre-started"
                    elif event_type == "system" and value.get("subtype") == "hook_response":
                        hook_events += 1
                        if (state != "pre-started" or value.get("hook_id") != hook_id
                                or value.get("hook_event") != "PreToolUse"
                                or value.get("hook_name") != "PreToolUse:Bash"
                                or value.get("session_id") != expected_session
                                or value.get("outcome") != "success"
                                or value.get("exit_code") not in {None, 0}
                                or _permission_pre_decision(value) != "ask"):
                            malformed = True
                        else:
                            state = "asked"
                    elif event_type == "tool_result":
                        tool_calls += 1
                        content = value.get("content")
                        identity = (provenance.get("sessionId"), provenance.get("parentToolUseId"))
                        structured = None
                        if isinstance(content, str) and len(content) <= 4096:
                            try:
                                structured = json.loads(content)
                            except json.JSONDecodeError:
                                pass
                        if (state != "asked" or value.get("tool_use_id") != call_id
                                or value.get("is_error") is not True
                                or identity != (expected_session, None)
                                or not isinstance(content, str) or not 1 <= len(content) <= 4096
                                or isinstance(structured, (dict, list))):
                            malformed = True
                        else:
                            state = "denied"
                    elif event_type == "result":
                        if (state != "denied" or value.get("subtype") != "success"
                                or value.get("is_error") is not False
                                or value.get("session_id") != expected_session):
                            malformed = True
                        else:
                            state = "terminal"
                    elif state == "terminal" or event_type in {"tool_use", "tool_result"}:
                        malformed = True
        if (malformed or state != "terminal" or observation is None
                or tool_calls != 2 or hook_events != 1):
            return {**empty, "toolCalls": tool_calls, "hookEvents": hook_events}
        fingerprint = observation["invocationFingerprint"]
        if load_permission_signal(signal_path, "deny", expected_nonce, fingerprint) is None:
            return {**empty, "toolCalls": tool_calls, "hookEvents": hook_events}
        return {
            **empty,
            "status": "pass", "reasonCode": "STRUCTURAL_DENIAL",
            "toolCalls": tool_calls, "hookEvents": hook_events,
            "workflowSessionIds": [expected_session],
            "routeClass": "workflow-denied", "guardProof": "exact-native-denial",
            "workflowExecutionSteps": observation["executionSteps"],
            "workflowValidationSteps": observation["validationSteps"],
            "operationId": observation["operationId"],
            "invocationFingerprint": fingerprint,
            "permissionPhase": "deny", "permissionDecision": "deny",
            "permissionCallCount": 1,
        }
    except (OSError, UnicodeError, ValueError):
        return empty


def _exact_workflow_sessions(samples: list[dict[str, Any]]) -> set[str] | None:
    observed: list[str] = []
    for sample in samples:
        sessions = sample.get("workflowSessionIds")
        if (not isinstance(sessions, list) or len(sessions) != 1
                or not isinstance(sessions[0], str)
                or not LABEL.fullmatch(sessions[0])):
            return None
        observed.append(sessions[0])
    return set(observed) if len(set(observed)) == len(observed) else None


def aggregate_results(
    runtime: dict[str, str], samples: list[dict[str, Any]], *,
    measurement: dict[str, Any] | None = None, expected_nonce: str | None = None,
    fixture_before: dict[str, Any] | None = None,
    fixture_after: dict[str, Any] | None = None,
) -> dict[str, Any]:
    for value in runtime.values():
        _label(value)
    if not 1 <= len(samples) <= 13:
        raise ValueError("invalid sample count")
    statuses = {sample.get("status") for sample in samples}
    tool_calls = sum(sample.get("toolCalls", 0) for sample in samples)
    hook_events = sum(sample.get("hookEvents", 0) for sample in samples)
    workflow_session_ids = _exact_workflow_sessions(samples)
    trusted_measurement = None
    if (measurement is not None and expected_nonce is not None
            and workflow_session_ids is not None):
        try:
            trusted_measurement = validate_trusted_measurement(
                measurement, expected_nonce, workflow_session_ids,
            )
        except ValueError:
            trusted_measurement = None
    percentages = (
        [stage["usedPercentage"] for stage in trusted_measurement["contextStages"]]
        if trusted_measurement is not None else []
    )
    role_count = len(trusted_measurement["roleProbes"]) if trusted_measurement is not None else 0
    tool_search_mode = (
        trusted_measurement["toolSearch"]["mode"]
        if trusted_measurement is not None else "unavailable"
    )
    workflow_samples = [sample for sample in samples if sample.get("routeClass") in {
        "persistent-one-shot", "workflow-incomplete", "workflow-denied",
    }]
    completed_workflows = [sample for sample in workflow_samples if (
        sample.get("routeClass") == "persistent-one-shot"
        and sample.get("guardProof") == "exact-native-approval"
        and sample.get("workflowOutcome") == "WORKFLOW_VALIDATED"
        and all(sample.get(field) == "completed" for field in (
            "workflowAuthentication", "workflowMutation", "workflowValidation",
        ))
    )]
    permission = {
        "mode": "synthetic-deterministic",
        "allow": "completed" if sum(
            sample.get("permissionPhase") == "allow"
            and sample.get("permissionDecision") == "allow"
            and sample.get("permissionCallCount") == 1 for sample in samples
        ) == 1 else "not-observed",
        "deny": "completed" if sum(
            sample.get("permissionPhase") == "deny"
            and sample.get("permissionDecision") == "deny"
            and sample.get("permissionCallCount") == 1 for sample in samples
        ) == 1 else "not-observed",
        "callCount": 0,
    }
    permission["callCount"] = sum(
        permission[field] == "completed" for field in ("allow", "deny")
    )

    def fixture_observation(value: Any) -> dict[str, Any] | None:
        try:
            observed = _exact(value, FIXTURE_OBSERVATION_FIELDS, "fixture observation")
        except ValueError:
            return None
        if (type(observed["enabled"]) is not bool
                or not isinstance(observed["revision"], int)
                or isinstance(observed["revision"], bool)
                or not 0 <= observed["revision"] <= 1_000_000):
            return None
        return observed

    before = fixture_observation(fixture_before)
    after = fixture_observation(fixture_after)
    allow_sample = samples[0] if len(samples) == 2 else None
    deny_sample = samples[1] if len(samples) == 2 else None
    distinct_bindings = bool(
        allow_sample and deny_sample
        and allow_sample.get("workflowSessionIds") != deny_sample.get("workflowSessionIds")
        and allow_sample.get("operationId") != deny_sample.get("operationId")
        and allow_sample.get("invocationFingerprint") != deny_sample.get("invocationFingerprint")
        and all(isinstance(sample.get("operationId"), str) for sample in (allow_sample, deny_sample))
        and all(re.fullmatch(r"[0-9a-f]{64}", sample.get("invocationFingerprint", "")) for sample in (allow_sample, deny_sample))
    )
    permission_pair = bool(
        statuses == {"pass"}
        and allow_sample and deny_sample
        and allow_sample.get("permissionPhase") == "allow"
        and allow_sample.get("permissionDecision") == "allow"
        and allow_sample.get("permissionCallCount") == 1
        and allow_sample in completed_workflows
        and deny_sample.get("permissionPhase") == "deny"
        and deny_sample.get("permissionDecision") == "deny"
        and deny_sample.get("permissionCallCount") == 1
        and deny_sample.get("routeClass") == "workflow-denied"
        and deny_sample.get("guardProof") == "exact-native-denial"
        and deny_sample.get("workflowOutcome") == "NOT_OBSERVED"
        and all(deny_sample.get(field) == "not-observed" for field in (
            "workflowAuthentication", "workflowMutation", "workflowValidation",
        ))
        and distinct_bindings
        and before is not None and before == after
        and permission == {
            "mode": "synthetic-deterministic", "allow": "completed",
            "deny": "completed", "callCount": 2,
        }
    )
    persistent = permission_pair
    route_class = (
        "persistent-one-shot" if persistent or (
            len(samples) == 1 and len(completed_workflows) == 1
        ) else
        "workflow-incomplete" if workflow_samples else
        "legacy-read-only-multi-command"
    )
    guard_proof = (
        "exact-native-approval" if persistent or completed_workflows else
        "exact-bound-read" if any(sample.get("guardProof") == "exact-bound-read" for sample in samples)
        else "exact-deny"
    )
    workflow_outcome = "WORKFLOW_VALIDATED" if completed_workflows else (
        "OUTCOME_UNKNOWN" if workflow_samples and (
            statuses != {"pass"} or any(
                sample.get("workflowOutcome") == "OUTCOME_UNKNOWN"
                for sample in workflow_samples
            )
        ) else "NOT_OBSERVED"
    )
    completed = completed_workflows[0] if len(completed_workflows) == 1 else None
    workflow = {
        "executionSteps": completed.get("workflowExecutionSteps", 0) if completed else sum(
            sample.get("workflowExecutionSteps", 0) for sample in workflow_samples
        ),
        "validationSteps": completed.get("workflowValidationSteps", 0) if completed else sum(
            sample.get("workflowValidationSteps", 0) for sample in workflow_samples
        ),
        "authentication": "completed" if completed else "not-observed",
        "mutation": "completed" if completed else "not-observed",
        "validation": "completed" if completed else "not-observed",
        "outcome": workflow_outcome,
    }
    if "fail" in statuses:
        status, reason, capability = "fail", "BOUNDARY_FAILURE", "OUTCOME_UNKNOWN"
    elif (not persistent or "inconclusive" in statuses or len(percentages) < 5 or tool_calls < 4
          or hook_events < 3 or role_count != 12):
        reason = "LEGACY_READ_ONLY_ONLY" if not workflow_samples else "RUNTIME_INCONCLUSIVE"
        status, capability = "inconclusive", (
            "OUTCOME_UNKNOWN" if workflow_outcome == "OUTCOME_UNKNOWN" else
            "AVAILABLE_RECOGNIZED" if tool_calls > 0 else "UNAVAILABLE"
        )
    else:
        status, reason, capability = "pass", "COMPATIBLE", "ACTIVE"
    return validate_aggregate({
        "status": status,
        "reasonCode": reason,
        "observedRuntime": runtime,
        "capabilityState": capability,
        "guardProof": guard_proof,
        "routeClass": route_class,
        "workflow": workflow,
        "roleCount": role_count,
        "toolCalls": tool_calls,
        "hookEvents": hook_events,
        "context": {
            "before": percentages[0] if len(percentages) >= 5 else 0,
            "afterSkill": percentages[1] if len(percentages) >= 5 else 0,
            "afterSubagent": percentages[2] if len(percentages) >= 5 else 0,
            "afterDiscovery": percentages[3] if len(percentages) >= 5 else 0,
            "afterUse": percentages[4] if len(percentages) >= 5 else 0,
            "toolSearchMode": tool_search_mode,
        },
        "cleanup": "pending",
        "permission": permission,
    }, allow_pending_cleanup=True)


def finalize_cleanup(value: Any, work_path: Path) -> dict[str, Any]:
    pending = validate_aggregate(value, allow_pending_cleanup=True)
    if pending["cleanup"] != "pending" or work_path.exists():
        raise ValueError("cleanup is not complete")
    if not work_path.is_absolute() or not work_path.name.startswith("p0-04b-browser."):
        raise ValueError("invalid cleanup path")
    return validate_aggregate({**pending, "cleanup": "verified"})


def self_test() -> None:
    sample = {
        "status": "pass", "reasonCode": "STRUCTURAL_RESULT", "toolCalls": 0,
        "hookEvents": 0, "roleLabels": [], "contextPercentages": [1, 2, 3, 4, 5],
    }
    result = aggregate_results({
        "claude": "observed", "provider": "observed", "model": "observed",
        "adapter": "unavailable",
    }, [sample])
    assert result["status"] == "inconclusive"
    assert result["routeClass"] == "legacy-read-only-multi-command"
    assert set(result) == AGGREGATE_FIELDS


def main(argv: list[str]) -> int:
    if argv == ["--self-test"]:
        self_test()
        return 0
    if len(argv) == 4 and argv[0] == "--evaluate-stream":
        result = evaluate_stream(Path(argv[1]), argv[2])
        Path(argv[3]).write_text(json.dumps(result, separators=(",", ":")) + "\n", encoding="utf-8")
        return 0
    if len(argv) == 7 and argv[0] in {"--evaluate-allow-stream", "--evaluate-deny-stream"}:
        evaluator = (
            evaluate_allowed_stream if argv[0] == "--evaluate-allow-stream"
            else evaluate_denied_stream
        )
        result = evaluator(
            Path(argv[1]), argv[2], Path(argv[3]), argv[4], argv[5],
        )
        Path(argv[6]).write_text(json.dumps(result, separators=(",", ":")) + "\n", encoding="utf-8")
        return 0
    if len(argv) == 6 and argv[0] == "--evaluate-measurement-stream":
        result = evaluate_measurement_stream(
            Path(argv[1]), argv[2], argv[3], argv[4],
        )
        Path(argv[5]).write_text(json.dumps(result, separators=(",", ":")) + "\n", encoding="utf-8")
        return 0
    if len(argv) == 5 and argv[0] == "--status-context":
        print(json.dumps(status_context_observation(
            Path(argv[1]), argv[2], argv[3], argv[4],
        ), separators=(",", ":")))
        return 0
    if len(argv) == 5 and argv[0] == "--status-context-failure-reason":
        print(status_context_failure_reason(
            Path(argv[1]), argv[2], argv[3], argv[4],
        ))
        return 0
    if len(argv) == 2 and argv[0] == "--pty-failure-reason":
        print(pty_failure_reason(Path(argv[1])))
        return 0
    if len(argv) == 4 and argv[0] == "--pty-context":
        print(json.dumps(pty_context_observation(
            Path(argv[1]), argv[2], argv[3],
        ), separators=(",", ":")))
        return 0
    if len(argv) == 3 and argv[0] == "--build-measurement":
        source = _load_private_json(Path(argv[1]), MAX_TRUSTED_MEASUREMENT_BYTES)
        if source is None:
            raise ValueError("trusted measurement source rejected")
        value = build_trusted_measurement_from_source(source)
        write_private_measurement(Path(argv[2]), value)
        return 0
    if len(argv) >= 8 and argv[0] == "--aggregate":
        runtime = {
            "claude": argv[3], "provider": argv[4], "model": argv[5], "adapter": argv[6],
        }
        samples = [json.loads(Path(name).read_text(encoding="utf-8")) for name in argv[7:]]
        workflow_sessions = _exact_workflow_sessions(samples)
        measurement = load_trusted_measurement(
            Path(argv[1]), argv[2], workflow_sessions,
        ) if workflow_sessions is not None else None
        print(json.dumps(aggregate_results(
            runtime, samples, measurement=measurement, expected_nonce=argv[2],
        ), separators=(",", ":")))
        return 0
    if len(argv) == 11 and argv[0] == "--aggregate-pair":
        runtime = {
            "claude": argv[5], "provider": argv[6], "model": argv[7], "adapter": argv[8],
        }
        samples = [json.loads(Path(name).read_text(encoding="utf-8")) for name in argv[9:11]]
        workflow_sessions = _exact_workflow_sessions(samples)
        measurement = load_trusted_measurement(
            Path(argv[1]), argv[2], workflow_sessions,
        ) if workflow_sessions is not None else None
        before = _load_private_json(Path(argv[3]), 4096)
        after = _load_private_json(Path(argv[4]), 4096)
        print(json.dumps(aggregate_results(
            runtime, samples, measurement=measurement, expected_nonce=argv[2],
            fixture_before=before, fixture_after=after,
        ), separators=(",", ":")))
        return 0
    if len(argv) == 3 and argv[0] == "--finalize-cleanup":
        value = json.loads(argv[1])
        print(json.dumps(finalize_cleanup(value, Path(argv[2])), separators=(",", ":")))
        return 0
    raise ValueError("unsupported parser invocation")


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (OSError, ValueError, json.JSONDecodeError):
        print("browser runtime evidence rejected", file=sys.stderr)
        raise SystemExit(2)
