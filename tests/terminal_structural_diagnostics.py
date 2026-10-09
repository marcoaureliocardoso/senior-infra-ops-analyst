"""Test-only, bounded content-free diagnostics. Never input to acceptance."""
import copy
import json

MAX_RECORDS=16
# Four context phases fit the existing 16 KiB outer offline-report limit.
MAX_BYTES=3072
POINTS=frozenset(('initial','prompt_ready','context_sent','context_numeric','panel_close_sent',
    'panel_closed','exit_ready','failure','native_cleanup','helper_cleanup'))
REASONS=frozenset(('CHECKPOINT','WAIT_DEADLINE','SETTLE_DEADLINE','EXIT_WAIT_DEADLINE','PROCESS_EXITED',
    'INPUT_UNPROVEN','RUNTIME_REJECTED','IO_FAILED','SUBPROCESS_FAILED','CLEANUP_COMPLETED',
    'NATIVE_CLEANUP_FAILED','TERMINAL_PROTOCOL_REJECTED','TERMINAL_DEPENDENCY_UNAVAILABLE',
    'TERMINAL_DEADLINE_EXCEEDED','TERMINAL_CLEANUP_FAILED'))
READINESS=frozenset(('READY','FRESHNESS_UNPROVEN','AUTHENTICATION_REQUIRED','STARTUP_SELECTION',
    'UNSUPPORTED_MARKER','CANDIDATE_COUNT','CURSOR_ROW_MISMATCH','CURSOR_COLUMN_MISMATCH'))
STRUCTURE_FIELDS=frozenset(('buffer','cursorX','cursorY','baseY','viewportY','candidateCount',
    'inputFresh','contextFresh','locationFresh','authentication','readiness'))


def _structure(value):
    if type(value) is not dict or set(value)!=STRUCTURE_FIELDS: return False
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

    def add(self,point,reasonCode,**fields):
        if (type(point) is not str or point not in POINTS
                or type(reasonCode) is not str or reasonCode not in REASONS
                or not set(fields)<={'structure','leaderReaped'}
                or ('structure' in fields and not _structure(fields['structure']))
                or ('leaderReaped' in fields and type(fields['leaderReaped']) is not bool)):
            self._rejected=True; return
        if self._truncated: return
        record={'point':point,'reasonCode':reasonCode,**copy.deepcopy(fields)}
        candidate={'records':self._records+[record],'truncated':False,'rejected':False}
        if (len(self._records)>=MAX_RECORDS
                or len(json.dumps(candidate,separators=(',',':')).encode('utf-8'))>MAX_BYTES):
            self._truncated=True; return
        self._records.append(record)

    def report(self):
        return copy.deepcopy({'records':self._records,'truncated':self._truncated,'rejected':self._rejected})
