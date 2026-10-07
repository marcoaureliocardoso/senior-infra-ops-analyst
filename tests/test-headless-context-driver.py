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


class HeadlessContextDriverTests(unittest.TestCase):
    def setUp(self):
        spec=importlib.util.spec_from_file_location('selected_driver',Path(__file__).with_name('claude-pty-driver.py'))
        self.driver=importlib.util.module_from_spec(spec); spec.loader.exec_module(self.driver)
        self.assertIn('terminal_state',inspect.signature(self.driver.drive).parameters,'selected state interface missing')
        self.temp=tempfile.TemporaryDirectory(prefix='headless-context-test-')
        self.addCleanup(self.temp.cleanup); self.root=Path(self.temp.name)

    def run_case(self,blocked,cleanup_failure=False):
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
            'if line()!=b"/exit\\r": raise SystemExit(1)\n',encoding='utf-8')
        state=TerminalState(Path(os.environ['P004B_TERMINAL_NODE']),Path(os.environ['P004B_TERMINAL_MODULE_ROOT']),time.monotonic()+10)
        original_close=state.close
        def failed_close():
            original_close()
            raise TerminalStateError('TERMINAL_CLEANUP_FAILED')
        with mock.patch.object(state,'close',side_effect=failed_close if cleanup_failure else original_close):
            result=self.driver.drive([sys.executable,str(fake)],self.root/'capture',6,self.root/'events',
                dialogue='context',terminal_state=state)
        self.assertEqual(result,2 if blocked or cleanup_failure else 0)
        data=seen.read_bytes() if seen.exists() else b''
        if blocked: self.assertNotIn(b'/context',data)
        else:
            self.assertEqual(data,b'/context\r/exit\r')
            records=[json.loads(line) for line in (self.root/'events').read_text().splitlines()]
            self.assertIn({'kind':'pty-driver','stage':'context_inspected','outcome':'passed','percent':7},records)
            if cleanup_failure:
                self.assertEqual(records[-1],{'kind':'pty-driver','stage':'terminal_cleanup','outcome':'failed'})
            else:
                self.assertEqual(records[-1]['stage'],'exit'); self.assertEqual(records[-1]['outcome'],'passed')
        with self.assertRaises(RuntimeError): state.snapshot()

    def test_current_nbsp_input_context_and_natural_exit(self): self.run_case(False)
    def test_settling_auth_revokes_input_without_slash_command(self): self.run_case(True)
    def test_cleanup_failure_overrides_successful_native_exit(self): self.run_case(False,True)

    def test_noncontext_selection_never_starts_native(self):
        marker=self.root/'native-effect'; fake=self.root/'native.py'
        fake.write_text('from pathlib import Path\nPath('+repr(str(marker))+').write_text("effect")\nprint("fixture")\n')
        state=TerminalState(Path(os.environ['P004B_TERMINAL_NODE']),Path(os.environ['P004B_TERMINAL_MODULE_ROOT']),time.monotonic()+8)
        self.assertEqual(self.driver.drive([sys.executable,str(fake)],self.root/'capture',4,
            dialogue='resume',terminal_state=state),2)
        self.assertFalse(marker.exists())
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
