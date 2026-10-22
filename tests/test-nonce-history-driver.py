"""Real Python PTY protocol, not native/provider/browser acceptance."""
from dataclasses import replace
from contextlib import ExitStack
import importlib.util
import json
from pathlib import Path
import time
import unittest
from unittest import mock

from nonce_history_fixtures import run_nonce_phase_case,VARIANTS
from resume_history_fixtures import CaseFixture
from terminal_state_adapter import TerminalCell
import terminal_input_challenge as challenge
import terminal_resume_history as history
import terminal_nonce_history_diagnostics as observation
import headless_context_driver as selected
from terminal_cancellation import TerminalCancelled,TerminalCancellation


class NonceHistoryDriverTests(unittest.TestCase):
    def clean(self,result):
        for field in ('inputExact','processReaped','helperReaped','caseRootAbsent','scopeReleased','sessionReleased'):
            self.assertTrue(result[field],field)

    def test_phase_matrix_preserves_exact_input_and_outcomes(self):
        for kind in ('text-turn','skill-turn'):
            for variant in VARIANTS:
                with self.subTest(kind=kind,variant=variant):
                    result=run_nonce_phase_case(kind,variant); self.clean(result)
                    rejected=variant not in ('stable','post-clear-move')
                    self.assertEqual(result['exitCode'],2 if rejected else 0)
                    self.assertEqual(result['inputBytes'],25 if variant.startswith('echo-') else
                        26 if variant.startswith('clear-') else 32)
                    report=result['diagnostics']
                    self.assertFalse(report['rejected']); self.assertFalse(report['truncated'])
                    failures=[r for r in report['records'] if r['point']=='failure']
                    if not rejected:
                        self.assertEqual(failures,[])
                        self.assertFalse(any('nonceHistoryContext' in r for r in report['records']))
                        continue
                    self.assertEqual(len(failures),1)
                    self.assertEqual(failures[0]['resumeHistoryFailure']['check'],'UNOWNED_NEW_PROFILE')
                    self.assertEqual(failures[0].get('nonceHistoryContext'),dict(site='HISTORY',
                        noncePhase='ECHO_MATCHED' if variant.startswith('echo-') else 'CLEAR_PENDING',
                        clearWrite='NOT_SENT' if variant.startswith('echo-') else 'ACKED',
                        clearEvidence='ABSENT',sdkBaseline='PRESENT',placement='OTHER_SLOT',
                        profile='EXACT' if variant.endswith('move') else 'DIFFERENT'))

    def bindings(self,f):
        return dict(state=f.state,scope=f.scope,native_owner=f.native,
            controller_owner=f.controller,transition_owner=f.transition)

    def test_observe_first_still_rejects_moved_clearing_snapshot(self):
        for kind in ('text-turn','skill-turn'):
            with self.subTest(kind=kind),CaseFixture(kind) as f:
                b=f.proven_resume(nonce_phase='CLEAR_PENDING'); rows=list(b['snapshot'].rows)
                rows[6]=rows[5]; rows[5]=tuple(TerminalCell('',1) for _ in range(120))
                # Clear the nonce using the original protocol row, not forged evidence.
                rows[37]=b['probe']._row
                moved=replace(b['snapshot'],rows=tuple(rows),cursorX=b['probe']._anchor.cursorX)
                session=observation._create_nonce_history_session(b['view'],**self.bindings(f),probe=b['probe'])
                try:
                    with self.assertRaises(history.ResumeHistoryError) as caught:
                        with observation._nonce_history_scope(session,probe=b['probe'],snapshot=moved,frame=5):
                            b['probe'].observe(moved,5)
                    detail=observation.nonce_history_failure_diagnostic(caught.exception)
                    self.assertEqual(detail['noncePhase'],'CLEAR_PENDING')
                    self.assertEqual(detail['clearEvidence'],'ABSENT')
                    self.assertEqual(history.resume_failure_diagnostic(caught.exception)['check'],'UNOWNED_NEW_PROFILE')
                finally: observation._close_nonce_history_session(session)

    def test_mutation_site_matrix_is_discriminated_without_reclassification(self):
        for kind in ('text-turn','skill-turn'):
            for transaction,moved in ((True,False),(True,True),(False,False)):
                with self.subTest(kind=kind,transaction=transaction,moved=moved),CaseFixture(kind) as f:
                    b=f.proven_resume(); rows=list(b['snapshot'].rows); cells=list(rows[5]); cells[1]=TerminalCell('\u00a0',1)
                    if moved: rows[5]=tuple(TerminalCell('',1) for _ in range(120))
                    rows[6 if moved else 5]=tuple(cells); snapshot=replace(b['snapshot'],rows=tuple(rows))
                    args=dict(policy=f.policy,snapshot=snapshot,frame=6,**self.bindings(f))
                    session=observation._create_nonce_history_session(b['view'],**self.bindings(f),probe=b['probe'])
                    try:
                        with self.assertRaises(history.ResumeHistoryError) as caught:
                            with observation._nonce_history_scope(session,probe=b['probe'],snapshot=snapshot,frame=6):
                                if transaction: history._try_commit_sdk_relocation(b['view'],b['probe'],b['receipt'],**args)
                                else: history.validate_resume_view(b['view'],**args)
                        detail=observation.nonce_history_failure_diagnostic(caught.exception)
                        self.assertEqual(detail['site'],'CANDIDATE_IDENTITY' if transaction else 'HISTORY')
                        self.assertEqual(detail['profile'],'DIFFERENT')
                        self.assertEqual(detail['placement'],'OTHER_SLOT' if moved else 'SAME_SLOT')
                        self.assertEqual(history.resume_failure_diagnostic(caught.exception)['check'],
                            'UNOWNED_NEW_PROFILE' if transaction else 'PINNED_PROFILE_CHANGED')
                    finally: observation._close_nonce_history_session(session)

    def test_clear_ack_is_dialogue_bound_and_never_inferred_from_phase(self):
        for kind in ('text-turn','skill-turn'):
            for fault,count,code in (('would-block',32,0),('io-error',25,2),('bad-count',26,2)):
                with self.subTest(kind=kind,fault=fault):
                    notes=[]; real=selected._note_nonce_clear_ack
                    def ack(session,**kwargs):
                        notes.append(kwargs['count']); return real(session,**kwargs)
                    with mock.patch.object(selected,'_note_nonce_clear_ack',side_effect=ack):
                        result=run_nonce_phase_case(kind,'stable',clear_fault=fault)
                    self.clean(result)
                    self.assertEqual((result['exitCode'],result['inputBytes']),(code,count))
                    self.assertEqual(notes,[1] if fault=='would-block' else [])
                    self.assertEqual(result['clearCalls'],2 if fault=='would-block' else 1)
                    if code==2:
                        failure=next(r for r in result['diagnostics']['records'] if r['point']=='failure')
                        self.assertEqual(failure['reasonCode'],'INPUT_PROBE_IO_FAILED')
            with CaseFixture(kind) as f:
                b=f.proven_resume(); probe=b['probe']
                session=observation._create_nonce_history_session(b['view'],**self.bindings(f))
                try:
                    observation._note_nonce_clear_attempt(session,probe=probe)
                    observation._note_nonce_clear_ack(session,probe=object(),count=1)
                    with observation._nonce_history_scope(session,probe=probe,snapshot=b['snapshot'],frame=5):
                        self.assertEqual(observation._CURRENT.get()['clearWrite'],'UNKNOWN')
                        self.assertEqual(observation._CURRENT.get()['noncePhase'],'PROVEN')
                    observation._note_nonce_clear_ack(session,probe=probe,count=1)
                    with observation._nonce_history_scope(session,probe=object(),snapshot=b['snapshot'],frame=5):
                        self.assertEqual(observation._CURRENT.get()['clearWrite'],'UNKNOWN')
                    with observation._nonce_history_scope(session,probe=None,snapshot=b['snapshot'],frame=5):
                        self.assertEqual(observation._CURRENT.get()['noncePhase'],'UNKNOWN')
                finally: observation._close_nonce_history_session(session)

    def test_capture_loss_preserves_bytes_errors_and_cleanup(self):
        for kind in ('text-turn','skill-turn'):
            for variant in ('stable','echo-move','clear-move','post-clear-move'):
                normal=run_nonce_phase_case(kind,variant); self.clean(normal)
                for mode in ('absent','capture-failure','collector-failure'):
                    with self.subTest(kind=kind,variant=variant,mode=mode):
                        result=run_nonce_phase_case(kind,variant,diagnostic_mode=mode); self.clean(result)
                        self.assertEqual((result['exitCode'],result['inputBytes'],result['clearCalls']),
                            (normal['exitCode'],normal['inputBytes'],normal['clearCalls']))
                        report=result['diagnostics']
                        self.assertFalse(any('nonceHistoryContext' in r for r in report['records']))
                        if mode!='collector-failure':
                            reduced=lambda rows:[{k:v for k,v in r.items() if k!='nonceHistoryContext'} for r in rows]
                            self.assertEqual(reduced(report['records']),reduced(normal['diagnostics']['records']))

    def test_session_and_projection_failure_do_not_change_rejection(self):
        for function in ('_create_nonce_history_session','nonce_history_failure_diagnostic'):
            with self.subTest(function=function),mock.patch.object(selected,function,side_effect=LookupError):
                result=run_nonce_phase_case('text-turn','echo-move'); self.clean(result)
                self.assertEqual((result['exitCode'],result['inputBytes']),(2,25))
                failure=next(r for r in result['diagnostics']['records'] if r['point']=='failure')
                self.assertEqual(failure['reasonCode'],'RESUME_HISTORY_LAYOUT_REJECTED')
                self.assertNotIn('nonceHistoryContext',failure)

    def test_annotation_excluded_routes_never_activate_session(self):
        path=Path(__file__).with_name('test-headless-context-driver.py')
        spec=importlib.util.spec_from_file_location('nonce_excluded_driver',path)
        module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        with mock.patch.object(selected,'_create_nonce_history_session',side_effect=AssertionError) as create:
            for route in ('live','initial','debug','edit-debug'):
                with self.subTest(route=route):
                    ui=module.HeadlessContextDriverTests('test_current_nbsp_input_context_and_natural_exit')
                    ui.setUp()
                    try:
                        if route=='live': ui.run_case(False)
                        else:
                            report=ui.run_pinned_probe(debug=route=='debug',edit_debug=route=='edit-debug')
                            self.assertFalse(any('nonceHistoryContext' in row for row in report['records']))
                    finally: ui.doCleanups()
            self.assertEqual(create.call_count,0)
        # Observation view bindings are explicitly refused by the session factory.
        from post_enter_observation_fixtures import ObservationCase
        with ObservationCase() as case:
            self.assertIsNone(observation._create_nonce_history_session(case.view,**self.bindings(case.fixture)))
        result=run_nonce_phase_case('text-turn','stable'); self.clean(result)
        self.assertFalse(any('nonceHistoryContext' in r for r in result['diagnostics']['records']))

    def test_cancellation_and_expiry_release_observation_scope(self):
        for point in ('before-guard','write-wait','rejection','disposal'):
            with self.subTest(point=point),TerminalCancellation() as cancellation,ExitStack() as patches:
                created={}; real_create=selected._create_nonce_history_session
                real_select=selected.select.select; real_fail=history._fail
                real_close=selected._close_nonce_history_session
                real_fresh=CaseFixture.fresh_terminal
                def fresh(fixture,**kwargs):
                    return real_fresh(fixture,**{**kwargs,'cancellation':cancellation})
                def create(view,**bindings):
                    session=real_create(view,**bindings); created.update(bindings,view=view)
                    if point=='before-guard':
                        cancellation.requested=True
                    return session
                def wait(read,write,error,timeout=None):
                    result=real_select(read,write,error,timeout)
                    if point=='write-wait' and write and created and not created.get('expired'):
                        if any(r.get('resume_view') is created['view'] and probe.phase=='CLEAR_PENDING'
                                for probe,r in list(challenge._CHALLENGES.items())):
                            created['expired']=True
                            cancellation.requested=True
                    return result
                def reject(record,*args,**kwargs):
                    if point=='rejection' and created:
                        # Expiry during rejection cannot refresh the captured facts.
                        patches.enter_context(mock.patch.object(history,'_now',return_value=time.monotonic()+100))
                    return real_fail(record,*args,**kwargs)
                def close(session):
                    real_close(session)
                    if point=='disposal': raise TerminalCancelled()
                patches.enter_context(mock.patch.object(selected,'_create_nonce_history_session',side_effect=create))
                patches.enter_context(mock.patch.object(CaseFixture,'fresh_terminal',new=fresh))
                patches.enter_context(mock.patch.object(selected.select,'select',side_effect=wait))
                patches.enter_context(mock.patch.object(history,'_fail',side_effect=reject))
                patches.enter_context(mock.patch.object(selected,'_close_nonce_history_session',side_effect=close))
                result=run_nonce_phase_case('text-turn','echo-move' if point=='rejection' else 'stable')
                self.clean(result)
                self.assertEqual(result['exitCode'],0 if point=='disposal' else 2)
                self.assertEqual(result['inputBytes'],{'before-guard':0,'write-wait':25,'rejection':25,'disposal':32}[point])

    def test_sampler_cost_is_bounded_local_work(self):
        measured={name:dict(calls=0,seconds=0.0) for name in ('entry','exit','freeze','project')}
        def timed(name,call,*args,**kwargs):
            started=time.perf_counter()
            try: return call(*args,**kwargs)
            finally:
                measured[name]['calls']+=1; measured[name]['seconds']+=time.perf_counter()-started
        with CaseFixture() as f:
            b=f.proven_resume(); session=observation._create_nonce_history_session(b['view'],**self.bindings(f))
            real=history.match_history_row
            try:
                with mock.patch('builtins.open',side_effect=AssertionError),\
                        mock.patch.object(f.state,'snapshot',side_effect=AssertionError),\
                        mock.patch.object(f.native,'poll',side_effect=AssertionError):
                    for _ in range(20):
                        scope=observation._nonce_history_scope(session,probe=b['probe'],snapshot=b['snapshot'],frame=5)
                        timed('entry',scope.__enter__)
                        try:
                            error=history._resume_layout_error(b['view'],'COMPOSE_ROW_CONFLICT')
                            with mock.patch.object(history,'match_history_row',wraps=real) as classify:
                                timed('freeze',observation._freeze_nonce_history_failure,error,
                                    record=history._VIEWS[b['view']],snapshot=b['snapshot'],frame=5,site='COMPOSITION')
                                self.assertLessEqual(classify.call_count,40)
                            self.assertIsNotNone(timed('project',observation.nonce_history_failure_diagnostic,error))
                        finally: timed('exit',scope.__exit__,None,None,None)
            finally: observation._close_nonce_history_session(session)
        for value in measured.values():
            self.assertEqual(value['calls'],20); self.assertGreaterEqual(value['seconds'],0)
        print(json.dumps({'observerMeasurement':measured},sort_keys=True))


if __name__=='__main__': unittest.main()
