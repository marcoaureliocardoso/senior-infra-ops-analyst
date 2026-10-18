"""Test-only cooperative cancellation and identity-bound Linux child ownership."""
from contextlib import contextmanager
import ctypes
import os
from pathlib import Path
import select
import signal
import stat
import subprocess
import sys
import threading
import time

MAX_OWNED=128
MAX_THREADS=256


class TerminalCancelled(RuntimeError):
    def __init__(self): super().__init__('terminal dialogue cancelled')


def _unavailable():
    return RuntimeError('terminal ownership unavailable')


def _subreaper(value=None):
    libc=ctypes.CDLL(None,use_errno=True)
    libc.prctl.argtypes=[ctypes.c_int,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_ulong]
    libc.prctl.restype=ctypes.c_int
    if value is None:
        result=ctypes.c_int()
        if libc.prctl(37,ctypes.addressof(result),0,0,0)!=0: raise _unavailable()
        return result.value
    if libc.prctl(36,int(value),0,0,0)!=0: raise _unavailable()


def _identity(pid):
    try:
        with Path(f'/proc/{pid}/stat').open('r',encoding='ascii') as stream:
            data=stream.read(4097)
        if len(data)>4096: raise _unavailable()
        tail=data.rsplit(')',1)[1].split()
        return int(tail[19]),int(tail[1])
    # An already-open proc descriptor can report ESRCH after normal exit.
    except (FileNotFoundError,ProcessLookupError): return None
    except (OSError,ValueError,IndexError,UnicodeError): raise _unavailable() from None


def _children(pid):
    try:
        tasks=list(Path(f'/proc/{pid}/task').iterdir())
        if len(tasks)>MAX_THREADS: raise _unavailable()
        values=set()
        for task in tasks:
            try:
                with (task/'children').open('r',encoding='ascii') as stream: data=stream.read(8193)
            except FileNotFoundError: continue
            if len(data)>8192: raise _unavailable()
            values.update(int(item) for item in data.split())
        if len(values)>MAX_OWNED or any(pid<=0 for pid in values): raise _unavailable()
        return values
    except FileNotFoundError: return set()
    except (OSError,ValueError,UnicodeError): raise _unavailable() from None


