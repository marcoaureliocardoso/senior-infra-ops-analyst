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
from terminal_state_adapter import TerminalSnapshot, TerminalCell, _snapshot
from terminal_context_echo import context_rejection_projection, _context_rejection_policy

FRAME_LIMIT=131072
EXCERPT_LIMIT=4096
REPORT_LIMIT=16384
_SEAL=object()
_CAPTURES=weakref.WeakSet()
_EDIT_CAPTURES=weakref.WeakKeyDictionary()
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


def _edit_live(value,state,scope):
    _audit()
    record=_EDIT_CAPTURES.get(value)
    if (record is None or state is not record['state'] or scope is not record['scope']
            or time.monotonic()>=record['deadline'] or state.helper_reaped
            or _identity(record['root'])!=record['identity']): raise RuntimeError('DEBUG_SCOPE_REJECTED')
    state.check_cancelled()
    return record


def _edit_row_valid(row):
    if type(row) is not tuple or len(row)!=120: return False
    for index,cell in enumerate(row):
        if (type(cell) is not TerminalCell or type(cell.text) is not str or type(cell.width) is not int
                or not 0<=cell.width<=2 or len(cell.text.encode('utf-16-le'))>32): return False
        if cell.width==0 and (cell.text or index==0 or row[index-1].width!=2): return False
        if cell.width==2 and (not cell.text or index==119 or row[index+1].width!=0 or row[index+1].text): return False
    return True


class ContextEditDebugCapture:
    __slots__=('__weakref__',)
    def __new__(cls,seal=None):
        if seal is not _SEAL: raise RuntimeError('DEBUG_SCOPE_REJECTED')
        return super().__new__(cls)

    def __repr__(self): return '<ContextEditDebugCapture>'

    def bind(self,*,controller_owner,transition_owner,journal):
        from terminal_context_echo import _create_edit_row_observer
        record=_EDIT_CAPTURES.get(self)
        if record is None or record['bound']: raise RuntimeError('DEBUG_SCOPE_REJECTED')
        _edit_live(self,record['state'],record['scope'])
        record['bound']=True
        record['observer']=_create_edit_row_observer(controller_owner=controller_owner,scope=record['scope'],
            state=record['state'],transition_owner=transition_owner,journal=journal)
        return record['observer']

    def prepare(self,error,*,controller_owner,transition_owner,journal,snapshot):
        record=_EDIT_CAPTURES.get(self)
        if record is None or record['attempted']: return
        record['attempted']=True; record['status']='OMITTED_SCOPE'
        try:
            _edit_live(self,record['state'],record['scope'])
            record['status']='OMITTED_PROVENANCE'
            observer=record['observer']
            if observer is None: return
            projected=observer.project(error,controller_owner=controller_owner,scope=record['scope'],
                state=record['state'],transition_owner=transition_owner,journal=journal,snapshot=snapshot)
            if projected is None: return
            row,deadline=projected
            if time.monotonic()>=deadline: record['status']='OMITTED_SCOPE'; return
            if not _edit_row_valid(row): record['status']='OMITTED_ROW_LIMIT'; return
            if _sensitive('\n'.join(''.join(cell.text for cell in cells) for cells in snapshot.rows)):
                record['status']='OMITTED_SENSITIVE'; return
            excerpt={'rowRelation':'OTHER_CAPTURED_ROW','text':_escape(TerminalInputPolicy._row_text(row))}
            if len(json.dumps(excerpt,sort_keys=True).encode('utf-8'))>EXCERPT_LIMIT:
                record['status']='OMITTED_EXCERPT_LIMIT'; return
            _edit_live(self,record['state'],record['scope'])
            record['excerpt']=excerpt; record['status']='PREPARED'
        except Exception:
            if record['status']!='OMITTED_SCOPE': record['status']='OMITTED_OBSERVER'
            record['excerpt']=None
        finally:
            try: self.finish()
            except Exception:
                record['excerpt']=None; record['status']='OMITTED_OBSERVER'
                observer=record['observer']; record['observer']=None
                if observer is not None:
                    try: observer.finish()
                    except Exception: pass

    def finish(self):
        record=_EDIT_CAPTURES.get(self)
        if record is not None:
            observer=record['observer']; record['observer']=None
            if observer is not None:
                try: observer.finish()
                except Exception: pass

    def pending_report(self):
        record=_EDIT_CAPTURES.get(self)
        if record is None or record['reported']: return {'status':'NO_CAPTURE'}
        record['reported']=True
        excerpt=record['excerpt']; record['excerpt']=None
        self.finish()
        if record['root'].exists() or record['root'].is_symlink(): return {'status':'OMITTED_CLEANUP'}
        report={'status':record['status']}
        if record['status']=='PREPARED' and excerpt is not None: report['excerpt']=copy.deepcopy(excerpt)
        return report


def create_context_edit_debug(scope,state,root):
    _audit()
    deadline=validate_probe_scope(scope,state)
    root=Path(root).absolute(); identity=_identity(root)
    value=ContextEditDebugCapture(_SEAL)
    _EDIT_CAPTURES[value]={'scope':scope,'state':state,'root':root,'identity':identity,'deadline':deadline,
        'bound':False,'observer':None,'attempted':False,'status':'NO_CAPTURE','excerpt':None,'reported':False}
    return value


def validate_context_edit_debug(value,state,scope):
    if type(value) is not ContextEditDebugCapture or value not in _EDIT_CAPTURES:
        raise RuntimeError('DEBUG_SCOPE_REJECTED')
    _edit_live(value,state,scope)
