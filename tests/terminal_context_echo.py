"""Private offline context-echo provenance. No IO, consent or nonce authority."""
from dataclasses import replace
import math
import re
import time
import weakref
from terminal_input_policy import TerminalInputPolicy, EmptyInputAssessment, InputAnchor
from terminal_state_adapter import TerminalSnapshot, MAX_CAPTURE
from terminal_context_diagnostics import ContextFailureJournal, valid_normalized_input_failure
from terminal_cancellation import TerminalCancelled

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


def _diagnostic(record,method,*args,**kwargs):
    journal=record.get('journal') if record is not None else None
    if type(journal) is not ContextFailureJournal: return
    try: getattr(journal,method)(*args,**kwargs)
    except Exception:
        # Observation loss cannot change the original operational failure or phase.
        try: journal.finish()
        except Exception: pass


def _phase(record,phase):
    record['phase']=phase
    _diagnostic(record,'set_phase',phase)


def _scope_rejection(record,error):
    from terminal_input_challenge import InputProofError
    if isinstance(error,TerminalCancelled): _diagnostic(record,'freeze',error,'CANCELLATION')
    elif isinstance(error,InputProofError): _diagnostic(record,'freeze',error,'SCOPE_BINDING')


def _fail(record,reason,check=None,*,normalized_input_failure=None):
    error=_error(reason)
    if check is not None: _diagnostic(record,'freeze',error,check,normalized_input_failure=normalized_input_failure)
    if record is not None: record['phase']='REVOKED'
    raise error


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
            or now<record['time'] or now>=record['deadline']): _fail(record,'INPUT_PROBE_DEADLINE','DEADLINE')
    record['time']=now
    try:
        run,deadline=_context_scope_binding(record['scope'],record['state'],allow_claimed=True)
        if run is not record['run'] or deadline!=record['deadline']:
            _fail(record,'INPUT_PROBE_REVOKED','SCOPE_BINDING')
        if record['native'].poll() is not None: _fail(record,'INPUT_PROBE_REVOKED','NATIVE_LIFETIME')
    except BaseException as error:
        _scope_rejection(record,error)
        record['phase']='REVOKED'; raise
    if frame is not None:
        if type(frame) is not int or not record['frame']<=frame<=MAX_CAPTURE:
            _fail(record,'INPUT_PROBE_STATE_REJECTED','FRAME_STATE')
        record['frame']=frame
    if snapshot is not None:
        if type(snapshot) is not TerminalSnapshot: _fail(record,'INPUT_PROBE_STATE_REJECTED','FRAME_STATE')
        if record['policy'].active_input_forbidden(snapshot): _fail(record,'INPUT_PROBE_REVOKED','FORBIDDEN_UI')


def _normalized_failure_detail(assessment,expected_anchor):
    if type(assessment) is not EmptyInputAssessment or type(expected_anchor) is not InputAnchor: return None
    if assessment.anchor is not None:
        return ({'reason':'ANCHOR_CHANGED'} if type(assessment.anchor) is InputAnchor
            and assessment.anchor!=expected_anchor else None)
    detail={'reason':assessment.reason}
    if assessment.rowRelation is not None: detail['rowRelation']=assessment.rowRelation
    if assessment.rowCause is not None: detail['rowCause']=assessment.rowCause
    return detail if valid_normalized_input_failure(detail) else None


