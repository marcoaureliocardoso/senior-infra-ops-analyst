"""Opt-in sealed offline debug data. Never permission, input or acceptance."""
import copy
import json
import os
from pathlib import Path
import re
import stat
import time
import unicodedata
import weakref

from terminal_input_challenge import audit_offline_namespace, validate_probe_scope, InputProofError
from terminal_input_policy import TerminalInputPolicy, parse_context_percent
from terminal_state_adapter import TerminalSnapshot, _snapshot
from terminal_context_echo import context_rejection_projection, _context_rejection_policy

FRAME_LIMIT=131072
EXCERPT_LIMIT=4096
REPORT_LIMIT=16384
_SEAL=object()
_CAPTURES=weakref.WeakSet()
_FACTS={'networkIsolated':True,'operatorStateHidden':True,'capabilitiesDropped':True}
_FILE='context-debug-frame.json'


def _audit():
    if audit_offline_namespace()!=_FACTS: raise RuntimeError('DEBUG_SCOPE_REJECTED')


def _identity(root):
    value=root.lstat()
    if (not stat.S_ISDIR(value.st_mode) or value.st_uid!=os.getuid()
            or stat.S_IMODE(value.st_mode)!=0o700): raise RuntimeError('DEBUG_SCOPE_REJECTED')
    return value.st_dev,value.st_ino


def _sensitive(text):
    normalized=unicodedata.normalize('NFKC',text).lower()
    folded=''.join(char for char in normalized if char.isascii() and char.isalnum())
    return (any(word in folded for word in ('apikey','password','authorization','cookie','canary',
                'secret','privatekey','bearer','accesstoken','refreshtoken','selectloginmethod',
                'howwouldyouliketologin','yesitrustthisfolder','choosethetextstylethatlooksbest'))
        or re.search(r'\bsk[-_][a-z0-9]{8,}|-----begin',normalized) is not None)


def _escape(text):
    return ''.join(('\\u%04x'%ord(char)) if unicodedata.category(char) in ('Cc','Cf') else char for char in text)


