"""Test-only, closed evidence contract. No native or provider operations."""
from __future__ import annotations

import copy
import json
import math
import os
import re
import stat
from pathlib import Path

STAGES = ("skill", "subagent", "discovery", "use")
USAGE_KEYS = {"input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"}
CONTEXT_KEYS = {"totalTokens", "maxTokens", "rawMaxTokens", "percentage", "autoCompactEnabled", "categoryCount"}
WITNESS_KEYS = {"latestResponseUsage", "sessionBound", "policyFixed", "historyLinked", "measurementHook",
                "claimVerified", "actionCalls", "toolResultsComplete", "toolSearchAvailable", "unexpectedCalls", "fault"}
REASONS = {"NONE", "USAGE_PROVENANCE_UNPROVEN", "NON_COMPARABLE", "SESSION_UNPROVEN", "HISTORY_UNPROVEN",
           "HOOK_UNPROVEN", "POLICY_UNPROVEN", "INVALID_OBSERVATION", "UNEXPECTED_TOOL", "STATE_UNPROVEN",
           "BUDGET_INCONCLUSIVE", "OPERATION_TIMEOUT", "CLEANUP_INCONCLUSIVE", "CAPABILITY_UNAVAILABLE",
           "CHALLENGE_UNAVAILABLE"}
SAFE_INT = 2**53-1


def exact(value, keys):
    if type(value) is not dict or set(value) != set(keys):
        raise ValueError("invalid closed schema")
    return value


def integer(value, maximum=SAFE_INT, minimum=0):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError("invalid bounded integer")
    return value


def label(value):
    if type(value) is not str or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value):
        raise ValueError("invalid private identity")
    return value


def usage_tuple(value):
    exact(value, USAGE_KEYS)
    for number in value.values(): integer(number)
    return copy.deepcopy(value)


def project_api_usage(raw: dict) -> dict:
    if type(raw) is not dict: return {"state": "INVALID", "values": None}
    if "apiUsage" not in raw: return {"state": "ABSENT", "values": None}
    if raw["apiUsage"] is None: return {"state": "NULL", "values": None}
    try:
        value = raw["apiUsage"]
        if type(value) is not dict: raise ValueError()
        return {"state": "VALID", "values": usage_tuple({k: value[k] for k in USAGE_KEYS})}
    except (ValueError, KeyError): return {"state": "INVALID", "values": None}


def context(value):
    exact(value, CONTEXT_KEYS)
    integer(value["totalTokens"])
    for k in ("maxTokens", "rawMaxTokens"): integer(value[k], minimum=1)
    integer(value["categoryCount"], 4096)
    p=value["percentage"]
    if type(p) not in (int, float) or not math.isfinite(p) or not 0 <= p <= 100:
        raise ValueError("invalid percentage")
    if type(value["autoCompactEnabled"]) is not bool: raise ValueError("invalid auto compact flag")
    return copy.deepcopy(value)


def project_context(raw: dict) -> dict:
    if type(raw) is not dict or type(raw.get("categories")) is not list:
        raise ValueError("invalid native context")
    try:
        return context({k: raw[k] for k in ("totalTokens", "maxTokens", "rawMaxTokens", "percentage")} |
                       {"autoCompactEnabled": raw["isAutoCompactEnabled"], "categoryCount": len(raw["categories"])})
    except KeyError: raise ValueError("missing native context scalar") from None


def observation(value):
    exact(value, {"context", "apiUsage"}); context(value["context"])
    u=exact(value["apiUsage"], {"state", "values"})
    if u["state"] not in ("ABSENT", "NULL", "VALID", "INVALID"): raise ValueError("invalid usage state")
    if u["state"] == "VALID": usage_tuple(u["values"])
    elif u["values"] is not None: raise ValueError("unexpected accounting")
    return copy.deepcopy(value)


