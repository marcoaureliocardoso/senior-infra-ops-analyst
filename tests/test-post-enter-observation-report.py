"""Closed structural observation summaries; no native/provider IO."""
import copy
import json
import unittest
import importlib.util
import os
from pathlib import Path
import tempfile
import sys
import time
import contextlib
import io
from unittest import mock
import terminal_post_enter_observation as observation
from post_enter_observation_fixtures import ObservationCase
import terminal_resume_history as history


class ObservationSummaryTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(callable(getattr(observation,'valid_observation_summary',None)),
            'closed observation summary validator is absent')

    def test_summary_rejects_unknown_keys_enums_and_wrong_types(self):
        valid={'outcome':'UNSUPPORTED_TRANSITION','stopCategory':'UNKNOWN_ROW','profileObserved':False}
        self.assertTrue(observation.valid_observation_summary(valid))
        for fields in ({'raw':'Synthetic contents'},{'menuState':'new text'},
                {'profileObserved':0},{'outcome':'arbitrary'},{'stopCategory':True},
                {'profileObserved':True}):
            with self.subTest(fields=fields):
                self.assertFalse(observation.valid_observation_summary({**valid,**fields}))

    def test_only_completed_closed_summary_can_be_taken_once(self):
        with ObservationCase() as c:
            c.submit(); self.assertIsNone(history.take_post_enter_result(c.request))
            frame=c.snapshot(commit=20); c.observer.observe(frame,3); c.observer.complete(frame,3)
            c.observer.close(); result=history.take_post_enter_result(c.request)
            self.assertTrue(observation.valid_observation_summary(result))
            result['outcome']='Injected value'
            self.assertEqual(c.observer.summary()['outcome'],'CURRENT_PROFILE_OBSERVED')
            self.assertIsNone(history.take_post_enter_result(c.request))
            rendered=json.dumps(c.observer.summary())
            for forbidden in ('/context','Synthetic','snapshot','deadline','scope','row'):
                self.assertNotIn(forbidden,rendered)
            self.assertEqual(set(observation._OBSERVATIONS[c.observer]),{'phase','closed','summary'})

    def test_positive_summary_requires_complete_coherent_profile(self):
        valid={'outcome':'CURRENT_PROFILE_OBSERVED','stopCategory':'COMPLETE','profileObserved':True,
            'menuState':'DISAPPEARED','inputState':'EMPTY','commitRelation':'NEW_CELL',
            'numericRelation':'BASELINE_EQUIVALENT'}
        self.assertTrue(observation.valid_observation_summary(valid))
        for key,value in (('stopCategory','AUTHENTICATION'),('menuState','EXACT_PRESENT'),
                ('inputState','OWNED_COMMAND_ECHO'),('commitRelation','PREENTER_INVENTORY'),
                ('numericRelation','CONFLICT')):
            with self.subTest(key=key):
                self.assertFalse(observation.valid_observation_summary({**valid,key:value}))
        self.assertFalse(observation.valid_observation_summary({key:value for key,value in valid.items() if key!='inputState'}))

    def test_stop_cannot_fabricate_positive_result_or_restore_failure(self):
        with ObservationCase() as c:
            c.submit()
            with self.assertRaises(RuntimeError): c.observer.stop('CURRENT_PROFILE_OBSERVED','COMPLETE')
            c.observer.stop('DEADLINE','DEADLINE'); original=c.observer.summary()
            c.observer.stop('SAFETY_STOP','OWNER_LOST')
            self.assertEqual(c.observer.summary(),original)


ROOT=Path(__file__).resolve().parents[1]


def current_report():
    return {'schema':'p004b-post-enter-observation-v1','mode':'observe-post-enter','acceptance':False,
        'outcome':'CURRENT_PROFILE_OBSERVED','stopCategory':'COMPLETE',
        'setup':{'initialCompleted':True,'sdkValidated':True},
        'cleanup':{'nativeReaped':True,'helperReaped':True,'caseRootAbsent':True,'disposableRootAbsent':True},
        'summary':{'outcome':'CURRENT_PROFILE_OBSERVED','stopCategory':'COMPLETE','profileObserved':True,
            'menuState':'DISAPPEARED','inputState':'EMPTY','commitRelation':'NEW_CELL',
            'numericRelation':'BASELINE_EQUIVALENT'}}


