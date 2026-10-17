"""Selected-path PTY behavior with real terminal state and controlled native UI."""
import importlib.util
import inspect
import errno
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
import terminal_context_debug as context_debug_module
from dataclasses import replace
from types import SimpleNamespace
from terminal_context_diagnostics import ContextFailureJournal
from terminal_cancellation import TerminalCancelled


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

    def run_pinned_probe(self,mode='success',fault=False,debug=False,collector_error=None,projection_fault=None,edit_debug=False):
        self.assertIn('input_probe_scope',inspect.signature(self.driver.drive).parameters,
            'offline selected-scope interface missing')
        seen=self.root/'probe-input'; fake=self.root/'probe-ui.py'
        menu_ready=self.root/'menu-ready'; menu_seen=self.root/'menu-seen'; menu_erased=self.root/'menu-erased'
        submit_ready=self.root/'submit-ready'; menu_request=self.root/'menu-request'
        loss_ready=self.root/'loss-ready'; loss_observed=self.root/'loss-observed'
        exit_menu_ready=self.root/'exit-menu-ready'
        completion=mode.startswith('completion-')
        menu_row=40 if mode=='completion-below' else 35
        completion_text='❯ /context  Synthetic completion A'
        if mode in ('completion-pre-enter-grid','completion-post-enter-new-grid'):
            completion_text='❯ /context  Context Usage Free space: 99%'
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
            + ('os.write(1,"\\x1b[6;1H❯ /resume\\x1b[38;3H".encode())\n' if mode=='baseline-history' else '') +
            'command=bytearray()\n'
            'for _ in range(8):\n'
            ' command.extend(read(1))\n'
            + ('' if mode=='missing-command-echo' else
                ' os.write(1,b"\\x1b[38;3H"+command)\n') +
            'if command!=b"/context": raise SystemExit(1)\n'
            + ('' if mode=='missing-command-echo' else
                'os.write(1,b"\\x1b[38;3H/contextX")\n' if mode=='wrong-command-echo' else
                'os.write(1,b"\\x1b[38;3H/context")\n') +
            ('Path('+repr(str(submit_ready))+').touch()\n'
                'while not Path('+repr(str(menu_request))+').exists(): time.sleep(.005)\n'
                'os.write(1,b"\\x1b[1;1HYes, I trust this folder\\x1b[38;11H")\n'
                'Path('+repr(str(menu_ready))+').touch()\n'
                'while not Path('+repr(str(menu_seen))+').exists(): time.sleep(.005)\n'
                'os.write(1,b"\\x1b[1;1H\\x1b[2K\\x1b[38;11H")\n'
                'Path('+repr(str(menu_erased))+').touch()\n' if mode=='late-writable-menu' else '') +
            ('Path('+repr(str(submit_ready))+').touch()\n'
                'while not Path('+repr(str(menu_request))+').exists(): time.sleep(.005)\n'
                'os.write(1,b"\\x1b[1;1HContext Usage\\r\\nFree space: 81%\\r\\nAutocompact buffer: 3%\\x1b[38;11H")\n'
                'Path('+repr(str(menu_ready))+').touch()\n' if mode=='pre-enter-numeric-grid' else '') +
            ('os.write(1,b"\\x1b[1;1HPress Esc to close\\x1b[38;11H")\n' if mode=='menu-before-submit' else '') +
            ('os.write(1,b"\\x1b[1;1HDo you want to use this API key?\\x1b[38;11H")\n' if mode=='auth-before-submit' else '') +
            ('os.write(1,"\\x1b[12;1H❯ autocomplete\\x1b[38;11H".encode())\n' if mode=='autocomplete-marker' else '') +
            ('os.write(1,"\\x1b[38;1H❯ /context".encode())\n' if mode in ('prefix-padding-repaint','diagnostic-loss') else '') +
            ('Path('+repr(str(submit_ready))+').touch()\n'
                'while not Path('+repr(str(menu_request))+').exists(): time.sleep(.005)\n'
                'os.write(1,'+repr(('\x1b['+('40' if mode=='normalized-suggestion-below' else '35')+';1H'
                    + ('' if mode=='normalized-plain-description' else '❯ ')
                    + '/context Synthetic context usage detail\x1b[38;11H').encode())+')\n'
                'Path('+repr(str(menu_ready))+').touch()\n' if mode.startswith('normalized-') else '') +
            ('while not Path('+repr(str(menu_request))+').exists(): time.sleep(.005)\n'
                'os.write(1,'+repr(('\x1b['+('40' if mode=='edit-suggestion-below' else '35')+';1H'
                    + ('' if mode=='edit-plain-description' else '❯ ')
                    + '/context Synthetic context usage detail\x1b[38;11H').encode())+')\n'
                'Path('+repr(str(menu_ready))+').touch()\n' if mode.startswith('edit-') else '') +
            ('while not Path('+repr(str(menu_request))+').exists(): time.sleep(.005)\n'
                + ('os.write(1,b"\\x1b[1;1HContext Usage\\r\\nFree space: 81%\\r\\nAutocompact buffer: 3%")\n'
                    if mode in ('completion-pre-enter-grid','completion-post-enter-new-grid') else '')
                + 'os.write(1,'+repr(('\x1b['+str(menu_row)+';1H'+completion_text+'\x1b[38;11H').encode())+')\n'
                'Path('+repr(str(menu_ready))+').touch()\n' if completion else '') +
            ('while not Path('+repr(str(menu_seen))+').exists(): time.sleep(.005)\n'
                'os.write(1,b"\\x1b[35;1H\\x1b[2K\\x1b[38;11H")\n'
                'Path('+repr(str(loss_ready))+').touch()\n'
                'while not Path('+repr(str(loss_observed))+').exists(): time.sleep(.005)\n'
                'os.write(1,'+repr(('\x1b[35;1H'+completion_text+'\x1b[38;11H').encode())+')\n'
                'Path('+repr(str(menu_erased))+').touch()\n' if mode=='completion-loss-restore' else '') +
            'if read(1)!=b"\\r": raise SystemExit(1)\n'
            + ('os.write(1,"\\x1b[2J\\x1b[38;1H❯\\u00a0".encode())\n'
                'read(1)\nraise SystemExit(1)\n' if mode=='completion-accept-only' else '')
            + ('os.write(1,b"\\x1b[1;1HYes, I trust this folder\\x1b[38;3H")\ntime.sleep(.2)\n' if mode=='pre-menu' else '') +
            'os.write(1,'+repr(('\x1b[2J\x1b[HContext Usage\r\nFree space: '+
                ('80' if mode=='completion-post-enter-new-grid' else '81')+
                '%\r\nAutocompact buffer: 3%\x1b[6;1H❯ /context\x1b[38;1H❯\u00a0').encode())+')\n'
            + ('os.write(1,'+repr(('\x1b[35;1H'+completion_text+'\x1b[38;3H').encode())+')\n'
                if mode=='completion-persists-after-enter' else '')
            + ('os.write(1,b\'Try "fix tests"\\x1b[38;3H\')\n' if mode=='suggestion' else '') +
            ('os.write(1,"\\x1b[12;1H❯ /exit\\x1b[38;3H".encode())\n' if mode=='unsupported-control' else '') +
            ('os.write(1,"\\x1b[12;1H❯ /context\\x1b[38;3H".encode())\n' if mode=='duplicate-history' else '') +
            ('os.write(1,"\\x1b[12;1H❯ unknown\\x1b[38;3H".encode())\n' if mode=='different-rejected-row-debug' else '') +
            'marker=read(16)\n'
            'os.write(1,b"\\x1b[38;3H"+marker)\n'
            + ('os.write(1,"\\x1b[6;1H\\x1b[2K❯ /exit\\x1b[38;19H".encode())\n' if mode=='history-mutated-during-nonce' else '') +
            ('os.write(1,b"\\x1b[12;3H"+marker+b"\\x1b[38;19H")\n' if mode=='nonce-in-history' else '') +
            ('os.write(1,"\\x1b[38;1H\\x1b[2K❯\\u00a0\\x1b[37;1H❯\\u00a0".encode()+marker)\n' if mode=='wrong-echo-row' else '') +
            ('os.write(1,b"\\x1b[1;1HPress Esc to close\\x1b[38;19H")\n' if mode=='menu-before-clear' else '') +
            ('os.write(1,b"\\x1b[1;1HDo you want to use this API key?\\x1b[38;19H")\n' if mode=='auth' else '') +
            'if read(1)!=b"\\x15": raise SystemExit(1)\n'
            + ('os.write(1,"\\x1b[38;1H\\x1b[2K❯\\u00a0".encode())\n' if mode!='uncleared' else '') +
            ('os.write(1,b"\\x1b[1;1HYes, I trust this folder\\x1b[38;3H")\n' if mode=='postclear-menu' else '') +
            ('if read(2)!=b"/e": raise SystemExit(1)\n'
                'os.write(1,"\\x1b[35;1H❯ /exit  Synthetic exit fixture\\x1b[38;3H".encode())\n'
                'Path('+repr(str(exit_menu_ready))+').touch()\n'
                'if read(4)!=b"xit\\r": raise SystemExit(1)\n' if mode=='completion-exit-menu' else
             'if read(2)!=b"/e": raise SystemExit(1)\n'
                + ('os.write(1,b"\\x1b[6;1H\\x1b[2K\\x1b[38;3H")\n' if mode=='partial-exit-history-restore' else
                    'os.write(1,"\\x1b[12;1H❯ unknown\\x1b[38;3H".encode())\n' if mode=='partial-exit-unowned-row-restore' else
                    'os.write(1,"\\x1b[38;1H❯ unknown".encode())\n') +
                'Path('+repr(str(menu_ready))+').touch()\n'
                'while not Path('+repr(str(menu_seen))+').exists(): time.sleep(.005)\n'
                + ('os.write(1,"\\x1b[6;1H❯ /context\\x1b[38;3H".encode())\n' if mode=='partial-exit-history-restore' else
                    'os.write(1,b"\\x1b[12;1H\\x1b[2K\\x1b[38;3H")\n' if mode=='partial-exit-unowned-row-restore' else
                    'os.write(1,"\\x1b[38;1H\\x1b[2K❯\\u00a0".encode())\n') +
                'Path('+repr(str(menu_erased))+').touch()\n'
                'if read(4)!=b"xit\\r": raise SystemExit(1)\n' if mode in
                    ('partial-exit-history-restore','partial-exit-unowned-row-restore','partial-exit-input-restore') else
              'if read(2)!=b"/e": raise SystemExit(1)\n'
                'os.write(1,b"\\x1b[1;1HYes, I trust this folder\\x1b[38;3H")\n'
                'Path('+repr(str(menu_ready))+').touch()\n'
                'while not Path('+repr(str(menu_seen))+').exists(): time.sleep(.005)\n'
                'os.write(1,b"\\x1b[1;1H\\x1b[2KContext Usage\\x1b[38;3H")\n'
                'Path('+repr(str(menu_erased))+').touch()\n'
                'if read(4)!=b"xit\\r": raise SystemExit(1)\n' if mode=='partial-exit-menu' else
                'if read(6)!=b"/exit\\r": raise SystemExit(1)\n'),encoding='utf-8')
        state=TerminalState(Path(os.environ['P004B_TERMINAL_NODE']),Path(os.environ['P004B_TERMINAL_MODULE_ROOT']),time.monotonic()+12)
        self.addCleanup(state.close)
        with mock.patch.object(input_challenge,'audit_offline_namespace',return_value={
                'networkIsolated':True,'operatorStateHidden':True,'capabilitiesDropped':True}):
            scope=input_challenge.create_offline_probe_issuer().issue_scope(state,object())
        debug_capture=None
        if debug:
            self.assertIn('context_debug',inspect.signature(self.driver.drive).parameters,'sealed debug interface missing')
            with mock.patch.object(context_debug_module,'audit_offline_namespace',return_value={
                    'networkIsolated':True,'operatorStateHidden':True,'capabilitiesDropped':True}):
                debug_capture=context_debug_module.create_context_debug(scope,state,self.root)
        edit_capture=None
        if edit_debug:
            self.assertIn('context_edit_debug',inspect.signature(self.driver.drive).parameters,
                'explicit edit diagnostic interface missing')
            with mock.patch.object(context_debug_module,'audit_offline_namespace',return_value={
                    'networkIsolated':True,'operatorStateHidden':True,'capabilitiesDropped':True}):
                edit_capture=context_debug_module.create_context_edit_debug(scope,state,self.root)
            self.edit_debug_capture=edit_capture
        diagnostics=TerminalDiagnostics()
        original=os.write; failed_fd=None; original_snapshot=state.snapshot
        command_accepted=False; enter_accepted=False; blocked_once=False; fault_seen=False; context_wait_fault=False
        original_launch=selected_controller.subprocess.Popen
        original_cancel=state.check_cancelled; original_clock=time.monotonic
        original_freeze=ContextFailureJournal.freeze
        original_projection=ContextFailureJournal.project_fields
        original_collect=TerminalDiagnostics.add; original_open=Path.open
        original_pty=selected_controller.pty.openpty
        original_begin=selected_controller.begin_context_command; original_probe=selected_controller.NonceInputChallenge
        captures=[]; terminal_fds=[]; children=[]; commands=[]; probes=[]
        def opened(path,*args,**kwargs):
            stream=original_open(path,*args,**kwargs)
            if path==self.root/'capture': captures.append(stream)
            return stream
        def opened_pty():
            pair=original_pty(); terminal_fds.extend(pair); return pair
        def began(*args,**kwargs):
            value=original_begin(*args,**kwargs); commands.append(value); return value
        def probed(*args,**kwargs):
            value=original_probe(*args,**kwargs); probes.append(value); return value
        def collected(collector,point,reason,**fields):
            if collector_error is not None and point in ('failure','native_cleanup','helper_cleanup'):
                raise collector_error('synthetic collector loss')
            return original_collect(collector,point,reason,**fields)
        def native_launch(*args,**kwargs):
            child=original_launch(*args,**kwargs); original_poll=child.poll
            children.append(child)
            def observed_poll():
                nonlocal fault_seen
                trigger=(mode=='post-command-write-failure' and command_accepted
                    or mode=='post-enter-live-loss' and enter_accepted)
                if trigger and not fault_seen: fault_seen=True; return 0
                return original_poll()
            child.poll=observed_poll
            return child
        def checked_cancel():
            nonlocal fault_seen
            original_cancel()
            if mode=='cancel-before-enter' and context_wait_fault and not fault_seen:
                fault_seen=True; raise TerminalCancelled()
        def checked_clock():
            return original_clock()+(20 if mode=='deadline-before-enter' and context_wait_fault else 0)
        def checked_freeze(journal,error,check,**kwargs):
            if mode=='diagnostic-loss': raise RuntimeError('synthetic observer loss')
            original_freeze(journal,error,check,**kwargs)
        def projected(journal,error,**bindings):
            if projection_fault=='raise': raise RuntimeError('synthetic projection loss')
            if projection_fault=='missing': return None
            if projection_fault=='malformed': return {'unexpected':'synthetic'}
            if projection_fault=='malformed-fields': return {'context_command_failure':{}}
            return original_projection(journal,error,**bindings)
        def observed_snapshot():
            value=original_snapshot()
            if mode=='completion-loss-restore' and loss_ready.exists() and not loss_observed.exists() and not any(cell.text=='❯' for cell in value.rows[34]):
                loss_observed.touch(); until=time.monotonic()+1
                while not menu_erased.exists() and time.monotonic()<until: time.sleep(.005)
            if mode in ('partial-exit-menu','late-writable-menu') and 'Yes, I trust this folder' in '\n'.join(
                    ''.join(cell.text for cell in row) for row in value.rows):
                menu_seen.touch()
                until=time.monotonic()+1
                while not menu_erased.exists() and time.monotonic()<until: time.sleep(.005)
            changed=(mode=='partial-exit-history-restore' and '/context' not in ''.join(cell.text for cell in value.rows[5])
                or mode=='partial-exit-unowned-row-restore' and 'unknown' in ''.join(cell.text for cell in value.rows[11])
                or mode=='partial-exit-input-restore' and 'unknown' in ''.join(cell.text for cell in value.rows[37]))
            if changed and menu_ready.exists() and not menu_seen.exists():
                menu_seen.touch(); until=time.monotonic()+1
                while not menu_erased.exists() and time.monotonic()<until: time.sleep(.005)
            return value
        def partial_writer(fd,payload):
            nonlocal failed_fd,command_accepted,enter_accepted,blocked_once
            if os.isatty(fd) and bytes(payload)==b'/context':
                if mode=='blocking-command-write' and not blocked_once:
                    blocked_once=True; raise BlockingIOError()
                if mode=='invalid-command-write-count': return 9
                if mode=='post-command-write-failure':
                    count=original(fd,payload); until=original_clock()+1
                    while (not seen.exists() or len(seen.read_bytes())<8) and original_clock()<until: time.sleep(.005)
                    command_accepted=True; return count
                command_accepted=True
            if os.isatty(fd) and bytes(payload)==b'\r' and mode=='post-enter-live-loss':
                count=original(fd,payload)
                # Ensure the controlled peer consumed the actual Enter before injecting owner loss.
                until=original_clock()+1
                while (not seen.exists() or len(seen.read_bytes())<9) and original_clock()<until: time.sleep(.005)
                enter_accepted=True; return count
            if mode in ('partial-command-write','partial-command-fault') and os.isatty(fd) and bytes(payload)==b'/context':
                count=original(fd,payload[:4])
                if mode=='partial-command-fault': failed_fd=fd
                return count
            if (mode.startswith('partial-exit-') or mode=='completion-exit-menu') and os.isatty(fd) and bytes(payload)==b'/exit\r':
                count=original(fd,payload[:2]); until=time.monotonic()+1
                ready=exit_menu_ready if mode=='completion-exit-menu' else menu_ready
                while not ready.exists() and time.monotonic()<until: time.sleep(.005)
                return count
            if fault and os.isatty(fd) and len(payload)==16 and all(char in b'0123456789abcdef' for char in payload):
                failed_fd=fd; return original(fd,payload[:8])
            if fd==failed_fd: raise OSError('synthetic write failed')
            return original(fd,payload)
        original_select=selected_controller.select.select
        original_proof=input_challenge.NonceInputChallenge.ownership_proof
        def proof_after_expiry(value):
            if mode=='expired-before-proof':
                with mock.patch.object(input_challenge,'_now',return_value=state.operation_deadline):
                    return original_proof(value)
            return original_proof(value)
        def writable_select(reads,writes,errors,timeout):
            nonlocal context_wait_fault
            if writes and command_accepted and mode in ('cancel-before-enter','deadline-before-enter'):
                context_wait_fault=True
            if reads and command_accepted and (mode.startswith('edit-') or completion) and not menu_request.exists():
                menu_request.touch(); until=time.monotonic()+1
                while not menu_ready.exists() and time.monotonic()<until: time.sleep(.005)
            if mode=='completion-loss-restore' and writes and menu_ready.exists() and not menu_seen.exists():
                menu_seen.touch(); until=time.monotonic()+1
                while not loss_ready.exists() and time.monotonic()<until: time.sleep(.005)
            if (mode in ('late-writable-menu','pre-enter-numeric-grid') or mode.startswith('normalized-')) and writes and submit_ready.exists() and not menu_request.exists():
                menu_request.touch(); until=time.monotonic()+1
                while not menu_ready.exists() and time.monotonic()<until: time.sleep(.005)
            return original_select(reads,writes,errors,timeout)
        with mock.patch.dict(os.environ,{'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1'},clear=True),\
                mock.patch.object(context_debug_module,'audit_offline_namespace',return_value={
                    'networkIsolated':True,'operatorStateHidden':True,'capabilitiesDropped':True}),\
                mock.patch.object(input_challenge,'audit_offline_namespace',return_value={
                    'networkIsolated':True,'operatorStateHidden':True,'capabilitiesDropped':True}),\
                mock.patch.object(state,'snapshot',side_effect=observed_snapshot),\
                mock.patch.object(selected_controller.select,'select',side_effect=writable_select),\
                mock.patch.object(input_challenge.NonceInputChallenge,'ownership_proof',new=proof_after_expiry),\
                mock.patch.object(selected_controller.subprocess,'Popen',side_effect=native_launch),\
                mock.patch.object(selected_controller,'time',SimpleNamespace(monotonic=checked_clock)),\
                mock.patch.object(state,'check_cancelled',side_effect=checked_cancel),\
                mock.patch.object(ContextFailureJournal,'freeze',new=checked_freeze),\
                mock.patch.object(ContextFailureJournal,'project_fields',new=projected),\
                mock.patch.object(TerminalDiagnostics,'add',new=collected),\
                mock.patch.object(Path,'open',new=opened),\
                mock.patch.object(selected_controller.pty,'openpty',side_effect=opened_pty),\
                mock.patch.object(selected_controller,'begin_context_command',side_effect=began),\
                mock.patch.object(selected_controller,'NonceInputChallenge',side_effect=probed),\
                mock.patch.object(os,'write',side_effect=partial_writer):
            result=self.driver.drive([sys.executable,str(fake)],self.root/'capture',6,self.root/'events',
                dialogue='context',terminal_state=state,terminal_diagnostics=diagnostics,input_probe_scope=scope,
                **({'context_debug':debug_capture} if debug else {}),
                **({'context_edit_debug':edit_capture} if edit_debug else {}))
        data=seen.read_bytes() if seen.exists() else b''
        success=mode in ('success','partial-command-write','blocking-command-write','normalized-plain-description','edit-plain-description',
            'completion-above','completion-below','completion-post-enter-new-grid')
        self.assertEqual(result,0 if success and not fault else 2)
        early=('missing-command-echo','wrong-command-echo','menu-before-submit','auth-before-submit',
            'autocomplete-marker','late-writable-menu','prefix-padding-repaint','diagnostic-loss',
            'post-command-write-failure','cancel-before-enter','deadline-before-enter',
            'normalized-suggestion-above','normalized-suggestion-below','normalized-observer-loss',
            'edit-suggestion-above','edit-suggestion-below','completion-loss-restore')
        if mode in ('baseline-history','invalid-command-write-count'): self.assertEqual(data,b'')
        elif mode=='partial-command-fault': self.assertEqual(data,b'/con')
        elif mode in early: self.assertEqual(data,b'/context')
        else: self.assertEqual(data[:9],b'/context\r')
        self.assertNotIn(b'\x1b',data)
        report=diagnostics.report()
        self.assertEqual(report['rejected'],projection_fault=='malformed-fields'); self.assertFalse(report['truncated'])
        self.assertTrue(state.helper_reaped)
        if collector_error is None:
            self.assertIn({'point':'native_cleanup','reasonCode':'CLEANUP_COMPLETED','leaderReaped':True},report['records'])
            if not success and not report['rejected']: self.assertEqual(sum(row['point']=='failure' for row in report['records']),1)
        else:
            self.assertFalse(any(row['point'] in ('failure','native_cleanup','helper_cleanup') for row in report['records']))
        if collector_error is not None or mode.startswith(('normalized-','edit-','completion-')):
            self.assertTrue(captures); self.assertTrue(all(stream.closed for stream in captures))
            self.assertEqual(len(terminal_fds),2)
            for descriptor in terminal_fds:
                with self.assertRaises(OSError) as caught: os.fstat(descriptor)
                self.assertEqual(caught.exception.errno,errno.EBADF)
            self.assertEqual(len(children),1); self.assertIsNotNone(children[0].poll())
            self.assertEqual(len(commands),1); self.assertEqual(commands[0].phase,'REVOKED')
            if mode not in early+('completion-accept-only','completion-pre-enter-grid','completion-persists-after-enter'):
                self.assertEqual(len(probes),1); self.assertEqual(probes[0].phase,'REVOKED')
            else: self.assertEqual(len(probes),0)
        if mode in ('baseline-history','partial-command-fault','invalid-command-write-count') or mode in early: pass
        elif mode=='post-enter-live-loss': self.assertEqual(data,b'/context\r')
        elif mode in ('suggestion','pre-menu','unsupported-control','duplicate-history','different-rejected-row-debug','pre-enter-numeric-grid',
                'completion-accept-only','completion-pre-enter-grid','completion-persists-after-enter'):
            self.assertEqual(data,b'/context\r')
        elif fault:
            self.assertLess(len(data),25); self.assertNotIn(b'\x15',data); self.assertNotIn(b'/exit',data[9:])
        else:
            self.assertRegex(data[9:25],rb'^[0-9a-f]{16}$')
            self.assertNotIn(data[9:25].decode(),json.dumps(report))
            if success: self.assertEqual(data[25:],b'\x15/exit\r')
            elif mode in ('auth','history-mutated-during-nonce','nonce-in-history','wrong-echo-row','menu-before-clear'): self.assertEqual(data[25:],b'')
            elif mode=='uncleared': self.assertEqual(data[25:],b'\x15')
            elif mode=='postclear-menu': self.assertEqual(data[25:],b'\x15')
            elif mode=='expired-before-proof': self.assertEqual(data[25:],b'\x15')
            elif mode.startswith('partial-exit-'): self.assertEqual(data[25:],b'\x15/e')
            elif mode=='completion-exit-menu': self.assertEqual(data[25:],b'\x15/e')
        if debug: self.debug_capture=debug_capture
        return report

    def test_pinned_input_probe_echo_clear_and_natural_exit(self): self.run_pinned_probe()

    def test_correlated_completion_selected_driver_success(self):
        import shutil
        for mode in ('completion-above','completion-below'):
            self.temp.cleanup(); self.setUp()
            report=self.run_pinned_probe(mode,edit_debug=True)
            self.assertIn('context_numeric',[row['point'] for row in report['records']])
            self.assertNotIn('Synthetic completion',json.dumps(report))
            shutil.rmtree(self.root)
            self.assertEqual(self.edit_debug_capture.pending_report(),{'status':'NO_CAPTURE'})

    def test_correlated_completion_only_accepts_once(self):
        report=self.run_pinned_probe('completion-accept-only')
        self.assertNotIn('context_numeric',[row['point'] for row in report['records']])

    def test_correlated_completion_writable_loss_and_restore(self):
        report=self.run_pinned_probe('completion-loss-restore')
        self.assertTrue((self.root/'loss-observed').exists()); self.assertTrue((self.root/'menu-erased').exists())
        failure=next(row for row in report['records'] if row['point']=='failure')
        self.assertEqual(failure['contextCommandFailure'],{'phase':'SUBMIT_PENDING','check':'NORMALIZED_ELIGIBILITY',
            'commandBytesWritten':8,'enterBytesWritten':0})
        self.assertNotIn('normalizedInputFailure',failure)

    def test_correlated_completion_pre_enter_numeric_not_proof(self):
        for mode in ('completion-pre-enter-grid','completion-post-enter-new-grid'):
            self.temp.cleanup(); self.setUp()
            report=self.run_pinned_probe(mode)
            self.assertEqual('input_probe_started' in [row['point'] for row in report['records']],mode=='completion-post-enter-new-grid')

    def test_correlated_completion_no_post_enter_or_exit_transfer(self):
        for mode in ('completion-persists-after-enter','completion-exit-menu'):
            self.temp.cleanup(); self.setUp(); self.run_pinned_probe(mode)
            if mode=='completion-exit-menu': self.assertTrue((self.root/'exit-menu-ready').exists())
    def run_owned_echo_case(self,mode='success'):
        report=self.run_pinned_probe(mode)
        return ((self.root/'probe-input').read_bytes(),
            [json.loads(line) for line in (self.root/'events').read_text().splitlines()],report)

    def test_owned_context_history_allows_nonce_clear_and_natural_exit(self):
        data,events,diagnostics=self.run_owned_echo_case()
        self.assertEqual(data[:9],b'/context\r')
        self.assertRegex(data[9:25],rb'^[0-9a-f]{16}$')
        self.assertEqual(data[25:],b'\x15/exit\r'); self.assertEqual(events[-1]['outcome'],'passed')
        self.assertFalse(diagnostics['rejected']); self.assertFalse(diagnostics['truncated'])

    def test_command_echo_and_pre_submit_forbidden_states_never_enter(self):
        for mode in ('missing-command-echo','wrong-command-echo','menu-before-submit',
                'auth-before-submit','autocomplete-marker','late-writable-menu'):
            with self.subTest(mode=mode):
                self.run_pinned_probe(mode)
                self.temp.cleanup(); self.setUp()

    def test_unowned_history_predicates_never_type_nonce(self):
        for mode in ('baseline-history','duplicate-history'):
            with self.subTest(mode=mode):
                self.run_pinned_probe(mode)
                self.temp.cleanup(); self.setUp()

    def test_history_and_nonce_location_loss_never_clear(self):
        for mode in ('history-mutated-during-nonce','nonce-in-history','wrong-echo-row'):
            with self.subTest(mode=mode):
                self.run_pinned_probe(mode)
                self.temp.cleanup(); self.setUp()

    def test_partial_command_write_progress_and_failure(self):
        self.run_pinned_probe('partial-command-write')
        self.temp.cleanup(); self.setUp()
        self.run_pinned_probe('partial-command-fault')

    def test_normalized_detail_reaches_report_without_enter(self):
        for mode in ('normalized-suggestion-above','normalized-suggestion-below'):
            self.temp.cleanup(); self.setUp()
            report=self.run_pinned_probe(mode)
            failure=next(row for row in report['records'] if row['point']=='failure')
            self.assertEqual(failure['reasonCode'],'INPUT_PROBE_REVOKED')
            self.assertEqual(failure['contextCommandFailure'],{'phase':'SUBMIT_PENDING','check':'NORMALIZED_ELIGIBILITY',
                'commandBytesWritten':8,'enterBytesWritten':0})
            self.assertEqual(failure['normalizedInputFailure'],{'reason':'UNSUPPORTED_ROW',
                'rowRelation':'OTHER_CAPTURED_ROW','rowCause':'UNRECOGNIZED_SHAPE'})
            self.assertEqual((self.root/'probe-input').read_bytes(),b'/context')
            self.assertNotIn('context_sent',[row['point'] for row in report['records']])
            self.assertNotIn('Visualize',json.dumps(report))
            events=[json.loads(line) for line in (self.root/'events').read_text().splitlines()]
            self.assertTrue(any(row['stage']=='context_inspected' and row['outcome']=='failed' for row in events))

    def test_normalized_plain_description_requires_numeric_context_after_enter(self):
        report=self.run_pinned_probe('normalized-plain-description')
        self.assertFalse(any('normalizedInputFailure' in row for row in report['records']))
        self.assertIn('context_numeric',[row['point'] for row in report['records']])
        self.assertTrue((self.root/'probe-input').read_bytes().startswith(b'/context\r'))

    def test_normalized_projection_loss_keeps_original_cleanup(self):
        for fault in ('raise','missing','malformed','malformed-fields'):
            self.temp.cleanup(); self.setUp()
            report=self.run_pinned_probe('normalized-observer-loss',projection_fault=fault)
            self.assertFalse(any('normalizedInputFailure' in row for row in report['records']))
            self.assertEqual((self.root/'probe-input').read_bytes(),b'/context')
        for error in (RuntimeError,LookupError):
            self.temp.cleanup(); self.setUp()
            self.run_pinned_probe('normalized-suggestion-above',collector_error=error)

    def test_normalized_detail_cannot_cross_dialogue_or_attach_late(self):
        first=self.run_pinned_probe('normalized-suggestion-above')
        self.assertTrue(any('normalizedInputFailure' in row for row in first['records']))
        for mode in ('success','menu-before-clear','partial-exit-input-restore'):
            self.temp.cleanup(); self.setUp()
            report=self.run_pinned_probe(mode)
            self.assertFalse(any('normalizedInputFailure' in row for row in report['records']))

    def test_normalized_debug_retains_early_omission(self):
        report=self.run_pinned_probe('normalized-suggestion-above',debug=True)
        self.assertTrue(any('normalizedInputFailure' in row for row in report['records']))
        self.assertEqual(self.debug_capture._status,'OMITTED_PROVENANCE')
        self.assertNotIn('Visualize',json.dumps(report))

    def test_partial_command_failure_reports_only_accepted_bytes(self):
        report=self.run_pinned_probe('partial-command-fault')
        failure=next(row for row in report['records'] if row['point']=='failure')
        self.assertEqual(failure['contextCommandFailure'],{'phase':'EDIT_PENDING','check':'IO_WRITE',
            'commandBytesWritten':4,'enterBytesWritten':0})

    def test_enter_ack_failure_has_no_completed_submission_checkpoint(self):
        report=self.run_pinned_probe('post-enter-live-loss')
        failure=next(row for row in report['records'] if row['point']=='failure')
        self.assertEqual(failure['contextCommandFailure'],{'phase':'SUBMIT_PENDING','check':'NATIVE_LIFETIME',
            'commandBytesWritten':8,'enterBytesWritten':1})
        self.assertNotIn('context_sent',[row['point'] for row in report['records']])

    def test_edit_capture_single_real_assessment_above_below(self):
        import shutil
        for mode in ('edit-suggestion-above','edit-suggestion-below'):
            report=self.run_pinned_probe(mode,edit_debug=True)
            failure=next(row for row in report['records'] if row['point']=='failure')
            self.assertEqual(failure['contextCommandFailure'],{'phase':'EDIT_PENDING',
                'check':'NORMALIZED_ELIGIBILITY','commandBytesWritten':8,'enterBytesWritten':0})
            self.assertEqual((self.root/'probe-input').read_bytes(),b'/context')
            shutil.rmtree(self.root)
            pending=self.edit_debug_capture.pending_report()
            self.assertEqual(pending,{'status':'PREPARED','excerpt':{'rowRelation':'OTHER_CAPTURED_ROW',
                'text':'❯ /context Synthetic context usage detail'}})
            self.assertNotIn('excerpt',self.edit_debug_capture.pending_report())
            self.root.mkdir(mode=0o700)
        self.run_pinned_probe('edit-plain-description',edit_debug=True)
        shutil.rmtree(self.root)
        self.assertEqual(self.edit_debug_capture.pending_report(),{'status':'NO_CAPTURE'})

    def test_edit_capture_release_and_observer_loss(self):
        import shutil
        for method in ('freeze','project','prepare','finish'):
            target=(__import__('terminal_context_echo').EditRowObserver if method in ('freeze','project') else
                context_debug_module.ContextEditDebugCapture)
            with mock.patch.object(target,method,side_effect=LookupError('synthetic observer loss')):
                report=self.run_pinned_probe('edit-suggestion-above',edit_debug=True,collector_error=RuntimeError)
            self.assertNotIn('context_sent',[row['point'] for row in report['records']])
            shutil.rmtree(self.root)
            self.assertNotIn('excerpt',self.edit_debug_capture.pending_report())
            self.root.mkdir(mode=0o700)

    def test_edit_capture_driver_validation_precedes_launch(self):
        self.assertIn('context_edit_debug',inspect.signature(self.driver.drive).parameters,
            'explicit edit diagnostic interface missing')
        for options in ({'context_edit_debug':{}},{'context_edit_debug':{},'context_debug':{}},
                        {'context_edit_debug':{},'dialogue':'manual'}):
            with mock.patch.object(selected_controller.subprocess,'Popen',side_effect=AssertionError('launched')):
                self.assertEqual(self.driver.drive(['never-launched'],self.root/'capture',2,**options),2)

    def test_post_write_failure_retains_ack_before_validation(self):
        report=self.run_pinned_probe('post-command-write-failure')
        failure=next(row for row in report['records'] if row['point']=='failure')
        self.assertEqual(failure['contextCommandFailure'],{'phase':'EDIT_PENDING','check':'NATIVE_LIFETIME',
            'commandBytesWritten':8,'enterBytesWritten':0})

    def test_blocking_invalid_and_diagnostic_failure_do_not_change_input(self):
        report=self.run_pinned_probe('blocking-command-write')
        self.assertFalse(any('contextCommandFailure' in row for row in report['records']))
        self.temp.cleanup(); self.setUp()
        report=self.run_pinned_probe('invalid-command-write-count')
        failure=next(row for row in report['records'] if row['point']=='failure')
        self.assertEqual(failure['reasonCode'],'INPUT_PROBE_IO_FAILED')
        self.assertNotIn('contextCommandFailure',failure)
        self.temp.cleanup(); self.setUp()
        report=self.run_pinned_probe('diagnostic-loss')
        failure=next(row for row in report['records'] if row['point']=='failure')
        self.assertEqual(failure['reasonCode'],'INPUT_PROBE_REVOKED')
        self.assertNotIn('contextCommandFailure',failure)

    def test_controller_boundary_phase_and_first_failure(self):
        for mode,check in (('auth-before-submit','AUTHENTICATION'),('menu-before-submit','FORBIDDEN_UI'),
                ('cancel-before-enter','CANCELLATION'),('deadline-before-enter','DEADLINE'),
                ('prefix-padding-repaint','PREFIX_CELLS')):
            with self.subTest(mode=mode):
                self.temp.cleanup(); self.setUp()
                report=self.run_pinned_probe(mode)
                failure=next(row for row in report['records'] if row['point']=='failure')
                self.assertEqual(failure['contextCommandFailure']['check'],check)
                self.assertEqual(failure['contextCommandFailure']['commandBytesWritten'],8)
                self.assertEqual(failure['contextCommandFailure']['enterBytesWritten'],0)
        self.temp.cleanup(); self.setUp()
        report=self.run_pinned_probe('menu-before-clear')
        self.assertFalse(any('contextCommandFailure' in row for row in report['records']))

    def test_early_command_debug_keeps_original_omission_contract(self):
        report=self.run_pinned_probe('prefix-padding-repaint',debug=True)
        failure=next(row for row in report['records'] if row['point']=='failure')
        self.assertEqual(failure['contextCommandFailure']['check'],'PREFIX_CELLS')
        self.assertEqual(self.debug_capture._status,'OMITTED_PROVENANCE')

    def test_original_rejection_and_close_survive_collector_loss_before_launch(self):
        class State:
            cancellation=None
            helper_reaped=False
            closed=False
            def snapshot(self): raise input_challenge.InputProofError('INPUT_PROBE_REVOKED')
            def close(self): self.closed=True; self.helper_reaped=True
        state=State()
        with mock.patch.object(TerminalDiagnostics,'add',side_effect=RuntimeError('synthetic collector loss')),\
                mock.patch.object(selected_controller.subprocess,'Popen',side_effect=AssertionError('unexpected process')):
            result=selected_controller.drive_context(['never-launched'],self.root/'capture',2,self.root/'events',
                None,state,writer=lambda *_:self.fail('unexpected write'),diagnostics=TerminalDiagnostics())
        self.assertEqual(result,2); self.assertTrue(state.closed)
        events=[json.loads(line) for line in (self.root/'events').read_text().splitlines()]
        self.assertEqual(events,[{'kind':'pty-driver','stage':'initial_screen','outcome':'failed'}])

    def test_persistent_collector_loss_preserves_owned_rejection_and_cleanup(self):
        for mode in ('prefix-padding-repaint','menu-before-clear'):
            with self.subTest(mode=mode):
                self.temp.cleanup(); self.setUp()
                self.run_pinned_probe(mode,collector_error=RuntimeError)
                events=[json.loads(line) for line in (self.root/'events').read_text().splitlines()]
                self.assertEqual(events[-1],{'kind':'pty-driver','stage':'context_inspected','outcome':'failed'})

    def test_persistent_unclassified_collector_loss_preserves_success_and_cleanup(self):
        self.run_pinned_probe('success',collector_error=LookupError)
        events=[json.loads(line) for line in (self.root/'events').read_text().splitlines()]
        self.assertEqual(events[-1],{'kind':'pty-driver','stage':'exit','outcome':'passed'})

    def test_menu_before_clear_never_clears_or_exits(self): self.run_pinned_probe('menu-before-clear')
    def test_expired_before_proof_never_sends_exit(self):
        report=self.run_pinned_probe('expired-before-proof')
        self.assertEqual(next(row for row in report['records'] if row['point']=='failure')['reasonCode'],'INPUT_PROBE_DEADLINE')

    def test_numeric_grid_arriving_during_enter_writable_wait_cannot_bind_history(self):
        self.run_pinned_probe('pre-enter-numeric-grid')

    def test_consumed_partial_exit_history_loss_cannot_restore_remaining_bytes(self):
        self.run_pinned_probe('partial-exit-history-restore')

    def test_consumed_unowned_row_cannot_restore_remaining_exit_bytes(self):
        self.run_pinned_probe('partial-exit-unowned-row-restore')

    def test_consumed_input_prefix_loss_cannot_restore_remaining_exit_bytes(self):
        self.run_pinned_probe('partial-exit-input-restore')
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

    def test_debug_capture_preserves_rejection_and_exports_only_after_root_disposal(self):
        report=self.run_pinned_probe('unsupported-control',debug=True)
        self.assertTrue((self.root/'context-debug-frame.json').is_file())
        self.assertNotIn('excerpt',self.debug_capture.report())
        self.assertFalse(any(row['point']=='input_probe_started' for row in report['records']))
        events=[json.loads(line) for line in (self.root/'events').read_text().splitlines()]
        self.assertEqual(events[-1],{'kind':'pty-driver','stage':'context_inspected','outcome':'failed'})
        self.temp.cleanup()
        debug=self.debug_capture.report()
        self.assertEqual(debug['status'],'READY')
        self.assertEqual(debug['excerpt']['rows'][0]['text'],'❯ /exit')

    def test_debug_selects_actual_unknown_row_not_owned_command_history(self):
        self.run_pinned_probe('different-rejected-row-debug',debug=True)
        self.assertTrue((self.root/'context-debug-frame.json').is_file())
        self.assertNotIn('excerpt',self.debug_capture.report())
        self.temp.cleanup()
        debug=self.debug_capture.report()
        self.assertEqual(debug['status'],'READY')
        self.assertEqual(debug['excerpt']['rows'][0]['index'],11)
        self.assertEqual(debug['excerpt']['rows'][0]['text'],'❯ unknown')

    def test_serialized_debug_request_rejects_before_native_startup(self):
        self.assertIn('context_debug',inspect.signature(self.driver.drive).parameters,'sealed debug interface missing')
        marker=self.root/'unexpected-native'
        state=TerminalState(Path(os.environ['P004B_TERMINAL_NODE']),Path(os.environ['P004B_TERMINAL_MODULE_ROOT']),time.monotonic()+5)
        result=self.driver.drive([sys.executable,'-c','from pathlib import Path; Path('+repr(str(marker))+').touch()'],
            self.root/'capture',5,self.root/'events',dialogue='context',terminal_state=state,context_debug={'enabled':True})
        self.assertEqual(result,2); self.assertFalse(marker.exists())
        self.assertTrue(state.helper_reaped)
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

    def test_resumed_sdk_prompt_shape_is_diagnosed_before_command_without_input(self):
        seen=self.root/'input'; fake=self.root/'resume-ui.py'
        fake.write_text('import os,select,time,tty\nfrom pathlib import Path\n'
            'tty.setraw(0)\n'
            'os.write(1,("\\x1b[?1049h\\x1b[1;1HContext Usage\\r\\nFree space: 81%\\r\\nAutocompact buffer: 3%"'
            '\n "\\x1b[6;1H❯ /context\\x1b[7;1H❯ P0-04B synthetic text control. Reply P004B_SKILL_OK only."'
            '\n "\\x1b[38;1H❯\\u00a0").encode())\n'
            'while True:\n'
            ' if select.select([0],[],[],.1)[0]:\n'
            '  value=os.read(0,4096)\n'
            '  with Path('+repr(str(seen))+').open("ab") as stream: stream.write(value)\n',encoding='utf-8')
        state=TerminalState(Path(os.environ['P004B_TERMINAL_NODE']),
            Path(os.environ['P004B_TERMINAL_MODULE_ROOT']),time.monotonic()+3)
        diagnostics=TerminalDiagnostics()
        result=self.driver.drive([sys.executable,str(fake)],self.root/'capture',3,self.root/'events',
            dialogue='context',terminal_state=state,terminal_diagnostics=diagnostics)
        self.assertEqual(result,2)
        self.assertEqual(seen.read_bytes() if seen.exists() else b'',b'')
        report=diagnostics.report()
        self.assertFalse(report['rejected']); self.assertFalse(report['truncated'])
        failure=next(row for row in report['records'] if row['point']=='failure')
        self.assertEqual(failure['reasonCode'],'WAIT_DEADLINE')
        self.assertEqual(failure['structure']['readiness'],'UNSUPPORTED_MARKER')
        self.assertEqual(failure['structure'].get('readinessRejection'),{
            'rowRelation':'OTHER_CAPTURED_ROW','rowCause':'UNRECOGNIZED_SHAPE','rowShape':'SDK_TEXT_PROMPT_SHAPE'})
        self.assertTrue(state.helper_reaped)
        self.assertIn({'point':'native_cleanup','reasonCode':'CLEANUP_COMPLETED','leaderReaped':True},report['records'])
        events=[json.loads(line) for line in (self.root/'events').read_text().splitlines()]
        self.assertIn({'kind':'pty-driver','stage':'prompt_ready','outcome':'failed'},events)
        self.assertFalse(any(row['stage']=='context_inspected' for row in events))
        self.assertNotIn('P004B_SKILL_OK',json.dumps(report))
        self.assertNotIn('❯',json.dumps(report))

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
