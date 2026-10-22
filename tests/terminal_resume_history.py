"""Private offline history facts, never an input/credential authorization API."""
from __future__ import annotations

from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import re
import stat
import time
from typing import BinaryIO
import unicodedata
import weakref

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


# Trusted supervisor-owned objects. Pure classifiers above never consult these.
RESUME_REASONS = frozenset('RESUME_HISTORY_'+suffix for suffix in (
    'SCOPE_REJECTED','SDK_REJECTED','LAYOUT_REJECTED','REPLAY_REJECTED','REVOKED'))
_SEAL = object()
_CASES = weakref.WeakKeyDictionary()
_SINKS = weakref.WeakKeyDictionary()
_PENDING = weakref.WeakKeyDictionary()
_LAUNCHES = weakref.WeakKeyDictionary()
_OFFERS = weakref.WeakKeyDictionary()
_VIEWS = weakref.WeakKeyDictionary()
_OBS_REQUESTS = weakref.WeakKeyDictionary()
_OBS_GUARDS = weakref.WeakKeyDictionary()
_OBS_RESULTS = weakref.WeakKeyDictionary()


class ResumeHistoryError(RuntimeError):
    def __init__(self, reason):
        self.reason = reason if type(reason) is str and reason in RESUME_REASONS else 'RESUME_HISTORY_REVOKED'
        super().__init__(self.reason)


_FAILURE_OBSERVATIONS = weakref.WeakKeyDictionary()
_LAYOUT_CHECKS = frozenset(('GEOMETRY_CHANGED','FORBIDDEN_UI','DUPLICATE_PROFILE',
    'PINNED_PROFILE_CHANGED','RETIRED_PROFILE_RETURNED','UNOWNED_NEW_PROFILE',
    'UNRECOGNIZED_HISTORY_ROW','INPUT_ANCHOR_REJECTED','COMPOSE_ROW_CONFLICT','NORMALIZATION_MISMATCH'))


def valid_resume_failure(value):
    if (type(value) is not dict or set(value)!={'phase','check','caseKind','historyKind'}
            or any(type(item) is not str for item in value.values())): return False
    return (value['phase'] in ('BINDING','BOUND','POST_SUBMIT') and value['check'] in _LAYOUT_CHECKS
        and value['caseKind'] in ('text-turn','skill-turn')
        and value['historyKind'] in ('NONE','CONTEXT','EXIT',
            'SDK_TEXT' if value['caseKind']=='text-turn' else 'SDK_SKILL'))


def _capture_resume_failure(error,record,check,history_kind='NONE'):
    # Closed scalars only, frozen before revocation; no case, row or owner survives.
    if type(error) is not ResumeHistoryError or error.reason!='RESUME_HISTORY_LAYOUT_REJECTED': return
    case=_CASES.get(record.get('case')) if type(record) is dict else None
    if case is None: return
    value={'phase':record.get('phase','BINDING'),'check':check,
        'caseKind':case['kind'],'historyKind':history_kind}
    if valid_resume_failure(value) and error not in _FAILURE_OBSERVATIONS:
        _FAILURE_OBSERVATIONS[error]=tuple(value.items())


def resume_failure_diagnostic(error):
    # Exception identity, not an attribute or serialized observation, is the key.
    if type(error) is not ResumeHistoryError or error.reason!='RESUME_HISTORY_LAYOUT_REJECTED': return None
    frozen=_FAILURE_OBSERVATIONS.get(error)
    value=dict(frozen) if frozen is not None else None
    return value if valid_resume_failure(value) else None


def _resume_layout_error(view,check,*,offer=None):
    error=ResumeHistoryError('RESUME_HISTORY_LAYOUT_REJECTED')
    try:
        record=_OFFERS.get(offer) if view is None else _VIEWS.get(view)
        _capture_resume_failure(error,record,check)
    except Exception: pass  # Optional observation must not interfere with revocation.
    return error


class _Branded:
    __slots__ = ('__weakref__',)
    def __new__(cls, seal=None):
        if seal is not _SEAL:
            raise ResumeHistoryError('RESUME_HISTORY_SCOPE_REJECTED')
        return super().__new__(cls)

    def __repr__(self):
        return '<'+type(self).__name__+'>'


