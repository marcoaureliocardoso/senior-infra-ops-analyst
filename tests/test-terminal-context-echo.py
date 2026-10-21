"""Correlated offline command echo; no real Claude/provider/browser."""
import importlib
import os
from pathlib import Path
import time
import unittest
from unittest import mock
from dataclasses import replace

import terminal_input_challenge as challenge
from terminal_input_policy import TerminalInputPolicy, EmptyInputAssessment
from terminal_state_adapter import TerminalState, TerminalCell, TerminalSnapshot, COUNT_KEYS
from terminal_context_diagnostics import _create_context_journal, ContextFailureJournal
from terminal_cancellation import TerminalCancelled

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

    def test_correlated_completion_full_echo_above_below(self):
        for index,description in ((8,'Synthetic A'),(39,'Δelta fixture')):
            self.fresh_scope(); command,_,_=self.diagnostic_edit()
            current=frame('❯\u00a0/context',10,history=((index,'❯ /context  '+description),))
            original=current.rows
            with mock.patch.object(self.policy,'_empty_input_assessment',wraps=self.policy._empty_input_assessment) as assess:
                self.assertEqual(command.observe(current,2),'COMMAND_ECHO_MATCHED')
            self.assertEqual(assess.call_count,1)
            self.assertEqual(assess.call_args.kwargs,{'excluded_row':index})
            self.assertIs(current.rows,original)
            self.assertEqual(command.submit_bytes(current,2),b'\r')
            self.assertEqual(command.observe(replace(current),3),'SUBMIT_PENDING')
            self.assertIsNone(self.policy.empty_input_anchor(current))

    def test_correlated_completion_origin_and_baseline(self):
        self.assertTrue(hasattr(self.m,'_correlated_menu_row'),'owned menu correlation missing')
        current=frame('❯\u00a0/context',10,history=((8,'❯ /context  Synthetic A'),))
        with self.assertRaises(challenge.InputProofError): self.begin(frame(history=((8,'❯ /context  Synthetic A'),)))
        for field in ('_menu_origin','scope','state','native','transition','run','deadline','anchor','row',
                'baseline-copy','origin-copy','selection-copy','selection-frame-copy'):
            self.fresh_scope(); command,journal,bindings=self.diagnostic_edit()
            record=self.m._COMMANDS[command]
            # A copied dict must not alter the actual owner's phase or journal.
            with self.assertRaises(challenge.InputProofError) as copied:
                self.m._correlated_menu_row(dict(record),current)
            self.assertEqual(copied.exception.reason,'INPUT_PROBE_SCOPE_REJECTED')
            self.assertEqual(command.phase,'EDIT_PENDING')
            self.assertIsNone(journal.project_fields(copied.exception,**bindings))
            self.assertEqual(command.observe(current,2),'COMMAND_ECHO_MATCHED')
            if field=='_menu_origin': record.pop(field)
            elif field=='baseline-copy':
                value=list(record['_menu_origin']); value[1]=replace(value[1]); record['_menu_origin']=tuple(value)
            elif field=='origin-copy': record['_menu_origin']=tuple(list(record['_menu_origin']))
            elif field=='selection-copy': record['_menu_selection']=tuple(list(record['_menu_selection']))
            elif field=='selection-frame-copy':
                value=list(record['_menu_selection']); value[2]=replace(value[2]); record['_menu_selection']=tuple(value)
            elif field=='deadline': record[field]-=1
            elif field=='anchor': record[field]=replace(record[field])
            elif field=='row': record[field]=tuple(list(record[field]))
            elif field=='native': record[field]=NativeFixture()
            else: record[field]=object()
            with self.assertRaises(challenge.InputProofError):
                command.submit_bytes(current,3)
            self.assertEqual(command.phase,'REVOKED')
            self.assertNotIn(command,self.m._MENU_BINDINGS)
            self.assertNotIn('_menu_origin',record); self.assertNotIn('_menu_selection',record)
        self.fresh_scope(); first,_,_=self.diagnostic_edit(); first.observe(current,2)
        first_record=self.m._COMMANDS[first]
        self.fresh_scope(); second,_,_=self.diagnostic_edit(); second_record=self.m._COMMANDS[second]
        second_record['_menu_origin']=first_record['_menu_origin']
        second_record['_menu_selection']=first_record['_menu_selection']
        with self.assertRaises(challenge.InputProofError): second.observe(current,2)
        self.assertEqual(first.phase,'COMMAND_ECHO_MATCHED')
        self.assertIn(first,self.m._MENU_BINDINGS)
        self.assertNotIn(second,self.m._MENU_BINDINGS)

    def test_correlated_completion_partial_or_wrong_echo(self):
        menu=((8,'❯ /context  Synthetic A'),)
        cases=[(written,frame('❯\u00a0'+'/context'[:echoed],2+echoed,history=menu))
            for written,echoed in ((0,0),(4,4),(7,7),(4,8),(8,7))]
        cases += [(8,current) for current in (
            frame('❯ /context',10,history=menu),frame('❯\u00a0/context X',10,history=menu),
            frame('❯\u00a0/contexX',10,history=menu),frame('❯\u00a0/context',9,history=menu),
            frame('❯\u00a0/context',10,history=menu,active='normal'),
            frame('❯\u00a0/context',10,history=menu,viewport=1),
            frame('❯\u00a0/context',10,history=((8,'❯ /exit  Synthetic A'),)))]
        for written,current in cases:
            self.fresh_scope(); command=self.begin(); command.type_bytes(self.empty,1)
            command.check_edit(self.empty,1,written)
            with self.assertRaises(challenge.InputProofError): command.observe(current,2)
            self.assertEqual(command.phase,'REVOKED')
        self.fresh_scope(); command,_,_=self.diagnostic_edit()
        with self.assertRaises(challenge.InputProofError): command.observe(frame('❯\u00a0/context',10,history=menu),1)

    def test_correlated_completion_loss_is_irreversible(self):
        current=frame('❯\u00a0/context',10,history=((8,'❯ /context  Synthetic A'),))
        variants=[self.command_echo,
            frame('❯\u00a0/context',10,history=((8,'❯ /context  Synthetic B'),)),
            frame('❯\u00a0/context',10,history=((9,'❯ /context  Synthetic A'),)),
            frame('❯\u00a0/context',10,history=((8,'❯ /context  Synthetic A'),(9,'❯ /context  Synthetic B'))),
            frame('❯\u00a0/context',10,history=((8,'❯ /context  Synthetic A'),(9,'Press Esc to close'))),
            replace(current,active='normal'),replace(current,viewportY=1)]
        for changed in variants+['expiry','cancel','helper','native']:
            self.fresh_scope(); command,journal,bindings=self.diagnostic_edit()
            command.observe(current,2); deadline=self.m._COMMANDS[command]['deadline']
            patch=(mock.patch.object(self.m,'_now',return_value=deadline) if changed=='expiry' else
                mock.patch.object(self.state,'check_cancelled',side_effect=TerminalCancelled()) if changed=='cancel' else
                mock.patch.object(self.native,'poll',return_value=0) if changed=='native' else mock.patch.object(self.m,'_now',wraps=self.m._now))
            if changed=='helper': self.state.close()
            with patch:
                with self.assertRaises((challenge.InputProofError,TerminalCancelled)):
                    command.observe(changed if type(changed) is TerminalSnapshot else current,3)
            with self.assertRaises(challenge.InputProofError): command.submit_bytes(current,4)
            record=self.m._COMMANDS[command]
            self.assertEqual(record['deadline'],deadline); self.assertNotIn(command,self.m._MENU_BINDINGS)
            self.assertNotIn('_menu_origin',record); self.assertNotIn('_menu_selection',record)

    def test_correlated_completion_other_rejection_provenance(self):
        for enabled in (False,True,'lost'):
            self.fresh_scope(); command,journal,bindings=self.diagnostic_edit(); record=self.m._COMMANDS[command]
            observer=None
            if enabled:
                observer=self.m._create_edit_row_observer(**bindings,journal=journal)
                self.addCleanup(observer.finish); observer.bind_command(record); record['edit_observer']=observer
            current=frame('❯\u00a0/context',10,history=((8,'❯ /context  Synthetic A'),(12,'❯ unrelated fixture')))
            patch=mock.patch.object(self.m.EditRowObserver,'freeze',side_effect=RuntimeError('observer lost')) if enabled=='lost' else mock.patch.object(self.m,'_now',wraps=self.m._now)
            with patch, mock.patch.object(self.policy,'_empty_input_assessment',wraps=self.policy._empty_input_assessment) as assess:
                with self.assertRaises(challenge.InputProofError) as caught: command.observe(current,2)
            self.assertEqual(assess.call_count,1); self.assertEqual(assess.call_args.kwargs,{'excluded_row':8})
            fields=journal.project_fields(caught.exception,**bindings)
            self.assertEqual(fields['context_command_failure'],{'phase':'EDIT_PENDING','check':'NORMALIZED_ELIGIBILITY','commandBytesWritten':8,'enterBytesWritten':0})
            self.assertEqual(fields['normalized_input_failure'],{'reason':'UNSUPPORTED_ROW','rowRelation':'OTHER_CAPTURED_ROW','rowCause':'UNRECOGNIZED_SHAPE'})
            if enabled is True:
                projection=observer.project(caught.exception,**bindings,journal=journal,snapshot=current)
                self.assertIs(projection[0],current.rows[12])
            elif enabled=='lost': self.assertIsNone(observer.project(caught.exception,**bindings,journal=journal,snapshot=current))
            self.assertNotIn(command,self.m._MENU_BINDINGS)

    def test_correlated_completion_retired_after_enter(self):
        current=frame('❯\u00a0/context',10,history=((8,'❯ /context  Synthetic A'),))
        for action in ('enter','invalidate','bad-ack'):
            self.fresh_scope(); command,_,_=self.diagnostic_edit(); command.observe(current,2)
            command.submit_bytes(current,2); record=self.m._COMMANDS[command]
            self.assertIsNotNone(record['_menu_selection'])
            if action=='enter':
                command.submission_written(1)
                with self.assertRaises(challenge.InputProofError):
                    command.bind_history(frame(history=((8,'❯ /context  Synthetic A'),),numeric=True),3)
            elif action=='invalidate': command.invalidate('INPUT_PROBE_REVOKED')
            else:
                with self.assertRaises(challenge.InputProofError): command.submission_written(0)
            self.assertNotIn(command,self.m._MENU_BINDINGS)
            self.assertNotIn('_menu_origin',record); self.assertNotIn('_menu_selection',record)

    def test_correlated_completion_pre_enter_numeric_not_proof(self):
        for changed_grid in (False,True):
            self.fresh_scope(); self.empty=frame(numeric=True)
            command,_,_=self.diagnostic_edit()
            menu=frame('❯\u00a0/context',10,numeric=True,
                history=((8,'❯ /context  Context Usage Free space: 99%'),))
            command.observe(menu,2)
            before=dict(vars(self.policy)); raw=self.policy._context_signature(menu)
            projected=self.m._preenter_context_signature(self.m._COMMANDS[command],menu)
            self.assertEqual(projected,('Context Usage','Free space: 81%','Autocompact buffer: 3%'))
            self.assertEqual(len(raw),4); self.assertEqual(vars(self.policy),before)
            command.submit_bytes(menu,2); command.observe(replace(menu),3)
            self.assertEqual(self.m._COMMANDS[command]['submit_frame'],3)
            self.assertEqual(self.m._COMMANDS[command]['submit_signature'],projected)
            self.assertEqual(self.policy._context_barrier,raw)
            command.submission_written(1)
            post=frame(numeric=True)
            if changed_grid:
                rows=list(post.rows); text='Free space: 80%'
                rows[1]=tuple([TerminalCell(c,1) for c in text]+[TerminalCell('',1)]*(120-len(text)))
                post=replace(post,rows=tuple(rows))
                self.assertIsNone(command.bind_history(post,4))
            else:
                with self.assertRaises(challenge.InputProofError): command.bind_history(post,4)

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

    def test_transient_grid_cannot_refresh_restored_pre_submission_grid(self):
        self.empty=frame(numeric=True)
        self.command_echo=frame('❯\u00a0/context',10,numeric=True)
        command=self.submit()
        transient=frame(numeric=True); rows=list(transient.rows)
        text='Free space: 80%'
        rows[1]=tuple([TerminalCell(c,1) for c in text]+[TerminalCell('',1)]*(120-len(text)))
        transient=replace(transient,rows=tuple(rows))
        self.policy.authentication(transient)  # Same passive observation as the concrete pump.
        command.observe(transient,3)
        with self.assertRaises(challenge.InputProofError): command.bind_history(self.numeric_history,4)

    def test_numeric_observed_during_submission_wait_cannot_supply_post_enter_evidence(self):
        command=self.begin(); command.type_bytes(self.empty,1); command.check_edit(self.empty,1,8)
        command.observe(self.command_echo,2); command.submit_bytes(self.command_echo,2)
        before_enter=frame('❯\u00a0/context',10,numeric=True)
        self.policy.authentication(before_enter)
        self.assertEqual(command.observe(before_enter,3),'SUBMIT_PENDING')
        command.submission_written(1)
        with self.assertRaises(challenge.InputProofError): command.bind_history(self.numeric_history,4)
        self.assertEqual(command.phase,'REVOKED')

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

    def diagnostic_begin(self,baseline=None):
        bindings={'controller_owner':object(),'scope':self.scope,'state':self.state,'transition_owner':self.owner}
        journal=_create_context_journal(**bindings); self.addCleanup(journal.finish)
        command=self.m.begin_context_command(self.scope,self.state,self.native,self.owner,
            self.policy,baseline or self.empty,1,_diagnostic_journal=journal)
        self.addCleanup(command.invalidate,'INPUT_PROBE_REVOKED')
        return command,journal,bindings

    def diagnostic_edit(self):
        command,journal,bindings=self.diagnostic_begin()
        command.type_bytes(self.empty,1); journal.acknowledge(8,submission=False,remaining=8)
        command.check_edit(self.empty,1,8)
        return command,journal,bindings

    def edit_row_fixture(self,**changes):
        self.assertTrue(callable(getattr(self.m,'_create_edit_row_observer',None)),
            'sealed edit-row observer missing')
        command,journal,bindings=self.diagnostic_edit()
        record=self.m._COMMANDS[command]
        observer=self.m._create_edit_row_observer(**bindings,journal=journal)
        self.addCleanup(observer.finish); observer.bind_command(record)
        snapshot=frame('❯\u00a0/context',10,history=((8,'❯ /context synthetic description'),))
        rows=list(snapshot.rows); rows[37]=self.empty.rows[37]
        assessment,index=self.policy._empty_input_assessment(replace(snapshot,cursorX=2,rows=tuple(rows)))
        error=challenge.InputProofError('INPUT_PROBE_REVOKED')
        detail={'reason':'UNSUPPORTED_ROW','rowRelation':'OTHER_CAPTURED_ROW','rowCause':'UNRECOGNIZED_SHAPE'}
        journal.freeze(error,'NORMALIZED_ELIGIBILITY',normalized_input_failure=detail)
        observer.freeze(error,'NORMALIZED_ELIGIBILITY',command_record=record,snapshot=snapshot,
            assessment=assessment,rejected_index=index,**changes)
        return observer,error,snapshot,record,journal,{**bindings,'journal':journal,'snapshot':snapshot}

    def test_edit_row_first_failure_binding(self):
        observer,error,snapshot,record,journal,bindings=self.edit_row_fixture()
        record['phase']='REVOKED'
        with mock.patch.object(self.policy,'_empty_input_assessment',side_effect=AssertionError('reclassified')),\
                mock.patch.object(self.m,'_now',side_effect=AssertionError('clock read')):
            projected=observer.project(error,**bindings)
        self.assertIsNotNone(projected)
        self.assertIs(projected[0],snapshot.rows[8]); self.assertEqual(projected[1],record['deadline'])
        self.assertEqual(len(journal.project(error,**{k:v for k,v in bindings.items() if k not in ('journal','snapshot')})),4)
        observer.finish(); self.assertIsNone(observer.project(error,**bindings))

    def test_edit_row_missing_first_cannot_enrich(self):
        self.assertTrue(callable(getattr(self.m,'_create_edit_row_observer',None)),
            'sealed edit-row observer missing')
        command,journal,bindings=self.diagnostic_edit(); record=self.m._COMMANDS[command]
        observer=self.m._create_edit_row_observer(**bindings,journal=journal); self.addCleanup(observer.finish)
        observer.bind_command(record)
        error=challenge.InputProofError('INPUT_PROBE_REVOKED')
        observer.freeze(error,'PREFIX_CELLS',command_record=record)
        snapshot=frame('❯\u00a0/context',10,history=((8,'❯ /context synthetic description'),))
        assessment=EmptyInputAssessment(None,'UNSUPPORTED_ROW','OTHER_CAPTURED_ROW','UNRECOGNIZED_SHAPE')
        journal.freeze(error,'NORMALIZED_ELIGIBILITY',normalized_input_failure={
            'reason':'UNSUPPORTED_ROW','rowRelation':'OTHER_CAPTURED_ROW','rowCause':'UNRECOGNIZED_SHAPE'})
        observer.freeze(error,'NORMALIZED_ELIGIBILITY',command_record=record,snapshot=snapshot,
            assessment=assessment,rejected_index=8)
        self.assertIsNone(observer.project(error,**bindings,journal=journal,snapshot=snapshot))
        observer.finish()
        self.assertNotIn('/context',repr(observer))

    def test_edit_row_rejects_foreign_and_equal_replacement_snapshot(self):
        observer,error,snapshot,record,journal,bindings=self.edit_row_fixture()
        for key in ('controller_owner','scope','state','transition_owner','journal'):
            self.assertIsNone(observer.project(error,**{**bindings,key:object()}))
        self.assertIsNone(observer.project(challenge.InputProofError('INPUT_PROBE_REVOKED'),**bindings))
        self.assertIsNone(observer.project(error,**{**bindings,'snapshot':replace(snapshot)}))
        run=record['run']; record['run']=object()
        self.assertIsNone(observer.project(error,**bindings)); record['run']=run
        with self.assertRaises(RuntimeError): observer.bind_command(dict(record))
        self.assertIsNone(observer.project(error,**bindings))

    def test_edit_row_current_or_unmarked_index_is_not_exportable(self):
        for index in (37,9,-1,True,40):
            self.fresh_scope()
            command,journal,bindings=self.diagnostic_edit(); record=self.m._COMMANDS[command]
            observer=self.m._create_edit_row_observer(**bindings,journal=journal)
            self.addCleanup(observer.finish); observer.bind_command(record)
            snapshot=frame('❯\u00a0/context',10,history=((8,'❯ /context synthetic description'),))
            error=challenge.InputProofError('INPUT_PROBE_REVOKED')
            journal.freeze(error,'NORMALIZED_ELIGIBILITY',normalized_input_failure={
                'reason':'UNSUPPORTED_ROW','rowRelation':'OTHER_CAPTURED_ROW','rowCause':'UNRECOGNIZED_SHAPE'})
            observer.freeze(error,'NORMALIZED_ELIGIBILITY',command_record=record,snapshot=snapshot,
                assessment=EmptyInputAssessment(None,'UNSUPPORTED_ROW','OTHER_CAPTURED_ROW','UNRECOGNIZED_SHAPE'),
                rejected_index=index)
            self.assertTrue(observer.project(error,**bindings,journal=journal,snapshot=snapshot) is None,
                'invalid row index became exportable')

    def test_edit_capture_enabled_preserves_single_actual_assessment(self):
        for enabled in (False,True):
            self.fresh_scope()
            bindings={'controller_owner':object(),'scope':self.scope,'state':self.state,'transition_owner':self.owner}
            journal=_create_context_journal(**bindings); self.addCleanup(journal.finish)
            observer=self.m._create_edit_row_observer(**bindings,journal=journal) if enabled else None
            if observer is not None: self.addCleanup(observer.finish)
            command=self.m.begin_context_command(self.scope,self.state,self.native,self.owner,self.policy,self.empty,1,
                _diagnostic_journal=journal,**({'_edit_row_observer':observer} if enabled else {}))
            self.addCleanup(command.invalidate,'INPUT_PROBE_REVOKED')
            command.type_bytes(self.empty,1); journal.acknowledge(8,submission=False,remaining=8)
            command.check_edit(self.empty,1,8)
            snapshot=frame('❯\u00a0/context',10,history=((8,'❯ /context synthetic description'),))
            with mock.patch.object(self.policy,'_empty_input_assessment',wraps=self.policy._empty_input_assessment) as assess:
                with self.assertRaises(challenge.InputProofError) as caught: command.observe(snapshot,2)
            self.assertEqual(assess.call_count,1)
            self.assertEqual(command.phase,'REVOKED')
            self.assertEqual(journal.project(caught.exception,**bindings),{'phase':'EDIT_PENDING',
                'check':'NORMALIZED_ELIGIBILITY','commandBytesWritten':8,'enterBytesWritten':0})
            if enabled:
                projected=observer.project(caught.exception,**bindings,journal=journal,snapshot=snapshot)
                self.assertIsNotNone(projected); self.assertIs(projected[0],snapshot.rows[8])

    def test_edit_bad_observer_cannot_change_rejection(self):
        bindings={'controller_owner':object(),'scope':self.scope,'state':self.state,'transition_owner':self.owner}
        journal=_create_context_journal(**bindings); self.addCleanup(journal.finish)
        command=self.m.begin_context_command(self.scope,self.state,self.native,self.owner,self.policy,self.empty,1,
            _diagnostic_journal=journal,_edit_row_observer=object())
        self.addCleanup(command.invalidate,'INPUT_PROBE_REVOKED')
        command.type_bytes(self.empty,1); journal.acknowledge(8,submission=False,remaining=8)
        command.check_edit(self.empty,1,8)
        with self.assertRaises(challenge.InputProofError) as caught:
            command.observe(frame('❯\u00a0/context',10,history=((8,'❯ /context synthetic description'),)),2)
        self.assertEqual(journal.project(caught.exception,**bindings),{'phase':'EDIT_PENDING',
            'check':'NORMALIZED_ELIGIBILITY','commandBytesWritten':8,'enterBytesWritten':0})

    def test_first_failing_predicate_is_frozen_before_revocation(self):
        cases=((frame('❯ /context',10),'PREFIX_CELLS'),
            (frame('❯\u00a0/context X',10),'TRAILING_CELLS'),
            (frame('❯\u00a0/context',10,history=((8,'❯ /context'),)),'NORMALIZED_ELIGIBILITY'),
            (frame('❯\u00a0/context',10,history=((8,'Press Esc to close'),)),'FORBIDDEN_UI'),
            (frame('❯\u00a0/context',10),'NATIVE_LIFETIME'))
        for snapshot,expected in cases:
            with self.subTest(check=expected):
                self.fresh_scope(); command,journal,bindings=self.diagnostic_edit()
                if expected=='NATIVE_LIFETIME': self.native.returncode=0
                with self.assertRaises(challenge.InputProofError) as caught: command.observe(snapshot,2)
                self.assertEqual(caught.exception.reason,'INPUT_PROBE_REVOKED')
                self.assertEqual(command.phase,'REVOKED')
                self.assertEqual(journal.project(caught.exception,**bindings),{
                    'phase':'EDIT_PENDING','check':expected,'commandBytesWritten':8,'enterBytesWritten':0})

    def test_normalized_suggestion_detail_uses_actual_single_assessment(self):
        for row in (34,39):
            self.fresh_scope(); command,journal,bindings=self.diagnostic_edit()
            snapshot=frame('❯\u00a0/context',10,
                history=((row,'❯ /context Synthetic context usage detail'),))
            self.policy.mark_transition(self.empty); self.policy.authentication(snapshot)
            assessed=[]; original=self.policy.empty_input_assessment
            def assess(value):
                result=original(value); assessed.append((value,result)); return result
            with mock.patch.object(self.policy,'empty_input_assessment',side_effect=assess):
                with self.assertRaises(challenge.InputProofError) as caught: command.observe(snapshot,2)
            self.assertEqual(len(assessed),1)
            self.assertEqual(assessed[0][1].reason,'UNSUPPORTED_ROW')
            self.assertEqual(self.policy.diagnostic_state(assessed[0][0])['readiness'],'READY')
            self.assertEqual(caught.exception.reason,'INPUT_PROBE_REVOKED'); self.assertEqual(command.phase,'REVOKED')
            self.assertEqual(journal.project_fields(caught.exception,**bindings),{
                'context_command_failure':{'phase':'EDIT_PENDING','check':'NORMALIZED_ELIGIBILITY',
                    'commandBytesWritten':8,'enterBytesWritten':0},
                'normalized_input_failure':{'reason':'UNSUPPORTED_ROW','rowRelation':'OTHER_CAPTURED_ROW',
                    'rowCause':'UNRECOGNIZED_SHAPE'}})

    def test_description_freshness_is_not_numeric_or_input_authority(self):
        command,journal,bindings=self.diagnostic_edit()
        snapshot=frame('❯\u00a0/context',10,
            history=((34,'/context   Visualize current context usage as a colored grid'),))
        self.policy.mark_transition(self.empty); self.policy.authentication(snapshot)
        self.assertTrue(self.policy.diagnostic_state(snapshot)['contextFresh'])
        self.assertIsNone(self.policy.context_percent(snapshot))
        self.assertEqual(command.observe(snapshot,2),'COMMAND_ECHO_MATCHED')
        self.assertIsNone(journal.project_fields(challenge.InputProofError('INPUT_PROBE_REVOKED'),**bindings))
        with self.assertRaises(challenge.InputProofError): command.bind_history(snapshot,3)

    def test_normalized_reason_matrix_and_anchor_comparison(self):
        for text,cause in (('❯ /context','CONTROL_COMMAND_SHAPE'),('❯\u200b','INVISIBLE_FORMAT_CHAR'),
                ('❯\u2003','UNSUPPORTED_WHITESPACE'),('❯ synthetic','UNRECOGNIZED_SHAPE'),('wide','MARKER_WIDTH')):
            self.fresh_scope(); command,journal,bindings=self.diagnostic_edit()
            snapshot=frame('❯\u00a0/context',10,history=((8,'❯ ' if text=='wide' else text),))
            if text=='wide':
                rows=list(snapshot.rows); row=list(rows[8]); row[0]=TerminalCell('❯',2); rows[8]=tuple(row)
                snapshot=replace(snapshot,rows=tuple(rows))
            with self.assertRaises(challenge.InputProofError) as caught: command.observe(snapshot,2)
            self.assertEqual(journal.project_fields(caught.exception,**bindings)['normalized_input_failure'],{
                'reason':'UNSUPPORTED_ROW','rowRelation':'OTHER_CAPTURED_ROW','rowCause':cause})
        for reason in ('FORBIDDEN_STATE','NO_MARKER','NONEMPTY_INPUT','MULTIPLE_MARKERS',
                'CURSOR_ROW_MISMATCH','CURSOR_COLUMN_MISMATCH','INSUFFICIENT_SPACE','ANCHOR_CHANGED'):
            self.fresh_scope(); command,journal,bindings=self.diagnostic_edit()
            with mock.patch.object(self.policy,'empty_input_assessment',return_value=EmptyInputAssessment(None,reason)):
                with self.assertRaises(challenge.InputProofError) as caught: command.observe(self.command_echo,2)
            self.assertEqual(caught.exception.reason,'INPUT_PROBE_REVOKED')
            self.assertEqual(journal.project_fields(caught.exception,**bindings)['normalized_input_failure'],{'reason':reason})
        self.fresh_scope(); command,journal,bindings=self.diagnostic_edit()
        anchor=self.policy.empty_input_anchor(self.empty)
        with mock.patch.object(self.policy,'empty_input_assessment',return_value=EmptyInputAssessment(replace(anchor,cursorX=3),'ELIGIBLE')):
            with self.assertRaises(challenge.InputProofError) as caught: command.observe(self.command_echo,2)
        self.assertEqual(journal.project_fields(caught.exception,**bindings)['normalized_input_failure'],{'reason':'ANCHOR_CHANGED'})
        for assessment in (EmptyInputAssessment(None,'unknown'),EmptyInputAssessment(None,'ELIGIBLE'),
                EmptyInputAssessment(None,'UNSUPPORTED_ROW'),EmptyInputAssessment(None,'NO_MARKER','CURSOR_ROW','MARKER_WIDTH')):
            self.fresh_scope(); command,journal,bindings=self.diagnostic_edit()
            with mock.patch.object(self.policy,'empty_input_assessment',return_value=assessment):
                with self.assertRaises(challenge.InputProofError) as caught: command.observe(self.command_echo,2)
            self.assertEqual(caught.exception.reason,'INPUT_PROBE_REVOKED')
            self.assertEqual(set(journal.project_fields(caught.exception,**bindings)),{'context_command_failure'})

    def test_preceding_fault_wins_without_normalized_detail(self):
        command,journal,bindings=self.diagnostic_edit()
        snapshot=frame('❯ /context',10,history=((8,'❯ synthetic'),))
        with self.assertRaises(challenge.InputProofError) as caught: command.observe(snapshot,2)
        fields=journal.project_fields(caught.exception,**bindings)
        self.assertEqual(fields['context_command_failure']['check'],'PREFIX_CELLS')
        self.assertNotIn('normalized_input_failure',fields)

    def test_detail_preparation_or_freeze_failure_preserves_original_rejection(self):
        snapshot=frame('❯\u00a0/context',10,history=((8,'❯ synthetic'),))
        for target in ('prepare','freeze'):
            self.fresh_scope(); command,journal,bindings=self.diagnostic_edit()
            patch=(mock.patch.object(self.m,'_normalized_failure_detail',side_effect=RuntimeError('synthetic observer loss'),create=True)
                if target=='prepare' else mock.patch.object(ContextFailureJournal,'freeze',side_effect=RuntimeError('synthetic observer loss')))
            with patch:
                with self.assertRaises(challenge.InputProofError) as caught: command.observe(snapshot,2)
            self.assertEqual(caught.exception.reason,'INPUT_PROBE_REVOKED'); self.assertEqual(command.phase,'REVOKED')
            fields=journal.project_fields(caught.exception,**bindings)
            if target=='prepare': self.assertEqual(set(fields),{'context_command_failure'})
            else: self.assertIsNone(fields)

    def test_actual_renderer_padding_preserved_or_repainted(self):
        for padding in ('\u00a0',' '):
            self.fresh_scope()
            self.state.feed('\x1b[?1049h\x1b[38;1H❯\u00a0'.encode())
            self.empty=self.state.snapshot()
            command,journal,bindings=self.diagnostic_edit()
            self.state.feed(('\x1b[38;1H❯'+padding+'/context').encode())
            snapshot=self.state.snapshot()
            if padding=='\u00a0':
                self.assertEqual(command.observe(snapshot,2),'COMMAND_ECHO_MATCHED')
                self.assertIsNone(journal.project(challenge.InputProofError('INPUT_PROBE_REVOKED'),**bindings))
            else:
                with self.assertRaises(challenge.InputProofError) as caught: command.observe(snapshot,2)
                self.assertEqual(journal.project(caught.exception,**bindings)['check'],'PREFIX_CELLS')

    def test_rejection_code_matrix_and_short_circuit_order(self):
        cases=(('geometry','ANCHOR_GEOMETRY'),('cursor','CURSOR_PROGRESS'),('body','COMMAND_CELLS'),
            ('frame','FRAME_STATE'),('phase','PHASE_STATE'),('write-count','WRITE_COUNT'),
            ('regression','ECHO_REGRESSION'),('incomplete','INCOMPLETE_ECHO'),('deadline','DEADLINE'),
            ('cancel','CANCELLATION'),('helper','SCOPE_BINDING'),('scope','SCOPE_BINDING'))
        for scenario,expected in cases:
            with self.subTest(scenario=scenario):
                self.fresh_scope(); command,journal,bindings=self.diagnostic_edit()
                try:
                    if scenario=='geometry': command.observe(replace(frame('❯ /contextX',11),cursorY=36),2)
                    elif scenario=='cursor': command.observe(frame('❯ /contextX',11),2)
                    elif scenario=='body': command.observe(frame('❯\u00a0/contExt',10),2)
                    elif scenario=='frame': command.observe(self.command_echo,0)
                    elif scenario=='phase': command.type_bytes(self.empty,2)
                    elif scenario=='write-count': command.check_edit(self.empty,2,7)
                    elif scenario=='regression':
                        command.observe(frame('❯\u00a0/con',6),2); command.observe(frame('❯\u00a0/co',5),3)
                    elif scenario=='incomplete':
                        command.observe(self.command_echo,2)
                        command.submit_bytes(frame('❯\u00a0/con',6),3)
                    elif scenario=='deadline':
                        with mock.patch.object(self.m,'_now',return_value=0): command.observe(self.command_echo,2)
                    elif scenario=='cancel':
                        with mock.patch.object(self.state,'check_cancelled',side_effect=TerminalCancelled()):
                            command.observe(self.command_echo,2)
                    elif scenario=='helper': self.state.close(); command.observe(self.command_echo,2)
                    else:
                        with mock.patch.object(challenge,'_context_scope_binding',return_value=(object(),self.state.operation_deadline)):
                            command.observe(self.command_echo,2)
                except (challenge.InputProofError,TerminalCancelled) as error:
                    self.assertEqual(command.phase,'REVOKED')
                    self.assertEqual(journal.project(error,**bindings)['check'],expected)
                else: self.fail('expected a real rejection')

    def test_fresh_context_first_failure_is_content_free_and_short_circuited(self):
        cases=((2,frame(numeric=True),'FRESH_CONTEXT_FRAME_NOT_ADVANCED'),
            (3,frame(),'FRESH_CONTEXT_SIGNATURE_UNCHANGED'),
            (3,frame(history=((0,'Context Usage'),)),'FRESH_CONTEXT_NUMERIC_UNAVAILABLE'))
        for frame_id,snapshot,expected in cases:
            with self.subTest(check=expected):
                self.fresh_scope(); command,journal,bindings=self.diagnostic_edit()
                command.observe(self.command_echo,2); command.submit_bytes(self.command_echo,2)
                journal.acknowledge(1,submission=True,remaining=1); command.submission_written(1)
                # Later predicates must not run after the first rejection. Real predicates
                # remain in use up to that boundary; no diagnostic-only observations.
                with mock.patch.object(self.policy,'_context_signature',
                        side_effect=AssertionError('signature after frame rejection') if frame_id==2
                        else self.policy._context_signature),\
                        mock.patch.object(self.policy,'context_percent',
                            side_effect=self.policy.context_percent if expected.endswith('NUMERIC_UNAVAILABLE')
                            else AssertionError('numeric observation after earlier rejection')):
                    with self.assertRaises(challenge.InputProofError) as caught:
                        command.bind_history(snapshot,frame_id)
                self.assertEqual(caught.exception.reason,'INPUT_PROBE_STATE_REJECTED')
                self.assertEqual(command.phase,'REVOKED')
                self.assertEqual(journal.project_fields(caught.exception,**bindings),{
                    'context_command_failure':{'phase':'CONTEXT_PENDING','check':expected,
                        'commandBytesWritten':8,'enterBytesWritten':1}})

    def test_fresh_context_observer_loss_cannot_change_rejection_or_revocation(self):
        for snapshot,frame_id in ((frame(numeric=True),2),(frame(),3),
                (frame(history=((0,'Context Usage'),)),3)):
            self.fresh_scope(); command,journal,bindings=self.diagnostic_edit()
            command.observe(self.command_echo,2); command.submit_bytes(self.command_echo,2)
            journal.acknowledge(1,submission=True,remaining=1); command.submission_written(1)
            with mock.patch.object(ContextFailureJournal,'freeze',side_effect=RuntimeError('observer loss')):
                with self.assertRaises(challenge.InputProofError) as caught:
                    command.bind_history(snapshot,frame_id)
            self.assertEqual(caught.exception.reason,'INPUT_PROBE_STATE_REJECTED')
            self.assertEqual(command.phase,'REVOKED')
            self.assertIsNone(journal.project_fields(caught.exception,**bindings))

    def test_history_rejection_codes_and_baseline_eligibility(self):
        for scenario,expected in (('fresh','FRESH_CONTEXT_SIGNATURE_UNCHANGED'),('duplicate','HISTORY_AMBIGUITY'),
                ('eligibility','HISTORY_ELIGIBILITY')):
            self.fresh_scope(); command,journal,bindings=self.diagnostic_edit()
            command.observe(self.command_echo,2); command.submit_bytes(self.command_echo,2)
            journal.acknowledge(1,submission=True,remaining=1); command.submission_written(1)
            snapshot=(frame() if scenario=='fresh' else
                frame(history=((10,'❯ /context'),(11,'❯ /context')),numeric=True) if scenario=='duplicate' else
                frame(history=((10,'❯ /context'),(12,'❯ unknown')),numeric=True))
            with self.assertRaises(challenge.InputProofError) as caught: command.bind_history(snapshot,3)
            self.assertEqual(journal.project(caught.exception,**bindings)['check'],expected)
        self.fresh_scope()
        bindings={'controller_owner':object(),'scope':self.scope,'state':self.state,'transition_owner':self.owner}
        journal=_create_context_journal(**bindings); self.addCleanup(journal.finish)
        with self.assertRaises(challenge.InputProofError) as caught:
            self.m.begin_context_command(self.scope,self.state,self.native,self.owner,self.policy,
                frame(history=((10,'❯ /context'),)),1,_diagnostic_journal=journal)
        self.assertEqual(journal.project(caught.exception,**bindings),{
            'phase':'BASELINE','check':'BASELINE_ELIGIBILITY','commandBytesWritten':0,'enterBytesWritten':0})

    def test_optional_observer_failure_preserves_original_revocation(self):
        command,journal,bindings=self.diagnostic_edit()
        with mock.patch.object(ContextFailureJournal,'freeze',side_effect=RuntimeError('observer failed')):
            with self.assertRaises(challenge.InputProofError) as caught: command.observe(frame('❯ /context',10),2)
        self.assertEqual(caught.exception.reason,'INPUT_PROBE_REVOKED'); self.assertEqual(command.phase,'REVOKED')
        self.assertIsNone(journal.project(caught.exception,**bindings))
        self.fresh_scope(); command,journal,bindings=self.diagnostic_begin()
        with mock.patch.object(ContextFailureJournal,'set_phase',side_effect=RuntimeError('observer failed')):
            self.assertEqual(command.type_bytes(self.empty,1),b'/context')
        with self.assertRaises(challenge.InputProofError) as caught: command.observe(frame('❯ /context',10),2)
        self.assertEqual(command.phase,'REVOKED'); self.assertIsNone(journal.project(caught.exception,**bindings))
        self.fresh_scope(); command,journal,bindings=self.diagnostic_edit()
        with mock.patch.object(self.state,'check_cancelled',side_effect=RuntimeError('unknown failure')):
            with self.assertRaises(RuntimeError) as caught: command.observe(self.command_echo,2)
        self.assertIsNone(journal.project(caught.exception,**bindings))


