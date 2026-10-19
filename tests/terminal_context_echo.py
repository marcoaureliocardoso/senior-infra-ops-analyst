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
from terminal_context_sample import sample_context

_SEAL=object()
_COMMANDS=weakref.WeakKeyDictionary()
_RECEIPTS=weakref.WeakKeyDictionary()
_OBSERVATIONS=weakref.WeakKeyDictionary()
_USED_SCOPES=weakref.WeakSet()
_EDIT_ROWS=weakref.WeakKeyDictionary()
_MENU_BINDINGS=weakref.WeakKeyDictionary()
_DISPLAY_TRACKERS=weakref.WeakKeyDictionary()
_DISPLAYS=weakref.WeakKeyDictionary()
_BODY='/context'


def _now(): return time.monotonic()


def _initial_context_facts(command, *, state, scope, native_owner, transition_owner):
    """Completed facts only: the original live validator must reject an exited owner."""
    from terminal_input_challenge import _context_scope_binding
    record=_COMMANDS.get(command) if type(command) is OwnedContextCommand else None
    if record is None: raise _error('INPUT_PROBE_SCOPE_REJECTED')
    run,deadline=_context_scope_binding(scope,state,allow_claimed=True)
    if (any(record[key] is not value for key,value in (('state',state),('scope',scope),
            ('native',native_owner),('transition',transition_owner),('run',run)))
            or record['deadline']!=deadline or record['phase']!='RECEIPT_READY'
            or record['written']!=8 or record['progress']!=8 or 'submit_frame' not in record
            or native_owner.poll()!=0):
        raise _error('INPUT_PROBE_SCOPE_REJECTED')
    return 8,1


def _error(reason,assessment=None):
    from terminal_input_challenge import InputProofError
    if assessment is None: return InputProofError(reason)
    return InputProofError(reason,assessment.reason,
        input_row_relation=assessment.rowRelation,input_row_cause=assessment.rowCause)


def _revoke_record_view(record):
    if record is not None and record.get('resume_view') is not None:
        from terminal_resume_history import revoke_resume_view
        revoke_resume_view(record['resume_view'])


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


def _fail(record,reason,check=None,*,normalized_input_failure=None,edit_snapshot=None,edit_assessment=None,rejected_index=None):
    error=_error(reason)
    if check is not None: _diagnostic(record,'freeze',error,check,normalized_input_failure=normalized_input_failure)
    observer=record.pop('edit_observer',None) if record is not None else None
    if observer is not None:
        try:
            observer.freeze(error,check,command_record=record,snapshot=edit_snapshot,
                assessment=edit_assessment,rejected_index=rejected_index)
        except Exception:
            try: observer.finish()
            except Exception: pass
    if record is not None:
        record['phase']='REVOKED'
        _release_display(record)
        _release_command_menu(record)
        _revoke_record_view(record)
    raise error


def _release_command_menu(record: dict) -> None:
    owner=next((key for key,value in _COMMANDS.items() if value is record),None)
    if owner is None: return
    _MENU_BINDINGS.pop(owner,None)
    record.pop('_menu_origin',None); record.pop('_menu_selection',None)


