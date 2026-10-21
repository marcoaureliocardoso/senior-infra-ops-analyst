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


class AcceptancePendingTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(callable(getattr(echo,'_prepare_acceptance_pending',None)),
            'acceptance-owned passive preparation is absent')

    def test_acceptance_pending_keeps_known_menu_and_echo_non_writable(self):
        for kind in ('text-turn','skill-turn'):
            for free,want in (('81',16),('80',17)):
                with self.subTest(kind=kind,free=free),DisplayCase(case_kind=kind,acceptance_pending=True) as c:
                    menu=(8,'❯ /context  Synthetic completion')
                    c.submit(extra=(menu,))
                    waiting=replace(c.snapshot(free=free,extra=(menu,(37,'❯ /context'))),cursorX=10)
                    self.assertIsNone(c.observe(waiting,3))
                    self.assertNotIn('display_witness',echo._COMMANDS[c.command])
                    self.assertEqual(history.resume_view_decision(c.view),'VALID')
                    current=c.snapshot(free=free,commit=20)
                    self.assertEqual(c.observe(current,4),want)
                    self.assertIsNotNone(c.command.bind_history(current,4))
                    with self.assertRaises(RuntimeError): c.command.bind_history(current,4)

    def test_direct_final_needs_no_transient_or_delay(self):
        for kind in ('text-turn','skill-turn'):
            with self.subTest(kind=kind),DisplayCase(case_kind=kind,acceptance_pending=True) as c:
                c.submit()
                current=c.snapshot(commit=20)
                self.assertEqual(c.observe(current,3),16)
                self.assertIsNotNone(c.command.bind_history(current,3))

    def test_pending_is_not_empty_input_or_bind_authority(self):
        for operation in ('bind','compose'):
            with self.subTest(operation=operation),DisplayCase(acceptance_pending=True) as c:
                c.submit(extra=((8,'❯ /context  Synthetic completion'),))
                current=c.snapshot(extra=((8,'❯ /context  Synthetic completion'),))
                self.assertIsNone(c.observe(current,3))
                with self.assertRaises(RuntimeError):
                    if operation=='bind': c.command.bind_history(current,3)
                    else:
                        f=c.fixture
                        echo._compose_input_assessment(f.policy,current,frame=3,state=f.state,scope=f.scope,
                            native_owner=f.native,controller_owner=f.controller,transition_owner=f.transition,
                            resume_view=c.view,context_command=c.command)
                self.assertEqual(c.command.phase,'REVOKED')
                with self.assertRaises(RuntimeError): c.observe(c.snapshot(commit=20),4)

    def assert_terminal_rejection(self,c,snapshot,frame=3):
        with self.assertRaises(RuntimeError): c.observe(snapshot,frame)
        self.assertEqual(c.command.phase,'REVOKED')
        self.assertEqual(history.resume_view_decision(c.view),'REJECTED')
        self.assertNotIn(c.command,echo._ACCEPTANCE_BINDINGS)
        with self.assertRaises(RuntimeError): c.observe(c.snapshot(commit=20),frame+1)

    def test_transient_plus_later_unknown_or_auth_row_rejects(self):
        for tail in ('❯ unknown','Do you want to use this API key?','Press Esc to close'):
            with self.subTest(tail=tail),DisplayCase(acceptance_pending=True) as c:
                menu=(8,'❯ /context  Synthetic completion'); c.submit(extra=(menu,))
                self.assert_terminal_rejection(c,c.snapshot(extra=(menu,(15,tail))))

    def test_transient_disappearance_is_monotonic(self):
        menu=(8,'❯ /context  Synthetic completion')
        for mutation in ('move','mutate','duplicate','unbound','reappear','echo-return','draft','width','cursor'):
            with self.subTest(mutation=mutation),DisplayCase(acceptance_pending=True) as c:
                c.submit(extra=() if mutation=='unbound' else (menu,))
                if mutation in ('reappear','echo-return'):
                    self.assertIsNone(c.observe(c.snapshot(),3))
                extra=(menu,)
                if mutation=='move': extra=((9,menu[1]),)
                elif mutation=='mutate': extra=((8,menu[1]+' X'),)
                elif mutation=='duplicate': extra=(menu,(9,menu[1]))
                elif mutation=='draft': extra=(menu,(37,'❯ draft'))
                elif mutation=='echo-return': extra=((37,'❯ /context'),)
                current=c.snapshot(extra=extra)
                if mutation in ('echo-return','cursor'): current=replace(current,cursorX=10 if mutation=='echo-return' else 3)
                if mutation=='width':
                    from terminal_state_adapter import TerminalCell
                    rows=list(current.rows); row=list(rows[8]); row[0]=TerminalCell('❯',2)
                    rows[8]=tuple(row); current=replace(current,rows=tuple(rows))
                self.assert_terminal_rejection(c,current,4 if mutation in ('reappear','echo-return') else 3)

    def test_incomplete_numeric_conflicts_survive_restoration(self):
        for extra in (((0,'Free space: 81% 80%'),),((0,'Autocompact buffer: 3% 4%'),),
                ((0,'Free space: 101%'),),((0,'Free space: 99%'),(1,'Autocompact buffer: 3%'))):
            with self.subTest(extra=extra),DisplayCase(acceptance_pending=True) as c:
                c.submit()
                self.assert_terminal_rejection(c,c.snapshot(numeric=False,extra=extra))

    def test_malformed_numeric_tokens_cannot_restore_acceptance(self):
        for text in ('Free space: -1%','Free space: 1000%',
                'Free space: 81% -81%','Autocompact buffer: -3%',
                'Free space: -0.1%','Free space: 1000000.5%',
                'Compact buffer: 1000%'):
            for kind in ('text-turn','skill-turn'):
                with self.subTest(text=text,kind=kind),DisplayCase(case_kind=kind,acceptance_pending=True) as c:
                    c.submit()
                    self.assert_terminal_rejection(c,c.snapshot(numeric=False,extra=((0,text),)))
                    with self.assertRaises(RuntimeError): c.command.bind_history(c.snapshot(commit=20),5)

    def test_candidate_loss_during_revalidation_is_terminal(self):
        for change in ('missing','moved','duplicate','numbers','anchor','menu'):
            with self.subTest(change=change),DisplayCase(acceptance_pending=True) as c:
                menu=(8,'❯ /context  Synthetic completion'); c.submit(extra=(menu,))
                self.assertEqual(c.observe(c.snapshot(commit=20),3),16)
                current=c.snapshot(commit=None if change=='missing' else 21 if change=='moved' else 20,
                    free='80' if change=='numbers' else None,
                    extra=(menu,) if change=='menu' else ((21,'❯ /context'),) if change=='duplicate' else ())
                if change=='anchor': current=replace(current,cursorX=3)
                self.assert_terminal_rejection(c,current,4)

    def test_inventory_pinned_and_retired_cells_never_become_commit(self):
        for mutation in ('menu-cell','old-cell','pinned-mutation','retired-return','no-commit','clear-only'):
            with self.subTest(mutation=mutation),DisplayCase(acceptance_pending=True) as c:
                c.submit(extra=((8,'❯ /context  Synthetic completion'),))
                if mutation in ('no-commit','clear-only'):
                    self.assertIsNone(c.observe(c.snapshot(numeric=mutation!='clear-only'),3))
                    self.assertNotIn('display_witness',echo._COMMANDS[c.command])
                    continue
                if mutation=='retired-return':
                    original=c.history; c.history=()
                    self.assertIsNone(c.observe(c.snapshot(),3)); c.history=original
                if mutation=='pinned-mutation': c.history=((5,'❯ /exit'),)
                self.assert_terminal_rejection(c,c.snapshot(commit=8 if mutation=='menu-cell' else
                    5 if mutation=='old-cell' else 20),4 if mutation=='retired-return' else 3)

    def test_pending_exclusions_end_before_nonce_and_exit(self):
        for phase in ('nonce','exit'):
            with self.subTest(phase=phase),DisplayCase(acceptance_pending=True) as c:
                menu=(8,'❯ /context  Synthetic completion'); c.submit(extra=(menu,))
                current=c.snapshot(commit=20); receipt=c.command.bind_history(current,3); f=c.fixture
                self.assertNotIn(c.command,echo._ACCEPTANCE_BINDINGS)
                probe=NonceInputChallenge(f.scope,f.native,f.transition,f.policy,current,3,
                    context_receipt=receipt,_resume_view=c.view,_controller_owner=f.controller)
                if phase=='nonce':
                    with self.assertRaises(RuntimeError): probe.type_bytes(c.snapshot(commit=20,extra=(menu,)),4)
                else:
                    marker=probe.type_bytes(current,3).decode()
                    echoed=replace(c.snapshot(commit=20,extra=((37,'❯ '+marker),)),cursorX=18)
                    self.assertEqual(probe.observe(echoed,4),'ECHO_MATCHED')
                    self.assertEqual(probe.clear_bytes(echoed,4),b'\x15')
                    self.assertEqual(probe.observe(current,5),'PROVEN')
                    self.assertFalse(probe.consume_exit(probe.ownership_proof(),
                        c.snapshot(commit=20,extra=(menu,)),6,f.native,f.transition))
                self.assertEqual(c.command.phase,'REVOKED')

    def test_preparation_and_acknowledgements_are_owned_one_shot(self):
        for count,remaining,foreign in ((True,8,False),(0,8,False),(9,8,False),(1,True,False),(1,7,False),(8,8,True)):
            with self.subTest(count=count,remaining=remaining,foreign=foreign),DisplayCase(acceptance_pending=True) as c:
                c.command.type_bytes(c.baseline,1)
                with self.assertRaises(RuntimeError):
                    echo._acknowledge_acceptance_edit(c.command,count,remaining=remaining,
                        controller_owner=object() if foreign else c.fixture.controller)
                self.assertEqual(c.command.phase,'REVOKED')
        with DisplayCase(acceptance_pending=True) as c:
            with self.assertRaises(RuntimeError):
                echo._prepare_acceptance_pending(c.command,c.baseline,1,controller_owner=c.fixture.controller)
            self.assertEqual(c.command.phase,'REVOKED')

    def test_pending_owners_frames_and_numeric_restoration_reject(self):
        for mutation in ('native','helper','controller','scope','run','state','transition','view','deadline','copy','backwards','numeric'):
            with self.subTest(mutation=mutation),DisplayCase(acceptance_pending=True) as c:
                c.submit(); current=c.snapshot()
                self.assertIsNone(c.observe(current,3))
                record=echo._COMMANDS[c.command]
                if mutation=='native': c.fixture.native.returncode=0
                elif mutation=='helper': c.fixture.state.close()
                elif mutation=='deadline': record['deadline']=0
                elif mutation=='view': record['resume_view']=object()
                elif mutation in ('controller','scope','run','state','transition'): record[mutation]=object()
                elif mutation=='numeric': self.assertIsNone(c.observe(c.snapshot(free='80'),4))
                bad=copy.copy(current) if mutation=='copy' else c.snapshot(commit=20)
                self.assert_terminal_rejection(c,bad,3 if mutation=='copy' else 2 if mutation=='backwards' else 5)

    def test_pending_cancellation_and_foreign_baseline_cannot_recover(self):
        from terminal_cancellation import TerminalCancelled
        with DisplayCase(acceptance_pending=True) as c:
            c.submit()
            with mock.patch.object(c.fixture.state,'check_cancelled',side_effect=TerminalCancelled()):
                self.assert_terminal_rejection(c,c.snapshot(commit=20))
        with DisplayCase() as c:
            with self.assertRaises(RuntimeError):
                echo._prepare_acceptance_pending(c.command,copy.copy(c.baseline),1,
                    controller_owner=c.fixture.controller)
            self.assertEqual(c.command.phase,'REVOKED')


if __name__=='__main__': unittest.main()
