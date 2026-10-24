#!/usr/bin/env python3
"""Actual loopback HTTP controls, zero native clients."""
import http.client
import json
import socket
import unittest

from browser_context_contract import stage_policy
from browser_context_gateway import Gateway, MAX_BODY


def before():
    return {"context":dict(totalTokens=100,maxTokens=10000,rawMaxTokens=10000,percentage=1,
            autoCompactEnabled=True,categoryCount=0),"apiUsage":{"state":"NULL","values":None}}


def request(stage="skill",nonce="run-001",history=None,stream=False,search=True):
    p=stage_policy(stage,nonce)
    return dict(model="synthetic",max_tokens=64,stream=stream,
        tools=[{"name":p["name"],"input_schema":{"type":"object"}}] if stage!="discovery" or search else [],
        messages=(history or [])+[{"role":"user","content":p["prompt"]}])


def post(g,body,path="/v1/messages",method="POST"):
    data=json.dumps(body).encode() if isinstance(body,dict) else body
    c=http.client.HTTPConnection("127.0.0.1",g.port,timeout=3)
    c.request(method,path,body=data,headers={"Content-Type":"application/json"})
    r=c.getresponse();raw=r.read();c.close()
    return r.status, raw


def action(g,stage="skill",history=None):
    body=request(stage,history=history);status,raw=post(g,body)
    if status!=200:raise AssertionError("synthetic action failed")
    reply=json.loads(raw)
    if reply["stop_reason"]=="tool_use":
        body["messages"] += [{"role":"assistant","content":reply["content"]},
            {"role":"user","content":[{"type":"tool_result","tool_use_id":reply["content"][0]["id"],"content":"synthetic"}]}]
        status,raw=post(g,body);reply=json.loads(raw)
    return reply