class AcceptanceSubmissionTests(unittest.TestCase):
    def test_actual_body_acknowledgements_not_diagnostic_counts_are_required(self):
        from context_display_fixtures import DisplayCase
        import terminal_context_echo as echo
        for counts in ((),(1,),(4,4)):
            with self.subTest(counts=counts),DisplayCase(acceptance_pending=True) as c:
                self.assertEqual(c.command.type_bytes(c.baseline,1),b'/context')
                total=0
                for count in counts:
                    echo._acknowledge_acceptance_edit(c.command,count,remaining=8-total,
                        controller_owner=c.fixture.controller)
                    total+=count
                c.command.check_edit(c.baseline,1,8)
                c.journal.acknowledge(8,submission=False,remaining=8)
                current=replace(c.snapshot(extra=((37,'❯ /context'),)),cursorX=10)
                self.assertEqual(c.command.observe(current,2),'COMMAND_ECHO_MATCHED')
                self.assertEqual(c.command.submit_bytes(current,2),b'\r')
                if total==8:
                    c.command.submission_written(1)
                    self.assertEqual(c.command.phase,'CONTEXT_PENDING')
                else:
                    with self.assertRaises(RuntimeError): c.command.submission_written(1)
                    self.assertEqual(c.command.phase,'REVOKED')

    def test_last_writable_wait_snapshot_defines_original_transients(self):
        from context_display_fixtures import DisplayCase
        import terminal_context_echo as echo
        with DisplayCase(acceptance_pending=True) as c:
            c.command.type_bytes(c.baseline,1)
            echo._acknowledge_acceptance_edit(c.command,8,remaining=8,controller_owner=c.fixture.controller)
            c.command.check_edit(c.baseline,1,8)
            current=replace(c.snapshot(extra=((37,'❯ /context'),)),cursorX=10)
            c.command.observe(current,2); c.command.submit_bytes(current,2)
            menu=(8,'❯ /context  Synthetic completion')
            latest=replace(c.snapshot(extra=(menu,(37,'❯ /context'))),cursorX=10)
            self.assertEqual(c.command.observe(latest,3),'SUBMIT_PENDING')
            c.command.submission_written(1)
            waiting=c.snapshot(extra=(menu,))
            self.assertIsNone(c.observe(waiting,4))
            self.assertEqual(c.observe(c.snapshot(commit=20),5),16)


if __name__=='__main__': unittest.main()
