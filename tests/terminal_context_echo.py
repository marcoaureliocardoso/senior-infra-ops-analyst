"""Private offline context-echo provenance. No IO, consent or nonce authority."""
from dataclasses import replace
import math
import re
import time
import weakref
from terminal_input_policy import TerminalInputPolicy
from terminal_state_adapter import TerminalSnapshot, MAX_CAPTURE

_SEAL=object()
_COMMANDS=weakref.WeakKeyDictionary()
_RECEIPTS=weakref.WeakKeyDictionary()
_OBSERVATIONS=weakref.WeakKeyDictionary()
_USED_SCOPES=weakref.WeakSet()
_BODY='/context'


def _now(): return time.monotonic()


def _error(reason,assessment=None):
    from terminal_input_challenge import InputProofError
    if assessment is None: return InputProofError(reason)
    return InputProofError(reason,assessment.reason,
        input_row_relation=assessment.rowRelation,input_row_cause=assessment.rowCause)


def _fail(record,reason):
    if record is not None: record['phase']='REVOKED'
    raise _error(reason)


class _Sealed:
    __slots__=('__weakref__',)
    def __new__(cls,seal=None):
        if seal is not _SEAL: raise _error('INPUT_PROBE_SCOPE_REJECTED')
        return super().__new__(cls)
    def __repr__(self): return '<'+type(self).__name__+'>'


class ContextEchoReceipt(_Sealed):
    __slots__=()


class ContextRejectionObservation(_Sealed):
    __slots__=()


def _live(record,frame=None,snapshot=None):
    from terminal_input_challenge import _context_scope_binding
    if record is None or record['phase']=='REVOKED': _fail(record,'INPUT_PROBE_REVOKED')
    now=_now()
    if (type(now) not in (int,float) or not math.isfinite(now)
            or type(record['time']) not in (int,float) or not math.isfinite(record['time'])
            or now<record['time'] or now>=record['deadline']): _fail(record,'INPUT_PROBE_DEADLINE')
    record['time']=now
    try:
        run,deadline=_context_scope_binding(record['scope'],record['state'],allow_claimed=True)
        if run is not record['run'] or deadline!=record['deadline'] or record['native'].poll() is not None:
            _fail(record,'INPUT_PROBE_REVOKED')
    except BaseException:
        record['phase']='REVOKED'; raise
    if frame is not None:
        if type(frame) is not int or not record['frame']<=frame<=MAX_CAPTURE:
            _fail(record,'INPUT_PROBE_STATE_REJECTED')
        record['frame']=frame
    if snapshot is not None:
        if type(snapshot) is not TerminalSnapshot: _fail(record,'INPUT_PROBE_STATE_REJECTED')
        if record['policy'].active_input_forbidden(snapshot): _fail(record,'INPUT_PROBE_REVOKED')


def _prefix(record,snapshot,written):
    anchor=record['anchor']
    if (snapshot.active!=anchor.buffer or snapshot.baseY!=anchor.baseY
            or snapshot.viewportY!=anchor.viewportY
            or snapshot.cursorY+snapshot.baseY-snapshot.viewportY!=anchor.row):
        _fail(record,'INPUT_PROBE_REVOKED')
    row=snapshot.rows[anchor.row]; count=snapshot.cursorX-anchor.cursorX
    if (not 0<=count<=written or row[:anchor.cursorX]!=record['row'][:anchor.cursorX]
            or any(cell.width!=1 or cell.text!=_BODY[index]
                for index,cell in enumerate(row[anchor.cursorX:anchor.cursorX+count]))
            or any(cell.width!=1 or cell.text not in ('',' ','\t','\u00a0')
                for cell in row[anchor.cursorX+count:])): _fail(record,'INPUT_PROBE_REVOKED')
    rows=list(snapshot.rows); rows[anchor.row]=record['row']
    normalized=replace(snapshot,cursorX=anchor.cursorX,rows=tuple(rows))
    if record['policy'].empty_input_anchor(normalized)!=anchor: _fail(record,'INPUT_PROBE_REVOKED')
    return count


def _history_rows(policy,snapshot):
    matches=[]
    cursor=snapshot.baseY+snapshot.cursorY-snapshot.viewportY
    for index,row in enumerate(snapshot.rows):
        if index==cursor: continue
        if (all(cell.width==1 for cell in row)
                and policy._candidate_evaluation(row)[1]=='CONTROL_COMMAND_SHAPE'
                and re.fullmatch(r'[ \t]*❯[ \t\u00a0]*/context[ \t\u00a0]*',policy._row_text(row))):
            matches.append(index)
    return matches


