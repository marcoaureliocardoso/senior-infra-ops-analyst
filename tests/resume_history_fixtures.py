"""Hand-authored public fixtures; never mounted into a native namespace."""
import json
from dataclasses import replace
import os
from pathlib import Path
import tempfile
import time
from unittest import mock

from terminal_state_adapter import TerminalCell, TerminalSnapshot


def history_snapshot(history=(), *, cursor_row=37):
    lines = dict(history)
    rows = []
    for index in range(40):
        text = lines.get(index, '❯ ' if index == cursor_row else '')
        if len(text) > 120:
            raise ValueError('fixture row too long')
        cells = [TerminalCell(char, 1) for char in text]
        cells.extend(TerminalCell('', 1) for _ in range(120-len(cells)))
        rows.append(tuple(cells))
    return TerminalSnapshot('normal', 2, cursor_row, 0, 0, tuple(rows), {})


def sdk_events(session, case_kind):
    events = [{'type': 'system', 'subtype': 'init', 'session_id': session,
               'tools': ['Skill']}]
    if case_kind == 'skill-turn':
        events.extend([
            {'type': 'assistant', 'session_id': session, 'parent_tool_use_id': None,
             'message': {'role': 'assistant', 'content': [
                 {'type': 'tool_use', 'id': 'call1', 'name': 'Skill',
                  'input': {'skill': 'context-continuity'}}]}},
            {'type': 'user', 'session_id': session, 'parent_tool_use_id': None,
             'message': {'role': 'user', 'content': [
                 {'type': 'tool_result', 'tool_use_id': 'call1',
                  'is_error': False, 'content': 'synthetic skill loaded'}]}},
        ])
    events.extend([
        {'type': 'assistant', 'session_id': session, 'parent_tool_use_id': None,
         'message': {'role': 'assistant', 'content': [
             {'type': 'text', 'text': 'P004B_SKILL_OK'}]}},
        {'type': 'result', 'session_id': session, 'subtype': 'success',
         'is_error': False, 'result': 'P004B_SKILL_OK'},
    ])
    return events


def encode_events(events):
    return b''.join(json.dumps(event).encode('utf-8')+b'\n' for event in events)


def sdk_stream(session, case_kind):
    return encode_events(sdk_events(session, case_kind))


class NativeFixture:
    """Unit lifetime peer only; driver/supervisor tests use real processes."""
    def __init__(self, args=()):
        self.args = list(args)
        self.returncode = None

    def poll(self):
        return self.returncode


def write_context_peer(path, *, mode, seen):
    """Real Python PTY peer, with explicit reads as protocol barriers."""
    text='P0-04B synthetic text control. Reply P004B_SKILL_OK only.'
    history=((5,'❯ '+text),(10,'❯ /context'),(12,'❯ /exit')) if mode!='initial' else ()
    initial='\x1b[?1049h'
    for row,line in history:
        initial+='\x1b['+str(row+1)+';1H'+line
    if mode=='duplicate': initial+='\x1b[7;1H❯ '+text
    if mode=='current-row': initial+='\x1b[38;1H❯ '+text
    else: initial+='\x1b[38;1H❯\u00a0'
    startup={'api_key':'Do you want to use this API key?',
        'theme':'Choose the text style that looks best with your terminal',
        'trust':'Yes, I trust this folder'}.get(mode)
    if startup: initial+='\x1b[1;1H'+startup+'\x1b[38;3H'
    after='\x1b[2J\x1b[HContext Usage\r\nFree space: 81%\r\nAutocompact buffer: 3%'
    for row,line in history:
        if mode=='retire' and row==5: continue
        after+='\x1b['+str(row+1)+';1H'+line
    after+='\x1b[21;1H❯ /context\x1b[38;1H❯\u00a0'
    if mode=='completion-only': after='\x1b[2J\x1b[38;1H❯\u00a0'
    path.write_text('import os,tty\nfrom pathlib import Path\n'
        'tty.setraw(0)\n'
        'def read(n):\n'
        ' data=bytearray()\n'
        ' while len(data)<n:\n'
        '  value=os.read(0,1)\n'
        '  if not value: raise SystemExit(3)\n'
        '  with Path('+repr(str(seen))+').open("ab") as stream: stream.write(value)\n'
        '  data.extend(value)\n'
        ' return bytes(data)\n'
        'os.write(1,'+repr(initial.encode())+')\n'
        + ('while True: read(1)\n' if startup or mode in ('duplicate','current-row') else
        'command=bytearray()\n'
        'for _ in range(8):\n'
        ' command.extend(read(1)); os.write(1,b"\\x1b[38;3H"+command)\n'
        'if command!=b"/context" or read(1)!=b"\\r": raise SystemExit(4)\n'
        'os.write(1,'+repr(after.encode())+')\n'
        'marker=read(16)\n'
        'os.write(1,b"\\x1b[38;3H"+marker)\n'
        'if read(1)!=b"\\x15": raise SystemExit(5)\n'
        'os.write(1,"\\x1b[38;1H\\x1b[2K❯\\u00a0".encode())\n'
        'if read(6)!=b"/exit\\r": raise SystemExit(6)\n'),encoding='utf-8')