def _correlated_menu_row(record: dict,snapshot: TerminalSnapshot) -> int | None:
    """A shape is usable only under this original live pre-Enter command."""
    owner=next((key for key,value in _COMMANDS.items() if value is record),None)
    if owner is None: raise _error('INPUT_PROBE_SCOPE_REJECTED')
    stored=_MENU_BINDINGS.get(owner)
    origin=record.get('_menu_origin'); selection=record.get('_menu_selection')
    if (stored is None or origin is not stored[0] or selection is not stored[1]
            or type(origin) is not tuple or len(origin)!=10 or origin[0]() is not owner):
        _fail(record,'INPUT_PROBE_REVOKED','NORMALIZED_ELIGIBILITY')
    _,baseline,scope,state,native,transition,run,deadline,anchor,baseline_frame=origin
    if (any(record.get(key) is not value for key,value in (
                ('scope',scope),('state',state),('native',native),('transition',transition),('run',run),('anchor',anchor)))
            or record.get('deadline')!=deadline or record.get('row') is not baseline.rows[anchor.row]):
        _fail(record,'INPUT_PROBE_REVOKED','NORMALIZED_ELIGIBILITY')
    eligible=(record['phase'] in ('EDIT_PENDING','COMMAND_ECHO_MATCHED','SUBMIT_PENDING')
        and record['written']==8 and snapshot.cursorX-anchor.cursorX==8
        and record['frame']>record['write_frame'] and record['frame']>baseline_frame)
    if not eligible:
        if selection is not None: _fail(record,'INPUT_PROBE_REVOKED','NORMALIZED_ELIGIBILITY')
        return None
    candidates=[index for index,row in enumerate(snapshot.rows)
        if index!=anchor.row and record['policy']._context_completion_row(row)]
    if selection is None:
        if len(candidates)!=1: return None
        index=candidates[0]
        # The original strict baseline is the only source of baseline evidence.
        if any('❯' in cell.text for cell in baseline.rows[index]):
            _fail(record,'INPUT_PROBE_REVOKED','NORMALIZED_ELIGIBILITY')
        selection=(index,snapshot.rows[index],snapshot,record['frame'])
        record['_menu_selection']=selection; _MENU_BINDINGS[owner]=(origin,selection)
    index,row,first,first_frame=selection
    if (candidates!=[index] or snapshot.rows[index]!=row or first.rows[index] is not row
            or record['frame']<first_frame
            or (snapshot.active,snapshot.baseY,snapshot.viewportY)!=(first.active,first.baseY,first.viewportY)):
        _fail(record,'INPUT_PROBE_REVOKED','NORMALIZED_ELIGIBILITY')
    return index


def _preenter_context_signature(record: dict,snapshot: TerminalSnapshot) -> tuple[str, ...]:
    # Only called after the same snapshot passed _prefix; no acceptance or IO.
    index=_correlated_menu_row(record,snapshot)
    rows=tuple(row for number,row in enumerate(snapshot.rows) if number!=index)
    return record['policy']._context_signature_rows(rows)


class _Sealed:
    __slots__=('__weakref__',)
    def __new__(cls,seal=None):
        if seal is not _SEAL: raise _error('INPUT_PROBE_SCOPE_REJECTED')
        return super().__new__(cls)
    def __repr__(self): return '<'+type(self).__name__+'>'


class ContextEchoReceipt(_Sealed):
    __slots__=()


class ContextDisplayWitness(_Sealed):
    __slots__=()


def _release_display(record):
    witness=record.pop('display_witness',None)
    if type(witness) is ContextDisplayWitness: _DISPLAYS.pop(witness,None)
    command=next((key for key,value in _COMMANDS.items() if value is record),None)
    tracker=_DISPLAY_TRACKERS.pop(command,None) if command is not None else None
    if tracker is not None:
        from terminal_resume_history import revoke_resume_view
        revoke_resume_view(tracker['owners'][6])


def _display_owners(record):
    return tuple(record.get(key) for key in ('scope','state','native','transition',
        'policy','run','resume_view','controller'))


def _display_tracker(command,record):
    tracker=_DISPLAY_TRACKERS.get(command)
    if (tracker is None or any(a is not b for a,b in zip(tracker['owners'],_display_owners(record)))
            or tracker['deadline']!=record['deadline']):
        _fail(record,'INPUT_PROBE_REVOKED','DISPLAY_WITNESS_UNPROVEN')
    return tracker


def _observe_resumed_display(command,snapshot,frame):
    record=_COMMANDS.get(command); _live(record,frame,snapshot)
    tracker=_display_tracker(command,record)
    sample=sample_context(snapshot)
    if record['phase'] in ('ELIGIBLE','EDIT_PENDING','COMMAND_ECHO_MATCHED','SUBMIT_PENDING'):
        tracker['baseline']=sample.numbers if sample is not None else None
        tracker['inventory'].update(_history_rows(record['policy'],snapshot))
        # A completion's cell position can never become the new committed row.
        tracker['inventory'].update(index for index,row in enumerate(snapshot.rows)
            if record['policy']._context_completion_row(row))
        return
    if record['phase'] not in ('CONTEXT_PENDING','RECEIPT_READY'):
        _fail(record,'INPUT_PROBE_STATE_REJECTED','PHASE_STATE')
    if frame<=record['submit_frame']: return
    if tracker['phase']=='AWAIT_DISPLAY' and sample is not None:
        numbers=sample.numbers
        if tracker['distinct'] is not None and numbers!=tracker['distinct']:
            _fail(record,'INPUT_PROBE_STATE_REJECTED','CONTEXT_SAMPLE_UNSTABLE')
        if numbers!=tracker['baseline']: tracker['distinct']=numbers
    if tracker['phase'] in ('CANDIDATE','CONSUMED'):
        _validate_resumed_display(command,snapshot,frame)


