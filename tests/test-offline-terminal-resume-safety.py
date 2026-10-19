"""No-provider safety contract for the isolated native offline regression."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import sys
import shutil
import signal
import subprocess
import time
import unittest
from unittest import mock
from terminal_structural_diagnostics import TerminalDiagnostics

ROOT=Path(__file__).resolve().parents[1]
MODULE=ROOT/'tests/offline-terminal-resume-probe.py'


def passed_stages():
    return [{'phase':phase,'events':[{'stage':'context_inspected','outcome':'passed','percent':16},
        {'stage':'exit','outcome':'passed'}],'diagnostics':{'records':[
            *({'point':point,'reasonCode':'CHECKPOINT'} for point in ('input_probe_started','input_probe_echo','input_probe_cleared')),
            *({'point':point,'reasonCode':'CLEANUP_COMPLETED','leaderReaped':True} for point in ('native_cleanup','helper_cleanup'))],
            'truncated':False,'rejected':False}} for phase in ('before','after')]


class OfflineTerminalResumeSafetyTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(MODULE.is_file(),'offline regression interface missing')
        spec=importlib.util.spec_from_file_location('offline_terminal_resume',MODULE)
        self.module=importlib.util.module_from_spec(spec); spec.loader.exec_module(self.module)

    def test_loopback_namespace_only(self):
        if not shutil.which('bwrap'):
            self.skipTest('Bubblewrap unavailable; namespace audit NOT proven, native controls remain blocked')
        report=self.module.run_isolation_audit(source=ROOT,
            node=Path(os.environ['P004B_TERMINAL_NODE']),module_root=Path(os.environ['P004B_TERMINAL_MODULE_ROOT']))
        self.assertEqual(report,{'networkIsolated':True,'operatorStateHidden':True,
            'capabilitiesDropped':True,'disposableRootAbsent':True})

    def test_scope_audit_rejects_host_and_checks_real_helper_inside_namespace(self):
        self.assertTrue(callable(getattr(self.module,'audit_input_probe_scope',None)),
            'actual namespace scope audit missing')
        with self.assertRaises(RuntimeError):
            self.module.audit_input_probe_scope(Path(os.environ['P004B_TERMINAL_NODE']),
                Path(os.environ['P004B_TERMINAL_MODULE_ROOT']))
        if not shutil.which('bwrap'): self.skipTest('Bubblewrap unavailable; input scope NOT proven')
        valid=self.module.run_isolation_audit(source=ROOT,node=Path(os.environ['P004B_TERMINAL_NODE']),
            module_root=Path(os.environ['P004B_TERMINAL_MODULE_ROOT']))
        self.assertTrue(valid['networkIsolated']); self.assertTrue(valid['disposableRootAbsent'])
        invalid=self.module.run_isolation_audit(source=ROOT,node=Path('/usr/bin/false'),
            module_root=Path(os.environ['P004B_TERMINAL_MODULE_ROOT']))
        self.assertEqual(invalid,{'reasonCode':'OFFLINE_PROBE_BLOCKED','disposableRootAbsent':True})

    def test_private_cleanup_before_report(self):
        with tempfile.TemporaryDirectory(prefix='offline-finalize-test-') as parent:
            root=Path(parent)/'owned'; root.mkdir(mode=0o700)
            (root/'raw').write_text('synthetic raw fixture')
            identity=root.stat()
            result=self.module.finalize_owned(root,identity,{'cases':[]})
            self.assertFalse(root.exists())
            self.assertTrue(result['disposableRootAbsent'])
        with tempfile.TemporaryDirectory(prefix='offline-finalize-test-') as parent:
            root=Path(parent)/'owned'; root.mkdir(mode=0o700); identity=root.stat()
            with mock.patch.object(self.module.shutil,'rmtree',side_effect=OSError):
                result=self.module.finalize_owned(root,identity,{'cases':[{'beforeExit':0}]})
            self.assertEqual(result,{'reasonCode':'OFFLINE_CLEANUP_FAILED'})

    def test_acceptance_requires_operational_context(self):
        case={'case':'skill-turn','beforeExit':0,'sdkExit':0,'afterExit':0,'contextInspected':True,
            'naturalExit':True,'caseRootAbsent':True,'skillCalls':1,'validSkillSample':True,'validSDKSample':True,
            'stages':passed_stages()}
        self.assertTrue(self.module.case_complete(case))
        for field,value in [('afterExit',2),('contextInspected',False),('naturalExit',False),
                            ('caseRootAbsent',False),('validSkillSample',False),('skillCalls',0),
                            ('validSDKSample',False),('validSDKSample',1)]:
            changed={**case,field:value}
            self.assertFalse(self.module.case_complete(changed))

    def test_success_without_retained_context_proof_is_inconclusive(self):
        case={'case':'text-turn','beforeExit':0,'sdkExit':0,'afterExit':0,'contextInspected':True,
            'naturalExit':True,'caseRootAbsent':True,'skillCalls':0,'validSkillSample':False,'validSDKSample':True,
            'stages':passed_stages()}
        self.assertTrue(self.module.case_complete(case))
        for fault in ('missing','empty','truncated','rejected','cleanup','echo'):
            import copy
            bad=copy.deepcopy(case)
            if fault=='missing': bad.pop('stages')
            elif fault=='empty': bad['stages']=[]
            elif fault in ('truncated','rejected'): bad['stages'][1]['diagnostics'][fault]=True
            else:
                point='native_cleanup' if fault=='cleanup' else 'input_probe_echo'
                bad['stages'][1]['diagnostics']['records']=[r for r in bad['stages'][1]['diagnostics']['records'] if r['point']!=point]
            with self.subTest(fault=fault): self.assertFalse(self.module.case_complete(bad))

    def fake_report(self,mode):
        from resume_history_fixtures import write_fake_cli
        if not shutil.which('bwrap'): self.skipTest('Bubblewrap unavailable; fake resume workflow NOT proven')
        with tempfile.TemporaryDirectory(prefix='resume-cli-double-') as directory:
            fake=Path(directory)/'synthetic-cli'
            write_fake_cli(fake,mode=mode)
            original=self.module.TerminalCancellation.spawn; launches=[]
            def launch(token,command,**options):
                launches.append(command); return original(token,command,**options)
            with mock.patch.object(self.module.TerminalCancellation,'spawn',new=launch):
                report=self.module.run_offline_controls(source=ROOT,claude=fake,
                    node=Path(os.environ['P004B_TERMINAL_NODE']),
                    module_root=Path(os.environ['P004B_TERMINAL_MODULE_ROOT']))
            self.assertEqual(len(launches),1,'isolated workflow must not repeat')
        self.assertTrue(report.get('disposableRootAbsent'))
        if mode=='interrupt':
            self.assertIn(report['reasonCode'],('OFFLINE_PROBE_BLOCKED','OFFLINE_PROBE_INTERRUPTED'))
            self.assertNotIn('cases',report)
        else: self.assertEqual(report.get('runtime'),'0.0.1',str({key:report.get(key)
            for key in ('reasonCode','failureDiagnostic')}))
        self.assertLessEqual(len(json.dumps(report,sort_keys=True).encode()),16384)
        for forbidden in ('session_id','sdk.stream','P004B_SKILL_OK','synthetic-offline-only-key','fixture-kind'):
            self.assertNotIn(forbidden,json.dumps(report))
        return report

    def test_isolated_fake_text_and_skill_resume_both_complete(self):
        report=self.fake_report('success')
        self.assertEqual(report['reasonCode'],'OFFLINE_CONTROLS_PASSED')
        self.assertEqual([case['case'] for case in report['cases']],['text-turn','skill-turn'])
        for case,messages,calls in zip(report['cases'],(1,2),(0,1)):
            self.assertEqual((case['messages'],case['skillCalls']),(messages,calls))
            self.assertIs(case.get('validSDKSample'),True)
            self.assertEqual((case['beforeExit'],case['sdkExit'],case['afterExit']),(0,0,0))
            self.assertTrue(case['contextInspected'] and case['naturalExit'] and case['caseRootAbsent'])
            for stage in case['stages']:
                self.assertFalse(stage['diagnostics']['rejected'] or stage['diagnostics']['truncated'])
                cleanups=[row for row in stage['diagnostics']['records'] if row['point'].endswith('_cleanup')]
                self.assertEqual(len(cleanups),2)
                self.assertTrue(all(row['reasonCode']=='CLEANUP_COMPLETED' and row['leaderReaped'] is True for row in cleanups))

    def test_exit_zero_wrong_session_never_launches_after(self):
        report=self.fake_report('wrong-session')
        self.assertEqual(report['reasonCode'],'OFFLINE_CONTROLS_INCONCLUSIVE')
        self.assertEqual(len(report['cases']),1)
        case=report['cases'][0]
        self.assertEqual((case['beforeExit'],case['sdkExit'],case['afterExit']),(0,0,2))
        self.assertIs(case.get('validSDKSample'),False)
        self.assertEqual([stage['phase'] for stage in case['stages']],['before'])

    def test_sdk_witness_reads_bound_descriptor_not_replaced_path(self):
        invalid=self.fake_report('replace-invalid')
        self.assertEqual(invalid['reasonCode'],'OFFLINE_CONTROLS_INCONCLUSIVE')
        self.assertIs(invalid['cases'][0].get('validSDKSample'),False)
        self.assertEqual([stage['phase'] for stage in invalid['cases'][0]['stages']],['before'])
        valid=self.fake_report('replace-valid')
        self.assertEqual(valid['reasonCode'],'OFFLINE_CONTROLS_PASSED')
        self.assertTrue(all(case.get('validSDKSample') is True for case in valid['cases']))

    def test_fake_view_loss_cleanup_failure_and_interrupt_stop_without_retry(self):
        for mode in ('view-loss','cleanup-failure','interrupt'):
            with self.subTest(mode=mode):
                report=self.fake_report(mode)
                self.assertNotEqual(report['reasonCode'],'OFFLINE_CONTROLS_PASSED')
                if mode!='interrupt': self.assertEqual(len(report['cases']),1)

    def test_phase_diagnostics_are_separate_and_cannot_supply_acceptance(self):
        self.assertTrue(callable(getattr(self.module,'context_stage_report',None)),
            'offline structural report integration missing')
        diagnostics=TerminalDiagnostics(); diagnostics.add('helper_cleanup','CLEANUP_COMPLETED',leaderReaped=True)
        events=[{'kind':'pty-driver','stage':'context_inspected','outcome':'passed','percent':16},
                {'kind':'pty-driver','stage':'context_inspected','outcome':'failed'}]
        report=self.module.context_stage_report('before',events,diagnostics)
        self.assertEqual(report,{'phase':'before','events':[
            {'stage':'context_inspected','outcome':'passed','percent':16},
            {'stage':'context_inspected','outcome':'failed'}],
            'diagnostics':{'records':[{'point':'helper_cleanup','reasonCode':'CLEANUP_COMPLETED','leaderReaped':True}],
                           'truncated':False,'rejected':False}})
        self.assertFalse(self.module.case_complete({'case':'text-turn','stages':[report]}))

    def test_four_maximal_context_diagnostics_fit_unchanged_outer_report_bound(self):
        diagnostics=TerminalDiagnostics()
        structure={'buffer':'normal','cursorX':120,'cursorY':39,'baseY':1000,'viewportY':1000,
            'candidateCount':40,'inputFresh':True,'contextFresh':True,'locationFresh':True,
            'authentication':'API_KEY_APPROVAL_REQUIRED','readiness':'AUTHENTICATION_REQUIRED'}
        for _ in range(100): diagnostics.add('failure','WAIT_DEADLINE',structure=structure)
        events=[{'kind':'pty-driver','stage':stage,'outcome':'passed'} for stage in
            ('initial_screen','api_key_approval','theme_selection','trust_selection','prompt_ready')]
        events += [{'kind':'pty-driver','stage':'context_inspected','outcome':'passed','percent':100},
                   {'kind':'pty-driver','stage':'exit','outcome':'passed'},
                   {'kind':'pty-driver','stage':'terminal_cleanup','outcome':'failed'}]
        cases=[{'case':name,'beforeExit':0,'sdkExit':0,'afterExit':0,'contextInspected':True,
            'naturalExit':True,'caseRootAbsent':True,'skillCalls':1,'validSkillSample':True,'messages':4,
            'stages':[self.module.context_stage_report(phase,events,diagnostics) for phase in ('before','after')]}
            for name in ('text-turn','skill-turn')]
        report={'reasonCode':'OFFLINE_CONTROLS_PASSED','runtime':'9999.9999.9999','cases':cases,
            'networkIsolated':True,'operatorStateHidden':True,'capabilitiesDropped':True,'disposableRootAbsent':True}
        self.assertLessEqual(len(json.dumps(report,sort_keys=True).encode()),16384)

    def test_no_live_mode_or_retry_authority(self):
        self.assertEqual(self.module.validate_mode(['--run-live']),False)
        self.assertEqual(self.module.validate_mode(['--repeat']),False)
        self.assertEqual(self.module.validate_mode(['--run-offline']),True)
        self.assertEqual(self.module.validate_mode(['--audit-isolation']),True)

    def test_debug_flag_is_offline_only_and_missing_runtime_never_launches(self):
        self.assertTrue(self.module.validate_mode(['--run-offline','--debug-context']))
        for args in (['--debug-context'],['--audit-isolation','--debug-context'],
                     ['--run-live','--debug-context'],['--run-offline','--debug-context','--repeat']):
            self.assertFalse(self.module.validate_mode(args))
        common=['--source',str(ROOT),'--node',os.environ['P004B_TERMINAL_NODE'],
                '--module-root',os.environ['P004B_TERMINAL_MODULE_ROOT']]
        with mock.patch.object(sys,'argv',[str(MODULE),'--run-offline','--debug-context',*common]),\
                mock.patch('builtins.print') as output:
            self.assertEqual(self.module.main(),2)
            self.assertEqual(json.loads(output.call_args.args[0]),{'reasonCode':'OFFLINE_PROBE_BLOCKED'})

    def test_stops_at_first_failed_case_without_retry(self):
        calls=[]
        def failed(name):
            calls.append(name)
            return {'case':name,'afterExit':2,'caseRootAbsent':True}
        report=self.module.run_cases(failed)
        self.assertEqual(calls,['text-turn'])
        self.assertEqual(report['reasonCode'],'OFFLINE_CONTROLS_INCONCLUSIVE')
        self.assertEqual(len(report['cases']),1)

    def test_edit_option_is_explicit_offline_only(self):
        self.assertTrue(self.module.validate_mode(['--run-offline','--debug-context-edit']))
        for args in (['--debug-context-edit'],['--run-live','--debug-context-edit'],
                     ['--audit-isolation','--debug-context-edit'],
                     ['--run-offline','--debug-context','--debug-context-edit'],
                     ['--run-offline','--debug-context-edit','--debug-context-edit']):
            self.assertFalse(self.module.validate_mode(args))
        common=['--source',str(ROOT),'--node',os.environ['P004B_TERMINAL_NODE'],
            '--module-root',os.environ['P004B_TERMINAL_MODULE_ROOT']]
        with mock.patch.object(sys,'argv',[str(MODULE),'--run-offline','--debug-context-edit',*common]),\
                mock.patch.object(self.module,'run_offline_controls',return_value={'reasonCode':'OFFLINE_PROBE_BLOCKED'}) as run,\
                mock.patch('builtins.print'):
            self.assertEqual(self.module.main(),2)
        self.assertTrue(run.call_args.kwargs['debug_context_edit'])

    def test_edit_transport_unavailable_blocks_before_spawn(self):
        # Before Task3 this was a closed gate; a missing executable must remain closed.
        with mock.patch.object(self.module.TerminalCancellation,'spawn',side_effect=AssertionError('launched')),\
                mock.patch.object(self.module.tempfile,'TemporaryFile',side_effect=AssertionError('report file')):
            result=self.module.run_offline_controls(source=ROOT,claude=Path('/unopened-native'),
                node=Path(os.environ['P004B_TERMINAL_NODE']),
                module_root=Path(os.environ['P004B_TERMINAL_MODULE_ROOT']),debug_context_edit=True)
        self.assertEqual(result['reasonCode'],'OFFLINE_PROBE_BLOCKED')
        self.assertNotIn('excerpt',result['debugContextEdit'])

    def read_edit_peer(self,code,*,seconds=2,cancel=False):
        self.assertTrue(callable(getattr(self.module,'_read_edit_namespace',None)),'bounded edit IPC missing')
        from terminal_cancellation import TerminalCancellation
        with tempfile.TemporaryDirectory(prefix='edit-ipc-peer-') as directory:
            pidfile=Path(directory)/'pid'
            childfile=Path(directory)/'child'
            prefix=('import os,sys,select\nfrom pathlib import Path\nPath('+repr(str(pidfile))+').write_text(str(os.getpid()))\n'
                'childfile=Path('+repr(str(childfile))+')\n')
            with TerminalCancellation() as token:
                if cancel:
                    original=token.check
                    def check():
                        if pidfile.exists(): token.requested=True
                        original()
                    token.check=check
                try:
                    return self.module._read_edit_namespace([sys.executable,'-I','-B','-c',prefix+code],
                        cancellation=token,deadline=time.monotonic()+seconds)
                finally:
                    self._edit_peer_pid=int(pidfile.read_text()) if pidfile.exists() else None
                    self._edit_descendant_pid=int(childfile.read_text()) if childfile.exists() else None

    def test_edit_pipe_eof_and_exit_are_independent(self):
        self.assertTrue(callable(getattr(self.module,'_read_edit_namespace',None)),'bounded edit IPC missing')
        start=time.monotonic()
        with self.assertRaises(TimeoutError):
            self.read_edit_peer('os.close(1)\nselect.select([],[],[],60)\n',seconds=.25)
        self.assertLess(time.monotonic()-start,3)
        if self._edit_peer_pid is not None: self.assertFalse(Path(f'/proc/{self._edit_peer_pid}').exists())
        code,data=self.read_edit_peer('os.write(1,b"{partial")\n')
        self.assertEqual((code,data),(0,b'{partial'))
        try:
            code,data=self.read_edit_peer('pid=os.fork()\n'
                'if pid==0: childfile.write_text(str(os.getpid())); select.select([],[],[],60); os._exit(0)\n'
                'while not childfile.exists(): select.select([],[],[],.005)\n'
                'os.write(1,b"{}"); os._exit(0)\n')
        except RuntimeError as error:
            self.assertEqual(str(error),'terminal ownership unavailable')
        else:
            self.assertIn(code,(0,2)); self.assertEqual(data,b'{}')
        self.assertFalse(Path(f'/proc/{self._edit_peer_pid}').exists())
        if self._edit_descendant_pid is not None:
            self.assertFalse(Path(f'/proc/{self._edit_descendant_pid}').exists())

    def test_edit_pipe_overflow_backpressure_and_cancel(self):
        from terminal_cancellation import TerminalCancelled
        self.assertTrue(callable(getattr(self.module,'_read_edit_namespace',None)),'bounded edit IPC missing')
        code,data=self.read_edit_peer('os.write(1,b"x"*16384)\n')
        self.assertEqual(code,0); self.assertEqual(len(data),16384)
        for count in (16385,262144):
            with self.assertRaises(ValueError): self.read_edit_peer('os.write(1,b"x"*'+str(count)+')\n')
            if self._edit_peer_pid is not None: self.assertFalse(Path(f'/proc/{self._edit_peer_pid}').exists())
        code,data=self.read_edit_peer('os.write(1,b"\\xe2"); os.write(1,b"\\x9d\\xaf")\n')
        self.assertEqual((code,data),(0,'❯'.encode()))
        with self.assertRaises(TerminalCancelled):
            self.read_edit_peer('select.select([],[],[],60)\n',cancel=True)
        if self._edit_peer_pid is not None: self.assertFalse(Path(f'/proc/{self._edit_peer_pid}').exists())

    def edit_namespace_fixture(self,*,payload=None,cleanup_fault=False,exit_fault=False,passed=False,
                               lifetime_phase=None,lifetime_fault=None):
        spec=importlib.util.spec_from_file_location('edit_debug_fixture',ROOT/'tests/test-terminal-context-debug.py')
        fixture=importlib.util.module_from_spec(spec); spec.loader.exec_module(fixture)
        base=fixture.edit_report_fixture()
        base['_pendingContextEdit']={'status':'PREPARED','excerpt':{
            'rowRelation':'OTHER_CAPTURED_ROW','text':'❯ /context synthetic description'}}
        if passed:
            import copy
            base['reasonCode']='OFFLINE_CONTROLS_PASSED'; first=base['cases'][0]
            first.update(beforeExit=0,sdkExit=0,afterExit=0,contextInspected=True,naturalExit=True)
            stage=first['stages'][0]; stage['events']=[{'stage':'context_inspected','outcome':'passed','percent':10}]
            stage['diagnostics']['records']=stage['diagnostics']['records'][1:]
            after=copy.deepcopy(stage); after['phase']='after'; first['stages'].append(after)
            second=copy.deepcopy(first); second.update(case='skill-turn',skillCalls=1,validSkillSample=True)
            base['cases'].append(second); base['_pendingContextEdit']={'status':'NO_CAPTURE'}
        data=json.dumps(base).encode() if payload is None else payload
        with tempfile.TemporaryDirectory(prefix='edit-namespace-fixture-') as directory:
            parent=Path(directory); owned=parent/'owned'; owned.mkdir(mode=0o700)
            fake=parent/'fake-bwrap'; fake.write_text('#!/usr/bin/python3 -I\nimport os\nos.write(1,'+repr(data)+')\n')
            fake.chmod(0o700)
            self._edit_outer_absent=False
            original_spawn=self.module.TerminalCancellation.spawn; spawns=[]; tokens=[]
            clock=time.monotonic; offset=[0]
            def fault(phase):
                if phase==lifetime_phase:
                    if lifetime_fault=='cancel': tokens[0].requested=True
                    elif lifetime_fault=='expire': offset[0]=1000
            def spawn(token,command,**kwargs):
                tokens.append(token)
                spawns.append(kwargs.get('stdout')); return original_spawn(token,command,**kwargs)
            original_remove=self.module.shutil.rmtree
            original_exit=self.module.TerminalCancellation.__exit__
            original_json=self.module._edit_json
            original_finalize=__import__('terminal_context_debug').finalize_edit_report
            self._edit_cleanup_guarded=False
            def parsed(data):
                result=original_json(data); fault('post-read'); return result
            def finalized(*args,**kwargs):
                result=original_finalize(*args,**kwargs); fault('publication'); return result
            def remove(path,*args,**kwargs):
                if cleanup_fault and Path(path)==owned: raise OSError('synthetic cleanup loss')
                result=original_remove(path,*args,**kwargs)
                if Path(path)==owned:
                    self._edit_cleanup_guarded=bool(tokens and tokens[0]._entered)
                    fault('root-cleanup')
                return result
            def exited(token,*args):
                result=original_exit(token,*args)
                fault('namespace-cleanup')
                if exit_fault: raise RuntimeError('synthetic ownership cleanup loss')
                return result
            with mock.patch.object(self.module.shutil,'which',return_value=str(fake)),\
                    mock.patch.object(self.module.tempfile,'mkdtemp',return_value=str(owned)),\
                    mock.patch.object(self.module.tempfile,'TemporaryFile',side_effect=AssertionError('report file opened')),\
                    mock.patch.object(self.module.TerminalCancellation,'spawn',new=spawn),\
                    mock.patch.object(self.module.TerminalCancellation,'__exit__',new=exited),\
                    mock.patch.object(self.module.time,'monotonic',side_effect=lambda:clock()+offset[0]),\
                    mock.patch.object(self.module,'_edit_json',side_effect=parsed),\
                    mock.patch('terminal_context_debug.finalize_edit_report',side_effect=finalized),\
                    mock.patch.object(self.module.shutil,'rmtree',side_effect=remove):
                result=self.module.run_offline_controls(source=ROOT,claude=Path('/usr/bin/true'),
                    node=Path(os.environ['P004B_TERMINAL_NODE']),
                    module_root=Path(os.environ['P004B_TERMINAL_MODULE_ROOT']),debug_context_edit=True)
            self._edit_outer_absent=not owned.exists()
            self.assertEqual(spawns,[subprocess.PIPE])
            return result

    def test_edit_publication_lifetime_covers_post_read_and_disposal(self):
        for phase in ('post-read','namespace-cleanup','root-cleanup','publication'):
            for failure in ('cancel','expire'):
                with self.subTest(phase=phase,failure=failure):
                    result=self.edit_namespace_fixture(lifetime_phase=phase,lifetime_fault=failure)
                    self.assertTrue(self._edit_outer_absent)
                    self.assertNotIn('excerpt',result['debugContextEdit'])
                    self.assertNotEqual(result['debugContextEdit']['status'],'READY')
                    self.assertEqual(result['reasonCode'],'OFFLINE_PROBE_INTERRUPTED' if failure=='cancel'
                                     else 'OFFLINE_PROBE_BLOCKED')
                    self.assertTrue(self._edit_cleanup_guarded)

    def test_edit_pipe_never_uses_report_tempfile(self):
        result=self.edit_namespace_fixture()
        self.assertTrue(self._edit_outer_absent)
        self.assertEqual(result['debugContextEdit']['status'],'READY')
        self.assertNotIn('_pendingContextEdit',result)

    def test_edit_publication_is_after_full_disposal(self):
        result=self.edit_namespace_fixture(cleanup_fault=True)
        self.assertFalse(self._edit_outer_absent)
        self.assertEqual(result['reasonCode'],'OFFLINE_CLEANUP_FAILED')
        self.assertNotIn('excerpt',result['debugContextEdit'])
        for payload in (b'{partial',b'{"runtime":"1.2.3","runtime":"1.2.4"}',b'\xff'):
            result=self.edit_namespace_fixture(payload=payload)
            self.assertTrue(self._edit_outer_absent)
            self.assertNotIn('excerpt',result['debugContextEdit'])
            self.assertNotIn('_pendingContextEdit',result)
        result=self.edit_namespace_fixture(exit_fault=True,passed=True)
        self.assertNotEqual(result['reasonCode'],'OFFLINE_CONTROLS_PASSED')
        self.assertNotIn('excerpt',result['debugContextEdit'])

    def test_edit_cli_rejects_duplicate_before_controls(self):
        import contextlib
        import io
        common=['--source',str(ROOT),'--node',os.environ['P004B_TERMINAL_NODE'],
            '--module-root',os.environ['P004B_TERMINAL_MODULE_ROOT']]
        with mock.patch.object(sys,'argv',[str(MODULE),'--run-offline','--debug-context-edit','--debug-context-edit',*common]),\
                mock.patch.object(self.module,'run_offline_controls',side_effect=AssertionError('controls reached')),\
                contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as caught: self.module.main()
        self.assertEqual(caught.exception.code,2)

    def test_edit_actual_preparation_namespace_and_disposal(self):
        if not shutil.which('bwrap'):
            self.skipTest('Bubblewrap unavailable; memory-only end-to-end path NOT proven')
        with tempfile.TemporaryDirectory(prefix='edit-fake-native-') as directory:
            fake=Path(directory)/'synthetic-ui'
            fake.write_text('#!/usr/bin/python3 -I\nimport os,sys,select,tty\n'
                'if "--version" in sys.argv: print("0.0.1 (Claude Code)"); raise SystemExit(0)\n'
                'tty.setraw(0)\nos.write(1,"\\x1b[?1049h\\x1b[38;1H❯\\u00a0".encode())\n'
                'body=bytearray()\n'
                'while len(body)<8: body.extend(os.read(0,8-len(body)))\n'
                'if body!=b"/context": raise SystemExit(1)\n'
                'os.write(1,"\\x1b[38;3H/context\\x1b[35;1H❯ /context synthetic diagnostic\\x1b[38;11H".encode())\n'
                'select.select([],[],[],60)\n',encoding='utf-8')
            fake.chmod(0o700)
            with mock.patch.object(self.module.tempfile,'TemporaryFile',side_effect=AssertionError('report file')):
                result=self.module.run_offline_controls(source=ROOT,claude=fake,
                    node=Path(os.environ['P004B_TERMINAL_NODE']),
                    module_root=Path(os.environ['P004B_TERMINAL_MODULE_ROOT']),debug_context_edit=True)
        self.assertEqual(result['reasonCode'],'OFFLINE_CONTROLS_INCONCLUSIVE')
        self.assertEqual(result['runtime'],'0.0.1')  # Fixture label, not an installed Claude observation.
        self.assertTrue(result['disposableRootAbsent']); self.assertTrue(result['cases'][0]['caseRootAbsent'])
        self.assertEqual(result['cases'][0]['messages'],0)
        self.assertEqual(result['debugContextEdit'],{'status':'READY','untrustedData':True,
            'chatCopyMayPersist':True,'excerpt':{'rowRelation':'OTHER_CAPTURED_ROW','text':'❯ /context synthetic diagnostic'}})

    def test_edit_pending_is_not_acceptance_or_cross_dialogue(self):
        case={'case':'text-turn','caseRootAbsent':True,'debugContextEdit':{'status':'READY'},
            '_pendingContextEdit':{'status':'PREPARED','excerpt':{'rowRelation':'OTHER_CAPTURED_ROW','text':'synthetic'}}}
        self.assertFalse(self.module.case_complete(case))

    def test_two_complete_cases_required(self):
        calls=[]
        def complete(name):
            calls.append(name)
            return {'case':name,'beforeExit':0,'sdkExit':0,'afterExit':0,
                'contextInspected':True,'naturalExit':True,'caseRootAbsent':True,
                'validSkillSample':name=='skill-turn','skillCalls':1 if name=='skill-turn' else 0,
                'validSDKSample':True,'stages':passed_stages()}
        report=self.module.run_cases(complete)
        self.assertEqual(calls,['text-turn','skill-turn'])
        self.assertEqual(report['reasonCode'],'OFFLINE_CONTROLS_PASSED')

    def test_cli_audit_option_runs_and_missing_claude_blocks(self):
        common=['--source',str(ROOT),'--node',os.environ['P004B_TERMINAL_NODE'],
                '--module-root',os.environ['P004B_TERMINAL_MODULE_ROOT']]
        with mock.patch.object(sys,'argv',[str(MODULE),'--audit-isolation',*common]):
            with mock.patch('builtins.print') as output:
                result=self.module.main()
                report=json.loads(output.call_args.args[0])
                if shutil.which('bwrap'):
                    self.assertEqual(result,0); self.assertTrue(report['networkIsolated'])
                else:
                    self.assertEqual(result,2); self.assertEqual(report,{'reasonCode':'OFFLINE_PROBE_BLOCKED'})
        with mock.patch.object(sys,'argv',[str(MODULE),'--run-offline',*common]):
            with mock.patch('builtins.print') as output:
                self.assertEqual(self.module.main(),2)
                self.assertEqual(json.loads(output.call_args.args[0]),{'reasonCode':'OFFLINE_PROBE_BLOCKED',
                    'failureDiagnostic':{'phase':'PRECHECK','exitCode':None,'signal':None,'exceptionClass':None,'errno':None}})

    def test_interruption_removes_namespace_root(self):
        with tempfile.TemporaryDirectory() as parent:
            owned=Path(parent)/'owned'; owned.mkdir(mode=0o700)
            with mock.patch.object(self.module.tempfile,'mkdtemp',return_value=str(owned)),\
                    mock.patch.object(self.module.shutil,'which',return_value='/usr/bin/bwrap'),\
                    mock.patch.object(self.module.TerminalCancellation,'spawn',side_effect=KeyboardInterrupt):
                report=self.module.run_isolation_audit(source=ROOT,
                    node=Path(os.environ['P004B_TERMINAL_NODE']),module_root=Path(os.environ['P004B_TERMINAL_MODULE_ROOT']))
            self.assertFalse(owned.exists())
            self.assertEqual(report,{'reasonCode':'OFFLINE_PROBE_INTERRUPTED','disposableRootAbsent':True})

    def test_bad_paths_return_closed_result(self):
        report=self.module.run_isolation_audit(source=ROOT/'absent',node=Path('/absent'),module_root=Path('/absent'))
        self.assertEqual(report,{'reasonCode':'OFFLINE_PROBE_BLOCKED'})

    def test_namespace_launcher_signal_reaps_fake_child_before_disposal(self):
        for signum in (signal.SIGTERM,signal.SIGHUP):
            with tempfile.TemporaryDirectory(prefix='namespace-signal-fixture-') as directory:
                root=Path(directory); owned=root/'owned'; owned.mkdir(mode=0o700)
                pidfile=root/'child.pid'; fake=root/'fake-bwrap'; wrapper=root/'wrapper.py'
                fake.write_text('#!/usr/bin/python3\nimport os,time\nfrom pathlib import Path\n'
                    'Path('+repr(str(pidfile))+').write_text(str(os.getpid()))\ntime.sleep(60)\n')
                fake.chmod(0o700)
                wrapper.write_text('import importlib.util,json,sys\nfrom pathlib import Path\n'
                    'sys.path.insert(0,'+repr(str(ROOT/'tests'))+')\n'
                    'spec=importlib.util.spec_from_file_location("probe",'+repr(str(MODULE))+')\n'
                    'm=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)\n'
                    'm.shutil.which=lambda _name:'+repr(str(fake))+'\n'
                    'm.tempfile.mkdtemp=lambda **_kwargs:'+repr(str(owned))+'\n'
                    'report=m.run_isolation_audit(source=Path('+repr(str(ROOT))+'),'
                    'node=Path('+repr(os.environ['P004B_TERMINAL_NODE'])+'),'
                    'module_root=Path('+repr(os.environ['P004B_TERMINAL_MODULE_ROOT'])+'))\n'
                    'print(json.dumps(report),flush=True)\n')
                process=subprocess.Popen([sys.executable,str(wrapper)],stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,env={'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1'})
                pid=None
                try:
                    deadline=time.monotonic()+3
                    while not pidfile.exists() and process.poll() is None and time.monotonic()<deadline: time.sleep(.01)
                    self.assertTrue(pidfile.exists()); pid=int(pidfile.read_text())
                    os.kill(process.pid,signum)
                    stdout,_stderr=process.communicate(timeout=5)
                    self.assertEqual(process.returncode,0)
                    self.assertEqual(json.loads(stdout),{'reasonCode':'OFFLINE_PROBE_INTERRUPTED','disposableRootAbsent':True})
                    self.assertFalse(owned.exists())
                    self.assertFalse(Path(f'/proc/{pid}').exists(),'namespace child was not reaped')
                finally:
                    for target in (pid,process.pid):
                        if target is not None:
                            try: os.kill(target,signal.SIGKILL)
                            except ProcessLookupError: pass
                    process.communicate(timeout=2)

    def test_offline_namespace_mounts_owned_echo_module(self):
        commands=[]
        def spawn(command,**kwargs):
            commands.append(command)
            kwargs['stdout'].write(json.dumps({'networkIsolated':True,'operatorStateHidden':True,
                'capabilitiesDropped':True}).encode())
            value=mock.Mock(); value.poll.return_value=0; value.returncode=0
            return value
        with mock.patch.object(self.module.shutil,'which',return_value='/usr/bin/bwrap'),\
                mock.patch.object(self.module.TerminalCancellation,'spawn',side_effect=spawn):
            report=self.module.run_isolation_audit(source=ROOT,node=Path(os.environ['P004B_TERMINAL_NODE']),
                module_root=Path(os.environ['P004B_TERMINAL_MODULE_ROOT']))
        self.assertTrue(report['disposableRootAbsent'])
        command=commands[0]; target='/opt/probe/terminal_context_echo.py'
        self.assertIn(target,command)
        index=command.index(target)
        self.assertEqual(command[index-2:index+1],['--ro-bind',str(ROOT/'tests/terminal_context_echo.py'),target])
        self.assertNotIn('/opt/probe/claude',command)

    def test_numeric_module_is_read_only_mounted_and_importable(self):
        commands=[]
        original=self.module.TerminalCancellation.spawn
        def launch(token,command,**options):
            commands.append(command)
            return original(token,command,**options)
        with mock.patch.object(self.module.TerminalCancellation,'spawn',new=launch):
            audit=self.module.run_isolation_audit(source=ROOT,
                node=Path(os.environ['P004B_TERMINAL_NODE']),
                module_root=Path(os.environ['P004B_TERMINAL_MODULE_ROOT']))
        self.assertEqual(len(commands),1)
        command=commands[0]; target='/opt/probe/terminal_context_sample.py'
        self.assertIn(target,command,'shared numeric parser is missing from the isolated mount')
        index=command.index(target)
        self.assertEqual(command[index-2:index+1],
            ['--ro-bind',str(ROOT/'tests/terminal_context_sample.py'),target])
        self.assertNotIn('/opt/probe/claude',command)
        self.assertEqual(audit,{'networkIsolated':True,'operatorStateHidden':True,
            'capabilitiesDropped':True,'disposableRootAbsent':True})
        report=self.fake_report('success')
        self.assertEqual(report['reasonCode'],'OFFLINE_CONTROLS_PASSED')
        self.assertTrue(all(case['caseRootAbsent'] for case in report['cases']))

    def test_owned_echo_failure_stops_first_case_and_disposes(self):
        spec=importlib.util.spec_from_file_location('owned_echo_fixture',ROOT/'tests/test-headless-context-driver.py')
        fixture=importlib.util.module_from_spec(spec); spec.loader.exec_module(fixture)
        ui=fixture.HeadlessContextDriverTests('test_debug_selects_actual_unknown_row_not_owned_command_history')
        ui.setUp(); self.addCleanup(ui.doCleanups)
        calls=[]; sdk_calls=[]
        def case(name):
            calls.append(name)
            diagnostics=ui.run_pinned_probe('different-rejected-row-debug',debug=True)
            events=[json.loads(line) for line in (ui.root/'events').read_text().splitlines()]
            before=0 if events[-1]['outcome']=='passed' else 2
            if before==0: sdk_calls.append(name)
            report={'case':name,'beforeExit':before,'sdkExit':2,'afterExit':2,
                'stages':[{'phase':'before','events':events,'diagnostics':diagnostics}]}
            identity=ui.root.stat(); cleaned=self.module.finalize_owned(ui.root,identity,report)
            self.assertFalse(ui.root.exists()); self.assertTrue(cleaned.pop('disposableRootAbsent'))
            return {**cleaned,'caseRootAbsent':True}
        report=self.module.run_cases(case)
        self.assertEqual(calls,['text-turn']); self.assertEqual(sdk_calls,[])
        self.assertEqual(report['reasonCode'],'OFFLINE_CONTROLS_INCONCLUSIVE')
        self.assertNotIn('❯',json.dumps(report)); self.assertFalse(ui.root.exists())

    def test_owned_echo_complete_report_stays_bounded(self):
        from terminal_context_debug import fit_debug_report
        diagnostics=TerminalDiagnostics()
        for _ in range(100): diagnostics.add('failure','INPUT_PROBE_INELIGIBLE',
            inputEligibility='UNSUPPORTED_ROW',inputRowRelation='OTHER_CAPTURED_ROW',inputRowCause='UNRECOGNIZED_SHAPE')
        phase=diagnostics.report()
        self.assertLessEqual(len(phase['records']),16)
        self.assertLessEqual(len(json.dumps(phase,sort_keys=True).encode()),3072)
        base={'reasonCode':'OFFLINE_CONTROLS_INCONCLUSIVE','cases':[{'stages':[{'diagnostics':phase}]}]}
        report=fit_debug_report(base,{'status':'READY','excerpt':{'text':'x'*4096}})
        envelope={**report,'networkIsolated':True,'operatorStateHidden':True,
            'capabilitiesDropped':True,'disposableRootAbsent':True}
        self.assertLessEqual(len((json.dumps(envelope,sort_keys=True)+'\n').encode()),16384)

    def test_fresh_context_labels_survive_failed_stage_aggregation_without_authority(self):
        for check in ('FRESH_CONTEXT_FRAME_NOT_ADVANCED','FRESH_CONTEXT_SIGNATURE_UNCHANGED',
                'FRESH_CONTEXT_NUMERIC_UNAVAILABLE'):
            with self.subTest(check=check):
                diagnostics=TerminalDiagnostics()
                observation={'phase':'CONTEXT_PENDING','check':check,'commandBytesWritten':8,'enterBytesWritten':1}
                diagnostics.add('failure','INPUT_PROBE_STATE_REJECTED',contextCommandFailure=observation)
                for _ in range(100):
                    diagnostics.add('failure','INPUT_PROBE_STATE_REJECTED',contextCommandFailure=observation)
                phase=self.module.context_stage_report('after',[
                    {'stage':'context_inspected','outcome':'passed','percent':16,'private':'synthetic-private'}],diagnostics)
                self.assertEqual(phase['events'],[{'stage':'context_inspected','outcome':'passed','percent':16}])
                self.assertTrue(phase['diagnostics']['truncated'])
                self.assertFalse(phase['diagnostics']['rejected'])
                self.assertTrue(all(row['contextCommandFailure']==observation for row in phase['diagnostics']['records']))
                self.assertLessEqual(len(json.dumps(phase['diagnostics'],sort_keys=True).encode()),3072)
                case={'case':'text-turn','stages':[phase]}
                report=self.module._bounded_standard_report({'reasonCode':'OFFLINE_CONTROLS_INCONCLUSIVE',
                    'cases':[case,case]},2,reserve_disposal=True)
                encoded=(json.dumps({**report,'disposableRootAbsent':True},sort_keys=True)+'\n').encode()
                self.assertLessEqual(len(encoded),16384)
                self.assertNotIn(b'synthetic-private',encoded)
                self.assertEqual(json.loads(encoded)['cases'][0]['stages'][0],phase)
                self.assertFalse(self.module.case_complete(case))

    def test_observer_is_read_only_mounted_without_native_in_audit(self):
        commands=[]
        def capture(command,**kwargs):
            commands.append(command); raise KeyboardInterrupt
        with mock.patch.object(self.module.TerminalCancellation,'spawn',side_effect=capture),\
                mock.patch.object(self.module.shutil,'which',return_value='/usr/bin/bwrap'):
            report=self.module.run_isolation_audit(source=ROOT,
                node=Path(os.environ['P004B_TERMINAL_NODE']),module_root=Path(os.environ['P004B_TERMINAL_MODULE_ROOT']))
        self.assertEqual(report,{'reasonCode':'OFFLINE_PROBE_INTERRUPTED','disposableRootAbsent':True})
        command=commands[0]; index=command.index('/opt/probe/terminal_context_diagnostics.py')
        self.assertEqual(command[index-2:index],['--ro-bind',str(ROOT/'tests/terminal_context_diagnostics.py')])
        self.assertNotIn('/opt/probe/claude',command)

    def test_four_observer_phases_with_debug_stay_bounded(self):
        from terminal_context_debug import fit_debug_report
        diagnostics=TerminalDiagnostics()
        structure={'buffer':'normal','cursorX':120,'cursorY':39,'baseY':1000,'viewportY':1000,
            'candidateCount':40,'inputFresh':True,'contextFresh':True,'locationFresh':True,
            'authentication':'NONE','readiness':'FRESHNESS_UNPROVEN'}
        observation={'phase':'COMMAND_ECHO_MATCHED','check':'NORMALIZED_ELIGIBILITY',
            'commandBytesWritten':8,'enterBytesWritten':0}
        for _ in range(100): diagnostics.add('failure','INPUT_PROBE_REVOKED',structure=structure,
            contextCommandFailure=observation,normalizedInputFailure={'reason':'UNSUPPORTED_ROW',
                'rowRelation':'CURSOR_OUTSIDE_CAPTURE','rowCause':'UNSUPPORTED_WHITESPACE'})
        phase=diagnostics.report()
        self.assertLessEqual(len(json.dumps(phase,sort_keys=True).encode()),3072)
        self.assertTrue(phase['truncated']); self.assertFalse(phase['rejected'])
        self.assertTrue(all('normalizedInputFailure' in row for row in phase['records']))
        base={'reasonCode':'OFFLINE_CONTROLS_INCONCLUSIVE','cases':[{
            'stages':[{'diagnostics':phase} for _ in range(2)]} for _ in range(2)]}
        report=fit_debug_report(base,{'status':'READY','excerpt':{'text':'x'*4096}})
        envelope={**report,'networkIsolated':True,'operatorStateHidden':True,
            'capabilitiesDropped':True,'disposableRootAbsent':True}
        self.assertLessEqual(len((json.dumps(envelope,sort_keys=True)+'\n').encode()),16384)
        self.assertEqual(report['reasonCode'],'OFFLINE_CONTROLS_INCONCLUSIVE')


class OfflineFailureDiagnosticsTests(unittest.TestCase):
    setUp=OfflineTerminalResumeSafetyTests.setUp
    fake_report=OfflineTerminalResumeSafetyTests.fake_report

    def outer_peer(self,body,*,error=None,expired=False,cancel=False,**flags):
        with tempfile.TemporaryDirectory(prefix='offline-failure-peer-') as directory:
            peer=Path(directory)/'peer'
            peer.write_text('#!/usr/bin/python3 -I\nimport os,signal\n'+body+'\n')
            peer.chmod(0o700)
            original=self.module.TerminalCancellation.spawn; launches=[]
            clock=time.monotonic; offset=[0]
            def spawn(token,command,**options):
                launches.append(command)
                if error is not None: raise error
                child=original(token,command,**options)
                if expired: offset[0]=1000
                if cancel: token.requested=True
                return child
            with mock.patch.object(self.module.shutil,'which',return_value=str(peer)),\
                    mock.patch.object(self.module.TerminalCancellation,'spawn',new=spawn),\
                    mock.patch.object(self.module.time,'monotonic',side_effect=lambda:clock()+offset[0]):
                result=self.module.run_offline_controls(source=ROOT,claude=peer,
                    node=Path(os.environ['P004B_TERMINAL_NODE']),
                    module_root=Path(os.environ['P004B_TERMINAL_MODULE_ROOT']),**flags)
            self.assertEqual(len(launches),1)
        self.assertTrue(result['disposableRootAbsent'])
        self.assertLessEqual(len((json.dumps(result)+'\n').encode()),16384)
        return result

    def test_nonzero_namespace_exit_preserves_code_without_raw_output(self):
        report=self.outer_peer('os.write(1,b"synthetic-private-output"); raise SystemExit(7)')
        self.assertEqual(report.get('failureDiagnostic'),{'phase':'NAMESPACE','exitCode':7,
            'signal':None,'exceptionClass':None,'errno':None})
        self.assertEqual(report['reasonCode'],'OFFLINE_PROBE_BLOCKED')
        self.assertNotIn('synthetic-private-output',json.dumps(report))

    def test_target_signal_is_not_invented_after_supervisor_normalization(self):
        report=self.outer_peer('os.kill(os.getpid(),signal.SIGTERM)')
        # The existing owned supervisor maps negative target returns to 2.
        # Its observable exit is not evidence of the target's original signal.
        self.assertEqual(report.get('failureDiagnostic'),{'phase':'NAMESPACE','exitCode':2,
            'signal':None,'exceptionClass':None,'errno':None})

    def test_supervisor_exit_during_proc_read_preserves_actual_result(self):
        for exit_code in (0,7):
            with self.subTest(exit_code=exit_code),tempfile.TemporaryDirectory(prefix='offline-proc-race-') as directory:
                peer=Path(directory)/'peer'; release=Path(directory)/'release'
                payload={'reasonCode':'OFFLINE_CONTROLS_INCONCLUSIVE','cases':[]}
                peer.write_text('#!/usr/bin/python3 -I\nimport os,time\nfrom pathlib import Path\n'
                    'print('+repr(json.dumps(payload))+',flush=True)\n'
                    'deadline=time.monotonic()+10\n'
                    'while not Path('+repr(str(release))+').exists():\n'
                    '    if time.monotonic()>=deadline: raise SystemExit(2)\n'
                    '    time.sleep(.005)\nraise SystemExit('+str(exit_code)+')\n')
                peer.chmod(0o700)
                original_open=Path.open; original_spawn=self.module.TerminalCancellation.spawn
                state={'process':None,'opened':False,'launches':0}
                def spawn(token,command,**options):
                    state['launches']+=1
                    state['process']=original_spawn(token,command,**options)
                    return state['process']
                def open_then_release(path,*args,**kwargs):
                    stream=original_open(path,*args,**kwargs)
                    process=state['process']
                    if (process is not None and path==Path(f'/proc/{process.pid}/stat') and not state['opened']):
                        state['opened']=True; release.touch()
                        self.assertEqual(process.wait(timeout=3),exit_code)
                    return stream
                with mock.patch.object(self.module.shutil,'which',return_value=str(peer)),\
                        mock.patch.object(self.module.TerminalCancellation,'spawn',new=spawn),\
                        mock.patch.object(Path,'open',new=open_then_release):
                    report=self.module.run_offline_controls(source=ROOT,claude=peer,
                        node=Path(os.environ['P004B_TERMINAL_NODE']),
                        module_root=Path(os.environ['P004B_TERMINAL_MODULE_ROOT']))
                self.assertTrue(state['opened']); self.assertEqual(state['launches'],1)
                self.assertTrue(report['disposableRootAbsent'])
                if exit_code==0: self.assertEqual(report,{**payload,'disposableRootAbsent':True})
                else:
                    self.assertEqual(report['reasonCode'],'OFFLINE_PROBE_BLOCKED')
                    self.assertEqual(report['failureDiagnostic'],{'phase':'NAMESPACE','exitCode':7,
                        'signal':None,'exceptionClass':None,'errno':None})
                    self.assertNotIn('cases',report)

    def test_launch_exception_exports_only_closed_class_and_errno(self):
        error=PermissionError(13,'synthetic-private-message','/synthetic-private-path')
        report=self.outer_peer('',error=error)
        self.assertEqual(report.get('failureDiagnostic'),{'phase':'NAMESPACE','exitCode':None,
            'signal':None,'exceptionClass':'PermissionError','errno':13})
        self.assertNotIn('synthetic-private',json.dumps(report))

    def test_invalid_and_oversized_json_are_bounded_namespace_failures(self):
        for body,kind in (('os.write(1,b"synthetic-invalid-json")','JSONDecodeError'),
                          ('os.write(1,b"x"*16385)','ValueError')):
            with self.subTest(kind=kind):
                report=self.outer_peer(body)
                self.assertEqual(report.get('failureDiagnostic'),{'phase':'NAMESPACE','exitCode':0,
                    'signal':None,'exceptionClass':kind,'errno':None})
                self.assertNotIn('synthetic-invalid-json',json.dumps(report))

    def test_serialized_diagnostic_cannot_change_failure_or_leak_unknown_fields(self):
        for diagnostic,want in (({'phase':'VERSION','exitCode':None,'signal':None,
                'exceptionClass':'FileNotFoundError','errno':2},'VERSION'),
                ({'phase':'synthetic-private-phase','exitCode':0,'signal':None,
                  'exceptionClass':'synthetic-private-class','errno':True},'NAMESPACE')):
            payload={'reasonCode':'OFFLINE_CONTROLS_PASSED','cases':[], 'failureDiagnostic':diagnostic}
            report=self.outer_peer('os.write(1,'+repr(json.dumps(payload).encode())+'); raise SystemExit(2)')
            self.assertEqual(report['reasonCode'],'OFFLINE_PROBE_BLOCKED')
            self.assertNotIn('cases',report)
            self.assertEqual(report.get('failureDiagnostic',{}).get('phase'),want)
            self.assertNotIn('synthetic-private',json.dumps(report))

    def test_missing_runtime_is_a_precheck_failure(self):
        report=self.module.run_offline_controls(source=ROOT,claude=Path('/unopened-native'),
            node=Path('/missing-synthetic-node'),module_root=Path(os.environ['P004B_TERMINAL_MODULE_ROOT']))
        self.assertEqual(report.get('failureDiagnostic'),{'phase':'PRECHECK','exitCode':None,
            'signal':None,'exceptionClass':'FileNotFoundError','errno':2})

    def test_debug_route_keeps_legacy_failure_envelope(self):
        report=self.outer_peer('raise SystemExit(7)',debug_context=True)
        self.assertEqual(report,{'reasonCode':'OFFLINE_PROBE_BLOCKED','disposableRootAbsent':True})

    def inner_peer(self,body,*,executable=True,node=None):
        with tempfile.TemporaryDirectory(prefix='offline-version-peer-') as directory:
            peer=Path(directory)/'peer'
            peer.write_text('#!/usr/bin/python3 -I\nimport os,signal,sys,time\n'+body+'\n')
            peer.chmod(0o700 if executable else 0o600)
            return self.module.run_offline_controls(source=ROOT,claude=peer,
                node=Path(node or os.environ['P004B_TERMINAL_NODE']),
                module_root=Path(os.environ['P004B_TERMINAL_MODULE_ROOT']))

    def test_version_exec_error_survives_the_nonzero_namespace_result(self):
        report=self.inner_peer('',executable=False)
        self.assertEqual(report.get('failureDiagnostic'),{'phase':'VERSION','exitCode':None,
            'signal':None,'exceptionClass':'PermissionError','errno':13})
        self.assertEqual(report['reasonCode'],'OFFLINE_PROBE_BLOCKED')
        self.assertTrue(report['disposableRootAbsent'])

    def test_version_signal_and_timeout_do_not_require_raw_stderr(self):
        for body,exit_code,kind in (('os.kill(os.getpid(),signal.SIGTERM)',-15,None),
                                   ('time.sleep(60)',None,'TimeoutExpired')):
            with self.subTest(kind=kind):
                report=self.inner_peer(body)
                self.assertEqual(report.get('failureDiagnostic'),{'phase':'VERSION','exitCode':exit_code,
                    'signal':15 if exit_code==-15 else None,'exceptionClass':kind,'errno':None})
                self.assertNotIn('runtime',report)

    def test_initial_context_failure_retains_original_inconclusive_decision(self):
        report=self.inner_peer('print("0.0.1 (Claude Code)")',node='/usr/bin/false')
        self.assertEqual(report['reasonCode'],'OFFLINE_CONTROLS_INCONCLUSIVE')
        case=report['cases'][0]
        self.assertEqual(case.get('failureDiagnostic'),{'phase':'INITIAL_CONTEXT','exitCode':None,
            'signal':None,'exceptionClass':'RuntimeError','errno':None})
        self.assertTrue(case['caseRootAbsent']); self.assertEqual(len(report['cases']),1)

    def test_sdk_and_resume_failures_name_the_actual_phase(self):
        for mode,phase,exit_code in (('wrong-session','SDK',0),('view-loss','RESUMED_CONTEXT',None)):
            with self.subTest(mode=mode):
                report=self.fake_report(mode)
                self.assertEqual(report['reasonCode'],'OFFLINE_CONTROLS_INCONCLUSIVE')
                self.assertEqual(report['cases'][0].get('failureDiagnostic'),{'phase':phase,
                    'exitCode':exit_code,'signal':None,'exceptionClass':None,'errno':None})

    def test_success_has_no_failure_metadata(self):
        report=self.fake_report('success')
        self.assertNotIn('failureDiagnostic',report)
        self.assertTrue(all('failureDiagnostic' not in case for case in report['cases']))

    def test_cleanup_failure_is_not_mislabeled_as_sdk_failure(self):
        report=self.fake_report('cleanup-failure')
        self.assertEqual(report['cases'][0].get('failureDiagnostic'),{'phase':'CLEANUP','exitCode':None,
            'signal':None,'exceptionClass':None,'errno':None})

    def test_unknown_exception_never_exports_its_name_or_message(self):
        error=type('SyntheticPrivateClass',(Exception,),{} )('synthetic-private-message')
        with mock.patch.object(sys,'argv',[str(MODULE),'--inner-controls']),\
                mock.patch.object(self.module,'_audit',return_value={}),\
                mock.patch.object(self.module,'_controls',side_effect=error),\
                mock.patch('builtins.print') as output:
            self.assertEqual(self.module.main(),2)
        report=json.loads(output.call_args.args[0])
        self.assertEqual(report.get('failureDiagnostic'),{'phase':'UNKNOWN','exitCode':None,
            'signal':None,'exceptionClass':'OTHER','errno':None})
        self.assertNotIn('synthetic-private',json.dumps(report).lower())

    def test_import_failure_is_not_lost_before_version(self):
        import builtins
        original=builtins.__import__
        def imports(name,*args,**kwargs):
            if name=='headless_context_driver': raise ImportError('synthetic-private-import')
            return original(name,*args,**kwargs)
        with mock.patch.object(sys,'argv',[str(MODULE),'--inner-controls']),\
                mock.patch.object(sys,'path',list(sys.path)),\
                mock.patch.object(self.module,'_audit',return_value={}),\
                mock.patch.object(builtins,'__import__',side_effect=imports),\
                mock.patch('builtins.print') as output:
            self.assertEqual(self.module.main(),2)
        report=json.loads(output.call_args.args[0])
        self.assertEqual(report.get('failureDiagnostic'),{'phase':'IMPORTS','exitCode':None,
            'signal':None,'exceptionClass':'ImportError','errno':None})
        self.assertNotIn('synthetic-private',json.dumps(report))

    def test_forged_diagnostic_types_are_not_exported(self):
        base={'phase':'VERSION','exitCode':None,'signal':None,'exceptionClass':None,'errno':None}
        for key,value in (('exitCode',True),('signal',True),('errno',True),('errno',5000),
                          ('exceptionClass',[]),('phase',[]),('unapproved','synthetic-private')):
            with self.subTest(key=key,value=value):
                payload={'reasonCode':'OFFLINE_PROBE_BLOCKED','failureDiagnostic':{**base,key:value}}
                report=self.outer_peer('os.write(1,'+repr(json.dumps(payload).encode())+'); raise SystemExit(2)')
                self.assertEqual(report.get('failureDiagnostic'),{'phase':'NAMESPACE','exitCode':2,
                    'signal':None,'exceptionClass':None,'errno':None})

    def test_missing_native_argument_is_diagnosed_without_launch(self):
        report=self.module.run_offline_controls(source=ROOT,claude=None,
            node=Path(os.environ['P004B_TERMINAL_NODE']),module_root=Path(os.environ['P004B_TERMINAL_MODULE_ROOT']))
        self.assertEqual(report.get('failureDiagnostic'),{'phase':'PRECHECK','exitCode':None,
            'signal':None,'exceptionClass':None,'errno':None})

    def test_outer_timeout_and_interruption_do_not_relaunch(self):
        for flags,reason,kind in (({'expired':True},'OFFLINE_PROBE_BLOCKED','TimeoutError'),
                                  ({'cancel':True},'OFFLINE_PROBE_INTERRUPTED','RuntimeError')):
            with self.subTest(flags=flags):
                report=self.outer_peer('import time; time.sleep(60)',**flags)
                self.assertEqual(report['reasonCode'],reason)
                self.assertEqual(report.get('failureDiagnostic'),{'phase':'NAMESPACE','exitCode':None,
                    'signal':None,'exceptionClass':kind,'errno':None})

    def test_final_envelope_budget_includes_disposal_receipt(self):
        payload={'reasonCode':'OFFLINE_PROBE_BLOCKED','padding':''}
        payload['padding']='x'*(16384-len(json.dumps(payload).encode()))
        self.assertEqual(len(json.dumps(payload).encode()),16384)
        report=self.outer_peer('os.write(1,'+repr(json.dumps(payload).encode())+')')
        self.assertEqual(report['reasonCode'],'OFFLINE_PROBE_BLOCKED')
        self.assertNotIn('padding',report)

    def test_optional_diagnostic_is_omitted_before_rejecting_a_bounded_envelope(self):
        detail={'phase':'VERSION','exitCode':7,'signal':None,'exceptionClass':None,'errno':None}
        payload={'reasonCode':'OFFLINE_CONTROLS_INCONCLUSIVE','padding':'','failureDiagnostic':detail}
        payload['padding']='x'*(16384-len(json.dumps(payload).encode()))
        report=self.outer_peer('os.write(1,'+repr(json.dumps(payload).encode())+')')
        self.assertEqual(report['reasonCode'],'OFFLINE_CONTROLS_INCONCLUSIVE')
        self.assertNotIn('failureDiagnostic',report)

    def test_nested_unknown_metadata_is_never_exported(self):
        payload={'reasonCode':'OFFLINE_CONTROLS_INCONCLUSIVE','cases':[{'case':'text-turn',
            'failureDiagnostic':{'phase':'synthetic-private-phase'}}]}
        report=self.outer_peer('os.write(1,'+repr(json.dumps(payload).encode())+')')
        self.assertNotIn('synthetic-private',json.dumps(report))

    def test_inner_budget_drops_optional_metadata_before_transport_rejection(self):
        import copy
        detail={'phase':'VERSION','exitCode':7,'signal':None,'exceptionClass':None,'errno':None}
        for location in ('envelope','case'):
            with self.subTest(location=location):
                payload={'reasonCode':'OFFLINE_CONTROLS_INCONCLUSIVE',
                    'cases':[{'case':'text-turn'}],'padding':''}
                final={**payload,'disposableRootAbsent':True}
                payload['padding']='x'*(16380-len((json.dumps(final,sort_keys=True)+'\n').encode()))
                original=copy.deepcopy(payload)
                (payload if location=='envelope' else payload['cases'][0])['failureDiagnostic']=detail
                with mock.patch.object(sys,'argv',[str(MODULE),'--inner-controls']),\
                        mock.patch.object(self.module,'_audit',return_value={}),\
                        mock.patch.object(self.module,'_controls',return_value=payload),\
                        mock.patch('builtins.print') as output:
                    self.assertEqual(self.module.main(),0)
                wire=(output.call_args.args[0]+'\n').encode()
                self.assertLessEqual(len(wire),16384)
                report=self.outer_peer('os.write(1,'+repr(wire)+')')
                self.assertEqual(report,{**original,'disposableRootAbsent':True})

    def test_success_envelope_never_exports_failure_metadata(self):
        detail={'phase':'VERSION','exitCode':7,'signal':None,'exceptionClass':None,'errno':None}
        payload={'reasonCode':'OFFLINE_CONTROLS_PASSED','cases':[], 'failureDiagnostic':detail}
        report=self.outer_peer('os.write(1,'+repr(json.dumps(payload).encode())+')')
        self.assertNotIn('failureDiagnostic',report)

    def test_nonobject_json_is_a_structural_failure_not_an_uncaught_exception(self):
        for value in ([],None,13,'synthetic-private-output'):
            with self.subTest(type=type(value).__name__):
                report=self.outer_peer('os.write(1,'+repr(json.dumps(value).encode())+')')
                self.assertEqual(report.get('failureDiagnostic'),{'phase':'NAMESPACE','exitCode':0,
                    'signal':None,'exceptionClass':'ValueError','errno':None})
                self.assertNotIn('synthetic-private',json.dumps(report))

    def test_unexpected_case_exception_survives_real_namespace_transport(self):
        code=('import sys\nsys.path.insert(0,"/opt/probe")\n'
            'import probe,terminal_state_adapter\n'
            'def failure(*args,**kwargs): raise TypeError("synthetic-private-failure")\n'
            'terminal_state_adapter.TerminalState=failure\n'
            'sys.argv=["/opt/probe/probe.py","--inner-controls"]\n'
            'raise SystemExit(probe.main())\n')
        original=self.module.TerminalCancellation.spawn; calls=[]
        def launch(token,command,**options):
            self.assertEqual(command[-2:],['/opt/probe/probe.py','--inner-controls'])
            calls.append(command)
            return original(token,command[:-2]+['-c',code],**options)
        with mock.patch.object(self.module.TerminalCancellation,'spawn',new=launch):
            report=self.inner_peer('print("0.0.1 (Claude Code)")')
        self.assertEqual(len(calls),1)
        self.assertEqual(report['reasonCode'],'OFFLINE_PROBE_BLOCKED')
        self.assertEqual(report.get('failureDiagnostic'),{'phase':'INITIAL_CONTEXT','exitCode':None,
            'signal':None,'exceptionClass':'TypeError','errno':None})
        self.assertTrue(report['disposableRootAbsent'])
        self.assertNotIn('synthetic-private',json.dumps(report))


if __name__=='__main__': unittest.main()
