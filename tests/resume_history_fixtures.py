"""Hand-authored public fixtures; never mounted into a native namespace."""
import json

from terminal_state_adapter import TerminalCell, TerminalSnapshot


def history_snapshot(history=(), *, cursor_row=37):
    lines = dict(history)
    rows = []
    for index in range(40):
        text = lines.get(index, '❯ ' if index == cursor_row else '')
        if len(text) > 120:
            raise ValueError('fixture row too long')
        cells = [TerminalCell(char, 1) for char in text]
        cells.extend(TerminalCell('', 1) for _ in range(120-len(cells)))
        rows.append(tuple(cells))
    return TerminalSnapshot('normal', 2, cursor_row, 0, 0, tuple(rows), {})


def sdk_events(session, case_kind):
    events = [{'type': 'system', 'subtype': 'init', 'session_id': session,
               'tools': ['Skill']}]
    if case_kind == 'skill-turn':
        events.extend([
            {'type': 'assistant', 'session_id': session, 'parent_tool_use_id': None,
             'message': {'role': 'assistant', 'content': [
                 {'type': 'tool_use', 'id': 'call1', 'name': 'Skill',
                  'input': {'skill': 'context-continuity'}}]}},
            {'type': 'user', 'session_id': session, 'parent_tool_use_id': None,
             'message': {'role': 'user', 'content': [
                 {'type': 'tool_result', 'tool_use_id': 'call1',
                  'is_error': False, 'content': 'synthetic skill loaded'}]}},
        ])
    events.extend([
        {'type': 'assistant', 'session_id': session, 'parent_tool_use_id': None,
         'message': {'role': 'assistant', 'content': [
             {'type': 'text', 'text': 'P004B_SKILL_OK'}]}},
        {'type': 'result', 'session_id': session, 'subtype': 'success',
         'is_error': False, 'result': 'P004B_SKILL_OK'},
    ])
    return events


def encode_events(events):
    return b''.join(json.dumps(event).encode('utf-8')+b'\n' for event in events)


def sdk_stream(session, case_kind):
    return encode_events(sdk_events(session, case_kind))