def _validate_resumed_display(command,snapshot,frame):
    record=_COMMANDS.get(command); _live(record,frame,snapshot)
    tracker=_display_tracker(command,record)
    witness=record.get('display_witness')
    bound=_DISPLAYS.get(witness) if type(witness) is ContextDisplayWitness else None
    if (bound is None or bound['command']() is not command or bound['tracker'] is not tracker
            or tracker['phase'] not in ('CANDIDATE','CONSUMED')
            or record.get('submit_frame')!=bound['submit_frame']
            or frame<bound['frame']):
        _fail(record,'INPUT_PROBE_REVOKED','DISPLAY_WITNESS_UNPROVEN')
    old=_resume_indices(record,snapshot,frame)
    if (sample_context(snapshot)!=bound['sample'] or snapshot.rows[bound['index']]!=bound['row']
            or _history_rows(record['policy'],snapshot,_excluded_rows=old)!=[bound['index']]
            or bound['index'] in old):
        _fail(record,'INPUT_PROBE_REVOKED','CONTEXT_SAMPLE_UNSTABLE')


def _assess_resumed_context(command,snapshot,frame):
    record=_COMMANDS.get(command); _live(record,frame,snapshot)
    if record['phase']!='CONTEXT_PENDING': _fail(record,'INPUT_PROBE_STATE_REJECTED','PHASE_STATE')
    _observe_resumed_display(command,snapshot,frame)
    if frame<=record['submit_frame']: return None
    tracker=_display_tracker(command,record)
    old=_resume_indices(record,snapshot,frame)
    matches=_history_rows(record['policy'],snapshot,_excluded_rows=old)
    if len(matches)>1: _fail(record,'INPUT_PROBE_REVOKED','DISPLAY_WITNESS_AMBIGUOUS')
    index=matches[0] if matches else None
    if index is not None and index in tracker['inventory']:
        _fail(record,'INPUT_PROBE_REVOKED','DISPLAY_WITNESS_AMBIGUOUS')
    excluded=frozenset(old | ({index} if index is not None else set()))
    assessment,rejected=record['policy']._empty_input_assessment(snapshot,_excluded_rows=excluded)
    observation=_observation(record['policy'],snapshot,assessment,rejected,excluded)
    if assessment.anchor is None:
        _revoke_record_view(record)
        return assessment,rejected,observation
    sample=sample_context(snapshot)
    if tracker['phase']=='CANDIDATE':
        bound=_DISPLAYS[record['display_witness']]
        if assessment.anchor!=bound['anchor']:
            _fail(record,'INPUT_PROBE_REVOKED','ANCHOR_GEOMETRY')
    elif index is not None and sample is not None:
        witness=ContextDisplayWitness(_SEAL)
        _DISPLAYS[witness]={'command':weakref.ref(command),'tracker':tracker,
            'submit_frame':record['submit_frame'],'frame':frame,'sample':sample,
            'index':index,'row':snapshot.rows[index],'anchor':assessment.anchor}
        record['display_witness']=witness; tracker['phase']='CANDIDATE'
    else: return None
    return assessment,rejected,observation


class ContextRejectionObservation(_Sealed):
    __slots__=()


