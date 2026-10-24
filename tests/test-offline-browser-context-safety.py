#!/usr/bin/env python3
"""Zero-native lifecycle, reservation, namespace and publication controls."""
import asyncio
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from browser_context_gateway import Gateway
from browser_context_project import prepare_project

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"tests/offline-browser-context-smoke.py"
spec=importlib.util.spec_from_file_location("context_smoke",SCRIPT)
smoke=importlib.util.module_from_spec(spec);spec.loader.exec_module(smoke)
NODE=Path(os.environ.get("P004B_TERMINAL_NODE",shutil.which("node") or "/missing"))


def fixture_module(name,filename):
    spec=importlib.util.spec_from_file_location(name,ROOT/"tests"/filename)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


class Factory:
    def __init__(self,g,p,*,bad_session=False,no_claim=False,no_history=False,late_fault=False,mutate_policy=False):
        self.g=g;self.p=p;self.clients=[];self.history=[];self.active=0
        self.bad_session=bad_session;self.no_claim=no_claim;self.no_history=no_history;self.late_fault=late_fault
        self.mutate_policy=mutate_policy
        self.sdk_fixtures=fixture_module("sdk_fixtures","test-browser-context-sdk.py")
        self.http=fixture_module("http_fixtures","test-browser-context-gateway.py")
    def __call__(self,policy,session,resume):
        factory=self
        class Client:
            def __init__(self):self.query_calls=0;self.context_calls=0;self.closed=False;self.q=asyncio.Queue();self.latest=None
            async def connect(self):
                if factory.active:raise AssertionError("overlap")
                factory.active+=1
            async def receive_messages(self):
                while True:
                    frame=await self.q.get()
                    if frame is None:return
                    yield frame
            async def get_context_usage(self):
                self.context_calls+=1;r=factory.sdk_fixtures.raw_context(self.context_calls==2)
                if self.latest:r["apiUsage"]=self.latest
                return r
            async def query(self,prompt):
                self.query_calls+=1
                if factory.mutate_policy:factory.p["config"].write_text('{"changed":true}')
                r=factory.http.action(factory.g,policy["stage"],[] if factory.no_history else factory.history)
                self.latest=r["usage"]
                factory.history.append({"role":"assistant","content":r["content"]})
                frames=factory.sdk_fixtures.frames(policy["stage"],"wrong" if factory.bad_session else session)
                for f in frames:
                    if f["type"]=="assistant":f["message"]["usage"]=self.latest
                if policy["stage"]=="subagent" and not factory.no_claim:
                    guard=fixture_module("measurement_guard","browser-measurement-guard.py")
                    value=dict(session_id=session,hook_event_name="PreToolUse",tool_name="Agent",tool_input=policy["input"])
                    guard.evaluate(json.dumps(value).encode(),factory.p["claim"],session)
                if policy["stage"] in ("discovery","use"):
                    calls=[{"jsonrpc":"2.0","id":1,"method":"initialize"},
                           {"jsonrpc":"2.0","id":2,"method":"tools/list"}]
                    if policy["stage"]=="use":calls.append({"jsonrpc":"2.0","id":3,"method":"tools/call","params":{
                        "name":"context_fixture_ping","arguments":{"nonce":"run-001"}}})
                    subprocess.run([sys.executable,str(ROOT/"tests/mcp-context-fixture.py"),str(factory.p["signal"]),"run-001"],
                        input="\n".join(json.dumps(x) for x in calls)+"\n",text=True,stdout=subprocess.DEVNULL,check=True)
                for f in frames:await self.q.put(f)
            async def disconnect(self):
                if factory.late_fault:factory.http.post(factory.g,factory.http.request(policy["stage"]))
                self.closed=True;factory.active-=1;await self.q.put(None)
        client=Client();self.clients.append(client);return client