class OfflineCase(_Branded): __slots__ = ()
class InitialCompletionSink(_Branded): __slots__ = ()
class PendingInitialCompletion(_Branded): __slots__ = ()
class SDKLaunch(_Branded): __slots__ = ()
class ResumeOffer(_Branded): __slots__ = ()
class ResumedHistoryView(_Branded): __slots__ = ()
class PostEnterObservationRequest(_Branded): __slots__ = ()
class PostEnterHistoryGuard(_Branded): __slots__ = ()


def _now():
    return time.monotonic()


def close_offline_case(case: OfflineCase) -> None:
    _close_offline_case(case,'INPUT_PROBE_REVOKED')


def _close_offline_case(case, reason):
    if type(case) is not OfflineCase:
        return
    dependents = []; observations=[]
    _CASES.pop(case, None)
    for registry in (_SINKS, _PENDING, _LAUNCHES, _OFFERS, _VIEWS, _OBS_REQUESTS, _OBS_GUARDS):
        for value, record in list(registry.items()):
            if record['case'] is case:
                registry.pop(value, None)
                dependents.extend(record.get('dependents', ()))
                if registry is _OBS_REQUESTS and not record.get('result_taken'):
                    observations.append((value,record.get('observer')))
    # Remove every capability before callbacks, preventing recursive reactivation.
    for dependent in dependents:
        current = dependent()
        if current is not None:
            current.invalidate(reason)
    # A fatal guard removes all operational authority first. Keep only the
    # actual observer's closed, sanitized result for its one-shot consumer.
    # No case/owner/row reference survives in this non-authoritative tombstone.
    if observations:
        from terminal_post_enter_observation import PostEnterObservation,_OBSERVATIONS,valid_observation_summary
        for request,observer in observations:
            try:
                evidence=_OBSERVATIONS.get(observer) if type(observer) is PostEnterObservation else None
                if evidence is not None and evidence.get('closed'):
                    summary=observer.summary()
                    if valid_observation_summary(summary): _OBS_RESULTS[request]=summary
            except Exception: pass  # Optional projection cannot interrupt revocation.


def _fail(record, reason='RESUME_HISTORY_SCOPE_REJECTED', *, check=None, history_kind='NONE'):
    error=ResumeHistoryError(reason)
    try: _capture_resume_failure(error,record,check,history_kind)
    except Exception: pass
    if record is not None:
        _close_offline_case(record['case'],reason)
    raise error


def _identity(path, *, directory):
    value = path.lstat()
    if (value.st_uid != os.getuid() or stat.S_ISLNK(value.st_mode)
            or not (stat.S_ISDIR(value.st_mode) if directory else stat.S_ISREG(value.st_mode))):
        raise ValueError('owned identity rejected')
    return value.st_dev, value.st_ino, value.st_uid, stat.S_IFMT(value.st_mode)


def _case(case, phases=None):
    record = _CASES.get(case) if type(case) is OfflineCase else None
    if record is None:
        _fail(None)
    try:
        now = _now()
        if (not math.isfinite(now) or now < record['time'] or now >= record['deadline']
                or _identity(record['root'],directory=True) != record['root_identity']
                or _identity(record['root']/'project',directory=True) != record['project_identity']
                or Path.cwd() != record['root']/'project'
                or record['root'].resolve(strict=True) != record['root']):
            _fail(record)
        if phases is not None and record['phase'] not in phases:
            _fail(record,'RESUME_HISTORY_REPLAY_REJECTED')
        record['time'] = now
        return record
    except (OSError,ValueError,AttributeError):
        _fail(record)