class EditRowObserver(_Sealed):
    """One private rejected row; never a new input or acceptance proof."""
    __slots__=()

    def bind_command(self,command_record):
        record=_EDIT_ROWS.get(self)
        command=next((key for key,value in _COMMANDS.items() if value is command_record),None)
        if (record is None or record['command'] is not None or command is None
                or any(command_record.get(key) is not value for key,value in zip(
                    ('scope','state','transition','journal'),record['bindings'][1:]))):
            self.finish(); raise _error('INPUT_PROBE_SCOPE_REJECTED')
        record.update(command=weakref.ref(command),run=command_record['run'],deadline=command_record['deadline'])

    def freeze(self,error,check,*,command_record,snapshot=None,assessment=None,rejected_index=None):
        record=_EDIT_ROWS.get(self)
        if record is None or record['attempted']: return
        record['attempted']=True
        command=record['command']() if record['command'] is not None else None
        if (command is None or _COMMANDS.get(command) is not command_record
                or command_record.get('run') is not record['run']
                or check!='NORMALIZED_ELIGIBILITY' or getattr(error,'reason',None)!='INPUT_PROBE_REVOKED'
                or type(snapshot) is not TerminalSnapshot or type(assessment) is not EmptyInputAssessment
                or assessment.anchor is not None
                or (assessment.reason,assessment.rowRelation,assessment.rowCause)!=
                    ('UNSUPPORTED_ROW','OTHER_CAPTURED_ROW','UNRECOGNIZED_SHAPE')
                or type(rejected_index) is not int or not 0<=rejected_index<len(snapshot.rows)
                or rejected_index==command_record['anchor'].row): return
        controller,scope,state,transition,journal=record['bindings']
        fields=journal.project_fields(error,controller_owner=controller,scope=scope,state=state,transition_owner=transition)
        if fields!={'context_command_failure':{'phase':'EDIT_PENDING','check':'NORMALIZED_ELIGIBILITY',
                'commandBytesWritten':8,'enterBytesWritten':0},'normalized_input_failure':{
                    'reason':'UNSUPPORTED_ROW','rowRelation':'OTHER_CAPTURED_ROW','rowCause':'UNRECOGNIZED_SHAPE'}}: return
        row=snapshot.rows[rejected_index]
        if (type(row) is not tuple or len(row)>120
                or not re.match(r'^\s*❯',TerminalInputPolicy._row_text(row))): return
        record['failure']=(error,weakref.ref(snapshot),row)

    def project(self,error,*,controller_owner,scope,state,transition_owner,journal,snapshot):
        record=_EDIT_ROWS.get(self)
        if record is None or record['failure'] is None: return None
        if any(a is not b for a,b in zip(
                (controller_owner,scope,state,transition_owner,journal),record['bindings'])): return None
        command=record['command']() if record['command'] is not None else None
        current=_COMMANDS.get(command) if command is not None else None
        failure=record['failure']
        if (current is None or current.get('run') is not record['run']
                or current.get('deadline')!=record['deadline'] or failure[0] is not error
                or failure[1]() is not snapshot
                or any(current.get(key) is not value for key,value in zip(
                    ('scope','state','transition','journal'),record['bindings'][1:]))): return None
        if journal.project_fields(error,controller_owner=controller_owner,scope=scope,state=state,
                transition_owner=transition_owner) is None: return None
        return failure[2],record['deadline']

    def finish(self):
        _EDIT_ROWS.pop(self,None)


def _create_edit_row_observer(*,controller_owner,scope,state,transition_owner,journal):
    if (type(controller_owner) is not object or type(transition_owner) is not object
            or type(journal) is not ContextFailureJournal or scope is None or state is None):
        raise _error('INPUT_PROBE_SCOPE_REJECTED')
    value=EditRowObserver(_SEAL)
    _EDIT_ROWS[value]={'bindings':(controller_owner,scope,state,transition_owner,journal),
        'command':None,'run':None,'deadline':None,'attempted':False,'failure':None}
    return value


def _live(record,frame=None,snapshot=None):
    from terminal_input_challenge import _context_scope_binding
    if record is None or record['phase']=='REVOKED': _fail(record,'INPUT_PROBE_REVOKED')
    command=next((key for key,value in _COMMANDS.items() if value is record),None)
    if command in _DISPLAY_TRACKERS: _display_tracker(command,record)
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
        record['phase']='REVOKED'; _release_display(record); _release_command_menu(record); _revoke_record_view(record); raise
    if frame is not None:
        if type(frame) is not int or not record['frame']<=frame<=MAX_CAPTURE:
            _fail(record,'INPUT_PROBE_STATE_REJECTED','FRAME_STATE')
        record['frame']=frame
    if snapshot is not None:
        if type(snapshot) is not TerminalSnapshot: _fail(record,'INPUT_PROBE_STATE_REJECTED','FRAME_STATE')
        if record['policy'].active_input_forbidden(snapshot): _fail(record,'INPUT_PROBE_REVOKED','FORBIDDEN_UI')
        if record.get('resume_view') is not None:
            from terminal_resume_history import validate_resume_view
            validate_resume_view(record['resume_view'],policy=record['policy'],snapshot=snapshot,
                frame=record['frame'],state=record['state'],scope=record['scope'],native_owner=record['native'],
                controller_owner=record['controller'],transition_owner=record['transition'])


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
    rejected=None
    if record.get('resume_view') is not None:
        command=next(key for key,value in _COMMANDS.items() if value is record)
        assessment,rejected,_=_compose_input_assessment(record['policy'],snapshot,frame=record['frame'],
            state=record['state'],scope=record['scope'],native_owner=record['native'],
            controller_owner=record['controller'],transition_owner=record['transition'],
            resume_view=record['resume_view'],context_command=command,normalized_snapshot=normalized)
    else:
        excluded=_correlated_menu_row(record,snapshot)
        if excluded is not None:
            assessment,rejected=record['policy']._empty_input_assessment(normalized,excluded_row=excluded)
        elif record.get('edit_observer') is not None:
            assessment,rejected=record['policy']._empty_input_assessment(normalized)
        else: assessment=record['policy'].empty_input_assessment(normalized)
    if assessment.anchor!=anchor:
        try: detail=_normalized_failure_detail(assessment,anchor)
        except Exception: detail=None
        _fail(record,'INPUT_PROBE_REVOKED','NORMALIZED_ELIGIBILITY',normalized_input_failure=detail,
            edit_snapshot=snapshot,edit_assessment=assessment,rejected_index=rejected)
    return count


