"""Maintained synthetic peers. Audit substitutions do NOT prove real isolation."""
from contextlib import ExitStack
import importlib.util
import json
import os
from pathlib import Path
import select
import subprocess
import sys
import time
from unittest import mock

from resume_history_fixtures import CaseFixture
import headless_context_driver as selected
import terminal_input_challenge as challenge
import terminal_nonce_history_diagnostics as observation
from terminal_structural_diagnostics import TerminalDiagnostics

VARIANTS=('stable','echo-move','echo-padding','clear-move','clear-padding','post-clear-move')


def _byte(fd):
    if not select.select([fd],[],[],3)[0]: raise RuntimeError('synthetic handshake deadline')
    if os.read(fd,1)!=b'1': raise RuntimeError('synthetic handshake rejected')


def _peer(kind,variant,seen,release,ack):
    import tty
    release=int(release); ack=int(ack)
    from terminal_resume_history import TEXT_PROMPT,SKILL_PROMPT
    prompt=TEXT_PROMPT if kind=='text-turn' else SKILL_PROMPT
    received=bytearray()
    protocol=b'/context\r0123456789abcdef\x15/exit\r'
    def read(count):
        result=bytearray()
        while len(result)<count:
            if not select.select([0],[],[],6)[0]: raise SystemExit(3)
            value=os.read(0,count-len(result))
            if not value: raise SystemExit(3)
            result.extend(value)
            received.extend(value)
            Path(seen).write_text(json.dumps(dict(count=len(received),exact=received==protocol[:len(received)])))
        return bytes(result)
    def screen(current=False):
        value='\x1b[?1049h\x1b[2J\x1b[HContext Usage\r\nFree space: 81%\r\nAutocompact buffer: 3%'
        value+='\x1b[6;1H❯ '+prompt+'\x1b[11;1H❯ /context\x1b[13;1H❯ /exit'
        if current: value+='\x1b[21;1H❯ /context'
        return (value+'\x1b[38;1H❯\u00a0').encode()
    def moved(cursor):
        gap='\u00a0' if variant.endswith('padding') else ' '
        return ('\x1b[6;1H\x1b[2K\x1b[7;1H❯'+gap+prompt+'\x1b[38;'+str(cursor)+'H').encode()
    tty.setraw(0); os.write(1,screen())
    command=bytearray()
    for _ in range(8):
        command.extend(read(1)); os.write(1,b'\x1b[38;3H'+command)
    if command!=b'/context' or read(1)!=b'\r': raise SystemExit(4)
    os.write(1,screen(True)); marker=read(16)
    if not all(c in b'0123456789abcdef' for c in marker): raise SystemExit(4)
    os.write(1,b'\x1b[38;3H'+marker)
    if variant.startswith('echo-'):
        _byte(release); os.write(1,moved(19)); os.write(ack,b'1')
        read(1); raise SystemExit(4)
    if read(1)!=b'\x15': raise SystemExit(4)
    cleared='\x1b[38;1H\x1b[2K❯\u00a0'.encode()
    if variant.startswith('clear-'):
        os.write(1,cleared+moved(3)); os.write(ack,b'1')
        read(1); raise SystemExit(5)
    os.write(1,cleared)
    if variant=='post-clear-move':
        _byte(release); os.write(1,moved(3)); os.write(ack,b'1')
    if read(6)!=b'/exit\r': raise SystemExit(4)


