"""Test-only, bounded content-free diagnostics. Never input to acceptance."""
import copy
import json
from terminal_input_policy import INPUT_ELIGIBILITY_REJECTIONS, INPUT_ROW_RELATIONS, INPUT_ROW_CAUSES
from terminal_context_diagnostics import valid_context_failure, valid_normalized_input_failure, valid_history_rejection, FAILURE_REASONS
from terminal_resume_history import RESUME_REASONS

MAX_RECORDS=16
# Four context phases fit the existing 16 KiB outer offline-report limit.
MAX_BYTES=3072
POINTS=frozenset(('initial','prompt_ready','context_sent','context_numeric','panel_close_sent',
    'panel_closed','exit_ready','failure','native_cleanup','helper_cleanup',
    'input_probe_started','input_probe_echo','input_probe_cleared','context_display'))
REASONS=frozenset(('CHECKPOINT','WAIT_DEADLINE','SETTLE_DEADLINE','EXIT_WAIT_DEADLINE','PROCESS_EXITED',
    'INPUT_UNPROVEN','RUNTIME_REJECTED','IO_FAILED','SUBPROCESS_FAILED','CLEANUP_COMPLETED',
    'NATIVE_CLEANUP_FAILED','TERMINAL_PROTOCOL_REJECTED','TERMINAL_DEPENDENCY_UNAVAILABLE',
    'TERMINAL_DEADLINE_EXCEEDED','TERMINAL_CLEANUP_FAILED')) | frozenset(
        'INPUT_PROBE_'+suffix for suffix in ('SCOPE_REJECTED','INELIGIBLE','ECHO_REJECTED',
            'CLEAR_REJECTED','REVOKED','DEADLINE','STATE_REJECTED','IO_FAILED')) | RESUME_REASONS
READINESS=frozenset(('READY','FRESHNESS_UNPROVEN','AUTHENTICATION_REQUIRED','STARTUP_SELECTION',
    'UNSUPPORTED_MARKER','CANDIDATE_COUNT','CURSOR_ROW_MISMATCH','CURSOR_COLUMN_MISMATCH'))
STRUCTURE_FIELDS=frozenset(('buffer','cursorX','cursorY','baseY','viewportY','candidateCount',
    'inputFresh','contextFresh','locationFresh','authentication','readiness'))


def _structure(value):
    if (type(value) is not dict
            or not STRUCTURE_FIELDS<=set(value)<=STRUCTURE_FIELDS|{'readinessRejection'}): return False
    if 'readinessRejection' in value:
        detail=value['readinessRejection']
        if (value['readiness']!='UNSUPPORTED_MARKER' or type(detail) is not dict
                or set(detail)!={'rowRelation','rowCause','rowShape'}
                or type(detail['rowRelation']) is not str or detail['rowRelation'] not in INPUT_ROW_RELATIONS
                or type(detail['rowCause']) is not str or detail['rowCause'] not in INPUT_ROW_CAUSES
                or type(detail['rowShape']) is not str or detail['rowShape'] not in ('SDK_TEXT_PROMPT_SHAPE','OTHER')
                or (detail['rowShape']=='SDK_TEXT_PROMPT_SHAPE' and detail['rowCause']!='UNRECOGNIZED_SHAPE')):
            return False
    for key,maximum in (('cursorX',120),('cursorY',39),('baseY',1000),('viewportY',1000),('candidateCount',40)):
        if type(value[key]) is not int or not 0<=value[key]<=maximum: return False
    if (type(value['buffer']) is not str or value['buffer'] not in ('normal','alternate')
            or value['viewportY']>value['baseY']
            or (value['buffer']=='alternate' and (value['baseY'] or value['viewportY']))): return False
    return (all(type(value[key]) is bool for key in ('inputFresh','contextFresh','locationFresh'))
        and type(value['authentication']) is str
        and value['authentication'] in ('NONE','API_KEY_APPROVAL_REQUIRED','LOGIN_REQUIRED')
        and type(value['readiness']) is str and value['readiness'] in READINESS)


