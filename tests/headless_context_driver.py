"""Explicit test-only context dialogue over a passive terminal-state adapter."""
import fcntl
import json
import os
import pty
import re
import select
import signal
import struct
import subprocess
import termios
import time

from terminal_input_policy import TerminalInputPolicy
from terminal_state_adapter import TerminalStateError, MAX_CAPTURE


def _terminate(process):
    if process is None: return
    try: os.killpg(process.pid,signal.SIGTERM)
    except ProcessLookupError: pass
    try: process.wait(timeout=.2)
    except subprocess.TimeoutExpired: pass
    try: os.killpg(process.pid,signal.SIGKILL)
    except ProcessLookupError: pass
    process.wait(timeout=.5)


def drive_context(command,capture_path,timeout_seconds,events_path,startup_approval,state,*,writer):
    policy=TerminalInputPolicy()
    deadline=time.monotonic()+timeout_seconds
    process=None; master=slave=None; capture=None
    current_stage='initial_screen'; total=0; startup_open=True
    result=2; snapshot=None

    def record(stage,outcome,percent=None):
        if events_path is None: return
        value={'kind':'pty-driver','stage':stage,'outcome':outcome}
        if percent is not None: value['percent']=percent
        with events_path.open('a',encoding='utf-8') as stream:
            stream.write(json.dumps(value,sort_keys=True)+'\n')

    def pump(wait=.2):
        nonlocal total,snapshot,current_stage
        readable,_,_=select.select([master],[],[],min(wait,max(0,deadline-time.monotonic())))
        if not readable: return False
        try: chunk=os.read(master,65536)
        except OSError: return False
        if not chunk: return False
        if total+len(chunk)>MAX_CAPTURE: raise RuntimeError('context capture limit')
        total+=len(chunk); capture.write(chunk)
        state.feed(chunk); snapshot=state.snapshot()
        authentication=policy.authentication(snapshot)
        if authentication and not startup_open:
            current_stage=authentication
            raise RuntimeError('late authentication')
        return True

    def wait_for(predicate):
        while time.monotonic()<deadline:
            pump()
            if predicate(): return
            if process.poll() is not None: raise RuntimeError('context process exited')
        raise TimeoutError('context deadline')

    def settle(seconds=.4):
        quiet=time.monotonic()+seconds
        while time.monotonic()<deadline:
            if pump(min(.1,max(0,quiet-time.monotonic()))): quiet=time.monotonic()+seconds
            elif time.monotonic()>=quiet: return
        raise TimeoutError('context settle deadline')

    def text_folded():
        return re.sub('[^a-z]','',policy.screen_text(snapshot).lower())

    def auth_clear():
        nonlocal current_stage
        authentication=policy.authentication(snapshot)
        if not authentication: return
        previous=current_stage; current_stage=authentication
        if authentication=='api_key_approval_required' and startup_open and startup_approval is not None:
            settle(.6)
            selection=startup_approval.selection(policy.screen_text(snapshot))
            if selection is None: raise RuntimeError('startup decision unavailable')
            policy.mark_transition(snapshot)
            if selection: writer(master,selection)
            writer(master,b'\r')
            wait_for(lambda: policy.authentication(snapshot) is None)
            settle()
            if policy.authentication(snapshot): raise RuntimeError('startup authentication reappeared')
            record('api_key_approval','passed'); current_stage=previous
            return
        raise RuntimeError('startup authentication requires independent decision')

    def send(line):
        # Drain already-available redraws and re-evaluate immediately before IO.
        while pump(0): pass
        auth_clear()
        if not policy.ready(snapshot): raise RuntimeError('input state unproven')
        writer(master,line.encode('utf-8')+b'\r')

    try:
        capture_path.parent.mkdir(parents=True,exist_ok=True)
        if events_path is not None:
            events_path.parent.mkdir(parents=True,exist_ok=True)
            events_path.write_text('',encoding='utf-8')
        snapshot=state.snapshot(); policy.mark_transition(snapshot)
        master,slave=pty.openpty()
        fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',40,120,0,0))
        process=subprocess.Popen(command,stdin=slave,stdout=slave,stderr=slave,
            close_fds=True,start_new_session=True)
        os.close(slave); slave=None
        capture=capture_path.open('wb',buffering=0)
        wait_for(lambda: total>0); settle(); record('initial_screen','passed')
        auth_clear()
        for stage,heading,selection in (
            ('theme_selection','choosethetextstylethatlooksbestwithyourterminal',b''),
            ('trust_selection','yesitrustthisfolder',b'\x1b[A')):
            if heading not in text_folded(): continue
            current_stage=stage; policy.mark_transition(snapshot)
            if selection: writer(master,selection)
            writer(master,b'\r')
            wait_for(lambda: heading not in text_folded())
            settle(); auth_clear(); record(stage,'passed')
        current_stage='prompt_ready'
        wait_for(lambda: (auth_clear() is None) and policy.ready(snapshot))
        settle(1); auth_clear()
        if not policy.ready(snapshot): raise RuntimeError('input changed while settling')
        record(current_stage,'passed'); startup_open=False
        if startup_approval is not None: startup_approval.revoke()
        current_stage='context_inspected'
        # Check current input first, then establish the numeric observation barrier.
        send('/context'); policy.mark_transition(snapshot)
        wait_for(lambda: policy.context_percent(snapshot) is not None)
        percentage=policy.context_percent(snapshot)
        record(current_stage,'passed',percentage)
        if not policy.ready(snapshot):
            auth_clear(); policy.mark_transition(snapshot)
            writer(master,b'\x1b')
            wait_for(lambda: policy.ready(snapshot)); settle(); auth_clear()
        current_stage='exit'; settle(.8); send('/exit')
        process.wait(timeout=min(8,max(.2,deadline-time.monotonic())))
        if process.returncode!=0: raise RuntimeError('nonzero context exit')
        record(current_stage,'passed'); result=0
    except (OSError,RuntimeError,TimeoutError,subprocess.SubprocessError) as error:
        if isinstance(error,TerminalStateError): current_stage='terminal_state'
        record(current_stage,'failed')
    finally:
        try:
            _terminate(process)
        except (OSError,subprocess.SubprocessError):
            record('terminal_cleanup','failed'); result=2
        if capture is not None: capture.close()
        for descriptor in (master,slave):
            if descriptor is not None:
                try: os.close(descriptor)
                except OSError: pass
        try: state.close()
        except TerminalStateError:
            record('terminal_cleanup','failed'); result=2
    return result
