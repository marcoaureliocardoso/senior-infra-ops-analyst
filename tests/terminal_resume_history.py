"""Private offline history facts, never an input/credential authorization API."""
from __future__ import annotations

from dataclasses import dataclass
import json
import re
import unicodedata

from terminal_state_adapter import TerminalCell

TEXT_PROMPT = 'P0-04B synthetic text control. Reply P004B_SKILL_OK only.'
SKILL_PROMPT = 'P0-04B synthetic. Invoke Skill(context-continuity) once; reply P004B_SKILL_OK. No browser.'
_TOKENS = {'CONTEXT': '/context', 'EXIT': '/exit',
           'SDK_TEXT': TEXT_PROMPT, 'SDK_SKILL': SKILL_PROMPT}
_LABEL = re.compile(r'[A-Za-z0-9_:/.-]{1,256}\Z')
_PADDING = {' ': 0, '\u00a0': 1}
MAX_SDK_BYTES = 5_000_000


@dataclass(frozen=True)
class HistoryProfile:
    kind: str
    marker_x: int
    gap: tuple[int, ...]
    tail: tuple[int, ...]


@dataclass(frozen=True)
class SDKFacts:
    valid: bool
    reason: str
    skill_calls: int


def match_history_row(row: tuple[TerminalCell, ...], kind: str) -> HistoryProfile | None:
    """Classify a complete fixed fixture, retaining only bounded geometry."""
    if type(kind) is not str or kind not in _TOKENS or type(row) is not tuple or len(row) != 120:
        return None
    characters = []
    for cell in row:
        if (type(cell) is not TerminalCell or type(cell.width) is not int or cell.width != 1
                or type(cell.text) is not str or len(cell.text) > 1):
            return None
        char = cell.text or ' '
        if char != '\u00a0' and (unicodedata.category(char).startswith('C')
                               or (char.isspace() and char != ' ')):
            return None
        characters.append(char)
    text = ''.join(characters)
    marker_x = len(text)-len(text.lstrip(' '))
    if marker_x == 120 or text[marker_x] != '❯' or text.count('❯') != 1:
        return None
    start = marker_x+1
    end = start
    while end < 120 and text[end] in _PADDING:
        end += 1
    token = _TOKENS[kind]
    if end == start or not text.startswith(token, end):
        return None
    tail = text[end+len(token):]
    if any(char not in _PADDING for char in tail):
        return None
    return HistoryProfile(kind, marker_x, tuple(_PADDING[c] for c in text[start:end]),
                          tuple(_PADDING[c] for c in tail))


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate field')
        result[key] = value
    return result


def _constant(_value):
    raise ValueError('nonfinite number')


class _SDKRejected(Exception):
    def __init__(self, reason):
        self.reason = reason


def _reject(reason):
    raise _SDKRejected(reason)


def _inspect_sdk_tree(value, expected_session, permitted_tools, depth=0):
    if depth > 32:
        _reject('BOUNDS')
    if isinstance(value, dict):
        if 'session_id' in value and value['session_id'] != expected_session:
            _reject('SESSION_MISMATCH')
        if value.get('parent_tool_use_id') is not None:
            _reject('TOOL_CONTRACT')
        if value.get('type') in ('tool_use', 'tool_result') and id(value) not in permitted_tools:
            _reject('TOOL_CONTRACT')
        for item in value.values():
            _inspect_sdk_tree(item, expected_session, permitted_tools, depth+1)
    elif isinstance(value, list):
        for item in value:
            _inspect_sdk_tree(item, expected_session, permitted_tools, depth+1)


def parse_sdk_sample(raw: bytes, *, expected_session: str, case_kind: str) -> SDKFacts:
    """Pure bounded stream validation. Facts cannot issue a resumed view."""
    calls = {}
    count = 0
    try:
        if (type(raw) is not bytes or not 0 < len(raw) <= MAX_SDK_BYTES):
            _reject('BOUNDS')
        if (type(expected_session) is not str or not _LABEL.fullmatch(expected_session)
                or case_kind not in ('text-turn', 'skill-turn')):
            _reject('MALFORMED')
        lines = raw.decode('utf-8').splitlines()
        if not 0 < len(lines) <= 4096:
            _reject('BOUNDS')
        initialized = finished = False
        for index, line in enumerate(lines):
            event = json.loads(line, object_pairs_hook=_unique, parse_constant=_constant)
            if type(event) is not dict:
                _reject('MALFORMED')
            event_type = event.get('type')
            if event_type not in ('system', 'assistant', 'user', 'result'):
                _reject('MALFORMED')
            if event.get('session_id') != expected_session:
                _reject('SESSION_MISMATCH')
            if finished:
                _reject('LIFECYCLE')
            is_init = event_type == 'system' and event.get('subtype') == 'init'
            if index == 0 and not is_init:
                _reject('LIFECYCLE')
            if is_init:
                if initialized:
                    _reject('LIFECYCLE')
                tools = event.get('tools')
                if (type(tools) is not list or len(tools) > 4096
                        or any(type(tool) is not str or not _LABEL.fullmatch(tool) for tool in tools)):
                    _reject('MALFORMED')
                initialized = True
            permitted = set()
            if event_type in ('assistant', 'user'):
                message = event.get('message')
                if type(message) is not dict or message.get('role') != event_type:
                    _reject('MALFORMED')
                blocks = message.get('content')
                if type(blocks) is not list or len(blocks) > 64:
                    _reject('BOUNDS')
                for block in blocks:
                    if type(block) is not dict:
                        _reject('MALFORMED')
                    block_type = block.get('type')
                    if block_type in ('text', 'thinking'):
                        if type(block.get('text' if block_type == 'text' else 'thinking')) is not str:
                            _reject('MALFORMED')
                        continue
                    if block_type not in ('tool_use', 'tool_result'):
                        _reject('TOOL_CONTRACT')
                    permitted.add(id(block))
                    if case_kind != 'skill-turn':
                        _reject('TOOL_CONTRACT')
                    if block_type == 'tool_use':
                        count = min(4, count+1)
                        identifier = block.get('id')
                        if (event_type != 'assistant' or type(identifier) is not str
                                or not _LABEL.fullmatch(identifier) or identifier in calls
                                or count != 1 or block.get('name') != 'Skill'
                                or block.get('input') != {'skill': 'context-continuity'}):
                            _reject('TOOL_CONTRACT')
                        calls[identifier] = False
                    else:
                        identifier = block.get('tool_use_id')
                        if (event_type != 'user' or type(identifier) is not str
                                or identifier not in calls or calls[identifier]
                                or ('is_error' in block and block['is_error'] is not False)):
                            _reject('TOOL_CONTRACT')
                        calls[identifier] = True
            _inspect_sdk_tree(event, expected_session, permitted)
            if event_type == 'result':
                if (not initialized or event.get('subtype') != 'success'
                        or event.get('is_error') is not False):
                    _reject('LIFECYCLE')
                if ((case_kind == 'skill-turn' and (count != 1 or not all(calls.values())))
                        or (case_kind == 'text-turn' and count != 0)):
                    _reject('TOOL_CONTRACT')
                finished = True
        if not initialized or not finished:
            _reject('LIFECYCLE')
        return SDKFacts(True, 'VALID', count)
    except _SDKRejected as error:
        return SDKFacts(False, error.reason, count)
    except (ValueError, TypeError, UnicodeError, RecursionError, OverflowError):
        return SDKFacts(False, 'MALFORMED', count)
