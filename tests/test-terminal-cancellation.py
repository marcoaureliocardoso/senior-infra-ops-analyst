"""Managed cancellation and exact family ownership; synthetic processes only."""
import importlib.util
import io
import os
from pathlib import Path
import signal
import select
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

MODULE=Path(__file__).with_name('terminal_cancellation.py')


class TerminalCancellationTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(MODULE.is_file(),'managed cancellation interface missing')
        spec=importlib.util.spec_from_file_location('terminal_cancellation',MODULE)
        self.module=importlib.util.module_from_spec(spec); spec.loader.exec_module(self.module)

    def test_signals_request_only_then_checkpoint_raises(self):
        for signum in (signal.SIGTERM,signal.SIGHUP):
            previous=signal.getsignal(signum)
            with self.module.TerminalCancellation() as token:
                self.assertTrue(callable(signal.getsignal(signum)))
                os.kill(os.getpid(),signum)
                self.assertTrue(token.requested)
                with self.assertRaises(self.module.TerminalCancelled): token.check()
            self.assertIs(signal.getsignal(signum),previous)

    def test_repeated_signals_cannot_interrupt_cleanup(self):
        with self.module.TerminalCancellation() as token:
            with token.cleanup():
                for signum in (signal.SIGTERM,signal.SIGHUP,signal.SIGTERM):
                    os.kill(os.getpid(),signum); token.check()
                self.assertTrue(token.requested)
            with self.assertRaises(self.module.TerminalCancelled): token.check()

    def test_exception_restores_prior_handlers(self):
        previous={s:signal.getsignal(s) for s in (signal.SIGTERM,signal.SIGHUP)}
        with self.assertRaisesRegex(RuntimeError,'synthetic fixture failure'):
            with self.module.TerminalCancellation(): raise RuntimeError('synthetic fixture failure')
        for signum,handler in previous.items(): self.assertIs(signal.getsignal(signum),handler)

    def test_identity_read_after_real_process_exit_is_absent(self):
        process=subprocess.Popen([sys.executable,'-I','-c','import time; time.sleep(30)'],
            stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
        descriptor=os.pidfd_open(process.pid,0)
        target=Path(f'/proc/{process.pid}/stat'); original=Path.open; opened=[]
        def open_then_exit(path,*args,**kwargs):
            stream=original(path,*args,**kwargs)
            if path==target:
                opened.append(True)
                signal.pidfd_send_signal(descriptor,signal.SIGTERM,None,0)
                process.wait(timeout=3)
            return stream
        try:
            with mock.patch.object(Path,'open',new=open_then_exit):
                try: identity=self.module._identity(process.pid)
                except RuntimeError: self.fail('normal disappearance became ownership unavailability')
                self.assertIsNone(identity)
            self.assertEqual(len(opened),1)
            self.assertIsNotNone(process.poll())
            self.assertTrue(select.select([descriptor],[],[],0)[0])
        finally:
            if process.poll() is None:
                signal.pidfd_send_signal(descriptor,signal.SIGKILL,None,0); process.wait(timeout=3)
            os.close(descriptor)

    def test_identity_permission_io_and_malformed_metadata_still_block(self):
        for error in (PermissionError(13,'synthetic'),OSError(5,'synthetic')):
            with self.subTest(kind=type(error).__name__),mock.patch.object(Path,'open',side_effect=error):
                with self.assertRaises(RuntimeError): self.module._identity(os.getpid())
        for body in ('','synthetic-invalid-stat','0 (synthetic) R invalid-parent','x'*4097):
            with self.subTest(size=len(body)),mock.patch.object(Path,'open',return_value=io.StringIO(body)):
                with self.assertRaises(RuntimeError): self.module._identity(os.getpid())

    def test_remember_still_rejects_changed_or_disappearing_identity(self):
        process=subprocess.Popen([sys.executable,'-I','-c','import time; time.sleep(30)'],
            stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
        parent=os.getpid()
        try:
            for identities in (((7,parent+1),),((7,parent),(8,parent)),
                               ((7,parent),(7,parent+1)),((7,parent),None)):
                with self.subTest(identities=identities),self.module.TerminalCancellation() as token:
                    with mock.patch.object(self.module,'_identity',side_effect=identities):
                        with self.assertRaises(RuntimeError): token._remember(process.pid,parent,process)
                    self.assertEqual(token._records,{})
                    self.assertIsNone(process.poll())
        finally:
            process.kill(); process.wait(timeout=3)

    def test_nonmain_thread_rejects_before_signal_change(self):
        errors=[]; previous=signal.getsignal(signal.SIGTERM)
        def worker():
            try:
                with self.module.TerminalCancellation(): errors.append('accepted')
            except RuntimeError: errors.append('blocked')
        thread=threading.Thread(target=worker); thread.start(); thread.join(timeout=2)
        self.assertFalse(thread.is_alive()); self.assertEqual(errors,['blocked'])
        self.assertIs(signal.getsignal(signal.SIGTERM),previous)

    def test_owned_family_stops_escaped_descendant_and_leaves_sibling(self):
        with tempfile.TemporaryDirectory(prefix='terminal-owned-family-') as directory:
            root=Path(directory); pidfile=root/'descendant.pid'
            body='import subprocess,sys,time\nfrom pathlib import Path\n'\
                'p=subprocess.Popen([sys.executable,"-c","import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(60)"],start_new_session=True)\n'\
                'Path('+repr(str(pidfile))+').write_text(str(p.pid))\ntime.sleep(60)\n'
            unrelated=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'],start_new_session=True)
            owned=None; child=None
            try:
                with self.module.TerminalCancellation() as token:
                    owned=subprocess.Popen([sys.executable,'-c',body],start_new_session=True)
                    token.publish_child(owned)
                    deadline=time.monotonic()+3
                    while not pidfile.exists() and time.monotonic()<deadline:
                        token.check(); time.sleep(.01)
                    self.assertTrue(pidfile.exists()); child=int(pidfile.read_text())
                    token.check()
                    os.kill(os.getpid(),signal.SIGTERM)
                    with self.assertRaises(self.module.TerminalCancelled): token.check()
                self.assertIsNotNone(owned.poll())
                self.assertFalse(Path(f'/proc/{child}').exists(),'owned descendant was not reaped')
                self.assertIsNone(unrelated.poll(),'unrelated sibling was terminated')
            finally:
                for pid in (child,owned.pid if owned else None,unrelated.pid):
                    if pid is not None:
                        try: os.kill(pid,signal.SIGKILL)
                        except ProcessLookupError: pass
                if owned: owned.wait(timeout=2)
                unrelated.wait(timeout=2)

    def test_gated_spawn_preserves_command_and_stdio(self):
        with self.module.TerminalCancellation() as token:
            self.assertTrue(callable(getattr(token,'spawn',None)),'gated spawn interface missing')
            process=token.spawn([sys.executable,'-c',
                'import sys; assert sys.argv[1:]==["argument with spaces"]; print("STDIO_OK")',
                'argument with spaces'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                env={'PATH':'/usr/bin:/bin'},start_new_session=True)
            stdout,stderr=process.communicate(timeout=3)
            self.assertEqual(process.returncode,0)
            self.assertEqual(stdout,b'STDIO_OK\n'); self.assertEqual(stderr,b'')

    def test_cancellation_during_publication_starts_no_target(self):
        with tempfile.TemporaryDirectory() as directory:
            marker=Path(directory)/'target-started'
            with self.module.TerminalCancellation() as token:
                self.assertTrue(callable(getattr(token,'spawn',None)),'gated spawn interface missing')
                publish=token.publish_child
                def cancelled(process):
                    publish(process); os.kill(os.getpid(),signal.SIGTERM)
                with mock.patch.object(token,'publish_child',side_effect=cancelled):
                    with self.assertRaises(self.module.TerminalCancelled):
                        token.spawn([sys.executable,'-c',
                            'from pathlib import Path; Path('+repr(str(marker))+').touch()'],
                            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
            self.assertFalse(marker.exists(),'target ran before ownership publication completed')

    def test_gated_spawn_reaps_fast_orphan_before_returning_success(self):
        with tempfile.TemporaryDirectory() as directory:
            pidfile=Path(directory)/'orphan.pid'; child=None
            try:
                with self.module.TerminalCancellation() as token:
                    self.assertTrue(callable(getattr(token,'spawn',None)),'gated spawn interface missing')
                    body='import subprocess,sys\nfrom pathlib import Path\n'\
                        'p=subprocess.Popen([sys.executable,"-c","import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(60)"],start_new_session=True)\n'\
                        'Path('+repr(str(pidfile))+').write_text(str(p.pid))\n'
                    process=token.spawn([sys.executable,'-c',body],stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,start_new_session=True)
                    self.assertEqual(process.wait(timeout=3),0)
                    child=int(pidfile.read_text())
                    self.assertFalse(Path(f'/proc/{child}').exists(),'escaped orphan survives successful supervisor exit')
            finally:
                if child is not None:
                    try: os.kill(child,signal.SIGKILL)
                    except ProcessLookupError: pass

    def test_terminating_one_owned_root_preserves_other_owned_root(self):
        with self.module.TerminalCancellation() as token:
            command=[sys.executable,'-c','import time;time.sleep(60)']
            first=token.spawn(command,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            second=token.spawn(command,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            token.terminate_child(first)
            self.assertIsNotNone(first.poll())
            self.assertIsNone(second.poll(),'independent owned root was closed prematurely')

    def test_unknown_prior_handler_blocks_without_overwriting_it(self):
        with mock.patch.object(self.module.signal,'getsignal',return_value=None), \
                mock.patch.object(self.module.signal,'signal') as changed:
            with self.assertRaisesRegex(RuntimeError,'terminal ownership unavailable'):
                with self.module.TerminalCancellation(): pass
            self.assertFalse(changed.called,'unrestorable signal handler was overwritten')

    def test_cleanup_failure_is_closed_and_restores_handlers(self):
        previous=signal.getsignal(signal.SIGTERM)
        process=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'],start_new_session=True)
        try:
            with self.assertRaisesRegex(RuntimeError,'^terminal cleanup failed$'):
                with self.module.TerminalCancellation() as token:
                    token.publish_child(process)
                    with mock.patch.object(self.module.signal,'pidfd_send_signal',side_effect=PermissionError('unexpected os failure')):
                        token.terminate_child(process)
            self.assertIs(signal.getsignal(signal.SIGTERM),previous)
        finally:
            process.kill(); process.wait(timeout=2)


if __name__=='__main__': unittest.main()
