"""Private content-free observation. Never acceptance, input or proof authority."""
from contextlib import contextmanager
from contextvars import ContextVar
import weakref

_SEAL=object()
_SESSIONS=weakref.WeakKeyDictionary()
_CURRENT=ContextVar('nonce_history_observation',default=None)
_FAILURES=weakref.WeakKeyDictionary()
_CAPTURING=weakref.WeakSet()
_ENUMS={
    'site':frozenset(('HISTORY','CANDIDATE_IDENTITY','CANDIDATE_DESTINATION','COMPOSITION','OTHER')),
    'noncePhase':frozenset(('NONE','ELIGIBLE','ECHO_PENDING','ECHO_MATCHED','CLEAR_PENDING','PROVEN','CONSUMED','REVOKED','UNKNOWN')),
    'clearWrite':frozenset(('NOT_SENT','ACKED','UNKNOWN')),
    'clearEvidence':frozenset(('ABSENT','PRESENT','UNKNOWN')),
    'sdkBaseline':frozenset(('ABSENT','PRESENT','UNKNOWN')),
    'placement':frozenset(('SAME_SLOT','OTHER_SLOT','NO_MATCH','MULTIPLE','UNKNOWN')),
    'profile':frozenset(('EXACT','DIFFERENT','UNAVAILABLE')),
}


def valid_nonce_history_context(value):
    return (type(value) is dict and value.keys()==_ENUMS.keys()
        and all(type(value[key]) is str and value[key] in values for key,values in _ENUMS.items()))


class _NonceHistorySession:
    __slots__=('__weakref__',)
    def __new__(cls,seal=None):
        if seal is not _SEAL: raise TypeError('private observation session')
        return super().__new__(cls)
    def __repr__(self): return '<NonceHistorySession>'
    def __reduce_ex__(self,_protocol): raise TypeError('private observation session')


def _bound_view(view,bindings):
    from terminal_resume_history import ResumedHistoryView,_VIEWS,_CASES
    from terminal_input_challenge import _SCOPES,OfflineProbeScope
    record=_VIEWS.get(view) if type(view) is ResumedHistoryView else None
    scope=bindings['scope']
    scoped=_SCOPES.get(scope) if type(scope) is OfflineProbeScope else None
    if (record is None or scoped is None or record.get('observation_request') is not None
            or record.get('phase') not in ('BOUND','POST_SUBMIT')
            or _CASES.get(record['case']) is None or scoped['terminal'] is not bindings['state']
            or scoped['run'] is not record['run'] or scoped['deadline']!=record['deadline']): return None
    for key,arg in (('state','state'),('scope','scope'),('native','native_owner'),
            ('controller','controller_owner'),('transition','transition_owner')):
        if record.get(key) is not bindings[arg]: return None
    return record


def _create_nonce_history_session(view,*,state,scope,native_owner,controller_owner,transition_owner,probe=None):
    try:
        bindings=dict(state=state,scope=scope,native_owner=native_owner,
            controller_owner=controller_owner,transition_owner=transition_owner)
        if _bound_view(view,bindings) is None: return None
        if probe is not None:
            from terminal_input_challenge import _read_nonce_history_status
            if _read_nonce_history_status(probe,view=view,**bindings) is None: return None
        session=_NonceHistorySession(_SEAL)
        _SESSIONS[session]=dict(view=view,bindings=bindings,probe=weakref.ref(probe) if probe is not None else None,
            clearWrite='UNKNOWN' if probe is not None else 'NOT_SENT',attempted=False)
        return session
    except Exception: return None


def _session_record(session):
    return _SESSIONS.get(session) if type(session) is _NonceHistorySession else None


def _status(record,probe):
    from terminal_input_challenge import _read_nonce_history_status
    if probe is None:
        return ('NONE','ABSENT') if record['probe'] is None else None
    observed=_read_nonce_history_status(probe,view=record['view'],**record['bindings'])
    if observed is None: return None
    bound=record['probe']
    if bound is None: record['probe']=weakref.ref(probe)
    elif bound() is not probe: return None
    return observed


