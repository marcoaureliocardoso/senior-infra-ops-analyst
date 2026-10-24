"""Public-SDK boundary for the test-only stage-owned context experiment.

Importing this module never connects, runs a version probe or selects a CLI.
"""
from __future__ import annotations

import asyncio
import dataclasses
import inspect
import json
import time
from pathlib import Path

from browser_context_contract import (finish_stage, label, project_api_usage,
                                      project_context, usage_tuple)


def detect_sdk(sdk: object) -> dict:
    client=getattr(sdk,"ClaudeSDKClient",None); options=getattr(sdk,"ClaudeAgentOptions",None)
    required={"tools","allowed_tools","permission_mode","setting_sources","system_prompt","strict_mcp_config",
              "max_turns","max_buffer_size","cli_path","session_id","resume","include_hook_events"}
    fields=set(getattr(options,"__dataclass_fields__",{}))
    available=(required <= fields and all(callable(getattr(client,k,None)) for k in
               ("connect","query","receive_messages","get_context_usage","disconnect")))
    return dict(available=available,reason="NONE" if available else "CAPABILITY_UNAVAILABLE")


def build_options(policy: dict, owned_root: Path, cli_path: Path, session_id: str, *, resume: bool):
    import claude_agent_sdk as sdk
    if not detect_sdk(sdk)["available"]: raise ValueError("CAPABILITY_UNAVAILABLE")
    root=owned_root.resolve(strict=True); cli=cli_path.resolve(strict=True); label(session_id)
    return sdk.ClaudeAgentOptions(
        tools=list(policy["tools"]), allowed_tools=list(policy["allowed_tools"]),
        system_prompt={"type":"preset","preset":"claude_code"},
        permission_mode="default",setting_sources=["project","local"],strict_mcp_config=True,
        mcp_servers=root/("fixture-mcp.json" if policy["mcp"]=="fixture" else "empty-mcp.json"),
        cwd=root/"project",cli_path=cli,max_turns=4,max_buffer_size=128*1024,include_hook_events=True,
        session_id=None if resume else session_id,resume=session_id if resume else None)


def wire(message):
    """Normalize public dataclasses, retaining metadata only for ephemeral checks."""
    if type(message) is dict:return message
    if not dataclasses.is_dataclass(message):raise ValueError("CAPABILITY_UNAVAILABLE")
    data=dataclasses.asdict(message); kind=type(message).__name__
    if kind=="AssistantMessage":
        content=[]
        for block in message.content:
            value=dataclasses.asdict(block)
            block_kind=type(block).__name__
            value["type"]={"ToolUseBlock":"tool_use","ToolResultBlock":"tool_result","TextBlock":"text",
                           "ThinkingBlock":"thinking"}.get(block_kind,"unknown")
            content.append(value)
        return dict(type="assistant",session_id=message.session_id,parent_tool_use_id=message.parent_tool_use_id,
                    error=message.error,message=dict(id=message.message_id,stop_reason=message.stop_reason,
                                                    usage=message.usage,content=content))
    if kind=="UserMessage":
        blocks=[]
        if isinstance(message.content,list):
            for block in message.content:
                value=dataclasses.asdict(block)
                value["type"]="tool_result" if type(block).__name__=="ToolResultBlock" else "unknown"
                blocks.append(value)
        return dict(type="user",parent_tool_use_id=message.parent_tool_use_id,origin=message.origin,
                    message={"content":blocks})
    if kind in ("SystemMessage","HookEventMessage","TaskStartedMessage","TaskNotificationMessage","TaskProgressMessage","TaskUpdatedMessage","MirrorErrorMessage"):
        return {**message.data,"type":"system","subtype":message.subtype}
    if kind=="ResultMessage":return {**data,"type":"result"}
    if kind=="ConversationResetMessage":return {**data,"type":"conversation_reset"}
    raise ValueError("CAPABILITY_UNAVAILABLE")