def offline_usage(before: dict, ordinal: int) -> dict:
    try:
        observation(before); integer(ordinal, 40, 1)
        d=min(before["context"][k] for k in ("maxTokens", "rawMaxTokens"))
        result=dict(input_tokens=d//8+ordinal, output_tokens=10,
                    cache_creation_input_tokens=0, cache_read_input_tokens=0)
        if result["input_tokens"]+10 > d//4 or before["apiUsage"]["values"] == result: raise ValueError()
        return usage_tuple(result)
    except (ValueError, TypeError): raise ValueError("CHALLENGE_UNAVAILABLE") from None


def stage_policy(stage: str, nonce: str) -> dict:
    label(nonce)
    actions = {
        "skill": ("Skill", {"skill": "context-continuity"}, ["Skill"], ["Skill(context-continuity)"], "empty",
            "P0-04B synthetic context measurement. Invoke Skill exactly once with only skill=context-continuity, then reply P004B_SKILL_OK. Do not perform browser work."),
        "subagent": ("Agent", {"description":"P004B_SUBAGENT_ACK", "prompt":"P004B_SUBAGENT_ACK", "subagent_type":"diagnostic-operator"},
            ["Agent"], ["Agent(diagnostic-operator)"], "empty",
            "P0-04B synthetic context measurement. Invoke Agent exactly once with description=P004B_SUBAGENT_ACK, prompt=P004B_SUBAGENT_ACK, and subagent_type=diagnostic-operator; then reply P004B_SUBAGENT_OK. Do not perform browser work."),
        "discovery": ("ToolSearch", {"query":"select:mcp__p004b-context__context_fixture_ping"}, ["ToolSearch"], ["ToolSearch"], "fixture",
            "P0-04B synthetic context measurement. If ToolSearch is available, invoke it exactly once with query=select:mcp__p004b-context__context_fixture_ping. Then reply P004B_DISCOVERY_OK. Do not call the discovered MCP tool."),
        "use": ("mcp__p004b-context__context_fixture_ping", {"nonce":nonce}, [], ["mcp__p004b-context__context_fixture_ping"], "fixture",
            f"P0-04B synthetic context measurement. Invoke mcp__p004b-context__context_fixture_ping exactly once with only nonce={nonce}, then reply P004B_USE_OK. Do not perform browser work."),
    }
    if stage not in actions: raise ValueError("invalid stage")
    name, inputs, tools, allowed, mcp, prompt=actions[stage]
    return dict(stage=stage, name=name, input=inputs, tools=tools, allowed_tools=allowed, mcp=mcp, prompt=prompt)


def validate_witness(stage, value):
    exact(value, WITNESS_KEYS)
    for key in ("sessionBound", "policyFixed", "claimVerified", "toolResultsComplete", "toolSearchAvailable"):
        if type(value[key]) is not bool: raise ValueError("invalid witness flag")
    for key in ("actionCalls", "unexpectedCalls"): integer(value[key], 40)
    if value["fault"] not in REASONS: raise ValueError("invalid closed fault")
    if value["latestResponseUsage"] is not None: usage_tuple(value["latestResponseUsage"])
    if value["historyLinked"] not in (("NOT_REQUIRED",) if stage=="skill" else ("OBSERVED", "UNPROVEN")):
        raise ValueError("invalid history witness")
    if value["measurementHook"] not in (("OBSERVED", "UNPROVEN") if stage=="subagent" else ("NOT_REQUIRED",)):
        raise ValueError("invalid hook witness")