def _history_rows(policy,snapshot,*,_excluded_rows=frozenset()):
    matches=[]
    cursor=snapshot.baseY+snapshot.cursorY-snapshot.viewportY
    for index,row in enumerate(snapshot.rows):
        if index==cursor or index in _excluded_rows: continue
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
        if record is not None:
            record['phase']='REVOKED'; _release_display(record); _release_command_menu(record); _revoke_record_view(record)

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
            record['submit_signature']=_preenter_context_signature(record,snapshot)
            record['submit_frame']=frame
        elif record['phase'] not in ('CONTEXT_PENDING','RECEIPT_READY'):
            _fail(record,'INPUT_PROBE_STATE_REJECTED','PHASE_STATE')
        if record.get('resume_view') is not None:
            _observe_resumed_display(self,snapshot,frame)
            tracker=_DISPLAY_TRACKERS.get(self)
            if record['phase']=='CONTEXT_PENDING' and tracker['phase']=='CANDIDATE':
                self.context_display_percent(snapshot,frame)
        return record['phase']

    def submit_bytes(self,snapshot,frame):
        record=_COMMANDS.get(self); _live(record,frame,snapshot)
        if record['phase']!='COMMAND_ECHO_MATCHED': _fail(record,'INPUT_PROBE_STATE_REJECTED','PHASE_STATE')
        if _prefix(record,snapshot,record['written'])!=len(_BODY):
            _fail(record,'INPUT_PROBE_STATE_REJECTED','INCOMPLETE_ECHO')
        record['policy'].mark_transition(snapshot)
        record['submit_signature']=_preenter_context_signature(record,snapshot)
        _phase(record,'SUBMIT_PENDING'); record['submit_frame']=frame
        if record.get('resume_view') is not None: _observe_resumed_display(self,snapshot,frame)
        return b'\r'

    def submission_written(self,count):
        record=_COMMANDS.get(self); _live(record)
        if record['phase']!='SUBMIT_PENDING': _fail(record,'INPUT_PROBE_STATE_REJECTED','PHASE_STATE')
        if type(count) is not int or count!=1: _fail(record,'INPUT_PROBE_STATE_REJECTED','WRITE_COUNT')
        _phase(record,'CONTEXT_PENDING')
        _release_command_menu(record)
        if record.get('resume_view') is not None:
            tracker=_display_tracker(self,record)
            if tracker['phase']!='PRE_ENTER': _fail(record,'INPUT_PROBE_STATE_REJECTED','PHASE_STATE')
            tracker['phase']='AWAIT_DISPLAY'
            from terminal_resume_history import note_resume_submission
            note_resume_submission(record['resume_view'],command=self)

    def context_display_percent(self,snapshot,frame):
        record=_COMMANDS.get(self); _live(record,frame,snapshot)
        if record.get('resume_view') is None: _fail(record,'INPUT_PROBE_SCOPE_REJECTED','SCOPE_BINDING')
        result=_assess_resumed_context(self,snapshot,frame)
        if result is None: return None
        assessment,_,observation=result
        if assessment.anchor is None:
            error=_error('INPUT_PROBE_INELIGIBLE',assessment)
            _diagnostic(record,'freeze',error,'HISTORY_ELIGIBILITY')
            self.invalidate('INPUT_PROBE_REVOKED')
            attach_context_rejection(error,observation); raise error
        return _DISPLAYS[record['display_witness']]['sample'].numbers.used

    def bind_history(self,snapshot,frame):
        record=_COMMANDS.get(self); _live(record,frame,snapshot)
        if record['phase']!='CONTEXT_PENDING': _fail(record,'INPUT_PROBE_STATE_REJECTED','PHASE_STATE')
        if frame<=record['submit_frame']:
            _fail(record,'INPUT_PROBE_STATE_REJECTED','FRESH_CONTEXT_FRAME_NOT_ADVANCED')
        if record.get('resume_view') is not None:
            result=_assess_resumed_context(self,snapshot,frame)
            if result is None: _fail(record,'INPUT_PROBE_STATE_REJECTED','DISPLAY_WITNESS_UNPROVEN')
            assessment,rejected,observation=result
            excluded=(_DISPLAYS[record['display_witness']]['index']
                if assessment.anchor is not None else None)
        else:
            if record['policy']._context_signature(snapshot)==record['submit_signature']:
                _fail(record,'INPUT_PROBE_STATE_REJECTED','FRESH_CONTEXT_SIGNATURE_UNCHANGED')
            if record['policy'].context_percent(snapshot) is None:
                _fail(record,'INPUT_PROBE_STATE_REJECTED','FRESH_CONTEXT_NUMERIC_UNAVAILABLE')
            matches=_history_rows(record['policy'],snapshot)
            if len(matches)>1: _fail(record,'INPUT_PROBE_REVOKED','HISTORY_AMBIGUITY')
            excluded=matches[0] if matches else None
            assessment,rejected=record['policy']._empty_input_assessment(snapshot,excluded)
            observation=_observation(record['policy'],snapshot,assessment,rejected,excluded) if excluded is not None else None
        if assessment.anchor is None:
            error=_error('INPUT_PROBE_INELIGIBLE',assessment)
            _diagnostic(record,'freeze',error,'HISTORY_ELIGIBILITY')
            self.invalidate('INPUT_PROBE_REVOKED')
            attach_context_rejection(error,observation)
            raise error
        _phase(record,'RECEIPT_READY')
        if record.get('resume_view') is not None:
            _display_tracker(self,record)['phase']='CONSUMED'
        # Later receipt/nonce lifetime failures are outside this observation window.
        record['journal']=None
        if excluded is None: return None
        value=ContextEchoReceipt(_SEAL)
        _RECEIPTS[value]=(self,excluded,snapshot.rows[excluded],assessment.anchor)
        return value


