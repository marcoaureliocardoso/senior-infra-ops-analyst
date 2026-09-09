#!/usr/bin/env python3
"""Content-free parser for the opt-in P0-04B runtime harness."""
from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


AGGREGATE_FIELDS = {
    "status", "reasonCode", "observedRuntime", "capabilityState", "guardProof",
    "routeClass", "workflow", "roleCount", "toolCalls", "hookEvents", "context",
    "cleanup",
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
}
OBSERVATION_STATES = {"completed", "not-observed"}
WORKFLOW_OUTCOMES = {
    "WORKFLOW_VALIDATED", "WORKFLOW_NOT_APPLIED", "OUTCOME_UNKNOWN", "NOT_OBSERVED",
}
WORKFLOW_EVIDENCE_FIELDS = {
    "operationId", "executionSteps", "validationSteps", "authenticationRequested",
    "mutationRequested", "validationRequested",
}
SHELL_CONTROL = re.compile(r"[\r\n\0;&|<>`]|\$\(")
EXPECTED_ASK_REASON = (
    "ASK_SENSITIVE_OPERATION: stage 1 "
    "BROWSER_PROTECTED_RUNNER/LOW_RISK_CHANGE. Operator confirmation is required "
    "before execution. Sensitive values are redacted."
)


def _exact(value: Any, fields: set[str], name: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError(f"invalid {name} fields")
    return value


def _label(value: Any) -> str:
    if not isinstance(value, str) or not LABEL.fullmatch(value):
        raise ValueError("invalid observed label")
    return value


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
        or result["toolCalls"] < 2
        or result["hookEvents"] < 2
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
    yield from records
    for record in records:
        message = record.get("message")
        if record.get("type") in {"assistant", "user"} and isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, list) and len(content) <= 64:
                for block in content:
                    if (isinstance(block, dict)
                            and block.get("type") in {"tool_use", "tool_result"}):
                        yield block


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
    for field, maximum in (("executionSteps", 16), ("validationSteps", 12)):
        if (not isinstance(observed[field], int) or isinstance(observed[field], bool)
                or not 1 <= observed[field] <= maximum):
            return None
    if any(not isinstance(observed[field], bool) for field in (
        "authenticationRequested", "mutationRequested", "validationRequested",
    )):
        return None
    return observed


def _workflow_result(content: Any, operation_id: str) -> str | None:
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
            or value.get("effect") != "SENSITIVE_READ"
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
            for value in _stream_records(event):
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
                    if (observation is not None and isinstance(tool_use_id, str)
                            and LABEL.fullmatch(tool_use_id)):
                        if tool_use_id in workflow_calls:
                            workflow_calls[tool_use_id]["invalid"] = True
                        else:
                            workflow_calls[tool_use_id] = {
                                **observation, "phase": "tool-use",
                                "invalid": orphan_expected_hook or bash_tool_uses != 1,
                                "outcome": "NOT_OBSERVED",
                            }
                            active_call_id = tool_use_id
                elif event_type == "tool_use" and active_call_id is not None:
                    invalidate_active()

                if (event_type == "tool_result" and isinstance(tool_use_id, str)
                        and tool_use_id in workflow_calls):
                    call = workflow_calls[tool_use_id]
                    outcome = _workflow_result(value.get("content"), call["operationId"])
                    if call["phase"] != "pre-approved" or outcome is None:
                        call["invalid"] = True
                    else:
                        call["phase"] = "tool-result"
                        call["outcome"] = outcome
                elif event_type == "tool_result" and active_call_id is not None:
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
        }
    if canary_seen:
        return {"status": "fail", "reasonCode": "CANARY_EXPOSED", "toolCalls": tool_calls, "hookEvents": hook_events, "roleLabels": [], "contextPercentages": [], **workflow_observation}
    if malformed or not result_seen:
        return {"status": "inconclusive", "reasonCode": "STREAM_INCONCLUSIVE", "toolCalls": tool_calls, "hookEvents": hook_events, "roleLabels": [], "contextPercentages": [], **workflow_observation}
    return {"status": "pass", "reasonCode": "STRUCTURAL_RESULT", "toolCalls": tool_calls, "hookEvents": hook_events, "roleLabels": [], "contextPercentages": [], **workflow_observation}


