"""Observation-only boundaries, synthetic inputs, no installed native runtime."""
import copy
from dataclasses import replace
import unittest
from unittest import mock
import terminal_resume_history as history
import terminal_context_echo as echo
from post_enter_observation_fixtures import ObservationCase
from resume_history_fixtures import CaseFixture


class ObservationGuardTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(callable(getattr(history,'offer_post_enter_observation',None)),
            'observation-only request factory is absent')

    def test_detach_withdraws_view_without_closing_case(self):
        with ObservationCase() as c:
            original=history._CASES[c.fixture.case]['deadline']
            c.submit(); guard=c.detach()
            self.assertEqual(history.resume_view_decision(c.view),'REJECTED')
            self.assertEqual(history._CASES[c.fixture.case]['phase'],'OBSERVING')
            self.assertEqual(history._CASES[c.fixture.case]['deadline'],original)
            self.assertEqual(c.validate_guard(guard),frozenset({5}))
            with self.assertRaises(RuntimeError): c.detach()

    def test_detached_observation_cannot_mint_acceptance(self):
        with ObservationCase() as c:
            c.submit(); c.detach()
            with self.assertRaises(RuntimeError): c.command.bind_history(c.snapshot(commit=20),3)

    def test_guard_does_not_require_retired_command_registry(self):
        with ObservationCase() as c:
            c.submit(); guard=c.detach()
            echo._COMMANDS.pop(c.command,None)
            self.assertEqual(c.validate_guard(guard,c.snapshot(commit=20)),frozenset({5}))

    def test_detach_requires_actual_submission(self):
        with ObservationCase() as c:
            with self.assertRaises(RuntimeError):
                history.detach_post_enter_history(c.request,view=c.view,command=c.command,
                    snapshot=c.baseline,frame=1,controller_owner=c.fixture.controller)

    def test_request_requires_sdk_audit_and_text_case(self):
        with CaseFixture() as f:
            with self.assertRaises(RuntimeError):
                history.offer_post_enter_observation(f.case,state=f.state,scope=f.scope,command=f.resume_command)
        with CaseFixture('skill-turn') as f:
            f.complete_initial(); f.validate_sdk('skill-turn'); f.fresh_terminal()
            with self.assertRaises(RuntimeError):
                history.offer_post_enter_observation(f.case,state=f.state,scope=f.scope,command=f.resume_command)
        with CaseFixture() as f:
            f.complete_initial(); f.validate_sdk('text-turn'); f.fresh_terminal()
            with mock.patch('terminal_input_challenge._audit',side_effect=RuntimeError):
                with self.assertRaises(RuntimeError):
                    history.offer_post_enter_observation(f.case,state=f.state,scope=f.scope,command=f.resume_command)

    def test_guard_owner_lifetime_and_geometry_losses_reject(self):
        for kind in ('native','helper','controller','transition','scope','state','deadline','clock','geometry','case','root'):
            with self.subTest(kind=kind),ObservationCase() as c:
                c.submit(); guard=c.detach(); f=c.fixture; snapshot=c.snapshot(); override={}
                if kind=='native': f.native.returncode=0
                elif kind=='helper': f.state.close()
                elif kind in ('controller','transition','scope','state'):
                    override[{'controller':'controller_owner','transition':'transition_owner'}.get(kind,kind)]=object()
                elif kind=='deadline': history._CASES[f.case]['deadline']=0
                elif kind=='clock': history._CASES[f.case]['time']=float('inf')
                elif kind=='geometry': snapshot=replace(snapshot,viewportY=1)
                elif kind=='case': history.close_offline_case(f.case)
                elif kind=='root': (f.root/'project').rename(f.root/'renamed')
                with self.assertRaises(RuntimeError): c.validate_guard(guard,snapshot,**override)

    def test_guard_preserves_history_retirement(self):
        with ObservationCase() as c:
            c.submit(); guard=c.detach()
            rows=list(c.snapshot().rows); rows[5]=rows[6]
            gone=replace(c.snapshot(),rows=tuple(rows))
            self.assertEqual(c.validate_guard(guard,gone),frozenset())
            with self.assertRaises(RuntimeError): c.validate_guard(guard,c.snapshot(),4)

    def test_guard_rejects_moved_or_replaced_history(self):
        for rows in (((5,'❯ /exit'),),((5,''),(6,'❯ '+history.TEXT_PROMPT))):
            with self.subTest(rows=rows),ObservationCase() as c:
                c.submit(); guard=c.detach()
                with self.assertRaises(RuntimeError):
                    c.validate_guard(guard,c.snapshot(extra=rows))

    def test_copied_or_unbound_guards_never_validate(self):
        with ObservationCase() as c:
            for value in (c.request,):
                for operation in (copy.copy,copy.deepcopy):
                    with self.assertRaises((RuntimeError,TypeError)): operation(value)
            c.submit(); guard=c.detach()
            for value in (True,{},object(),None):
                with self.assertRaises(RuntimeError): c.validate_guard(value)
            history.close_post_enter_history(guard)
            history.close_post_enter_history(guard)
            with self.assertRaises(RuntimeError): c.validate_guard(guard)


class ObservationHandoffTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(callable(getattr(echo,'_prepare_post_enter_observation',None)),
            'owned observation handoff is absent')

    def test_handoff_retires_all_acceptance_paths(self):
        with ObservationCase() as c:
            c.submit(extra=((8,'❯ /context  Synthetic completion'),))
            self.assertEqual(c.observer.phase,'AWAIT_DISPLAY')
            self.assertIs(c.command.post_enter_observation(),c.observer)
            self.assertNotIn(c.command,echo._COMMANDS)
            for method in (c.command.bind_history,c.command.context_display_percent,c.command.type_bytes):
                with self.assertRaises(RuntimeError): method(c.snapshot(commit=20),4)

    def test_handoff_uses_last_writable_wait_frame(self):
        with ObservationCase() as c:
            c.submit(extra=((8,'❯ /context  Synthetic completion'),),wait_free='80')
            import terminal_post_enter_observation as observation
            record=observation._OBSERVATIONS[c.observer]
            self.assertEqual(record['submit_frame'],3)
            self.assertEqual(record['baseline'].used,17)
            self.assertIn(8,record['inventory'])
            self.assertEqual(record['menu_index'],8)

    def test_handoff_rejects_wrong_counts_and_replay(self):
        for count in (0,2,True):
            with self.subTest(count=count),ObservationCase() as c:
                with self.assertRaises(RuntimeError): c.submit(ack=count)
        with ObservationCase() as c:
            c.submit()
            with self.assertRaises(RuntimeError): c.command.submission_written(1)

    def test_handoff_cannot_prepare_from_incomplete_or_foreign_evidence(self):
        with ObservationCase() as c:
            f=c.fixture
            with self.assertRaises(RuntimeError):
                echo._prepare_post_enter_observation(c.command,c.baseline,1,
                    request=c.request,controller_owner=f.controller)
        with ObservationCase() as c:
            c.command.type_bytes(c.baseline,1); c.command.check_edit(c.baseline,1,8)
            current=replace(c.snapshot(extra=((37,'❯ /context'),)),cursorX=10)
            c.command.observe(current,2)
            with self.assertRaises(RuntimeError):
                echo._prepare_post_enter_observation(c.command,current,2,
                    request=c.request,controller_owner=object())

    def test_handoff_preparation_rejects_lost_or_copied_evidence(self):
        for kind in ('partial','snapshot-copy','frame','request','native','helper','deadline','menu'):
            with self.subTest(kind=kind),ObservationCase() as c:
                c.command.type_bytes(c.baseline,1); c.command.check_edit(c.baseline,1,8)
                extra=() if kind=='partial' else ((8,'❯ /context  Synthetic completion'),)
                current=replace(c.snapshot(extra=(*extra,
                    (37,'❯ /conte' if kind=='partial' else '❯ /context'))),cursorX=8 if kind=='partial' else 10)
                c.command.observe(current,2)
                f=c.fixture; request=c.request; frame=2
                if kind=='snapshot-copy': current=replace(current)
                elif kind=='frame': frame=True
                elif kind=='request': request=object()
                elif kind=='native': f.native.returncode=0
                elif kind=='helper': f.state.close()
                elif kind=='deadline': echo._COMMANDS[c.command]['deadline']=0
                elif kind=='menu':
                    current=replace(c.snapshot(extra=((8,'❯ /context  Changed completion'),(37,'❯ /context'))),cursorX=10)
                    frame=3
                with self.assertRaises(RuntimeError):
                    echo._prepare_post_enter_observation(c.command,current,frame,
                        request=request,controller_owner=f.controller)

    def test_handoff_unbranded_view_is_rejected_before_registry_indexing(self):
        with CaseFixture() as f:
            f.fresh_terminal()
            from resume_history_fixtures import history_snapshot
            try:
                echo.begin_context_command(f.scope,f.state,f.native,f.transition,
                    f.policy,history_snapshot(),1,_resume_view={},_controller_owner=f.controller)
            except Exception as error: self.assertIsInstance(error,RuntimeError)
            else: self.fail('unbranded view accepted')