def begin_context_command(scope,state,native_owner,transition_owner,policy,baseline,frame,*,_diagnostic_journal=None,
                          _edit_row_observer=None,_resume_view=None,_controller_owner=None):
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
    if _resume_view is not None:
        assessment,_,_=_compose_input_assessment(policy,baseline,frame=frame,state=state,scope=scope,
            native_owner=native_owner,controller_owner=_controller_owner,transition_owner=transition_owner,
            resume_view=_resume_view)
    else: assessment=policy.empty_input_assessment(baseline)
    if assessment.anchor is None:
        error=_error('INPUT_PROBE_INELIGIBLE',assessment)
        _diagnostic(record,'freeze',error,'BASELINE_ELIGIBILITY')
        raise error
    value=OwnedContextCommand(_SEAL)
    _COMMANDS[value]={'scope':scope,'state':state,'native':native_owner,'transition':transition_owner,
        'policy':policy,'run':run,'deadline':deadline,'time':_now(),'frame':frame,'phase':'ELIGIBLE',
        'anchor':assessment.anchor,'row':baseline.rows[assessment.anchor.row],'written':0,'progress':0,
        'journal':_diagnostic_journal,'resume_view':_resume_view,'controller':_controller_owner}
    if _resume_view is not None:
        from terminal_resume_history import _register_resume_dependent
        _register_resume_dependent(_resume_view,value)
    command_record=_COMMANDS[value]
    origin=(weakref.ref(value),baseline,scope,state,native_owner,transition_owner,run,deadline,assessment.anchor,frame)
    command_record['_menu_origin']=origin; command_record['_menu_selection']=None
    _MENU_BINDINGS[value]=(origin,None)
    if _resume_view is not None:
        _DISPLAY_TRACKERS[value]={'owners':_display_owners(command_record),'deadline':deadline,
            'phase':'PRE_ENTER','inventory':set(),'baseline':None,'distinct':None}
        _observe_resumed_display(value,baseline,frame)
    if type(_edit_row_observer) is EditRowObserver:
        try:
            _edit_row_observer.bind_command(_COMMANDS[value])
            _COMMANDS[value]['edit_observer']=_edit_row_observer
        except Exception:
            # Optional observation loss never changes command authority.
            try: _edit_row_observer.finish()
            except Exception: pass
    _diagnostic(_COMMANDS[value],'set_phase','ELIGIBLE')
    _live(_COMMANDS[value],frame,baseline)
    return value


