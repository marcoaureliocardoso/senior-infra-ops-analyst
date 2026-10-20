"""Frozen structural rejection facts; no Claude/provider or acceptance authority."""
from dataclasses import replace
import json
import unittest
from unittest import mock

from context_display_fixtures import DisplayCase
import terminal_context_echo as echo
import terminal_context_diagnostics as diagnostic
from terminal_input_challenge import InputProofError
from terminal_structural_diagnostics import TerminalDiagnostics


DETAIL={'rowShape':'CONTEXT_COMPLETION','preEnterMenuCell':True,'historyCell':'NONE',
    'samplePresent':True,'newHistoryCount':0,'displayPhase':'AWAIT_DISPLAY'}
FAILURE={'phase':'CONTEXT_PENDING','check':'HISTORY_ELIGIBILITY',
    'commandBytesWritten':8,'enterBytesWritten':1}
FIELDS={'contextCommandFailure':FAILURE,'inputEligibility':'UNSUPPORTED_ROW',
    'inputRowRelation':'OTHER_CAPTURED_ROW','inputRowCause':'UNRECOGNIZED_SHAPE'}


class HistoryRejectionTests(unittest.TestCase):
    def failure(self,c,current,frame=3):
        with self.assertRaises(InputProofError) as caught: c.observe(current,frame)
        error=caught.exception
        self.assertEqual(error.reason,'INPUT_PROBE_INELIGIBLE')
        self.assertEqual(c.journal.project(error,**c.bindings),FAILURE)
        self.assertEqual(c.command.phase,'REVOKED')
        return error,c.journal.project_fields(error,**c.bindings)

    def test_known_menu_is_geometry_not_input_authority(self):
        with DisplayCase() as c:
            menu=((8,'❯ /context  Synthetic completion'),)
            c.submit(extra=menu)
            error,fields=self.failure(c,c.snapshot(extra=menu))
            self.assertEqual(fields['history_rejection'],DETAIL)
            with self.assertRaises(RuntimeError): c.observe(c.snapshot(commit=20),4)
            self.assertEqual(c.journal.project_fields(error,**c.bindings)['history_rejection'],DETAIL)

    def test_same_shape_elsewhere_is_not_the_preenter_menu_cell(self):
        with DisplayCase() as c:
            c.submit(extra=((8,'❯ /context  Synthetic completion'),))
            _,fields=self.failure(c,c.snapshot(extra=((9,'❯ /context  Synthetic completion'),)))
            self.assertEqual(fields['history_rejection'],{**DETAIL,'preEnterMenuCell':False})

    def test_retired_sdk_position_is_not_claimed_as_partial_text_identity(self):
        with DisplayCase() as c:
            c.submit()
            _,fields=self.failure(c,c.snapshot(extra=((5,'❯ P0-04B synthetic text'),)))
            self.assertEqual(fields['history_rejection'],{**DETAIL,'rowShape':'OTHER',
                'preEnterMenuCell':False,'historyCell':'RETIRED_SDK_TEXT'})

    def test_unknown_row_with_and_without_sample_or_commit(self):
        for numeric,commit in ((False,None),(True,None),(True,20)):
            with self.subTest(numeric=numeric,commit=commit),DisplayCase() as c:
                c.submit()
                _,fields=self.failure(c,c.snapshot(numeric=numeric,commit=commit,extra=((8,'❯ Synthetic unknown'),)))
                self.assertEqual(fields['history_rejection'],{**DETAIL,'rowShape':'OTHER',
                    'preEnterMenuCell':False,'samplePresent':numeric,'newHistoryCount':int(commit is not None)})

    def test_post_candidate_rejection_freezes_candidate_phase(self):
        with DisplayCase() as c:
            c.submit(); self.assertEqual(c.observe(c.snapshot(commit=20),3),16)
            _,fields=self.failure(c,c.snapshot(commit=20,extra=((39,'❯ unknown'),)),4)
            self.assertEqual(fields['history_rejection'],{**DETAIL,'rowShape':'OTHER',
                'preEnterMenuCell':False,'newHistoryCount':1,'displayPhase':'CANDIDATE'})

    def test_retired_command_positions_are_not_excluded_by_the_observer(self):
        for index,token,kind in ((10,'/context','CONTEXT'),(12,'/exit','EXIT')):
            with self.subTest(kind=kind),DisplayCase(history_rows=((index,'❯ '+token),)) as c:
                c.submit()
                _,fields=self.failure(c,c.snapshot(extra=((index,'❯ unknown'),)))
                self.assertEqual(fields['history_rejection'],{**DETAIL,'rowShape':'OTHER',
                    'preEnterMenuCell':False,'historyCell':'RETIRED_'+kind})

    def test_actual_cursor_rejection_is_classified_without_raw_cells(self):
        with DisplayCase() as c:
            c.submit()
            frame=replace(c.snapshot(extra=((37,'❯ /context'),)),cursorX=10)
            error,fields=self.failure(c,frame)
            self.assertEqual(error.input_row_relation,'CURSOR_ROW')
            self.assertEqual(fields['history_rejection'],{**DETAIL,'rowShape':'CONTEXT_COMMAND','preEnterMenuCell':False})
            self.assertNotIn('/context',json.dumps(fields))

    def test_projection_rejects_foreign_bindings_copied_error_and_finished_journal(self):
        with DisplayCase() as c:
            c.submit(); error,fields=self.failure(c,c.snapshot(extra=((8,'❯ unknown'),)))
            fields['history_rejection']['rowShape']='private-content'
            self.assertEqual(c.journal.project_fields(error,**c.bindings)['history_rejection']['rowShape'],'OTHER')
            copied=InputProofError(error.reason,error.input_eligibility,
                input_row_relation=error.input_row_relation,input_row_cause=error.input_row_cause)
            copied.__dict__.update(error.__dict__)
            self.assertIsNone(c.journal.project_fields(copied,**c.bindings))
            for key in c.bindings:
                with self.subTest(key=key):
                    self.assertIsNone(c.journal.project_fields(error,**{**c.bindings,key:object()}))
            c.journal.finish()
            self.assertIsNone(c.journal.project_fields(error,**c.bindings))

    def test_optional_freeze_failure_preserves_original_rejection(self):
        with DisplayCase() as c:
            c.submit()
            with mock.patch.object(echo,'_freeze_history_rejection',side_effect=ValueError):
                _,fields=self.failure(c,c.snapshot(extra=((8,'❯ unknown'),)))
            self.assertEqual(fields,{'context_command_failure':FAILURE})

    def test_optional_menu_note_failure_never_changes_submission_or_acceptance(self):
        with DisplayCase() as c:
            with mock.patch.object(echo,'_note_diagnostic_menu',side_effect=ValueError): c.submit()
            self.assertEqual(c.observe(c.snapshot(commit=20),3),16)
            self.assertIsNotNone(c.command.bind_history(c.snapshot(commit=20),4))

    def test_observer_validation_loss_keeps_original_journal_and_record(self):
        with DisplayCase() as c:
            c.submit()
            with mock.patch.object(diagnostic,'valid_history_rejection',side_effect=ValueError):
                _,fields=self.failure(c,c.snapshot(extra=((8,'❯ unknown'),)))
            self.assertEqual(fields,{'context_command_failure':FAILURE})
        collector=TerminalDiagnostics(); baseline=TerminalDiagnostics()
        with mock.patch('terminal_structural_diagnostics.valid_history_rejection',side_effect=ValueError):
            collector.add('failure','INPUT_PROBE_INELIGIBLE',**FIELDS,historyRejection=DETAIL)
        baseline.add('failure','INPUT_PROBE_INELIGIBLE',**FIELDS)
        self.assertEqual(collector.report(),baseline.report())

    def test_optional_projection_loss_keeps_original_failure(self):
        with DisplayCase() as c:
            c.submit()
            with mock.patch.object(echo,'_history_rejection_detail',side_effect=ValueError):
                _,fields=self.failure(c,c.snapshot(extra=((8,'❯ unknown'),)))
            self.assertEqual(fields,{'context_command_failure':FAILURE})

    def test_closed_schema_omits_invalid_optional_metadata_only(self):
        valid_history_rejection=getattr(diagnostic,'valid_history_rejection',None)
        self.assertTrue(callable(valid_history_rejection),'closed history-rejection schema is absent')
        invalid=[{},None,{**DETAIL,'raw':'private-content'},{**DETAIL,'samplePresent':1},
            {**DETAIL,'newHistoryCount':True},{**DETAIL,'newHistoryCount':2},
            {**DETAIL,'rowShape':'private-content'},{**DETAIL,'historyCell':'SDK_TEXT'},
            {**DETAIL,'displayPhase':'CONSUMED'}]
        self.assertTrue(valid_history_rejection(DETAIL))
        for value in invalid:
            with self.subTest(value=value):
                self.assertFalse(valid_history_rejection(value))
                collector=TerminalDiagnostics(); collector.add('failure','INPUT_PROBE_INELIGIBLE',
                    **FIELDS,historyRejection=value)
                baseline=TerminalDiagnostics(); baseline.add('failure','INPUT_PROBE_INELIGIBLE',**FIELDS)
                self.assertEqual(collector.report(),baseline.report())

    def test_export_requires_exact_failure_and_is_detached(self):
        collector=TerminalDiagnostics(); collector.add('failure','INPUT_PROBE_INELIGIBLE',**FIELDS,historyRejection=DETAIL)
        report=collector.report(); self.assertEqual(report['records'][0]['historyRejection'],DETAIL)
        report['records'][0]['historyRejection']['rowShape']='private-content'
        self.assertEqual(collector.report()['records'][0]['historyRejection']['rowShape'],'CONTEXT_COMPLETION')
        for point,reason,fields in (('prompt_ready','CHECKPOINT',{}),
                ('failure','INPUT_PROBE_INELIGIBLE',{**FIELDS,'contextCommandFailure':{**FAILURE,'check':'BASELINE_ELIGIBILITY'}})):
            candidate=TerminalDiagnostics(); baseline=TerminalDiagnostics()
            candidate.add(point,reason,**fields,historyRejection=DETAIL); baseline.add(point,reason,**fields)
            self.assertEqual(candidate.report(),baseline.report())

    def test_optional_annotations_never_displace_base_failure_or_cleanup(self):
        annotated=TerminalDiagnostics(); baseline=TerminalDiagnostics()
        for i in range(7):
            annotated.add('failure','INPUT_PROBE_INELIGIBLE',**FIELDS,historyRejection=DETAIL)
            baseline.add('failure','INPUT_PROBE_INELIGIBLE',**FIELDS)
        for point in ('native_cleanup','helper_cleanup'):
            annotated.add(point,'CLEANUP_COMPLETED',leaderReaped=True)
            baseline.add(point,'CLEANUP_COMPLETED',leaderReaped=True)
        report=annotated.report(); plain=baseline.report()
        self.assertEqual(plain['records'][-1]['point'],'helper_cleanup')
        self.assertLessEqual(len(json.dumps(report,sort_keys=True).encode()),3072)
        self.assertEqual(len(report['records']),len(plain['records']))
        for row in report['records']: row.pop('historyRejection',None)
        self.assertEqual(report,plain)
        self.assertEqual(annotated.report(),annotated.report())


if __name__=='__main__': unittest.main()
