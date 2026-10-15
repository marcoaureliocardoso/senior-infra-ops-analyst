"""Private content-free write observations. No IO, live validation or authority."""
import weakref
from terminal_input_policy import INPUT_ELIGIBILITY_REJECTIONS, INPUT_ROW_RELATIONS, INPUT_ROW_CAUSES

PHASES=frozenset(('BASELINE','ELIGIBLE','EDIT_PENDING','COMMAND_ECHO_MATCHED',
    'SUBMIT_PENDING','CONTEXT_PENDING','RECEIPT_READY'))
CHECKS=frozenset(('BASELINE_ELIGIBILITY','SCOPE_BINDING','DEADLINE','CANCELLATION',
    'NATIVE_LIFETIME','AUTHENTICATION','FORBIDDEN_UI','FRAME_STATE','PHASE_STATE',
    'WRITE_COUNT','ANCHOR_GEOMETRY','CURSOR_PROGRESS','PREFIX_CELLS','COMMAND_CELLS',
    'TRAILING_CELLS','NORMALIZED_ELIGIBILITY','ECHO_REGRESSION','INCOMPLETE_ECHO',
    'FRESH_CONTEXT','HISTORY_AMBIGUITY','HISTORY_ELIGIBILITY','IO_WRITE'))
FAILURE_REASONS=frozenset(('RUNTIME_REJECTED','TERMINAL_DEADLINE_EXCEEDED')) | frozenset(
    'INPUT_PROBE_'+suffix for suffix in ('SCOPE_REJECTED','INELIGIBLE','ECHO_REJECTED',
        'CLEAR_REJECTED','REVOKED','DEADLINE','STATE_REJECTED','IO_FAILED'))
_FIELDS=('phase','check','commandBytesWritten','enterBytesWritten')
_SEAL=object()
_JOURNALS=weakref.WeakKeyDictionary()
_ATTACHMENTS=weakref.WeakKeyDictionary()


def valid_normalized_input_failure(value):
    if (type(value) is not dict or type(value.get('reason')) is not str
            or value['reason'] not in INPUT_ELIGIBILITY_REJECTIONS): return False
    if value['reason']!='UNSUPPORTED_ROW': return set(value)=={'reason'}
    return (set(value)=={'reason','rowRelation','rowCause'}
        and type(value['rowRelation']) is str and value['rowRelation'] in INPUT_ROW_RELATIONS
        and type(value['rowCause']) is str and value['rowCause'] in INPUT_ROW_CAUSES)


def valid_context_failure(value):
    return (type(value) is dict and set(value)==set(_FIELDS)
        and type(value['phase']) is str and value['phase'] in PHASES
        and type(value['check']) is str and value['check'] in CHECKS
        and type(value['commandBytesWritten']) is int and 0<=value['commandBytesWritten']<=8
        and type(value['enterBytesWritten']) is int and 0<=value['enterBytesWritten']<=1)


class _Sealed:
    __slots__=('__weakref__',)
    def __new__(cls,seal=None):
        if seal is not _SEAL: raise TypeError('private observation')
        return super().__new__(cls)
    def __repr__(self): return '<'+type(self).__name__+'>'


class _ContextFailureAttachment(_Sealed):
    __slots__=()


class ContextFailureJournal(_Sealed):
    __slots__=()

    def bind_run(self,run_owner):
        record=_JOURNALS.get(self)
        if record is None: return
        if type(run_owner) is not object or (record['run'] is not None and record['run'] is not run_owner):
            record['valid']=False
        else: record['run']=run_owner

    def set_phase(self,phase):
        record=_JOURNALS.get(self)
        if record is None or record['attempted']: return
        if type(phase) is not str or phase not in PHASES: record['valid']=False
        else: record['phase']=phase

    def acknowledge(self,count,*,submission,remaining):
        record=_JOURNALS.get(self)
        if record is None or not record['valid'] or record['attempted']: return False
        key='enter' if submission is True else 'command'
        limit=1 if submission is True else 8
        if (type(submission) is not bool or type(count) is not int or type(remaining) is not int
                or remaining!=limit-record[key] or not 0<count<=remaining):
            record['valid']=False; return False
        record[key]+=count
        return True

    def freeze(self,error,check,*,normalized_input_failure=None):
        record=_JOURNALS.get(self)
        if record is None or record['attempted']: return
        record['attempted']=True
        if (not record['valid'] or not isinstance(error,RuntimeError)
                or type(check) is not str or check not in CHECKS
                or hasattr(error,'_context_command_failure')): return
        payload=(record['phase'],check,record['command'],record['enter'])
        if not valid_context_failure(dict(zip(_FIELDS,payload))): return
        detail=None
        if (check=='NORMALIZED_ELIGIBILITY' and getattr(error,'reason',None)=='INPUT_PROBE_REVOKED'
                and valid_normalized_input_failure(normalized_input_failure)):
            detail=tuple(sorted(normalized_input_failure.items()))
        attachment=_ContextFailureAttachment(_SEAL)
        _ATTACHMENTS[attachment]=(weakref.ref(self),payload,detail)
        # Exception identity is held only for this transition and released by finish().
        record['failure']=(error,attachment,payload,detail)
        error._context_command_failure=attachment

    def project(self,error,*,controller_owner,scope,state,transition_owner):
        fields=self.project_fields(error,controller_owner=controller_owner,scope=scope,
            state=state,transition_owner=transition_owner)
        return fields['context_command_failure'] if fields is not None else None

    def project_fields(self,error,*,controller_owner,scope,state,transition_owner):
        record=_JOURNALS.get(self)
        if (record is None or not record['valid']
                or any(actual is not expected for actual,expected in zip(
                    (controller_owner,scope,state,transition_owner),record['bindings']))): return None
        failure=record['failure']
        if failure is None or failure[0] is not error: return None
        attachment=getattr(error,'_context_command_failure',None)
        if type(attachment) is not _ContextFailureAttachment or attachment is not failure[1]: return None
        registered=_ATTACHMENTS.get(attachment)
        if registered is None or registered[0]() is not self or registered[1:]!=failure[2:]: return None
        value=dict(zip(_FIELDS,registered[1]))
        if not valid_context_failure(value): return None
        fields={'context_command_failure':value}
        if registered[2] is not None:
            detail=dict(registered[2])
            if valid_normalized_input_failure(detail): fields['normalized_input_failure']=detail
        return fields

    def finish(self):
        record=_JOURNALS.pop(self,None)
        if record is not None and record['failure'] is not None:
            _ATTACHMENTS.pop(record['failure'][1],None)


def _create_context_journal(*,controller_owner,scope,state,transition_owner):
    # The controller has already validated its offline route. This is not a scope issuer.
    if type(controller_owner) is not object or type(transition_owner) is not object or scope is None or state is None:
        return None
    value=ContextFailureJournal(_SEAL)
    _JOURNALS[value]={'bindings':(controller_owner,scope,state,transition_owner),'run':None,
        'phase':'BASELINE','command':0,'enter':0,'valid':True,'attempted':False,'failure':None}
    return value