def create_offline_case(root: Path, *, session_id: str, case_kind: str, owner: object) -> OfflineCase:
    from terminal_input_challenge import _audit
    try:
        _audit()
        if (type(root) is not Path and not isinstance(root,Path)) or not root.is_absolute():
            raise ValueError('root rejected')
        if (type(session_id) is not str or not _LABEL.fullmatch(session_id)
                or case_kind not in ('text-turn','skill-turn') or type(owner) is not object
                or root.resolve(strict=True) != root or Path.cwd() != root/'project'):
            raise ValueError('case rejected')
        root_identity = _identity(root,directory=True)
        project_identity = _identity(root/'project',directory=True)
        now = _now()
        if not math.isfinite(now): raise ValueError('clock rejected')
    except (OSError,ValueError,RuntimeError,AttributeError):
        _fail(None)
    case = OfflineCase(_SEAL)
    _CASES[case] = {'case':case,'root':root,'root_identity':root_identity,
        'project_identity':project_identity,'session':session_id,'kind':case_kind,
        'owner':owner,'deadline':now+165,'time':now,'phase':'CREATED'}
    return case


def _argv(record, stage):
    common = ('--strict-mcp-config','--mcp-config',str(record['root']/'mcp.json'))
    if stage != 'sdk':
        return ('/opt/probe/claude','--session-id' if stage=='initial' else '--resume',record['session'],*common)
    return ('/opt/probe/claude','-p',SKILL_PROMPT if record['kind']=='skill-turn' else TEXT_PROMPT,
        '--resume',record['session'],*common,'--permission-mode','default','--tools','Skill',
        '--allowedTools','Skill(context-continuity)','--include-hook-events','--verbose',
        '--output-format','stream-json','--max-turns','4')


def _scope(state, scope):
    from terminal_input_challenge import _context_scope_binding
    return _context_scope_binding(scope,state,allow_claimed=True)


def _binding(case, state, scope, command, stage):
    record = _case(case)
    try:
        run, deadline = _scope(state,scope)
        if type(command) is not tuple or command != _argv(record,stage):
            _fail(record)
    except (RuntimeError,TypeError,AttributeError):
        _fail(record)
    return {'case':case,'state':state,'scope':scope,'run':run,'deadline':deadline,'command':command}


def initial_completion_sink(case, *, state, scope, command):
    record = _case(case,('CREATED',))
    if 'sink' in record: _fail(record,'RESUME_HISTORY_REPLAY_REJECTED')
    binding = _binding(case,state,scope,command,'initial')
    value = InitialCompletionSink(_SEAL)
    _SINKS[value] = binding
    record['sink'] = weakref.ref(value)
    return value


def _registered(value, registry, expected_type):
    record = registry.get(value) if type(value) is expected_type else None
    if record is None: _fail(None)
    _case(record['case'])
    return record


def validate_initial_sink(sink, *, state, scope, command):
    record = _registered(sink,_SINKS,InitialCompletionSink)
    _case(record['case'],('CREATED',))
    if state is not record['state'] or scope is not record['scope'] or command != record['command']:
        _fail(record)
    _binding(record['case'],state,scope,command,'initial')


def bind_initial_sink(sink, *, controller_owner, native_owner, transition_owner):
    record = _registered(sink,_SINKS,InitialCompletionSink)
    validate_initial_sink(sink,state=record['state'],scope=record['scope'],command=record['command'])
    if ('controller' in record or type(controller_owner) is not object or type(transition_owner) is not object
            or not callable(getattr(native_owner,'poll',None)) or native_owner.poll() is not None):
        _fail(record)
    record.update(controller=controller_owner,native=native_owner,transition=transition_owner)


def capture_initial_completion(sink, *, controller_owner, state, scope, native_owner,
                               transition_owner, context_command, probe, frame, exit_written):
    from terminal_context_echo import _initial_context_facts
    from terminal_input_challenge import _initial_nonce_completed
    from terminal_state_adapter import MAX_CAPTURE
    record = _registered(sink,_SINKS,InitialCompletionSink)
    validate_initial_sink(sink,state=state,scope=scope,command=record['command'])
    try:
        if (any(record.get(key) is not value for key,value in (
                ('controller',controller_owner),('native',native_owner),('transition',transition_owner)))
                or type(frame) is not int or not 0 <= frame <= MAX_CAPTURE
                or type(exit_written) is not int or exit_written != 6
                or native_owner.poll() != 0 or 'captured' in record):
            _fail(record)
        facts = _initial_context_facts(context_command,state=state,scope=scope,
            native_owner=native_owner,transition_owner=transition_owner)
        if facts != (8,1) or not _initial_nonce_completed(probe,state=state,scope=scope,
                native_owner=native_owner,transition_owner=transition_owner):
            _fail(record)
    except (RuntimeError,TypeError,AttributeError):
        _fail(record)
    value = PendingInitialCompletion(_SEAL)
    _PENDING[value] = {'case':record['case'],'state':state,'scope':scope,'native':native_owner,
                       'deadline':record['deadline']}
    record['captured'] = True
    return value


