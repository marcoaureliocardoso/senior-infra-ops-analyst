"""Observation never grants terminal input authority; synthetic protocol fixtures."""
import copy
import gc
import importlib
import importlib.util
import pickle
import unittest
import weakref
from unittest import mock

import terminal_input_challenge as challenge
import terminal_resume_history as history
from resume_history_fixtures import CaseFixture


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


if __name__=='__main__': unittest.main()