class TerminalDiagnostics:
    def __init__(self):
        self._records=[]; self._truncated=False; self._rejected=False
        self._history_annotations={}

    def add(self,point,reasonCode,**fields):
        optional=fields.pop('historyRejection',None)
        base=fields.get('contextCommandFailure')
        keep_history=False
        try:
            keep_history=(point=='failure' and reasonCode=='INPUT_PROBE_INELIGIBLE'
                and fields.get('inputEligibility')=='UNSUPPORTED_ROW' and valid_context_failure(base)
                and base=={'phase':'CONTEXT_PENDING','check':'HISTORY_ELIGIBILITY','commandBytesWritten':8,'enterBytesWritten':1}
                and valid_history_rejection(optional))
        except Exception: pass
        if (type(point) is not str or point not in POINTS
                or type(reasonCode) is not str or reasonCode not in REASONS
                or not set(fields)<={'structure','leaderReaped','inputEligibility','inputRowRelation','inputRowCause',
                    'contextCommandFailure','normalizedInputFailure','resumeViewDecision'}
                or (point=='context_display' and (reasonCode!='CHECKPOINT'
                    or set(fields)-{'resumeViewDecision'}
                    or fields.get('resumeViewDecision','VALID')!='VALID'))
                or (reasonCode in RESUME_REASONS and point!='failure')
                or ('resumeViewDecision' in fields and (point in ('native_cleanup','helper_cleanup')
                    or type(fields['resumeViewDecision']) is not str or fields['resumeViewDecision'] not in ('VALID','REJECTED')))
                or (reasonCode in RESUME_REASONS and fields.get('resumeViewDecision','REJECTED')!='REJECTED')
                or ('contextCommandFailure' in fields and (point!='failure' or reasonCode not in FAILURE_REASONS
                    or not valid_context_failure(fields['contextCommandFailure'])))
                or ('normalizedInputFailure' in fields and (point!='failure' or reasonCode!='INPUT_PROBE_REVOKED'
                    or not valid_context_failure(fields.get('contextCommandFailure'))
                    or fields['contextCommandFailure']['check']!='NORMALIZED_ELIGIBILITY'
                    or not valid_normalized_input_failure(fields['normalizedInputFailure'])))
                or ('inputEligibility' in fields and (point!='failure' or reasonCode!='INPUT_PROBE_INELIGIBLE'
                    or type(fields['inputEligibility']) is not str
                    or fields['inputEligibility'] not in INPUT_ELIGIBILITY_REJECTIONS))
                or (('inputRowRelation' in fields or 'inputRowCause' in fields) and
                    (point!='failure' or reasonCode!='INPUT_PROBE_INELIGIBLE'
                    or fields.get('inputEligibility')!='UNSUPPORTED_ROW'
                    or type(fields.get('inputRowRelation')) is not str
                    or fields['inputRowRelation'] not in INPUT_ROW_RELATIONS
                    or type(fields.get('inputRowCause')) is not str
                    or fields['inputRowCause'] not in INPUT_ROW_CAUSES))
                or ('structure' in fields and not _structure(fields['structure']))
                or ('leaderReaped' in fields and type(fields['leaderReaped']) is not bool)):
            self._rejected=True; return
        if self._truncated: return
        record={'point':point,'reasonCode':reasonCode,**copy.deepcopy(fields)}
        candidate={'records':self._records+[record],'truncated':False,'rejected':False}
        if (len(self._records)>=MAX_RECORDS
                or len(json.dumps(candidate,sort_keys=True).encode('utf-8'))>MAX_BYTES):
            self._truncated=True; return
        self._records.append(record)
        if keep_history:
            try: self._history_annotations[len(self._records)-1]=copy.deepcopy(optional)
            except Exception: pass

    def report(self):
        result=copy.deepcopy({'records':self._records,'truncated':self._truncated,'rejected':self._rejected})
        # Decorate only after all base records (including cleanup) have priority.
        for index,detail in self._history_annotations.items():
            try:
                result['records'][index]['historyRejection']=copy.deepcopy(detail)
                if len(json.dumps(result,sort_keys=True).encode('utf-8'))>MAX_BYTES:
                    result['records'][index].pop('historyRejection')
            except Exception:
                result['records'][index].pop('historyRejection',None)
        return result
