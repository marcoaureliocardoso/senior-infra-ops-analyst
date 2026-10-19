"""Pure numeric observations are data, not command freshness or input authority."""
import dataclasses
from decimal import Decimal
import importlib
from pathlib import Path
import unittest
from unittest import mock

from terminal_input_policy import TerminalInputPolicy, parse_context_percent
from terminal_state_adapter import TerminalCell, TerminalSnapshot


def grid(free='81', buffer='3', *, y=10, cursor=2):
    rows = [tuple(TerminalCell('', 1) for _ in range(120)) for _ in range(40)]
    for index, text in ((y, 'Context Usage'), (y+1, f'Free space: {free}%'),
            (y+2, f'Autocompact buffer: {buffer}%'), (37, '❯ ')):
        rows[index] = tuple(TerminalCell(char, 1) for char in text.ljust(120))
    return TerminalSnapshot('normal', cursor, 37, 0, 0, tuple(rows), {})


class ContextSampleTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(Path(__file__).with_name('terminal_context_sample.py').is_file(),
            'pure canonical numeric observation API is absent')
        self.module = importlib.import_module('terminal_context_sample')

    def test_decimal_identity_and_legacy_rounding(self):
        parse = self.module.parse_context_values
        a = parse('Context Usage\nFree space: 81%\nAutocompact buffer: 3%', True)
        b = parse('Context Usage\nFree space: 81.0%\nAutocompact buffer: 3.00%', True)
        c = parse('Context Usage\nFree space: 80%\nAutocompact buffer: 4%', True)
        self.assertEqual((a.free, a.buffer, a.used), (Decimal('81'), Decimal('3'), 16))
        self.assertEqual(a, b)
        self.assertEqual(c.used, 16)
        self.assertNotEqual(a, c)
        for free, used in (('81.5',16), ('80.5',16), ('81.5001',15)):
            text = f'Context Usage\nFree space: {free}%\nCompact buffer: 3%'
            self.assertEqual(parse(text).used, used)
            self.assertEqual(parse_context_percent(text), used)

    def test_parser_keeps_validation_and_rendered_order_contract(self):
        parse = self.module.parse_context_values
        for text in ('Context Usage\nFree space: 81%\nFree space: 80%',
                'Context Usage\nFree space: 81%\nCompact buffer:',
                'Context Usage\nFree space: 101%',
                'Context Usage\nFree space: 81%\nCompact buffer: 30%',
                'Free space: 81%\nCompact buffer: 3%',
                'Context Usage\nFree space: 81%\nCompact buffer: 3%\nCompact buffer: 4%'):
            for rendered in (False,True):
                with self.subTest(text=text, rendered=rendered):
                    self.assertIsNone(parse(text, rendered))
        result = parse('Context Usage\nFree space: 81%')
        self.assertEqual((result.free,result.buffer,result.used), (Decimal('81'),None,19))
        reversed_rows = 'Context Usage\n81% Free space\n3% Compact buffer'
        self.assertIsNone(parse(reversed_rows))
        self.assertEqual(parse(reversed_rows,True).used,16)

    def test_sample_is_pure_and_not_authority(self):
        current = grid()
        policy = TerminalInputPolicy()
        policy.mark_transition(current)
        before = dict(vars(policy))
        with mock.patch('builtins.open',side_effect=AssertionError('unexpected IO')), \
                mock.patch('time.monotonic',side_effect=AssertionError('unexpected clock')), \
                mock.patch.object(TerminalInputPolicy,'_observe',side_effect=AssertionError('sticky observer')):
            sample = self.module.sample_context(current)
            again = self.module.sample_context(current)
        self.assertEqual(sample,again)
        self.assertEqual(vars(policy),before)
        self.assertEqual(sample.geometry,('normal',0,0,(10,11,12)))
        self.assertEqual(self.module.sample_context(grid(cursor=18)),sample)
        self.assertNotEqual(self.module.sample_context(grid(y=11)).geometry,sample.geometry)
        self.assertEqual(self.module.sample_context(grid(y=11)).numbers,sample.numbers)
        self.assertIsNone(policy.context_percent(current))
        with self.assertRaises(dataclasses.FrozenInstanceError): sample.numbers.used = 99
        self.assertEqual(self.module.ContextNumbers(Decimal('81'),Decimal('3'),16),sample.numbers)


if __name__ == '__main__': unittest.main()
