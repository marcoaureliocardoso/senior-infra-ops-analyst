#!/usr/bin/env python3
"""Public SDK parser/options in memory; fake clients only, never connect CLI."""
import asyncio
import copy
import importlib.util
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

from browser_context_contract import stage_policy
from browser_context_sdk import StageEvents, build_options, detect_sdk, run_stage

SDK_PRESENT = importlib.util.find_spec("claude_agent_sdk") is not None
U=dict(input_tokens=1251,output_tokens=10,cache_creation_input_tokens=0,cache_read_input_tokens=0)


def frames(stage="skill", sid="native-001"):
    p=stage_policy(stage,"run-001")
    value=[dict(type="system",subtype="init",session_id=sid,tools=p["tools"]),
        dict(type="assistant",session_id=sid,message=dict(id="m1",model="synthetic",stop_reason="tool_use",usage=U,
             content=[dict(type="tool_use",id="t1",name=p["name"],input=p["input"])]))]
    if stage=="subagent":
        for kind in ("hook_started","hook_response"):
            value.append(dict(type="system",subtype=kind,session_id=sid,hook_id="h1",hook_event="PreToolUse",
                hook_name="PreToolUse:Agent",tool_use_id="t1",exit_code=0,outcome="success",
                output='{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow","permissionDecisionReason":"P004B_MEASUREMENT_GUARD_FIRST_CALL"}}'))
    value += [dict(type="user",message={"content":[dict(type="tool_result",tool_use_id="t1",content="synthetic",is_error=False)]}),
        dict(type="assistant",session_id=sid,message=dict(id="m2",model="synthetic",stop_reason="end_turn",usage=U,
             content=[dict(type="text",text="P004B_OK")])),
        dict(type="result",subtype="success",duration_ms=1,duration_api_ms=1,is_error=False,num_turns=2,
             session_id=sid,usage={**U,"input_tokens":9999},result="P004B_OK")]
    return value


def raw_context(after=False):
    r=dict(totalTokens=101 if after else 100,maxTokens=10000,rawMaxTokens=10000,
           percentage=1,isAutoCompactEnabled=True,categories=[])
    if after:r["apiUsage"]=U
    return r


class FakeClient:
    def __init__(self, late=None, close_timeout=False):
        self.order=[]; self.queue=asyncio.Queue(); self.reads=0; self.late=late; self.close_timeout=close_timeout
    async def connect(self): self.order.append("connect")
    async def receive_messages(self):
        self.order.append("consumer")
        while True:
            m=await self.queue.get()
            if m is None:return
            yield m
    async def get_context_usage(self):
        self.reads+=1; self.order.append("before" if self.reads==1 else "after")
        if self.reads==2 and self.late: await self.queue.put(self.late); await asyncio.sleep(0)
        return raw_context(self.reads==2)
    async def query(self,prompt):
        self.order.append("query")
        for f in frames():await self.queue.put(f)
    async def disconnect(self):
        self.order.append("close")
        if self.close_timeout: raise TimeoutError()
        await self.queue.put(None)


