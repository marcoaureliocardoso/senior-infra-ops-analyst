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
from dataclasses import replace

from terminal_input_policy import TerminalInputPolicy
from terminal_state_adapter import TerminalStateError, MAX_CAPTURE
from terminal_structural_diagnostics import TerminalDiagnostics
from terminal_input_challenge import NonceInputChallenge, InputProofError, validate_probe_scope
from terminal_context_echo import begin_context_command, assess_context_input, validate_context_history, _invalidate_context_receipt
from terminal_context_diagnostics import _create_context_journal
from terminal_cancellation import TerminalCancelled


class _ContextFailure(RuntimeError):
    def __init__(self,reason):
        self.reason=reason
        super().__init__(reason)


def exit_input_owned(policy,snapshot,anchor,original_row,written,*,context_receipt=None,scope=None,state=None,
                     native_owner=None,transition_owner=None,frame=None):
    """Structure of the already-authorized fixed command, never a new IO grant."""
    def reject():
        if context_receipt is not None: _invalidate_context_receipt(context_receipt)
        return False
    bindings={'receipt':context_receipt,'scope':scope,'state':state,'native_owner':native_owner,
        'transition_owner':transition_owner,'frame':frame}
    if context_receipt is not None:
        try:
            validate_context_history(context_receipt,policy,snapshot,**{key:value for key,value in bindings.items()
                if key!='receipt'})
        except InputProofError: return reject()
    if type(written) is not int or not 0<=written<=5: return reject()
    if (snapshot.active!=anchor.buffer or snapshot.baseY!=anchor.baseY
            or snapshot.viewportY!=anchor.viewportY
            or snapshot.cursorY+snapshot.baseY-snapshot.viewportY!=anchor.row): return reject()
    row=snapshot.rows[anchor.row]; count=snapshot.cursorX-anchor.cursorX
    if not 0<=count<=written or row[:anchor.cursorX]!=original_row[:anchor.cursorX]: return reject()
    if any(cell.width!=1 or cell.text!='/exit'[index]
            for index,cell in enumerate(row[anchor.cursorX:anchor.cursorX+count])): return reject()
    if any(cell.width!=1 or cell.text not in ('',' ','\t','\u00a0')
            for cell in row[anchor.cursorX+count:]): return reject()
    rows=list(snapshot.rows); rows[anchor.row]=original_row
    normalized=replace(snapshot,cursorX=anchor.cursorX,rows=tuple(rows))
    try: valid=assess_context_input(policy,normalized,**bindings)[0].anchor==anchor
    except InputProofError: return reject()
    return True if valid else reject()


def _terminate(process):
    if process is None: return
    try: os.killpg(process.pid,signal.SIGTERM)
    except ProcessLookupError: pass
    try: process.wait(timeout=.2)
    except subprocess.TimeoutExpired: pass
    try: os.killpg(process.pid,signal.SIGKILL)
    except ProcessLookupError: pass
    process.wait(timeout=.5)


