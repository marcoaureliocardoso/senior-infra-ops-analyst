"""Content-free diagnostic retention, never operational proof."""
import importlib.util
import json
from pathlib import Path
import unittest


class TerminalStructuralDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        path=Path(__file__).with_name('terminal_structural_diagnostics.py')
        self.assertTrue(path.is_file(),'bounded diagnostic collector missing')
        spec=importlib.util.spec_from_file_location('terminal_structural_diagnostics',path)
        self.module=importlib.util.module_from_spec(spec); spec.loader.exec_module(self.module)
        self.collector=self.module.TerminalDiagnostics()

    def test_readiness_rejection_is_retained_as_closed_atomic_structure(self):
        structure={'buffer':'alternate','cursorX':2,'cursorY':37,'baseY':0,'viewportY':0,
            'candidateCount':1,'inputFresh':True,'contextFresh':True,'locationFresh':True,
            'authentication':'NONE','readiness':'UNSUPPORTED_MARKER',
            'readinessRejection':{'rowRelation':'OTHER_CAPTURED_ROW','rowCause':'UNRECOGNIZED_SHAPE',
                'rowShape':'SDK_TEXT_PROMPT_SHAPE'}}
        self.collector.add('failure','WAIT_DEADLINE',structure=structure)
        report=self.collector.report()
        self.assertEqual(report,{'records':[{'point':'failure','reasonCode':'WAIT_DEADLINE',
            'structure':structure}],'truncated':False,'rejected':False})
        structure['readinessRejection']['rowShape']='OTHER'
        self.assertEqual(self.collector.report()['records'][0]['structure']['readinessRejection']['rowShape'],
            'SDK_TEXT_PROMPT_SHAPE')

    def test_readiness_rejection_rejects_content_partial_detail_and_wrong_decision(self):
        base={'buffer':'normal','cursorX':2,'cursorY':1,'baseY':0,'viewportY':0,
            'candidateCount':1,'inputFresh':True,'contextFresh':False,'locationFresh':False,
            'authentication':'NONE','readiness':'UNSUPPORTED_MARKER'}
        detail={'rowRelation':'OTHER_CAPTURED_ROW','rowCause':'UNRECOGNIZED_SHAPE','rowShape':'OTHER'}
        changes=[{'rowShape':'private-draft'},{'rowCause':True},{'rowRelation':1},
            {'text':'private-draft'},{'hash':'ab'*32},{'rowShape':{}},
            {'rowCause':'CONTROL_COMMAND_SHAPE','rowShape':'SDK_TEXT_PROMPT_SHAPE'}]
        invalid=[{**detail,**change} for change in changes]
        invalid += [{key:value for key,value in detail.items() if key!=missing} for missing in detail]
        invalid += [None,True,[]]
        for value in invalid:
            self.collector.add('failure','WAIT_DEADLINE',structure={**base,'readinessRejection':value})
        self.collector.add('failure','WAIT_DEADLINE',structure={**base,'readiness':'READY',
            'readinessRejection':detail})
        self.assertEqual(self.collector.report(),{'records':[],'truncated':False,'rejected':True})
        self.assertNotIn('private-draft',json.dumps(self.collector.report()))

    def test_readiness_rejection_obeys_unchanged_budget(self):
        structure={'buffer':'alternate','cursorX':2,'cursorY':37,'baseY':0,'viewportY':0,
            'candidateCount':1,'inputFresh':True,'contextFresh':True,'locationFresh':True,
            'authentication':'NONE','readiness':'UNSUPPORTED_MARKER',
            'readinessRejection':{'rowRelation':'OTHER_CAPTURED_ROW','rowCause':'UNRECOGNIZED_SHAPE',
                'rowShape':'SDK_TEXT_PROMPT_SHAPE'}}
        for _ in range(100): self.collector.add('failure','WAIT_DEADLINE',structure=structure)
        report=self.collector.report()
        self.assertGreater(len(report['records']),0)
        self.assertTrue(report['truncated']); self.assertFalse(report['rejected'])
        self.assertLessEqual(len(json.dumps(report,sort_keys=True).encode()),3072)

    def test_closed_fields_reject_content_and_hashes_without_forwarding(self):
        for fields in ({'text':'synthetic-secret'},{'hash':'ab'*32},
                       {'leaderReaped':'synthetic-secret'},{'leaderReaped':1}):
            self.collector.add('failure','WAIT_DEADLINE',**fields)
        self.assertEqual(self.collector.report(),{'records':[],'truncated':False,'rejected':True})
        self.assertNotIn('synthetic-secret',json.dumps(self.collector.report()))

    def test_closed_reason_and_checkpoint_reject_arbitrary_exception_content(self):
        self.collector.add('failure','synthetic-secret')
        self.collector.add('synthetic-secret','WAIT_DEADLINE')
        self.assertEqual(self.collector.report(),{'records':[],'truncated':False,'rejected':True})

    def test_eligibility_subcodes_are_retained_only_as_closed_failure_metadata(self):
        codes=('FORBIDDEN_STATE','NO_MARKER','UNSUPPORTED_ROW','NONEMPTY_INPUT',
            'MULTIPLE_MARKERS','CURSOR_ROW_MISMATCH','CURSOR_COLUMN_MISMATCH',
            'INSUFFICIENT_SPACE','ANCHOR_CHANGED')
        for code in codes:
            self.collector.add('failure','INPUT_PROBE_INELIGIBLE',inputEligibility=code)
        self.assertEqual(self.collector.report(),{'records':[
            {'point':'failure','reasonCode':'INPUT_PROBE_INELIGIBLE','inputEligibility':code}
            for code in codes],'truncated':False,'rejected':False})

    def test_eligibility_metadata_rejects_content_types_and_wrong_event_binding(self):
        for value in ('synthetic-private-text','ELIGIBLE',{'reason':'NONEMPTY_INPUT'},True,1,None):
            self.collector.add('failure','INPUT_PROBE_INELIGIBLE',inputEligibility=value)
        self.collector.add('context_numeric','CHECKPOINT',inputEligibility='NO_MARKER')
        self.collector.add('failure','WAIT_DEADLINE',inputEligibility='NO_MARKER')
        self.assertEqual(self.collector.report(),{'records':[],'truncated':False,'rejected':True})
        self.assertNotIn('synthetic-private-text',json.dumps(self.collector.report()))

    def test_eligibility_metadata_counts_against_unchanged_byte_and_record_limits(self):
        structure={'buffer':'normal','cursorX':120,'cursorY':39,'baseY':1000,'viewportY':1000,
            'candidateCount':40,'inputFresh':True,'contextFresh':True,'locationFresh':True,
            'authentication':'API_KEY_APPROVAL_REQUIRED','readiness':'AUTHENTICATION_REQUIRED'}
        for _ in range(100):
            self.collector.add('failure','INPUT_PROBE_INELIGIBLE',structure=structure,
                inputEligibility='CURSOR_COLUMN_MISMATCH')
        report=self.collector.report()
        self.assertGreater(len(report['records']),0)
        self.assertLess(len(report['records']),16)
        self.assertTrue(report['truncated']); self.assertFalse(report['rejected'])
        self.assertLessEqual(len(json.dumps(report,separators=(',',':')).encode()),3072)

    def test_record_limit_is_bounded_and_truncation_is_explicit(self):
        for _ in range(100): self.collector.add('failure','WAIT_DEADLINE')
        report=self.collector.report()
        self.assertEqual(len(report['records']),16)
        self.assertTrue(report['truncated']); self.assertFalse(report['rejected'])
        self.assertLessEqual(len(json.dumps(report,separators=(',',':')).encode()),3072)

    def test_rejected_row_metadata_is_an_atomic_closed_pair_on_unsupported_failure(self):
        pairs=[('CURSOR_ROW',cause) for cause in ('INVISIBLE_FORMAT_CHAR','UNSUPPORTED_WHITESPACE',
            'MARKER_WIDTH','CONTROL_COMMAND_SHAPE','UNRECOGNIZED_SHAPE')]
        pairs.extend((relation,'CONTROL_COMMAND_SHAPE') for relation in ('OTHER_CAPTURED_ROW','CURSOR_OUTSIDE_CAPTURE'))
        for relation,cause in pairs:
            self.collector.add('failure','INPUT_PROBE_INELIGIBLE',inputEligibility='UNSUPPORTED_ROW',
                inputRowRelation=relation,inputRowCause=cause)
        self.assertEqual(self.collector.report(),{'records':[
            {'point':'failure','reasonCode':'INPUT_PROBE_INELIGIBLE','inputEligibility':'UNSUPPORTED_ROW',
                'inputRowRelation':relation,'inputRowCause':cause} for relation,cause in pairs],
            'truncated':False,'rejected':False})

    def test_row_metadata_rejects_partial_pairs_wrong_binding_and_content(self):
        valid={'inputEligibility':'UNSUPPORTED_ROW','inputRowRelation':'CURSOR_ROW','inputRowCause':'MARKER_WIDTH'}
        for change in ({'inputRowCause':'synthetic-private-text'},{'inputRowCause':{}},
                {'inputRowRelation':True},{'inputRowRelation':1},{'inputRowRelation':'row 37'},
                {'inputEligibility':'NO_MARKER'},{'text':'synthetic-private-text'}):
            self.collector.add('failure','INPUT_PROBE_INELIGIBLE',**{**valid,**change})
        for missing in ('inputRowRelation','inputRowCause','inputEligibility'):
            self.collector.add('failure','INPUT_PROBE_INELIGIBLE',**{key:value for key,value in valid.items() if key!=missing})
        self.collector.add('failure','WAIT_DEADLINE',**valid)
        self.collector.add('context_numeric','CHECKPOINT',**valid)
        self.assertEqual(self.collector.report(),{'records':[],'truncated':False,'rejected':True})
        self.assertNotIn('synthetic-private-text',json.dumps(self.collector.report()))

    def test_row_metadata_uses_existing_byte_budget_and_detached_reports(self):
        structure={'buffer':'normal','cursorX':120,'cursorY':39,'baseY':1000,'viewportY':1000,
            'candidateCount':40,'inputFresh':True,'contextFresh':True,'locationFresh':True,
            'authentication':'NONE','readiness':'FRESHNESS_UNPROVEN'}
        for _ in range(100):
            self.collector.add('failure','INPUT_PROBE_INELIGIBLE',inputEligibility='UNSUPPORTED_ROW',
                inputRowRelation='CURSOR_OUTSIDE_CAPTURE',inputRowCause='UNSUPPORTED_WHITESPACE',structure=structure)
        report=self.collector.report()
        self.assertGreater(len(report['records']),0); self.assertLess(len(report['records']),16)
        self.assertTrue(report['truncated']); self.assertFalse(report['rejected'])
        self.assertLessEqual(len(json.dumps(report,separators=(',',':')).encode()),3072)
        report['records'][0]['inputRowCause']='synthetic-private-text'
        self.assertEqual(self.collector.report()['records'][0]['inputRowCause'],'UNSUPPORTED_WHITESPACE')

    def test_probe_codes_are_structural_and_never_payload_fields(self):
        for point in ('input_probe_started','input_probe_echo','input_probe_cleared'):
            self.collector.add(point,'CHECKPOINT')
        self.collector.add('failure','INPUT_PROBE_ECHO_REJECTED')
        self.collector.add('input_probe_echo','CHECKPOINT',marker='synthetic marker')
        report=self.collector.report()
        self.assertEqual(len(report['records']),4)
        self.assertTrue(report['rejected'])
        self.assertNotIn('synthetic marker',json.dumps(report))

    def test_structure_is_whitelisted_and_numeric_coordinates_are_bounded(self):
        structure={'buffer':'alternate','cursorX':2,'cursorY':37,'baseY':0,'viewportY':0,
            'candidateCount':1,'inputFresh':False,'contextFresh':True,'locationFresh':False,
            'authentication':'NONE','readiness':'FRESHNESS_UNPROVEN'}
        self.collector.add('panel_close_sent','CHECKPOINT',structure=structure)
        for fields in ({**structure,'cursorX':121},{**structure,'buffer':'secret'},
                       {**structure,'cellText':'secret'},{**structure,'contextFresh':1},
                       {**structure,'baseY':1}):
            self.collector.add('failure','WAIT_DEADLINE',structure=fields)
        report=self.collector.report()
        self.assertEqual(report['records'],[{'point':'panel_close_sent','reasonCode':'CHECKPOINT','structure':structure}])
        self.assertTrue(report['rejected'])

    def test_byte_limit_and_detached_report_prevent_unbounded_or_mutable_retention(self):
        structure={'buffer':'normal','cursorX':120,'cursorY':39,'baseY':1000,'viewportY':1000,
            'candidateCount':40,'inputFresh':True,'contextFresh':True,'locationFresh':True,
            'authentication':'API_KEY_APPROVAL_REQUIRED','readiness':'AUTHENTICATION_REQUIRED'}
        for _ in range(100): self.collector.add('failure','WAIT_DEADLINE',structure=structure)
        report=self.collector.report()
        self.assertLess(len(report['records']),16)
        self.assertTrue(report['truncated'])
        self.assertLessEqual(len(json.dumps(report,separators=(',',':')).encode()),3072)
        report['records'][0]['structure']['cursorX']=99999
        self.assertEqual(self.collector.report()['records'][0]['structure']['cursorX'],120)

    def test_context_failure_atomic_closed_shape(self):
        valid={'phase':'EDIT_PENDING','check':'PREFIX_CELLS','commandBytesWritten':8,'enterBytesWritten':0}
        self.collector.add('failure','INPUT_PROBE_REVOKED',contextCommandFailure=valid)
        self.assertEqual(self.collector.report()['records'],[
            {'point':'failure','reasonCode':'INPUT_PROBE_REVOKED','contextCommandFailure':valid}])
        for change in ({'text':'synthetic-private-text'},{'phase':'REVOKED'},{'check':'unknown'},
                {'commandBytesWritten':True},{'commandBytesWritten':9},{'enterBytesWritten':-1},
                {'enterBytesWritten':2},{'enterBytesWritten':1.0}):
            self.collector.add('failure','INPUT_PROBE_REVOKED',contextCommandFailure={**valid,**change})
        self.collector.add('failure','INPUT_PROBE_REVOKED',contextCommandFailure={'phase':'BASELINE'})
        report=self.collector.report()
        self.assertEqual(len(report['records']),1); self.assertTrue(report['rejected'])
        self.assertNotIn('synthetic-private-text',json.dumps(report))

    def test_context_failure_event_binding(self):
        valid={'phase':'SUBMIT_PENDING','check':'CANCELLATION','commandBytesWritten':8,'enterBytesWritten':1}
        for reason in ('INPUT_PROBE_REVOKED','RUNTIME_REJECTED','TERMINAL_DEADLINE_EXCEEDED'):
            self.collector.add('failure',reason,contextCommandFailure=valid)
        self.assertEqual(len(self.collector.report()['records']),3)
        for point,reason in (('context_sent','CHECKPOINT'),('native_cleanup','CLEANUP_COMPLETED'),
                ('failure','WAIT_DEADLINE'),('failure','IO_FAILED')):
            self.collector.add(point,reason,contextCommandFailure=valid)
        self.assertEqual(len(self.collector.report()['records']),3)
        self.assertTrue(self.collector.report()['rejected'])

    def test_normalized_sibling_requires_exact_failure_binding(self):
        base={'phase':'EDIT_PENDING','check':'NORMALIZED_ELIGIBILITY','commandBytesWritten':8,'enterBytesWritten':0}
        detail={'reason':'UNSUPPORTED_ROW','rowRelation':'OTHER_CAPTURED_ROW','rowCause':'UNRECOGNIZED_SHAPE'}
        self.collector.add('failure','INPUT_PROBE_REVOKED',contextCommandFailure=base,normalizedInputFailure=detail)
        self.assertEqual(len(self.collector.report()['records']),1)
        for point,reason,fields in (
                ('failure','INPUT_PROBE_REVOKED',{'normalizedInputFailure':detail}),
                ('failure','RUNTIME_REJECTED',{'contextCommandFailure':base,'normalizedInputFailure':detail}),
                ('context_sent','CHECKPOINT',{'contextCommandFailure':base,'normalizedInputFailure':detail}),
                ('native_cleanup','CLEANUP_COMPLETED',{'contextCommandFailure':base,'normalizedInputFailure':detail}),
                ('failure','INPUT_PROBE_REVOKED',{'contextCommandFailure':{**base,'check':'PREFIX_CELLS'},'normalizedInputFailure':detail})):
            self.collector.add(point,reason,**fields)
        self.assertEqual(len(self.collector.report()['records']),1)
        self.assertTrue(self.collector.report()['rejected'])

    def test_normalized_sibling_is_atomic_and_detached(self):
        base={'phase':'EDIT_PENDING','check':'NORMALIZED_ELIGIBILITY','commandBytesWritten':8,'enterBytesWritten':0}
        detail={'reason':'UNSUPPORTED_ROW','rowRelation':'OTHER_CAPTURED_ROW','rowCause':'UNRECOGNIZED_SHAPE'}
        self.collector.add('failure','INPUT_PROBE_REVOKED',contextCommandFailure=base,normalizedInputFailure=detail)
        self.assertEqual(self.collector.report()['records'][0]['normalizedInputFailure'],detail)
        report=self.collector.report(); report['records'][0]['normalizedInputFailure']['reason']='unknown'
        detail['rowCause']='unknown'
        self.assertEqual(self.collector.report()['records'][0]['normalizedInputFailure']['rowCause'],'UNRECOGNIZED_SHAPE')
        for invalid in (None,{}, {'reason':'ELIGIBLE'}, {'reason':'NO_MARKER','rowCause':'MARKER_WIDTH'},
                {'reason':'UNSUPPORTED_ROW','rowCause':'MARKER_WIDTH'}, {'reason':'NO_MARKER','text':'synthetic-content'}):
            self.collector.add('failure','INPUT_PROBE_REVOKED',contextCommandFailure=base,normalizedInputFailure=invalid)
        self.assertEqual(len(self.collector.report()['records']),1)
        self.assertTrue(self.collector.report()['rejected'])
        self.assertNotIn('synthetic-content',json.dumps(self.collector.report()))

    def test_normalized_sibling_uses_actual_export_budget(self):
        base={'phase':'COMMAND_ECHO_MATCHED','check':'NORMALIZED_ELIGIBILITY','commandBytesWritten':8,'enterBytesWritten':0}
        detail={'reason':'UNSUPPORTED_ROW','rowRelation':'CURSOR_OUTSIDE_CAPTURE','rowCause':'UNSUPPORTED_WHITESPACE'}
        for _ in range(100):
            self.collector.add('failure','INPUT_PROBE_REVOKED',contextCommandFailure=base,normalizedInputFailure=detail)
        report=self.collector.report()
        self.assertGreater(len(report['records']),0); self.assertLessEqual(len(report['records']),16)
        self.assertLessEqual(len(json.dumps(report,sort_keys=True).encode()),3072)
        self.assertTrue(report['truncated']); self.assertFalse(report['rejected'])

    def test_context_failure_budget_and_detached_report(self):
        valid={'phase':'COMMAND_ECHO_MATCHED','check':'NORMALIZED_ELIGIBILITY',
            'commandBytesWritten':8,'enterBytesWritten':0}
        for _ in range(100):
            self.collector.add('failure','INPUT_PROBE_REVOKED',contextCommandFailure=valid)
        report=self.collector.report()
        self.assertLessEqual(len(report['records']),16)
        self.assertLessEqual(len(json.dumps(report,separators=(',',':')).encode()),3072)
        self.assertTrue(report['truncated']); self.assertFalse(report['rejected'])
        valid['check']='synthetic-private-text'; report['records'][0]['contextCommandFailure']['check']='unknown'
        self.assertEqual(self.collector.report()['records'][0]['contextCommandFailure']['check'],'NORMALIZED_ELIGIBILITY')


if __name__=='__main__': unittest.main()