def finish_stage(stage, before, after, witness):
    if stage not in STAGES: raise ValueError("invalid stage")
    validate_witness(stage, witness)
    for sample in (before, after):
        if sample is not None: observation(sample)
    delta=None; reason=witness["fault"]
    if reason=="NONE":
        if before is None or after is None: reason="INVALID_OBSERVATION"
        elif before["apiUsage"]["state"]=="INVALID" or after["apiUsage"]["state"]=="INVALID": reason="INVALID_OBSERVATION"
        elif any(before["context"][k] != after["context"][k] for k in ("maxTokens", "rawMaxTokens")): reason="NON_COMPARABLE"
        elif not witness["sessionBound"]: reason="SESSION_UNPROVEN"
        elif not witness["policyFixed"] or not all(s["context"]["autoCompactEnabled"] for s in (before, after)): reason="POLICY_UNPROVEN"
        elif witness["historyLinked"]=="UNPROVEN": reason="HISTORY_UNPROVEN"
        elif witness["measurementHook"]=="UNPROVEN" or (stage=="subagent" and not witness["claimVerified"]): reason="HOOK_UNPROVEN"
        elif witness["unexpectedCalls"]: reason="UNEXPECTED_TOOL"
        elif witness["actionCalls"] != (0 if stage=="discovery" and not witness["toolSearchAvailable"] else 1) or not witness["toolResultsComplete"]: reason="STATE_UNPROVEN"
        elif (after["apiUsage"]["state"] != "VALID" or witness["latestResponseUsage"] is None or
              after["apiUsage"]["values"] != witness["latestResponseUsage"] or
              (before["apiUsage"]["state"]=="VALID" and before["apiUsage"]["values"]==after["apiUsage"]["values"])):
            reason="USAGE_PROVENANCE_UNPROVEN"
    if before is not None and after is not None and all(before["context"][k]==after["context"][k] for k in ("maxTokens", "rawMaxTokens")):
        delta=after["context"]["totalTokens"]-before["context"]["totalTokens"]
    return copy.deepcopy(dict(stage=stage, before=before, after=after, witness=witness,
                         outcome="QUALIFIED" if reason=="NONE" else "INCONCLUSIVE", reason=reason, deltaTokens=delta))


def validate_main(value, expected_nonce, expected_session):
    exact(value, {"schema", "schemaVersion", "runNonce", "sessionId", "stages", "outcome", "reason", "cleanupVerified"})
    if value["schema"]!="MAIN_STAGE_CONTEXT_V2" or type(value["schemaVersion"]) is not int or value["schemaVersion"]!=2:
        raise ValueError("invalid main schema")
    if label(value["runNonce"])!=label(expected_nonce) or label(value["sessionId"])!=label(expected_session): raise ValueError("identity mismatch")
    if type(value["cleanupVerified"]) is not bool or value["reason"] not in REASONS: raise ValueError("invalid main flags")
    records=value["stages"]
    if type(records) is not list or len(records)>4: raise ValueError("invalid stage list")
    for stage, record in zip(STAGES, records):
        exact(record, {"stage", "before", "after", "witness", "outcome", "reason", "deltaTokens"})
        if record["stage"]!=stage or record!=finish_stage(stage, record["before"], record["after"], record["witness"]):
            raise ValueError("unverified stage reduction")
    success=(len(records)==4 and all(r["outcome"]=="QUALIFIED" for r in records) and value["cleanupVerified"])
    reason=("CLEANUP_INCONCLUSIVE" if not value["cleanupVerified"] else
            next((r["reason"] for r in records if r["outcome"]!="QUALIFIED"), "NONE" if success else "STATE_UNPROVEN"))
    if value["outcome"] != ("MAIN_STAGE_QUALIFIED" if success else "INCONCLUSIVE") or value["reason"]!=reason:
        raise ValueError("unverified main reduction")
    return copy.deepcopy(value)


def public_main(value):
    value=validate_main(value, value.get("runNonce"), value.get("sessionId"))
    return {k:v for k,v in value.items() if k not in ("runNonce", "sessionId")}


def load_private(path: Path, nonce: str, session: str):
    """Bounded POSIX private evidence; never read a FIFO or follow a symlink."""
    if os.name!="posix": raise ValueError("private evidence requires POSIX")
    fd=os.open(path, os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        info=os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode)!=0o600 or info.st_uid!=os.getuid() or not 1<=info.st_size<=65536:
            raise ValueError("unsafe private evidence")
        def unique(pairs):
            result={}
            for key,val in pairs:
                if key in result: raise ValueError("duplicate key")
                result[key]=val
            return result
        data=os.read(fd,65537)
        if len(data)!=info.st_size: raise ValueError("changed private evidence")
        return validate_main(json.loads(data, object_pairs_hook=unique), nonce, session)
    finally: os.close(fd)