def finish_initial_completion(pending, *, result, native_cleanup, helper_cleanup):
    record = _registered(pending,_PENDING,PendingInitialCompletion)
    case = _case(record['case'],('CREATED',))
    if (type(result) is not int or result != 0 or native_cleanup != 'CLEANUP_COMPLETED'
            or helper_cleanup != 'CLEANUP_COMPLETED' or record['native'].poll() != 0
            or not record['state'].helper_reaped or _now() >= record['deadline']):
        _fail(record)
    case.update(phase='INITIAL_COMPLETE',initial_state=weakref.ref(record['state']),
                initial_scope=weakref.ref(record['scope']))
    _PENDING.pop(pending)
    sink = case.pop('sink')()
    if sink is not None: _SINKS.pop(sink,None)


def sdk_started(case, *, child, command, stream: BinaryIO):
    import fcntl
    record = _case(case,('INITIAL_COMPLETE',))
    try:
        path = Path(stream.name)
        status = os.fstat(stream.fileno())
        identity = (status.st_dev,status.st_ino,status.st_uid,stat.S_IFMT(status.st_mode))
        if (type(command) is not tuple or command != _argv(record,'sdk')
                or tuple(child.args) != command or child.poll() is not None
                or path != record['root']/'sdk.stream' or _identity(path,directory=False) != identity
                or status.st_mode & 0o077 or status.st_nlink != 1
                or fcntl.fcntl(stream.fileno(),fcntl.F_GETFL) & os.O_ACCMODE != os.O_RDWR):
            _fail(record,'RESUME_HISTORY_SDK_REJECTED')
    except (OSError,ValueError,TypeError,AttributeError):
        _fail(record,'RESUME_HISTORY_SDK_REJECTED')
    launch = SDKLaunch(_SEAL)
    _LAUNCHES[launch] = {'case':case,'child':child,'command':command,'stream':stream,'identity':identity,
                         'deadline':min(record['deadline'],_now()+25)}
    record['phase'] = 'SDK_RUNNING'
    return launch


def sdk_finished(launch):
    record = _registered(launch,_LAUNCHES,SDKLaunch)
    case = _case(record['case'],('SDK_RUNNING',))
    if _now() >= record['deadline']: _fail(record,'RESUME_HISTORY_SDK_REJECTED')
    try:
        stream = record['stream']; status = os.fstat(stream.fileno())
        if ((status.st_dev,status.st_ino,status.st_uid,stat.S_IFMT(status.st_mode)) != record['identity']
                or tuple(record['child'].args) != record['command'] or record['child'].poll() != 0):
            _fail(record,'RESUME_HISTORY_SDK_REJECTED')
        stream.flush(); stream.seek(0)
        facts = parse_sdk_sample(stream.read(MAX_SDK_BYTES+1),expected_session=case['session'],case_kind=case['kind'])
        _case(record['case'],('SDK_RUNNING',))
        if _now() >= record['deadline']: _fail(record,'RESUME_HISTORY_SDK_REJECTED')
    except (OSError,ValueError,TypeError,AttributeError):
        _fail(record,'RESUME_HISTORY_SDK_REJECTED')
    _LAUNCHES.pop(launch,None)
    if facts.valid: case['phase'] = 'SDK_VALIDATED'
    else: close_offline_case(record['case'])
    return facts


def offer_resume(case, *, state, scope, command):
    record = _case(case,('SDK_VALIDATED',))
    if state is record['initial_state']() or scope is record['initial_scope']():
        _fail(record)
    binding = _binding(case,state,scope,command,'resume')
    value = ResumeOffer(_SEAL)
    _OFFERS[value] = binding
    record['phase'] = 'VIEW_OFFERED'
    return value