class GatewayTests(unittest.TestCase):
    def test_json_and_sse_accounting_agree(self):
        tuples=[]
        for stream in (False,True):
            with Gateway("run-001") as g:
                g.begin_stage("skill");g.arm(before())
                status,raw=post(g,request(stream=stream));self.assertEqual(status,200)
                if stream:
                    events=[json.loads(line[6:]) for line in raw.decode().splitlines() if line.startswith("data: ")]
                    start=events[0]["message"]["usage"];start.update(events[-2]["usage"]);tuples.append(start)
                else:tuples.append(json.loads(raw)["usage"])
        self.assertEqual(tuples[0],tuples[1]);self.assertEqual(tuples[0]["input_tokens"],1251)

    def test_stage_tool_script_is_exact(self):
        with Gateway("run-001") as g:
            g.begin_stage("skill");g.arm(before())
            status,raw=post(g,request());reply=json.loads(raw);p=stage_policy("skill","run-001")
            self.assertEqual(reply["content"][0]["name"],p["name"]);self.assertEqual(reply["content"][0]["input"],p["input"])
            self.assertNotIn("marker",json.dumps(g.snapshot()).lower())

    def test_agent_child_requests_count_toward_global_budget(self):
        with Gateway("run-001") as g:
            g.begin_stage("skill");g.arm(before());reply=action(g)
            history=[{"role":"assistant","content":reply["content"]}]
            g.begin_stage("subagent");g.arm(before());post(g,request("subagent",history=history))
            child=dict(model="synthetic",messages=[{"role":"user","content":"P004B_SUBAGENT_ACK"}])
            self.assertEqual(post(g,child)[0],200);self.assertEqual(g.snapshot()["generationAttempts"],4)

    def test_available_and_unavailable_search_branches(self):
        for search in (False,True):
            with Gateway("run-001") as g:
                history=[]
                for stage in ("skill","subagent"):
                    g.begin_stage(stage);g.arm(before());r=action(g,stage,history)
                    history.append({"role":"assistant","content":r["content"]})
                g.begin_stage("discovery");g.arm(before())
                status,raw=post(g,request("discovery",history=history,search=search))
                self.assertEqual(status,200);r=json.loads(raw)
                self.assertEqual(r["stop_reason"],"tool_use" if search else "end_turn")

    def test_nonce_ping_occurs_once(self):
        with Gateway("run-001") as g:
            history=[]
            for stage in ("skill","subagent","discovery"):
                g.begin_stage(stage);g.arm(before());r=action(g,stage,history)
                history.append({"role":"assistant","content":r["content"]})
            g.begin_stage("use");g.arm(before());r=action(g,"use",history)
            self.assertEqual(g.snapshot()["fault"],"NONE")
            self.assertNotEqual(post(g,request("use",history=history))[0],200)

    def test_prior_marker_must_be_assistant_history_from_current_run(self):
        with Gateway("run-001") as g:
            g.begin_stage("skill");g.arm(before());r=action(g)
            g.begin_stage("subagent");g.arm(before())
            self.assertEqual(post(g,request("subagent",history=[{"role":"assistant","content":r["content"]}]))[0],200)
            self.assertTrue(g.snapshot()["historyLinked"]["subagent"])

    def test_fixed_ack_system_user_text_other_stage_and_other_run_do_not_bind(self):
        for role in ("user","system"):
            with Gateway("run-001") as g:
                g.begin_stage("skill");g.arm(before());r=action(g)
                g.begin_stage("subagent");g.arm(before())
                self.assertEqual(post(g,request("subagent",history=[{"role":role,"content":r["content"]}]))[0],409)
                self.assertEqual(g.snapshot()["fault"],"HISTORY_UNPROVEN")

    def test_local_removed_corrupt_substitute_history_fails(self):
        for content in ("P004B_SKILL_OK","removed","another-run-marker"):
            with Gateway("run-001") as g:
                g.begin_stage("skill");g.arm(before());action(g)
                g.begin_stage("subagent");g.arm(before())
                self.assertEqual(post(g,request("subagent",history=[{"role":"assistant","content":content}]))[0],409)

    def test_40_generation_192_total_48_stage_budgets(self):
        with Gateway("run-001") as g:
            history=[]
            for stage in ("skill","subagent","discovery","use"):
                g.begin_stage(stage)
                for _ in range(48):self.assertEqual(post(g,{"messages":[]},"/v1/messages/count_tokens")[0],200)
                g.arm(before());r=action(g,stage,history);history.append({"role":"assistant","content":r["content"]})
            self.assertEqual(g.snapshot()["countAttempts"],192)
            self.assertEqual(post(g,{"messages":[]},"/v1/messages/count_tokens")[0],409)
            self.assertEqual(g.snapshot()["fault"],"BUDGET_INCONCLUSIVE")
        with Gateway("run-001") as g:
            g.begin_stage("skill");g.arm(before());r=action(g)
            g.begin_stage("subagent");g.arm(before());post(g,request("subagent",history=[{"role":"assistant","content":r["content"]}]))
            child={"messages":[{"role":"user","content":"P004B_SUBAGENT_ACK"}]}
            for _ in range(37):self.assertEqual(post(g,child)[0],200)
            self.assertEqual(g.snapshot()["generationAttempts"],40)
            self.assertEqual(post(g,child)[0],409)
            self.assertEqual(g.snapshot()["fault"],"BUDGET_INCONCLUSIVE")

    def test_duplicate_generation_parser_methods_and_timeout_faults_are_sticky(self):
        for payload,method in ((b'{"messages":[],"messages":[]}',"POST"),(b'{"x":NaN}',"POST"),(b'{}',"GET")):
            with Gateway("run-001") as g:
                g.begin_stage("skill");g.arm(before());self.assertNotEqual(post(g,payload,method=method)[0],200)
                fault=g.snapshot()["fault"];self.assertNotEqual(fault,"NONE")
                self.assertNotEqual(post(g,request())[0],200);self.assertEqual(g.snapshot()["fault"],fault)
        with Gateway("run-001") as g:
            g.begin_stage("skill")
            self.assertEqual(post(g,request())[0],409);self.assertEqual(g.snapshot()["fault"],"STATE_UNPROVEN")
        with Gateway("run-001") as g:
            g.begin_stage("skill")
            s=socket.create_connection(("127.0.0.1",g.port));s.sendall(b"POST /v1/messages HTTP/1.1\r\nHost: localhost\r\nContent-Length: 10\r\n\r\n{")
            s.settimeout(3);s.recv(4096);s.close()
            self.assertEqual(g.snapshot()["fault"],"STATE_UNPROVEN")

    def test_body_cap_exact_and_one_byte_overflow(self):
        for length,expected in ((MAX_BODY,200),(MAX_BODY+1,413)):
            with Gateway("run-001") as g:
                g.begin_stage("skill")
                raw=b'{"messages":[],"padding":"'+b'x'*(length-29)+b'"}'
                # Derive padding from encoded base, not a hand-counted JSON delimiter.
                base=b'{"messages":[],"padding":""}'
                raw=base[:-2]+b'x'*(length-len(base))+base[-2:]
                self.assertEqual(len(raw),length)
                self.assertEqual(post(g,raw,"/v1/messages/count_tokens")[0],expected)

    def test_late_request_fault_is_visible_after_exit(self):
        with Gateway("run-001") as g:
            g.begin_stage("skill");g.arm(before());action(g)
            post(g,request());self.assertNotEqual(g.snapshot()["fault"],"NONE")
        self.assertTrue(g.stopped);self.assertNotEqual(g.snapshot()["fault"],"NONE")

    def test_shutdown_waits_for_inflight_request_fault(self):
        with Gateway("run-001") as g:
            g.begin_stage("skill")
            s=socket.create_connection(("127.0.0.1",g.port))
            s.sendall(b"POST /v1/messages HTTP/1.1\r\nHost: localhost\r\nContent-Length: 10\r\n\r\n{")
            # The counting fact proves that the handler is in flight, not merely queued in TCP.
            import time
            deadline=time.monotonic()+1
            while not g.snapshot()["generationAttempts"] and time.monotonic()<deadline:time.sleep(.001)
        s.close()
        self.assertTrue(g.stopped)
        self.assertEqual(g.snapshot()["fault"],"STATE_UNPROVEN")


if __name__=="__main__":unittest.main()