class OfflineObservationReportTests(unittest.TestCase):
    def setUp(self):
        spec=importlib.util.spec_from_file_location('offline_observation',ROOT/'tests/offline-terminal-resume-probe.py')
        self.module=importlib.util.module_from_spec(spec); spec.loader.exec_module(self.module)
        self.assertTrue(callable(getattr(self.module,'run_post_enter_observation',None)),
            'isolated observation mode is absent')

    def test_closed_report_requires_coherent_proof_and_actual_parent_disposal(self):
        report=current_report()
        self.assertTrue(self.module.valid_post_enter_report(report))
        self.assertEqual(self.module.post_enter_exit_code(report),0)
        report['cleanup']['disposableRootAbsent']=False
        self.assertEqual(self.module.post_enter_exit_code(report),2)
        for mutate in (lambda r:r.update(raw='Synthetic private text'),
                lambda r:r.update(acceptance=True),lambda r:r['setup'].update(sdkValidated=1),
                lambda r:r['summary'].update(commitRelation='PREENTER_INVENTORY'),
                lambda r:r['cleanup'].update(nativeReaped=False)):
            with self.subTest(mutate=mutate):
                changed=current_report(); mutate(changed)
                self.assertFalse(self.module.valid_post_enter_report(changed))

    def test_optional_projection_fault_withholds_positive_without_losing_cleanup(self):
        report=current_report(); report['summary']={'raw':'Synthetic private text'*10000}
        fitted=self.module.fit_post_enter_report(report,reserve_disposal=True)
        self.assertTrue(self.module.valid_post_enter_report(fitted))
        self.assertNotIn('summary',fitted)
        self.assertEqual(fitted['cleanup'],report['cleanup'])
        self.assertEqual(self.module.post_enter_exit_code(fitted),2)
        self.assertLessEqual(len((json.dumps(fitted,sort_keys=True)+'\n').encode()),16384)
        self.assertNotIn('Synthetic',json.dumps(fitted))

    def test_observation_schema_cannot_be_promoted_by_legacy_proof_fields(self):
        # Exercise the real acceptance consumer with otherwise valid fixture proofs.
        spec=importlib.util.spec_from_file_location('offline_safety_fixtures',ROOT/'tests/test-offline-terminal-resume-safety.py')
        helper=importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
        legacy={'case':'text-turn','beforeExit':0,'sdkExit':0,'afterExit':0,'contextInspected':True,
            'naturalExit':True,'caseRootAbsent':True,'validSDKSample':True,'skillCalls':0,'stages':helper.passed_stages()}
        self.assertTrue(self.module.case_complete(legacy))
        self.assertFalse(self.module.case_complete({**legacy,'schema':'p004b-post-enter-observation-v1','acceptance':False}))

    def test_mode_is_exclusive_and_missing_runtime_never_launches(self):
        self.assertTrue(self.module.validate_mode(['--observe-post-enter']))
        for args in (['--observe-post-enter']*2,['--run-offline','--observe-post-enter'],
                ['--observe-post-enter','--debug-context'],['--observe-post-enter','--debug-context-edit'],
                ['--audit-isolation','--observe-post-enter']):
            self.assertFalse(self.module.validate_mode(args))
        with mock.patch.object(self.module,'_namespace',side_effect=AssertionError('namespace attempted')):
            report=self.module.run_post_enter_observation(source=ROOT,claude=None,
                node=Path('/unresolved-helper'),module_root=Path('/unresolved-modules'))
        self.assertEqual(report['outcome'],'SETUP_BLOCKED')
        self.assertEqual(self.module.post_enter_exit_code(report),2)

    def test_real_namespace_only_runs_one_synthetic_text_case(self):
        from resume_history_fixtures import write_fake_cli
        with tempfile.TemporaryDirectory() as directory:
            fake=Path(directory)/'synthetic-cli'; write_fake_cli(fake,mode='equal-values'); fake.chmod(0o700)
            report=self.module.run_post_enter_observation(source=ROOT,claude=fake,
                node=Path(os.environ['P004B_TERMINAL_NODE']),module_root=Path(os.environ['P004B_TERMINAL_MODULE_ROOT']))
        self.assertEqual(report['outcome'],'CURRENT_PROFILE_OBSERVED',report)
        self.assertEqual(self.module.post_enter_exit_code(report),0)
        self.assertIs(report['acceptance'],False)
        self.assertFalse(self.module.case_complete(report))
        self.assertEqual(report['setup'],{'initialCompleted':True,'sdkValidated':True})
        self.assertTrue(all(report['cleanup'].values()))
        for raw in ('cases','runtime','messages','stages','session','prompt','coordinates','stream'):
            self.assertNotIn(raw,json.dumps(report))

    def test_bounded_pipe_reaps_oversized_child_before_disposal(self):
        self.assertTrue(callable(getattr(self.module,'_post_enter_namespace_report',None)),
            'bounded observation namespace transport is absent')
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/'owned'; root.mkdir(mode=0o700)
            pidfile=Path(directory)/'synthetic-child.pid'
            code='import os,time; from pathlib import Path; Path('+repr(str(pidfile))+').write_text(str(os.getpid())); os.write(1,b"X"*20000); time.sleep(60)'
            started=time.monotonic()
            report=self.module._post_enter_namespace_report([sys.executable,'-c',code],root,root.stat())
            self.assertLess(time.monotonic()-started,4)
            self.assertFalse(root.exists())
            self.assertFalse(Path('/proc/'+pidfile.read_text()).exists())
        self.assertEqual(self.module.post_enter_exit_code(report),2)
        self.assertTrue(report['cleanup']['disposableRootAbsent'])
        self.assertNotIn('summary',report)

    def test_nonzero_forged_duplicate_or_truncated_child_cannot_publish_positive(self):
        value=current_report(); value['cleanup']['disposableRootAbsent']=False
        valid=json.dumps(value)
        for payload,code in ((valid,2),(valid[:-1],0),('[1,2]',0),
                (valid[:-1]+',"acceptance":true}',0)):
            with self.subTest(code=code,payload=payload[:10]),tempfile.TemporaryDirectory() as directory:
                root=Path(directory)/'owned'; root.mkdir(mode=0o700)
                script='import os,sys; os.write(1,'+repr(payload.encode())+'); sys.exit('+str(code)+')'
                report=self.module._post_enter_namespace_report([sys.executable,'-c',script],root,root.stat())
                self.assertEqual(self.module.post_enter_exit_code(report),2)
                self.assertNotIn('summary',report)
                self.assertFalse(root.exists())
                self.assertTrue(report['cleanup']['disposableRootAbsent'])

    def test_cleanup_failure_suppresses_detail_and_no_output_precedes_disposal(self):
        value=current_report(); value['cleanup']['disposableRootAbsent']=False
        script='import os; os.write(1,'+repr(json.dumps(value).encode())+')'
        for fail in (False,True):
            with self.subTest(fail=fail),tempfile.TemporaryDirectory() as directory:
                root=Path(directory)/'owned'; root.mkdir(mode=0o700); identity=root.stat()
                output=io.StringIO(); actual=self.module.finalize_owned
                def dispose(path,owned,report):
                    self.assertEqual(output.getvalue(),'')
                    if fail: return {'reasonCode':'OFFLINE_CLEANUP_FAILED'}
                    return actual(path,owned,report)
                with contextlib.redirect_stdout(output),mock.patch.object(self.module,'finalize_owned',side_effect=dispose):
                    report=self.module._post_enter_namespace_report([sys.executable,'-c',script],root,identity)
                self.assertEqual(self.module.post_enter_exit_code(report),2 if fail else 0)
                if fail:
                    self.assertEqual(report['outcome'],'CLEANUP_FAILED')
                    self.assertNotIn('summary',report)

    def test_root_substitution_withholds_disposal_and_observation(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/'owned'; root.mkdir(mode=0o700); identity=root.stat()
            script=('from pathlib import Path; p=Path('+repr(str(root))+'); '
                'p.rename(p.with_name("moved")); p.mkdir(mode=0o700)')
            report=self.module._post_enter_namespace_report([sys.executable,'-c',script],root,identity)
        self.assertEqual(report['outcome'],'CLEANUP_FAILED')
        self.assertIs(report['cleanup']['disposableRootAbsent'],False)
        self.assertNotIn('summary',report)

    def test_inner_host_entry_and_mixed_cli_modes_never_reach_controls(self):
        common=['--source',str(ROOT),'--node',os.environ['P004B_TERMINAL_NODE'],
            '--module-root',os.environ['P004B_TERMINAL_MODULE_ROOT']]
        for options in (['--observe-post-enter']*2,['--observe-post-enter','--debug-context'],
                ['--observe-post-enter','--debug-context-edit'],['--observe-post-enter','--run-offline']):
            with self.subTest(options=options),mock.patch.object(sys,'argv',['probe',*options,*common]),\
                    contextlib.redirect_stderr(io.StringIO()),mock.patch.object(self.module,'run_post_enter_observation') as run:
                with self.assertRaises(SystemExit) as error: self.module.main()
                self.assertEqual(error.exception.code,2); run.assert_not_called()
        with mock.patch.object(sys,'argv',['probe','--inner-post-enter-observation']),\
                mock.patch.object(self.module,'_controls') as controls,contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(self.module.main(),2)
            controls.assert_not_called()


if __name__=='__main__': unittest.main()
