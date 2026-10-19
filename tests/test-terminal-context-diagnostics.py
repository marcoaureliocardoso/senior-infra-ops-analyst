"""Pure content-free command accounting; no native runtime or provider."""
import importlib
import json
from pathlib import Path
import time
import unittest
from unittest import mock

from terminal_input_challenge import InputProofError


class ContextDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(Path(__file__).with_name('terminal_context_diagnostics.py').is_file(),
            'private command diagnostic component missing')
        self.m=importlib.import_module('terminal_context_diagnostics')

    def journal(self):
        bindings={name:object() for name in ('controller_owner','scope','state','transition_owner')}
        journal=self.m._create_context_journal(**bindings)
        self.addCleanup(journal.finish)
        return journal,bindings

    def freeze(self,journal,check='PREFIX_CELLS'):
        error=InputProofError('INPUT_PROBE_REVOKED')
        journal.freeze(error,check)
        return error

    def test_enter_ack_survives_freeze_and_projection(self):
        journal,bindings=self.journal(); journal.bind_run(object())
        journal.set_phase('EDIT_PENDING')
        self.assertTrue(journal.acknowledge(4,submission=False,remaining=8))
        self.assertTrue(journal.acknowledge(4,submission=False,remaining=4))
        journal.set_phase('SUBMIT_PENDING')
        self.assertTrue(journal.acknowledge(1,submission=True,remaining=1))
        error=self.freeze(journal,'NATIVE_LIFETIME')
        expected={'phase':'SUBMIT_PENDING','check':'NATIVE_LIFETIME',
            'commandBytesWritten':8,'enterBytesWritten':1}
        self.assertEqual(journal.project(error,**bindings),expected)
        journal.set_phase('REVOKED'); journal.freeze(error,'SCOPE_BINDING')
        self.assertEqual(journal.project(error,**bindings),expected)
        journal.freeze(InputProofError('INPUT_PROBE_REVOKED'),'PHASE_STATE')
        self.assertEqual(journal.project(error,**bindings),expected)

    def test_fresh_context_closed_labels_survive_serialized_structural_projection(self):
        from terminal_structural_diagnostics import TerminalDiagnostics,MAX_BYTES
        for check in ('FRESH_CONTEXT_FRAME_NOT_ADVANCED','FRESH_CONTEXT_SIGNATURE_UNCHANGED',
                'FRESH_CONTEXT_NUMERIC_UNAVAILABLE','FRESH_CONTEXT','DISPLAY_WITNESS_UNPROVEN',
                'DISPLAY_WITNESS_AMBIGUOUS','CONTEXT_SAMPLE_UNSTABLE'):
            with self.subTest(check=check):
                journal,bindings=self.journal(); journal.bind_run(object())
                journal.set_phase('EDIT_PENDING'); journal.acknowledge(8,submission=False,remaining=8)
                journal.set_phase('SUBMIT_PENDING'); journal.acknowledge(1,submission=True,remaining=1)
                journal.set_phase('CONTEXT_PENDING')
                error=InputProofError('INPUT_PROBE_STATE_REJECTED'); journal.freeze(error,check)
                projected=journal.project_fields(error,**bindings)
                expected={'phase':'CONTEXT_PENDING','check':check,'commandBytesWritten':8,'enterBytesWritten':1}
                self.assertEqual(projected,{'context_command_failure':expected})
                collector=TerminalDiagnostics()
                collector.add('failure',error.reason,contextCommandFailure=projected['context_command_failure'])
                encoded=json.dumps(collector.report(),sort_keys=True).encode()
                self.assertLessEqual(len(encoded),MAX_BYTES)
                self.assertEqual(json.loads(encoded),{'records':[{'point':'failure',
                    'reasonCode':'INPUT_PROBE_STATE_REJECTED','contextCommandFailure':expected}],
                    'truncated':False,'rejected':False})
                for change in ({'check':check+' synthetic-private'},{'signature':'synthetic-private'},
                        {'commandBytesWritten':True},{'enterBytesWritten':2}):
                    rejected=TerminalDiagnostics()
                    rejected.add('failure',error.reason,contextCommandFailure={**expected,**change})
                    self.assertEqual(rejected.report(),{'records':[],'truncated':False,'rejected':True})

    def test_invalid_ack_suppresses_projection(self):
        for count in (True,0,-1,9,1.0,None):
            with self.subTest(count=count):
                journal,bindings=self.journal(); journal.set_phase('EDIT_PENDING')
                self.assertFalse(journal.acknowledge(count,submission=False,remaining=8))
                self.assertFalse(journal.acknowledge(1,submission=False,remaining=8))
                self.assertIsNone(journal.project(self.freeze(journal),**bindings))
        for submission,remaining in ((1,8),(False,True),(False,7),(True,2)):
            journal,bindings=self.journal(); journal.set_phase('EDIT_PENDING')
            self.assertFalse(journal.acknowledge(1,submission=submission,remaining=remaining))
            self.assertIsNone(journal.project(self.freeze(journal),**bindings))

    def test_acknowledgements_cannot_exceed_each_fixed_write(self):
        journal,bindings=self.journal(); journal.set_phase('EDIT_PENDING')
        self.assertTrue(journal.acknowledge(8,submission=False,remaining=8))
        self.assertFalse(journal.acknowledge(1,submission=False,remaining=0))
        self.assertIsNone(journal.project(self.freeze(journal),**bindings))
        journal,bindings=self.journal(); journal.set_phase('SUBMIT_PENDING')
        self.assertTrue(journal.acknowledge(1,submission=True,remaining=1))
        self.assertFalse(journal.acknowledge(1,submission=True,remaining=0))
        self.assertIsNone(journal.project(self.freeze(journal),**bindings))

    def test_forged_foreign_closed_or_replaced_attachment_omitted(self):
        with self.assertRaises(TypeError): self.m.ContextFailureJournal()
        journal,bindings=self.journal(); error=self.freeze(journal,'BASELINE_ELIGIBILITY')
        self.assertIsNotNone(journal.project(error,**bindings))
        for key in bindings:
            self.assertIsNone(journal.project(error,**{**bindings,key:object()}))
        other=InputProofError('INPUT_PROBE_REVOKED')
        other._context_command_failure=error._context_command_failure
        self.assertIsNone(journal.project(other,**bindings))
        foreign,foreign_bindings=self.journal()
        self.assertIsNone(foreign.project(error,**foreign_bindings))
        original=error._context_command_failure
        error._context_command_failure={}
        self.assertIsNone(journal.project(error,**bindings))
        error._context_command_failure=original
        projected=journal.project(error,**bindings); projected['check']='synthetic-private-text'
        self.assertEqual(journal.project(error,**bindings)['check'],'BASELINE_ELIGIBILITY')
        journal.finish()
        self.assertIsNone(journal.project(error,**bindings))

    def test_invalid_phase_check_and_changed_run_disable_new_observation(self):
        for phase,check in (('unknown','PREFIX_CELLS'),('BASELINE','unknown'),(1,'PREFIX_CELLS')):
            journal,bindings=self.journal(); journal.set_phase(phase)
            self.assertIsNone(journal.project(self.freeze(journal,check),**bindings))
        journal,bindings=self.journal(); run=object(); journal.bind_run(run); journal.bind_run(run)
        journal.bind_run(object())
        self.assertIsNone(journal.project(self.freeze(journal),**bindings))

    def test_projection_has_no_live_effects(self):
        class State:
            def check_cancelled(self): raise AssertionError('unexpected live validation')
            def poll(self): raise AssertionError('unexpected poll')
            def snapshot(self): raise AssertionError('unexpected IPC')
        bindings={name:object() for name in ('controller_owner','scope','transition_owner')}
        bindings['state']=State()
        journal=self.m._create_context_journal(**bindings); self.addCleanup(journal.finish)
        error=self.freeze(journal,'SCOPE_BINDING')
        with mock.patch.object(time,'monotonic',side_effect=AssertionError('unexpected clock')):
            self.assertEqual(journal.project(error,**bindings),{
                'phase':'BASELINE','check':'SCOPE_BINDING','commandBytesWritten':0,'enterBytesWritten':0})
        self.assertEqual(str(error),'INPUT_PROBE_REVOKED')
        self.assertNotIn('SCOPE_BINDING',repr(journal))
        self.assertNotIn('BASELINE',repr(error._context_command_failure))

    def test_failure_observation_cannot_cross_dialogues(self):
        first,first_bindings=self.journal(); first.set_phase('EDIT_PENDING')
        first.acknowledge(8,submission=False,remaining=8); error=self.freeze(first)
        second,second_bindings=self.journal()
        self.assertIsNone(second.project(error,**second_bindings))
        second_error=self.freeze(second,'BASELINE_ELIGIBILITY')
        self.assertEqual(second.project(second_error,**second_bindings)['commandBytesWritten'],0)
        self.assertEqual(first.project(error,**first_bindings)['commandBytesWritten'],8)

    def test_normalized_detail_closed_shapes(self):
        self.assertTrue(hasattr(self.m,'valid_normalized_input_failure'),'normalized detail validator missing')
        for reason in ('FORBIDDEN_STATE','NO_MARKER','NONEMPTY_INPUT','MULTIPLE_MARKERS',
                'CURSOR_ROW_MISMATCH','CURSOR_COLUMN_MISMATCH','INSUFFICIENT_SPACE','ANCHOR_CHANGED'):
            self.assertTrue(self.m.valid_normalized_input_failure({'reason':reason}))
        for relation in ('CURSOR_ROW','OTHER_CAPTURED_ROW','CURSOR_OUTSIDE_CAPTURE'):
            for cause in ('INVISIBLE_FORMAT_CHAR','UNSUPPORTED_WHITESPACE','MARKER_WIDTH',
                    'CONTROL_COMMAND_SHAPE','UNRECOGNIZED_SHAPE'):
                self.assertTrue(self.m.valid_normalized_input_failure({
                    'reason':'UNSUPPORTED_ROW','rowRelation':relation,'rowCause':cause}))
        valid={'reason':'UNSUPPORTED_ROW','rowRelation':'OTHER_CAPTURED_ROW','rowCause':'UNRECOGNIZED_SHAPE'}
        variants=[None,True,[],json.dumps(valid),{}, {'reason':'ELIGIBLE'}, {'reason':None},
            {'reason':'NO_MARKER','rowCause':'MARKER_WIDTH'}, {'reason':'NO_MARKER','text':'synthetic-content'}]
        variants.extend({**valid,**change} for change in (
            {'reason':'unknown'},{'rowRelation':True},{'rowCause':1},{'rowCause':'unknown'},{'text':'synthetic-content'}))
        variants.extend({key:value for key,value in valid.items() if key!=missing} for missing in valid)
        for value in variants: self.assertFalse(self.m.valid_normalized_input_failure(value))

    def test_paired_projection_is_frozen_and_base_contract_unchanged(self):
        journal,bindings=self.journal(); journal.set_phase('EDIT_PENDING')
        journal.acknowledge(8,submission=False,remaining=8)
        detail={'reason':'UNSUPPORTED_ROW','rowRelation':'OTHER_CAPTURED_ROW','rowCause':'UNRECOGNIZED_SHAPE'}
        error=InputProofError('INPUT_PROBE_REVOKED')
        journal.freeze(error,'NORMALIZED_ELIGIBILITY',normalized_input_failure=detail)
        expected={'context_command_failure':{'phase':'EDIT_PENDING','check':'NORMALIZED_ELIGIBILITY',
            'commandBytesWritten':8,'enterBytesWritten':0},'normalized_input_failure':dict(detail)}
        self.assertEqual(journal.project_fields(error,**bindings),expected)
        self.assertEqual(journal.project(error,**bindings),expected['context_command_failure'])
        detail['reason']='NO_MARKER'
        projected=journal.project_fields(error,**bindings); projected['normalized_input_failure']['rowCause']='unknown'
        projected['context_command_failure']['commandBytesWritten']=0
        journal.set_phase('SUBMIT_PENDING')
        journal.freeze(error,'NORMALIZED_ELIGIBILITY',normalized_input_failure={'reason':'ANCHOR_CHANGED'})
        self.assertEqual(journal.project_fields(error,**bindings),expected)

    def test_detail_loss_does_not_destroy_valid_base_or_enrich_later(self):
        for detail,check,error in (({},'NORMALIZED_ELIGIBILITY',InputProofError('INPUT_PROBE_REVOKED')),
                ({'reason':'ELIGIBLE'},'NORMALIZED_ELIGIBILITY',InputProofError('INPUT_PROBE_REVOKED')),
                ({'reason':'NO_MARKER'},'PREFIX_CELLS',InputProofError('INPUT_PROBE_REVOKED')),
                ({'reason':'NO_MARKER'},'NORMALIZED_ELIGIBILITY',RuntimeError()),
                ({'reason':'NO_MARKER'},'NORMALIZED_ELIGIBILITY',InputProofError('INPUT_PROBE_INELIGIBLE'))):
            journal,bindings=self.journal()
            journal.freeze(error,check,normalized_input_failure=detail)
            fields=journal.project_fields(error,**bindings)
            self.assertEqual(set(fields),{'context_command_failure'})
            self.assertEqual(fields['context_command_failure']['check'],check)
            journal.freeze(error,'NORMALIZED_ELIGIBILITY',normalized_input_failure={'reason':'NO_MARKER'})
            self.assertEqual(journal.project_fields(error,**bindings),fields)

    def test_paired_projection_rejects_foreign_closed_and_replaced_bindings(self):
        journal,bindings=self.journal(); journal.bind_run(object())
        error=InputProofError('INPUT_PROBE_REVOKED')
        journal.freeze(error,'NORMALIZED_ELIGIBILITY',normalized_input_failure={'reason':'ANCHOR_CHANGED'})
        for key in bindings:
            self.assertIsNone(journal.project_fields(error,**{**bindings,key:object()}))
        other=InputProofError('INPUT_PROBE_REVOKED'); other._context_command_failure=error._context_command_failure
        self.assertIsNone(journal.project_fields(other,**bindings))
        foreign,foreign_bindings=self.journal()
        self.assertIsNone(foreign.project_fields(error,**foreign_bindings))
        original=error._context_command_failure; error._context_command_failure={}
        self.assertIsNone(journal.project_fields(error,**bindings))
        error._context_command_failure=original
        journal.bind_run(object())
        self.assertIsNone(journal.project_fields(error,**bindings))
        journal.finish(); self.assertIsNone(journal.project_fields(error,**bindings))

    def test_paired_projection_has_no_live_effects(self):
        class State:
            def check_cancelled(self): raise AssertionError('live validation')
            def poll(self): raise AssertionError('native poll')
            def snapshot(self): raise AssertionError('helper IPC')
        bindings={name:object() for name in ('controller_owner','scope','transition_owner')}; bindings['state']=State()
        journal=self.m._create_context_journal(**bindings); self.addCleanup(journal.finish)
        error=InputProofError('INPUT_PROBE_REVOKED')
        journal.freeze(error,'NORMALIZED_ELIGIBILITY',normalized_input_failure={'reason':'NO_MARKER'})
        with mock.patch.object(time,'monotonic',side_effect=AssertionError('clock')):
            fields=journal.project_fields(error,**bindings)
        self.assertEqual(fields['normalized_input_failure'],{'reason':'NO_MARKER'})
        self.assertEqual(str(error),'INPUT_PROBE_REVOKED')

    def test_serialized_shape_validation_never_accepts_extra_content(self):
        valid={'phase':'EDIT_PENDING','check':'PREFIX_CELLS','commandBytesWritten':8,'enterBytesWritten':0}
        self.assertTrue(self.m.valid_context_failure(valid))
        variants=({'text':'synthetic-private-text'},{'phase':'REVOKED'},{'check':'unknown'},
            {'commandBytesWritten':True},{'enterBytesWritten':True},{'commandBytesWritten':9},
            {'enterBytesWritten':2},{'commandBytesWritten':-1},{'check':None})
        for changes in variants:
            self.assertFalse(self.m.valid_context_failure({**valid,**changes}))
        self.assertFalse(self.m.valid_context_failure({key:value for key,value in valid.items() if key!='phase'}))
        self.assertFalse(self.m.valid_context_failure(json.dumps(valid)))


if __name__=='__main__': unittest.main()
