"""Observation never grants terminal input authority; synthetic protocol fixtures."""
import copy
import gc
import importlib
import importlib.util
import pickle
import unittest
import weakref
from dataclasses import replace
from unittest import mock

import terminal_input_challenge as challenge
import terminal_resume_history as history
from resume_history_fixtures import CaseFixture
from terminal_state_adapter import TerminalCell


class NonceHistoryDiagnosticsTests(unittest.TestCase):
    def observer(self):
        name='terminal_nonce_history_diagnostics'
        self.assertIsNotNone(importlib.util.find_spec(name),'private observation behavior missing')
        return importlib.import_module(name)

    def bindings(self,f):
        return dict(state=f.state,scope=f.scope,native_owner=f.native,
            controller_owner=f.controller,transition_owner=f.transition)

    def session(self,d,f,b,**kwargs):
        result=d._create_nonce_history_session(b['view'],**self.bindings(f),**kwargs)
        self.assertIsNotNone(result)
        self.addCleanup(d._close_nonce_history_session,result)
        return result

    def test_scope_binds_actual_snapshot_and_restores_on_all_paths(self):
        d=self.observer()
        with CaseFixture() as f:
            b=f.proven_resume(); session=self.session(d,f,b,probe=b['probe'])
            args=dict(probe=b['probe'],snapshot=b['snapshot'],frame=b['frame'])
            self.assertIsNone(d._CURRENT.get())
            with d._nonce_history_scope(session,**args):
                current=d._CURRENT.get()
                self.assertIs(current['snapshot'],b['snapshot'])
                self.assertEqual(current['frame'],5)
                self.assertEqual(current['noncePhase'],'PROVEN')
                self.assertEqual(current['clearEvidence'],'PRESENT')
                with d._nonce_history_scope(None,**args):
                    self.assertIsNone(d._CURRENT.get())
                self.assertIs(d._CURRENT.get(),current)
            self.assertIsNone(d._CURRENT.get())
            wrong={**self.bindings(f),'controller_owner':object()}
            self.assertIsNone(d._create_nonce_history_session(b['view'],**wrong))
            record=history._VIEWS[b['view']]
            with mock.patch.dict(record,observation_request=object()):
                self.assertIsNone(d._create_nonce_history_session(b['view'],**self.bindings(f)))

    def test_scope_exit_preserves_primary_exception(self):
        d=self.observer()
        with CaseFixture() as f:
            b=f.proven_resume(); session=self.session(d,f,b)
            error=RuntimeError('synthetic rejection')
            with self.assertRaises(RuntimeError) as caught:
                with d._nonce_history_scope(session,probe=b['probe'],snapshot=b['snapshot'],frame=5):
                    raise error
            self.assertIs(caught.exception,error)
            self.assertIsNone(d._CURRENT.get())
            with mock.patch.object(d,'_capture_scope',side_effect=ValueError):
                with self.assertRaises(RuntimeError) as caught:
                    with d._nonce_history_scope(session,probe=b['probe'],snapshot=b['snapshot'],frame=5):
                        self.assertIsNone(d._CURRENT.get()); raise error
            self.assertIs(caught.exception,error)
            self.assertIsNone(d._CURRENT.get())

    def test_status_reader_is_pure_and_public_phase_is_not_evidence(self):
        reader=getattr(challenge,'_read_nonce_history_status',None)
        self.assertTrue(callable(reader),'pure registered-state reader missing')
        for phase in ('ELIGIBLE','ECHO_PENDING','ECHO_MATCHED','CLEAR_PENDING','PROVEN'):
            with self.subTest(phase=phase),CaseFixture() as f:
                b=f.proven_resume(nonce_phase=phase); probe=b['probe']
                before=(probe._last_frame,probe._last_time,dict(challenge._CHALLENGES[probe]),
                    dict(history._VIEWS[b['view']]))
                with mock.patch.object(probe,'_check_lifetime',side_effect=AssertionError),\
                        mock.patch.object(f.native,'poll',side_effect=AssertionError):
                    self.assertEqual(reader(probe,view=b['view'],**self.bindings(f)),
                        (phase,'PRESENT' if phase=='PROVEN' else 'ABSENT'))
                self.assertEqual(before,(probe._last_frame,probe._last_time,
                    dict(challenge._CHALLENGES[probe]),dict(history._VIEWS[b['view']])))
                if phase!='PROVEN':
                    probe.phase='PROVEN'
                    self.assertEqual(reader(probe,view=b['view'],**self.bindings(f)),('PROVEN','ABSENT'))
                self.assertIsNone(reader(probe,view=b['view'],
                    **{**self.bindings(f),'controller_owner':object()}))

    def test_clear_write_status_is_observation_not_permission(self):
        d=self.observer()
        with CaseFixture() as f:
            b=f.proven_resume(nonce_phase='ECHO_MATCHED'); probe=b['probe']
            late=self.session(d,f,b,probe=probe)
            session=self.session(d,f,b)
            def status(handle,p=probe):
                with d._nonce_history_scope(handle,probe=p,snapshot=b['snapshot'],frame=b['frame']):
                    current=d._CURRENT.get()
                    return current['clearWrite'] if current is not None else None
            self.assertEqual(status(late),'UNKNOWN')
            self.assertEqual(status(session),'NOT_SENT')
            d._note_nonce_clear_ack(session,probe=probe,count=1)
            self.assertEqual(status(session),'NOT_SENT','ack requires a matching attempt')
            d._note_nonce_clear_attempt(session,probe=probe)
            self.assertEqual(status(session),'UNKNOWN')
            for count in (True,0,2,None):
                d._note_nonce_clear_ack(session,probe=probe,count=count)
                self.assertEqual(status(session),'UNKNOWN')
            d._note_nonce_clear_ack(session,probe=probe,count=1)
            self.assertEqual(status(session),'ACKED')
            self.assertEqual(probe.phase,'ECHO_MATCHED')
            d._note_nonce_clear_attempt(session,probe=probe)
            self.assertEqual(status(session),'UNKNOWN','new uncertainty cannot borrow previous ACK')
            self.assertEqual(status(session,None),'UNKNOWN')
            fake=object.__new__(d._NonceHistorySession)
            self.assertIsNone(status(fake))
            with self.assertRaises(TypeError): pickle.dumps(session)
            with self.assertRaises(TypeError): copy.copy(session)

    def test_closed_schema_rejects_extra_keys_and_non_strings(self):
        d=self.observer()
        valid=dict(site='HISTORY',noncePhase='PROVEN',clearWrite='ACKED',clearEvidence='PRESENT',
            sdkBaseline='PRESENT',placement='SAME_SLOT',profile='EXACT')
        self.assertTrue(d.valid_nonce_history_context(valid))
        enums=dict(site=('HISTORY','CANDIDATE_IDENTITY','CANDIDATE_DESTINATION','COMPOSITION','OTHER'),
            noncePhase=('NONE','ELIGIBLE','ECHO_PENDING','ECHO_MATCHED','CLEAR_PENDING','PROVEN','CONSUMED','REVOKED','UNKNOWN'),
            clearWrite=('NOT_SENT','ACKED','UNKNOWN'),clearEvidence=('ABSENT','PRESENT','UNKNOWN'),
            sdkBaseline=('ABSENT','PRESENT','UNKNOWN'),placement=('SAME_SLOT','OTHER_SLOT','NO_MATCH','MULTIPLE','UNKNOWN'),
            profile=('EXACT','DIFFERENT','UNAVAILABLE'))
        for key,values in enums.items():
            for value in values: self.assertTrue(d.valid_nonce_history_context({**valid,key:value}))
            for value in (True,1,None,[],{},'arbitrary'):
                self.assertFalse(d.valid_nonce_history_context({**valid,key:value}))
        self.assertFalse(d.valid_nonce_history_context({**valid,'extra':'HISTORY'}))
        self.assertFalse(d.valid_nonce_history_context({k:v for k,v in valid.items() if k!='site'}))

    def test_scope_and_session_release_owned_references(self):
        d=self.observer()
        with CaseFixture() as f:
            b=f.proven_resume(); session=self.session(d,f,b)
            with d._nonce_history_scope(session,probe=b['probe'],snapshot=b['snapshot'],frame=5):
                self.assertIsNotNone(d._CURRENT.get())
            d._close_nonce_history_session(session)
            self.assertNotIn(session,d._SESSIONS)
            with d._nonce_history_scope(session,probe=b['probe'],snapshot=b['snapshot'],frame=5):
                self.assertIsNone(d._CURRENT.get())
            ref=weakref.ref(session); self._cleanups.clear(); del session; gc.collect()
            self.assertIsNone(ref())
            self.assertIsNone(d._CURRENT.get())

    def test_missing_binding_metadata_is_not_reported_as_absent_baseline(self):
        d=self.observer()
        with CaseFixture() as f:
            b=f.proven_resume(); session=self.session(d,f,b)
            record=history._VIEWS[b['view']]
            for key in ('sdk_identity','sdk_position'):
                with mock.patch.dict(record):
                    record.pop(key)
                    with d._nonce_history_scope(session,probe=b['probe'],snapshot=b['snapshot'],frame=5):
                        self.assertTrue(d._CURRENT.get() is None,'incomplete binding must omit observation')