class ContextDebugCapture:
    def __new__(cls,seal=None):
        if seal is not _SEAL: raise RuntimeError('DEBUG_SCOPE_REJECTED')
        return super().__new__(cls)

    def __repr__(self): return '<ContextDebugCapture>'

    def _live(self,state,scope):
        _audit()
        if (self not in _CAPTURES or state is not self._state or scope is not self._scope
                or time.monotonic()>=self._deadline or state.helper_reaped
                or _identity(self._root)!=self._identity): raise RuntimeError('DEBUG_SCOPE_REJECTED')
        state.check_cancelled()

    def capture(self,state,scope,snapshot,error,*,numeric_context=False):
        if self._attempted: return
        self._attempted=True
        self._status='OMITTED_SCOPE'
        directory=descriptor=None
        try:
            self._live(state,scope)
            if (numeric_context is not True or type(snapshot) is not TerminalSnapshot
                    or not isinstance(error,InputProofError) or error.reason!='INPUT_PROBE_INELIGIBLE'
                    or error.input_eligibility!='UNSUPPORTED_ROW'):
                self._status='OMITTED_PROVENANCE'; return
            policy=_context_rejection_policy(error) or TerminalInputPolicy()
            receipt_aware,rejected=context_rejection_projection(error,snapshot,policy)
            assessment=policy.empty_input_assessment(snapshot) if not receipt_aware else None
            if ((receipt_aware and rejected is None) or (not receipt_aware and
                    (assessment.reason!='UNSUPPORTED_ROW' or assessment.rowRelation!=error.input_row_relation
                        or assessment.rowCause!=error.input_row_cause))
                    or parse_context_percent(policy.screen_text(snapshot),True) is None):
                self._status='OMITTED_PROVENANCE'; return
            # Scan all cells before storing any frame; unknown credential-like material omits everything.
            if _sensitive('\n'.join(''.join(cell.text for cell in row) for row in snapshot.rows)):
                self._status='OMITTED_SENSITIVE'; return
            data={'active':snapshot.active,'cursorX':snapshot.cursorX,'cursorY':snapshot.cursorY,
                'baseY':snapshot.baseY,'viewportY':snapshot.viewportY,'replyCounts':dict(snapshot.replyCounts),
                'rows':[[{'text':cell.text,'width':cell.width} for cell in row] for row in snapshot.rows]}
            encoded=json.dumps(data,separators=(',',':'),ensure_ascii=False).encode('utf-8')
            if len(encoded)>FRAME_LIMIT:
                self._status='OMITTED_FRAME_LIMIT'; return
            _snapshot(data)  # Same bounded cell/geometry validation as the actual transport.
            self._live(state,scope)
            directory=os.open(self._root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
            observed=os.fstat(directory)
            if (observed.st_dev,observed.st_ino)!=self._identity: raise RuntimeError('DEBUG_SCOPE_REJECTED')
            descriptor=os.open(_FILE,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,
                0o600,dir_fd=directory)
            remaining=memoryview(encoded)
            while remaining:
                self._live(state,scope)
                written=os.write(descriptor,remaining)
                if written<=0: raise OSError
                remaining=remaining[written:]
            self._live(state,scope)
            if not receipt_aware:
                rejected=next(index for index,row in enumerate(snapshot.rows)
                    if re.match(r'^\s*❯',policy._row_text(row)) and policy._candidate(row) is None)
            cursor=snapshot.baseY+snapshot.cursorY-snapshot.viewportY
            selected=[rejected]+([cursor] if 0<=cursor<len(snapshot.rows) and cursor!=rejected else [])
            rows=[]
            for index in selected:
                row=snapshot.rows[index]
                rows.append({'index':index,'role':'rejected' if index==rejected else 'cursor',
                    'text':_escape(policy._row_text(row)),
                    'cells':[{'x':x,'text':_escape(cell.text),'width':cell.width} for x,cell in enumerate(row)
                        if cell.text or cell.width!=1]})
            excerpt={'buffer':snapshot.active,'cursorX':snapshot.cursorX,'cursorRow':cursor,'rows':rows}
            if len(json.dumps(excerpt,sort_keys=True).encode())>EXCERPT_LIMIT:
                self._status='OMITTED_EXCERPT_LIMIT'; return
            self._excerpt=excerpt; self._status='READY'
        except (OSError,RuntimeError,ValueError,TypeError,AttributeError,StopIteration,UnicodeError):
            self._excerpt=None
        finally:
            for owned in (descriptor,directory):
                if owned is not None:
                    try: os.close(owned)
                    except OSError: self._status='OMITTED_IO'; self._excerpt=None

    def report(self):
        # No excerpt can leave the case while its raw frame/history root still exists.
        if self._root.exists() or self._root.is_symlink(): return {'status':'OMITTED_CLEANUP'}
        report={'status':self._status,'untrustedData':True,'chatCopyMayPersist':True}
        if self._status=='READY' and self._excerpt is not None: report['excerpt']=copy.deepcopy(self._excerpt)
        return report


def create_context_debug(scope,state,root):
    _audit()
    deadline=validate_probe_scope(scope,state)
    root=Path(root).absolute()
    identity=_identity(root)
    value=ContextDebugCapture(_SEAL)
    value._state=state; value._scope=scope; value._root=root; value._identity=identity
    value._deadline=deadline; value._attempted=False; value._excerpt=None; value._status='NO_CAPTURE'
    _CAPTURES.add(value)
    return value


def validate_context_debug(value,state,scope):
    if type(value) is not ContextDebugCapture or value not in _CAPTURES:
        raise RuntimeError('DEBUG_SCOPE_REJECTED')
    value._live(state,scope)


def fit_debug_report(report,debug):
    def complete_size(value):
        # main merges audit facts, finalize_owned adds the receipt, print adds a newline.
        envelope={**_FACTS,**value,'disposableRootAbsent':True}
        return len((json.dumps(envelope,sort_keys=True)+'\n').encode())
    candidate={**report,'debugContext':debug}
    if complete_size(candidate)>REPORT_LIMIT:
        candidate={**report,'debugContext':{'status':'OMITTED_REPORT_LIMIT'}}
    if complete_size(candidate)>REPORT_LIMIT:
        return {'reasonCode':'OFFLINE_DEBUG_REPORT_LIMIT','debugContext':{'status':'OMITTED_REPORT_LIMIT'}}
    return candidate