def _observation(policy,snapshot,assessment,rejected,excluded):
    if rejected is None or assessment.reason!='UNSUPPORTED_ROW': return None
    value=ContextRejectionObservation(_SEAL)
    _OBSERVATIONS[value]=(policy,snapshot,assessment,rejected,excluded)
    return value


class OwnedContextCommand(_Sealed):
    __slots__=()

    @property
    def phase(self):
        record=_COMMANDS.get(self)
        if record is None: raise _error('INPUT_PROBE_SCOPE_REJECTED')
        return record['phase']

    def invalidate(self,reason):
        record=_COMMANDS.get(self)
        if record is not None: record['phase']='REVOKED'

    def type_bytes(self,snapshot,frame):
        record=_COMMANDS.get(self); _live(record,frame,snapshot)
        if record['phase']!='ELIGIBLE': _fail(record,'INPUT_PROBE_STATE_REJECTED')
        _prefix(record,snapshot,0)
        record['phase']='EDIT_PENDING'; record['write_frame']=frame
        return _BODY.encode('ascii')

    def check_edit(self,snapshot,frame,written):
        record=_COMMANDS.get(self); _live(record,frame,snapshot)
        if (record['phase'] not in ('EDIT_PENDING','COMMAND_ECHO_MATCHED') or type(written) is not int
                or not record['written']<=written<=len(_BODY)): _fail(record,'INPUT_PROBE_STATE_REJECTED')
        _prefix(record,snapshot,written); record['written']=written

    def observe(self,snapshot,frame):
        record=_COMMANDS.get(self); _live(record,frame,snapshot)
        if record['phase'] in ('EDIT_PENDING','COMMAND_ECHO_MATCHED'):
            if frame<=record['write_frame']: _fail(record,'INPUT_PROBE_STATE_REJECTED')
            count=_prefix(record,snapshot,record['written'])
            if count<record['progress']: _fail(record,'INPUT_PROBE_REVOKED')
            record['progress']=count
            record['phase']='COMMAND_ECHO_MATCHED' if count==len(_BODY) else 'EDIT_PENDING'
        elif record['phase']=='SUBMIT_PENDING':
            if _prefix(record,snapshot,record['written'])!=len(_BODY): _fail(record,'INPUT_PROBE_REVOKED')
        elif record['phase'] not in ('CONTEXT_PENDING','RECEIPT_READY'):
            _fail(record,'INPUT_PROBE_STATE_REJECTED')
        return record['phase']

    def submit_bytes(self,snapshot,frame):
        record=_COMMANDS.get(self); _live(record,frame,snapshot)
        if record['phase']!='COMMAND_ECHO_MATCHED' or _prefix(record,snapshot,record['written'])!=len(_BODY):
            _fail(record,'INPUT_PROBE_STATE_REJECTED')
        record['policy'].mark_transition(snapshot)
        record['submit_signature']=record['policy']._context_signature(snapshot)
        record['phase']='SUBMIT_PENDING'; record['submit_frame']=frame
        return b'\r'

    def submission_written(self,count):
        record=_COMMANDS.get(self); _live(record)
        if record['phase']!='SUBMIT_PENDING' or type(count) is not int or count!=1:
            _fail(record,'INPUT_PROBE_STATE_REJECTED')
        record['phase']='CONTEXT_PENDING'

    def bind_history(self,snapshot,frame):
        record=_COMMANDS.get(self); _live(record,frame,snapshot)
        if (record['phase']!='CONTEXT_PENDING' or frame<=record['submit_frame']
                or record['policy']._context_signature(snapshot)==record['submit_signature']
                or record['policy'].context_percent(snapshot) is None): _fail(record,'INPUT_PROBE_STATE_REJECTED')
        matches=_history_rows(record['policy'],snapshot)
        if len(matches)>1: _fail(record,'INPUT_PROBE_REVOKED')
        excluded=matches[0] if matches else None
        assessment,rejected=record['policy']._empty_input_assessment(snapshot,excluded)
        if assessment.anchor is None:
            record['phase']='REVOKED'
            error=_error('INPUT_PROBE_INELIGIBLE',assessment)
            if excluded is not None: attach_context_rejection(error,
                _observation(record['policy'],snapshot,assessment,rejected,excluded))
            raise error
        record['phase']='RECEIPT_READY'
        if excluded is None: return None
        value=ContextEchoReceipt(_SEAL)
        _RECEIPTS[value]=(self,excluded,snapshot.rows[excluded],assessment.anchor)
        return value