class StageEvents:
    """Sticky reducer; result success remains provisional until stream closure."""
    def __init__(self,policy,expected_session):
        self.policy=policy; self.expected_session=label(expected_session)
        self.session_id=None;self.init=False;self.result=False;self.terminal=False;self.fault="NONE"
        self.calls={};self.completed=set();self.message_ids=set();self.hooks={};self.hook_done=False
        self.latest=None;self.advertised=False;self.policy_fixed=False;self.search=False;self.unexpected=0

    def fail(self,reason):
        if self.fault=="NONE":self.fault=reason

    def feed(self,message):
        try:self._feed(wire(message))
        except (ValueError,TypeError,KeyError,AttributeError):self.fail("CAPABILITY_UNAVAILABLE")

    def _feed(self,m):
        kind=m.get("type"); parent=m.get("parent_tool_use_id")
        if kind=="conversation_reset":self.fail("STATE_UNPROVEN");return
        if kind=="system":
            subtype=m.get("subtype")
            if subtype=="init":
                if self.init or self.terminal:self.fail("STATE_UNPROVEN")
                self.init=True
                if m.get("session_id")!=self.expected_session:self.fail("SESSION_UNPROVEN")
                else:self.session_id=m["session_id"]
                tools=m.get("tools")
                self.advertised=(type(tools) is list and len(tools)<=4096 and all(type(x) is str for x in tools))
                self.search=self.advertised and "ToolSearch" in tools
                if not self.advertised:self.fail("CAPABILITY_UNAVAILABLE")
                permitted=set(self.policy["tools"])
                if self.policy["mcp"]=="fixture":permitted.add("mcp__p004b-context__context_fixture_ping")
                self.policy_fixed=self.advertised and len(set(tools))==len(tools) and set(tools)<=permitted
                if self.advertised and not self.policy_fixed:self.fail("POLICY_UNPROVEN")
                return
            if subtype in ("hook_started","hook_response"):
                if m.get("outcome") not in (None,"success") or m.get("exit_code") not in (None,0):
                    self.fail("HOOK_UNPROVEN");return
                if self.policy["stage"]!="subagent" or m.get("hook_event")!="PreToolUse":
                    # Successful configured hooks are not operational qualification.
                    return
                if self.terminal:self.fail("HOOK_UNPROVEN");return
                if (m.get("session_id")!=self.expected_session or m.get("hook_name")!="PreToolUse:Agent" or
                    m.get("tool_use_id") not in self.calls):self.fail("HOOK_UNPROVEN");return
                hid=label(m.get("hook_id"))
                if subtype=="hook_started":
                    if hid in self.hooks:self.fail("HOOK_UNPROVEN")
                    self.hooks[hid]=m["tool_use_id"]
                else:
                    if self.hooks.pop(hid,None)!=m["tool_use_id"] or self.hook_done:self.fail("HOOK_UNPROVEN");return
                    output=m.get("output")
                    if type(output) is not str or len(output.encode())>32768:self.fail("HOOK_UNPROVEN");return
                    parsed=json.loads(output).get("hookSpecificOutput",{})
                    self.hook_done=(m.get("exit_code")==0 and m.get("outcome")=="success" and
                        parsed.get("hookEventName")=="PreToolUse" and parsed.get("permissionDecision")=="allow" and
                        parsed.get("permissionDecisionReason")=="P004B_MEASUREMENT_GUARD_FIRST_CALL")
                    if not self.hook_done:self.fail("HOOK_UNPROVEN")
                return
            # A reset, deferred task, retry, compaction or unknown system event cannot be assumed harmless.
            self.fail("STATE_UNPROVEN");return
        if kind=="assistant":
            if self.terminal:self.fail("STATE_UNPROVEN")
            if not self.init:self.fail("SESSION_UNPROVEN")
            if m.get("session_id")!=self.expected_session:self.fail("SESSION_UNPROVEN")
            if m.get("error"):self.fail("STATE_UNPROVEN")
            msg=m["message"];content=msg.get("content")
            if type(content) is not list or len(content)>4096:self.fail("STATE_UNPROVEN");return
            for block in content:
                if block.get("type")=="tool_use":
                    if parent or block.get("name")!=self.policy["name"] or block.get("input")!=self.policy["input"] or self.calls:
                        self.unexpected=min(40,self.unexpected+1);self.fail("UNEXPECTED_TOOL");continue
                    tid=label(block.get("id"));self.calls[tid]=True
                elif block.get("type") not in ("text","thinking"):self.fail("UNEXPECTED_TOOL")
            if not parent:
                self.latest=None
                mid=msg.get("id")
                if not mid or mid in self.message_ids:self.fail("USAGE_PROVENANCE_UNPROVEN")
                else:self.message_ids.add(mid)
                if msg.get("stop_reason")=="end_turn":
                    try:self.latest=usage_tuple({k:msg["usage"][k] for k in ("input_tokens","output_tokens","cache_creation_input_tokens","cache_read_input_tokens")})
                    except (KeyError,TypeError,ValueError):self.latest=None
            return
        if kind=="user":
            if self.terminal:self.fail("STATE_UNPROVEN")
            if m.get("origin") is not None:self.fail("STATE_UNPROVEN")
            for block in m.get("message",{}).get("content",[]):
                if block.get("type")!="tool_result":self.fail("STATE_UNPROVEN");continue
                tid=block.get("tool_use_id")
                if tid not in self.calls or tid in self.completed or block.get("is_error") not in (None,False):self.fail("STATE_UNPROVEN")
                else:self.completed.add(tid)
            return
        if kind=="result":
            if parent:return  # child totals are not latest top-level usage
            if self.terminal:self.fail("STATE_UNPROVEN")
            self.terminal=True
            if m.get("session_id")!=self.expected_session:self.fail("SESSION_UNPROVEN")
            if (m.get("subtype")!="success" or m.get("is_error") is not False or m.get("deferred_tool_use") or
                m.get("permission_denials") or m.get("errors") or m.get("origin") or
                m.get("terminal_reason") not in (None,"completed")):self.fail("STATE_UNPROVEN")
            self.result=self.fault=="NONE";return
        self.fail("CAPABILITY_UNAVAILABLE")

    def snapshot(self):
        return dict(latestResponseUsage=self.latest,sessionBound=self.init and self.result and self.session_id==self.expected_session and self.fault!="SESSION_UNPROVEN",
                    policyFixed=self.policy_fixed,historyLinked="NOT_REQUIRED" if self.policy["stage"]=="skill" else "UNPROVEN",
                    measurementHook=("OBSERVED" if self.hook_done and not self.hooks else "UNPROVEN") if self.policy["stage"]=="subagent" else "NOT_REQUIRED",
                    claimVerified=False,actionCalls=len(self.calls),toolResultsComplete=self.terminal and set(self.calls)==self.completed,
                    toolSearchAvailable=self.search,unexpectedCalls=self.unexpected,fault=self.fault)


