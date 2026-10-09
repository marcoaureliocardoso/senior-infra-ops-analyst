"""Selected-path PTY behavior with real terminal state and controlled native UI."""
import importlib.util
import inspect
import json
import os
import signal
import subprocess
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest import mock

from terminal_state_adapter import TerminalState, TerminalStateError
from terminal_structural_diagnostics import TerminalDiagnostics


class HeadlessContextDriverTests(unittest.TestCase):
    def setUp(self):
        spec=importlib.util.spec_from_file_location('selected_driver',Path(__file__).with_name('claude-pty-driver.py'))
        self.driver=importlib.util.module_from_spec(spec); spec.loader.exec_module(self.driver)
        self.assertIn('terminal_state',inspect.signature(self.driver.drive).parameters,'selected state interface missing')
        self.temp=tempfile.TemporaryDirectory(prefix='headless-context-test-')
        self.addCleanup(self.temp.cleanup); self.root=Path(self.temp.name)

    def run_case(self,blocked,cleanup_failure=False,diagnostics=None,exit_stalls=False):
        seen=self.root/'input'; fake=self.root/'native.py'
        fake.write_text('import os,select,time,tty\nfrom pathlib import Path\n'
            'tty.setraw(0)\n'
            'os.write(1,"\\x1b[?1049h\\x1b[38;1H❯\\u00a0".encode())\n'
            + ('time.sleep(.8)\nos.write(1,"\\x1b[1;1HDo you want to use this API key?\\r\\n❯ 1. No".encode())\n' if blocked else '') +
            'def line():\n'
            ' value=bytearray()\n'
            ' while select.select([0],[],[],8)[0]:\n'
            '  value.extend(os.read(0,1))\n'
            '  if value.endswith(b"\\r"): break\n'
            ' with Path('+repr(str(seen))+').open("ab") as stream: stream.write(value)\n'
            ' return bytes(value)\n'
            'if line()!=b"/context\\r": raise SystemExit(1)\n'
            'os.write(1,"\\x1b[2J\\x1b[HContext Usage\\r\\nFree space: 90%\\r\\nAutocompact buffer: 3%\\r\\n❯\\u00a0".encode())\n'
            'if line()!=b"/exit\\r": raise SystemExit(1)\n'
            + ('time.sleep(10)\n' if exit_stalls else ''),encoding='utf-8')
        state=TerminalState(Path(os.environ['P004B_TERMINAL_NODE']),Path(os.environ['P004B_TERMINAL_MODULE_ROOT']),time.monotonic()+10)
        original_close=state.close
        def failed_close():
            original_close()
            raise TerminalStateError('TERMINAL_CLEANUP_FAILED')
        with mock.patch.object(state,'close',side_effect=failed_close if cleanup_failure else original_close):
            result=self.driver.drive([sys.executable,str(fake)],self.root/'capture',6,self.root/'events',
                dialogue='context',terminal_state=state,
                **({'terminal_diagnostics':diagnostics} if diagnostics is not None else {}))
        self.assertEqual(result,2 if blocked or cleanup_failure or exit_stalls else 0)
        data=seen.read_bytes() if seen.exists() else b''
        if blocked: self.assertNotIn(b'/context',data)
        else:
            self.assertEqual(data,b'/context\r/exit\r')
            records=[json.loads(line) for line in (self.root/'events').read_text().splitlines()]
            self.assertIn({'kind':'pty-driver','stage':'context_inspected','outcome':'passed','percent':7},records)
            if cleanup_failure:
                self.assertEqual(records[-1],{'kind':'pty-driver','stage':'terminal_cleanup','outcome':'failed'})
            else:
                self.assertEqual(records[-1]['stage'],'exit')
                self.assertEqual(records[-1]['outcome'],'failed' if exit_stalls else 'passed')
        with self.assertRaises(RuntimeError): state.snapshot()

    def test_current_nbsp_input_context_and_natural_exit(self): self.run_case(False)
    def test_settling_auth_revokes_input_without_slash_command(self): self.run_case(True)
    def test_cleanup_failure_overrides_successful_native_exit(self): self.run_case(False,True)

    def test_separate_diagnostics_preserve_success_and_proof_schema(self):
        self.assertIn('terminal_diagnostics',inspect.signature(self.driver.drive).parameters,
            'selected diagnostic interface missing')
        diagnostics=TerminalDiagnostics(); self.run_case(False,diagnostics=diagnostics)
        report=diagnostics.report()
        self.assertFalse(report['rejected']); self.assertFalse(report['truncated'])
        self.assertIn({'point':'helper_cleanup','reasonCode':'CLEANUP_COMPLETED','leaderReaped':True},report['records'])
        records=[json.loads(line) for line in (self.root/'events').read_text().splitlines()]
        self.assertTrue(all(set(row)<={'kind','stage','outcome','percent'} for row in records))
        self.assertNotIn('❯',json.dumps(report))

    def test_expired_close_and_same_position_readiness_are_distinct_diagnostics(self):
        self.assertIn('terminal_diagnostics',inspect.signature(self.driver.drive).parameters,
            'selected diagnostic interface missing')
        seen=self.root/'input'; fake=self.root/'native.py'
        fake.write_text('import os,time,tty\nfrom pathlib import Path\n'
            'tty.setraw(0)\n'
            'os.write(1,"\\x1b[?1049h\\x1b[38;1H❯\\u00a0".encode())\n'
            'value=bytearray()\n'
            'while not value.endswith(b"\\r"): value.extend(os.read(0,1))\n'
            'Path('+repr(str(seen))+').write_bytes(value)\n'
            'os.write(1,b"\\x1b[1;1HContext Usage\\r\\nFree space: 81%\\r\\nAutocompact buffer: 3%\\x1b[38;3H")\n'
            'value=os.read(0,1)\n'
            'with Path('+repr(str(seen))+').open("ab") as stream: stream.write(value)\n'
            'os.write(1,b"\\x1b[1;1H\\x1b[2K\\x1b[2;1H\\x1b[2K\\x1b[3;1H\\x1b[2K\\x1b[38;3H")\n'
            'time.sleep(10)\n',encoding='utf-8')
        state=TerminalState(Path(os.environ['P004B_TERMINAL_NODE']),Path(os.environ['P004B_TERMINAL_MODULE_ROOT']),time.monotonic()+3.8)
        diagnostics=TerminalDiagnostics()
        result=self.driver.drive([sys.executable,str(fake)],self.root/'capture',4,self.root/'events',
            dialogue='context',terminal_state=state,terminal_diagnostics=diagnostics)
        self.assertEqual(result,2); self.assertEqual(seen.read_bytes(),b'/context\r\x1b')
        report=diagnostics.report(); self.assertFalse(report['truncated']); self.assertFalse(report['rejected'])
        failure=next(row for row in report['records'] if row['point']=='failure')
        self.assertEqual(failure['reasonCode'],'WAIT_DEADLINE')
        self.assertEqual(failure['structure']['readiness'],'FRESHNESS_UNPROVEN')
        self.assertEqual(failure['structure']['cursorY'],37)
        self.assertFalse(failure['structure']['inputFresh'])
        self.assertIn({'point':'helper_cleanup','reasonCode':'TERMINAL_DEADLINE_EXCEEDED','leaderReaped':True},report['records'])
        records=[json.loads(line) for line in (self.root/'events').read_text().splitlines()]
        self.assertIn({'kind':'pty-driver','stage':'context_inspected','outcome':'passed','percent':16},records)
        self.assertEqual(records[-1],{'kind':'pty-driver','stage':'terminal_cleanup','outcome':'failed'})

    def test_reap_observation_failure_cannot_change_operational_result(self):
        diagnostics=TerminalDiagnostics()
        with mock.patch.object(TerminalState,'helper_reaped',new_callable=mock.PropertyMock,
                side_effect=RuntimeError('synthetic private exception')):
            try: self.run_case(False,diagnostics=diagnostics)
            except RuntimeError: self.fail('passive observation failure escaped the diagnostic channel')
        self.assertTrue(diagnostics.report()['rejected'])
        self.assertNotIn('synthetic private exception',json.dumps(diagnostics.report()))

    def test_cleanup_failure_not_promoted_by_reaped_leader(self):
        diagnostics=TerminalDiagnostics(); self.run_case(False,True,diagnostics)
        self.assertIn({'point':'helper_cleanup','reasonCode':'TERMINAL_CLEANUP_FAILED','leaderReaped':True},
            diagnostics.report()['records'])

    def test_exit_wait_timeout_has_closed_operational_reason_without_success(self):
        diagnostics=TerminalDiagnostics(); started=time.monotonic()
        self.run_case(False,diagnostics=diagnostics,exit_stalls=True)
        self.assertLess(time.monotonic()-started,8)
        report=diagnostics.report()
        failure=next(row for row in report['records'] if row['point']=='failure')
        self.assertEqual(failure['reasonCode'],'EXIT_WAIT_DEADLINE')
        self.assertIn({'point':'native_cleanup','reasonCode':'CLEANUP_COMPLETED','leaderReaped':True},report['records'])
        self.assertIn({'point':'helper_cleanup','reasonCode':'CLEANUP_COMPLETED','leaderReaped':True},report['records'])
        records=[json.loads(line) for line in (self.root/'events').read_text().splitlines()]
        self.assertNotIn({'kind':'pty-driver','stage':'exit','outcome':'passed'},records)

    def test_noncontext_selection_never_starts_native(self):
        marker=self.root/'native-effect'; fake=self.root/'native.py'
        fake.write_text('from pathlib import Path\nPath('+repr(str(marker))+').write_text("effect")\nprint("fixture")\n')
        state=TerminalState(Path(os.environ['P004B_TERMINAL_NODE']),Path(os.environ['P004B_TERMINAL_MODULE_ROOT']),time.monotonic()+8)
        self.assertEqual(self.driver.drive([sys.executable,str(fake)],self.root/'capture',4,
            dialogue='resume',terminal_state=state),2)
        self.assertFalse(marker.exists())
        with self.assertRaises(RuntimeError): state.snapshot()

    def test_split_status_after_context_cannot_enable_exit(self):
        seen=self.root/'input'; fake=self.root/'native.py'
        fake.write_text('import os,select,time,tty\nfrom pathlib import Path\n'
            'tty.setraw(0)\n'
            'os.write(1,"\\x1b[?1049h\\x1b[38;1H❯\\u00a0".encode())\n'
            'def line():\n'
            ' value=bytearray()\n'
            ' while select.select([0],[],[],8)[0]:\n'
            '  value.extend(os.read(0,1))\n'
            '  if value.endswith(b"\\r"): break\n'
            ' with Path('+repr(str(seen))+').open("ab") as stream: stream.write(value)\n'
            ' return bytes(value)\n'
            'if line()!=b"/context\\r": raise SystemExit(1)\n'
            'os.write(1,b"\\x1b[1;1HContext Usage\\r\\nFree space: 90%\\r\\nAutocompact buffer: 3%\\x1b[38;3H")\n'
            'if os.read(0,1)!=b"\\x1b": raise SystemExit(1)\n'
            'os.write(1,b"\\x1b[6;1Hnew status\\x1b[6;11H")\ntime.sleep(.3)\n'
            'os.write(1,b"\\x1b[38;3H")\n'
            'if line()!=b"/exit\\r": raise SystemExit(1)\n',encoding='utf-8')
        state=TerminalState(Path(os.environ['P004B_TERMINAL_NODE']),Path(os.environ['P004B_TERMINAL_MODULE_ROOT']),time.monotonic()+8)
        result=self.driver.drive([sys.executable,str(fake)],self.root/'capture',4,
            self.root/'events',dialogue='context',terminal_state=state)
        self.assertEqual(result,2)
        self.assertEqual(seen.read_bytes(),b'/context\r')
        records=[json.loads(line) for line in (self.root/'events').read_text().splitlines()]
        self.assertIn({'kind':'pty-driver','stage':'context_inspected','outcome':'passed','percent':7},records)
        self.assertEqual(records[-1]['outcome'],'failed')
        with self.assertRaises(RuntimeError): state.snapshot()

    def test_unsupported_platform_rejects_before_importing_posix_controller(self):
        state=TerminalState(Path(os.environ['P004B_TERMINAL_NODE']),Path(os.environ['P004B_TERMINAL_MODULE_ROOT']),time.monotonic()+8)
        try:
            with mock.patch.object(self.driver.os,'name','nt'), \
                 mock.patch.dict(sys.modules,{'headless_context_driver':None}):
                try:
                    outcome=self.driver.drive([sys.executable],self.root/'capture',4,
                        dialogue='context',terminal_state=state)
                except ImportError:
                    outcome='POSIX_IMPORT_ATTEMPTED'
                self.assertEqual(outcome,2)
        finally: state.close()

    def test_interrupt_terminates_native_group_and_helper(self):
        pidfile=self.root/'descendant.pid'; fake=self.root/'native.py'
        fake.write_text('import subprocess,sys,time,os\n'
            'from pathlib import Path\n'
            'p=subprocess.Popen([sys.executable,"-c","import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(60)"])\n'
            'Path('+repr(str(pidfile))+').write_text(str(p.pid))\n'
            'os.write(1,"❯\\u00a0".encode())\ntime.sleep(60)\n',encoding='utf-8')
        state=TerminalState(Path(os.environ['P004B_TERMINAL_NODE']),Path(os.environ['P004B_TERMINAL_MODULE_ROOT']),time.monotonic()+8)
        created=[]; original=self.driver.subprocess.Popen
        def launch(*args,**kwargs):
            process=original(*args,**kwargs); created.append(process); return process
        try:
            with mock.patch.object(state,'feed',side_effect=KeyboardInterrupt), \
                 mock.patch.object(self.driver.subprocess,'Popen',side_effect=launch):
                with self.assertRaises(KeyboardInterrupt):
                    self.driver.drive([sys.executable,str(fake)],self.root/'capture',4,
                        dialogue='context',terminal_state=state)
            pid=int(pidfile.read_text()); stopped=False
            for _ in range(40):
                target=Path(f'/proc/{pid}/stat')
                if not target.exists() or target.read_text().split()[2]=='Z': stopped=True; break
                time.sleep(.025)
            self.assertTrue(stopped)
            with self.assertRaises(RuntimeError): state.snapshot()
        finally:
            for process in created:
                try: os.killpg(process.pid,signal.SIGKILL)
                except ProcessLookupError: pass
                process.wait(timeout=2)
            state.close()


if __name__=='__main__': unittest.main()