class NonceHistoryFreezeTests(unittest.TestCase):
    observer=NonceHistoryDiagnosticsTests.observer
    bindings=NonceHistoryDiagnosticsTests.bindings
    session=NonceHistoryDiagnosticsTests.session

    def args(self,f,b,snapshot=None,frame=None):
        return dict(policy=f.policy,**self.bindings(f),snapshot=snapshot or b['snapshot'],
            frame=b['frame']+1 if frame is None else frame)

    def changed(self,b,*,destination=5,padding=False,duplicate=False,remove=False):
        rows=list(b['snapshot'].rows); source=rows[5]
        rows[5]=tuple(TerminalCell('',1) for _ in range(120))
        if padding:
            source=(*source[:1],TerminalCell('\u00a0',1),*source[2:])
        if not remove: rows[destination]=source
        if duplicate: rows[7]=source
        return replace(b['snapshot'],rows=tuple(rows))

    def reject(self,d,f,b,snapshot,*,transaction=False,frame=None):
        args=self.args(f,b,snapshot,frame)
        session=self.session(d,f,b,probe=b['probe'])
        with self.assertRaises(history.ResumeHistoryError) as caught:
            with d._nonce_history_scope(session,probe=b['probe'],snapshot=snapshot,frame=args['frame']):
                if transaction:
                    history._try_commit_sdk_relocation(b['view'],b['probe'],b['receipt'],**args)
                else: history.validate_resume_view(b['view'],**args)
        self.assertEqual(caught.exception.reason,'RESUME_HISTORY_LAYOUT_REJECTED')
        self.assertEqual(history.resume_view_decision(b['view']),'REJECTED')
        project=getattr(d,'nonce_history_failure_diagnostic',lambda _e:None)
        detail=project(caught.exception)
        self.assertIsNotNone(detail,'coherent failure facts must be frozen before revocation')
        self.assertEqual(b['probe'].phase,'REVOKED')
        return detail,caught.exception

    def test_actual_sites_freeze_before_revocation(self):
        d=self.observer()
        for kind in ('text-turn','skill-turn'):
            for phase in ('ECHO_MATCHED','CLEAR_PENDING','PROVEN'):
                with self.subTest(kind=kind,phase=phase),CaseFixture(kind) as f:
                    b=f.proven_resume(nonce_phase=phase)
                    detail,_=self.reject(d,f,b,self.changed(b,destination=6))
                    self.assertEqual(detail,dict(site='HISTORY',noncePhase=phase,clearWrite='UNKNOWN',
                        clearEvidence='PRESENT' if phase=='PROVEN' else 'ABSENT',
                        sdkBaseline='PRESENT',placement='OTHER_SLOT',profile='EXACT'))

    def test_same_label_distinguishes_identity_and_destination_sites(self):
        d=self.observer()
        for kind in ('text-turn','skill-turn'):
            for variant,site,check in (('padding','CANDIDATE_IDENTITY','UNOWNED_NEW_PROFILE'),
                    ('destination','CANDIDATE_DESTINATION','UNOWNED_NEW_PROFILE'),
                    ('retired','OTHER','RETIRED_PROFILE_RETURNED')):
                with self.subTest(kind=kind,variant=variant),CaseFixture(kind) as f:
                    b=f.proven_resume(pinned_exit=True)
                    record=history._VIEWS[b['view']]
                    target=self.changed(b,padding=True) if variant=='padding' else self.changed(b,destination=12)
                    if variant=='retired':
                        # Acquire retirement via an actual accepted disappearance, not registry injection.
                        absent=self.changed(b,remove=True)
                        history.validate_resume_view(b['view'],**self.args(f,b,absent))
                        target=b['snapshot']
                    detail,error=self.reject(d,f,b,target,transaction=True,frame=7)
                    self.assertEqual(history.resume_failure_diagnostic(error)['check'],check)
                    self.assertEqual(detail['site'],site)
                    self.assertEqual(detail['profile'],'DIFFERENT' if variant=='padding' else 'EXACT')

    def test_failure_after_commit_uses_current_authorized_slot(self):
        d=self.observer()
        self.assertTrue(callable(getattr(d,'nonce_history_failure_diagnostic',None)),'failure observation missing')
        for kind in ('text-turn','skill-turn'):
            with self.subTest(kind=kind),CaseFixture(kind) as f:
                b=f.proven_resume(); moved=self.changed(b,destination=6)
                self.assertTrue(history._try_commit_sdk_relocation(b['view'],b['probe'],b['receipt'],
                    **self.args(f,b,moved)))
                # Same snapshot, separately scoped later guard sees the committed slot.
                session=self.session(d,f,b,probe=b['probe'])
                with d._nonce_history_scope(session,probe=b['probe'],snapshot=moved,frame=6):
                    error=history._resume_layout_error(b['view'],'COMPOSE_ROW_CONFLICT',
                        _nonce_snapshot=moved,_nonce_frame=6,_nonce_site='COMPOSITION')
                self.assertEqual(d.nonce_history_failure_diagnostic(error)['placement'],'SAME_SLOT')

    def test_nested_cross_frame_capture_cannot_replace_first_failure(self):
        d=self.observer()
        self.assertTrue(callable(getattr(d,'nonce_history_failure_diagnostic',None)),'failure observation missing')
        with CaseFixture() as f:
            b=f.proven_resume(); bad=self.changed(b,padding=True)
            detail,error=self.reject(d,f,b,bad)
            original=dict(detail)
            error.nonceHistoryContext={**detail,'site':'OTHER'}
            counterfeit=history.ResumeHistoryError(error.reason)
            counterfeit.__dict__.update(error.__dict__)
            self.assertIsNone(d.nonce_history_failure_diagnostic(counterfeit))
            d._freeze_nonce_history_failure(error,record={},snapshot=bad,frame=100,site='OTHER')
            self.assertEqual(d.nonce_history_failure_diagnostic(error),original)
        for mismatch in ('frame','snapshot','projected','nested'):
            with self.subTest(mismatch=mismatch),CaseFixture() as f:
                b=f.proven_resume(); session=self.session(d,f,b)
                snap=b['snapshot']; record=history._VIEWS[b['view']]
                with d._nonce_history_scope(session,probe=b['probe'],snapshot=snap,frame=6):
                    error=history._resume_layout_error(b['view'],'PINNED_PROFILE_CHANGED')
                    args=dict(record=record,snapshot=snap,frame=6,site='HISTORY')
                    if mismatch=='frame': args['frame']=7
                    if mismatch=='snapshot': args['snapshot']=replace(snap,cursorX=3)
                    if mismatch=='projected': args['record']={**record,'_read_only':True}
                    if mismatch=='nested':
                        with d._nonce_history_scope(None,probe=None,snapshot=snap,frame=6):
                            d._freeze_nonce_history_failure(error,**args)
                    else: d._freeze_nonce_history_failure(error,**args)
                    self.assertIsNone(d.nonce_history_failure_diagnostic(error))

    def test_sampler_performs_no_io_validation_or_metadata_refresh(self):
        d=self.observer()
        self.assertTrue(callable(getattr(d,'nonce_history_failure_diagnostic',None)),'failure observation missing')
        with CaseFixture() as f:
            b=f.proven_resume(); session=self.session(d,f,b,probe=b['probe']); snap=b['snapshot']
            record=history._VIEWS[b['view']]; before=history._view_fingerprint(record)
            with mock.patch.object(f.native,'poll',side_effect=AssertionError),\
                    mock.patch.object(b['probe'],'_check_lifetime',side_effect=AssertionError),\
                    mock.patch.object(history,'_case',side_effect=AssertionError),\
                    mock.patch.object(history,'validate_resume_view',side_effect=AssertionError):
                with d._nonce_history_scope(session,probe=b['probe'],snapshot=snap,frame=6):
                    error=history._resume_layout_error(b['view'],'COMPOSE_ROW_CONFLICT',
                        _nonce_snapshot=snap,_nonce_frame=6,_nonce_site='COMPOSITION')
                self.assertEqual(d.nonce_history_failure_diagnostic(error)['profile'],'EXACT')
            self.assertEqual(history._view_fingerprint(record),before)
        with CaseFixture() as f:
            b=f.proven_resume(); bad=self.changed(b,padding=True)
            with mock.patch.object(d,'_capture_scope',side_effect=ValueError):
                with self.assertRaises(history.ResumeHistoryError):
                    with d._nonce_history_scope(self.session(d,f,b),probe=b['probe'],snapshot=bad,frame=6):
                        history.validate_resume_view(b['view'],**self.args(f,b,bad))
            self.assertEqual(history.resume_view_decision(b['view']),'REJECTED')

    def test_missing_duplicate_and_unrecognized_profiles_are_not_inequality(self):
        d=self.observer()
        for variant,placement,profile,baseline in (('absent','UNKNOWN','UNAVAILABLE','ABSENT'),
                ('removed','NO_MATCH','UNAVAILABLE','PRESENT'),
                ('unrecognized','NO_MATCH','UNAVAILABLE','PRESENT'),
                ('duplicate','MULTIPLE','UNAVAILABLE','PRESENT')):
            with self.subTest(variant=variant),CaseFixture() as f:
                b=f.proven_resume(sdk_history=variant!='absent')
                snap=b['snapshot']
                if variant in ('removed','unrecognized'): snap=self.changed(b,remove=True)
                if variant=='duplicate': snap=self.changed(b,duplicate=True)
                if variant=='unrecognized':
                    rows=list(snap.rows); rows[5]=tuple(TerminalCell(c,1) for c in ('❯ not recognized').ljust(120))
                    snap=replace(snap,rows=tuple(rows))
                session=self.session(d,f,b,probe=b['probe'])
                with d._nonce_history_scope(session,probe=b['probe'],snapshot=snap,frame=6):
                    error=history._resume_layout_error(b['view'],'COMPOSE_ROW_CONFLICT',
                        _nonce_snapshot=snap,_nonce_frame=6,_nonce_site='COMPOSITION')
                detail=d.nonce_history_failure_diagnostic(error)
                self.assertEqual((detail['placement'],detail['profile'],detail['sdkBaseline']),
                    (placement,profile,baseline))

    def test_reentrant_sampler_stays_bounded_and_first_invocation_wins(self):
        d=self.observer()
        with CaseFixture() as f:
            b=f.proven_resume(); snap=b['snapshot']; record=history._VIEWS[b['view']]
            session=self.session(d,f,b); calls=[]; reentered=False
            real=history.match_history_row
            with d._nonce_history_scope(session,probe=b['probe'],snapshot=snap,frame=6):
                error=history._resume_layout_error(b['view'],'COMPOSE_ROW_CONFLICT')
                def match(row,kind):
                    nonlocal reentered
                    calls.append(True)
                    if not reentered:
                        reentered=True
                        d._freeze_nonce_history_failure(error,record=record,snapshot=snap,frame=6,site='OTHER')
                    return real(row,kind)
                with mock.patch.object(history,'match_history_row',side_effect=match):
                    d._freeze_nonce_history_failure(error,record=record,snapshot=snap,frame=6,site='COMPOSITION')
            self.assertLessEqual(len(calls),40)
            self.assertEqual(d.nonce_history_failure_diagnostic(error)['site'],'COMPOSITION')


if __name__=='__main__': unittest.main()