def validate_resume_offer(offer, *, state, scope, command):
    record = _registered(offer,_OFFERS,ResumeOffer)
    _case(record['case'],('VIEW_OFFERED',))
    if state is not record['state'] or scope is not record['scope'] or command != record['command']:
        _fail(record)
    _binding(record['case'],state,scope,command,'resume')


def _frame(record, snapshot, frame):
    from terminal_state_adapter import TerminalSnapshot, MAX_CAPTURE
    if (type(snapshot) is not TerminalSnapshot or type(frame) is not int or not 0 <= frame <= MAX_CAPTURE
            or frame < record.get('frame',0)
            or (frame == record.get('frame') and snapshot is not record['snapshot']())):
        _fail(record,'RESUME_HISTORY_REPLAY_REJECTED')
    record.update(frame=frame,snapshot=weakref.ref(snapshot))


def _current_binding(record, native_owner, controller_owner, transition_owner):
    try:
        run, deadline = _scope(record['state'],record['scope'])
        if (run is not record['run'] or deadline != record['deadline'] or native_owner.poll() is not None
                or type(controller_owner) is not object or type(transition_owner) is not object):
            _fail(record)
    except (RuntimeError,TypeError,AttributeError):
        _fail(record)


def _profiles(case, policy, snapshot, *, binding, allow_context_repeats=False, failure_record=None):
    cursor = snapshot.baseY+snapshot.cursorY-snapshot.viewportY
    profiles = {}
    kinds = ('CONTEXT','EXIT','SDK_SKILL' if case['kind']=='skill-turn' else 'SDK_TEXT')
    for index, row in enumerate(snapshot.rows):
        if index == cursor: continue
        profile = next((candidate for kind in kinds
            if (candidate := match_history_row(row,kind)) is not None),None)
        if profile is not None:
            if (profile.kind in (p.kind for p in profiles.values())
                    and not (allow_context_repeats and profile.kind == 'CONTEXT')):
                _fail(failure_record if failure_record is not None else case,
                    'RESUME_HISTORY_LAYOUT_REJECTED',check='DUPLICATE_PROFILE',history_kind=profile.kind)
            profiles[index] = profile
        elif binding and re.match(r'^\s*❯',policy._row_text(row)):
            _fail(failure_record if failure_record is not None else case,
                'RESUME_HISTORY_LAYOUT_REJECTED',check='UNRECOGNIZED_HISTORY_ROW')
    return profiles


def try_bind_resume_view(offer, *, policy, snapshot, frame, native_owner, controller_owner, transition_owner):
    record = _registered(offer,_OFFERS,ResumeOffer)
    validate_resume_offer(offer,state=record['state'],scope=record['scope'],command=record['command'])
    _current_binding(record,native_owner,controller_owner,transition_owner)
    _frame(record,snapshot,frame)
    if policy.active_input_forbidden(snapshot): _fail(record,'RESUME_HISTORY_LAYOUT_REJECTED',check='FORBIDDEN_UI')
    case = _case(record['case'])
    profiles = _profiles(case,policy,snapshot,binding=True,failure_record=record)
    assessment,_ = policy._empty_input_assessment(snapshot,_excluded_rows=frozenset(profiles))
    if assessment.reason == 'NO_MARKER': return None
    if assessment.anchor is None: _fail(record,'RESUME_HISTORY_LAYOUT_REJECTED',check='INPUT_ANCHOR_REJECTED')
    policy._observe(snapshot)
    if not policy._input_is_fresh(): return None
    view = ResumedHistoryView(_SEAL)
    _VIEWS[view] = {**record,'policy':policy,'native':native_owner,'controller':controller_owner,
        'transition':transition_owner,'geometry':(snapshot.active,snapshot.baseY,snapshot.viewportY),
        'profiles':profiles,'phase':'BOUND','dependents':[],'retired':set()}
    _OFFERS.pop(offer)
    return view