def aggregate_results(runtime: dict[str, str], samples: list[dict[str, Any]]) -> dict[str, Any]:
    for value in runtime.values():
        _label(value)
    if not 1 <= len(samples) <= 13:
        raise ValueError("invalid sample count")
    statuses = {sample.get("status") for sample in samples}
    percentages = [
        value
        for sample in samples
        for value in sample.get("contextPercentages", [])
        if isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 100
    ]
    tool_calls = sum(sample.get("toolCalls", 0) for sample in samples)
    hook_events = sum(sample.get("hookEvents", 0) for sample in samples)
    role_labels = {
        role for sample in samples for role in sample.get("roleLabels", [])
        if isinstance(role, str) and LABEL.fullmatch(role)
    }
    workflow_samples = [
        sample for sample in samples
        if sample.get("routeClass") in {"persistent-one-shot", "workflow-incomplete"}
    ]
    completed_workflows = [
        sample for sample in workflow_samples
        if sample.get("routeClass") == "persistent-one-shot"
        and sample.get("guardProof") == "exact-native-approval"
        and sample.get("workflowOutcome") == "WORKFLOW_VALIDATED"
        and all(sample.get(field) == "completed" for field in (
            "workflowAuthentication", "workflowMutation", "workflowValidation",
        ))
    ]
    persistent = (
        statuses == {"pass"}
        and len(workflow_samples) == len(samples)
        and len(completed_workflows) == len(samples)
    )
    route_class = (
        "persistent-one-shot" if persistent else
        "workflow-incomplete" if workflow_samples else
        "legacy-read-only-multi-command"
    )
    guard_proof = (
        "exact-native-approval" if persistent else
        "exact-bound-read" if any(sample.get("guardProof") == "exact-bound-read" for sample in samples)
        else "exact-deny"
    )
    workflow_outcome = "WORKFLOW_VALIDATED" if persistent else (
        "OUTCOME_UNKNOWN" if workflow_samples and (
            statuses != {"pass"} or any(
                sample.get("workflowOutcome") == "OUTCOME_UNKNOWN"
                for sample in workflow_samples
            )
        ) else "NOT_OBSERVED"
    )
    workflow = {
        "executionSteps": sum(
            sample.get("workflowExecutionSteps", 0) for sample in workflow_samples
        ),
        "validationSteps": sum(
            sample.get("workflowValidationSteps", 0) for sample in workflow_samples
        ),
        "authentication": "completed" if persistent else "not-observed",
        "mutation": "completed" if persistent else "not-observed",
        "validation": "completed" if persistent else "not-observed",
        "outcome": workflow_outcome,
    }
    if "fail" in statuses:
        status, reason, capability = "fail", "BOUNDARY_FAILURE", "OUTCOME_UNKNOWN"
    elif (not persistent or "inconclusive" in statuses or len(percentages) < 5 or tool_calls < 2
          or hook_events < 2 or len(role_labels) != 12):
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
        "roleCount": len(role_labels),
        "toolCalls": tool_calls,
        "hookEvents": hook_events,
        "context": {
            "before": percentages[0] if len(percentages) >= 5 else 0,
            "afterSkill": percentages[1] if len(percentages) >= 5 else 0,
            "afterSubagent": percentages[2] if len(percentages) >= 5 else 0,
            "afterDiscovery": percentages[3] if len(percentages) >= 5 else 0,
            "afterUse": percentages[4] if len(percentages) >= 5 else 0,
            "toolSearchMode": "available-used" if len(percentages) >= 5 else "unavailable",
        },
        "cleanup": "pending",
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
    if len(argv) >= 6 and argv[0] == "--aggregate":
        runtime = {
            "claude": argv[1], "provider": argv[2], "model": argv[3], "adapter": argv[4],
        }
        samples = [json.loads(Path(name).read_text(encoding="utf-8")) for name in argv[5:]]
        print(json.dumps(aggregate_results(runtime, samples), separators=(",", ":")))
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
