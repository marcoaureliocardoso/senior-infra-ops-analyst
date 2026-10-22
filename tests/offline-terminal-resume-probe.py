#!/usr/bin/env python3
"""Offline-only native regression. No operator settings, key or real provider."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import selectors
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from terminal_cancellation import TerminalCancellation, TerminalCancelled
from terminal_structural_diagnostics import TerminalDiagnostics
from terminal_input_challenge import audit_offline_namespace, create_offline_probe_issuer, InputProofError, validate_probe_scope


FAILURE_PHASES=frozenset(('PRECHECK','NAMESPACE','IMPORTS','VERSION','INITIAL_CONTEXT',
    'SDK','RESUMED_CONTEXT','CLEANUP','UNKNOWN'))
_EXCEPTION_TYPES=(json.JSONDecodeError,subprocess.TimeoutExpired,subprocess.CalledProcessError,
    PermissionError,FileNotFoundError,TimeoutError,OSError,ModuleNotFoundError,ImportError,
    ValueError,TypeError,RuntimeError)
_EXCEPTION_LABELS=frozenset(kind.__name__ for kind in _EXCEPTION_TYPES)|{'OTHER'}


def _failure_diagnostic(phase,*,error=None,exit_code=None):
    code=exit_code if type(exit_code) is int and -255<=exit_code<=255 else None
    label=next((kind.__name__ for kind in _EXCEPTION_TYPES if isinstance(error,kind)),
        'OTHER' if error is not None else None)
    number=getattr(error,'errno',None) if isinstance(error,OSError) else None
    return {'phase':phase if type(phase) is str and phase in FAILURE_PHASES else 'UNKNOWN',
        'exitCode':code,'signal':-code if code is not None and code<0 else None,
        'exceptionClass':label,'errno':number if type(number) is int and 0<=number<=4095 else None}


def _valid_failure_diagnostic(value):
    if type(value) is not dict or set(value)!={'phase','exitCode','signal','exceptionClass','errno'}: return False
    phase,code,signal_number,label,number=(value[key] for key in ('phase','exitCode','signal','exceptionClass','errno'))
    if type(phase) is not str or phase not in FAILURE_PHASES: return False
    if code is not None and (type(code) is not int or not -255<=code<=255): return False
    if signal_number is not None and type(signal_number) is not int: return False
    if signal_number!=(-code if code is not None and code<0 else None): return False
    if label is not None and (type(label) is not str or label not in _EXCEPTION_LABELS): return False
    return number is None or (type(number) is int and 0<=number<=4095)


def _failed(report,phase,*,enabled,error=None,exit_code=None):
    return {**report,'failureDiagnostic':_failure_diagnostic(phase,error=error,exit_code=exit_code)} if enabled else report


def _bounded_standard_report(report,exit_code,*,reserve_disposal=False):
    cases=report.get('cases',[])
    records=[report]+([case for case in cases if type(case) is dict] if type(cases) is list else [])
    success=report.get('reasonCode')=='OFFLINE_CONTROLS_PASSED'
    for record in records:
        if 'failureDiagnostic' in record and (success or not _valid_failure_diagnostic(record['failureDiagnostic'])):
            record.pop('failureDiagnostic')
    def size():
        envelope={**report,'disposableRootAbsent':True} if reserve_disposal else report
        return len((json.dumps(envelope,sort_keys=True)+'\n').encode())
    if size()>16384:
        # Optional observation must be sacrificed before the existing result.
        for record in records: record.pop('failureDiagnostic',None)
    if size()>16384:
        return _failed({'reasonCode':'OFFLINE_PROBE_BLOCKED',
            'disposableRootAbsent':report.get('disposableRootAbsent') is True},
            'NAMESPACE',enabled=True,error=ValueError(),exit_code=exit_code)
    return report


class _OfflineFailure(Exception):
    def __init__(self,phase,error):
        self.diagnostic=_failure_diagnostic(phase,error=error)
        super().__init__('OFFLINE_PROBE_BLOCKED')


def context_stage_report(phase,rows,diagnostics):
    """Separate structural diagnostics from the unchanged reduced proof stream."""
    reduced=[{key:row[key] for key in ('stage','outcome','percent') if key in row} for row in rows]
    return {'phase':phase,'events':reduced,'diagnostics':diagnostics.report()}


def validate_mode(arguments):
    return arguments in (['--run-offline'],['--audit-isolation'],['--run-offline','--debug-context'],
                         ['--run-offline','--debug-context-edit'],['--observe-post-enter'])


def _new_post_enter_report(outcome='SETUP_BLOCKED',category='SETUP'):
    return {'schema':'p004b-post-enter-observation-v1','mode':'observe-post-enter','acceptance':False,
        'outcome':outcome,'stopCategory':category,'setup':{'initialCompleted':False,'sdkValidated':False},
        'cleanup':{'nativeReaped':False,'helperReaped':False,'caseRootAbsent':False,'disposableRootAbsent':False}}


def _known_post_enter_cleanup_failure(value):
    if type(value) is not dict: return False
    template=_new_post_enter_report()
    for key in ('setup','cleanup'):
        fields=value.get(key)
        if (type(fields) is not dict or set(fields)!=set(template[key])
                or any(type(item) is not bool for item in fields.values())): return False
    # False in a setup-blocked envelope means unobserved, not an invented
    # cleanup failure. Once setup or observation occurred, all child cleanup
    # proofs are required for either a positive or a negative observation.
    occurred=any(value['setup'].values()) or 'summary' in value
    return occurred and not all(value['cleanup'][key]
        for key in ('nativeReaped','helperReaped','caseRootAbsent'))


def valid_post_enter_report(value):
    from terminal_post_enter_observation import OUTCOMES,STOP_CATEGORIES,valid_observation_summary
    keys={'schema','mode','acceptance','outcome','stopCategory','setup','cleanup'}
    if type(value) is not dict or not keys<=set(value)<=keys|{'summary'}: return False
    if (value['schema']!='p004b-post-enter-observation-v1' or value['mode']!='observe-post-enter'
            or value['acceptance'] is not False or type(value['outcome']) is not str or value['outcome'] not in OUTCOMES
            or type(value['stopCategory']) is not str or value['stopCategory'] not in STOP_CATEGORIES): return False
    for name,fields in (('setup',{'initialCompleted','sdkValidated'}),
            ('cleanup',{'nativeReaped','helperReaped','caseRootAbsent','disposableRootAbsent'})):
        if (type(value[name]) is not dict or set(value[name])!=fields
                or any(type(item) is not bool for item in value[name].values())): return False
    if _known_post_enter_cleanup_failure(value) and not (
            value['outcome']=='CLEANUP_FAILED' and value['stopCategory']=='CLEANUP' and 'summary' not in value): return False
    if 'summary' in value:
        summary=value['summary']
        if (not valid_observation_summary(summary) or summary['outcome']!=value['outcome']
                or summary['stopCategory']!=value['stopCategory'] or not all(value['setup'].values())): return False
        if len((json.dumps(summary,sort_keys=True)+'\n').encode())>3072: return False
    if value['outcome']=='CURRENT_PROFILE_OBSERVED':
        return ('summary' in value and value['stopCategory']=='COMPLETE'
            and all(value['cleanup'][key] for key in ('nativeReaped','helperReaped','caseRootAbsent')))
    return not (value['outcome']=='CLEANUP_FAILED' and ('summary' in value or value['stopCategory']!='CLEANUP'))


def fit_post_enter_report(value,*,reserve_disposal=False):
    report=dict(value) if type(value) is dict else _new_post_enter_report('SAFETY_STOP','REPORT')
    if not valid_post_enter_report(report):
        original=report; report=_new_post_enter_report('SAFETY_STOP','REPORT')
        for key in ('setup','cleanup'):
            candidate=original.get(key)
            if (type(candidate) is dict and set(candidate)==set(report[key])
                    and all(type(item) is bool for item in candidate.values())): report[key]=dict(candidate)
        summary=original.get('summary')
        # An invalid optional annotation must not erase an independent negative.
        reduced={key:item for key,item in original.items() if key!='summary'}
        if summary is not None and valid_post_enter_report(reduced): report=reduced
    if _known_post_enter_cleanup_failure(value):
        report={**_new_post_enter_report('CLEANUP_FAILED','CLEANUP'),
            'setup':dict(value['setup']),'cleanup':dict(value['cleanup'])}
    size_report={**report,'cleanup':{**report['cleanup'],
        'disposableRootAbsent':True if reserve_disposal else report['cleanup']['disposableRootAbsent']}}
    if len((json.dumps(size_report,sort_keys=True)+'\n').encode())>16384:
        return _new_post_enter_report('SAFETY_STOP','REPORT')
    return report


def _post_enter_child_code(report):
    return 0 if (valid_post_enter_report(report) and report['outcome']=='CURRENT_PROFILE_OBSERVED'
        and all(report['setup'].values()) and all(report['cleanup'][key]
            for key in ('nativeReaped','helperReaped','caseRootAbsent'))) else 2


def post_enter_exit_code(report):
    return 0 if _post_enter_child_code(report)==0 and report['cleanup']['disposableRootAbsent'] is True else 2


def case_complete(case):
    if type(case) is not dict or 'schema' in case or 'acceptance' in case: return False
    required=(all(type(case.get(key)) is int and case[key]==0 for key in ('beforeExit','sdkExit','afterExit'))
        and case.get('contextInspected') is True and case.get('naturalExit') is True
        and case.get('caseRootAbsent') is True and case.get('validSDKSample') is True)
    stages=case.get('stages')
    if not required or type(stages) is not list or len(stages)!=2: return False
    for phase,stage in zip(('before','after'),stages):
        if type(stage) is not dict or stage.get('phase')!=phase: return False
        diagnostics=stage.get('diagnostics')
        if (type(diagnostics) is not dict or diagnostics.get('rejected') is not False
                or diagnostics.get('truncated') is not False or type(diagnostics.get('records')) is not list): return False
        rows=diagnostics['records']
        # Serialized observations cannot mint a capability, but missing or forged
        # required evidence must still withhold aggregate success.
        replay=TerminalDiagnostics()
        for row in rows:
            if (type(row) is not dict or not {'point','reasonCode'}<=set(row)
                    or any(type(key) is not str for key in row)): return False
            replay.add(row['point'],row['reasonCode'],
                **{key:value for key,value in row.items() if key not in ('point','reasonCode')})
        if replay.report()!=diagnostics: return False
        display=[index for index,row in enumerate(rows) if row['point']=='context_display']
        if phase=='before' and display: return False
        if phase=='after':
            started=[index for index,row in enumerate(rows) if row['point']=='input_probe_started']
            if len(display)!=1 or len(started)!=1 or display[0]>=started[0]: return False
        for point in ('input_probe_started','input_probe_echo','input_probe_cleared','native_cleanup','helper_cleanup'):
            matches=[row for row in rows if type(row) is dict and row.get('point')==point]
            if len(matches)!=1: return False
            if point.endswith('_cleanup'):
                if matches[0].get('reasonCode')!='CLEANUP_COMPLETED' or matches[0].get('leaderReaped') is not True: return False
            elif matches[0].get('reasonCode')!='CHECKPOINT': return False
        events=stage.get('events')
        if type(events) is not list or any(not any(type(event) is dict and event.get('stage')==step
                and event.get('outcome')=='passed' for event in events) for step in ('context_inspected','exit')): return False
    return (type(case.get('skillCalls')) is int and
        ((case.get('case')=='text-turn' and case['skillCalls']==0) or
         (case.get('case')=='skill-turn' and case.get('validSkillSample') is True and case['skillCalls']==1)))


def finalize_owned(root,identity,report):
    try:
        current=root.lstat()
        if (not stat.S_ISDIR(current.st_mode) or current.st_uid!=os.getuid()
                or current.st_dev!=identity.st_dev or current.st_ino!=identity.st_ino
                or not shutil.rmtree.avoids_symlink_attacks): raise ValueError
        shutil.rmtree(root)
        if root.exists() or root.is_symlink(): raise ValueError
    except (OSError,ValueError): return {'reasonCode':'OFFLINE_CLEANUP_FAILED'}
    return {**report,'disposableRootAbsent':True}


def _audit():
    try: return audit_offline_namespace()
    except InputProofError: raise ValueError from None


def audit_input_probe_scope(node,module_root):
    """Audit-only seam: no Claude mount/launch, no PTY or synthetic submission."""
    from terminal_state_adapter import TerminalState
    issuer=create_offline_probe_issuer()
    state=TerminalState(node,module_root,time.monotonic()+5)
    try:
        scope=issuer.issue_scope(state,object())
        if validate_probe_scope(scope,state)!=state.operation_deadline: raise ValueError
        try: issuer.issue_scope(state,object())
        except InputProofError: pass
        else: raise ValueError
    finally: state.close()


def _read_edit_namespace(command,*,cancellation,deadline):
    if time.monotonic()>=deadline: raise TimeoutError
    process=cancellation.spawn(command,env={'PATH':'/usr/bin:/bin'},stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,start_new_session=True)
    data=bytearray(); eof=False
    try:
        descriptor=process.stdout.fileno(); os.set_blocking(descriptor,False)
        with selectors.DefaultSelector() as selector:
            selector.register(descriptor,selectors.EVENT_READ)
            while True:
                cancellation.check()
                remaining=deadline-time.monotonic()
                if remaining<=0: raise TimeoutError
                if eof and process.poll() is not None:
                    cancellation.terminate_child(process)
                    cancellation.check()
                    if time.monotonic()>=deadline: raise TimeoutError
                    return process.returncode,bytes(data)
                for _key,_events in selector.select(min(.02,remaining)):
                    try: chunk=os.read(descriptor,16385-len(data))
                    except BlockingIOError: continue
                    if not chunk:
                        eof=True; selector.unregister(descriptor); break
                    data.extend(chunk)
                    if len(data)>16384: raise ValueError('offline report limit')
    finally:
        data.clear()
        if process.stdout is not None: process.stdout.close()


def _edit_json(data):
    def pairs(items):
        result={}
        for key,value in items:
            if key in result: raise ValueError('duplicate offline field')
            result[key]=value
        return result
    def constant(_value): raise ValueError('invalid offline value')
    return json.loads(data.decode('utf-8'),object_pairs_hook=pairs,parse_constant=constant)


def _edit_namespace_report(command,root,identity):
    from terminal_context_debug import _valid_edit_base, finalize_edit_report
    report={'reasonCode':'OFFLINE_PROBE_BLOCKED'}; pending={'status':'NO_CAPTURE'}
    cleaned=None; namespace_reaped=False; cancellation=TerminalCancellation()
    deadline=time.monotonic()+165
    def live(*,active=False):
        if active: cancellation.check()
        elif cancellation.requested: raise TerminalCancelled()
        if time.monotonic()>=deadline: raise TimeoutError
    try:
        with cancellation:
            try:
                code,data=_read_edit_namespace(command,cancellation=cancellation,deadline=deadline)
                if code: raise ValueError
                parsed=_edit_json(data)
                if type(parsed) is not dict: raise ValueError
                pending=parsed.pop('_pendingContextEdit',{'status':'NO_CAPTURE'})
                if not _valid_edit_base(parsed): raise ValueError
                report=parsed
                live(active=True)
            except (KeyboardInterrupt,TerminalCancelled):
                report={'reasonCode':'OFFLINE_PROBE_INTERRUPTED'}; pending={'status':'OMITTED_SCOPE'}
            except (OSError,ValueError,TypeError,RuntimeError,UnicodeError,subprocess.SubprocessError):
                report={'reasonCode':'OFFLINE_PROBE_BLOCKED'}; pending={'status':'OMITTED_PROVENANCE'}
            finally:
                # Reader disposal precedes root removal; keep handlers active during cleanup.
                with cancellation.cleanup(): cleaned=finalize_owned(root,identity,report)
            live(active=True)
        namespace_reaped=True
        live()
        disposed=cleaned.pop('disposableRootAbsent',False)
        public=finalize_edit_report(cleaned,pending,disposal_proven=disposed is True)
        live()
        return public
    except (KeyboardInterrupt,TerminalCancelled):
        reason='OFFLINE_PROBE_INTERRUPTED'
    except (OSError,ValueError,TypeError,RuntimeError,UnicodeError,subprocess.SubprocessError):
        reason='OFFLINE_PROBE_BLOCKED'
    if cleaned is None: cleaned=finalize_owned(root,identity,{'reasonCode':reason})
    disposed=cleaned.pop('disposableRootAbsent',False)
    if cleaned.get('reasonCode')!='OFFLINE_CLEANUP_FAILED': cleaned={'reasonCode':reason}
    return finalize_edit_report(cleaned,{'status':'OMITTED_SCOPE'},
        disposal_proven=disposed is True and namespace_reaped)


def _post_enter_namespace_report(command,root,identity,*,deadline=None):
    # Reuse only the bounded pipe reader, not the edit-debug capture/export path.
    hard_deadline=time.monotonic()+165 if deadline is None else deadline
    report=_new_post_enter_report(); reaped=False; cleaned=None
    cancellation=TerminalCancellation(); entered=False
    try:
        with cancellation:
            entered=True
            try:
                code,data=_read_edit_namespace(command,cancellation=cancellation,deadline=hard_deadline-5)
                value=_edit_json(data)
                cleanup_failure=_known_post_enter_cleanup_failure(value)
                if cleanup_failure: value=fit_post_enter_report(value)
                if (not valid_post_enter_report(value) or value['cleanup']['disposableRootAbsent'] is not False
                        or type(code) is not int or code not in (0,2)
                        or (not cleanup_failure and code!=_post_enter_child_code(value))):
                    raise ValueError
                report=value
                cancellation.check()
            except (KeyboardInterrupt,TerminalCancelled):
                report=_new_post_enter_report('SAFETY_STOP','CANCELLED')
            except (OSError,ValueError,TypeError,RuntimeError,UnicodeError,subprocess.SubprocessError):
                report=_new_post_enter_report('SAFETY_STOP','CAPTURE_PROTOCOL')
            finally:
                # Reap the entire owned cohort before removing raw storage.
                # Keep the signal latch installed, but defer interruption of
                # disposal itself. No new process or input authority is issued.
                with cancellation.cleanup():
                    cancellation._dispose()
                    reaped=True
                    cleaned=finalize_owned(root,identity,report)
            cancellation.check()
            if time.monotonic()>=hard_deadline: raise TimeoutError
    except (KeyboardInterrupt,TerminalCancelled):
        report=_new_post_enter_report('SAFETY_STOP','CANCELLED')
    except TimeoutError:
        report=_new_post_enter_report('DEADLINE','DEADLINE')
    except (OSError,ValueError,RuntimeError,KeyboardInterrupt,TerminalCancelled):
        report=_new_post_enter_report('CLEANUP_FAILED','CLEANUP')
    if not entered:
        # No namespace child could have been spawned when setup was rejected.
        cleaned=finalize_owned(root,identity,report)
    disposed=type(cleaned) is dict and cleaned.get('disposableRootAbsent') is True
    if not disposed or not reaped:
        failed=_new_post_enter_report('CLEANUP_FAILED','CLEANUP')
        failed['cleanup']['disposableRootAbsent']=disposed
        return failed
    if cancellation.requested: report=_new_post_enter_report('SAFETY_STOP','CANCELLED')
    report['cleanup']={**report['cleanup'],'disposableRootAbsent':True}
    return fit_post_enter_report(report)


def _acceptance_namespace_report(command,root,identity,*,deadline):
    """Own ordinary acceptance until its final checked, disposed result."""
    cancellation=TerminalCancellation(); entered=False; reaped=False; closed=False
    report={'reasonCode':'OFFLINE_PROBE_BLOCKED'}; cleaned=None; exit_code=None
    cleanup_error=None
    errors=(OSError,ValueError,TypeError,RuntimeError,UnicodeError,subprocess.SubprocessError)

    def live(*,work=False):
        cancellation.check()
        if time.monotonic()>=(deadline-5 if work else deadline): raise TimeoutError

    def rejected(error):
        reason='OFFLINE_PROBE_INTERRUPTED' if isinstance(error,(KeyboardInterrupt,TerminalCancelled)) else 'OFFLINE_PROBE_BLOCKED'
        return _failed({'reasonCode':reason},'NAMESPACE',enabled=True,error=error,exit_code=exit_code)

    try:
        with cancellation:
            entered=True
            try:
                live(work=True)
                with tempfile.TemporaryFile(dir=root) as output:
                    result=cancellation.spawn(command,env={'PATH':'/usr/bin:/bin'},stdin=subprocess.DEVNULL,
                        stdout=output,stderr=subprocess.DEVNULL,start_new_session=True)
                    while result.poll() is None:
                        live(work=True)
                        time.sleep(.02)
                    live(work=True)
                    exit_code=result.returncode
                    output.seek(0); data=output.read(16385)
                    live(work=True)
                    if exit_code:
                        report=_failed(report,'NAMESPACE',enabled=True,exit_code=exit_code)
                        # A failed child cannot make its success claim authoritative.
                        if len(data)<=16384:
                            try:
                                value=_edit_json(data)
                                detail=value.get('failureDiagnostic') if type(value) is dict else None
                                if _valid_failure_diagnostic(detail): report['failureDiagnostic']=dict(detail)
                            except (ValueError,UnicodeError): pass
                    else:
                        if len(data)>16384: raise ValueError
                        value=json.loads(data)
                        if type(value) is not dict: raise ValueError
                        report=value
                    live(work=True)
            except (KeyboardInterrupt,TerminalCancelled) as error:
                report=rejected(error)
            except errors as error:
                report=rejected(error)
            finally:
                data=b''
                # Cancellation is latched, not acted on between reap and disposal.
                # The capture handle above is already closed on every path.
                with cancellation.cleanup():
                    try:
                        cancellation._dispose()
                        reaped=True
                        cleaned=finalize_owned(root,identity,report)
                    except (KeyboardInterrupt,*errors) as error:
                        cleanup_error=error
            if type(cleaned) is dict:
                report=_bounded_standard_report(cleaned,exit_code)
            try: live()
            except (KeyboardInterrupt,*errors) as error: report=rejected(error)
        closed=True
    except (KeyboardInterrupt,TerminalCancelled) as error:
        report=rejected(error)
        if entered: cleanup_error=error
        closed=not cancellation._entered
    except errors as error:
        report=rejected(error)
        if entered: cleanup_error=error
        closed=not cancellation._entered
    if not entered:
        # Entry rejection cannot have spawned a child; still remove owned storage.
        cleaned=finalize_owned(root,identity,report)
        reaped=True
    disposed=type(cleaned) is dict and cleaned.get('disposableRootAbsent') is True
    if (cleanup_error is not None or not reaped or not closed or not disposed
            or cleaned.get('reasonCode')=='OFFLINE_CLEANUP_FAILED'):
        failed=_failed({'reasonCode':'OFFLINE_CLEANUP_FAILED'},'CLEANUP',enabled=True,error=cleanup_error)
        if disposed: failed['disposableRootAbsent']=True
        return failed  # Fixed closed fields only; no content-bearing fit after teardown.
    # Teardown can latch a request after the last in-context check. This is the
    # checked return boundary, not an atomic transaction with a caller's stdout.
    if cancellation.requested: report=rejected(TerminalCancelled())
    elif time.monotonic()>=deadline: report=rejected(TimeoutError())
    # Ordinary reports were already fitted with disposal under supervision;
    # replacements contain only fixed closed fields and the bounded diagnostic.
    return {**report,'disposableRootAbsent':True}


def _namespace(*,source,node,module_root,claude=None,audit=False,debug_context=False,debug_context_edit=False,post_enter_observation=False):
    outer_deadline=time.monotonic()+165 if post_enter_observation is True else None
    if (type(post_enter_observation) is not bool or (post_enter_observation and
            (audit or debug_context is not False or debug_context_edit is not False))):
        return _new_post_enter_report()
    observe=not audit and debug_context is False and debug_context_edit is False and not post_enter_observation
    if observe: outer_deadline=time.monotonic()+165
    if (type(debug_context_edit) is not bool or (debug_context_edit and (audit or debug_context))):
        return {'reasonCode':'OFFLINE_PROBE_BLOCKED'}
    if type(debug_context) is not bool or (audit and debug_context): return {'reasonCode':'OFFLINE_PROBE_BLOCKED'}
    try:
        source=source.resolve(strict=True); node=node.resolve(strict=True); module_root=module_root.resolve(strict=True)
        bwrap=shutil.which('bwrap')
        if not bwrap or not node.is_file(): raise ValueError
    except (OSError,ValueError) as error:
        return _new_post_enter_report() if post_enter_observation else _failed({'reasonCode':'OFFLINE_PROBE_BLOCKED'},'PRECHECK',enabled=observe,error=error)
    root=Path(tempfile.mkdtemp(prefix='p004b-offline-terminal-'))
    identity=root.stat()
    report=_new_post_enter_report() if post_enter_observation else {'reasonCode':'OFFLINE_PROBE_BLOCKED'}
    phase='PRECHECK'; exit_code=None
    pending={'status':'NO_CAPTURE'}; namespace_reaped=False
    try:
        command=[bwrap,'--die-with-parent','--new-session','--unshare-user','--unshare-pid',
            '--unshare-ipc','--unshare-uts','--unshare-net','--cap-drop','ALL',
            '--ro-bind','/usr','/usr','--symlink','usr/bin','/bin','--symlink','usr/sbin','/sbin',
            '--symlink','usr/lib','/lib','--symlink','usr/lib64','/lib64','--dev','/dev','--proc','/proc',
            '--dir','/opt','--dir','/opt/probe','--dir','/opt/modules','--dir','/opt/modules/@xterm',
            '--dir','/etc','--dir','/home','--dir','/root','--dir','/run','--dir','/tmp','--dir','/mnt',
            '--dir','/var','--dir','/var/tmp','--bind',str(root),'/work','--chdir','/work',
            '--ro-bind',str(Path(__file__).resolve()),'/opt/probe/probe.py',
            '--ro-bind',str(node),'/opt/probe/node',
            '--ro-bind',str(module_root/'@xterm/headless'),'/opt/modules/@xterm/headless',
            '--ro-bind',str(source/'skills/context-continuity'),'/opt/skill',
            '--dir','/opt/probe/terminal-runtime',
            '--ro-bind',str(source/'tests/terminal-runtime/package-lock.json'),'/opt/probe/terminal-runtime/package-lock.json']
        for name in ('claude-pty-driver.py','headless_context_driver.py','terminal_input_policy.py','terminal_cancellation.py',
                     'terminal_context_sample.py',
                     'terminal_input_challenge.py',
                     'terminal_resume_history.py',
                     'terminal_nonce_history_diagnostics.py',
                     'terminal_context_debug.py',
                     'terminal_context_echo.py',
                     'terminal_context_diagnostics.py',
                     'terminal_structural_diagnostics.py',
                     'terminal_state_adapter.py','terminal-state-adapter.mjs','browser_startup_approval.py',
                     'browser_operations_live.py'):
            command += ['--ro-bind',str(source/'tests'/name),'/opt/probe/'+name]
        if post_enter_observation:
            command += ['--ro-bind',str(source/'tests/terminal_post_enter_observation.py'),'/opt/probe/terminal_post_enter_observation.py']
        if not audit:
            claude=claude.resolve(strict=True)
            if not claude.is_file(): raise ValueError
            command += ['--ro-bind',str(claude),'/opt/probe/claude']
        command += ['--clearenv','--setenv','PATH','/usr/bin:/bin','--setenv','PYTHONDONTWRITEBYTECODE','1',
            '/usr/bin/python3','/opt/probe/probe.py','--inner-audit' if audit else
                '--inner-controls-debug' if debug_context else '--inner-controls-edit-debug' if debug_context_edit else
                '--inner-post-enter-observation' if post_enter_observation else '--inner-controls']
        if debug_context_edit:
            return _edit_namespace_report(command,root,identity)
        if post_enter_observation:
            return _post_enter_namespace_report(command,root,identity,deadline=outer_deadline)
        if observe:
            return _acceptance_namespace_report(command,root,identity,deadline=outer_deadline)
        else:
            phase='NAMESPACE'
            with TerminalCancellation() as cancellation, tempfile.TemporaryFile(dir=root) as output:
                deadline=time.monotonic()+165
                result=cancellation.spawn(command,env={'PATH':'/usr/bin:/bin'},stdin=subprocess.DEVNULL,
                    stdout=output,stderr=subprocess.DEVNULL,start_new_session=True)
                while result.poll() is None:
                    cancellation.check()
                    if time.monotonic()>=deadline: raise TimeoutError
                    time.sleep(.02)
                cancellation.check()
                output.seek(0); data=output.read(16385)
            exit_code=result.returncode
            if exit_code:
                report=_failed(report,'NAMESPACE',enabled=observe,exit_code=exit_code)
                # A child failure stays blocked, even if its JSON claims success.
                # Only closed passive metadata survives a nonzero namespace exit.
                if observe and len(data)<=16384:
                    try:
                        value=_edit_json(data)
                        detail=value.get('failureDiagnostic') if type(value) is dict else None
                        if _valid_failure_diagnostic(detail): report['failureDiagnostic']=dict(detail)
                    except (ValueError,UnicodeError): pass
            else:
                if len(data)>16384: raise ValueError
                value=json.loads(data)
                if observe and type(value) is not dict: raise ValueError
                report=value
                if observe and type(report) is dict and 'failureDiagnostic' in report:
                    if not _valid_failure_diagnostic(report['failureDiagnostic']): report.pop('failureDiagnostic')
    except (KeyboardInterrupt,TerminalCancelled) as error:
        report=(_new_post_enter_report('SAFETY_STOP','CANCELLED') if post_enter_observation else
            _failed({'reasonCode':'OFFLINE_PROBE_INTERRUPTED'},phase,enabled=observe,error=error,exit_code=exit_code))
    except (OSError,ValueError,TypeError,RuntimeError,UnicodeError,subprocess.SubprocessError) as error:
        report=(_new_post_enter_report('SAFETY_STOP','CAPTURE_PROTOCOL') if post_enter_observation else
            _failed(report,phase,enabled=observe,error=error,exit_code=exit_code))
        if debug_context_edit:
            report={'reasonCode':'OFFLINE_PROBE_BLOCKED'}; pending={'status':'OMITTED_PROVENANCE'}
    cleaned=finalize_owned(root,identity,report)
    if post_enter_observation:
        disposed=cleaned.pop('disposableRootAbsent',False) is True
        if not disposed:
            failed=_new_post_enter_report('CLEANUP_FAILED','CLEANUP')
            failed['cleanup']['disposableRootAbsent']=disposed
            return failed
        report['cleanup']={**report['cleanup'],'disposableRootAbsent':True}
        return fit_post_enter_report(report)
    if cleaned.get('reasonCode')=='OFFLINE_CLEANUP_FAILED':
        cleaned=_failed(cleaned,'CLEANUP',enabled=observe)
    if debug_context_edit:
        from terminal_context_debug import finalize_edit_report
        disposed=cleaned.pop('disposableRootAbsent',False)
        return finalize_edit_report(cleaned,pending,disposal_proven=disposed is True and namespace_reaped)
    return _bounded_standard_report(cleaned,exit_code) if observe else cleaned


def run_isolation_audit(*,source,node,module_root):
    return _namespace(source=source,node=node,module_root=module_root,audit=True)


def run_offline_controls(*,source,claude,node,module_root,debug_context=False,debug_context_edit=False):
    if claude is None:
        return _failed({'reasonCode':'OFFLINE_PROBE_BLOCKED'},'PRECHECK',
            enabled=debug_context is False and debug_context_edit is False)
    return _namespace(source=source,claude=claude,node=node,module_root=module_root,debug_context=debug_context,
        debug_context_edit=debug_context_edit)


def run_post_enter_observation(*,source,claude,node,module_root):
    if claude is None: return _new_post_enter_report()
    return _namespace(source=source,claude=claude,node=node,module_root=module_root,post_enter_observation=True)


def run_cases(run_case):
    cases=[]
    for name in ('text-turn','skill-turn'):
        case=run_case(name); cases.append(case)
        if not case_complete(case):
            return {'reasonCode':'OFFLINE_CONTROLS_INCONCLUSIVE','cases':cases}
    return {'reasonCode':'OFFLINE_CONTROLS_PASSED','cases':cases}


def _post_enter_case_report(case):
    report=_new_post_enter_report()
    stages=case.get('stages',[])
    initial=(type(case.get('beforeExit')) is int and case['beforeExit']==0 and bool(stages)
        and all(any(row.get('stage')==point and row.get('outcome')=='passed'
            for row in stages[0].get('events',[])) for point in ('context_inspected','exit')))
    report['setup']={'initialCompleted':initial,'sdkValidated':case.get('validSDKSample') is True}
    for key,point in (('nativeReaped','native_cleanup'),('helperReaped','helper_cleanup')):
        report['cleanup'][key]=bool(stages) and all(any(row.get('point')==point and
            row.get('reasonCode')=='CLEANUP_COMPLETED' and row.get('leaderReaped') is True
            for row in stage['diagnostics']['records']) for stage in stages)
    report['cleanup']['caseRootAbsent']=case.get('caseRootAbsent') is True
    summary=case.get('observationSummary')
    from terminal_post_enter_observation import valid_observation_summary
    if summary is not None and valid_observation_summary(summary):
        report.update(summary=summary,outcome=summary['outcome'],stopCategory=summary['stopCategory'])
    elif all(report['setup'].values()): report.update(outcome='SAFETY_STOP',stopCategory='REPORT')
    if not all(report['cleanup'][key] for key in ('nativeReaped','helperReaped','caseRootAbsent')):
        report.update(outcome='CLEANUP_FAILED',stopCategory='CLEANUP'); report.pop('summary',None)
    if case.get('afterExit')!=0 and report['outcome']=='CURRENT_PROFILE_OBSERVED':
        report.update(outcome='SAFETY_STOP',stopCategory='REPORT'); report.pop('summary',None)
    return fit_post_enter_report(report,reserve_disposal=True)


def _controls(*,debug_context=False,debug_context_edit=False,post_enter_observation=False):
    observe=not debug_context and not debug_context_edit
    sys.path.insert(0,'/opt/probe')
    try:
        from terminal_state_adapter import TerminalState
        from browser_startup_approval import StartupApproval
        from terminal_resume_history import (create_offline_case,initial_completion_sink,offer_resume,
            sdk_started,sdk_finished,close_offline_case,TEXT_PROMPT,SKILL_PROMPT)
        from headless_context_driver import _terminate
        from terminal_context_debug import create_context_debug, fit_debug_report, create_context_edit_debug, _fit_edit_pending_report
        spec=importlib.util.spec_from_file_location('offline_pty_driver','/opt/probe/claude-pty-driver.py')
        driver=importlib.util.module_from_spec(spec); spec.loader.exec_module(driver)
    except Exception as error:
        if observe: raise _OfflineFailure('IMPORTS',error) from None
        raise
    debug_reports=[]
    edit_reports=[]
    try:
        version=subprocess.run(['/opt/probe/claude','--version'],env={'PATH':'/usr/bin:/bin','HOME':'/work'},
            capture_output=True,timeout=5)
    except Exception as error:
        if observe: raise _OfflineFailure('VERSION',error) from None
        raise
    match=re.fullmatch(rb'(\d{1,4}\.\d{1,4}\.\d{1,4}) \(Claude Code\)\s*',version.stdout)
    if version.returncode or not match:
        return _failed({'reasonCode':'OFFLINE_RUNTIME_UNAVAILABLE'},'VERSION',enabled=observe,exit_code=version.returncode)

    def run_case(name):
        root=Path(tempfile.mkdtemp(prefix='case-',dir='/work')); identity=root.stat()
        report={'case':name,'beforeExit':2,'sdkExit':2,'afterExit':2,
            'contextInspected':False,'naturalExit':False,'caseRootAbsent':False,
            'skillCalls':0,'validSkillSample':False,'validSDKSample':False,'messages':0,'stages':[]}
        server=None; thread=None; old_env=dict(os.environ); old_cwd=Path.cwd()
        case_record=None
        phase='PRECHECK'; phase_exit=None
        debug_captures=[]
        edit_captures=[]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def do_GET(self): self.send_error(404)
            def do_POST(self):
                try:
                    length=int(self.headers.get('Content-Length','0'))
                    if self.path not in ('/v1/messages','/v1/messages?beta=true') or not 0<length<=1048576:
                        self.send_error(400); return
                    body=json.loads(self.rfile.read(length))
                    report['messages']+=1
                    if report['messages']>4: self.send_error(429); return
                    skill=name=='skill-turn' and report['messages']==1
                    block=({'type':'tool_use','id':'toolu_synthetic_skill','name':'Skill',
                            'input':{'skill':'context-continuity'}} if skill else
                           {'type':'text','text':'P004B_SKILL_OK'})
                    message={'id':'msg_synthetic','type':'message','role':'assistant','model':'synthetic-model',
                        'content':[block],'stop_reason':'tool_use' if skill else 'end_turn','stop_sequence':None,
                        'usage':{'input_tokens':100,'output_tokens':10}}
                    if body.get('stream') is True:
                        start={**message,'content':[],'stop_reason':None,'usage':{'input_tokens':100,'output_tokens':0}}
                        first={**block,'input':{}} if skill else {'type':'text','text':''}
                        delta=({'type':'input_json_delta','partial_json':json.dumps(block['input'])} if skill else
                               {'type':'text_delta','text':block['text']})
                        events=[('message_start',{'type':'message_start','message':start}),
                            ('content_block_start',{'type':'content_block_start','index':0,'content_block':first}),
                            ('content_block_delta',{'type':'content_block_delta','index':0,'delta':delta}),
                            ('content_block_stop',{'type':'content_block_stop','index':0}),
                            ('message_delta',{'type':'message_delta','delta':{'stop_reason':message['stop_reason'],
                                'stop_sequence':None},'usage':{'output_tokens':10}}),
                            ('message_stop',{'type':'message_stop'})]
                        data=''.join('event: '+event+'\ndata: '+json.dumps(value)+'\n\n' for event,value in events).encode()
                        content_type='text/event-stream'
                    else: data=json.dumps(message).encode(); content_type='application/json'
                    self.send_response(200); self.send_header('Content-Type',content_type)
                    self.send_header('Content-Length',str(len(data))); self.end_headers(); self.wfile.write(data)
                except (OSError,ValueError,TypeError): pass
        try:
            home=root/'home'; config=root/'config'; project=root/'project'
            for directory in (home,config,project): directory.mkdir(mode=0o700)
            for directory in (home,config):
                (directory/'.claude.json').write_text('{"hasCompletedOnboarding":true}',encoding='utf-8')
            (config/'skills').mkdir(); (config/'skills/context-continuity').symlink_to('/opt/skill')
            mcp=root/'mcp.json'; mcp.write_text('{"mcpServers":{}}',encoding='utf-8')
            server=HTTPServer(('127.0.0.1',0),Handler); server.timeout=1
            thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
            os.environ.clear(); os.environ.update({'HOME':str(home),'CLAUDE_CONFIG_DIR':str(config),
                'PATH':'/usr/bin:/bin','TERM':'xterm-256color','COLORTERM':'truecolor',
                'ANTHROPIC_BASE_URL':'http://127.0.0.1:'+str(server.server_port),
                'ANTHROPIC_API_KEY':'synthetic-offline-only-key','ANTHROPIC_MODEL':'synthetic-model',
                'DISABLE_NONESSENTIAL_TRAFFIC':'1','CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC':'1',
                'CLAUDE_CODE_DISABLE_AUTOUPDATER':'1','PYTHONDONTWRITEBYTECODE':'1'})
            os.chdir(project); session=str(uuid.uuid4())
            case_record=create_offline_case(root,session_id=session,case_kind=name,owner=object())
            common=['--strict-mcp-config','--mcp-config',str(mcp)]
            def context(phase,resume):
                diagnostics=TerminalDiagnostics()
                state=TerminalState(node=Path('/opt/probe/node'),module_root=Path('/opt/modules'),
                    deadline=time.monotonic()+25)
                scope=create_offline_probe_issuer().issue_scope(state,object())
                debug=create_context_debug(scope,state,root) if debug_context else None
                if debug is not None: debug_captures.append(debug)
                edit_debug=create_context_edit_debug(scope,state,root) if debug_context_edit else None
                if edit_debug is not None: edit_captures.append(edit_debug)
                events=root/(phase+'.events')
                approval=StartupApproval(time.time()+25,time.time) if not resume else None
                command=('/opt/probe/claude','--resume' if resume else '--session-id',session,*common)
                if resume and post_enter_observation:
                    from terminal_resume_history import offer_post_enter_observation,take_post_enter_result
                    request=offer_post_enter_observation(case_record,state=state,scope=scope,command=command)
                private=({'_post_enter_observation':request} if resume and post_enter_observation else
                    {'_resume_offer':offer_resume(case_record,state=state,scope=scope,command=command)} if resume else
                    {'_initial_completion_sink':initial_completion_sink(case_record,state=state,scope=scope,command=command)})
                code=driver.drive(list(command),
                    root/(phase+'.capture'),25,events,dialogue='context',startup_approval=approval,
                    terminal_state=state,terminal_diagnostics=diagnostics,input_probe_scope=scope,context_debug=debug,
                    context_edit_debug=edit_debug,**private)
                if resume and post_enter_observation:
                    report['observationSummary']=take_post_enter_result(request)
                rows=[json.loads(line) for line in events.read_text().splitlines()] if events.exists() else []
                report['stages'].append(context_stage_report(phase,rows,diagnostics))
                return code,any(row.get('stage')=='context_inspected' and row.get('outcome')=='passed' for row in rows),\
                    any(row.get('stage')=='exit' and row.get('outcome')=='passed' for row in rows)
            phase='INITIAL_CONTEXT'
            before,inspected,exited=context('before',False); report['beforeExit']=before
            if before!=0 or not inspected or not exited:
                report=_failed(report,phase,enabled=observe)
            if before==0 and inspected and exited:
                phase='SDK'
                prompt=SKILL_PROMPT if name=='skill-turn' else TEXT_PROMPT
                sdk=['/opt/probe/claude','-p',prompt,'--resume',session,*common,'--permission-mode','default',
                    '--tools','Skill','--allowedTools','Skill(context-continuity)','--include-hook-events',
                    '--verbose','--output-format','stream-json','--max-turns','4']
                stream=root/'sdk.stream'
                def owned_stdout(path,flags):
                    return os.open(path,flags|os.O_NOFOLLOW|os.O_CLOEXEC,0o600)
                child=None
                with open(stream,'x+b',opener=owned_stdout) as stdout,(root/'sdk.stderr').open('xb') as stderr:
                    try:
                        child=subprocess.Popen(sdk,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,
                            start_new_session=True,close_fds=True)
                        launch=sdk_started(case_record,child=child,command=tuple(sdk),stream=stdout)
                        child.wait(timeout=25)
                        report['sdkExit']=child.returncode
                        phase_exit=child.returncode
                        sample=sdk_finished(launch)
                    finally:
                        if child is not None: _terminate(child)
                report['validSDKSample']=sample.valid
                report['skillCalls']=sample.skill_calls
                if name=='skill-turn': report['validSkillSample']=sample.valid and sample.skill_calls==1
                if sample.valid:
                    phase='RESUMED_CONTEXT'; phase_exit=None
                    after,inspected_after,exited_after=context('after',True); report['afterExit']=after
                    report['contextInspected']=inspected and inspected_after
                    report['naturalExit']=exited and exited_after
                    if not post_enter_observation and (after!=0 or not inspected_after or not exited_after):
                        report=_failed(report,phase,enabled=observe)
                else: report=_failed(report,phase,enabled=observe,exit_code=phase_exit)
        except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as error:
            report=_failed(report,phase,enabled=observe,error=error,exit_code=phase_exit)
        except Exception as error:
            if observe: raise _OfflineFailure(phase,error) from None
            raise
        finally:
            try:
                if case_record is not None: close_offline_case(case_record)
                if server is not None: server.shutdown(); server.server_close()
                if thread is not None: thread.join(timeout=2)
                os.chdir(old_cwd); os.environ.clear(); os.environ.update(old_env)
            except Exception as error:
                if observe: raise _OfflineFailure('CLEANUP',error) from None
                raise
        cleaned=finalize_owned(root,identity,report)
        if cleaned.get('reasonCode')=='OFFLINE_CLEANUP_FAILED':
            if debug_context: debug_reports.append({'status':'OMITTED_CLEANUP'})
            return _failed({'case':name,'caseRootAbsent':False},'CLEANUP',enabled=observe)
        debug_reports.extend(debug.report() for debug in debug_captures)
        for capture in edit_captures:
            try: edit_reports.append(capture.pending_report())
            except Exception: edit_reports.append({'status':'OMITTED_OBSERVER'})
        cleaned.pop('disposableRootAbsent',None); cleaned['caseRootAbsent']=True
        return cleaned
    if post_enter_observation:
        return _post_enter_case_report(run_case('text-turn'))
    report={'runtime':match[1].decode('ascii'),**run_cases(run_case)}
    if debug_context:
        debug=next((value for value in debug_reports if value['status']!='NO_CAPTURE'),{'status':'NO_CAPTURE'})
        report=fit_debug_report(report,debug)
    if debug_context_edit:
        pending=next((value for value in edit_reports if value.get('status')!='NO_CAPTURE'),{'status':'NO_CAPTURE'})
        report=_fit_edit_pending_report(report,pending)
    return report


def main():
    if sys.argv[1:]==['--inner-post-enter-observation']:
        try:
            _audit()
            report=fit_post_enter_report(_controls(post_enter_observation=True),reserve_disposal=True)
        except BaseException:
            report=_new_post_enter_report('SETUP_BLOCKED','SETUP')
        print(json.dumps(report,sort_keys=True)); return _post_enter_child_code(report)
    if sys.argv[1:] in (['--inner-audit'],['--inner-controls'],['--inner-controls-debug'],['--inner-controls-edit-debug']):
        observe=sys.argv[1:]==['--inner-controls']
        try:
            report=_audit()
            if sys.argv[1:] in (['--inner-controls'],['--inner-controls-debug'],['--inner-controls-edit-debug']):
                report={**report,**_controls(debug_context=sys.argv[1:]==['--inner-controls-debug'],
                    debug_context_edit=sys.argv[1:]==['--inner-controls-edit-debug'])}
            else: audit_input_probe_scope(Path('/opt/probe/node'),Path('/opt/modules'))
            if observe: report=_bounded_standard_report(report,0,reserve_disposal=True)
            print(json.dumps(report,sort_keys=True)); return 0
        except _OfflineFailure as error:
            if not observe: raise
            print(json.dumps({'reasonCode':'OFFLINE_PROBE_BLOCKED','failureDiagnostic':error.diagnostic},sort_keys=True))
            return 2
        except Exception as error:
            if observe:
                print(json.dumps(_failed({'reasonCode':'OFFLINE_PROBE_BLOCKED'},'UNKNOWN',enabled=True,error=error),sort_keys=True))
                return 2
            if isinstance(error,(OSError,ValueError,RuntimeError)): return 2
            raise
    parser=argparse.ArgumentParser(description=__doc__)
    modes=parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--audit-isolation',dest='mode',action='store_const',const='--audit-isolation')
    modes.add_argument('--run-offline',dest='mode',action='store_const',const='--run-offline')
    modes.add_argument('--observe-post-enter',dest='mode',action='store_const',const='--observe-post-enter')
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--node',type=Path,required=True)
    parser.add_argument('--module-root',type=Path,required=True)
    parser.add_argument('--claude',type=Path)
    parser.add_argument('--debug-context',action='store_true',help='Opt-in offline synthetic context failure excerpt; chat copy may persist')
    parser.add_argument('--debug-context-edit',action='store_true',help='Opt-in offline rejected edit-row excerpt; chat copy may persist')
    args=parser.parse_args()
    if args.mode=='--observe-post-enter' and sys.argv[1:].count('--observe-post-enter')!=1:
        parser.error('observation mode cannot be repeated')
    if sys.argv[1:].count('--debug-context-edit')>1: parser.error('edit debug cannot be repeated')
    if args.debug_context and args.mode!='--run-offline': parser.error('debug context requires offline controls')
    if args.debug_context_edit and (args.mode!='--run-offline' or args.debug_context):
        parser.error('edit debug requires exclusive offline controls')
    if args.mode=='--observe-post-enter':
        report=run_post_enter_observation(source=args.source,node=args.node,module_root=args.module_root,claude=args.claude)
        print(json.dumps(report,sort_keys=True)); return post_enter_exit_code(report)
    report=(run_isolation_audit(source=args.source,node=args.node,module_root=args.module_root)
        if args.mode=='--audit-isolation' else run_offline_controls(source=args.source,node=args.node,
            module_root=args.module_root,claude=args.claude,debug_context=args.debug_context,
            debug_context_edit=args.debug_context_edit))
    print(json.dumps(report,sort_keys=True))
    return 0 if report.get('reasonCode') in (None,'OFFLINE_CONTROLS_PASSED') else 2


if __name__=='__main__': raise SystemExit(main())
