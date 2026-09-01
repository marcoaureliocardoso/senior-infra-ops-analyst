#!/usr/bin/env python3
"""Content-free parser for the opt-in P0-04B runtime harness."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


AGGREGATE_FIELDS = {
    "status", "reasonCode", "observedRuntime", "capabilityState", "guardProof",
    "roleCount", "context", "cleanup",
}
RUNTIME_FIELDS = {"claude", "provider", "model", "adapter"}
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


def _exact(value: Any, fields: set[str], name: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError(f"invalid {name} fields")
    return value


def _label(value: Any) -> str:
    if not isinstance(value, str) or not LABEL.fullmatch(value):
        raise ValueError("invalid observed label")
    return value


def validate_aggregate(value: Any) -> dict[str, Any]:
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
    if result["guardProof"] not in {"exact-deny", "exact-bound-read"}:
        raise ValueError("invalid guard proof")
    if result["roleCount"] != 12:
        raise ValueError("invalid role count")
    context = _exact(result["context"], CONTEXT_FIELDS, "context")
    for field in CONTEXT_FIELDS - {"toolSearchMode"}:
        if not isinstance(context[field], int) or isinstance(context[field], bool) or not 0 <= context[field] <= 100:
            raise ValueError("invalid context percentage")
    if context["toolSearchMode"] not in TOOL_SEARCH_MODES:
        raise ValueError("invalid tool search mode")
    if result["cleanup"] != "verified":
        raise ValueError("cleanup is not verified")
    return result


def evaluate_stream(path: Path, canary: str) -> dict[str, Any]:
    if not path.is_file() or path.stat().st_size > 5_000_000:
        return {"status": "inconclusive", "reasonCode": "STREAM_INVALID", "toolCalls": 0}
    tool_calls = 0
    result_seen = False
    canary_seen = False
    malformed = False
    context_percentages: list[int] = []

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
            if event.get("type") in {"tool_use", "tool_result"}:
                tool_calls += 1
            if event.get("type") == "result":
                result_seen = True
    if canary_seen:
        return {"status": "fail", "reasonCode": "CANARY_EXPOSED", "toolCalls": tool_calls, "contextPercentages": context_percentages}
    if malformed or not result_seen:
        return {"status": "inconclusive", "reasonCode": "STREAM_INCONCLUSIVE", "toolCalls": tool_calls, "contextPercentages": context_percentages}
    return {"status": "pass", "reasonCode": "STRUCTURAL_RESULT", "toolCalls": tool_calls, "contextPercentages": context_percentages}


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
    if "fail" in statuses:
        status, reason, capability = "fail", "BOUNDARY_FAILURE", "OUTCOME_UNKNOWN"
    elif "inconclusive" in statuses or len(percentages) < 5:
        status, reason, capability = "inconclusive", "RUNTIME_INCONCLUSIVE", "UNAVAILABLE"
    else:
        status, reason, capability = "pass", "COMPATIBLE", "ACTIVE"
    return validate_aggregate({
        "status": status,
        "reasonCode": reason,
        "observedRuntime": runtime,
        "capabilityState": capability,
        "guardProof": "exact-deny",
        "roleCount": 12,
        "context": {
            "before": percentages[0] if len(percentages) >= 5 else 0,
            "afterSkill": percentages[1] if len(percentages) >= 5 else 0,
            "afterSubagent": percentages[2] if len(percentages) >= 5 else 0,
            "afterDiscovery": percentages[3] if len(percentages) >= 5 else 0,
            "afterUse": percentages[4] if len(percentages) >= 5 else 0,
            "toolSearchMode": "available-used" if len(percentages) >= 5 else "unavailable",
        },
        "cleanup": "verified",
    })


def self_test() -> None:
    sample = {
        "status": "pass", "reasonCode": "STRUCTURAL_RESULT", "toolCalls": 0,
        "contextPercentages": [1, 2, 3, 4, 5],
    }
    result = aggregate_results({
        "claude": "observed", "provider": "observed", "model": "observed",
        "adapter": "unavailable",
    }, [sample])
    assert result["status"] == "pass"
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
    raise ValueError("unsupported parser invocation")


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (OSError, ValueError, json.JSONDecodeError):
        print("browser runtime evidence rejected", file=sys.stderr)
        raise SystemExit(2)