def _capture_scope(session,probe,snapshot,frame):
    from terminal_state_adapter import TerminalSnapshot,MAX_CAPTURE
    record=_session_record(session)
    if (record is None or type(snapshot) is not TerminalSnapshot or type(frame) is not int
            or not 0<=frame<=MAX_CAPTURE): return None
    view_record=_bound_view(record['view'],record['bindings'])
    if view_record is None: return None
    status=_status(record,probe)
    return dict(snapshot=snapshot,frame=frame,view=record['view'],view_record=view_record,
        identity=view_record['sdk_identity'],position=view_record['sdk_position'],
        caseKind=__import__('terminal_resume_history')._CASES[view_record['case']]['kind'],
        noncePhase=status[0] if status is not None else 'UNKNOWN',
        clearEvidence=status[1] if status is not None else 'UNKNOWN',
        clearWrite=record['clearWrite'] if status is not None else 'UNKNOWN')


@contextmanager
def _nonce_history_scope(session,*,probe,snapshot,frame):
    captured=None
    try: captured=_capture_scope(session,probe,snapshot,frame)
    except Exception: pass
    token=_CURRENT.set(captured)
    try:
        yield
    finally:
        _CURRENT.reset(token)
        if captured is not None: captured.clear()


def _note_nonce_clear_attempt(session,*,probe):
    try:
        record=_session_record(session)
        if record is not None and probe is not None and _status(record,probe) is not None:
            record.update(clearWrite='UNKNOWN',attempted=True)
    except Exception: pass


def _note_nonce_clear_ack(session,*,probe,count):
    try:
        record=_session_record(session)
        if (record is not None and probe is not None and _status(record,probe) is not None
                and record['attempted'] and type(count) is int and count==1):
            record.update(clearWrite='ACKED',attempted=False)
    except Exception: pass


def _close_nonce_history_session(session):
    try:
        record=_SESSIONS.pop(session,None) if type(session) is _NonceHistorySession else None
        if record is not None: record.clear()
    except Exception: pass


def _freeze_nonce_history_failure(error,*,record,snapshot,frame,site):
    capturing=False
    try:
        from terminal_resume_history import resume_failure_diagnostic,match_history_row,_SDK_RELOCATIONS
        captured=_CURRENT.get()
        base=resume_failure_diagnostic(error)
        if (captured is None or base is None or error in _FAILURES or error in _CAPTURING
                or captured['snapshot'] is not snapshot or type(frame) is not int
                or captured['frame']!=frame or base['caseKind']!=captured['caseKind']
                or type(site) is not str or site not in _ENUMS['site']): return
        if record is not captured['view_record']:
            # Only the actual private candidate can supply a projected record.
            if not any(bound['projected'] is record and bound['view']() is captured['view']
                    and bound['snapshot']() is snapshot and bound['frame']==frame
                    for bound in _SDK_RELOCATIONS.values()): return
        if len(snapshot.rows)>40: return
        _CAPTURING.add(error); capturing=True
        kind='SDK_TEXT' if captured['caseKind']=='text-turn' else 'SDK_SKILL'
        cursor=snapshot.baseY+snapshot.cursorY-snapshot.viewportY
        profiles=[(index,profile) for index,row in enumerate(snapshot.rows) if index!=cursor
            and (profile:=match_history_row(row,kind)) is not None]
        baseline=captured['identity']; position=captured['position']
        placement='UNKNOWN'; profile='UNAVAILABLE'
        if type(position) is int:
            if not profiles: placement='NO_MATCH'
            elif len(profiles)>1: placement='MULTIPLE'
            else: placement='SAME_SLOT' if profiles[0][0]==position else 'OTHER_SLOT'
        if baseline is not None and len(profiles)==1:
            profile='EXACT' if profiles[0][1]==baseline[1] else 'DIFFERENT'
        value=dict(site=site,noncePhase=captured['noncePhase'],clearWrite=captured['clearWrite'],
            clearEvidence=captured['clearEvidence'],sdkBaseline='PRESENT' if baseline is not None else 'ABSENT',
            placement=placement,profile=profile)
        if (_CURRENT.get() is captured and error not in _FAILURES and valid_nonce_history_context(value)):
            _FAILURES[error]=tuple(value.items())
    except Exception: pass
    finally:
        if capturing: _CAPTURING.discard(error)


def nonce_history_failure_diagnostic(error):
    try:
        from terminal_resume_history import resume_failure_diagnostic
        if resume_failure_diagnostic(error) is None: return None
        frozen=_FAILURES.get(error)
        value=dict(frozen) if frozen is not None else None
        return value if valid_nonce_history_context(value) else None
    except Exception: return None
