"""Bounded private terminal transport, not authorization or a live entrypoint."""
from __future__ import annotations

import base64
from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import selectors
import signal
import subprocess
import time
from types import MappingProxyType
from typing import Mapping

MAX_FRAME = 131072
MAX_FEED = 65536
MAX_CAPTURE = 8388608
PROTOCOL = 'TERMINAL_PROTOCOL_REJECTED'
DEPENDENCY = 'TERMINAL_DEPENDENCY_UNAVAILABLE'
DEADLINE = 'TERMINAL_DEADLINE_EXCEEDED'
CLEANUP = 'TERMINAL_CLEANUP_FAILED'
REASONS = frozenset((PROTOCOL, DEPENDENCY, DEADLINE, CLEANUP))
COUNT_KEYS = frozenset(('primaryAttributes','secondaryAttributes','cursorPosition','status','other'))


class TerminalStateError(RuntimeError):
    def __init__(self, reason: str):
        self.reason = reason if reason in REASONS else PROTOCOL
        super().__init__(self.reason)


def _unique(pairs):
    value = {}
    for key, item in pairs:
        if key in value: raise ValueError('duplicate field')
        value[key] = item
    return value


def _constant(_value):
    raise ValueError('nonfinite value')


def _json(data):
    return json.loads(data, object_pairs_hook=_unique, parse_constant=_constant)


def _canonical(location: Path, directory: bool = False) -> Path:
    if (not isinstance(location,Path) or not location.is_absolute() or location.is_symlink()
            or location.resolve(strict=True) != location
            or not (location.is_dir() if directory else location.is_file())):
        raise ValueError('invalid runtime artifact')
    return location


def validate_terminal_runtime(node: Path, module_root: Path) -> None:
    try:
        if os.name != 'posix': raise ValueError('unsupported platform')
        _canonical(node)
        if not os.access(node,os.X_OK): raise ValueError('not executable')
        _canonical(module_root,True)
        package = _canonical(module_root/'@xterm/headless',True)
        metadata = _canonical(package/'package.json')
        if metadata.stat().st_size > 65536: raise ValueError('metadata limit')
        info = _json(metadata.read_text(encoding='utf-8'))
        lock = _json(Path(__file__).with_name('terminal-runtime').joinpath('package-lock.json').read_text(encoding='utf-8'))
        expected = lock['packages']['node_modules/@xterm/headless']['version']
        if (info['name'] != '@xterm/headless' or info['version'] != expected
                or info['main'] != 'lib-headless/xterm-headless.js'):
            raise ValueError('unsupported runtime')
        _canonical(package/'lib-headless/xterm-headless.js')
    except (OSError,ValueError,TypeError,KeyError,UnicodeError):
        raise TerminalStateError(DEPENDENCY) from None


@dataclass(frozen=True)
class TerminalCell:
    text: str
    width: int


@dataclass(frozen=True)
class TerminalSnapshot:
    active: str
    cursorX: int
    cursorY: int
    baseY: int
    viewportY: int
    rows: tuple[tuple[TerminalCell,...],...]
    replyCounts: Mapping[str,int]


def _integer(value, low, high):
    if type(value) is not int or not low <= value <= high: raise ValueError('invalid integer')
    return value


def _snapshot(value) -> TerminalSnapshot:
    keys = {'active','cursorX','cursorY','baseY','viewportY','rows','replyCounts'}
    if type(value) is not dict or set(value) != keys or value['active'] not in ('normal','alternate'):
        raise ValueError('invalid snapshot')
    x = _integer(value['cursorX'],0,120)
    y = _integer(value['cursorY'],0,39)
    base = _integer(value['baseY'],0,1000)
    view = _integer(value['viewportY'],0,base)
    if value['active']=='alternate' and (base or view): raise ValueError('invalid alternate state')
    rows = value['rows']
    if type(rows) is not list or len(rows)!=40: raise ValueError('invalid rows')
    parsed = []
    for row in rows:
        if type(row) is not list or len(row)!=120: raise ValueError('invalid columns')
        cells=[]
        for cell in row:
            if type(cell) is not dict or set(cell)!= {'text','width'} or type(cell['text']) is not str:
                raise ValueError('invalid cell')
            if len(cell['text'].encode('utf-16-le'))>32: raise ValueError('cell limit')
            cells.append(TerminalCell(cell['text'],_integer(cell['width'],0,2)))
        for index,cell in enumerate(cells):
            if cell.width==0 and (cell.text or index==0 or cells[index-1].width!=2):
                raise ValueError('orphan continuation')
            if cell.width==2 and (not cell.text or index==119 or cells[index+1].width!=0 or cells[index+1].text):
                raise ValueError('incomplete wide cell')
        parsed.append(tuple(cells))
    counts=value['replyCounts']
    if type(counts) is not dict or set(counts)!=COUNT_KEYS: raise ValueError('invalid counts')
    counts = {key:_integer(count,0,MAX_CAPTURE) for key,count in counts.items()}
    return TerminalSnapshot(value['active'],x,y,base,view,tuple(parsed),MappingProxyType(counts))


