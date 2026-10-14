"""Correlated offline command echo; no real Claude/provider/browser."""
import importlib
import os
from pathlib import Path
import time
import unittest
from unittest import mock
from dataclasses import replace

import terminal_input_challenge as challenge
from terminal_input_policy import TerminalInputPolicy
from terminal_state_adapter import TerminalState, TerminalCell, TerminalSnapshot, COUNT_KEYS

FACTS={'networkIsolated':True,'operatorStateHidden':True,'capabilitiesDropped':True}


def frame(text='❯\u00a0',x=2,y=37,*,history=(),numeric=False,active='alternate',base=0,viewport=0):
    lines=dict(history)
    if numeric: lines.update({0:'Context Usage',1:'Free space: 81%',2:'Autocompact buffer: 3%'})
    lines[y]=text
    rows=[]
    for index in range(40):
        row=[TerminalCell(char,1) for char in lines.get(index,'')]
        row.extend(TerminalCell('',1) for _ in range(120-len(row)))
        rows.append(tuple(row))
    return TerminalSnapshot(active,x,y,base,viewport,tuple(rows),{key:0 for key in COUNT_KEYS})


class NativeFixture:
    def __init__(self): self.returncode=None
    def poll(self): return self.returncode


class ContextEchoTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(Path(__file__).with_name('terminal_context_echo.py').is_file(),
            'correlated context echo component missing')
        self.m=importlib.import_module('terminal_context_echo')
        patch=mock.patch.object(challenge,'audit_offline_namespace',return_value=FACTS)
        patch.start(); self.addCleanup(patch.stop)
        self.state=TerminalState(Path(os.environ['P004B_TERMINAL_NODE']),
            Path(os.environ['P004B_TERMINAL_MODULE_ROOT']),time.monotonic()+20)
        self.addCleanup(self.state.close)
        self.run=object(); self.owner=object(); self.native=NativeFixture()
        self.scope=challenge.create_offline_probe_issuer().issue_scope(self.state,self.run)
        self.policy=TerminalInputPolicy()
        self.empty=frame(); self.command_echo=frame('❯\u00a0/context',10)
        self.numeric_history=frame(history=((10,'❯ /context'),),numeric=True)

    def begin(self,baseline=None):
        command=self.m.begin_context_command(self.scope,self.state,self.native,self.owner,
            self.policy,baseline or self.empty,1)
        self.addCleanup(command.invalidate,'INPUT_PROBE_REVOKED')
        return command

    def submit(self):
        command=self.begin()
        self.assertEqual(command.type_bytes(self.empty,1),b'/context')
        # Trusted fixture models the actual count returned by the concrete writer.
        command.check_edit(self.empty,1,8)
        self.assertEqual(command.observe(self.command_echo,2),'COMMAND_ECHO_MATCHED')
        self.assertEqual(command.submit_bytes(self.command_echo,2),b'\r')
        command.submission_written(1)
        return command

    def receipt(self):
        return self.submit().bind_history(self.numeric_history,3)

    def assess(self,snapshot,candidate_receipt,number=3,**changes):
        bindings={'receipt':candidate_receipt,'scope':self.scope,'state':self.state,
            'native_owner':self.native,'transition_owner':self.owner,'frame':number,**changes}
        return self.m.assess_context_input(self.policy,snapshot,**bindings)

    def fresh_scope(self):
        self.state=TerminalState(Path(os.environ['P004B_TERMINAL_NODE']),
            Path(os.environ['P004B_TERMINAL_MODULE_ROOT']),time.monotonic()+20)
        self.addCleanup(self.state.close)
        self.run=object(); self.native=NativeFixture(); self.policy=TerminalInputPolicy()
        self.scope=challenge.create_offline_probe_issuer().issue_scope(self.state,self.run)

    def test_exact_command_echo_submission_then_owned_history(self):
        receipt=self.receipt()
        self.assertIs(type(receipt),self.m.ContextEchoReceipt)
        assessment,rejection=self.assess(self.numeric_history,receipt)
        self.assertEqual((assessment.reason,assessment.anchor.row,assessment.anchor.cursorX),('ELIGIBLE',37,2))
        self.assertIsNone(rejection)
        self.assertIsNone(self.policy.empty_input_anchor(self.numeric_history))
        self.assertNotIn('/context',repr(receipt))
        with self.assertRaises(AttributeError): receipt.history_row=0

    def test_coordinates_are_observed_not_pinned(self):
        self.empty=frame(y=30); self.command_echo=frame('❯\u00a0/context',10,30)
        self.numeric_history=frame(y=30,history=((8,'❯ /context'),),numeric=True)
        assessment,_=self.assess(self.numeric_history,self.receipt())
        self.assertEqual(assessment.anchor.row,30)

    def test_partial_echo_cannot_submit_until_complete(self):
        command=self.begin(); command.type_bytes(self.empty,1)
        command.check_edit(self.empty,1,4)
        self.assertEqual(command.observe(frame('❯\u00a0/con',6),2),'EDIT_PENDING')
        with self.assertRaises(challenge.InputProofError): command.submit_bytes(frame('❯\u00a0/con',6),2)
        self.assertEqual(command.phase,'REVOKED')

    def test_observed_echo_cannot_exceed_written_prefix(self):
        command=self.begin(); command.type_bytes(self.empty,1)
        command.check_edit(self.empty,1,4)
        with self.assertRaises(challenge.InputProofError): command.observe(self.command_echo,2)
        self.assertEqual(command.phase,'REVOKED')

    def test_write_ack_or_stale_grid_cannot_bind_history(self):
        command=self.begin()
        with self.assertRaises(challenge.InputProofError): command.bind_history(self.numeric_history,2)
        # A separate scope is required after failure; no retry of the revoked command.
        terminal=TerminalState(Path(os.environ['P004B_TERMINAL_NODE']),
            Path(os.environ['P004B_TERMINAL_MODULE_ROOT']),time.monotonic()+10)
        self.addCleanup(terminal.close)
        self.scope=challenge.create_offline_probe_issuer().issue_scope(terminal,object()); self.state=terminal
        old=frame(numeric=True)
        self.empty=old; self.command_echo=frame('❯\u00a0/context',10,numeric=True)
        command=self.submit()
        with self.assertRaises(challenge.InputProofError): command.bind_history(self.numeric_history,3)

    def test_preexisting_resume_echo_and_duplicate_rows_rejected(self):
        with self.assertRaises(challenge.InputProofError): self.begin(self.numeric_history)
        with self.assertRaises(challenge.InputProofError): self.begin()
        self.fresh_scope()
        command=self.submit()
        duplicate=frame(history=((10,'❯ /context'),(11,'❯ /context')),numeric=True)
        with self.assertRaises(challenge.InputProofError): command.bind_history(duplicate,3)

    def test_no_history_needs_no_exception_but_binding_stays_one_shot(self):
        command=self.submit(); plain=frame(numeric=True)
        self.assertIsNone(command.bind_history(plain,3))
        self.assertIsNotNone(self.policy.empty_input_anchor(plain))
        with self.assertRaises(challenge.InputProofError): command.bind_history(self.numeric_history,4)

    def test_receipt_constructor_serialized_host_foreign_or_replayed_rejected(self):
        with self.assertRaises(challenge.InputProofError): self.m.ContextEchoReceipt()
        with mock.patch.object(challenge,'audit_offline_namespace',side_effect=challenge.InputProofError('INPUT_PROBE_SCOPE_REJECTED')):
            with self.assertRaises(challenge.InputProofError): self.begin()
        receipt=self.receipt()
        with self.assertRaises(challenge.InputProofError): self.begin()
        for changes in ({'receipt':{}},{'scope':{}},{'state':object()},
                {'native_owner':NativeFixture()},{'transition_owner':object()}):
            self.fresh_scope(); receipt=self.receipt()
            with self.assertRaises(challenge.InputProofError): self.assess(self.numeric_history,receipt,**changes)

    def test_history_change_disappearance_or_geometry_change_revokes(self):
        variants=(frame(history=((10,'❯ /exit'),),numeric=True),frame(numeric=True),
            frame(history=((11,'❯ /context'),),numeric=True),
            replace(self.numeric_history,active='normal'),replace(self.numeric_history,viewportY=1))
        for changed in variants:
            # Each variant needs its own original capability; rejection is irreversible.
            terminal=TerminalState(Path(os.environ['P004B_TERMINAL_NODE']),
                Path(os.environ['P004B_TERMINAL_MODULE_ROOT']),time.monotonic()+10)
            self.addCleanup(terminal.close)
            self.state=terminal; self.scope=challenge.create_offline_probe_issuer().issue_scope(terminal,object())
            receipt=self.receipt()
            with self.assertRaises(challenge.InputProofError): self.assess(changed,receipt,4)
            with self.assertRaises(challenge.InputProofError): self.assess(self.numeric_history,receipt,5)

    def test_shared_assessment_preserves_default_order_and_actual_rejection(self):
        receipt=self.receipt()
        unknown=frame(history=((10,'❯ /context'),(12,'❯ unknown')),numeric=True)
        assessment,observation=self.assess(unknown,receipt,4)
        self.assertEqual((assessment.reason,assessment.rowRelation,assessment.rowCause),
            ('UNSUPPORTED_ROW','OTHER_CAPTURED_ROW','UNRECOGNIZED_SHAPE'))
        self.assertEqual(self.policy.empty_input_assessment(unknown).rowCause,'CONTROL_COMMAND_SHAPE')
        error=challenge.InputProofError('INPUT_PROBE_INELIGIBLE',assessment.reason,
            input_row_relation=assessment.rowRelation,input_row_cause=assessment.rowCause)
        self.m.attach_context_rejection(error,observation)
        self.assertEqual(self.m.context_rejection_projection(error,unknown,self.policy),(True,12))
        self.assertNotIn('unknown',repr(observation))

    def test_rejection_projection_is_snapshot_bound_and_non_authoritative(self):
        receipt=self.receipt()
        unknown=frame(history=((10,'❯ /context'),(12,'❯ unknown')),numeric=True)
        assessment,observation=self.assess(unknown,receipt,4)
        error=challenge.InputProofError('INPUT_PROBE_INELIGIBLE',assessment.reason,
            input_row_relation=assessment.rowRelation,input_row_cause=assessment.rowCause)
        self.m.attach_context_rejection(error,observation)
        self.assertEqual(self.m.context_rejection_projection(error,replace(unknown),self.policy),(True,None))
        with self.assertRaises(challenge.InputProofError): self.assess(unknown,observation,4)
        ordinary=challenge.InputProofError('INPUT_PROBE_REVOKED')
        self.assertEqual(self.m.context_rejection_projection(ordinary,unknown,self.policy),(False,None))

    def test_expiry_backward_clock_cancellation_helper_or_native_loss(self):
        receipt=self.receipt()
        with mock.patch.object(self.m,'_now',return_value=self.state.operation_deadline):
            with self.assertRaises(challenge.InputProofError) as caught: self.assess(self.numeric_history,receipt,4)
        self.assertEqual(caught.exception.reason,'INPUT_PROBE_DEADLINE')
        with self.assertRaises(challenge.InputProofError): self.assess(self.numeric_history,receipt,5)

    def test_native_exit_revokes_receipt(self):
        receipt=self.receipt(); self.native.returncode=0
        with self.assertRaises(challenge.InputProofError): self.assess(self.numeric_history,receipt,4)

    def test_helper_loss_revokes_receipt(self):
        receipt=self.receipt(); self.state.close()
        with self.assertRaises(challenge.InputProofError): self.assess(self.numeric_history,receipt,4)

    def test_auth_menu_and_cancellation_revoke_receipt(self):
        receipt=self.receipt()
        with mock.patch.object(self.state,'check_cancelled',side_effect=RuntimeError('synthetic cancellation')):
            with self.assertRaises(RuntimeError): self.assess(self.numeric_history,receipt,4)
        with self.assertRaises(challenge.InputProofError): self.assess(self.numeric_history,receipt,5)

    def test_auth_and_menu_revoke_without_recovery(self):
        for text in ('Do you want to use this API key?','Yes, I trust this folder','Press Esc to close'):
            self.fresh_scope(); receipt=self.receipt()
            forbidden=frame(history=((10,'❯ /context'),(12,text)),numeric=True)
            with self.assertRaises(challenge.InputProofError): self.assess(forbidden,receipt,4)
            with self.assertRaises(challenge.InputProofError): self.assess(self.numeric_history,receipt,5)

    def test_backward_clock_and_stale_frame_revoke(self):
        receipt=self.receipt()
        with mock.patch.object(self.m,'_now',return_value=0):
            with self.assertRaises(challenge.InputProofError) as caught: self.assess(self.numeric_history,receipt,4)
        self.assertEqual(caught.exception.reason,'INPUT_PROBE_DEADLINE')
        self.fresh_scope(); receipt=self.receipt()
        with self.assertRaises(challenge.InputProofError): self.assess(self.numeric_history,receipt,2)

    def test_nonfinite_initial_clock_cannot_create_command(self):
        now=time.monotonic()
        with mock.patch.object(self.m,'_now',side_effect=(float('nan'),now)):
            with self.assertRaises(challenge.InputProofError): self.begin()

    def test_unsupported_cells_in_history_cannot_bind(self):
        for text in ('❯\u2003/context','❯\u200b/context','❯ /context extra'):
            self.fresh_scope(); command=self.submit()
            bad=frame(history=((10,text),),numeric=True)
            with self.assertRaises(challenge.InputProofError): command.bind_history(bad,3)

    def test_complete_exact_partial_progress_can_submit_once(self):
        command=self.begin(); command.type_bytes(self.empty,1)
        command.check_edit(self.empty,1,4)
        partial=frame('❯\u00a0/con',6)
        self.assertEqual(command.observe(partial,2),'EDIT_PENDING')
        command.check_edit(partial,2,8)
        self.assertEqual(command.observe(self.command_echo,3),'COMMAND_ECHO_MATCHED')
        self.assertEqual(command.submit_bytes(self.command_echo,3),b'\r')
        command.submission_written(1)
        receipt=command.bind_history(self.numeric_history,4)
        self.assertIs(type(receipt),self.m.ContextEchoReceipt)
        with self.assertRaises(challenge.InputProofError): command.submit_bytes(self.command_echo,5)


if __name__=='__main__': unittest.main()