def run_nonce_phase_case(case_kind,variant,*,diagnostic_mode='normal',clear_fault=None):
    if case_kind not in ('text-turn','skill-turn') or variant not in VARIANTS: raise ValueError('synthetic case')
    if diagnostic_mode not in ('normal','absent','capture-failure','collector-failure'): raise ValueError('synthetic mode')
    if clear_fault not in (None,'would-block','io-error','bad-count'): raise ValueError('synthetic fault')
    spec=importlib.util.spec_from_file_location('nonce_driver_fixture',Path(__file__).with_name('claude-pty-driver.py'))
    driver=importlib.util.module_from_spec(spec); spec.loader.exec_module(driver)
    with CaseFixture(case_kind) as f:
        f.complete_initial(); assert f.validate_sdk(case_kind).valid; f.fresh_terminal()
        seen=f.root/'input'; diagnostic=TerminalDiagnostics()
        release_r,release_w=os.pipe(); ack_r,ack_w=os.pipe()
        real_popen=subprocess.Popen; real_write=os.write; real_observe=challenge.NonceInputChallenge.observe
        children=[]; released=False; clear_calls=0; sessions_before=len(observation._SESSIONS)
        def observe(probe,snapshot,frame):
            nonlocal released
            phase=real_observe(probe,snapshot,frame)
            if not released and probe._resume_view is not None and (
                    (phase=='ECHO_MATCHED' and variant.startswith('echo-'))
                    or (phase=='PROVEN' and variant=='post-clear-move')):
                released=True; real_write(release_w,b'1'); _byte(ack_r)
            return phase
        def write(fd,data):
            nonlocal clear_calls
            is_clear=bytes(data)==b'\x15'
            if is_clear:
                clear_calls+=1
                if clear_fault=='would-block' and clear_calls==1: raise BlockingIOError()
                if clear_fault=='io-error': raise OSError()
            result=real_write(fd,data)
            if is_clear and variant.startswith('clear-'): _byte(ack_r)
            return 2 if is_clear and clear_fault=='bad-count' else result
        def prepare_launch(command,options):
            actual=[sys.executable,str(Path(__file__).resolve()),'--peer',case_kind,variant,
                str(seen),str(release_r),str(ack_w)]
            if '--owned-child' in command:
                boundary=command.index('--')+1
                assert tuple(command[boundary:])==f.resume_command
                actual=[*command[:boundary],*actual]
            else: assert tuple(command)==f.resume_command
            options['pass_fds']=tuple(set(options.get('pass_fds',()))|{release_r,ack_w})
            return actual,options
        class PeerProcess(real_popen):
            def __init__(self,command,**options):
                actual,options=prepare_launch(command,options)
                super().__init__(actual,**options)
                children.append(self)
        try:
            with ExitStack() as patches:
                patches.enter_context(mock.patch.object(challenge.NonceInputChallenge,'observe',new=observe))
                patches.enter_context(mock.patch.object(challenge.secrets,'token_hex',return_value='0123456789abcdef'))
                patches.enter_context(mock.patch.object(selected.os,'write',new=write))
                patches.enter_context(mock.patch.object(selected.subprocess,'Popen',new=PeerProcess))
                if diagnostic_mode=='absent':
                    patches.enter_context(mock.patch.object(selected,'_create_nonce_history_session',return_value=None,create=True))
                if diagnostic_mode=='capture-failure':
                    patches.enter_context(mock.patch.object(observation,'_capture_scope',side_effect=ValueError))
                if diagnostic_mode=='collector-failure':
                    patches.enter_context(mock.patch.object(diagnostic,'add',side_effect=ValueError))
                code=driver.drive(list(f.resume_command),f.root/'capture',10,f.root/'events',dialogue='context',
                    terminal_state=f.state,terminal_diagnostics=diagnostic,input_probe_scope=f.scope,_resume_offer=f.offer())
        finally:
            for fd in (release_r,release_w,ack_r,ack_w): os.close(fd)
        facts=json.loads(seen.read_bytes()) if seen.exists() else dict(count=0,exact=True)
        # The peer compares concrete bytes in memory; its sidecar is counters only.
        result=dict(exitCode=code,inputBytes=facts['count'],inputExact=facts['exact'],
            diagnostics=diagnostic.report(),processReaped=all(c.poll() is not None for c in children),
            helperReaped=f.state.helper_reaped,clearCalls=clear_calls,
            scopeReleased=observation._CURRENT.get() is None,
            sessionReleased=len(observation._SESSIONS)==sessions_before)
        root=f.root
    result['caseRootAbsent']=not root.exists()
    return result


if __name__=='__main__':
    if len(sys.argv)!=7 or sys.argv[1]!='--peer': raise SystemExit(2)
    _peer(*sys.argv[2:])