def validate_resume_view(view, *, policy, snapshot, frame, state, scope, native_owner, controller_owner, transition_owner):
    record = _registered(view,_VIEWS,ResumedHistoryView)
    _current_binding(record,native_owner,controller_owner,transition_owner)
    if (record['phase'] not in ('BOUND','POST_SUBMIT') or any(record[key] is not value for key,value in (
            ('policy',policy),('state',state),('scope',scope),('native',native_owner),
            ('controller',controller_owner),('transition',transition_owner)))):
        _fail(record)
    _frame(record,snapshot,frame)
    if record['geometry'] != (snapshot.active,snapshot.baseY,snapshot.viewportY):
        _fail(record,'RESUME_HISTORY_LAYOUT_REJECTED',check='GEOMETRY_CHANGED')
    if policy.active_input_forbidden(snapshot):
        _fail(record,'RESUME_HISTORY_LAYOUT_REJECTED',check='FORBIDDEN_UI')
    post = record['phase'] == 'POST_SUBMIT'
    return _history_indices(record,policy,snapshot,post=post,
        current_acked=lambda: _current_command_acked(view,record))


def _history_indices(record,policy,snapshot,*,post,current_acked):
    profiles = _profiles(_case(record['case']),policy,snapshot,binding=False,allow_context_repeats=post,failure_record=record)
    pinned = record['profiles']
    for index, expected in pinned.items():
        actual = profiles.get(index)
        if index in record['retired']:
            if actual is not None: _fail(record,'RESUME_HISTORY_LAYOUT_REJECTED',
                check='RETIRED_PROFILE_RETURNED',history_kind=actual.kind)
        elif actual != expected:
            if not post or actual is not None: _fail(record,'RESUME_HISTORY_LAYOUT_REJECTED',
                check='PINNED_PROFILE_CHANGED',history_kind=expected.kind)
            record['retired'].add(index)
    for index, actual in profiles.items():
        if index in pinned: continue
        # New current-command history is not an old-history exclusion. The fresh
        # command/receipt must justify it separately; retired baseline identity
        # cannot be promoted or interpreted as movement into that row.
        context_retired = any(pinned[i].kind == 'CONTEXT' for i in record['retired'])
        if (not post or actual.kind != 'CONTEXT' or context_retired
                or not current_acked()):
            _fail(record,'RESUME_HISTORY_LAYOUT_REJECTED',check='UNOWNED_NEW_PROFILE',history_kind=actual.kind)
    return frozenset(index for index in pinned if index not in record['retired'])


def offer_post_enter_observation(case, *, state, scope, command):
    from terminal_input_challenge import _audit
    _audit()
    record=_case(case,('SDK_VALIDATED',))
    if record['kind']!='text-turn': _fail(record)
    offer=offer_resume(case,state=state,scope=scope,command=command)
    request=PostEnterObservationRequest(_SEAL)
    _OFFERS[offer]['observation_request']=request
    _OBS_REQUESTS[request]={**_OFFERS[offer],'offer':offer,'phase':'OFFERED'}
    return request


def observation_resume_offer(request, *, state, scope, command):
    record=_registered(request,_OBS_REQUESTS,PostEnterObservationRequest)
    if record['phase']!='OFFERED': _fail(record)
    offer=record['offer']
    validate_resume_offer(offer,state=state,scope=scope,command=command)
    return offer


def detach_post_enter_history(request, *, view, command, snapshot, frame, controller_owner):
    request_record=_registered(request,_OBS_REQUESTS,PostEnterObservationRequest)
    record=_registered(view,_VIEWS,ResumedHistoryView)
    if (request_record['phase']!='OFFERED' or record.get('observation_request') is not request
            or request_record['case'] is not record['case'] or record['phase']!='POST_SUBMIT'
            or controller_owner is not record['controller'] or not _current_command_acked(view,record)
            or not any(item() is command for item in record['dependents'])):
        _fail(record)
    validate_resume_view(view,policy=record['policy'],snapshot=snapshot,frame=frame,
        state=record['state'],scope=record['scope'],native_owner=record['native'],
        controller_owner=controller_owner,transition_owner=record['transition'])
    guard=PostEnterHistoryGuard(_SEAL)
    _OBS_GUARDS[guard]={**record,'profiles':dict(record['profiles']),
        'retired':set(record['retired']),'dependents':[],'acked':True}
    _VIEWS.pop(view)
    request_record['phase']='CONSUMED'
    _case(record['case'])['phase']='OBSERVING'
    return guard