class SDKTests(unittest.TestCase):
    def test_declared_sdk_missing_never_qualifies(self):
        self.assertEqual(detect_sdk(SimpleNamespace()), {"available":False,"reason":"CAPABILITY_UNAVAILABLE"})

    @unittest.skipUnless(SDK_PRESENT,"optional public SDK absent; native qualification unavailable")
    def test_options_are_fixed_project_local_and_default_permission(self):
        import claude_agent_sdk as sdk
        self.assertTrue(detect_sdk(sdk)["available"])
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); cli=root/"cli"; cli.touch()
            for stage in ("skill","subagent","discovery","use"):
                p=stage_policy(stage,"run-001"); o=build_options(p,root,cli,"native-001",resume=stage!="skill")
                self.assertEqual(o.tools,p["tools"]);self.assertEqual(o.allowed_tools,p["allowed_tools"])
                self.assertEqual(o.permission_mode,"default");self.assertEqual(o.setting_sources,["project","local"])
                self.assertEqual(o.system_prompt,{"type":"preset","preset":"claude_code"})
                self.assertTrue(o.strict_mcp_config);self.assertIsNone(o.agents)
                self.assertEqual(Path(o.cli_path),cli.resolve());self.assertEqual(o.max_turns,4)
                self.assertEqual(o.max_buffer_size,128*1024)
                self.assertEqual(o.resume,"native-001" if stage!="skill" else None)

    @unittest.skipUnless(SDK_PRESENT,"optional public SDK absent; parser checks skipped explicitly")
    def test_parser_preserves_latest_usage_and_agent_hook_fields(self):
        from claude_agent_sdk._internal.message_parser import parse_message
        for stage in ("skill","subagent"):
            e=StageEvents(stage_policy(stage,"run-001"),"native-001")
            for raw in frames(stage):e.feed(parse_message(raw))
            self.assertTrue(e.terminal); self.assertEqual(e.snapshot()["latestResponseUsage"],U)
            self.assertTrue(e.snapshot()["sessionBound"])
            self.assertEqual(e.snapshot()["measurementHook"],"OBSERVED" if stage=="subagent" else "NOT_REQUIRED")

    def test_missing_partial_cumulative_nested_or_replayed_usage_is_unproven(self):
        for bad in (None,{"input_tokens":1251}):
            events=frames();events[-2]["message"]["usage"]=bad
            e=StageEvents(stage_policy("skill","run-001"),"native-001")
            for f in events:e.feed(f)
            self.assertIsNone(e.snapshot()["latestResponseUsage"])
        events=frames();events[-2]["parent_tool_use_id"]="t1"
        e=StageEvents(stage_policy("skill","run-001"),"native-001")
        for f in events:e.feed(f)
        self.assertIsNone(e.snapshot()["latestResponseUsage"])

    def test_actual_init_result_must_match(self):
        for index in (0,-1):
            events=frames();events[index]["session_id"]="wrong"
            e=StageEvents(stage_policy("skill","run-001"),"native-001")
            for f in events:e.feed(f)
            self.assertFalse(e.snapshot()["sessionBound"])
            self.assertEqual(e.fault,"SESSION_UNPROVEN")

    def test_advertised_policy_drift_is_not_fixed(self):
        events=frames();events[0]["tools"].append("Bash")
        e=StageEvents(stage_policy("skill","run-001"),"native-001")
        for frame in events:e.feed(frame)
        self.assertEqual(e.fault,"POLICY_UNPROVEN")
        self.assertFalse(e.snapshot()["policyFixed"])

    def test_unexpected_background_reset_or_compaction_stops(self):
        for late in (dict(type="system",subtype="compact_boundary"),dict(type="conversation_reset"),
                     dict(type="system",subtype="task_started"),
                     dict(type="assistant",session_id="native-001",message={"content":[{"type":"tool_use","id":"x","name":"Bash","input":{}}]})):
            e=StageEvents(stage_policy("skill","run-001"),"native-001")
            for f in frames()+[late]:e.feed(f)
            self.assertNotEqual(e.fault,"NONE")

    def test_one_consumer_before_query_after_close_order(self):
        c=FakeClient(); arms=[]
        result=asyncio.run(run_stage(c,stage_policy("skill","run-001"),"native-001",resume=False,
            before_query=lambda x:arms.append(x),history_check=lambda:True,claim_check=lambda:True,stage_deadline=time.monotonic()+5))
        self.assertEqual(c.order,["connect","consumer","before","query","after","close"])
        self.assertEqual(len(arms),1);self.assertTrue(result["clientsClosed"])
        self.assertEqual(result["record"]["outcome"],"QUALIFIED")

    def test_after_result_tool_or_hook_failure_revokes_success(self):
        for late in (dict(type="system",subtype="hook_response",hook_event="PreToolUse",outcome="error"),
                     dict(type="system",subtype="task_notification")):
            c=FakeClient(late=late)
            r=asyncio.run(run_stage(c,stage_policy("skill","run-001"),"native-001",resume=False,
                before_query=lambda x:None,history_check=lambda:True,claim_check=lambda:True,stage_deadline=time.monotonic()+5))
            self.assertEqual(r["record"]["outcome"],"INCONCLUSIVE")

    def test_close_timeout_dominates_pair(self):
        c=FakeClient(close_timeout=True)
        r=asyncio.run(run_stage(c,stage_policy("skill","run-001"),"native-001",resume=False,
            before_query=lambda x:None,history_check=lambda:True,claim_check=lambda:True,stage_deadline=time.monotonic()+.2))
        self.assertFalse(r["clientsClosed"]);self.assertEqual(r["record"]["reason"],"CLEANUP_INCONCLUSIVE")

    def test_invalid_before_stops_without_query(self):
        class InvalidBefore(FakeClient):
            async def get_context_usage(self):
                self.order.append("before")
                return {**raw_context(),"apiUsage":{"input_tokens":True}}
        c=InvalidBefore()
        r=asyncio.run(run_stage(c,stage_policy("skill","run-001"),"native-001",resume=False,
            before_query=lambda x:None,history_check=lambda:True,claim_check=lambda:True,stage_deadline=time.monotonic()+5))
        self.assertNotIn("query",c.order)
        self.assertEqual(r["record"]["reason"],"INVALID_OBSERVATION")


if __name__=="__main__":unittest.main()
