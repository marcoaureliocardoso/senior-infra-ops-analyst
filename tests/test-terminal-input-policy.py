"""Current-input semantic tests over explicit cell fixtures, without a model."""
import importlib.util
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
