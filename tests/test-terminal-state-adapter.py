"""Real private-process boundary tests; no provider or operator configuration."""
import dataclasses
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / 'tests/terminal_state_adapter.py'


class TerminalStateTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(MODULE.is_file(), 'terminal state interface missing')
        spec = importlib.util.spec_from_file_location('terminal_state_adapter', MODULE)
        self.module = importlib.util.module_from_spec(spec)
        # Dataclass annotations need a registered module during import.
        import sys
        sys.modules[spec.name] = self.module
        spec.loader.exec_module(self.module)
        self.node = Path(os.environ['P004B_TERMINAL_NODE']).resolve(strict=True)
        self.modules = Path(os.environ['P004B_TERMINAL_MODULE_ROOT']).resolve(strict=True)
        self.temp = tempfile.TemporaryDirectory(prefix='terminal-transport-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def state(self, node=None, seconds=5):
        state = self.module.TerminalState(node or self.node, self.modules, time.monotonic()+seconds)
        self.addCleanup(state.close)
        return state

    def helper(self, body):
        helper = self.root / 'node-fixture'
        helper.write_text('#!/usr/bin/python3\n'+body, encoding='utf-8')
        helper.chmod(0o700)
        return helper

    def replying_helper(self, snapshot):
        return self.helper('import json, sys\n' +
            'snapshot = '+repr(snapshot)+'\n' +
            'for line in sys.stdin:\n' +
            ' request=json.loads(line)\n' +
            ' value={"id":request["id"],"ok":True}\n' +
            ' if request["op"]=="snapshot": value["snapshot"]=snapshot\n' +
            ' print(json.dumps(value,separators=(",",":")),flush=True)\n' +
            ' if request["op"]=="close": break\n')

    def valid_snapshot(self):
        return {'active':'normal','cursorX':0,'cursorY':0,'baseY':0,'viewportY':0,
            'rows':[[{'text':'','width':1} for _ in range(120)] for _ in range(40)],
            'replyCounts':{'primaryAttributes':0,'secondaryAttributes':0,
                'cursorPosition':0,'status':0,'other':0}}

    def test_round_trip_real_cells(self):
        state = self.state()
        state.feed('界e\u0301\u00a0'.encode())
        snapshot = state.snapshot()
        self.assertEqual(snapshot.rows[0][0].width,2)
        self.assertEqual(snapshot.rows[0][1].width,0)
        self.assertEqual(snapshot.rows[0][2].text,'e\u0301')
        self.assertEqual(snapshot.rows[0][3].text,'\u00a0')
        self.assertEqual(snapshot.cursorX,4)
        self.assertEqual(snapshot.active,'normal')
        with self.assertRaises(dataclasses.FrozenInstanceError):
            snapshot.cursorX=1

    def test_original_deadline_view_is_passive_and_read_only(self):
        state=self.state()
        self.assertTrue(hasattr(type(state),'operation_deadline'),'original deadline view missing')
        request_id=state._id
        self.assertEqual(state.operation_deadline,state._deadline)
        self.assertEqual(state._id,request_id)
        with self.assertRaises(AttributeError): state.operation_deadline=time.monotonic()+100

    def test_real_engine_restore_and_reply_counts(self):
        state = self.state()
        state.feed(b'MAIN\x1b[?1049hALT\x1b[c\x1b[6n')
        self.assertEqual(state.snapshot().active,'alternate')
        state.feed(b'\x1b[?1049l')
        result = state.snapshot()
        self.assertEqual(result.active,'normal')
        self.assertEqual(result.cursorX,4)
        self.assertEqual(result.replyCounts['primaryAttributes'],1)
        self.assertEqual(result.replyCounts['cursorPosition'],1)

    def test_schema_rejects_hostile_child(self):
        for field,value in [('active','other'),('cursorX',121),('cursorY',40),
                            ('baseY',-1),('viewportY',True),('extra',0)]:
            with self.subTest(field=field):
                snapshot = self.valid_snapshot(); snapshot[field]=value
                state = self.state(self.replying_helper(snapshot))
                with self.assertRaises(self.module.TerminalStateError) as error:
                    state.snapshot()
                self.assertEqual(error.exception.reason,'TERMINAL_PROTOCOL_REJECTED')
                state.close()
        for cell in ({'text':'x','width':3},{'text':'x'*17,'width':1},
                     {'text':'x','width':True},{'text':'x','width':1,'extra':True}):
            snapshot=self.valid_snapshot(); snapshot['rows'][0][0]=cell
            state=self.state(self.replying_helper(snapshot))
            with self.assertRaises(self.module.TerminalStateError): state.snapshot()
            state.close()

    def test_duplicate_unknown_and_wrong_reply_id(self):
        for payload in ('{"id":1,"id":1,"ok":true}', '{"id":1,"ok":true,"extra":0}',
                        '{"id":2,"ok":true}', '{"id":NaN,"ok":true}'):
            node=self.helper('import sys\nsys.stdin.readline()\nprint('+repr(payload)+',flush=True)\n')
            with self.assertRaises(self.module.TerminalStateError) as error:
                self.state(node)
            self.assertEqual(error.exception.reason,'TERMINAL_PROTOCOL_REJECTED')

    def test_wide_cell_continuations_must_be_consistent(self):
        for cells in ([{'text':'','width':0}], [{'text':'界','width':2}],
                      [{'text':'界','width':2},{'text':'x','width':0}]):
            with self.subTest(count=len(cells)):
                snapshot=self.valid_snapshot()
                snapshot['rows'][0][:len(cells)]=cells
                state=self.state(self.replying_helper(snapshot))
                try:
                    with self.assertRaises(self.module.TerminalStateError): state.snapshot()
                finally: state.close()

    def test_timeout_stderr_and_unterminated_frame(self):
        cases = [('import time\ntime.sleep(60)\n','TERMINAL_DEADLINE_EXCEEDED'),
            ('import os, time\nos.write(2,b"diagnostic"*20000)\ntime.sleep(60)\n','TERMINAL_PROTOCOL_REJECTED'),
            ('import os, time\nos.write(1,b"x"*131073)\ntime.sleep(60)\n','TERMINAL_PROTOCOL_REJECTED')]
        for body,reason in cases:
            node=self.helper(body); started=time.monotonic()
            with self.assertRaises(self.module.TerminalStateError) as error:
                self.state(node,seconds=.5)
            self.assertEqual(error.exception.reason,reason)
            self.assertLess(time.monotonic()-started,2)
            self.assertEqual(str(error.exception),reason)

    def test_clean_environment_and_invalid_paths(self):
        node=self.helper('import os, json, sys\n'
            'for line in sys.stdin:\n'
            ' r=json.loads(line)\n'
            ' if any(k in os.environ for k in ("ANTHROPIC_API_KEY","NODE_OPTIONS","NODE_PATH","HOME")): sys.exit(2)\n'
            ' print(json.dumps({"id":r["id"],"ok":True}),flush=True)\n'
            ' if r["op"]=="close": break\n')
        with mock.patch.dict(os.environ,{'NODE_OPTIONS':'--unused','NODE_PATH':'/invalid','ANTHROPIC_API_KEY':'synthetic'}):
            state=self.state(node); state.close()
        with self.assertRaises(self.module.TerminalStateError):
            self.module.validate_terminal_runtime(Path('relative'),self.modules)
        link=self.root/'modules'; link.symlink_to(self.modules)
        with self.assertRaises(self.module.TerminalStateError):
            self.module.validate_terminal_runtime(self.node,link)
        with self.assertRaises(self.module.TerminalStateError):
            self.module.validate_terminal_runtime(self.node,self.root)

    def test_close_on_every_path(self):
        state=self.state(); state.close(); state.close()
        with self.assertRaises(self.module.TerminalStateError): state.snapshot()
        failing=self.state()
        with self.assertRaises(self.module.TerminalStateError): failing.feed(b'x'*65537)
        failing.close()

    def test_reap_observation_is_passive_and_does_not_hide_expired_close(self):
        state=self.state()
        self.assertTrue(hasattr(type(state),'helper_reaped'),'passive helper observation missing')
        request_id=state._id
        self.assertFalse(state.helper_reaped)
        self.assertEqual(state._id,request_id)
        state._deadline=time.monotonic()-1
        with self.assertRaises(self.module.TerminalStateError) as error: state.close()
        self.assertEqual(error.exception.reason,'TERMINAL_DEADLINE_EXCEEDED')
        self.assertTrue(state.helper_reaped)

    def test_timeout_terminates_owned_descendant_group(self):
        pidfile=self.root/'child.pid'
        node=self.helper('import os, signal, subprocess, time\n'
            'signal.signal(signal.SIGTERM,signal.SIG_IGN)\n'
            'p=subprocess.Popen(["/usr/bin/python3","-c","import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(60)"])\n'
            'open('+repr(str(pidfile))+',"w").write(str(p.pid))\ntime.sleep(60)\n')
        with self.assertRaises(self.module.TerminalStateError): self.state(node,seconds=.5)
        pid=int(pidfile.read_text())
        ended=False
        for _ in range(40):
            status=Path(f'/proc/{pid}/stat')
            if not status.exists() or status.read_text().split()[2]=='Z': ended=True; break
            time.sleep(.025)
        self.assertTrue(ended,'owned descendant remains running')

    def test_interrupt_reaps_real_helper(self):
        created=[]; original=self.module.subprocess.Popen
        def launch(*args,**kwargs):
            process=original(*args,**kwargs); created.append(process); return process
        with mock.patch.object(self.module.subprocess,'Popen',side_effect=launch), \
             mock.patch.object(self.module.selectors.DefaultSelector,'select',side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt): self.state()
        self.assertEqual(len(created),1)
        self.assertIsNotNone(created[0].poll())
        self.assertTrue(created[0].stdout.closed)
        self.assertTrue(created[0].stderr.closed)

    def test_cleanup_failure_cannot_be_reported_as_success(self):
        node=self.helper('import signal,json,sys,time\n'
            'signal.signal(signal.SIGTERM,signal.SIG_IGN)\n'
            'r=json.loads(sys.stdin.readline())\n'
            'print(json.dumps({"id":r["id"],"ok":True}),flush=True)\n'
            'time.sleep(60)\n')
        created=[]; original=self.module.subprocess.Popen
        def launch(*args,**kwargs):
            process=original(*args,**kwargs); created.append(process); return process
        with mock.patch.object(self.module.subprocess,'Popen',side_effect=launch): state=self.state(node)
        try:
            with mock.patch.object(self.module.os,'killpg',side_effect=PermissionError):
                with self.assertRaises(self.module.TerminalStateError) as error: state.close()
            self.assertEqual(error.exception.reason,'TERMINAL_CLEANUP_FAILED')
        finally:
            os.killpg(created[0].pid,signal.SIGKILL)
            created[0].wait(timeout=2)


if __name__=='__main__': unittest.main()
