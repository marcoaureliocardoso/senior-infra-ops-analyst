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

    def test_no_live_mode_or_retry_authority(self):
        self.assertEqual(self.module.validate_mode(['--run-live']),False)
        self.assertEqual(self.module.validate_mode(['--repeat']),False)
        self.assertEqual(self.module.validate_mode(['--run-offline']),True)
        self.assertEqual(self.module.validate_mode(['--audit-isolation']),True)

    def test_stops_at_first_failed_case_without_retry(self):
        calls=[]
        def failed(name):
            calls.append(name)
            return {'case':name,'afterExit':2,'caseRootAbsent':True}
        report=self.module.run_cases(failed)
        self.assertEqual(calls,['text-turn'])
        self.assertEqual(report['reasonCode'],'OFFLINE_CONTROLS_INCONCLUSIVE')
        self.assertEqual(len(report['cases']),1)

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


if __name__=='__main__': unittest.main()
