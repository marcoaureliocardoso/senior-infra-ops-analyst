"""Current-input semantic tests over explicit cell fixtures, without a model."""
import importlib.util
import ast
import dataclasses
from pathlib import Path
import unittest
from unittest import mock

from terminal_state_adapter import TerminalCell, TerminalSnapshot

MODULE=Path(__file__).with_name('terminal_input_policy.py')


def snapshot(lines=(),x=0,y=0,active='normal',base=0,view=0):
    rows=[]
    for index in range(40):
        cells=[]
        for char in lines[index] if index<len(lines) else '':
            if char=='界': cells.extend((TerminalCell(char,2),TerminalCell('',0)))
            else: cells.append(TerminalCell(char,1))
        cells.extend(TerminalCell('',1) for _ in range(120-len(cells)))
        rows.append(tuple(cells))
    return TerminalSnapshot(active,x,y,base,view,tuple(rows),{})


class TerminalInputPolicyTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(MODULE.is_file(),'terminal input policy missing')
        spec=importlib.util.spec_from_file_location('terminal_input_policy',MODULE)
        module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        self.policy=module.TerminalInputPolicy()
        self.policy.mark_transition(snapshot())

    def test_readiness_rejection_describes_actual_row_not_earlier_ignored_history(self):
        current=snapshot(['❯ /context','❯ P0-04B synthetic text control. Reply P004B_SKILL_OK only.',
            '❯ '],x=2,y=2)
        self.assertFalse(self.policy.ready(current))
        detail=self.policy.diagnostic_state(current)
        self.assertEqual(detail['readiness'],'UNSUPPORTED_MARKER')
        self.assertEqual(detail.get('readinessRejection'),{'rowRelation':'OTHER_CAPTURED_ROW',
            'rowCause':'UNRECOGNIZED_SHAPE','rowShape':'SDK_TEXT_PROMPT_SHAPE'})
        # The active gate deliberately still rejects the earlier control history.
        self.assertEqual(self.policy.empty_input_assessment(current).rowCause,'CONTROL_COMMAND_SHAPE')
        self.assertIsNone(self.policy.empty_input_anchor(current))

    def test_readiness_rejection_reports_parser_cause_and_cursor_relation(self):
        wide=snapshot(['❯ '],x=2)
        row=list(wide.rows[0]); row[0]=TerminalCell('❯',2); row[1]=TerminalCell('',0)
        wide=dataclasses.replace(wide,rows=(tuple(row),)+wide.rows[1:])
        cases=[(snapshot(['❯ private-draft'],x=2),'CURSOR_ROW','UNRECOGNIZED_SHAPE'),
            (snapshot(['❯\u200b','❯ '],x=2,y=1),'OTHER_CAPTURED_ROW','INVISIBLE_FORMAT_CHAR'),
            (snapshot(['❯\u2003','❯ '],x=2,y=1),'OTHER_CAPTURED_ROW','UNSUPPORTED_WHITESPACE'),
            (wide,'CURSOR_ROW','MARKER_WIDTH'),
            (snapshot(['❯ unknown'],x=2,base=50),'CURSOR_OUTSIDE_CAPTURE','UNRECOGNIZED_SHAPE')]
        for current,relation,cause in cases:
            with self.subTest(relation=relation,cause=cause):
                self.policy.mark_transition(snapshot())
                # Establish freshness independently of current cursor eligibility.
                self.policy.ready(snapshot(['❯ '],x=2))
                detail=self.policy.diagnostic_state(current)
                self.assertEqual(detail['readiness'],'UNSUPPORTED_MARKER')
                self.assertEqual(detail.get('readinessRejection'),{'rowRelation':relation,
                    'rowCause':cause,'rowShape':'OTHER'})
                self.assertNotIn('private-draft',repr(detail))

    def test_readiness_shape_is_exact_display_classification_not_history_permission(self):
        # Consume the public fixture, not any deleted native screen or transcript.
        source=ast.parse(Path(__file__).with_name('offline-terminal-resume-probe.py').read_text())
        assignment=next(node for node in ast.walk(source) if isinstance(node,ast.Assign)
            and any(isinstance(target,ast.Name) and target.id=='prompt' for target in node.targets)
            and isinstance(node.value,ast.IfExp))
        prompt=ast.literal_eval(assignment.value.orelse)
        for suffix,shape in (('', 'SDK_TEXT_PROMPT_SHAPE'),(' extra','OTHER'),
                ('\u200b','OTHER'),('!','OTHER')):
            with self.subTest(shape=shape,suffix=repr(suffix)):
                current=snapshot(['❯ '+prompt+suffix,'❯ '],x=2,y=1)
                self.policy.mark_transition(snapshot())
                self.assertFalse(self.policy.ready(current))
                detail=self.policy.diagnostic_state(current)
                self.assertEqual(detail.get('readinessRejection'),{'rowRelation':'OTHER_CAPTURED_ROW',
                    'rowCause':'INVISIBLE_FORMAT_CHAR' if suffix=='\u200b' else 'UNRECOGNIZED_SHAPE',
                    'rowShape':shape})
                self.assertIsNone(self.policy.empty_input_anchor(current))
                self.assertNotIn(prompt,repr(detail))

    def test_readiness_diagnostic_is_pure_detached_and_absent_for_other_decisions(self):
        rejected=snapshot(['❯ private-draft','❯ '],x=2,y=1)
        self.assertFalse(self.policy.ready(rejected))
        before=dict(vars(self.policy))
        with mock.patch('builtins.open',side_effect=AssertionError('unexpected IO')):
            detail=self.policy.diagnostic_state(rejected)
        self.assertIsInstance(detail.get('readinessRejection'),dict)
        detail['readinessRejection']['rowShape']='private-draft'
        self.assertEqual(self.policy.diagnostic_state(rejected)['readinessRejection']['rowShape'],'OTHER')
        self.assertEqual(vars(self.policy),before)
        cases=[(snapshot(['❯ '],x=2),False,'FRESHNESS_UNPROVEN'),
            (snapshot(['❯ '],x=2),True,'READY'),
            (snapshot(['Do you want to use this API key?','❯ private'],x=2,y=1),True,'AUTHENTICATION_REQUIRED'),
            (snapshot(['Yes, I trust this folder','❯ private'],x=2,y=1),True,'STARTUP_SELECTION'),
            (snapshot(['❯ /context']),True,'CANDIDATE_COUNT')]
        for current,fresh,reason in cases:
            with self.subTest(reason=reason):
                self.policy.mark_transition(snapshot())
                if fresh: self.policy.ready(snapshot(['❯ '],x=2))
                state_before=dict(vars(self.policy))
                detail=self.policy.diagnostic_state(current)
                self.assertEqual(detail['readiness'],reason)
                self.assertNotIn('readinessRejection',detail)
                self.assertEqual(vars(self.policy),state_before)

    def test_readiness_shape_geometry_and_padding_never_grant_input_authority(self):
        prompt='P0-04B synthetic text control. Reply P004B_SKILL_OK only.'
        row=snapshot(['❯ '+prompt]).rows[0]
        malformed=[row[:-1],row+(TerminalCell('',1),),
            row[:-1]+(TerminalCell('',0),),row[:-1]+(TerminalCell('',2),)]
        rows=[(candidate,'OTHER') for candidate in malformed]
        rows += [(snapshot([prefix+prompt+suffix]).rows[0],'SDK_TEXT_PROMPT_SHAPE')
            for prefix,suffix in (('❯ ',' '),(' \t❯\t','\t'),('❯\u00a0','\u00a0'))]
        for index,(candidate,shape) in enumerate(rows):
            with self.subTest(case=index):
                current=snapshot(['','❯ '],x=2,y=1)
                current=dataclasses.replace(current,rows=(candidate,)+current.rows[1:])
                self.policy.mark_transition(snapshot())
                self.assertFalse(self.policy.ready(current))
                self.assertEqual(self.policy.diagnostic_state(current).get('readinessRejection'),{
                    'rowRelation':'OTHER_CAPTURED_ROW','rowCause':'UNRECOGNIZED_SHAPE','rowShape':shape})
                self.assertIsNone(self.policy.empty_input_anchor(current))

    def test_context_completion_row_grammar(self):
        self.assertTrue(callable(getattr(self.policy,'_context_completion_row',None)),
            'bounded completion classifier missing')
        cases=[('❯ /context  Synthetic A',True),('  ❯  /context       Δelta',True),
            ('❯ /context  Cafe\u0301',True),('❯ /context',False),
            ('❯ /contextX  Synthetic A',False),('❯ /exit  Synthetic A',False),
            ('❯ /context  ',False),('❯ /context Synthetic A',False),
            ('❯ /context  Synthetic ❯',False)]
        for index,(text,want) in enumerate(cases):
            with self.subTest(case=index):
                self.assertEqual(self.policy._context_completion_row(snapshot([text]).rows[0]),want)

    def test_context_completion_row_cells_and_purity(self):
        self.assertTrue(callable(getattr(self.policy,'_context_completion_row',None)),
            'bounded completion classifier missing')
        valid=snapshot(['❯ /context  Synthetic A']).rows[0]
        malformed=[valid[:-1],valid+(TerminalCell('',1),),list(valid),None,
            (None,)+valid[1:],(TerminalCell('❯',0),)+valid[1:],
            (TerminalCell('❯',2),)+valid[1:],valid[:2]+(TerminalCell('/context',1),)+valid[3:]]
        malformed += [snapshot(['❯ /context  Synthetic'+char]).rows[0]
            for char in ('\u200b','\ufeff','\t','\u00a0','\u2003','\x01','界')]
        before=dict(vars(self.policy))
        with (mock.patch.object(self.policy,'_observe',side_effect=AssertionError('impure')) as observe,
                mock.patch('builtins.open',side_effect=AssertionError('IO')) as io):
            self.assertTrue(self.policy._context_completion_row(valid))
            # A combining sequence within one width-one renderer cell is still data.
            combined=valid[:12]+(TerminalCell('e\u0301',1),)+valid[13:]
            self.assertTrue(self.policy._context_completion_row(combined))
            for index,row in enumerate(malformed):
                with self.subTest(case=index): self.assertFalse(self.policy._context_completion_row(row))
            observe.assert_not_called(); io.assert_not_called()
        self.assertEqual(vars(self.policy),before)

    def test_completion_shape_alone_keeps_strict_assessment(self):
        current=snapshot(['❯ /context  Synthetic A','❯ '],x=2,y=1)
        self.policy.mark_transition(current)
        self.assertEqual(self.policy.empty_input_assessment(current).reason,'UNSUPPORTED_ROW')
        self.assertIsNone(self.policy.empty_input_anchor(current))
        self.assertFalse(self.policy.ready(current))
        self.assertIsNone(self.policy.context_percent(current))

    def test_current_input_forms(self):
        for text,x in [('❯',1),('❯ ',2),('❯\u00a0',2),('❯ ready',7),
                       ('❯ Try "fix tests"',2),('❯ Try "界"',2)]:
            with self.subTest(x=x):
                self.policy.mark_transition(snapshot())
                self.assertTrue(self.policy.ready(snapshot([text],x=x)))

    def require_active_anchor(self):
        self.assertTrue(callable(getattr(self.policy,'empty_input_anchor',None)),
            'pure empty-input eligibility missing')

    def test_active_anchor_rejects_suggestion_without_changing_passive_ready(self):
        self.require_active_anchor()
        for text,x in [('❯ Try "fix tests"',2),('❯ ready',7)]:
            self.policy.mark_transition(snapshot())
            current=snapshot([text],x=x)
            self.assertIsNone(self.policy.empty_input_anchor(current))
            self.assertTrue(self.policy.ready(current))

    def test_active_anchor_does_not_observe_stale_input(self):
        self.require_active_anchor()
        current=snapshot(['❯\u00a0'],x=2)
        self.policy.mark_transition(current)
        before=self.policy.diagnostic_state(current)
        anchor=self.policy.empty_input_anchor(current)
        self.assertEqual(vars(anchor),{'buffer':'normal','row':0,'cursorX':2,
            'baseY':0,'viewportY':0,'markerX':0})
        self.assertEqual(self.policy.diagnostic_state(current),before)
        self.assertFalse(self.policy.ready(current))
        with self.assertRaises(dataclasses.FrozenInstanceError): anchor.row=1

    def test_active_anchor_pinned_alternate_and_supported_padding(self):
        self.require_active_anchor()
        for padding in (' ','\t','\u00a0'):
            current=snapshot(['']*37+['❯'+padding],x=2,y=37,active='alternate')
            anchor=self.policy.empty_input_anchor(current)
            self.assertEqual((anchor.buffer,anchor.row,anchor.cursorX),('alternate',37,2))

    def test_empty_input_evaluation_classifies_each_rejection_without_relaxing_it(self):
        self.assertTrue(callable(getattr(self.policy,'empty_input_evaluation',None)),
            'shared empty-input evaluation missing')
        cases=[
            (snapshot(['Do you want to use this API key?','❯ '],x=2,y=1),'FORBIDDEN_STATE'),
            (snapshot(['Press Esc to close','❯ '],x=2,y=1),'FORBIDDEN_STATE'),
            (snapshot(),'NO_MARKER'),
            (snapshot(['❯\u200b'],x=2),'UNSUPPORTED_ROW'),
            (snapshot(['❯ /context','❯ '],x=2,y=1),'UNSUPPORTED_ROW'),
            (snapshot(['❯ Try "synthetic private text"'],x=2),'NONEMPTY_INPUT'),
            (snapshot(['❯ ready'],x=7),'NONEMPTY_INPUT'),
            (snapshot(['❯ ','❯ '],x=2,y=1),'MULTIPLE_MARKERS'),
            (snapshot(['❯ '],x=2,y=1),'CURSOR_ROW_MISMATCH'),
            (snapshot(['❯ '],x=0),'CURSOR_COLUMN_MISMATCH'),
            (snapshot([' '*103+'❯ '],x=105),'INSUFFICIENT_SPACE')]
        for current,expected in cases:
            with self.subTest(expected=expected):
                anchor,reason=self.policy.empty_input_evaluation(current)
                self.assertIsNone(anchor)
                self.assertEqual(reason,expected)
                self.assertIsNone(self.policy.empty_input_anchor(current))
                self.assertNotIn('synthetic private text',reason)

    def test_empty_input_evaluation_preserves_anchor_boundary_and_is_pure(self):
        self.assertTrue(callable(getattr(self.policy,'empty_input_evaluation',None)),
            'shared empty-input evaluation missing')
        for current,expected in (
                (snapshot(['']*37+['❯\u00a0'],x=2,y=37,active='alternate'),
                    {'buffer':'alternate','row':37,'cursorX':2,'baseY':0,'viewportY':0,'markerX':0}),
                (snapshot([' '*102+'❯ '],x=104),
                    {'buffer':'normal','row':0,'cursorX':104,'baseY':0,'viewportY':0,'markerX':102})):
            self.policy.mark_transition(current)
            before=dict(vars(self.policy))
            anchor,reason=self.policy.empty_input_evaluation(current)
            self.assertEqual(reason,'ELIGIBLE')
            self.assertEqual(vars(anchor),expected)
            self.assertEqual(vars(self.policy.empty_input_anchor(current)),expected)
            self.assertEqual(vars(self.policy),before)
            self.assertFalse(self.policy.ready(current))

    def test_unsupported_row_assessment_classifies_actual_parser_branch_and_location(self):
        self.assertTrue(callable(getattr(self.policy,'empty_input_assessment',None)),
            'content-free rejected-row assessment missing')
        wide=snapshot(['❯ '],x=2)
        rows=list(wide.rows); row=list(rows[0]); row[0]=TerminalCell('❯',2); row[1]=TerminalCell('',0)
        rows[0]=tuple(row); wide=dataclasses.replace(wide,rows=tuple(rows))
        cases=[
            (snapshot(['❯\u200b'],x=2),'CURSOR_ROW','INVISIBLE_FORMAT_CHAR'),
            (snapshot(['❯\u2003'],x=2),'CURSOR_ROW','UNSUPPORTED_WHITESPACE'),
            (snapshot(['❯\u2003\u200b'],x=2),'CURSOR_ROW','UNSUPPORTED_WHITESPACE'),
            (snapshot(['❯\u200b\u2003'],x=2),'CURSOR_ROW','INVISIBLE_FORMAT_CHAR'),
            (wide,'CURSOR_ROW','MARKER_WIDTH'),
            (snapshot(['❯ /context'],x=2),'CURSOR_ROW','CONTROL_COMMAND_SHAPE'),
            (snapshot(['❯ /exit','❯ '],x=2,y=1),'OTHER_CAPTURED_ROW','CONTROL_COMMAND_SHAPE'),
            (snapshot(['❯ /context','❯ '],x=2,y=1),'OTHER_CAPTURED_ROW','CONTROL_COMMAND_SHAPE'),
            (snapshot(['❯ /context'],x=2,base=50),'CURSOR_OUTSIDE_CAPTURE','CONTROL_COMMAND_SHAPE'),
            (snapshot(['❯ /context extra'],x=2),'CURSOR_ROW','UNRECOGNIZED_SHAPE'),
            (snapshot(['❯ /exit;other'],x=2),'CURSOR_ROW','UNRECOGNIZED_SHAPE'),
            (snapshot(['❯ synthetic-private-text'],x=2),'CURSOR_ROW','UNRECOGNIZED_SHAPE')]
        for current,relation,cause in cases:
            with self.subTest(relation=relation,cause=cause):
                assessment=self.policy.empty_input_assessment(current)
                self.assertIsNone(assessment.anchor)
                self.assertEqual(assessment.reason,'UNSUPPORTED_ROW')
                self.assertEqual((assessment.rowRelation,assessment.rowCause),(relation,cause))
                self.assertEqual(self.policy.empty_input_evaluation(current),(None,'UNSUPPORTED_ROW'))
                self.assertIsNone(self.policy.empty_input_anchor(current))
                self.assertNotIn('synthetic-private-text',repr(assessment))

    def test_row_assessment_is_immutable_pure_and_absent_for_other_decisions(self):
        self.assertTrue(callable(getattr(self.policy,'empty_input_assessment',None)),
            'content-free rejected-row assessment missing')
        current=snapshot(['❯ '],x=2)
        self.policy.mark_transition(current); before=dict(vars(self.policy))
        assessment=self.policy.empty_input_assessment(current)
        self.assertEqual(vars(assessment),{'anchor':self.policy.empty_input_anchor(current),
            'reason':'ELIGIBLE','rowRelation':None,'rowCause':None})
        self.assertEqual(vars(assessment.anchor),{'buffer':'normal','row':0,'cursorX':2,
            'baseY':0,'viewportY':0,'markerX':0})
        self.assertEqual(vars(self.policy),before)
        with self.assertRaises(dataclasses.FrozenInstanceError): assessment.rowCause='UNRECOGNIZED_SHAPE'
        for other,reason in ((snapshot(),'NO_MARKER'),
                (snapshot(['❯ Try "synthetic-private-text"'],x=2),'NONEMPTY_INPUT'),
                (snapshot(['❯ ','❯ '],x=2,y=1),'MULTIPLE_MARKERS')):
            detail=self.policy.empty_input_assessment(other)
            self.assertEqual((detail.reason,detail.rowRelation,detail.rowCause),(reason,None,None))
            self.assertNotIn('synthetic-private-text',repr(detail))
        self.assertEqual(vars(self.policy),before)
        self.assertFalse(self.policy.ready(current))

    def test_active_anchor_rejects_draft_history_auth_menus_and_modal(self):
        self.require_active_anchor()
        for lines in (['❯ /context'],['❯ existing draft'],['❯ /context','❯ '],
                ['❯ ','❯ '],['❯ Dark','❯ '],['❯ 1. Yes','❯ '],
                ['Do you want to use this API key?','❯ '],
                ['How would you like to log in?','❯ '],
                ['Yes, I trust this folder','❯ '],
                ['Choose the text style that looks best with your terminal','❯ '],
                ['Press Esc to close','❯ '],['Press Escape to close','❯ ']):
            with self.subTest(count=len(lines)):
                self.assertIsNone(self.policy.empty_input_anchor(snapshot(lines,x=2,y=len(lines)-1)))

    def test_active_anchor_rejects_cursor_invisible_and_space_overflow(self):
        self.require_active_anchor()
        for current in (snapshot(['❯ '],x=0),snapshot(['❯ '],x=2,y=1),
                snapshot(['❯ '],x=2,base=50),snapshot(['❯\u2003'],x=2),
                snapshot(['❯\u200b'],x=2),snapshot(['界❯ '],x=4),
                snapshot([' '*103+'❯ '],x=105)):
            self.assertIsNone(self.policy.empty_input_anchor(current))
        self.assertIsNotNone(self.policy.empty_input_anchor(snapshot([' '*102+'❯ '],x=104)))

    def test_structural_projection_does_not_observe_or_refresh_input(self):
        self.assertTrue(callable(getattr(self.policy,'diagnostic_state',None)),
            'passive diagnostic projection missing')
        old=snapshot(['status','❯ '],x=2,y=1)
        self.policy.mark_transition(old)
        # Merely sampling a changed input must not latch freshness.
        changed=snapshot(['status','❯ Try "synthetic secret"'],x=2,y=1)
        record=self.policy.diagnostic_state(changed)
        self.assertEqual(record,{'buffer':'normal','cursorX':2,'cursorY':1,'baseY':0,'viewportY':0,
            'candidateCount':1,'inputFresh':False,'contextFresh':False,'locationFresh':False,
            'authentication':'NONE','readiness':'FRESHNESS_UNPROVEN'})
        self.assertNotIn('synthetic secret',str(record))
        self.assertFalse(self.policy.ready(old))

    def test_structural_rejection_codes_follow_readiness_without_relaxing_it(self):
        self.assertTrue(callable(getattr(self.policy,'diagnostic_state',None)),
            'passive diagnostic projection missing')
        cases=[(['❯ '],2,0,'READY'),(['❯ ','❯ '],2,1,'CANDIDATE_COUNT'),
            (['❯ Dark','❯ '],2,1,'UNSUPPORTED_MARKER'),
            (['❯ '],2,1,'CURSOR_ROW_MISMATCH'),(['❯ '],0,0,'CURSOR_COLUMN_MISMATCH'),
            (['Do you want to use this API key?','❯ '],2,1,'AUTHENTICATION_REQUIRED'),
            (['Yes, I trust this folder','❯ '],2,1,'STARTUP_SELECTION')]
        for lines,x,y,reason in cases:
            with self.subTest(reason=reason):
                self.policy.mark_transition(snapshot())
                current=snapshot(lines,x=x,y=y)
                self.assertTrue(self.policy.ready(snapshot(['❯ '],x=2)))
                allowed=self.policy.ready(current)
                self.assertEqual(self.policy.diagnostic_state(current)['readiness'],reason)
                self.assertEqual(allowed,reason=='READY')

    def test_same_position_panel_close_reports_unproven_freshness(self):
        self.assertTrue(callable(getattr(self.policy,'diagnostic_state',None)),
            'passive diagnostic projection missing')
        panel=snapshot(['Context Usage','Free space: 81%','Autocompact buffer: 3%','❯ '],x=2,y=3)
        self.policy.mark_transition(panel)
        restored=snapshot(['','','','❯ '],x=2,y=3)
        self.assertFalse(self.policy.ready(restored))
        record=self.policy.diagnostic_state(restored)
        self.assertEqual(record['readiness'],'FRESHNESS_UNPROVEN')
        self.assertEqual([record[key] for key in ('inputFresh','contextFresh','locationFresh')],
            [False,True,False])

    def test_cursor_must_be_on_current_visible_candidate(self):
        for state in (snapshot(['❯ '],x=0),snapshot(['❯ '],x=2,y=1),
                      snapshot(['❯ '],x=2,base=50,view=0),
                      snapshot(['❯ ','❯ '],x=2,y=1),snapshot(['界❯ '],x=4)):
            self.policy.mark_transition(snapshot())
            self.assertFalse(self.policy.ready(state))

    def test_cursor_padding_has_material_bound(self):
        self.assertFalse(self.policy.ready(snapshot(['❯\u00a0'],x=119)))

    def test_history_menu_auth_and_padding(self):
        for value in ['❯ /context','❯ /exit','❯ P0-04B synthetic context measurement.',
                      '❯ 1. Selected option','❯ Dark','❯\u200b','❯\u2003','❯\ufeff',
                      '❯ Try unquoted','❯ Try “curly quotes”']:
            self.policy.mark_transition(snapshot())
            self.assertFalse(self.policy.ready(snapshot([value],x=2)))
        for heading in ['Choose the text style that looks best with your terminal',
                        'Yes, I trust this folder','Do you want to use this API key?',
                        'Select login method']:
            self.policy.mark_transition(snapshot())
            self.assertFalse(self.policy.ready(snapshot([heading,'❯ '],x=2,y=1)))
        self.policy.mark_transition(snapshot())
        self.assertFalse(self.policy.ready(snapshot(['❯ Dark','❯ '],x=2,y=1)))

    def test_known_history_does_not_supply_or_prevent_current_input(self):
        state=snapshot(['❯ /context','❯ P0-04B synthetic context measurement.','❯ '],x=2,y=2)
        self.assertTrue(self.policy.ready(state))
        self.policy.mark_transition(state)
        self.assertFalse(self.policy.ready(state))

    def test_status_redraw_cannot_refresh_stale_input(self):
        old=snapshot(['status','❯ '],x=2,y=1)
        self.policy.mark_transition(old)
        self.assertFalse(self.policy.ready(snapshot(['new status','❯ '],x=2,y=1)))
        self.assertTrue(self.policy.ready(snapshot(['new status','❯ Try "fix tests"'],x=2,y=1)))
        self.assertFalse(self.policy.ready(snapshot(['Yes, I trust this folder','❯ '],x=2,y=1)))

    def test_cursor_shift_alone_cannot_refresh_stale_input(self):
        self.policy.mark_transition(snapshot(['❯ '],x=2))
        self.assertFalse(self.policy.ready(snapshot(['status','❯ '],x=2,y=1)))

    def test_split_status_cursor_visit_cannot_refresh_stale_input(self):
        old=snapshot(['status','❯ '],x=2,y=1)
        for unrelated in ('new status','❯ Dark','❯ /exit'):
            with self.subTest(unrelated=unrelated):
                self.policy.mark_transition(old)
                for _ in range(3):
                    visiting=snapshot([unrelated,'❯ '],x=10,y=0)
                    self.assertFalse(self.policy.ready(visiting))
                    # Auth/context consumers observe redraws too; neither may latch input freshness.
                    self.policy.authentication(visiting)
                    self.policy.context_percent(visiting)
                    restored=snapshot([unrelated,'❯ '],x=2,y=1)
                    self.assertFalse(self.policy.ready(restored))
                self.assertFalse(self.policy.ready(old))

    def test_input_change_then_return_to_blank_is_fresh(self):
        blank=snapshot(['❯ '],x=2)
        self.policy.mark_transition(blank)
        self.assertFalse(self.policy.ready(snapshot(['❯ /context'],x=10)))
        self.assertTrue(self.policy.ready(blank))

    def test_cursor_column_jitter_does_not_refresh_unchanged_input(self):
        old=snapshot(['❯ '],x=2)
        self.policy.mark_transition(old)
        self.assertFalse(self.policy.ready(snapshot(['❯ '],x=0)))
        self.assertFalse(self.policy.ready(old))

    def test_partial_context_status_cannot_refresh_stale_location(self):
        old=snapshot(['status','❯ '],x=2,y=1)
        for label in ('Free space: 90%','Context Usage','Autocompact buffer: 3%'):
            self.policy.mark_transition(old)
            visiting=snapshot([label,'❯ '],x=10,y=0)
            self.assertIsNone(self.policy.context_percent(visiting))
            self.assertFalse(self.policy.ready(visiting))
            self.assertFalse(self.policy.ready(snapshot([label,'❯ '],x=2,y=1)))

    def test_normalization_does_not_hide_unsupported_padding(self):
        state=snapshot(['❯\u00a0'],x=2)
        self.assertEqual(self.policy.screen_text(state).splitlines()[0],'❯')
        self.assertTrue(self.policy.ready(state))
        self.policy.mark_transition(snapshot())
        self.assertFalse(self.policy.ready(snapshot(['❯\u2003'],x=2)))

    def test_authentication_classifications_are_closed(self):
        self.assertEqual(self.policy.authentication(snapshot(['Do you want to use this API key?'])),
            'api_key_approval_required')
        self.assertEqual(self.policy.authentication(snapshot(['How would you like to log in?'])),
            'login_required')
        self.assertIsNone(self.policy.authentication(snapshot(['ordinary status'])))

    def test_context_exact_numeric_labels(self):
        for lines,expected in [(['Context Usage','Free space: 90%','Autocompact buffer: 3%'],7),
                               (['Context Usage','Free space: 100%'],0),
                               (['Context Usage','Free space: 0%'],100),
                               (['Context Usage','Free space: 82.9%','Compact buffer: 3%'],14)]:
            self.policy.mark_transition(snapshot())
            self.assertEqual(self.policy.context_percent(snapshot(lines)),expected)
        for lines in [['Free space: 90%'],['Context Usage','Free space:'],
                      ['Context Usage','Free space: 90%','Free space: 80%'],
                      ['Context Usage','Free space: 100%','Compact buffer: 3%'],
                      ['Context Usage','Free space: 90%','Compact buffer:']]:
            self.policy.mark_transition(snapshot())
            self.assertIsNone(self.policy.context_percent(snapshot(lines)))

    def test_old_context_and_unrelated_status_remain_unproven(self):
        old=snapshot(['Context Usage','Free space: 90%'])
        self.policy.mark_transition(old)
        self.assertIsNone(self.policy.context_percent(snapshot(['Context Usage','Free space: 90%','status'])))
        self.assertIsNone(self.policy.context_percent(snapshot(['status','Context Usage','Free space: 90%'])))


if __name__=='__main__': unittest.main()