class TerminalCancellation:
    def __init__(self):
        self.requested=False
        self._depth=0
        self._entered=False
        self._handlers={}
        self._records={}
        self._roots={}
        self._prior_subreaper=None
        self._exclusive_children=False

    def _request(self,_signum,_frame): self.requested=True

    def __enter__(self):
        if (self._entered or os.name!='posix' or not sys.platform.startswith('linux')
                or threading.current_thread() is not threading.main_thread()
                or not callable(getattr(os,'pidfd_open',None))
                or not callable(getattr(signal,'pidfd_send_signal',None))): raise _unavailable()
        descriptor=None
        try:
            handlers={signum:signal.getsignal(signum) for signum in (signal.SIGTERM,signal.SIGHUP)}
            if any(handler is None for handler in handlers.values()): raise _unavailable()
            descriptor=os.pidfd_open(os.getpid(),0)
            _children(os.getpid())
            self._prior_subreaper=_subreaper(); _subreaper(1)
            for signum in (signal.SIGTERM,signal.SIGHUP):
                self._handlers[signum]=handlers[signum]
                signal.signal(signum,self._request)
            self._entered=True
            return self
        except (OSError,RuntimeError,ValueError):
            self._restore()
            raise _unavailable() from None
        finally:
            if descriptor is not None: os.close(descriptor)

    def _restore(self):
        for signum,handler in self._handlers.items(): signal.signal(signum,handler)
        self._handlers.clear()
        if self._prior_subreaper is not None:
            _subreaper(self._prior_subreaper); self._prior_subreaper=None
        self._entered=False

    def _remember(self,pid,expected_parent,owner):
        if pid in self._records: return
        if len(self._records)>=MAX_OWNED: raise _unavailable()
        before=_identity(pid)
        if before is None: return
        if before[1]!=expected_parent: raise _unavailable()
        try: descriptor=os.pidfd_open(pid,0)
        except ProcessLookupError: return
        try:
            after=_identity(pid)
            if after!=before: raise _unavailable()
        except BaseException:
            os.close(descriptor); raise
        self._records[pid]=(before[0],descriptor,owner)

    def publish_child(self,process):
        if not self._entered or not isinstance(process,subprocess.Popen): raise _unavailable()
        if process.poll() is not None:
            if not self._exclusive_children: raise _unavailable()
            self._roots[process.pid]=process
            self._discover()
            return
        self._remember(process.pid,os.getpid(),process)
        if process.pid not in self._records: raise _unavailable()
        self._roots[process.pid]=process
        self._discover()

    def _discover(self):
        # Only the dedicated one-target supervisor owns every direct adoption.
        # Ordinary callers never sweep unrelated children of their interpreter.
        if self._exclusive_children:
            owner=next(iter(self._roots.values()),None)
            if owner is not None:
                for child in _children(os.getpid()): self._remember(child,os.getpid(),owner)
        pending=list(self._records); visited=set()
        while pending:
            pid=pending.pop()
            if pid in visited: continue
            visited.add(pid)
            record=self._records.get(pid); identity=_identity(pid)
            if record is None or identity is None or identity[0]!=record[0]: continue
            for child in _children(pid):
                self._remember(child,pid,record[2])
                if child in self._records: pending.append(child)

    def spawn(self,command,**options):
        self.check()
        if (not isinstance(command,list) or not command or any(type(value) is not str for value in command)
                or options.get('start_new_session',True) is not True
                or set(options)-{'stdin','stdout','stderr','env','cwd','close_fds','start_new_session'}):
            raise _unavailable()
        read_fd,write_fd=os.pipe()
        process=None
        try:
            options={**options,'start_new_session':True,'close_fds':True,'pass_fds':(read_fd,)}
            process=subprocess.Popen([sys.executable,'-I','-B',str(Path(__file__).resolve()),
                '--owned-child',str(read_fd),'--',*command],**options)
            self.publish_child(process)
            self.check()  # No target can run until the parent owns its supervisor.
            if os.write(write_fd,b'G')!=1: raise _unavailable()
            return process
        except BaseException:
            with self.cleanup():
                if process is not None and process.pid in self._roots:
                    self._dispose(process)
                elif process is not None:
                    process.terminate()
                    try: process.wait(timeout=.3)
                    except subprocess.TimeoutExpired:
                        process.kill(); process.wait(timeout=.3)
            raise
        finally:
            os.close(read_fd); os.close(write_fd)

    def terminate_child(self,process):
        if process.pid not in self._roots: raise _unavailable()
        try:
            with self.cleanup(): self._dispose(process)
        except (OSError,ValueError): raise RuntimeError('terminal cleanup failed') from None

    def check(self):
        if not self._entered: raise _unavailable()
        self._discover()
        if self.requested and self._depth==0: raise TerminalCancelled()

    @contextmanager
    def cleanup(self):
        self._depth+=1
        try: yield
        finally: self._depth-=1

    def _reap(self):
        for process in self._roots.values(): process.poll()
        for pid in self._records:
            if pid not in self._roots:
                current=_identity(pid)
                if current is None or current[0]!=self._records[pid][0]: continue
                try: os.waitpid(pid,os.WNOHANG)
                except ChildProcessError: pass

    def _dispose(self,owner=None):
        deadline=time.monotonic()+.7; kill_at=time.monotonic()+.1
        sent=set()
        while True:
            self._discover(); self._reap()
            alive=[]
            selected={pid:record for pid,record in self._records.items() if owner is None or record[2] is owner}
            for pid,(_start,descriptor,_owner) in selected.items():
                if not select.select([descriptor],[],[],0)[0]: alive.append((pid,descriptor))
            if not alive:
                self._reap()
                if all((identity:=_identity(pid)) is None or identity[0]!=record[0]
                       for pid,record in selected.items()): return
            if time.monotonic()>=deadline: raise RuntimeError('terminal cleanup failed')
            signum=signal.SIGKILL if time.monotonic()>=kill_at else signal.SIGTERM
            for pid,descriptor in reversed(alive):
                if (pid,signum) not in sent:
                    try: signal.pidfd_send_signal(descriptor,signum,None,0)
                    except ProcessLookupError: pass
                    sent.add((pid,signum))
            time.sleep(.01)

    def __exit__(self,_type,_value,_traceback):
        try:
            with self.cleanup(): self._dispose()
        except (OSError,ValueError): raise RuntimeError('terminal cleanup failed') from None
        finally:
            for _pid,(_start,descriptor,_owner) in self._records.items(): os.close(descriptor)
            self._records.clear(); self._roots.clear()
            self._restore()
        return False


def _owned_child(descriptor,command):
    if descriptor<3 or not stat.S_ISFIFO(os.fstat(descriptor).st_mode) or not command: return 2
    result=2
    token=TerminalCancellation()
    with token:
        deadline=time.monotonic()+2
        released=False
        while time.monotonic()<deadline:
            token.check()
            if select.select([descriptor],[],[],.02)[0]:
                released=os.read(descriptor,1)==b'G'; break
        os.close(descriptor)
        if not released: return 2
        token.check()
        # This fresh interpreter has no unrelated jobs; every later adoption
        # can only descend from the one approved target launched below.
        token._exclusive_children=True
        process=subprocess.Popen(command,close_fds=True,start_new_session=True)
        token.publish_child(process)
        try:
            while process.poll() is None:
                token.check(); time.sleep(.01)
            token.check(); result=process.returncode
        except TerminalCancelled: result=2
    return 2 if token.requested or result is None or result<0 else result


if __name__=='__main__':
    try:
        if len(sys.argv)<5 or sys.argv[1]!='--owned-child' or sys.argv[3]!='--': raise _unavailable()
        code=_owned_child(int(sys.argv[2]),sys.argv[4:])
    except BaseException: code=2
    raise SystemExit(code)