def _resume_indices(record,snapshot,frame):
    if record.get('resume_view') is None: return frozenset()
    from terminal_resume_history import validate_resume_view
    return validate_resume_view(record['resume_view'],policy=record['policy'],snapshot=snapshot,
        frame=frame,state=record['state'],scope=record['scope'],native_owner=record['native'],
        controller_owner=record['controller'],transition_owner=record['transition'])


def _resume_submission_acked(command,view):
    record=_COMMANDS.get(command) if type(command) is OwnedContextCommand else None
    return bool(record is not None and record.get('resume_view') is view
        and record['phase'] in ('CONTEXT_PENDING','RECEIPT_READY')
        and record['written']==8 and record['progress']==8 and 'submit_frame' in record)


def validate_context_history(receipt,policy,snapshot,*,scope,state,native_owner,transition_owner,frame,
                             _resume_view=None,_controller_owner=None):
    registered=_RECEIPTS.get(receipt) if type(receipt) is ContextEchoReceipt else None
    if registered is None: raise _error('INPUT_PROBE_SCOPE_REJECTED')
    command,index,row,anchor=registered; record=_COMMANDS.get(command)
    if (record is not None and (record.get('resume_view') is not _resume_view
            or (record.get('resume_view') is not None and record.get('controller') is not _controller_owner))):
        _fail(record,'INPUT_PROBE_REVOKED')
    _live(record,frame,snapshot)
    if record.get('resume_view') is not None: _validate_resumed_display(command,snapshot,frame)
    old=_resume_indices(record,snapshot,frame)
    if (record['phase']!='RECEIPT_READY' or policy is not record['policy'] or scope is not record['scope']
            or state is not record['state'] or native_owner is not record['native']
            or transition_owner is not record['transition'] or snapshot.active!=anchor.buffer
            or snapshot.baseY!=anchor.baseY or snapshot.viewportY!=anchor.viewportY
            or snapshot.cursorY+snapshot.baseY-snapshot.viewportY!=anchor.row
            or snapshot.rows[index]!=row or _history_rows(policy,snapshot,_excluded_rows=old)!=[index]
            or index in old):
        _fail(record,'INPUT_PROBE_REVOKED')
    return index


def assess_context_input(policy,snapshot,*,receipt,scope,state,native_owner,transition_owner,frame,
                         _resume_view=None,_controller_owner=None,_actual_snapshot=None,_normalization_owner=None):
    if _resume_view is not None:
        if receipt is None:
            from terminal_resume_history import revoke_resume_view
            revoke_resume_view(_resume_view)
            raise _error('INPUT_PROBE_STATE_REJECTED')
        assessment,_,observation=_compose_input_assessment(policy,_actual_snapshot or snapshot,frame=frame,
            state=state,scope=scope,native_owner=native_owner,controller_owner=_controller_owner,
            transition_owner=transition_owner,resume_view=_resume_view,context_receipt=receipt,
            normalized_snapshot=snapshot if _actual_snapshot is not None else None,
            normalization_owner=_normalization_owner)
        return assessment,observation
    excluded=None
    if receipt is not None:
        excluded=validate_context_history(receipt,policy,snapshot,scope=scope,state=state,
            native_owner=native_owner,transition_owner=transition_owner,frame=frame)
    assessment,rejected=policy._empty_input_assessment(snapshot,excluded)
    observation=_observation(policy,snapshot,assessment,rejected,excluded) if receipt is not None else None
    if receipt is not None and assessment.anchor is None:
        _RECEIPTS[receipt][0].invalidate('INPUT_PROBE_REVOKED')
    return assessment,observation