class SafetyTests(unittest.TestCase):
    @unittest.skipUnless(NODE.is_file(),"existing Node runtime required")
    def test_four_queries_eight_reads_four_clients_no_overlap(self):
        with tempfile.TemporaryDirectory() as d:
            p=prepare_project(ROOT,Path(d),node_path=NODE);g=Gateway("run-001");factory=Factory(g,p)
            r=asyncio.run(smoke.run_main(factory,g,p,nonce="run-001",requested_session="native-001",deadline=time.monotonic()+20))
            self.assertEqual(r["schema"],"MAIN_STAGE_CONTEXT_V2");self.assertEqual(r["outcome"],"MAIN_STAGE_QUALIFIED")
            self.assertEqual([s["stage"] for s in r["stages"]],["skill","subagent","discovery","use"])
            self.assertEqual(len(factory.clients),4)
            self.assertTrue(all(c.query_calls==1 and c.context_calls==2 and c.closed for c in factory.clients))
            self.assertTrue(r["cleanupVerified"]);self.assertEqual((g.user_queries,g.context_calls),(4,8))

    @unittest.skipUnless(NODE.is_file(),"existing Node runtime required")
    def test_mismatch_partial_failure_does_not_start_next_stage(self):
        with tempfile.TemporaryDirectory() as d:
            p=prepare_project(ROOT,Path(d),node_path=NODE);g=Gateway("run-001");factory=Factory(g,p,bad_session=True)
            r=asyncio.run(smoke.run_main(factory,g,p,nonce="run-001",requested_session="native-001",deadline=time.monotonic()+20))
            self.assertEqual(len(factory.clients),1);self.assertEqual(r["reason"],"SESSION_UNPROVEN")

    @unittest.skipUnless(NODE.is_file(),"existing Node runtime required")
    def test_missing_guard_claim_or_continuity_cannot_promote(self):
        for flag in ("no_claim","no_history"):
            with tempfile.TemporaryDirectory() as d:
                p=prepare_project(ROOT,Path(d),node_path=NODE);g=Gateway("run-001");factory=Factory(g,p,**{flag:True})
                r=asyncio.run(smoke.run_main(factory,g,p,nonce="run-001",requested_session="native-001",deadline=time.monotonic()+20))
                self.assertEqual(r["outcome"],"INCONCLUSIVE");self.assertEqual(len(factory.clients),2)

    @unittest.skipUnless(NODE.is_file(),"existing Node runtime required")
    def test_shutdown_fault_refreshes_final_snapshot(self):
        with tempfile.TemporaryDirectory() as d:
            p=prepare_project(ROOT,Path(d),node_path=NODE);g=Gateway("run-001");factory=Factory(g,p,late_fault=True)
            r=asyncio.run(smoke.run_main(factory,g,p,nonce="run-001",requested_session="native-001",deadline=time.monotonic()+20))
            self.assertEqual(r["outcome"],"INCONCLUSIVE");self.assertNotEqual(r["reason"],"NONE")

    @unittest.skipUnless(NODE.is_file(),"existing Node runtime required")
    def test_policy_mutation_within_pair_revokes_success(self):
        with tempfile.TemporaryDirectory() as d:
            p=prepare_project(ROOT,Path(d),node_path=NODE);g=Gateway("run-001");factory=Factory(g,p,mutate_policy=True)
            r=asyncio.run(smoke.run_main(factory,g,p,nonce="run-001",requested_session="native-001",deadline=time.monotonic()+20))
            self.assertEqual(r["reason"],"POLICY_UNPROVEN");self.assertEqual(len(factory.clients),1)
    def test_default_live_legacy_wrong_hash_and_reused_grant_never_spawn(self):
        with mock.patch.object(smoke,"run_namespace",side_effect=AssertionError("must not spawn")):
            self.assertEqual(smoke.main([]),0)
            for args in (["--run-live"],["--run-provenance","x"],["--run-offline","wrong"]):
                self.assertEqual(smoke.main(args),2)
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"attempt.json";sha="a"*64
            with self.assertRaises(ValueError):smoke.reserve(path,sha,"b"*64,"1"*40)
            self.assertFalse(path.exists())
            smoke.reserve(path,sha,sha,"1"*40)
            self.assertEqual(path.stat().st_mode&0o777,0o600)
            with self.assertRaises(FileExistsError):smoke.reserve(path,sha,sha,"1"*40)

    def test_no_operator_environment_or_bundled_cli_mount(self):
        c=smoke.namespace_command(Path("/tmp/owned"),Path("/explicit/sdk"),Path("/explicit/cli"),Path("/explicit/node"),audit=True,parent_net=1)
        self.assertIn("--unshare-net",c);self.assertIn("--cap-drop",c);self.assertIn("--clearenv",c)
        self.assertNotIn("/explicit/cli",c);self.assertIn("/opt/sdk/claude_agent_sdk/_bundled",c)
        bind_sources=[c[i+1] for i,x in enumerate(c[:-2]) if x in ("--bind","--ro-bind")]
        self.assertNotIn(str(Path.home()),bind_sources)

    @unittest.skipUnless(os.name=="posix","POSIX supervisor required")
    def test_harmless_supervisor_timeout_oversize_and_owned_cleanup(self):
        from terminal_cancellation import TerminalCancellation
        for code,error in (("import time;time.sleep(2)",TimeoutError),("print('x'*65537)",ValueError)):
            with TerminalCancellation() as cancellation:
                child=cancellation.spawn([sys.executable,"-I","-c",code],stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,stdin=subprocess.DEVNULL,env={"PATH":"/usr/bin:/bin"})
                try:
                    with self.assertRaises(error):smoke.collect(child,cancellation,time.monotonic()+.25)
                finally:cancellation.terminate_child(child);child.stdout.close()
                self.assertIsNotNone(child.poll())
        root=Path(tempfile.mkdtemp(prefix="p004b-stage-context-",dir="/tmp"));identity=root.lstat()
        self.assertTrue(smoke.dispose_owned(root,identity,"p004b-stage-context-"));self.assertFalse(root.exists())

    def test_partial_cleanup_oversize_output_and_deadline_cannot_publish_success(self):
        report=smoke.empty_report("a"*64,"1"*40)
        for change in ({"cleanupVerified":False},{"elapsedSeconds":601},{"main":{"extra":"raw"}}):
            candidate={**report,**change,"outcome":"MAIN_STAGE_QUALIFIED","reason":"NONE"}
            with self.assertRaises(ValueError):smoke.validate_outer(candidate)
        with self.assertRaises(ValueError):smoke.decode_report(b"x"*65537)

    @unittest.skipUnless(os.name=="posix" and shutil.which("bwrap"),"Linux bubblewrap required")
    def test_actual_zero_cli_namespace_audit(self):
        # This mode intentionally mounts neither a real nor a fake CLI.
        result=smoke.run_namespace(audit=True,sdk_root=None,cli_path=None,node_path=None,deadline=time.monotonic()+20)
        self.assertEqual(result["outcome"],"ISOLATION_AUDIT_PASSED")
        self.assertTrue(result["cleanupVerified"])
        self.assertEqual(result["nativeExecutablesMounted"],0)


if __name__=="__main__":unittest.main()
