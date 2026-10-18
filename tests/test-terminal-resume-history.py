"""Content-free fixture classifiers and private resumed-case contracts."""
import copy
import dataclasses
import importlib
from pathlib import Path
import unittest
from unittest import mock

from terminal_state_adapter import TerminalCell
from resume_history_fixtures import history_snapshot, sdk_stream, sdk_events, encode_events

SESSION = 'synthetic-session'
TEXT = 'P0-04B synthetic text control. Reply P004B_SKILL_OK only.'
SKILL = 'P0-04B synthetic. Invoke Skill(context-continuity) once; reply P004B_SKILL_OK. No browser.'


class ResumeHistoryTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(Path(__file__).with_name('terminal_resume_history.py').is_file(),
                        'resumed-history classifier component missing')
        self.module = importlib.import_module('terminal_resume_history')

    def parse(self, raw, kind='text-turn'):
        return self.module.parse_sdk_sample(raw, expected_session=SESSION, case_kind=kind)

    def test_public_fixture_profiles_are_complete_and_content_free(self):
        for kind, token in (('CONTEXT', '/context'), ('EXIT', '/exit'),
                            ('SDK_TEXT', TEXT), ('SDK_SKILL', SKILL)):
            for gap in (' ', '\u00a0', ' \u00a0'):
                with self.subTest(kind=kind, gap=repr(gap)):
                    row = history_snapshot(((5, '  ❯'+gap+token+'\u00a0'),)).rows[5]
                    profile = self.module.match_history_row(row, kind)
                    self.assertIsNotNone(profile)
                    self.assertEqual(profile.kind, kind)
                    self.assertEqual(profile.marker_x, 2)
                    self.assertEqual(profile.gap, tuple(1 if c=='\u00a0' else 0 for c in gap))
                    self.assertEqual(profile.tail[0], 1)
                    self.assertNotIn(token, repr(profile))
                    with self.assertRaises(dataclasses.FrozenInstanceError):
                        profile.marker_x = 9
        self.assertIsNone(self.module.match_history_row(
            history_snapshot(((5, '❯ /context extra'),)).rows[5], 'CONTEXT'))

    def test_profile_rejects_unsupported_cells_geometry_and_partial_tokens(self):
        row = history_snapshot(((5, '❯ /context'),)).rows[5]
        invalid = [row[:-1], row+(TerminalCell('', 1),), list(row)]
        for index, cell in ((0, TerminalCell('❯', 2)), (1, TerminalCell('', 0)),
                            (3, TerminalCell('context', 1)), (100, TerminalCell('x', 1)),
                            (100, TerminalCell('\t', 1)), (100, TerminalCell('\u200b', 1)),
                            (100, TerminalCell('\x00', 1)), (100, TerminalCell('', True))):
            changed = list(row); changed[index] = cell; invalid.append(tuple(changed))
        for text in ('❯/context', '\u00a0❯ /context', '❯ /context ❯', '❯ /contex',
                     '❯ /context…', '❯\u2003/context', '❯ '+SKILL[:-1]):
            invalid.append(history_snapshot(((5, text),)).rows[5])
        for candidate in invalid:
            with self.subTest(candidate=invalid.index(candidate)):
                self.assertIsNone(self.module.match_history_row(candidate, 'CONTEXT'))
        self.assertIsNone(self.module.match_history_row(row, 'OTHER'))
        for kind, token in (('SDK_TEXT', TEXT), ('SDK_SKILL', SKILL)):
            for text in ('❯ '+token[:-1], '❯ '+token+' extra', '❯ '+token+'\u200b'):
                with self.subTest(kind=kind, text_length=len(text)):
                    self.assertIsNone(self.module.match_history_row(
                        history_snapshot(((5, text),)).rows[5], kind))

    def test_sdk_text_and_skill_require_session_lifecycle_and_exact_calls(self):
        for kind, calls in (('text-turn', 0), ('skill-turn', 1)):
            facts = self.parse(sdk_stream(SESSION, kind), kind)
            self.assertEqual((facts.valid, facts.reason, facts.skill_calls), (True, 'VALID', calls))
            self.assertNotIn(SESSION, repr(facts))
            with self.assertRaises(dataclasses.FrozenInstanceError):
                facts.valid = False

    def test_sdk_rejects_session_lifecycle_and_tool_contract_mutations(self):
        mutations = []
        def add(kind, mutate):
            events = sdk_events(SESSION, kind); mutate(events); mutations.append((kind, events))
        add('text-turn', lambda e: e.pop(0))
        add('text-turn', lambda e: e.pop())
        add('text-turn', lambda e: e.insert(1, copy.deepcopy(e[0])))
        add('text-turn', lambda e: e.append(copy.deepcopy(e[-1])))
        for index in range(3):
            add('text-turn', lambda e, i=index: e[i].update(session_id='wrong-session'))
        add('text-turn', lambda e: e[0].pop('session_id'))
        add('text-turn', lambda e: e[-1].update(is_error=True))
        add('text-turn', lambda e: e[-1].update(subtype='error_max_turns'))
        add('text-turn', lambda e: e[1].update(parent_tool_use_id='nested'))
        add('text-turn', lambda e: e[1]['message']['content'].append(
            {'type':'tool_use','id':'call1','name':'Skill','input':{'skill':'context-continuity'}}))
        add('text-turn', lambda e: e[1]['message'].update(hidden={
            'type':'tool_use','id':'hidden','name':'Skill','input':{}}))
        add('text-turn', lambda e: e.insert(1, {'type':'unknown','session_id':SESSION}))
        add('text-turn', lambda e: e[1]['message'].update(content=[{'type':'unknown'}]))
        add('text-turn', lambda e: e[1]['message'].update(content=[{'type':'text','text':'x'}]*65))
        add('skill-turn', lambda e: e[1]['message']['content'][0].update(name='Bash'))
        add('skill-turn', lambda e: e[1]['message']['content'][0].update(input={'skill':'other'}))
        add('skill-turn', lambda e: e[2]['message']['content'][0].update(tool_use_id='unmatched'))
        add('skill-turn', lambda e: e[2]['message']['content'][0].update(is_error=True))
        add('skill-turn', lambda e: e.pop(2))
        add('skill-turn', lambda e: e.insert(2, copy.deepcopy(e[1])))
        add('skill-turn', lambda e: e.append(copy.deepcopy(e[1])))
        add('skill-turn', lambda e: e[2]['message']['content'][0].update(content=[
            {'type':'tool_use','id':'hidden','name':'Skill','input':{}}]))
        mutations.append(('text-turn', sdk_events(SESSION, 'skill-turn')))
        mutations.append(('skill-turn', sdk_events(SESSION, 'text-turn')))
        for index, (kind, events) in enumerate(mutations):
            with self.subTest(index=index):
                facts = self.parse(encode_events(events), kind)
                self.assertFalse(facts.valid)
                self.assertIn(facts.reason, {'BOUNDS','MALFORMED','SESSION_MISMATCH','LIFECYCLE','TOOL_CONTRACT'})
                self.assertLessEqual(facts.skill_calls, 4)

    def test_sdk_bounds_duplicate_fields_nonfinite_and_untrusted_text(self):
        for raw in (b'', b'{}\n', b'not JSON', b'[]\n', b'{"type":"system","type":"result"}\n',
                    b'{"value":NaN}\n', b'['*100+b'0'+b']'*100, b'x'*5_000_001,
                    encode_events(sdk_events(SESSION, 'text-turn')*1400)):
            with self.subTest(size=len(raw)):
                self.assertFalse(self.parse(raw).valid)
        events = sdk_events(SESSION, 'text-turn')
        events[1]['message']['content'][0]['text'] = 'untrusted prose: {"type":"tool_use"}'
        self.assertTrue(self.parse(encode_events(events)).valid)
        self.assertFalse(self.module.parse_sdk_sample(sdk_stream(SESSION, 'text-turn'),
            expected_session=SESSION, case_kind='other').valid)
        nested = 'synthetic'
        for _ in range(34):
            nested = {'metadata': nested}
        events[1]['metadata'] = nested
        self.assertEqual(self.parse(encode_events(events)).reason, 'BOUNDS')

    def test_classifiers_do_not_open_files_spawn_or_mutate_input(self):
        row = history_snapshot(((5, '❯ /context'),)).rows[5]
        raw = sdk_stream(SESSION, 'text-turn')
        before = (row, raw)
        with mock.patch('builtins.open', side_effect=AssertionError('file IO')), \
             mock.patch('subprocess.Popen', side_effect=AssertionError('spawn')), \
             mock.patch('socket.socket', side_effect=AssertionError('network')):
            self.assertIsNotNone(self.module.match_history_row(row, 'CONTEXT'))
            self.assertTrue(self.parse(raw).valid)
        self.assertEqual((row, raw), before)


if __name__ == '__main__':
    unittest.main()