class ObservationClassifierTests(unittest.TestCase):
    def setUp(self):
        import terminal_post_enter_observation as observation
        self.module=observation
        self.assertTrue(callable(getattr(observation.PostEnterObservation,'observe',None)),
            'read-only observational assessment is absent')

    def test_known_menu_does_not_hide_unknown_row(self):
        with ObservationCase() as c:
            menu=((8,'❯ /context  Synthetic completion'),)
            c.submit(extra=menu)
            c.observer.observe(c.snapshot(extra=(*menu,(39,'❯ Unknown input'))),3)
            self.assertEqual(c.observer.summary()['outcome'],'UNSUPPORTED_TRANSITION')
            self.assertEqual(c.observer.summary()['stopCategory'],'UNKNOWN_ROW')
            self.assertFalse(c.observer.candidate_ready)

    def test_menu_and_owned_echo_can_only_wait_without_authority(self):
        with ObservationCase() as c:
            menu=((8,'❯ /context  Synthetic completion'),)
            c.submit(extra=menu)
            c.observer.observe(replace(c.snapshot(extra=(*menu,(37,'❯ /context'))),cursorX=10),3)
            self.assertEqual(c.observer.phase,'AWAIT_DISPLAY')
            self.assertFalse(c.observer.candidate_ready)
            with self.assertRaises(RuntimeError): c.observer.summary()
            with self.assertRaises(RuntimeError): c.command.bind_history(c.snapshot(commit=20),4)

    def test_same_cell_history_is_classified_not_promoted(self):
        with ObservationCase() as c:
            c.submit(extra=((8,'❯ /context  Synthetic completion'),))
            c.observer.observe(c.snapshot(commit=8),3)
            self.assertEqual(c.observer.summary()['outcome'],'INVENTORIED_CELL_REPLACEMENT')
            self.assertEqual(c.observer.summary()['commitRelation'],'PREENTER_INVENTORY')

    def test_full_profile_needs_latest_revalidation(self):
        for menu in ((),((8,'❯ /context  Synthetic completion'),)):
            with self.subTest(menu=menu),ObservationCase() as c:
                c.submit(extra=menu)
                self.assertIsNone(c.observer.observe(c.snapshot(),3))
                final=c.snapshot(commit=20)
                c.observer.observe(final,4)
                self.assertTrue(c.observer.candidate_ready)
                with self.assertRaises(RuntimeError): c.observer.summary()
                c.observer.complete(final,4)
                self.assertEqual(c.observer.summary()['outcome'],'CURRENT_PROFILE_OBSERVED')
                self.assertTrue(c.observer.summary()['profileObserved'])
                self.assertNotIn(c.command,echo._COMMANDS)

    def test_menu_and_input_disappearance_are_monotonic(self):
        for kind in ('menu','input'):
            with self.subTest(kind=kind),ObservationCase() as c:
                menu=((8,'❯ /context  Synthetic completion'),)
                c.submit(extra=menu); c.observer.observe(c.snapshot(),3)
                frame=(c.snapshot(extra=menu) if kind=='menu' else
                    replace(c.snapshot(extra=((37,'❯ /context'),)),cursorX=10))
                c.observer.observe(frame,4)
                self.assertEqual(c.observer.summary()['outcome'],'UNSUPPORTED_TRANSITION')
                self.assertFalse(c.observer.summary()['profileObserved'])

    def test_candidate_loss_never_returns_to_waiting(self):
        for bad in ('commit','sample','input','duplicate'):
            with self.subTest(bad=bad),ObservationCase() as c:
                c.submit(); c.observer.observe(c.snapshot(commit=20),3)
                changed=c.snapshot(commit=None if bad=='commit' else 20,
                    free='80' if bad=='sample' else None,
                    extra=((39,'❯ Unknown'),) if bad=='input' else ((21,'❯ /context'),) if bad=='duplicate' else ())
                c.observer.observe(changed,4)
                first=c.observer.summary()
                c.observer.observe(c.snapshot(commit=20),5)
                self.assertEqual(c.observer.summary(),first)
                self.assertNotEqual(first['outcome'],'CURRENT_PROFILE_OBSERVED')

    def test_conflicting_then_restored_sample_cannot_recover(self):
        with ObservationCase() as c:
            c.submit(); c.observer.observe(c.snapshot(free='80'),3)
            c.observer.observe(c.snapshot(commit=20),4)
            self.assertEqual(c.observer.summary()['stopCategory'],'NUMERIC_CONFLICT')

    def test_intraframe_numeric_conflicts_survive_later_restoration(self):
        for extra in (((3,'Free space: 80%'),),((3,'Autocompact buffer: 4%'),),
                ((1,'Free space: 99%'),),((1,'Free space: 80% 81%'),)):
            with self.subTest(extra=extra),ObservationCase() as c:
                menu=((8,'❯ /context  Synthetic completion'),)
                c.submit(extra=menu)
                c.observer.observe(c.snapshot(extra=(*menu,*extra)),3)
                self.assertEqual(c.observer.phase,'FINISHED')
                first=c.observer.summary()
                self.assertEqual(first['outcome'],'UNSUPPORTED_TRANSITION')
                self.assertEqual(first['stopCategory'],'NUMERIC_CONFLICT')
                self.assertEqual(first['numericRelation'],'CONFLICT')
                final=c.snapshot(commit=20)
                c.observer.observe(final,4); c.observer.complete(final,4)
                self.assertEqual(c.observer.summary(),first)

    def test_absent_partial_and_equivalent_numeric_rows_are_not_conflicts(self):
        for numeric,extra in ((False,()),(False,((0,'Context Usage'),(2,'Autocompact buffer: 3%'))),
                (True,((3,'Free space: 81.0%'),))):
            with self.subTest(numeric=numeric,extra=extra),ObservationCase() as c:
                c.submit()
                c.observer.observe(c.snapshot(numeric=numeric,extra=extra),3)
                self.assertEqual(c.observer.phase,'AWAIT_DISPLAY')
                final=c.snapshot(commit=20)
                c.observer.observe(final,4); c.observer.complete(final,4)
                self.assertEqual(c.observer.summary()['outcome'],'CURRENT_PROFILE_OBSERVED')

    def test_menu_change_move_duplicate_and_unowned_layout_reject(self):
        for rows in (((8,'❯ /context  Changed'),),((9,'❯ /context  Synthetic completion'),),
                ((8,'❯ /context  Synthetic completion'),(9,'❯ /context  Synthetic completion')),
                ((8,'❯ /model  Synthetic completion'),)):
            with self.subTest(rows=rows),ObservationCase() as c:
                c.submit(extra=((8,'❯ /context  Synthetic completion'),))
                c.observer.observe(c.snapshot(extra=rows),3)
                self.assertEqual(c.observer.summary()['outcome'],'UNSUPPORTED_TRANSITION')

    def test_history_violation_cause_survives_fatal_case_invalidation(self):
        for kind in ('replace','move','retired-return'):
            with self.subTest(kind=kind),ObservationCase() as c:
                c.submit(); frame=3
                if kind=='retired-return':
                    c.observer.observe(c.snapshot(extra=((5,''),)),frame)
                    frame+=1; bad=c.snapshot()
                else:
                    bad=c.snapshot(extra=((5,'❯ /exit'),) if kind=='replace' else
                        ((5,''),(6,'❯ '+history.TEXT_PROMPT)))
                c.observer.observe(bad,frame)
                result=c.observer.summary()
                self.assertEqual(result['outcome'],'UNSUPPORTED_TRANSITION')
                self.assertEqual(result['stopCategory'],'HISTORY_CONFLICT')
                self.assertFalse(result['profileObserved'])
                self.assertNotIn(c.fixture.case,history._CASES)
                self.assertNotIn(c.request,history._OBS_REQUESTS)
                final=c.snapshot(commit=20)
                c.observer.observe(final,frame+1); c.observer.complete(final,frame+1)
                self.assertEqual(c.observer.summary(),result)
                # The actual one-shot report consumer can read only the frozen
                # closed summary, never a reopened case/guard/input capability.
                self.assertEqual(history.take_post_enter_result(c.request),result)
                self.assertIsNone(history.take_post_enter_result(c.request))

    def test_observer_owner_deadline_auth_geometry_and_frame_guards(self):
        for kind in ('native','helper','deadline','auth','geometry','stale','bool','case'):
            with self.subTest(kind=kind),ObservationCase() as c:
                c.submit(); frame=3; current=c.snapshot(commit=20)
                if kind=='native': c.fixture.native.returncode=0
                elif kind=='helper': c.fixture.state.close()
                elif kind=='deadline': self.module._OBSERVATIONS[c.observer]['deadline']=0
                elif kind=='auth': current=c.snapshot(extra=((9,'Do you want to use this API key?'),))
                elif kind=='geometry': current=replace(current,baseY=1)
                elif kind=='stale': frame=2
                elif kind=='bool': frame=True
                elif kind=='case': history.close_offline_case(c.fixture.case)
                c.observer.observe(current,frame)
                self.assertEqual(c.observer.phase,'FINISHED')
                self.assertFalse(c.observer.summary()['profileObserved'])

    def test_unsupported_input_cells_and_unowned_completion_stop(self):
        for kind in ('draft','wide','invisible','unowned-menu'):
            with self.subTest(kind=kind),ObservationCase() as c:
                c.submit(); current=c.snapshot(commit=20)
                if kind=='unowned-menu': current=c.snapshot(extra=((8,'❯ /context  Synthetic completion'),))
                else:
                    rows=list(current.rows); row=list(rows[37])
                    row[2]=replace(row[2],text='X' if kind=='draft' else '\u200b' if kind=='invisible' else '',
                        width=2 if kind=='wide' else 1)
                    rows[37]=tuple(row); current=replace(current,rows=tuple(rows))
                c.observer.observe(current,3)
                self.assertEqual(c.observer.phase,'FINISHED')
                self.assertFalse(c.observer.summary()['profileObserved'])


if __name__=='__main__': unittest.main()
