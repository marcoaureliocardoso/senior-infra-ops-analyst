"""Credential-free wiring tests of real entrypoint/reducer boundaries."""
import contextlib
import importlib.util
import io
import json
import os
import subprocess
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest import mock

from browser_launch_diagnostics import context_failure_phases, reduce_line
from browser_operations_live import pty_failure_phases, pty_failure_reason, pty_context_observation
from browser_disposable_launcher import preflight_environment

ROOT=Path(__file__).resolve().parents[1]


class TerminalWiringTests(unittest.TestCase):
    def setUp(self):
        spec=importlib.util.spec_from_file_location('context_entry',ROOT/'tests/browser-context-driver.py')
        self.module=importlib.util.module_from_spec(spec); spec.loader.exec_module(self.module)
        self.temp=tempfile.TemporaryDirectory(prefix='terminal-wiring-test-')
        self.addCleanup(self.temp.cleanup); self.root=Path(self.temp.name)

    def test_browser_context_entry_cannot_activate_offline_observation(self):
        with mock.patch.object(sys,'argv',['context-entry','--observe-post-enter']),\
                contextlib.redirect_stderr(io.StringIO()),\
                mock.patch.object(self.module,'prepare_approval',side_effect=AssertionError('approval consumed')) as approval:
            with self.assertRaises(SystemExit) as error: self.module.main()
        self.assertEqual(error.exception.code,2)
        approval.assert_not_called()

    def test_missing_runtime_precedes_claim_consumption(self):
        claim=self.root/'claim'; claim.write_text('owned test claim')
        args=['context-entry','--claim',str(claim),'--commit','a'*40,'--run-nonce','p004b-'+'b'*32,
            '--source-root',str(ROOT),'--capture',str(self.root/'capture'),'--events',str(self.root/'events'),
            '--dialogue','context','--timeout','5','--terminal-engine','headless',
            '--terminal-node',os.environ['P004B_TERMINAL_NODE'],
            '--terminal-module-root',str(self.root/'absent'),'--',sys.executable]
        with mock.patch.object(sys,'argv',args), \
             mock.patch.object(self.module,'prepare_approval',side_effect=AssertionError('approval reached before dependency gate')), \
             contextlib.redirect_stderr(io.StringIO()):
            try: outcome=self.module.main()
            except SystemExit: outcome='ARGPARSE_FAILED'
        self.assertEqual(outcome,2)
        self.assertEqual(claim.read_text(),'owned test claim')
        self.assertFalse((self.root/'capture').exists())

    def test_live_entrypoint_rejects_probe_activation_before_claim(self):
        claim=self.root/'claim'; claim.write_text('owned test claim')
        args=['context-entry','--claim',str(claim),'--commit','a'*40,'--run-nonce','p004b-'+'b'*32,
            '--source-root',str(ROOT),'--capture',str(self.root/'capture'),'--events',str(self.root/'events'),
            '--input-probe-scope','offline','--',sys.executable]
        with mock.patch.object(sys,'argv',args),\
                mock.patch.dict(os.environ,{'P004B_INPUT_PROBE':'1'}),\
                mock.patch.object(self.module,'prepare_approval',side_effect=AssertionError('claim reached')),\
                contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as caught: self.module.main()
        self.assertEqual(caught.exception.code,2)
        self.assertEqual(claim.read_text(),'owned test claim')
        self.assertFalse((self.root/'capture').exists())

    def test_real_helper_is_initialized_before_single_claim_consumption(self):
        from terminal_state_adapter import TerminalState
        private=self.root/'startup'; private.mkdir(mode=0o700)
        config=self.root/'home/.claude'; config.mkdir(parents=True,mode=0o700)
        mcp=self.root/'mcp.json'; mcp.write_text('{"mcpServers":{}}')
        native=self.root/'native'
        native.write_text('#!/usr/bin/python3\nimport os,tty\n'
            'tty.setraw(0)\nos.write(1,"\\x1b[?1049h\\x1b[38;1H❯\\u00a0".encode())\n'
            'def line():\n'
            ' value=bytearray()\n'
            ' while not value.endswith(b"\\r"): value.extend(os.read(0,1))\n'
            ' return value\n'
            'if line()!=b"/context\\r": raise SystemExit(1)\n'
            'os.write(1,"\\x1b[2J\\x1b[HContext Usage\\r\\nFree space: 90%\\r\\n❯\\u00a0".encode())\n'
            'if line()!=b"/exit\\r": raise SystemExit(1)\n',encoding='utf-8')
        native.chmod(0o700)
        session='11111111-1111-4111-8111-111111111111'; commit='a'*40; nonce='p004b-'+'b'*32
        endpoint='https://api.deepseek.com/anthropic'; now=int(time.time())
        claim=private/'claim.json'
        claim.write_text(json.dumps({'commit':commit,'runNonce':nonce,'sessionId':session,
            'endpoint':endpoint,'configDir':str(config),'executable':str(native),'probe':'main-before',
            'issuedAt':now,'expiresAt':now+120})); claim.chmod(0o600)
        args=['entry','--claim',str(claim),'--commit',commit,'--run-nonce',nonce,'--source-root',str(ROOT),
            '--capture',str(self.root/'capture'),'--events',str(self.root/'events'),'--dialogue','context',
            '--timeout','8','--terminal-engine','headless','--terminal-node',os.environ['P004B_TERMINAL_NODE'],
            '--terminal-module-root',os.environ['P004B_TERMINAL_MODULE_ROOT'],'--',str(native),
            '--session-id',session,'--strict-mcp-config','--mcp-config',str(mcp)]
        order=[]; initialized=[]; original=self.module.prepare_approval
        def open_state(*args,**kwargs):
            state=TerminalState(*args,**kwargs)
            self.assertEqual(state.snapshot().active,'normal')
            initialized.append(state); order.append('initialized'); return state
        def approve(*args,**kwargs):
            order.append('claim'); return original(*args,**kwargs)
        with mock.patch.object(sys,'argv',args), mock.patch.object(self.module,'TerminalState',side_effect=open_state), \
             mock.patch.object(self.module,'prepare_approval',side_effect=approve), \
             mock.patch.object(self.module,'source_head',return_value=commit), \
             mock.patch.dict(os.environ,{'ANTHROPIC_BASE_URL':endpoint,'CLAUDE_CONFIG_DIR':str(config)}):
            self.assertEqual(self.module.main(),0)
        self.assertEqual(order,['initialized','claim'])
        self.assertEqual(len(initialized),1)
        self.assertFalse(claim.exists()); self.assertTrue((private/'spent').exists())
        with self.assertRaises(RuntimeError): initialized[0].snapshot()

    def test_preflight_forwards_only_explicit_public_terminal_paths(self):
        source={'HOME':'/owned','PATH':'/usr/bin','P004B_TERMINAL_NODE':'/test/node',
            'P004B_TERMINAL_MODULE_ROOT':'/test/modules','ANTHROPIC_API_KEY':'synthetic',
            'P004B_LIVE_AUTHORIZED':'1','NODE_OPTIONS':'--unused'}
        self.assertEqual(preflight_environment(source),{'HOME':'/owned','PATH':'/usr/bin',
            'P004B_TERMINAL_NODE':'/test/node','P004B_TERMINAL_MODULE_ROOT':'/test/modules'})

    def test_shared_driver_cli_blocks_missing_runtime_without_native_effect(self):
        marker=self.root/'effect'; fake=self.root/'native.py'
        fake.write_text('from pathlib import Path\nPath('+repr(str(marker))+').write_text("effect")\n')
        result=subprocess.run([sys.executable,str(ROOT/'tests/claude-pty-driver.py'),
            '--capture',str(self.root/'capture'),'--dialogue','context','--timeout','5',
            '--terminal-engine','headless','--terminal-node',os.environ['P004B_TERMINAL_NODE'],
            '--terminal-module-root',str(self.root/'absent'),'--',sys.executable,str(fake)],
            capture_output=True,timeout=10)
        self.assertEqual(result.returncode,2)
        self.assertEqual(result.stderr.strip(),b'BLOCKED: test terminal runtime unavailable')
        self.assertFalse(marker.exists()); self.assertFalse((self.root/'capture').exists())

    def test_credential_free_terminal_preflight_has_closed_result(self):
        preflight=ROOT/'tests/terminal-runtime-preflight.py'
        self.assertTrue(preflight.is_file(),'terminal preflight interface missing')
        for modules,expected in [(os.environ['P004B_TERMINAL_MODULE_ROOT'],0),(str(self.root/'absent'),2)]:
            result=subprocess.run([sys.executable,str(preflight),'--node',os.environ['P004B_TERMINAL_NODE'],
                '--module-root',modules],capture_output=True,timeout=10)
            self.assertEqual(result.returncode,expected)
            self.assertEqual(result.stderr,b'')
            value=json.loads(result.stdout)
            self.assertEqual(set(value),{'reasonCode'})
            self.assertEqual(value['reasonCode'],'TERMINAL_RUNTIME_READY' if expected==0 else 'TERMINAL_DEPENDENCY_UNAVAILABLE')

    def test_smoke_missing_runtime_blocks_before_private_root_creation(self):
        result=subprocess.run(['/bin/bash',str(ROOT/'tests/live-browser-operations-smoke.sh'),'--preflight'],
            env={'HOME':str(self.root),'TMPDIR':str(self.root),'PATH':'/usr/bin:/bin'},
            capture_output=True,timeout=20)
        self.assertEqual(result.returncode,2)
        self.assertEqual(result.stderr.strip(),b'BLOCKED: test terminal runtime paths are required')
        self.assertEqual(list(self.root.iterdir()),[])

    def test_package_gate_does_not_provision_implicitly(self):
        result=subprocess.run(['/bin/bash',str(ROOT/'tests/validate-package.sh')],
            env={'HOME':str(self.root),'PATH':'/usr/bin:/bin'},capture_output=True,timeout=20)
        self.assertEqual(result.returncode,2)
        self.assertEqual(result.stderr.strip(),b'test terminal runtime paths are required')

    def test_terminal_failure_diagnostics_are_closed(self):
        for stage in ('terminal_state','terminal_cleanup'):
            events=self.root/'events'
            events.write_text(json.dumps({'kind':'pty-driver','stage':'initial_screen','outcome':'passed'})+'\n'+
                json.dumps({'kind':'pty-driver','stage':stage,'outcome':'failed'})+'\n')
            expected='initial_screen:passed,'+stage+':failed'
            self.assertEqual(pty_failure_phases(events),expected)
            self.assertEqual(pty_failure_reason(events),'PTY_'+stage.upper()+'_FAILED')
            diagnostic=f'BLOCKED: trusted context probe failed: main-before (PTY_{stage.upper()}_FAILED)'
            self.assertEqual(reduce_line(diagnostic.encode())['reasonCode'],'PTY_'+stage.upper()+'_FAILED')
            with self.assertRaises(ValueError): pty_context_observation(events,'synthetic-session','before')
        phases=context_failure_phases('terminal_preflight:failed')
        self.assertEqual(phases,[{'stage':'terminal_preflight','outcome':'failed'}])

    def test_post_exit_cleanup_failure_remains_failure_not_acceptance(self):
        events=self.root/'events'
        values=[{'kind':'pty-driver','stage':stage,'outcome':'passed'} for stage in ('initial_screen','prompt_ready')]
        values += [{'kind':'pty-driver','stage':'context_inspected','outcome':'passed','percent':7},
                   {'kind':'pty-driver','stage':'exit','outcome':'passed'},
                   {'kind':'pty-driver','stage':'terminal_cleanup','outcome':'failed'}]
        events.write_text(''.join(json.dumps(item)+'\n' for item in values))
        self.assertTrue(pty_failure_phases(events).endswith('terminal_cleanup:failed'))
        with self.assertRaises(ValueError): pty_context_observation(events,'synthetic-session','before')

    def test_structural_diagnostics_cannot_be_loaded_as_pty_acceptance(self):
        events=self.root/'events'
        events.write_text(json.dumps({'point':'helper_cleanup','reasonCode':'CLEANUP_COMPLETED',
            'leaderReaped':True})+'\n')
        with self.assertRaises(ValueError): pty_context_observation(events,'synthetic-session','before')
        events.write_text(json.dumps({'point':'failure','reasonCode':'INPUT_PROBE_REVOKED',
            'contextCommandFailure':{'phase':'EDIT_PENDING','check':'NORMALIZED_ELIGIBILITY',
                'commandBytesWritten':8,'enterBytesWritten':0},
            'normalizedInputFailure':{'reason':'UNSUPPORTED_ROW','rowRelation':'OTHER_CAPTURED_ROW',
                'rowCause':'UNRECOGNIZED_SHAPE'}})+'\n')
        with self.assertRaises(ValueError): pty_context_observation(events,'synthetic-session','before')

    def test_no_live_or_serialized_receipt_activation(self):
        import inspect
        import headless_context_driver
        self.assertNotIn('context_receipt',inspect.signature(headless_context_driver.drive_context).parameters)
        claim=self.root/'claim'; claim.write_text('owned test claim')
        args=['context-entry','--claim',str(claim),'--commit','a'*40,'--run-nonce','p004b-'+'b'*32,
            '--source-root',str(ROOT),'--capture',str(self.root/'capture'),'--events',str(self.root/'events'),
            '--context-receipt','{}','--',sys.executable]
        with mock.patch.object(sys,'argv',args),contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as caught: self.module.main()
        self.assertEqual(caught.exception.code,2); self.assertFalse((self.root/'capture').exists())
        self.assertEqual(claim.read_text(),'owned test claim')

    def test_owned_echo_unit_is_in_complete_package_gate(self):
        self.assertIn('python3 tests/test-terminal-context-echo.py',(ROOT/'tests/validate-package.sh').read_text())

    def test_owned_echo_source_excluded_from_nori_staging(self):
        sys.path.insert(0,str(ROOT))
        from scripts.nori_package import build_staging
        destination=self.root/'staging'
        build_staging(ROOT,destination)
        self.assertFalse((destination/'tests').exists())
        self.assertFalse(any(path.name=='terminal_context_echo.py' for path in destination.rglob('*')))
        self.assertFalse(any(path.name=='terminal_context_diagnostics.py' for path in destination.rglob('*')))

    def test_context_observer_suite_is_dispatched_by_package_gate(self):
        commands=self.root/'bin'; commands.mkdir()
        python=commands/'python3'
        python.write_text('#!/bin/sh\n'
            'if [ "$1" = tests/test-terminal-context-diagnostics.py ]; then echo observer-suite; exit 42; fi\n'
            'if [ "$1" = tests/test-terminal-structural-diagnostics.py ]; then echo observer-skipped; exit 43; fi\n'
            'exit 0\n')
        node=commands/'node'; node.write_text('#!/bin/sh\nexit 0\n')
        python.chmod(0o700); node.chmod(0o700)
        result=subprocess.run(['/bin/bash',str(ROOT/'tests/validate-package.sh')],cwd=ROOT,
            env={'PATH':str(commands)+':/usr/bin:/bin','P004B_TERMINAL_NODE':'synthetic',
                'P004B_TERMINAL_MODULE_ROOT':'synthetic'},capture_output=True,text=True,timeout=5)
        self.assertEqual((result.returncode,result.stdout.strip()),(42,'observer-suite'))

    def test_nonce_diagnostic_suites_are_dispatched_by_package_gate(self):
        for target in ('test-terminal-nonce-history-diagnostics.py','test-nonce-history-driver.py'):
            with self.subTest(suite=target):
                commands=self.root/target; commands.mkdir()
                python=commands/'python3'
                python.write_text('#!/bin/sh\n'
                    'if [ "$1" = tests/'+target+' ]; then echo nonce-suite; exit 42; fi\nexit 0\n')
                node=commands/'node'; node.write_text('#!/bin/sh\nexit 0\n')
                python.chmod(0o700); node.chmod(0o700)
                result=subprocess.run(['/bin/bash',str(ROOT/'tests/validate-package.sh')],cwd=ROOT,
                    env={'PATH':str(commands)+':/usr/bin:/bin','P004B_TERMINAL_NODE':'synthetic',
                        'P004B_TERMINAL_MODULE_ROOT':'synthetic'},capture_output=True,text=True,timeout=5)
                self.assertEqual((result.returncode,result.stdout.strip()),(42,'nonce-suite'))


if __name__=='__main__': unittest.main()
