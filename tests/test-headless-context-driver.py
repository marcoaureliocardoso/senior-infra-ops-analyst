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
import terminal_input_challenge as input_challenge
import headless_context_driver as selected_controller
from dataclasses import replace


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

    def run_pinned_probe(self,mode='success',fault=False):
        self.assertIn('input_probe_scope',inspect.signature(self.driver.drive).parameters,
            'offline selected-scope interface missing')
        seen=self.root/'probe-input'; fake=self.root/'probe-ui.py'
        menu_ready=self.root/'menu-ready'; menu_seen=self.root/'menu-seen'; menu_erased=self.root/'menu-erased'
        fake.write_text('import os,time,tty\nfrom pathlib import Path\n'
            'tty.setraw(0)\n'
            'os.write(1,"\\x1b[?1049h\\x1b[38;1H❯\\u00a0".encode())\n'
            'def read(n):\n'
            ' data=bytearray()\n'
            ' while len(data)<n:\n'
            '  value=os.read(0,1)\n'
            '  if not value: raise SystemExit(1)\n'
            '  with Path('+repr(str(seen))+').open("ab") as stream: stream.write(value)\n'
            '  data.extend(value)\n'
            ' return bytes(data)\n'
            'if read(9)!=b"/context\\r": raise SystemExit(1)\n'
            + ('os.write(1,b"\\x1b[1;1HYes, I trust this folder\\x1b[38;3H")\ntime.sleep(.2)\n' if mode=='pre-menu' else '') +
            'os.write(1,b"\\x1b[1;1H\\x1b[2KContext Usage\\r\\nFree space: 81%\\r\\nAutocompact buffer: 3%\\x1b[38;3H")\n'
            + ('os.write(1,b\'Try "fix tests"\\x1b[38;3H\')\n' if mode=='suggestion' else '') +
            ('os.write(1,"\\x1b[6;1H❯ /context\\x1b[38;3H".encode())\n' if mode=='unsupported-control' else '') +
            'marker=read(16)\n'
            'os.write(1,b"\\x1b[38;3H"+marker)\n'
            + ('os.write(1,b"\\x1b[1;1HDo you want to use this API key?\\x1b[38;19H")\n' if mode=='auth' else '') +
            'if read(1)!=b"\\x15": raise SystemExit(1)\n'
            + ('os.write(1,"\\x1b[38;1H\\x1b[2K❯\\u00a0".encode())\n' if mode!='uncleared' else '') +
            ('os.write(1,b"\\x1b[1;1HYes, I trust this folder\\x1b[38;3H")\n' if mode=='postclear-menu' else '') +
            ('if read(2)!=b"/e": raise SystemExit(1)\n'
                'os.write(1,b"\\x1b[1;1HYes, I trust this folder\\x1b[38;3H")\n'
                'Path('+repr(str(menu_ready))+').touch()\n'
                'while not Path('+repr(str(menu_seen))+').exists(): time.sleep(.005)\n'
                'os.write(1,b"\\x1b[1;1H\\x1b[2KContext Usage\\x1b[38;3H")\n'
                'Path('+repr(str(menu_erased))+').touch()\n'
                'if read(4)!=b"xit\\r": raise SystemExit(1)\n' if mode=='partial-exit-menu' else
                'if read(6)!=b"/exit\\r": raise SystemExit(1)\n'),encoding='utf-8')
        state=TerminalState(Path(os.environ['P004B_TERMINAL_NODE']),Path(os.environ['P004B_TERMINAL_MODULE_ROOT']),time.monotonic()+12)
        with mock.patch.object(input_challenge,'audit_offline_namespace',return_value={
                'networkIsolated':True,'operatorStateHidden':True,'capabilitiesDropped':True}):
            scope=input_challenge.create_offline_probe_issuer().issue_scope(state,object())
        diagnostics=TerminalDiagnostics()
        original=os.write; failed_fd=None; original_snapshot=state.snapshot
        def observed_snapshot():
            value=original_snapshot()
            if mode=='partial-exit-menu' and 'Yes, I trust this folder' in '\n'.join(
                    ''.join(cell.text for cell in row) for row in value.rows):
                menu_seen.touch()
                until=time.monotonic()+1
                while not menu_erased.exists() and time.monotonic()<until: time.sleep(.005)
            return value
        def partial_writer(fd,payload):
            nonlocal failed_fd
            if mode=='partial-exit-menu' and os.isatty(fd) and bytes(payload)==b'/exit\r':
                count=original(fd,payload[:2]); until=time.monotonic()+1
                while not menu_ready.exists() and time.monotonic()<until: time.sleep(.005)
                return count
            if fault and os.isatty(fd) and len(payload)==16 and all(char in b'0123456789abcdef' for char in payload):
                failed_fd=fd; return original(fd,payload[:8])
            if fd==failed_fd: raise OSError('synthetic write failed')
            return original(fd,payload)
        with mock.patch.dict(os.environ,{'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1'},clear=True),\
                mock.patch.object(state,'snapshot',side_effect=observed_snapshot),\
                mock.patch.object(os,'write',side_effect=partial_writer if fault or mode=='partial-exit-menu' else original):
            result=self.driver.drive([sys.executable,str(fake)],self.root/'capture',6,self.root/'events',
                dialogue='context',terminal_state=state,terminal_diagnostics=diagnostics,input_probe_scope=scope)
        data=seen.read_bytes() if seen.exists() else b''
        self.assertEqual(result,0 if mode=='success' and not fault else 2)
        self.assertEqual(data[:9],b'/context\r')
        self.assertNotIn(b'\x1b',data)
        report=diagnostics.report()
        self.assertFalse(report['rejected']); self.assertFalse(report['truncated'])
        self.assertTrue(state.helper_reaped)
        if mode in ('suggestion','pre-menu','unsupported-control'): self.assertEqual(data,b'/context\r')
        elif fault:
            self.assertLess(len(data),25); self.assertNotIn(b'\x15',data); self.assertNotIn(b'/exit',data[9:])
        else:
            self.assertRegex(data[9:25],rb'^[0-9a-f]{16}$')
            self.assertNotIn(data[9:25].decode(),json.dumps(report))
            if mode=='success': self.assertEqual(data[25:],b'\x15/exit\r')
            elif mode=='auth': self.assertEqual(data[25:],b'')
            elif mode=='uncleared': self.assertEqual(data[25:],b'\x15')
            elif mode=='postclear-menu': self.assertEqual(data[25:],b'\x15')
            elif mode=='partial-exit-menu': self.assertEqual(data[25:],b'\x15/e')
        return report

    def test_pinned_input_probe_echo_clear_and_natural_exit(self): self.run_pinned_probe()
    def test_probe_does_not_overwrite_visible_suggestion(self): self.run_pinned_probe('suggestion')

    def test_ineligibility_subcode_reaches_diagnostics_without_changing_proof_events(self):
        report=self.run_pinned_probe('suggestion')
        failed=[row for row in report['records'] if row['point']=='failure']
        self.assertEqual(len(failed),1)
        self.assertEqual(failed[0]['reasonCode'],'INPUT_PROBE_INELIGIBLE')
        self.assertEqual(failed[0].get('inputEligibility'),'NONEMPTY_INPUT')
        self.assertNotIn('fix tests',json.dumps(report))
        events=[json.loads(line) for line in (self.root/'events').read_text().splitlines()]
        self.assertEqual(events[-1],{'kind':'pty-driver','stage':'context_inspected','outcome':'failed'})
        self.assertTrue(all(set(row)<={'kind','stage','outcome','percent'} for row in events))

    def test_unsupported_control_shape_outside_cursor_is_diagnostic_only_and_never_typed(self):
        report=self.run_pinned_probe('unsupported-control')
        failed=[row for row in report['records'] if row['point']=='failure']
        self.assertEqual(len(failed),1)
        self.assertEqual(failed[0]['reasonCode'],'INPUT_PROBE_INELIGIBLE')
        self.assertEqual(failed[0].get('inputEligibility'),'UNSUPPORTED_ROW')
        self.assertEqual((failed[0].get('inputRowRelation'),failed[0].get('inputRowCause')),
            ('OTHER_CAPTURED_ROW','CONTROL_COMMAND_SHAPE'))
        self.assertNotIn('❯ /context',json.dumps(report))
        self.assertFalse(any(row['point']=='input_probe_started' for row in report['records']))
        events=[json.loads(line) for line in (self.root/'events').read_text().splitlines()]
        self.assertEqual(events[-1],{'kind':'pty-driver','stage':'context_inspected','outcome':'failed'})
        self.assertTrue(all(set(row)<={'kind','stage','outcome','percent'} for row in events))
    def test_auth_after_echo_prevents_clear_and_exit(self): self.run_pinned_probe('auth')
    def test_missing_clear_ack_prevents_exit(self): self.run_pinned_probe('uncleared')
    def test_partial_marker_write_failure_has_no_second_edit(self): self.run_pinned_probe(fault=True)
    def test_menu_after_clear_prevents_exit(self): self.run_pinned_probe('postclear-menu')
    def test_observed_menu_before_numeric_never_types_marker(self): self.run_pinned_probe('pre-menu')
    def test_observed_menu_during_partial_exit_never_sends_remaining_bytes(self):
        self.run_pinned_probe('partial-exit-menu')

    def test_serialized_scope_rejects_before_native_startup(self):
        self.assertIn('input_probe_scope',inspect.signature(self.driver.drive).parameters,
            'offline selected-scope interface missing')
        marker=self.root/'effect'; fake=self.root/'fake.py'
        fake.write_text('from pathlib import Path\nPath('+repr(str(marker))+').write_text("effect")\n')
        state=TerminalState(Path(os.environ['P004B_TERMINAL_NODE']),Path(os.environ['P004B_TERMINAL_MODULE_ROOT']),time.monotonic()+5)
        self.assertEqual(self.driver.drive([sys.executable,str(fake)],self.root/'capture',4,
            dialogue='context',terminal_state=state,input_probe_scope={'offline':True}),2)
        self.assertFalse(marker.exists()); self.assertTrue(state.helper_reaped)

    def test_exit_dispatch_rechecks_exact_owned_prefix_and_menu_state(self):
        self.assertTrue(callable(getattr(selected_controller,'exit_input_owned',None)),
            'concrete exit-shape fence missing')
        from terminal_input_policy import TerminalInputPolicy
        state=TerminalState(Path(os.environ['P004B_TERMINAL_NODE']),Path(os.environ['P004B_TERMINAL_MODULE_ROOT']),time.monotonic()+5)
        try:
            state.feed('❯\u00a0'.encode()); empty=state.snapshot()
            policy=TerminalInputPolicy(); anchor=policy.empty_input_anchor(empty)
            self.assertTrue(selected_controller.exit_input_owned(policy,empty,anchor,empty.rows[0],0))
            state.feed(b'/ex'); partial=state.snapshot()
            self.assertTrue(selected_controller.exit_input_owned(policy,partial,anchor,empty.rows[0],3))
            self.assertFalse(selected_controller.exit_input_owned(policy,partial,anchor,empty.rows[0],2))
            state.feed(b'\x1b[2;1HYes, I trust this folder\x1b[1;6H')
            self.assertFalse(selected_controller.exit_input_owned(policy,state.snapshot(),anchor,empty.rows[0],3))
        finally: state.close()
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
