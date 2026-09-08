#!/usr/bin/env python3
"""Content-free parser for the opt-in P0-04B runtime harness."""
from __future__ import annotations

import base64
import json
import re
import shlex
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
MUTABLE_EFFECTS = {"LOW_RISK_CHANGE", "DISRUPTIVE_CHANGE", "DESTRUCTIVE_CHANGE"}
WORKFLOW_REASON_CODES = {
    "WORKFLOW_VALIDATED", "WORKFLOW_NOT_APPLIED", "OUTCOME_UNKNOWN",
}


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
        result["status"] != "pass"
        or result["capabilityState"] != "ACTIVE"
        or result["guardProof"] != "exact-native-approval"
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


def _decode_step(token: str) -> dict[str, Any] | None:
    if not isinstance(token, str) or not 1 <= len(token) <= 2048:
        return None
    if "=" in token or not re.fullmatch(r"[A-Za-z0-9_-]+", token):
        return None
    try:
        raw = base64.b64decode(
            token + "=" * (-len(token) % 4), altchars=b"-_", validate=True,
        )
        if not 1 <= len(raw) <= 1536:
            return None
        if base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii") != token:
            return None
        value = json.loads(raw.decode("utf-8", errors="strict"))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _workflow_command(command: Any) -> dict[str, Any] | None:
    if not isinstance(command, str) or not 1 <= len(command) <= 65536:
        return None
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        return None
    runner_indexes = [
        index for index, token in enumerate(tokens)
        if token.replace("\\", "/").endswith(
            "skills/browser-operations/scripts/browser-runner.mjs"
        )
    ]
    if len(runner_indexes) != 1:
        return None
    args = tokens[runner_indexes[0] + 1:]
    if args.count("--step") != 1:
        return None
    step_index = args.index("--step")
    if step_index + 1 >= len(args) or args[step_index + 1] != "workflow":
        return None
    execution_tokens = [
        args[index + 1] for index, token in enumerate(args[:-1])
        if token == "--workflow-step"
    ]
    validation_tokens = [
        args[index + 1] for index, token in enumerate(args[:-1])
        if token == "--validation-step"
    ]
    execution = [_decode_step(token) for token in execution_tokens]
    validation = [_decode_step(token) for token in validation_tokens]
    if (not 1 <= len(execution) <= 16 or not 1 <= len(validation) <= 12
            or any(step is None for step in execution + validation)):
        return None
    authenticated = any(step.get("step") == "fill" for step in execution)
    mutable = any(step.get("effect") in MUTABLE_EFFECTS for step in execution)
    independently_validated = validation[-1].get("step") == "inspect"
    return {
        "executionSteps": len(execution),
        "validationSteps": len(validation),
        "authenticationRequested": authenticated,
        "mutationRequested": mutable,
        "validationRequested": independently_validated,
    }


def _workflow_result(content: Any) -> str | None:
    candidates: list[str] = []
    if isinstance(content, str) and len(content) <= 4096:
        candidates.append(content)
    elif isinstance(content, list) and len(content) <= 8:
        candidates.extend(
            block["text"] for block in content
            if isinstance(block, dict) and block.get("type") == "text"
            and isinstance(block.get("text"), str) and len(block["text"]) <= 4096
        )
    for candidate in candidates:
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if (isinstance(value, dict)
                and set(value) == {
                    "status", "reasonCode", "operationId", "step", "effect",
                    "validationRequired", "observation",
                }
                and value.get("step") == "workflow"
                and value.get("reasonCode") in WORKFLOW_REASON_CODES):
            return value["reasonCode"]
    return None


