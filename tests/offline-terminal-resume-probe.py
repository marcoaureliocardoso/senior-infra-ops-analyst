#!/usr/bin/env python3
"""Offline-only native regression. No operator settings, key or real provider."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
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


def context_stage_report(phase,rows,diagnostics):
    """Separate structural diagnostics from the unchanged reduced proof stream."""
    reduced=[{key:row[key] for key in ('stage','outcome','percent') if key in row} for row in rows]
    return {'phase':phase,'events':reduced,'diagnostics':diagnostics.report()}


def validate_mode(arguments):
    return arguments in (['--run-offline'],['--audit-isolation'],['--run-offline','--debug-context'])


def case_complete(case):
    required=(case.get('beforeExit')==0 and case.get('sdkExit')==0 and case.get('afterExit')==0
        and case.get('contextInspected') is True and case.get('naturalExit') is True
        and case.get('caseRootAbsent') is True)
    return required and (case.get('case')=='text-turn' or
        (case.get('case')=='skill-turn' and case.get('validSkillSample') is True and case.get('skillCalls')==1))


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


def _namespace(*,source,node,module_root,claude=None,audit=False,debug_context=False):
    if type(debug_context) is not bool or (audit and debug_context): return {'reasonCode':'OFFLINE_PROBE_BLOCKED'}
    try:
        source=source.resolve(strict=True); node=node.resolve(strict=True); module_root=module_root.resolve(strict=True)
        bwrap=shutil.which('bwrap')
        if not bwrap or not node.is_file(): raise ValueError
    except (OSError,ValueError): return {'reasonCode':'OFFLINE_PROBE_BLOCKED'}
    root=Path(tempfile.mkdtemp(prefix='p004b-offline-terminal-'))
    identity=root.stat()
    report={'reasonCode':'OFFLINE_PROBE_BLOCKED'}
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
                     'terminal_input_challenge.py',
                     'terminal_context_debug.py',
                     'terminal_structural_diagnostics.py',
                     'terminal_state_adapter.py','terminal-state-adapter.mjs','browser_startup_approval.py',
                     'browser_operations_live.py'):
            command += ['--ro-bind',str(source/'tests'/name),'/opt/probe/'+name]
        if not audit:
            claude=claude.resolve(strict=True)
            if not claude.is_file(): raise ValueError
            command += ['--ro-bind',str(claude),'/opt/probe/claude']
        command += ['--clearenv','--setenv','PATH','/usr/bin:/bin','--setenv','PYTHONDONTWRITEBYTECODE','1',
            '/usr/bin/python3','/opt/probe/probe.py','--inner-audit' if audit else
                '--inner-controls-debug' if debug_context else '--inner-controls']
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
        if result.returncode or len(data)>16384: raise ValueError
        report=json.loads(data)
    except (KeyboardInterrupt,TerminalCancelled): report={'reasonCode':'OFFLINE_PROBE_INTERRUPTED'}
    except (OSError,ValueError,TypeError,RuntimeError,UnicodeError,subprocess.SubprocessError): pass
    return finalize_owned(root,identity,report)


def run_isolation_audit(*,source,node,module_root):
    return _namespace(source=source,node=node,module_root=module_root,audit=True)


def run_offline_controls(*,source,claude,node,module_root,debug_context=False):
    if claude is None: return {'reasonCode':'OFFLINE_PROBE_BLOCKED'}
    return _namespace(source=source,claude=claude,node=node,module_root=module_root,debug_context=debug_context)


def run_cases(run_case):
    cases=[]
    for name in ('text-turn','skill-turn'):
        case=run_case(name); cases.append(case)
        if not case_complete(case):
            return {'reasonCode':'OFFLINE_CONTROLS_INCONCLUSIVE','cases':cases}
    return {'reasonCode':'OFFLINE_CONTROLS_PASSED','cases':cases}


def _controls(*,debug_context=False):
    sys.path.insert(0,'/opt/probe')
    from terminal_state_adapter import TerminalState
    from browser_startup_approval import StartupApproval
    from browser_operations_live import evaluate_measurement_stream
    from terminal_context_debug import create_context_debug, fit_debug_report
    debug_reports=[]
    spec=importlib.util.spec_from_file_location('offline_pty_driver','/opt/probe/claude-pty-driver.py')
    driver=importlib.util.module_from_spec(spec); spec.loader.exec_module(driver)
    version=subprocess.run(['/opt/probe/claude','--version'],env={'PATH':'/usr/bin:/bin','HOME':'/work'},
        capture_output=True,timeout=5)
    match=re.fullmatch(rb'(\d{1,4}\.\d{1,4}\.\d{1,4}) \(Claude Code\)\s*',version.stdout)
    if version.returncode or not match: return {'reasonCode':'OFFLINE_RUNTIME_UNAVAILABLE'}

    def run_case(name):
        root=Path(tempfile.mkdtemp(prefix='case-',dir='/work')); identity=root.stat()
        report={'case':name,'beforeExit':2,'sdkExit':2,'afterExit':2,
            'contextInspected':False,'naturalExit':False,'caseRootAbsent':False,
            'skillCalls':0,'validSkillSample':False,'messages':0,'stages':[]}
        server=None; thread=None; old_env=dict(os.environ); old_cwd=Path.cwd()
        debug_captures=[]
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
            common=['--strict-mcp-config','--mcp-config',str(mcp)]
            def context(phase,resume):
                diagnostics=TerminalDiagnostics()
                state=TerminalState(node=Path('/opt/probe/node'),module_root=Path('/opt/modules'),
                    deadline=time.monotonic()+25)
                scope=create_offline_probe_issuer().issue_scope(state,object())
                debug=create_context_debug(scope,state,root) if debug_context else None
                if debug is not None: debug_captures.append(debug)
                events=root/(phase+'.events')
                approval=StartupApproval(time.time()+25,time.time) if not resume else None
                code=driver.drive(['/opt/probe/claude','--resume' if resume else '--session-id',session,*common],
                    root/(phase+'.capture'),25,events,dialogue='context',startup_approval=approval,
                    terminal_state=state,terminal_diagnostics=diagnostics,input_probe_scope=scope,context_debug=debug)
                rows=[json.loads(line) for line in events.read_text().splitlines()] if events.exists() else []
                report['stages'].append(context_stage_report(phase,rows,diagnostics))
                return code,any(row.get('stage')=='context_inspected' and row.get('outcome')=='passed' for row in rows),\
                    any(row.get('stage')=='exit' and row.get('outcome')=='passed' for row in rows)
            before,inspected,exited=context('before',False); report['beforeExit']=before
            if before==0 and inspected and exited:
                prompt=('P0-04B synthetic context measurement. Invoke Skill exactly once with only '
                    'skill=context-continuity, then reply P004B_SKILL_OK. Do not perform browser work.'
                    if name=='skill-turn' else 'P0-04B synthetic text control. Reply P004B_SKILL_OK only.')
                sdk=['/opt/probe/claude','-p',prompt,'--resume',session,*common,'--permission-mode','default',
                    '--tools','Skill','--allowedTools','Skill(context-continuity)','--include-hook-events',
                    '--verbose','--output-format','stream-json','--max-turns','4']
                stream=root/'sdk.stream'
                with stream.open('wb') as stdout,(root/'sdk.stderr').open('wb') as stderr:
                    result=subprocess.run(sdk,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,timeout=25)
                report['sdkExit']=result.returncode
                if name=='skill-turn':
                    sample=evaluate_measurement_stream(stream,session,'skill','synthetic-probe')
                    report['skillCalls']=sample['skillCalls']; report['validSkillSample']=sample['terminalSuccess']
                if result.returncode==0:
                    after,inspected_after,exited_after=context('after',True); report['afterExit']=after
                    report['contextInspected']=inspected and inspected_after
                    report['naturalExit']=exited and exited_after
        except (OSError,ValueError,RuntimeError,subprocess.SubprocessError): pass
        finally:
            if server is not None: server.shutdown(); server.server_close()
            if thread is not None: thread.join(timeout=2)
            os.chdir(old_cwd); os.environ.clear(); os.environ.update(old_env)
        cleaned=finalize_owned(root,identity,report)
        if cleaned.get('reasonCode')=='OFFLINE_CLEANUP_FAILED':
            if debug_context: debug_reports.append({'status':'OMITTED_CLEANUP'})
            return {'case':name,'caseRootAbsent':False}
        debug_reports.extend(debug.report() for debug in debug_captures)
        cleaned.pop('disposableRootAbsent',None); cleaned['caseRootAbsent']=True
        return cleaned
    report={'runtime':match[1].decode('ascii'),**run_cases(run_case)}
    if debug_context:
        debug=next((value for value in debug_reports if value['status']!='NO_CAPTURE'),{'status':'NO_CAPTURE'})
        report=fit_debug_report(report,debug)
    return report


def main():
    if sys.argv[1:] in (['--inner-audit'],['--inner-controls'],['--inner-controls-debug']):
        try:
            report=_audit()
            if sys.argv[1:] in (['--inner-controls'],['--inner-controls-debug']):
                report={**report,**_controls(debug_context=sys.argv[1:]==['--inner-controls-debug'])}
            else: audit_input_probe_scope(Path('/opt/probe/node'),Path('/opt/modules'))
            print(json.dumps(report,sort_keys=True)); return 0
        except (OSError,ValueError,RuntimeError): return 2
    parser=argparse.ArgumentParser(description=__doc__)
    modes=parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--audit-isolation',dest='mode',action='store_const',const='--audit-isolation')
    modes.add_argument('--run-offline',dest='mode',action='store_const',const='--run-offline')
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--node',type=Path,required=True)
    parser.add_argument('--module-root',type=Path,required=True)
    parser.add_argument('--claude',type=Path)
    parser.add_argument('--debug-context',action='store_true',help='Opt-in offline synthetic context failure excerpt; chat copy may persist')
    args=parser.parse_args()
    if args.debug_context and args.mode!='--run-offline': parser.error('debug context requires offline controls')
    report=(run_isolation_audit(source=args.source,node=args.node,module_root=args.module_root)
        if args.mode=='--audit-isolation' else run_offline_controls(source=args.source,node=args.node,
            module_root=args.module_root,claude=args.claude,debug_context=args.debug_context))
    print(json.dumps(report,sort_keys=True))
    return 0 if report.get('reasonCode') in (None,'OFFLINE_CONTROLS_PASSED') else 2


if __name__=='__main__': raise SystemExit(main())