class TerminalState:
    def __init__(self,node:Path,module_root:Path,deadline:float):
        self._process = None
        self._closed = False
        self._id = 0
        self._total = 0
        self._deadline = deadline
        try:
            if isinstance(deadline,bool) or not math.isfinite(deadline): raise TerminalStateError(DEADLINE)
            validate_terminal_runtime(node,module_root)
            if time.monotonic()>=deadline: raise TerminalStateError(DEADLINE)
            self._process = subprocess.Popen([str(node),str(Path(__file__).with_name('terminal-state-adapter.mjs')),
                '--module-root',str(module_root)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8'},cwd=Path(__file__).parent,
                start_new_session=True,close_fds=True)
            for stream in (self._process.stdin,self._process.stdout,self._process.stderr):
                os.set_blocking(stream.fileno(),False)
            self._exchange('init')
        except BaseException as error:
            self._shutdown()
            if isinstance(error,(KeyboardInterrupt,SystemExit,TerminalStateError)): raise
            raise TerminalStateError(DEPENDENCY) from None

    def _exchange(self,op,data=None):
        if self._closed or self._process is None: raise TerminalStateError(PROTOCOL)
        self._id += 1
        request = {'id':self._id,'op':op}
        if op=='feed': request['data']=data
        payload=(json.dumps(request,separators=(',',':'),ensure_ascii=False)+'\n').encode('utf-8')
        remaining_payload=memoryview(payload)
        observed=bytearray()
        deadline=min(self._deadline,time.monotonic()+2)
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(self._process.stdin,selectors.EVENT_WRITE,'stdin')
                selector.register(self._process.stdout,selectors.EVENT_READ,'stdout')
                selector.register(self._process.stderr,selectors.EVENT_READ,'stderr')
                while True:
                    remaining=deadline-time.monotonic()
                    if remaining<=0: raise TerminalStateError(DEADLINE)
                    for key,_events in selector.select(min(.1,remaining)):
                        if key.data=='stdin':
                            try: written=os.write(key.fd,remaining_payload[:8192])
                            except BlockingIOError: continue
                            if not written: raise TerminalStateError(PROTOCOL)
                            remaining_payload=remaining_payload[written:]
                            if not remaining_payload: selector.unregister(key.fileobj)
                            continue
                        try: chunk=os.read(key.fd,16384)
                        except BlockingIOError: continue
                        if key.data=='stderr':
                            if chunk: raise TerminalStateError(PROTOCOL)
                            selector.unregister(key.fileobj)
                            continue
                        if not chunk: raise TerminalStateError(PROTOCOL)
                        observed.extend(chunk)
                        if len(observed)>MAX_FRAME: raise TerminalStateError(PROTOCOL)
                        ending=observed.find(b'\n')
                        if ending<0: continue
                        if remaining_payload or ending!=len(observed)-1: raise TerminalStateError(PROTOCOL)
                        reply=_json(observed[:-1].decode('utf-8',errors='strict'))
                        if type(reply) is not dict: raise ValueError('invalid reply')
                        if reply.get('ok') is False:
                            if set(reply)!={'id','ok','reason'} or type(reply['id']) is not int or reply['id']!=0:
                                raise ValueError('invalid rejection')
                            raise TerminalStateError(reply['reason'])
                        keys={'id','ok','snapshot'} if op=='snapshot' else {'id','ok'}
                        if (set(reply)!=keys or type(reply['id']) is not int or reply['id']!=self._id
                                or reply['ok'] is not True): raise ValueError('invalid reply')
                        return _snapshot(reply['snapshot']) if op=='snapshot' else None
        except BaseException as error:
            self._shutdown()
            if isinstance(error,(KeyboardInterrupt,SystemExit,TerminalStateError)): raise
            raise TerminalStateError(PROTOCOL) from None

    def feed(self,data:bytes)->None:
        if type(data) is not bytes or len(data)>MAX_FEED or self._total+len(data)>MAX_CAPTURE:
            self._shutdown()
            raise TerminalStateError(PROTOCOL)
        self._total+=len(data)
        self._exchange('feed',base64.b64encode(data).decode('ascii'))

    def snapshot(self)->TerminalSnapshot:
        return self._exchange('snapshot')

    def _shutdown(self,graceful=False):
        if self._closed: return
        self._closed=True
        process=self._process
        failed=False
        try:
            if process is not None:
                if graceful:
                    try: process.wait(timeout=.05)
                    except subprocess.TimeoutExpired: pass
                try: os.killpg(process.pid,signal.SIGTERM)
                except ProcessLookupError: pass
                try: process.wait(timeout=.05)
                except subprocess.TimeoutExpired: pass
                # Always clean the group, even if its leader exited first.
                try: os.killpg(process.pid,signal.SIGKILL)
                except ProcessLookupError: pass
                process.wait(timeout=.2)
        except (OSError,subprocess.SubprocessError): failed=True
        finally:
            if process is not None:
                for stream in (process.stdin,process.stdout,process.stderr):
                    if stream is not None: stream.close()
        if failed: raise TerminalStateError(CLEANUP) from None

    def close(self)->None:
        if self._closed: return
        try: self._exchange('close')
        finally: self._shutdown(graceful=True)
