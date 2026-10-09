"""Private offline-only edit/echo/clear proof. Never consent or terminal IO."""
from dataclasses import replace
import math
from pathlib import Path
import re
import secrets
import socket
import time
import weakref

from terminal_input_policy import TerminalInputPolicy
from terminal_state_adapter import TerminalState, TerminalSnapshot, MAX_CAPTURE

REASONS=frozenset('INPUT_PROBE_'+suffix for suffix in (
    'SCOPE_REJECTED','INELIGIBLE','ECHO_REJECTED','CLEAR_REJECTED','REVOKED',
    'DEADLINE','STATE_REJECTED','IO_FAILED'))
_SEAL=object()
_ISSUERS=weakref.WeakSet()
_TERMINALS=weakref.WeakSet()
_SCOPES=weakref.WeakKeyDictionary()


class InputProofError(RuntimeError):
    def __init__(self,reason):
        self.reason=reason if type(reason) is str and reason in REASONS else 'INPUT_PROBE_STATE_REJECTED'
        super().__init__(self.reason)


def _now(): return time.monotonic()


def audit_offline_namespace():
    try:
        if {name for _,name in socket.if_nameindex()}!={'lo'}: raise ValueError
        if Path('/mnt/c').exists() or any(Path('/home').iterdir()) or any(Path('/root').iterdir()): raise ValueError
        caps=re.search(r'^CapEff:\s*([0-9a-fA-F]+)$',Path('/proc/self/status').read_text(),re.MULTILINE)
        if caps is None or int(caps[1],16)!=0: raise ValueError
    except (OSError,ValueError): raise InputProofError('INPUT_PROBE_SCOPE_REJECTED') from None
    return {'networkIsolated':True,'operatorStateHidden':True,'capabilitiesDropped':True}


def _audit():
    if audit_offline_namespace()!={'networkIsolated':True,'operatorStateHidden':True,'capabilitiesDropped':True}:
        raise InputProofError('INPUT_PROBE_SCOPE_REJECTED')


class OfflineProbeScope:
    __slots__=('__weakref__',)
    def __new__(cls,seal=None):
        if seal is not _SEAL: raise InputProofError('INPUT_PROBE_SCOPE_REJECTED')
        return super().__new__(cls)
    def __repr__(self): return '<OfflineProbeScope>'


class OfflineProbeIssuer:
    __slots__=('__weakref__',)
    def __new__(cls,seal=None):
        if seal is not _SEAL: raise InputProofError('INPUT_PROBE_SCOPE_REJECTED')
        return super().__new__(cls)
    def __repr__(self): return '<OfflineProbeIssuer>'
    def issue_scope(self,terminal,run_owner):
        _audit()
        if (self not in _ISSUERS or type(terminal) is not TerminalState
                or type(run_owner) is not object or terminal in _TERMINALS):
            raise InputProofError('INPUT_PROBE_SCOPE_REJECTED')
        deadline=terminal.operation_deadline
        if (type(deadline) not in (int,float) or not math.isfinite(deadline) or _now()>=deadline
                or terminal.helper_reaped): raise InputProofError('INPUT_PROBE_SCOPE_REJECTED')
        terminal.check_cancelled()
        scope=OfflineProbeScope(_SEAL)
        _SCOPES[scope]={'terminal':terminal,'run':run_owner,'deadline':deadline,'claimed':False}
        _TERMINALS.add(terminal)
        return scope


def create_offline_probe_issuer():
    _audit(); issuer=OfflineProbeIssuer(_SEAL); _ISSUERS.add(issuer); return issuer


def validate_probe_scope(scope,terminal):
    record=_SCOPES.get(scope) if type(scope) is OfflineProbeScope else None
    if (record is None or record['terminal'] is not terminal or record['claimed']
            or _now()>=record['deadline'] or terminal.helper_reaped):
        raise InputProofError('INPUT_PROBE_SCOPE_REJECTED')
    terminal.check_cancelled()
    return record['deadline']


class InputOwnershipProof:
    __slots__=()
    def __new__(cls,seal=None):
        if seal is not _SEAL: raise InputProofError('INPUT_PROBE_STATE_REJECTED')
        return super().__new__(cls)
    def __repr__(self): return '<InputOwnershipProof>'


