"""HISTORY_COMMIT_V1: correlated display, not native recomputation."""
import copy
from dataclasses import replace
import unittest
from unittest import mock

from context_display_fixtures import DisplayCase, TEXT
import terminal_context_echo as echo
import terminal_resume_history as history
from terminal_input_challenge import InputProofError, NonceInputChallenge


class ContextDisplayTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(callable(getattr(echo.OwnedContextCommand,'context_display_percent',None)),
            'owned resumed-display readiness is absent')

    def test_equal_values_need_new_owned_commit(self):
        with DisplayCase() as c:
            c.submit()
            self.assertIsNone(c.observe(c.snapshot(),3))
            current=c.snapshot(commit=20)
            self.assertEqual(c.observe(current,4),16)
            with mock.patch.object(c.fixture.policy,'_empty_input_assessment',
                    wraps=c.fixture.policy._empty_input_assessment) as assessment:
                receipt=c.command.bind_history(current,4)
                self.assertEqual(assessment.call_count,1)
            self.assertIsNotNone(receipt)
            self.assertEqual(c.command.phase,'RECEIPT_READY')
            self.assertEqual(history.resume_view_decision(c.view),'VALID')
            with self.assertRaises(InputProofError): c.command.bind_history(current,4)

    def test_text_change_without_commit_is_not_evidence(self):
        for mutation in ('heading','order','cursor','changed-numbers'):
            with self.subTest(mutation=mutation),DisplayCase() as c:
                c.submit()
                current=c.snapshot(free='80' if mutation=='changed-numbers' else None)
                rows=list(current.rows)
                if mutation=='heading': rows[0]=c.snapshot(extra=((0,'Context Usage (local)'),)).rows[0]
                if mutation=='order': rows[1],rows[2]=rows[2],rows[1]
                current=replace(current,rows=tuple(rows),cursorX=3 if mutation=='cursor' else 2)
                if mutation=='cursor':
                    with self.assertRaises(InputProofError): c.observe(current,3)
                    self.assertEqual(c.command.phase,'REVOKED')
                    continue
                self.assertIsNone(c.observe(current,3))
                with self.assertRaises(InputProofError) as caught: c.command.bind_history(current,3)
                self.assertEqual(caught.exception.reason,'INPUT_PROBE_STATE_REJECTED')
                self.assertEqual(c.journal.project(caught.exception,**c.bindings)['check'],'DISPLAY_WITNESS_UNPROVEN')

    def test_changed_sample_needs_same_owned_commit(self):
        with DisplayCase() as c:
            c.submit()
            self.assertIsNone(c.observe(c.snapshot(),3))
            current=c.snapshot(free='80',commit=20)
            self.assertEqual(c.observe(current,4),17)
            self.assertIsNotNone(c.command.bind_history(current,4))

    def test_conflicting_sample_cannot_restore_baseline(self):
        for free,buffer in (('81','3'),('79','3'),('81','2')):
            with self.subTest(free=free,buffer=buffer),DisplayCase() as c:
                c.submit()
                self.assertIsNone(c.observe(c.snapshot(free='80'),3))
                with self.assertRaises(InputProofError) as caught:
                    c.observe(c.snapshot(free=free,buffer=buffer,commit=20),4)
                self.assertEqual(c.journal.project(caught.exception,**c.bindings)['check'],'CONTEXT_SAMPLE_UNSTABLE')
                self.assertEqual(c.command.phase,'REVOKED')
                self.assertEqual(history.resume_view_decision(c.view),'REJECTED')

    def test_candidate_loss_is_irreversible(self):
        for mutation in ('missing','moved','duplicated','numeric','geometry','incomplete','anchor'):
            with self.subTest(mutation=mutation),DisplayCase() as c:
                c.submit(); current=c.snapshot(commit=20)
                self.assertEqual(c.observe(current,3),16)
                bad=c.snapshot(commit=None if mutation=='missing' else 21 if mutation=='moved' else 20,
                    free='80' if mutation=='numeric' else None,
                    extra=((21,'❯ /context'),) if mutation=='duplicated' else (),
                    numeric=mutation!='incomplete')
                if mutation=='geometry':
                    rows=list(bad.rows); rows[1],rows[3]=rows[3],rows[1]; bad=replace(bad,rows=tuple(rows))
                if mutation=='anchor': bad=replace(bad,cursorX=3)
                with self.assertRaises(RuntimeError): c.observe(bad,4)
                with self.assertRaises(RuntimeError): c.observe(current,5)
                self.assertEqual(c.command.phase,'REVOKED')

    def test_canonical_spelling_before_commit_is_not_a_conflict(self):
        with DisplayCase() as c:
            c.submit()
            self.assertIsNone(c.observe(c.snapshot(free='81.0',buffer='3.00'),3))
            self.assertEqual(c.observe(c.snapshot(commit=20),4),16)

    def test_sample_history_and_nonce_remain_separate(self):
        with DisplayCase() as c:
            c.submit(); current=c.snapshot(commit=20)
            self.assertEqual(c.observe(current,3),16)
            f=c.fixture
            with self.assertRaises(RuntimeError):
                NonceInputChallenge(f.scope,f.native,f.transition,f.policy,current,3,
                    _resume_view=c.view,_controller_owner=f.controller)

    def test_consumed_sample_is_checked_during_nonce_and_exit(self):
        with DisplayCase() as c:
            c.submit(); current=c.snapshot(commit=20)
            receipt=c.command.bind_history(current,3)
            f=c.fixture
            probe=NonceInputChallenge(f.scope,f.native,f.transition,f.policy,current,3,
                context_receipt=receipt,_resume_view=c.view,_controller_owner=f.controller)
            marker=probe.type_bytes(current,3).decode()
            nonce=replace(c.snapshot(commit=20,extra=((37,'❯ '+marker),)),cursorX=18)
            self.assertEqual(probe.observe(nonce,4),'ECHO_MATCHED')
            self.assertEqual(probe.clear_bytes(nonce,4),b'\x15')
            self.assertEqual(probe.observe(current,5),'PROVEN')
            changed=c.snapshot(free='80',commit=20)
            self.assertFalse(probe.consume_exit(probe.ownership_proof(),changed,6,f.native,f.transition))
            self.assertEqual(c.command.phase,'REVOKED')

    def test_unbound_resumed_view_never_types_nonce(self):
        with DisplayCase() as c:
            c.submit(); f=c.fixture; current=c.snapshot()
            self.assertIsNone(c.command.context_display_percent(current,3))
            with self.assertRaises(InputProofError):
                NonceInputChallenge(f.scope,f.native,f.transition,f.policy,current,3,
                    _resume_view=c.view,_controller_owner=f.controller)
            self.assertEqual(c.command.phase,'REVOKED')

    def test_witness_cannot_cross_command_or_be_forged(self):
        self.assertTrue(hasattr(echo,'ContextDisplayWitness'))
        with self.assertRaises(InputProofError): echo.ContextDisplayWitness()
        with DisplayCase() as c:
            c.submit(); current=c.snapshot(commit=20); c.observe(current,3)
            witness=echo._COMMANDS[c.command]['display_witness']
            self.assertEqual(repr(witness),'<ContextDisplayWitness>')
            for operation in (copy.copy,copy.deepcopy):
                with self.assertRaises((InputProofError,TypeError)): operation(witness)
            echo._COMMANDS[c.command]['display_witness']={'profile':'HISTORY_COMMIT_V1'}
            with self.assertRaises(RuntimeError): c.command.bind_history(current,3)

    def test_preenter_and_old_rows_cannot_be_promoted(self):
        with DisplayCase(history_rows=((5,'❯ '+TEXT),(20,'❯ /context'))) as c:
            c.submit()
            self.assertIsNone(c.observe(c.snapshot(),3))
        with DisplayCase() as c:
            c.submit(extra=((8,'❯ /context  Synthetic completion'),))
            self.assertIsNone(c.observe(c.snapshot(),3))
            with self.assertRaises(RuntimeError): c.observe(c.snapshot(commit=8),4)

    def test_bool_stale_frame_and_wrong_phase_reject(self):
        for frame in (True,0,2):
            with self.subTest(frame=frame),DisplayCase() as c:
                c.submit()
                with self.assertRaises(RuntimeError): c.command.context_display_percent(c.snapshot(commit=20),frame)
        with DisplayCase() as c:
            with self.assertRaises(RuntimeError): c.command.context_display_percent(c.baseline,1)

    def test_lifetime_and_owner_changes_reject(self):
        for mutation in ('native','helper','controller','scope','run','deadline','backwards',
                'state','policy','transition','resume_view','native-substitution'):
            with self.subTest(mutation=mutation),DisplayCase() as c:
                c.submit(); current=c.snapshot(commit=20); c.observe(current,3)
                record=echo._COMMANDS[c.command]
                if mutation=='native': c.fixture.native.returncode=0
                elif mutation=='helper': c.fixture.state.close()
                elif mutation=='deadline': record['deadline']=0
                elif mutation=='backwards': record['time']=float('inf')
                elif mutation=='native-substitution': record['native']=object()
                else: record[mutation]=object()
                with self.assertRaises(RuntimeError): c.command.bind_history(current,3)
                self.assertEqual(c.command.phase,'REVOKED')

    def test_replayed_witness_attachment_cannot_bind_a_new_command(self):
        with DisplayCase() as c:
            c.submit(); current=c.snapshot(commit=20); c.observe(current,3)
            witness=echo._COMMANDS[c.command]['display_witness']
            self.assertIsNotNone(c.command.bind_history(current,3))
        with DisplayCase() as c:
            c.submit(); current=c.snapshot(commit=20)
            echo._COMMANDS[c.command]['display_witness']=witness
            # No private registry entry can be restored by replaying an attachment.
            tracker=echo._DISPLAY_TRACKERS[c.command]
            tracker['phase']='CANDIDATE'
            with self.assertRaises(InputProofError): c.command.bind_history(current,3)
            self.assertEqual(c.command.phase,'REVOKED')

    def test_metric_row_movement_before_commit_and_composer_agree(self):
        with DisplayCase() as c:
            c.submit(); current=c.snapshot(commit=20)
            rows=list(current.rows); rows[1],rows[3]=rows[3],rows[1]
            current=replace(current,rows=tuple(rows))
            f=c.fixture
            with mock.patch.object(f.policy,'_empty_input_assessment',wraps=f.policy._empty_input_assessment) as assess:
                assessment,index,_=echo._compose_input_assessment(f.policy,current,frame=3,
                    state=f.state,scope=f.scope,native_owner=f.native,controller_owner=f.controller,
                    transition_owner=f.transition,resume_view=c.view,context_command=c.command)
                self.assertEqual(assess.call_count,1)
            self.assertEqual((assessment.reason,index),('ELIGIBLE',None))
            self.assertIsNotNone(c.command.bind_history(current,3))

    def test_bad_enter_ack_and_late_ui_never_issue_a_witness(self):
        for count in (0,True,2):
            with self.subTest(count=count),DisplayCase() as c:
                c.command.type_bytes(c.baseline,1); c.command.check_edit(c.baseline,1,8)
                echoed=replace(c.snapshot(extra=((37,'❯ /context'),)),cursorX=10)
                c.command.observe(echoed,2); c.command.submit_bytes(echoed,2)
                with self.assertRaises(InputProofError): c.command.submission_written(count)
                self.assertEqual(c.command.phase,'REVOKED')

    def test_composer_rejection_revokes_without_a_bind_caller(self):
        with DisplayCase() as c:
            c.submit(); f=c.fixture
            current=c.snapshot(commit=20,extra=((39,'❯ synthetic unknown'),))
            assessment,index,observation=echo._compose_input_assessment(f.policy,current,frame=3,
                state=f.state,scope=f.scope,native_owner=f.native,controller_owner=f.controller,
                transition_owner=f.transition,resume_view=c.view,context_command=c.command)
            self.assertEqual((assessment.reason,index),('UNSUPPORTED_ROW',39))
            self.assertIsNotNone(observation)
            self.assertEqual(c.command.phase,'REVOKED')
            self.assertEqual(history.resume_view_decision(c.view),'REJECTED')
        for label in ('Do you want to use this API key?','Yes, I trust this folder'):
            with self.subTest(label=label),DisplayCase() as c:
                c.submit(); c.observe(c.snapshot(commit=20),3)
                with self.assertRaises(RuntimeError): c.observe(c.snapshot(commit=20,extra=((6,label),)),4)
                self.assertEqual(c.command.phase,'REVOKED')


if __name__=='__main__': unittest.main()
