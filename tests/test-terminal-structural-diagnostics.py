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


if __name__=='__main__': unittest.main()