def _prefix(record,snapshot,written):
    anchor=record['anchor']
    if (snapshot.active!=anchor.buffer or snapshot.baseY!=anchor.baseY
            or snapshot.viewportY!=anchor.viewportY
            or snapshot.cursorY+snapshot.baseY-snapshot.viewportY!=anchor.row):
        _fail(record,'INPUT_PROBE_REVOKED','ANCHOR_GEOMETRY')
    row=snapshot.rows[anchor.row]; count=snapshot.cursorX-anchor.cursorX
    if not 0<=count<=written: _fail(record,'INPUT_PROBE_REVOKED','CURSOR_PROGRESS')
    if row[:anchor.cursorX]!=record['row'][:anchor.cursorX]: _fail(record,'INPUT_PROBE_REVOKED','PREFIX_CELLS')
    if any(cell.width!=1 or cell.text!=_BODY[index]
            for index,cell in enumerate(row[anchor.cursorX:anchor.cursorX+count])):
        _fail(record,'INPUT_PROBE_REVOKED','COMMAND_CELLS')
    if any(cell.width!=1 or cell.text not in ('',' ','\t','\u00a0') for cell in row[anchor.cursorX+count:]):
        _fail(record,'INPUT_PROBE_REVOKED','TRAILING_CELLS')
    rows=list(snapshot.rows); rows[anchor.row]=record['row']
    normalized=replace(snapshot,cursorX=anchor.cursorX,rows=tuple(rows))
    assessment=record['policy'].empty_input_assessment(normalized)
    if assessment.anchor!=anchor:
        try: detail=_normalized_failure_detail(assessment,anchor)
        except Exception: detail=None
        _fail(record,'INPUT_PROBE_REVOKED','NORMALIZED_ELIGIBILITY',normalized_input_failure=detail)
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
        if record['phase']!='ELIGIBLE': _fail(record,'INPUT_PROBE_STATE_REJECTED','PHASE_STATE')
        _prefix(record,snapshot,0)
        _phase(record,'EDIT_PENDING'); record['write_frame']=frame
        return _BODY.encode('ascii')

    def check_edit(self,snapshot,frame,written):
        record=_COMMANDS.get(self); _live(record,frame,snapshot)
        if record['phase'] not in ('EDIT_PENDING','COMMAND_ECHO_MATCHED'):
            _fail(record,'INPUT_PROBE_STATE_REJECTED','PHASE_STATE')
        if type(written) is not int or not record['written']<=written<=len(_BODY):
            _fail(record,'INPUT_PROBE_STATE_REJECTED','WRITE_COUNT')
        _prefix(record,snapshot,written); record['written']=written

    def observe(self,snapshot,frame):
        record=_COMMANDS.get(self); _live(record,frame,snapshot)
        if record['phase'] in ('EDIT_PENDING','COMMAND_ECHO_MATCHED'):
            if frame<=record['write_frame']: _fail(record,'INPUT_PROBE_STATE_REJECTED','FRAME_STATE')
            count=_prefix(record,snapshot,record['written'])
            if count<record['progress']: _fail(record,'INPUT_PROBE_REVOKED','ECHO_REGRESSION')
            record['progress']=count
            _phase(record,'COMMAND_ECHO_MATCHED' if count==len(_BODY) else 'EDIT_PENDING')
        elif record['phase']=='SUBMIT_PENDING':
            if _prefix(record,snapshot,record['written'])!=len(_BODY):
                _fail(record,'INPUT_PROBE_REVOKED','INCOMPLETE_ECHO')
            # Every guarded observation is still pre-Enter until its actual write acknowledgement.
            # Keep the last numeric/frame boundary, never a post-Enter redraw.
            record['policy'].mark_transition(snapshot)
            record['submit_signature']=record['policy']._context_signature(snapshot)
            record['submit_frame']=frame
        elif record['phase'] not in ('CONTEXT_PENDING','RECEIPT_READY'):
            _fail(record,'INPUT_PROBE_STATE_REJECTED','PHASE_STATE')
        return record['phase']

    def submit_bytes(self,snapshot,frame):
        record=_COMMANDS.get(self); _live(record,frame,snapshot)
        if record['phase']!='COMMAND_ECHO_MATCHED': _fail(record,'INPUT_PROBE_STATE_REJECTED','PHASE_STATE')
        if _prefix(record,snapshot,record['written'])!=len(_BODY):
            _fail(record,'INPUT_PROBE_STATE_REJECTED','INCOMPLETE_ECHO')
        record['policy'].mark_transition(snapshot)
        record['submit_signature']=record['policy']._context_signature(snapshot)
        _phase(record,'SUBMIT_PENDING'); record['submit_frame']=frame
        return b'\r'

    def submission_written(self,count):
        record=_COMMANDS.get(self); _live(record)
        if record['phase']!='SUBMIT_PENDING': _fail(record,'INPUT_PROBE_STATE_REJECTED','PHASE_STATE')
        if type(count) is not int or count!=1: _fail(record,'INPUT_PROBE_STATE_REJECTED','WRITE_COUNT')
        _phase(record,'CONTEXT_PENDING')

    def bind_history(self,snapshot,frame):
        record=_COMMANDS.get(self); _live(record,frame,snapshot)
        if record['phase']!='CONTEXT_PENDING': _fail(record,'INPUT_PROBE_STATE_REJECTED','PHASE_STATE')
        if (frame<=record['submit_frame']
                or record['policy']._context_signature(snapshot)==record['submit_signature']
                or record['policy'].context_percent(snapshot) is None):
            _fail(record,'INPUT_PROBE_STATE_REJECTED','FRESH_CONTEXT')
        matches=_history_rows(record['policy'],snapshot)
        if len(matches)>1: _fail(record,'INPUT_PROBE_REVOKED','HISTORY_AMBIGUITY')
        excluded=matches[0] if matches else None
        assessment,rejected=record['policy']._empty_input_assessment(snapshot,excluded)
        if assessment.anchor is None:
            error=_error('INPUT_PROBE_INELIGIBLE',assessment)
            _diagnostic(record,'freeze',error,'HISTORY_ELIGIBILITY')
            record['phase']='REVOKED'
            if excluded is not None: attach_context_rejection(error,
                _observation(record['policy'],snapshot,assessment,rejected,excluded))
            raise error
        _phase(record,'RECEIPT_READY')
        # Later receipt/nonce lifetime failures are outside this observation window.
        record['journal']=None
        if excluded is None: return None
        value=ContextEchoReceipt(_SEAL)
        _RECEIPTS[value]=(self,excluded,snapshot.rows[excluded],assessment.anchor)
        return value


