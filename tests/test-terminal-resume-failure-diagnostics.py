"""Closed optional history-check evidence; never acceptance or input authority."""
from dataclasses import replace
import json
import unittest
from unittest import mock

from context_display_fixtures import DisplayCase
import terminal_context_echo as echo
import terminal_resume_history as history
import terminal_structural_diagnostics as structural
from terminal_structural_diagnostics import TerminalDiagnostics


class ResumeFailureDiagnosticsTests(unittest.TestCase):
    def projection(self,error):
        project=getattr(history,'resume_failure_diagnostic',None)
        self.assertTrue(callable(project),'closed history failure projection is absent')
        return project(error)

    def test_actual_guards_freeze_distinct_checks_before_revocation(self):
        variants=(('return','RETIRED_PROFILE_RETURNED'),('duplicate','DUPLICATE_PROFILE'),
            ('move','UNOWNED_NEW_PROFILE'),('padding','PINNED_PROFILE_CHANGED'),
            ('geometry','GEOMETRY_CHANGED'),('forbidden','FORBIDDEN_UI'))
        for kind in ('text-turn','skill-turn'):
            for variant,check in variants:
                with self.subTest(kind=kind,variant=variant),DisplayCase(case_kind=kind,acceptance_pending=True) as c:
                    c.submit(); current=c.snapshot(commit=20); c.command.bind_history(current,3)
                    f=c.fixture; original=c.history
                    if variant=='return':
                        c.history=(); c.command.observe(c.snapshot(commit=20),4); c.history=original
                    elif variant=='duplicate': c.history=(*original,(7,original[0][1]))
                    elif variant=='move': c.history=((6,original[0][1]),)
                    elif variant=='padding': c.history=((5,original[0][1].replace('❯ ','❯\u00a0')),)
                    bad=c.snapshot(commit=20)
                    if variant=='geometry': bad=replace(bad,viewportY=1)
                    if variant=='forbidden': bad=c.snapshot(commit=20,extra=((8,'Press Esc to close'),))
                    with self.assertRaises(history.ResumeHistoryError) as caught:
                        history.validate_resume_view(c.view,policy=f.policy,snapshot=bad,frame=5,state=f.state,
                            scope=f.scope,native_owner=f.native,controller_owner=f.controller,transition_owner=f.transition)
                    self.assertEqual(history.resume_view_decision(c.view),'REJECTED')
                    self.assertEqual(c.command.phase,'REVOKED')
                    self.assertEqual(self.projection(caught.exception),{'phase':'POST_SUBMIT','check':check,
                        'caseKind':kind,'historyKind':('NONE' if variant in ('geometry','forbidden') else
                            'SDK_TEXT' if kind=='text-turn' else 'SDK_SKILL')})

    def test_normalization_guard_carries_its_own_subreason(self):
        with DisplayCase(acceptance_pending=True) as c:
            c.submit(); current=c.snapshot(commit=20); c.command.bind_history(current,3); f=c.fixture
            with self.assertRaises(history.ResumeHistoryError) as caught:
                echo._compose_input_assessment(f.policy,current,frame=4,state=f.state,scope=f.scope,
                    native_owner=f.native,controller_owner=f.controller,transition_owner=f.transition,
                    resume_view=c.view,context_command=c.command,normalized_snapshot=replace(current,cursorX=3))
            self.assertEqual(self.projection(caught.exception),{'phase':'POST_SUBMIT',
                'check':'NORMALIZATION_MISMATCH','caseKind':'text-turn','historyKind':'NONE'})
            self.assertEqual(history.resume_view_decision(c.view),'REJECTED')

    def test_unattached_exception_cannot_replay_or_mint_evidence(self):
        error=history.ResumeHistoryError('RESUME_HISTORY_LAYOUT_REJECTED')
        error._resume_history_failure={'phase':'POST_SUBMIT','check':'GEOMETRY_CHANGED',
            'caseKind':'text-turn','historyKind':'NONE'}
        self.assertIsNone(self.projection(error))
        self.assertIsNone(self.projection(RuntimeError('not diagnostic content')))

    def test_annotation_failure_never_prevents_revocation(self):
        with DisplayCase(acceptance_pending=True) as c:
            c.submit(); current=c.snapshot(commit=20); c.command.bind_history(current,3); f=c.fixture
            with mock.patch.object(history,'_capture_resume_failure',side_effect=ValueError('synthetic fault'),create=True):
                with self.assertRaises(history.ResumeHistoryError) as caught:
                    history.validate_resume_view(c.view,policy=f.policy,snapshot=replace(current,viewportY=1),
                        frame=4,state=f.state,scope=f.scope,native_owner=f.native,
                        controller_owner=f.controller,transition_owner=f.transition)
            self.assertEqual(caught.exception.reason,'RESUME_HISTORY_LAYOUT_REJECTED')
            self.assertEqual(history.resume_view_decision(c.view),'REJECTED')
            self.assertEqual(c.command.phase,'REVOKED')
            self.assertIsNone(self.projection(caught.exception))

    def test_closed_optional_field_replays_without_changing_base(self):
        detail={'phase':'POST_SUBMIT','check':'RETIRED_PROFILE_RETURNED',
            'caseKind':'text-turn','historyKind':'SDK_TEXT'}
        collector=TerminalDiagnostics()
        collector.add('failure','RESUME_HISTORY_LAYOUT_REJECTED',resumeViewDecision='REJECTED',resumeHistoryFailure=detail)
        report=collector.report()
        self.assertEqual(report,{'records':[{'point':'failure','reasonCode':'RESUME_HISTORY_LAYOUT_REJECTED',
            'resumeViewDecision':'REJECTED','resumeHistoryFailure':detail}],'truncated':False,'rejected':False})
        replay=TerminalDiagnostics()
        for row in report['records']:
            replay.add(row['point'],row['reasonCode'],**{k:v for k,v in row.items() if k not in ('point','reasonCode')})
        self.assertEqual(replay.report(),report)
        detail['check']='arbitrary rejected text'
        self.assertEqual(report['records'][0]['resumeHistoryFailure']['check'],'RETIRED_PROFILE_RETURNED')

    def test_invalid_optional_payload_is_omitted_without_rejecting_base(self):
        good={'phase':'POST_SUBMIT','check':'DUPLICATE_PROFILE','caseKind':'text-turn','historyKind':'SDK_TEXT'}
        for bad in (None,{},'untrusted content',{**good,'check':'untrusted content'},
                    {**good,'raw':'not allowed'},{**good,'caseKind':True},
                    {**good,'caseKind':'skill-turn'},{**good,'phase':'untrusted content'}):
            with self.subTest(bad=bad):
                collector=TerminalDiagnostics()
                collector.add('failure','RESUME_HISTORY_LAYOUT_REJECTED',resumeHistoryFailure=bad)
                self.assertEqual(collector.report(),{'records':[{'point':'failure',
                    'reasonCode':'RESUME_HISTORY_LAYOUT_REJECTED'}],'truncated':False,'rejected':False})

    def test_optional_field_never_appears_on_success_or_cleanup(self):
        detail={'phase':'POST_SUBMIT','check':'GEOMETRY_CHANGED','caseKind':'text-turn','historyKind':'NONE'}
        for point,reason in (('prompt_ready','CHECKPOINT'),('native_cleanup','CLEANUP_COMPLETED'),
                             ('failure','INPUT_PROBE_REVOKED')):
            collector=TerminalDiagnostics(); collector.add(point,reason,resumeHistoryFailure=detail)
            self.assertEqual(collector.report(),{'records':[{'point':point,'reasonCode':reason}],
                'truncated':False,'rejected':False})

    def test_optional_annotation_cannot_displace_cleanup_under_size_pressure(self):
        detail={'phase':'POST_SUBMIT','check':'GEOMETRY_CHANGED','caseKind':'text-turn','historyKind':'NONE'}
        collector=TerminalDiagnostics()
        collector.add('failure','RESUME_HISTORY_LAYOUT_REJECTED',resumeHistoryFailure=detail)
        for _ in range(13): collector.add('prompt_ready','CHECKPOINT')
        collector.add('native_cleanup','CLEANUP_COMPLETED',leaderReaped=True)
        collector.add('helper_cleanup','CLEANUP_COMPLETED',leaderReaped=True)
        self.assertFalse(collector.report()['truncated'])
        self.assertEqual([r['point'] for r in collector.report()['records']][-2:],['native_cleanup','helper_cleanup'])
        self.assertLessEqual(len(json.dumps(collector.report(),sort_keys=True).encode()),3072)

    def test_optional_detail_is_sacrificed_before_base_record_budget(self):
        detail={'phase':'POST_SUBMIT','check':'GEOMETRY_CHANGED','caseKind':'text-turn','historyKind':'NONE'}
        with mock.patch.object(structural,'MAX_BYTES',450):
            collector=TerminalDiagnostics()
            collector.add('failure','RESUME_HISTORY_LAYOUT_REJECTED',resumeHistoryFailure=detail)
            collector.add('prompt_ready','CHECKPOINT')
            collector.add('native_cleanup','CLEANUP_COMPLETED',leaderReaped=True)
            collector.add('helper_cleanup','CLEANUP_COMPLETED',leaderReaped=True)
            report=collector.report()
        self.assertEqual(len(report['records']),4)
        self.assertFalse(report['truncated']); self.assertFalse(report['rejected'])
        self.assertNotIn('resumeHistoryFailure',report['records'][0])
        self.assertLessEqual(len(json.dumps(report,sort_keys=True).encode()),450)


if __name__=='__main__': unittest.main()
