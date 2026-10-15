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
            'naturalExit':True,'caseRootAbsent':True,'skillCalls':1,'validSkillSample':True}
        self.assertTrue(self.module.case_complete(case))
        for field,value in [('afterExit',2),('contextInspected',False),('naturalExit',False),
                            ('caseRootAbsent',False),('validSkillSample',False),('skillCalls',0)]:
            changed={**case,field:value}
            self.assertFalse(self.module.case_complete(changed))

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
        with mock.patch.object(self.module.TerminalCancellation,'spawn',side_effect=AssertionError('launched')),\
                mock.patch.object(self.module.tempfile,'TemporaryFile',side_effect=AssertionError('report file')):
            result=self.module.run_offline_controls(source=ROOT,claude=Path('/unopened-native'),
                node=Path(os.environ['P004B_TERMINAL_NODE']),
                module_root=Path(os.environ['P004B_TERMINAL_MODULE_ROOT']),debug_context_edit=True)
        self.assertEqual(result,{'reasonCode':'OFFLINE_PROBE_BLOCKED'})

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
                'validSkillSample':True,'skillCalls':1}
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
                self.assertEqual(json.loads(output.call_args.args[0]),{'reasonCode':'OFFLINE_PROBE_BLOCKED'})

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


if __name__=='__main__': unittest.main()