def begin_context_command(scope,state,native_owner,transition_owner,policy,baseline,frame,*,_diagnostic_journal=None):
    from terminal_input_challenge import _context_scope_binding
    record={'journal':_diagnostic_journal,'phase':'BASELINE'}
    try: run,deadline=_context_scope_binding(scope,state)
    except BaseException as error:
        _scope_rejection(record,error); raise
    _diagnostic(record,'bind_run',run)
    if (scope in _USED_SCOPES or type(policy) is not TerminalInputPolicy or type(transition_owner) is not object
            or not callable(getattr(native_owner,'poll',None)) or type(frame) is not int
            or not 0<=frame<=MAX_CAPTURE or type(baseline) is not TerminalSnapshot):
        _fail(record,'INPUT_PROBE_SCOPE_REJECTED','SCOPE_BINDING')
    _USED_SCOPES.add(scope)
    assessment=policy.empty_input_assessment(baseline)
    if assessment.anchor is None:
        error=_error('INPUT_PROBE_INELIGIBLE',assessment)
        _diagnostic(record,'freeze',error,'BASELINE_ELIGIBILITY')
        raise error
    value=OwnedContextCommand(_SEAL)
    _COMMANDS[value]={'scope':scope,'state':state,'native':native_owner,'transition':transition_owner,
        'policy':policy,'run':run,'deadline':deadline,'time':_now(),'frame':frame,'phase':'ELIGIBLE',
        'anchor':assessment.anchor,'row':baseline.rows[assessment.anchor.row],'written':0,'progress':0,
        'journal':_diagnostic_journal}
    _diagnostic(_COMMANDS[value],'set_phase','ELIGIBLE')
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
