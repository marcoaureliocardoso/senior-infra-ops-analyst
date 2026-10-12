"""Current-input semantic tests over explicit cell fixtures, without a model."""
import importlib.util
import dataclasses
from pathlib import Path
import unittest

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