class NonceInputChallenge:
    def __init__(self,scope,native_owner,transition_owner,policy,initial,frame):
        record=_SCOPES.get(scope) if type(scope) is OfflineProbeScope else None
        if record is None: raise InputProofError('INPUT_PROBE_SCOPE_REJECTED')
        validate_probe_scope(scope,record['terminal']); record['claimed']=True
        self._scope=scope; self._record=record
        self._native=native_owner; self._transition=transition_owner
        self._policy=policy; self._proof=None; self._marker=None
        self.phase='ELIGIBLE'; self._last_frame=frame; self._write_frame=frame; self._progress=0
        self._last_time=_now()
        if (type(frame) is not int or not 0<=frame<=MAX_CAPTURE
                or not isinstance(policy,TerminalInputPolicy)):
            self._fail('INPUT_PROBE_STATE_REJECTED')
        self._anchor=policy.empty_input_anchor(initial)
        if self._anchor is None: self._fail('INPUT_PROBE_INELIGIBLE')
        self._row=initial.rows[self._anchor.row]

    def __repr__(self): return '<NonceInputChallenge>'

    def invalidate(self,reason):
        self.phase='REVOKED'; self._marker=None; self._proof=None
        self._reason=reason if type(reason) is str and reason in REASONS else 'INPUT_PROBE_STATE_REJECTED'

    def _fail(self,reason):
        self.invalidate(reason); raise InputProofError(reason)

    def _check(self,frame=None):
        if self.phase=='REVOKED': raise InputProofError('INPUT_PROBE_REVOKED')
        now=_now()
        if not math.isfinite(now) or now<self._last_time or now>=self._record['deadline']:
            self._fail('INPUT_PROBE_DEADLINE')
        self._last_time=now
        try: self._record['terminal'].check_cancelled()
        except BaseException:
            self.invalidate('INPUT_PROBE_REVOKED'); raise
        if self._record['terminal'].helper_reaped: self._fail('INPUT_PROBE_REVOKED')
        if frame is not None:
            if type(frame) is not int or not self._last_frame<=frame<=MAX_CAPTURE:
                self._fail('INPUT_PROBE_STATE_REJECTED')
            self._last_frame=frame

    def type_bytes(self,snapshot,frame):
        self._check(frame)
        if self.phase!='ELIGIBLE': self._fail('INPUT_PROBE_STATE_REJECTED')
        if self._policy.empty_input_anchor(snapshot)!=self._anchor: self._fail('INPUT_PROBE_INELIGIBLE')
        self._marker=secrets.token_hex(8)
        self.phase='ECHO_PENDING'; self._write_frame=frame
        return self._marker.encode('ascii')

    def _echo_length(self,snapshot,reason):
        anchor=self._anchor
        if (snapshot.active!=anchor.buffer or snapshot.baseY!=anchor.baseY
                or snapshot.viewportY!=anchor.viewportY
                or snapshot.cursorY+snapshot.baseY-snapshot.viewportY!=anchor.row): self._fail(reason)
        if any(self._marker in self._policy._row_text(row) for index,row in enumerate(snapshot.rows)
                if index!=anchor.row): self._fail(reason)
        row=snapshot.rows[anchor.row]
        prefix=row[:anchor.cursorX]
        if prefix!=self._row[:anchor.cursorX]: self._fail(reason)
        raw=''.join(cell.text or (' ' if cell.width else '') for cell in row[anchor.cursorX:])
        tail=raw.rstrip(' \t\u00a0')
        if (not self._marker.startswith(tail) or any(cell.width!=1 for cell in row[anchor.cursorX:])
                or snapshot.cursorX!=anchor.cursorX+len(tail)): self._fail(reason)
        rows=list(snapshot.rows); rows[anchor.row]=self._row
        normalized=replace(snapshot,cursorX=anchor.cursorX,rows=tuple(rows))
        if self._policy.empty_input_anchor(normalized)!=anchor: self._fail('INPUT_PROBE_REVOKED')
        return len(tail)

    def observe(self,snapshot,frame):
        self._check(frame)
        if self.phase=='CONSUMED': return self.phase
        if self.phase=='ELIGIBLE':
            if self._policy.empty_input_anchor(snapshot)!=self._anchor: self._fail('INPUT_PROBE_INELIGIBLE')
            return self.phase
        if self.phase in ('ECHO_PENDING','ECHO_MATCHED'):
            if frame<=self._write_frame: self._fail('INPUT_PROBE_STATE_REJECTED')
            count=self._echo_length(snapshot,'INPUT_PROBE_ECHO_REJECTED')
            if count<self._progress: self._fail('INPUT_PROBE_ECHO_REJECTED')
            self._progress=count
            self.phase='ECHO_MATCHED' if count==16 else 'ECHO_PENDING'
        elif self.phase=='CLEAR_PENDING':
            if frame<=self._write_frame: self._fail('INPUT_PROBE_STATE_REJECTED')
            count=self._echo_length(snapshot,'INPUT_PROBE_CLEAR_REJECTED')
            if count==0:
                self.phase='PROVEN'; self._marker=None; self._proof=InputOwnershipProof(_SEAL)
            elif count!=16: self._fail('INPUT_PROBE_CLEAR_REJECTED')
        elif self.phase=='PROVEN':
            if self._policy.empty_input_anchor(snapshot)!=self._anchor: self._fail('INPUT_PROBE_REVOKED')
        else: self._fail('INPUT_PROBE_STATE_REJECTED')
        return self.phase

    def clear_bytes(self,snapshot,frame):
        self._check(frame)
        if self.phase!='ECHO_MATCHED': self._fail('INPUT_PROBE_STATE_REJECTED')
        if self._echo_length(snapshot,'INPUT_PROBE_ECHO_REJECTED')!=16: self._fail('INPUT_PROBE_ECHO_REJECTED')
        self.phase='CLEAR_PENDING'; self._write_frame=frame
        return b'\x15'

    def ownership_proof(self):
        self._check()
        if self.phase!='PROVEN': self._fail('INPUT_PROBE_STATE_REJECTED')
        return self._proof

    def consume_exit(self,proof,snapshot,frame,native_owner,transition_owner):
        try:
            self._check(frame)
            if (self.phase!='PROVEN' or proof is not self._proof or type(proof) is not InputOwnershipProof
                    or native_owner is not self._native or transition_owner is not self._transition
                    or self._policy.empty_input_anchor(snapshot)!=self._anchor):
                self._fail('INPUT_PROBE_REVOKED')
            self.phase='CONSUMED'; self._proof=None; return True
        except InputProofError: return False