def validate_post_enter_history(guard, *, policy, snapshot, frame, state, scope,
        native_owner, controller_owner, transition_owner):
    record=_registered(guard,_OBS_GUARDS,PostEnterHistoryGuard)
    _case(record['case'],('OBSERVING',))
    _current_binding(record,native_owner,controller_owner,transition_owner)
    if (any(record[key] is not value for key,value in (('policy',policy),('state',state),
            ('scope',scope),('native',native_owner),('controller',controller_owner),
            ('transition',transition_owner))) or record['acked'] is not True): _fail(record)
    _frame(record,snapshot,frame)
    if (record['geometry']!=(snapshot.active,snapshot.baseY,snapshot.viewportY)
            or policy.active_input_forbidden(snapshot)):
        _fail(record,'RESUME_HISTORY_LAYOUT_REJECTED')
    return _history_indices(record,policy,snapshot,post=True,current_acked=lambda: record['acked'] is True)


def close_post_enter_history(guard):
    if type(guard) is PostEnterHistoryGuard: _OBS_GUARDS.pop(guard,None)


def take_post_enter_result(request):
    if type(request) is PostEnterObservationRequest and request in _OBS_RESULTS:
        return _OBS_RESULTS.pop(request)
    record=_OBS_REQUESTS.get(request) if type(request) is PostEnterObservationRequest else None
    if record is None or record.get('result_taken'): return None
    observer=record.get('observer')
    from terminal_post_enter_observation import PostEnterObservation,_OBSERVATIONS
    evidence=_OBSERVATIONS.get(observer) if type(observer) is PostEnterObservation else None
    if evidence is None or not evidence.get('closed'): return None
    record['result_taken']=True
    return observer.summary()


def _register_resume_dependent(view, dependent):
    from terminal_context_echo import OwnedContextCommand, _COMMANDS
    from terminal_input_challenge import NonceInputChallenge, _CHALLENGES
    record = _registered(view,_VIEWS,ResumedHistoryView)
    if type(dependent) is OwnedContextCommand:
        binding = _COMMANDS.get(dependent)
    elif type(dependent) is NonceInputChallenge:
        binding = _CHALLENGES.get(dependent)
    else: binding = None
    if (binding is None or binding.get('resume_view') is not view
            or any(binding.get(key) is not record[key] for key in ('scope','native','transition','controller'))):
        _fail(record)
    if not any(item() is dependent for item in record['dependents']):
        record['dependents'].append(weakref.ref(dependent))


def _current_command_acked(view, record):
    from terminal_context_echo import _resume_submission_acked
    return any(_resume_submission_acked(item(),view) for item in record['dependents'])


def note_resume_submission(view, *, command):
    from terminal_context_echo import _resume_submission_acked
    record = _registered(view,_VIEWS,ResumedHistoryView)
    if (record['phase'] != 'BOUND' or not any(item() is command for item in record['dependents'])
            or not _resume_submission_acked(command,view)):
        _fail(record,'RESUME_HISTORY_REPLAY_REJECTED')
    record['phase'] = 'POST_SUBMIT'


def finish_resume_view(view):
    from terminal_input_challenge import NonceInputChallenge, _initial_nonce_completed
    record = _registered(view,_VIEWS,ResumedHistoryView)
    consumed=any(type(value:=item()) is NonceInputChallenge and
        _initial_nonce_completed(value,state=record['state'],scope=record['scope'],
            native_owner=record['native'],transition_owner=record['transition']) for item in record['dependents'])
    if (record['phase']!='POST_SUBMIT' or not _current_command_acked(view,record) or not consumed
            or record['native'].poll() != 0 or not record['state'].helper_reaped):
        _fail(record)
    _case(record['case'])['phase'] = 'FINISHED'
    record['phase'] = 'FINISHED'


def revoke_resume_view(view):
    record = _VIEWS.get(view) if type(view) is ResumedHistoryView else None
    if record is not None: close_offline_case(record['case'])


def resume_view_decision(view):
    record = _VIEWS.get(view) if type(view) is ResumedHistoryView else None
    return 'VALID' if record is not None and record['phase'] in ('BOUND','POST_SUBMIT','FINISHED') else 'REJECTED'