def drive_context(command,capture_path,timeout_seconds,events_path,startup_approval,state,*,writer,diagnostics=None,
                  input_probe_scope=None,context_debug=None):
    policy=TerminalInputPolicy()
    deadline=time.monotonic()+timeout_seconds
    process=None; master=slave=None; capture=None
    current_stage='initial_screen'; total=0; startup_open=True
    result=2; snapshot=None
    frame=0; probe=None; transition=None
    exit_written=0
    context_command=None; context_receipt=None
    context_journal=None; journal_active=False; controller_owner=object()
    numeric_context_observed=False
    if input_probe_scope is not None:
        deadline=min(deadline,validate_probe_scope(input_probe_scope,state))

    def journal_call(method,*args,**kwargs):
        if context_journal is None: return None
        try: return getattr(context_journal,method)(*args,**kwargs)
        except Exception:
            try: context_journal.finish()
            except Exception: pass
            return None

    def note_failure(error,check):
        if journal_active: journal_call('freeze',error,check)
        return error

    def command_error(reason,check):
        return note_failure(InputProofError(reason),check)

    def check_cancelled():
        try: state.check_cancelled()
        except TerminalCancelled as error:
            note_failure(error,'CANCELLATION'); raise

    def diagnose(point,reason='CHECKPOINT',*,structural=True,reap=None,input_eligibility=None,
                 input_row_relation=None,input_row_cause=None,context_command_failure=None):
        if type(diagnostics) is not TerminalDiagnostics: return
        try:
            fields={}
            if input_eligibility is not None: fields['inputEligibility']=input_eligibility
            if input_row_relation is not None: fields['inputRowRelation']=input_row_relation
            if input_row_cause is not None: fields['inputRowCause']=input_row_cause
            if context_command_failure is not None: fields['contextCommandFailure']=context_command_failure
            if structural and snapshot is not None: fields['structure']=policy.diagnostic_state(snapshot)
            if reap=='native': fields['leaderReaped']=process is not None and process.poll() is not None
            elif reap=='helper': fields['leaderReaped']=state.helper_reaped
        except Exception:
            # A producer failure can mark rejection if the collector is healthy.
            try: diagnostics.add('failure','DIAGNOSTIC_REJECTED')
            except Exception: pass
            return
        try: diagnostics.add(point,reason,**fields)
        except Exception:
            # Never retry an unavailable collector or interrupt operational cleanup.
            pass

    def record(stage,outcome,percent=None):
        if events_path is None: return
        value={'kind':'pty-driver','stage':stage,'outcome':outcome}
        if percent is not None: value['percent']=percent
        with events_path.open('a',encoding='utf-8') as stream:
            stream.write(json.dumps(value,sort_keys=True)+'\n')

    def exit_owned(written):
        return exit_input_owned(policy,snapshot,probe._anchor,probe._row,written,
            context_receipt=context_receipt,scope=input_probe_scope,state=state,native_owner=process,
            transition_owner=transition,frame=frame)

    def pump(wait=.2):
        nonlocal total,snapshot,current_stage,frame
        check_cancelled()
        readable,_,_=select.select([master],[],[],min(wait,max(0,deadline-time.monotonic())))
        if not readable: return False
        try: chunk=os.read(master,65536)
        except OSError: return False
        if not chunk: return False
        if total+len(chunk)>MAX_CAPTURE: raise RuntimeError('context capture limit')
        total+=len(chunk); capture.write(chunk)
        try: state.feed(chunk); snapshot=state.snapshot(); frame+=1
        except TerminalCancelled as error:
            note_failure(error,'CANCELLATION'); raise
        except TerminalStateError as error:
            if error.reason=='TERMINAL_DEADLINE_EXCEEDED': note_failure(error,'DEADLINE')
            raise
        authentication=policy.authentication(snapshot)
        if authentication and not startup_open:
            current_stage=authentication
            raise note_failure(RuntimeError('late authentication'),'AUTHENTICATION')
        if input_probe_scope is not None and not startup_open and policy.active_input_forbidden(snapshot):
            error=command_error('INPUT_PROBE_REVOKED','FORBIDDEN_UI')
            if probe is not None: probe.invalidate('INPUT_PROBE_REVOKED')
            if context_command is not None: context_command.invalidate('INPUT_PROBE_REVOKED')
            raise error
        if context_command is not None and probe is None: context_command.observe(snapshot,frame)
        if probe is not None:
            probe.observe(snapshot,frame)
            if probe.phase=='CONSUMED' and not exit_owned(exit_written):
                probe.invalidate('INPUT_PROBE_REVOKED')
                raise InputProofError('INPUT_PROBE_REVOKED')
        return True

    def wait_for(predicate):
        while time.monotonic()<deadline:
            pump()
            if predicate(): return
            if process.poll() is not None: raise _ContextFailure('PROCESS_EXITED')
        raise _ContextFailure('WAIT_DEADLINE')

    def settle(seconds=.4):
        quiet=time.monotonic()+seconds
        while time.monotonic()<deadline:
            if pump(min(.1,max(0,quiet-time.monotonic()))): quiet=time.monotonic()+seconds
            elif time.monotonic()>=quiet: return
        raise _ContextFailure('SETTLE_DEADLINE')

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
        raise note_failure(RuntimeError('startup authentication requires independent decision'),'AUTHENTICATION')

    def send(line):
        # Drain already-available redraws and re-evaluate immediately before IO.
        while pump(0): pass
        auth_clear()
        if not policy.ready(snapshot): raise _ContextFailure('INPUT_UNPROVEN')
        writer(master,line.encode('utf-8')+b'\r')

    def operation_live():
        check_cancelled()
        if time.monotonic()>=deadline: raise command_error('INPUT_PROBE_DEADLINE','DEADLINE')
        if process.poll() is not None: raise command_error('INPUT_PROBE_REVOKED','NATIVE_LIFETIME')
        if probe is not None: probe._check()

    def owned_write(payload,phase):
        nonlocal exit_written
        pending=memoryview(payload)
        written=0
        while pending:
            while pump(0): pass
            operation_live(); auth_clear()
            if probe.phase!=phase: raise InputProofError('INPUT_PROBE_STATE_REJECTED')
            if phase=='CONSUMED' and not exit_owned(written):
                raise InputProofError('INPUT_PROBE_REVOKED')
            if not select.select([], [master], [], min(.1,max(0,deadline-time.monotonic())))[1]: continue
            # Readiness/auth/deadline can change while waiting for writable IO.
            while pump(0): pass
            operation_live(); auth_clear()
            if probe.phase!=phase: raise InputProofError('INPUT_PROBE_STATE_REJECTED')
            if phase=='CONSUMED' and not exit_owned(written):
                raise InputProofError('INPUT_PROBE_REVOKED')
            try: count=os.write(master,pending)
            except BlockingIOError: continue
            except OSError: raise InputProofError('INPUT_PROBE_IO_FAILED') from None
            if not count: raise InputProofError('INPUT_PROBE_IO_FAILED')
            written+=count
            if phase=='CONSUMED': exit_written=written
            pending=pending[count:]

    def command_write(payload,*,submission=False):
        pending=memoryview(payload); written=0
        while pending:
            def check():
                operation_live(); auth_clear()
                if submission:
                    if context_command.observe(snapshot,frame)!='SUBMIT_PENDING':
                        raise command_error('INPUT_PROBE_STATE_REJECTED','PHASE_STATE')
                else: context_command.check_edit(snapshot,frame,written)
            while pump(0): pass
            check()
            if not select.select([], [master], [], min(.1,max(0,deadline-time.monotonic())))[1]: continue
            while pump(0): pass
            check()
            try: count=os.write(master,pending)
            except BlockingIOError: continue
            except OSError: raise command_error('INPUT_PROBE_IO_FAILED','IO_WRITE') from None
            if type(count) is not int or not 0<count<=len(pending):
                journal_call('acknowledge',count,submission=submission,remaining=len(pending))
                raise command_error('INPUT_PROBE_IO_FAILED','IO_WRITE')
            journal_call('acknowledge',count,submission=submission,remaining=len(pending))
            written+=count; pending=pending[count:]
            if submission: context_command.submission_written(count)
            else: context_command.check_edit(snapshot,frame,written)

    try:
        capture_path.parent.mkdir(parents=True,exist_ok=True)
        if events_path is not None:
            events_path.parent.mkdir(parents=True,exist_ok=True)
            events_path.write_text('',encoding='utf-8')
        snapshot=state.snapshot(); policy.mark_transition(snapshot)
        master,slave=pty.openpty()
        if input_probe_scope is not None: os.set_blocking(master,False)
        fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',40,120,0,0))
        state.check_cancelled()
        launch=state.cancellation.spawn if state.cancellation is not None else subprocess.Popen
        process=launch(command,stdin=slave,stdout=slave,stderr=slave,
            close_fds=True,start_new_session=True)
        os.close(slave); slave=None
        capture=capture_path.open('wb',buffering=0)
        wait_for(lambda: total>0); settle(); record('initial_screen','passed')
        diagnose('initial')
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
        if not policy.ready(snapshot): raise _ContextFailure('INPUT_UNPROVEN')
        record(current_stage,'passed'); startup_open=False
        diagnose('prompt_ready')
        if startup_approval is not None: startup_approval.revoke()
        current_stage='context_inspected'
        transition=object()
        # Check current input first, then establish the numeric observation barrier.
        if input_probe_scope is not None:
            try:
                context_journal=_create_context_journal(controller_owner=controller_owner,scope=input_probe_scope,
                    state=state,transition_owner=transition)
            except Exception: context_journal=None
            journal_active=True
            while pump(0): pass
            operation_live(); auth_clear()
            context_command=begin_context_command(input_probe_scope,state,process,transition,policy,snapshot,frame,
                _diagnostic_journal=context_journal)
            command_write(context_command.type_bytes(snapshot,frame))
            wait_for(lambda: context_command.phase=='COMMAND_ECHO_MATCHED')
            while pump(0): pass
            operation_live(); auth_clear()
            command_write(context_command.submit_bytes(snapshot,frame),submission=True)
        else:
            send('/context'); policy.mark_transition(snapshot)
        diagnose('context_sent')
        wait_for(lambda: policy.context_percent(snapshot) is not None)
        percentage=policy.context_percent(snapshot)
        record(current_stage,'passed',percentage)
        numeric_context_observed=True
        diagnose('context_numeric')
        if input_probe_scope is not None:
            while pump(0): pass
            operation_live(); auth_clear()
            context_receipt=context_command.bind_history(snapshot,frame)
            journal_active=False
            probe=NonceInputChallenge(input_probe_scope,process,transition,policy,snapshot,frame,
                context_receipt=context_receipt)
            owned_write(probe.type_bytes(snapshot,frame),'ECHO_PENDING')
            diagnose('input_probe_started',structural=False)
            wait_for(lambda: probe.phase=='ECHO_MATCHED')
            diagnose('input_probe_echo',structural=False)
            while pump(0): pass
            operation_live(); auth_clear()
            owned_write(probe.clear_bytes(snapshot,frame),'CLEAR_PENDING')
            wait_for(lambda: probe.phase=='PROVEN')
            diagnose('input_probe_cleared',structural=False)
        elif not policy.ready(snapshot):
            auth_clear(); policy.mark_transition(snapshot)
            writer(master,b'\x1b')
            diagnose('panel_close_sent')
            wait_for(lambda: policy.ready(snapshot)); settle(); auth_clear()
            diagnose('panel_closed')
        current_stage='exit'; settle(.8)
        if probe is not None:
            while pump(0): pass
            operation_live(); auth_clear()
            proof=probe.ownership_proof()
            if not probe.consume_exit(proof,snapshot,frame,process,transition):
                raise InputProofError('INPUT_PROBE_REVOKED')
            owned_write(b'/exit\r','CONSUMED')
        else: send('/exit')
        diagnose('exit_ready')
        process.wait(timeout=min(8,max(.2,deadline-time.monotonic())))
        if process.returncode!=0: raise RuntimeError('nonzero context exit')
        state.check_cancelled()
        record(current_stage,'passed'); result=0
    except (OSError,RuntimeError,TimeoutError,subprocess.SubprocessError) as error:
        if isinstance(error,TerminalStateError): current_stage='terminal_state'
        record(current_stage,'failed')
        reason=(error.reason if isinstance(error,(TerminalStateError,_ContextFailure,InputProofError)) else
            'EXIT_WAIT_DEADLINE' if isinstance(error,subprocess.TimeoutExpired) else
            'WAIT_DEADLINE' if isinstance(error,TimeoutError) else
            'IO_FAILED' if isinstance(error,OSError) else
            'SUBPROCESS_FAILED' if isinstance(error,subprocess.SubprocessError) else 'RUNTIME_REJECTED')
        metadata=({'input_eligibility':error.input_eligibility,'input_row_relation':error.input_row_relation,
            'input_row_cause':error.input_row_cause} if isinstance(error,InputProofError) else {})
        metadata['context_command_failure']=journal_call('project',error,controller_owner=controller_owner,
            scope=input_probe_scope,state=state,transition_owner=transition)
        diagnose('failure',reason,**metadata)
        if context_debug is not None:
            try:
                context_debug.capture(state,input_probe_scope,snapshot,error,numeric_context=numeric_context_observed)
            except (OSError,RuntimeError,ValueError,TypeError,AttributeError): pass
    finally:
        journal_call('finish')
        if probe is not None: probe.invalidate('INPUT_PROBE_REVOKED')
        if context_command is not None: context_command.invalidate('INPUT_PROBE_REVOKED')
        if startup_approval is not None: startup_approval.revoke()
        native_cleanup='CLEANUP_COMPLETED'
        try:
            if process is not None and state.cancellation is not None:
                state.cancellation.terminate_child(process)
            else: _terminate(process)
        except (OSError,RuntimeError,subprocess.SubprocessError):
            record('terminal_cleanup','failed'); result=2
            native_cleanup='NATIVE_CLEANUP_FAILED'
        diagnose('native_cleanup',native_cleanup,structural=False,reap='native')
        if capture is not None: capture.close()
        for descriptor in (master,slave):
            if descriptor is not None:
                try: os.close(descriptor)
                except OSError: pass
        helper_cleanup='CLEANUP_COMPLETED'
        try: state.close()
        except TerminalStateError as error:
            record('terminal_cleanup','failed'); result=2
            helper_cleanup=error.reason
        diagnose('helper_cleanup',helper_cleanup,structural=False,reap='helper')
    return result