def _compose_input_assessment(policy,actual_snapshot,*,frame,state,scope,native_owner,controller_owner,
        transition_owner,resume_view=None,context_receipt=None,context_command=None,normalized_snapshot=None,
        normalization_owner=None):
    from terminal_resume_history import validate_resume_view, revoke_resume_view, ResumeHistoryError
    excluded=set()
    if resume_view is not None:
        excluded.update(validate_resume_view(resume_view,policy=policy,snapshot=actual_snapshot,frame=frame,
            state=state,scope=scope,native_owner=native_owner,controller_owner=controller_owner,
            transition_owner=transition_owner))
    def add(index):
        if index is None: return
        cursor=actual_snapshot.baseY+actual_snapshot.cursorY-actual_snapshot.viewportY
        if type(index) is not int or not 0<=index<len(actual_snapshot.rows) or index in excluded or index==cursor:
            revoke_resume_view(resume_view); raise ResumeHistoryError('RESUME_HISTORY_LAYOUT_REJECTED')
        excluded.add(index)
    if context_receipt is not None:
        add(validate_context_history(context_receipt,policy,actual_snapshot,scope=scope,state=state,
            native_owner=native_owner,transition_owner=transition_owner,frame=frame,
            _resume_view=resume_view,_controller_owner=controller_owner))
    if context_command is not None:
        record=_COMMANDS.get(context_command) if type(context_command) is OwnedContextCommand else None
        if record is None or record.get('resume_view') is not resume_view or record.get('controller') is not controller_owner:
            revoke_resume_view(resume_view); raise ResumeHistoryError('RESUME_HISTORY_SCOPE_REJECTED')
        _live(record,frame,actual_snapshot)
        if record['phase'] in ('ELIGIBLE','EDIT_PENDING','COMMAND_ECHO_MATCHED','SUBMIT_PENDING'):
            add(_correlated_menu_row(record,actual_snapshot))
        elif record['phase']=='CONTEXT_PENDING':
            if normalized_snapshot is not None:
                _fail(record,'INPUT_PROBE_STATE_REJECTED','PHASE_STATE')
            result=_assess_resumed_context(context_command,actual_snapshot,frame)
            if result is None: _fail(record,'INPUT_PROBE_STATE_REJECTED','DISPLAY_WITNESS_UNPROVEN')
            return result
    target=actual_snapshot
    if normalized_snapshot is not None:
        source=_COMMANDS.get(context_command) if type(context_command) is OwnedContextCommand else None
        if source is None:
            from terminal_input_challenge import NonceInputChallenge, _CHALLENGES
            source=_CHALLENGES.get(normalization_owner) if type(normalization_owner) is NonceInputChallenge else None
        if (source is None or source.get('resume_view') is not resume_view
                or any(source.get(key) is not value for key,value in (
                    ('scope',scope),('native',native_owner),('controller',controller_owner),('transition',transition_owner)))):
            revoke_resume_view(resume_view); raise ResumeHistoryError('RESUME_HISTORY_SCOPE_REJECTED')
        cursor=actual_snapshot.baseY+actual_snapshot.cursorY-actual_snapshot.viewportY
        if (type(normalized_snapshot) is not TerminalSnapshot
                or not 0<=cursor<len(actual_snapshot.rows)
                or (normalized_snapshot.active,normalized_snapshot.baseY,normalized_snapshot.viewportY,
                    normalized_snapshot.cursorY)!=(actual_snapshot.active,actual_snapshot.baseY,
                    actual_snapshot.viewportY,actual_snapshot.cursorY)
                or len(normalized_snapshot.rows)!=len(actual_snapshot.rows)
                or normalized_snapshot.rows[cursor]!=source['row']
                or normalized_snapshot.cursorX!=source['anchor'].cursorX
                or any(a!=b for i,(a,b) in enumerate(zip(actual_snapshot.rows,normalized_snapshot.rows)) if i!=cursor)):
            revoke_resume_view(resume_view); raise ResumeHistoryError('RESUME_HISTORY_LAYOUT_REJECTED')
        target=normalized_snapshot
    assessment,index=policy._empty_input_assessment(target,_excluded_rows=frozenset(excluded))
    # Frozen debug counterfactual may omit the already-proven normalized cursor;
    # this never participates in input authority and stores no copied row.
    debug_excluded=frozenset(excluded | ({cursor} if normalized_snapshot is not None else set()))
    observation=_observation(policy,actual_snapshot,assessment,index,debug_excluded)
    if assessment.anchor is None and resume_view is not None: revoke_resume_view(resume_view)
    return assessment,index,observation


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
    if type(excluded) is frozenset:
        current,rejected=policy._empty_input_assessment(snapshot,_excluded_rows=excluded)
    else: current,rejected=policy._empty_input_assessment(snapshot,excluded)
    return (True,index) if current==assessment and rejected==index else (True,None)
