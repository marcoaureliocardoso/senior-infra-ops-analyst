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
