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
            echo._COMMANDS.pop(c.command)
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


if __name__=='__main__': unittest.main()