def begin_context_command(scope,state,native_owner,transition_owner,policy,baseline,frame):
    from terminal_input_challenge import _context_scope_binding
    run,deadline=_context_scope_binding(scope,state)
    if (scope in _USED_SCOPES or type(policy) is not TerminalInputPolicy or type(transition_owner) is not object
            or not callable(getattr(native_owner,'poll',None)) or type(frame) is not int
            or not 0<=frame<=MAX_CAPTURE or type(baseline) is not TerminalSnapshot):
        raise _error('INPUT_PROBE_SCOPE_REJECTED')
    _USED_SCOPES.add(scope)
    assessment=policy.empty_input_assessment(baseline)
    if assessment.anchor is None: raise _error('INPUT_PROBE_INELIGIBLE',assessment)
    value=OwnedContextCommand(_SEAL)
    _COMMANDS[value]={'scope':scope,'state':state,'native':native_owner,'transition':transition_owner,
        'policy':policy,'run':run,'deadline':deadline,'time':_now(),'frame':frame,'phase':'ELIGIBLE',
        'anchor':assessment.anchor,'row':baseline.rows[assessment.anchor.row],'written':0,'progress':0}
    _live(_COMMANDS[value],frame,baseline)
    return value


def validate_context_history(receipt,policy,snapshot,*,scope,state,native_owner,transition_owner,frame):
    registered=_RECEIPTS.get(receipt) if type(receipt) is ContextEchoReceipt else None
    if registered is None: raise _error('INPUT_PROBE_SCOPE_REJECTED')
    command,index,row,anchor=registered; record=_COMMANDS.get(command)
    _live(record,frame,snapshot)
    if (record['phase']!='RECEIPT_READY' or policy is not record['policy'] or scope is not record['scope']
            or state is not record['state'] or native_owner is not record['native']
            or transition_owner is not record['transition'] or snapshot.active!=anchor.buffer
            or snapshot.baseY!=anchor.baseY or snapshot.viewportY!=anchor.viewportY
            or snapshot.cursorY+snapshot.baseY-snapshot.viewportY!=anchor.row
            or snapshot.rows[index]!=row or _history_rows(policy,snapshot)!=[index]):
        _fail(record,'INPUT_PROBE_REVOKED')
    return index


def assess_context_input(policy,snapshot,*,receipt,scope,state,native_owner,transition_owner,frame):
    excluded=None
    if receipt is not None:
        excluded=validate_context_history(receipt,policy,snapshot,scope=scope,state=state,
            native_owner=native_owner,transition_owner=transition_owner,frame=frame)
    assessment,rejected=policy._empty_input_assessment(snapshot,excluded)
    observation=_observation(policy,snapshot,assessment,rejected,excluded) if receipt is not None else None
    if receipt is not None and assessment.anchor is None:
        _RECEIPTS[receipt][0].invalidate('INPUT_PROBE_REVOKED')
    return assessment,observation


def attach_context_rejection(error,observation):
    if observation is not None: error._context_rejection=observation
    return error


def _invalidate_context_receipt(receipt):
    registered=_RECEIPTS.get(receipt) if type(receipt) is ContextEchoReceipt else None
    if registered is not None: registered[0].invalidate('INPUT_PROBE_REVOKED')


def _context_rejection_policy(error):
    """Frozen pure evaluator identity only; never validates live authority."""
    value=getattr(error,'_context_rejection',None)
    registered=_OBSERVATIONS.get(value) if type(value) is ContextRejectionObservation else None
    return registered[0] if registered is not None else None


def context_rejection_projection(error,snapshot,policy):
    if not hasattr(error,'_context_rejection'): return False,None
    value=error._context_rejection
    registered=_OBSERVATIONS.get(value) if type(value) is ContextRejectionObservation else None
    if registered is None: return True,None
    original_policy,original,assessment,index,excluded=registered
    if (policy is not original_policy or snapshot is not original or error.reason!='INPUT_PROBE_INELIGIBLE'
            or error.input_eligibility!=assessment.reason or error.input_row_relation!=assessment.rowRelation
            or error.input_row_cause!=assessment.rowCause): return True,None
    current,rejected=policy._empty_input_assessment(snapshot,excluded)
    return (True,index) if current==assessment and rejected==index else (True,None)