async def run_stage(client,policy,expected_session,*,resume,before_query,history_check,claim_check,stage_deadline):
    events=StageEvents(policy,expected_session); before=after=None; closed=False; consumer=None
    terminal=asyncio.Event()
    def remaining(limit=25):return max(0,min(limit,stage_deadline-time.monotonic()))
    async def receive():
        try:
            async for message in client.receive_messages():
                events.feed(message)
                if events.terminal or events.fault!="NONE":terminal.set()
        except Exception:events.fail("CAPABILITY_UNAVAILABLE");terminal.set()
        finally:
            if not events.terminal:events.fail("STATE_UNPROVEN")
            terminal.set()
    try:
        async with asyncio.timeout(remaining()):await client.connect()
        consumer=asyncio.create_task(receive())
        await asyncio.sleep(0)
        async with asyncio.timeout(remaining()):
            raw=await client.get_context_usage();before=dict(context=project_context(raw),apiUsage=project_api_usage(raw))
        if before["apiUsage"]["state"]=="INVALID":raise ValueError("INVALID_OBSERVATION")
        if before["context"]["autoCompactEnabled"] is not True:
            events.fail("POLICY_UNPROVEN");raise ValueError("POLICY_UNPROVEN")
        value=before_query(before)
        if inspect.isawaitable(value):await value
        async with asyncio.timeout(remaining()):await client.query(policy["prompt"])
        async with asyncio.timeout(remaining(120)):await terminal.wait()
        if events.fault=="NONE" and events.terminal:
            async with asyncio.timeout(remaining()):
                raw=await client.get_context_usage();after=dict(context=project_context(raw),apiUsage=project_api_usage(raw))
    except TimeoutError:events.fail("OPERATION_TIMEOUT")
    except ValueError as exc:events.fail(str(exc) if str(exc) in ("CHALLENGE_UNAVAILABLE","CAPABILITY_UNAVAILABLE") else "INVALID_OBSERVATION")
    except Exception:events.fail("STATE_UNPROVEN")
    finally:
        try:
            async with asyncio.timeout(remaining()):
                await client.disconnect()
                if consumer:await consumer
            closed=True
        except (TimeoutError,Exception):
            events.fault="CLEANUP_INCONCLUSIVE"
            if consumer:
                consumer.cancel()
                try:await consumer
                except (asyncio.CancelledError,Exception):pass
    w=events.snapshot()
    if resume:w["historyLinked"]="OBSERVED" if history_check() is True else "UNPROVEN"
    w["claimVerified"]=claim_check() is True if policy["stage"]=="subagent" else True
    return dict(sessionId=events.session_id,record=finish_stage(policy["stage"],before,after,w),clientsClosed=closed)