def evaluate_stream(path: Path, canary: str) -> dict[str, Any]:
    if not path.is_file() or path.stat().st_size > 5_000_000:
        return {"status": "inconclusive", "reasonCode": "STREAM_INVALID", "toolCalls": 0}
    tool_calls = 0
    result_seen = False
    canary_seen = False
    malformed = False
    context_percentages: list[int] = []
    hook_events = 0
    role_labels: set[str] = set()
    workflow_calls: dict[str, dict[str, Any]] = {}
    workflow_results: dict[str, str] = {}
    pre_hooks: set[str] = set()
    post_hooks: set[str] = set()

    def inspect_structural(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key == "used_percentage" and isinstance(child, int) and not isinstance(child, bool) and 0 <= child <= 100:
                    if len(context_percentages) < 32:
                        context_percentages.append(child)
                inspect_structural(child)
        elif isinstance(value, list):
            for child in value:
                inspect_structural(child)
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
            inspect_structural(event)
            for value in _stream_records(event):
                event_type = value.get("type")
                if event_type in {"tool_use", "tool_result"}:
                    tool_calls += 1
                if value.get("hook_event_name") in {
                    "PreToolUse", "PostToolUse", "PostToolUseFailure",
                }:
                    hook_events += 1
                if (isinstance(value.get("agent_type"), str)
                        and LABEL.fullmatch(value["agent_type"])):
                    role_labels.add(value["agent_type"])
                if event_type == "result":
                    result_seen = True
                tool_use_id = value.get("id") if event_type == "tool_use" else value.get("tool_use_id")
                if (event_type == "tool_use" and value.get("name") == "Bash"
                        and isinstance(tool_use_id, str) and LABEL.fullmatch(tool_use_id)):
                    tool_input = value.get("input")
                    observation = _workflow_command(
                        tool_input.get("command") if isinstance(tool_input, dict) else None
                    )
                    if observation is not None:
                        workflow_calls[tool_use_id] = observation
                if (event_type == "tool_result" and isinstance(tool_use_id, str)
                        and tool_use_id in workflow_calls):
                    outcome = _workflow_result(value.get("content"))
                    if outcome is not None:
                        workflow_results[tool_use_id] = outcome
                if (value.get("hook_event_name") == "PreToolUse"
                        and value.get("tool_name") == "Bash"
                        and isinstance(value.get("tool_use_id"), str)):
                    pre_hooks.add(value["tool_use_id"])
                if (value.get("hook_event_name") == "PostToolUse"
                        and value.get("tool_name") == "Bash"
                        and isinstance(value.get("tool_use_id"), str)):
                    post_hooks.add(value["tool_use_id"])
    workflow_observation = {
        "routeClass": "legacy-read-only-multi-command",
        "guardProof": "exact-bound-read" if pre_hooks & post_hooks else "exact-deny",
        "workflowExecutionSteps": 0,
        "workflowValidationSteps": 0,
        "workflowAuthentication": "not-observed",
        "workflowMutation": "not-observed",
        "workflowValidation": "not-observed",
        "workflowOutcome": "NOT_OBSERVED",
    }
    if workflow_calls:
        call_id, observed = next(iter(workflow_calls.items()))
        outcome = workflow_results.get(call_id, "NOT_OBSERVED")
        complete = (
            len(workflow_calls) == 1
            and call_id in pre_hooks
            and call_id in post_hooks
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
        return {"status": "fail", "reasonCode": "CANARY_EXPOSED", "toolCalls": tool_calls, "hookEvents": hook_events, "roleLabels": sorted(role_labels), "contextPercentages": context_percentages, **workflow_observation}
    if malformed or not result_seen:
        return {"status": "inconclusive", "reasonCode": "STREAM_INCONCLUSIVE", "toolCalls": tool_calls, "hookEvents": hook_events, "roleLabels": sorted(role_labels), "contextPercentages": context_percentages, **workflow_observation}
    return {"status": "pass", "reasonCode": "STRUCTURAL_RESULT", "toolCalls": tool_calls, "hookEvents": hook_events, "roleLabels": sorted(role_labels), "contextPercentages": context_percentages, **workflow_observation}


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
        and bool(workflow_samples)
        and len(completed_workflows) == len(workflow_samples)
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
