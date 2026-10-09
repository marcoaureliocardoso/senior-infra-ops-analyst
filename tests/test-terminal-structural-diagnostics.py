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

    def test_record_limit_is_bounded_and_truncation_is_explicit(self):
        for _ in range(100): self.collector.add('failure','WAIT_DEADLINE')
        report=self.collector.report()
        self.assertEqual(len(report['records']),16)
        self.assertTrue(report['truncated']); self.assertFalse(report['rejected'])
        self.assertLessEqual(len(json.dumps(report,separators=(',',':')).encode()),3072)

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
