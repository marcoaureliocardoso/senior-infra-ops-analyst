"""Real signal delivery to selected CLIs; every target is a synthetic Python UI."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest

ROOT=Path(__file__).resolve().parents[1]


class HeadlessDriverSignalTests(unittest.TestCase):
    def run_case(self,entrypoint,signum,phase='pty'):
        with tempfile.TemporaryDirectory(prefix='headless-signal-') as directory:
            root=Path(directory); root.chmod(0o700)
            for name in ('home','config','startup-approval'): (root/name).mkdir(mode=0o700)
            fake=root/'native'; pidfile=root/'native.pid'; childfile=root/'descendant.pid'
            launched=root/'launched'; source_wait=root/'source-wait'; helper_pid=root/'helper.pid'
            fake.write_text('#!/usr/bin/python3\nimport os,subprocess,sys,time,tty\nfrom pathlib import Path\n'
                'tty.setraw(0)\n'
                'p=subprocess.Popen([sys.executable,"-c","import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(60)"],start_new_session=True)\n'
                'Path('+repr(str(childfile))+').write_text(str(p.pid))\n'
                'Path('+repr(str(pidfile))+').write_text(str(os.getpid()))\n'
                'os.write(1,"❯\\u00a0".encode())\ntime.sleep(60)\n',encoding='utf-8')
            fake.chmod(0o700)
            node=Path(os.environ['P004B_TERMINAL_NODE'])
            if phase=='ipc':
                node=root/'slow-node'
                node.write_text('#!/usr/bin/python3\nimport os,subprocess,sys,time\nfrom pathlib import Path\n'
                    'p=subprocess.Popen([sys.executable,"-c","import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(60)"],start_new_session=True)\n'
                    'Path('+repr(str(childfile))+').write_text(str(p.pid))\n'
                    'Path('+repr(str(helper_pid))+').write_text(str(os.getpid()))\ntime.sleep(60)\n')
                node.chmod(0o700)
            mcp=root/'mcp.json'; mcp.write_text('{"mcpServers":{}}')
            session='11111111-1111-4111-8111-111111111111'; commit='a'*40; nonce='p004b-'+'b'*32
            claim=root/'startup-approval/claim.json'
            issued=int(time.time())
            claim.write_text(json.dumps({'commit':commit,'runNonce':nonce,'sessionId':session,
                'endpoint':'https://synthetic.example.invalid/anthropic','configDir':str(root/'config'),
                'executable':str(fake),'probe':'main-before','issuedAt':issued,'expiresAt':issued+60}))
            claim.chmod(0o600)
            driver=ROOT/'tests'/({'public':'claude-pty-driver.py','dedicated':'browser-context-driver.py',
                'preflight':'terminal-runtime-preflight.py'}[entrypoint])
            wrapper=root/'wrapper.py'
            wrapper.write_text('import importlib.util,subprocess,sys,time\nfrom pathlib import Path\n'
                'sys.path.insert(0,'+repr(str(ROOT/'tests'))+')\n'
                'import terminal_cancellation\n'
                'Original=subprocess.Popen\n'
                'class Logged(Original):\n'
                ' def __init__(self,*args,**kwargs):\n'
                '  super().__init__(*args,**kwargs)\n'
                '  with Path('+repr(str(launched))+').open("a") as stream: stream.write(str(self.pid)+"\\n")\n'
                'subprocess.Popen=Logged\n'
                'spec=importlib.util.spec_from_file_location("selected",'+repr(str(driver))+')\n'
                'module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)\n'
                + ('def source_head(_root):\n'
                   + (' Path('+repr(str(source_wait))+').touch()\n time.sleep(.4)\n' if phase=='claim' else '')
                   +' return '+repr(commit)+'\nmodule.source_head=source_head\n' if entrypoint=='dedicated' else '')
                +'sys.argv=['+repr(str(driver))+',*sys.argv[1:]]\nraise SystemExit(module.main())\n')
            args=['--capture',str(root/'capture'),'--events',str(root/'events'),'--dialogue','context',
                '--timeout','10','--terminal-engine','headless','--terminal-node',str(node),
                '--terminal-module-root',os.environ['P004B_TERMINAL_MODULE_ROOT']]
            if entrypoint=='dedicated':
                args+=['--claim',str(claim),'--commit',commit,'--run-nonce',nonce,'--source-root',str(ROOT)]
            args+=['--',str(fake),'--session-id',session,'--strict-mcp-config','--mcp-config',str(mcp)]
            if entrypoint=='preflight':
                args=['--node',str(node),'--module-root',os.environ['P004B_TERMINAL_MODULE_ROOT']]
            env={'PATH':'/usr/bin:/bin','HOME':str(root/'home'),'CLAUDE_CONFIG_DIR':str(root/'config'),
                'ANTHROPIC_BASE_URL':'https://synthetic.example.invalid/anthropic','PYTHONDONTWRITEBYTECODE':'1'}
            process=subprocess.Popen([sys.executable,str(wrapper),*args],env=env,
                stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
            known=set()
            def collect():
                for path in (launched,pidfile,childfile,helper_pid):
                    if path.exists():
                        for item in path.read_text().split(): known.add(int(item))
            try:
                marker=source_wait if phase=='claim' else helper_pid if phase=='ipc' else pidfile
                deadline=time.monotonic()+5
                while not marker.exists() and process.poll() is None and time.monotonic()<deadline: time.sleep(.01)
                self.assertTrue(marker.exists(),'synthetic phase never reached')
                collect(); os.kill(process.pid,signum)
                # A second managed signal must not interrupt disposal.
                time.sleep(.01)
                if process.poll() is None: os.kill(process.pid,signum)
                self.assertEqual(process.wait(timeout=5),2,'driver did not return a closed cancellation failure')
                collect()
                deadline=time.monotonic()+2
                while any(Path(f'/proc/{pid}').exists() for pid in known) and time.monotonic()<deadline: time.sleep(.01)
                self.assertTrue(known)
                self.assertFalse(any(Path(f'/proc/{pid}').exists() for pid in known),'owned process was not reaped')
                if phase=='claim':
                    self.assertTrue(claim.exists()); self.assertFalse((claim.parent/'spent').exists())
                if (root/'events').exists():
                    events=[json.loads(line) for line in (root/'events').read_text().splitlines()]
                    self.assertFalse(any(row.get('stage')=='exit' and row.get('outcome')=='passed' for row in events))
            finally:
                collect()
                for pid in known|{process.pid}:
                    try: os.kill(pid,signal.SIGKILL)
                    except ProcessLookupError: pass
                    try: os.waitpid(pid,os.WNOHANG)
                    except ChildProcessError: pass
                process.wait(timeout=2)

    def test_public_pty_term_and_hup(self):
        for signum in (signal.SIGTERM,signal.SIGHUP):
            with self.subTest(signum=signum): self.run_case('public',signum)

    def test_dedicated_pty_term_and_hup(self):
        for signum in (signal.SIGTERM,signal.SIGHUP):
            with self.subTest(signum=signum): self.run_case('dedicated',signum)

    def test_public_ipc_term_and_hup(self):
        for signum in (signal.SIGTERM,signal.SIGHUP):
            with self.subTest(signum=signum): self.run_case('public',signum,'ipc')

    def test_dedicated_source_wait_cancel_leaves_claim_unconsumed(self):
        for signum in (signal.SIGTERM,signal.SIGHUP):
            with self.subTest(signum=signum): self.run_case('dedicated',signum,'claim')

    def test_preflight_ipc_term_and_hup(self):
        for signum in (signal.SIGTERM,signal.SIGHUP):
            with self.subTest(signum=signum): self.run_case('preflight',signum,'ipc')


if __name__=='__main__': unittest.main()