class CaseFixture:
    def __init__(self, case_kind='text-turn'):
        self.kind = case_kind
        self.session = 'synthetic-session'
        self.resources = []

    def __enter__(self):
        import terminal_input_challenge as challenge
        import terminal_resume_history as history
        self.patch = mock.patch.object(challenge, 'audit_offline_namespace', return_value={
            'networkIsolated':True,'operatorStateHidden':True,'capabilitiesDropped':True})
        self.patch.start()
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root/'project').mkdir(mode=0o700)
        self.old_cwd = Path.cwd(); os.chdir(self.root/'project')
        self.owner = object()
        self.case = history.create_offline_case(self.root, session_id=self.session,
            case_kind=self.kind, owner=self.owner)
        common = ('--strict-mcp-config','--mcp-config',str(self.root/'mcp.json'))
        self.initial_command = ('/opt/probe/claude','--session-id',self.session,*common)
        self.resume_command = ('/opt/probe/claude','--resume',self.session,*common)
        prompt = ('P0-04B synthetic text control. Reply P004B_SKILL_OK only.' if self.kind=='text-turn'
                  else 'P0-04B synthetic. Invoke Skill(context-continuity) once; reply P004B_SKILL_OK. No browser.')
        self.sdk_command = ('/opt/probe/claude','-p',prompt,'--resume',self.session,*common,
            '--permission-mode','default','--tools','Skill','--allowedTools','Skill(context-continuity)',
            '--include-hook-events','--verbose','--output-format','stream-json','--max-turns','4')
        self.fresh_terminal()
        self.sink = history.initial_completion_sink(self.case, state=self.state,
            scope=self.scope, command=self.initial_command)
        return self

    def fresh_terminal(self):
        from terminal_state_adapter import TerminalState
        from terminal_input_policy import TerminalInputPolicy
        import terminal_input_challenge as challenge
        self.state = TerminalState(Path(os.environ['P004B_TERMINAL_NODE']),
            Path(os.environ['P004B_TERMINAL_MODULE_ROOT']), time.monotonic()+20)
        self.resources.append(self.state)
        self.scope = challenge.create_offline_probe_issuer().issue_scope(self.state, object())
        self.policy = TerminalInputPolicy(); self.native = NativeFixture()
        self.controller = object(); self.transition = object()

    def initial_protocol(self):
        import terminal_context_echo as echo
        import terminal_input_challenge as challenge
        import terminal_resume_history as history
        empty = history_snapshot()
        history.bind_initial_sink(self.sink, controller_owner=self.controller,
            native_owner=self.native, transition_owner=self.transition)
        self.context_command = echo.begin_context_command(self.scope,self.state,self.native,
            self.transition,self.policy,empty,1)
        command = self.context_command
        assert command.type_bytes(empty,1) == b'/context'
        command.check_edit(empty,1,8)
        echoed = replace(history_snapshot(((37,'❯ /context'),)),cursorX=10)
        assert command.observe(echoed,2) == 'COMMAND_ECHO_MATCHED'
        assert command.submit_bytes(echoed,2) == b'\r'
        command.submission_written(1)
        numeric = history_snapshot(((0,'Context Usage'),(1,'Free space: 81%'),
            (2,'Autocompact buffer: 3%'),(10,'❯ /context')))
        receipt = command.bind_history(numeric,3)
        self.probe = challenge.NonceInputChallenge(self.scope,self.native,self.transition,
            self.policy,numeric,3,context_receipt=receipt)
        marker = self.probe.type_bytes(numeric,3).decode('ascii')
        nonce = replace(history_snapshot(((0,'Context Usage'),(1,'Free space: 81%'),
            (2,'Autocompact buffer: 3%'),(10,'❯ /context'),(37,'❯ '+marker))),cursorX=18)
        assert self.probe.observe(nonce,4) == 'ECHO_MATCHED'
        assert self.probe.clear_bytes(nonce,4) == b'\x15'
        assert self.probe.observe(numeric,5) == 'PROVEN'
        assert self.probe.consume_exit(self.probe.ownership_proof(),numeric,5,self.native,self.transition)
        self.native.returncode = 0

    def capture(self, **changes):
        import terminal_resume_history as history
        bindings = dict(controller_owner=self.controller,state=self.state,scope=self.scope,
            native_owner=self.native,transition_owner=self.transition,
            context_command=self.context_command,probe=self.probe,frame=5,exit_written=6)
        bindings.update(changes)
        return history.capture_initial_completion(self.sink, **bindings)

    def complete_initial(self):
        import terminal_resume_history as history
        self.initial_protocol()
        pending = self.capture()
        self.context_command.invalidate('INPUT_PROBE_REVOKED')
        self.probe.invalidate('INPUT_PROBE_REVOKED')
        self.state.close()
        history.finish_initial_completion(pending,result=0,native_cleanup='CLEANUP_COMPLETED',
            helper_cleanup='CLEANUP_COMPLETED')

    def validate_sdk(self, case_kind):
        import terminal_resume_history as history
        stream = (self.root/'sdk.stream').open('w+b')
        os.chmod(stream.name,0o600); self.resources.append(stream)
        stream.write(sdk_stream(self.session,case_kind)); stream.flush()
        self.sdk_child = NativeFixture(self.sdk_command)
        self.launch = history.sdk_started(self.case,child=self.sdk_child,
            command=self.sdk_command,stream=stream)
        self.sdk_child.returncode = 0
        return history.sdk_finished(self.launch)

    def offer(self):
        import terminal_resume_history as history
        return history.offer_resume(self.case,state=self.state,scope=self.scope,command=self.resume_command)

    def __exit__(self, *_args):
        import terminal_resume_history as history
        history.close_offline_case(self.case)
        for resource in reversed(self.resources):
            resource.close()
        os.chdir(self.old_cwd)
        self.temporary.cleanup(); self.patch.stop()
