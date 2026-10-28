"""Audit CLI/protocol controls; no sudo or native journal process is executed."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import ci_isolation_root as worker
import ci_isolation_linux as linux


class AuditWorkerTests(unittest.TestCase):
    def run_audit(self, directory, mode, *, cli=False):
        cache = Path(directory)/('b'*64); cache.mkdir()
        info = cache.stat(); nonce = 'a'*32
        request = json.dumps({'pids': [4321], 'window': [8.0, 9.0]})
        marker = {'nonce': nonce, 'source': 'b'*64, 'identity': [info.st_dev, info.st_ino]}
        def launch(argv, **kwargs):
            # Journalctl's documented parser contract, not the project's argv builder.
            valid = argv == ['/usr/bin/journalctl', '--dmesg', '--no-pager', '--output=json',
                             '--since', '@8.000000', '--until', '@9.000000']
            if mode == 'missing': raise FileNotFoundError('private tool details')
            rc = 0 if valid and mode == 'empty' else 7
            kwargs['stdout'].write(b'' if rc == 0 else b'private journal diagnostic')
            return SimpleNamespace(returncode=rc, poll=lambda: rc)
        output = io.StringIO()
        argv = ['audit-read', str(worker.ROOT/'tests/ci-runtime-lock.json'), nonce, request]
        with patch.object(worker.os, 'geteuid', return_value=0), \
                patch.object(worker, 'CACHE_BASE', Path(directory)), \
                patch.object(worker, 'load_runtime_spec', return_value=SimpleNamespace(source_sha256='b'*64)), \
                patch.object(worker, 'protected_directory'), \
                patch.object(worker, 'read_record', return_value=marker), \
                patch.object(worker, 'load_owned_runtime', return_value=SimpleNamespace(binary=Path('/synthetic/bwrap'))), \
                patch.object(worker, 'verify_installed_runtime'), \
                patch.object(worker.time, 'time', return_value=10.0), \
                patch.object(worker.subprocess, 'Popen', side_effect=launch), contextlib.redirect_stdout(output):
            if cli:
                self.assertTrue(callable(getattr(worker, 'cli', None)), 'closed worker diagnostic entrypoint missing')
                status = worker.cli(argv)
            else:
                worker.main(argv)
                status = 0
        return status, output.getvalue()

    def test_audit_uses_documented_kernel_filter_and_returns_false_for_empty_journal(self):
        with tempfile.TemporaryDirectory() as directory:
            try: status, output = self.run_audit(directory, 'empty')
            except ValueError:
                self.fail('documented journal filter must accept the audit command')
            self.assertEqual(status, 0)
            self.assertEqual(json.loads(output), {'matched': False})

    def test_worker_reports_internal_phase_code_and_numeric_tool_result_only(self):
        for mode, phase, error, rc in (
            ('nonzero', 'AUDIT_JOURNAL_WAIT', 'CI_ROOT_COMMAND_FAILED', 7),
            ('missing', 'AUDIT_JOURNAL_SPAWN', 'OS_ERROR', None),
        ):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                status, output = self.run_audit(directory, mode, cli=True)
                self.assertEqual(status, 1)
                self.assertTrue(output.startswith('CI_ROOT_FAILURE '))
                self.assertEqual(json.loads(output.removeprefix('CI_ROOT_FAILURE ')),
                                 {'phase': phase, 'error': error, 'workerReturnCode': 1, 'commandReturnCode': rc})
                self.assertNotIn('private', output)
                self.assertNotIn(directory, output)

    def test_parent_preserves_valid_worker_failure_without_exporting_stream(self):
        detail = {'phase': 'AUDIT_JOURNAL_WAIT', 'error': 'CI_ROOT_COMMAND_FAILED',
                  'workerReturnCode': 1, 'commandReturnCode': 7}
        with tempfile.TemporaryDirectory() as directory:
            executor = linux.LinuxExecutor(SimpleNamespace(source_sha256='a'*64), Path(directory), 'b'*32, 'c'*64)
            def launch(argv, **kwargs):
                self.assertEqual(argv[0], '/usr/bin/sudo')
                kwargs['stdout'].write(b'CI_ROOT_FAILURE ' + json.dumps(detail).encode() + b'\n')
                return SimpleNamespace(returncode=1, poll=lambda: 1)
            with patch.object(linux.subprocess, 'Popen', side_effect=launch), self.assertRaises(ValueError) as caught:
                executor.root_action('audit-read', time.monotonic()+5, '{}')
            self.assertEqual(caught.exception.args, ('CI_ROOT_WORKER_FAILED', detail))

    def test_malformed_frames_and_transport_exits_remain_finite_failures(self):
        from ci_worker_diagnostics import decode_failure
        good = b'CI_ROOT_FAILURE {"phase":"AUDIT_REQUEST","error":"CI_AUDIT_SCOPE_REJECTED","workerReturnCode":1,"commandReturnCode":null}'
        for payload, rc, error in (
            (b'private transport output', 124, 'CI_ROOT_TRANSPORT_FAILED'),
            (good + b' private trailing output', 1, 'CI_ROOT_PROTOCOL_INVALID'),
            (good.replace(b'"AUDIT_REQUEST"', b'"private"'), 1, 'CI_ROOT_PROTOCOL_INVALID'),
            (good.replace(b'"workerReturnCode":1', b'"workerReturnCode":true'), 1, 'CI_ROOT_PROTOCOL_INVALID'),
            (good.replace(b'"commandReturnCode":null', b'"commandReturnCode":256'), 1, 'CI_ROOT_PROTOCOL_INVALID'),
            (good.replace(b'"phase":"AUDIT_REQUEST"', b'"phase":"ROOT_SCOPE","phase":"AUDIT_REQUEST"'), 1, 'CI_ROOT_PROTOCOL_INVALID'),
            (good, 124, 'CI_ROOT_PROTOCOL_INVALID'),
            (b'CI_ROOT_FAILURE ' + b'x'*1025, 1, 'CI_ROOT_PROTOCOL_INVALID'),
            (b'CI_ROOT_FAILURE \xff', 1, 'CI_ROOT_PROTOCOL_INVALID'),
        ):
            with self.subTest(rc=rc, length=len(payload)):
                self.assertEqual(decode_failure(payload, rc), {'phase': 'TRANSPORT', 'error': error,
                                  'workerReturnCode': rc, 'commandReturnCode': None})

    def test_only_valid_worker_detail_can_enter_public_diagnostics(self):
        import ci_diagnostics as diag
        self.assertIn('workerFailure', diag.empty_diagnostics())
        value = {'phase': 'AUDIT_JOURNAL_WAIT', 'error': 'CI_ROOT_COMMAND_FAILED',
                 'workerReturnCode': 1, 'commandReturnCode': -9}
        record = {**diag.empty_diagnostics(), 'phase': 'PREPARE', 'stage': 'POLICY_AUDIT',
                  'error': 'CI_ROOT_WORKER_FAILED', 'workerFailure': value}
        self.assertEqual(diag.validate_diagnostics(record), record)
        for detail in ({**value, 'phase': 'private'}, {**value, 'error': 'private'},
                       {**value, 'commandReturnCode': True}, {**value, 'commandReturnCode': -129},
                       {**value, 'workerReturnCode': 256}, {**value, 'text': 'private'}):
            with self.subTest(keys=sorted(detail)), self.assertRaises(ValueError):
                diag.validate_diagnostics({**record, 'workerFailure': detail})
        with self.assertRaises(ValueError):
            diag.validate_diagnostics({**record, 'error': 'CI_COMMAND_FAILED'})
        self.assertEqual(diag.error_code(ValueError('CI_ROOT_WORKER_FAILED')), 'UNKNOWN_ERROR')
        self.assertEqual(diag.error_code(ValueError('CI_ROOT_WORKER_FAILED', {'text': 'private'})), 'UNKNOWN_ERROR')

    def test_inner_timeout_and_output_limit_keep_numeric_result_and_no_stream(self):
        from ci_worker_diagnostics import encode_failure
        for mode, expected, rc in (('timeout', 'CI_ROOT_COMMAND_TIMEOUT', -9),
                                   ('oversize', 'CI_ROOT_COMMAND_OUTPUT_LIMIT', 0)):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                trace = {'phase': 'ROOT_SCOPE', 'commandReturnCode': None}
                process = SimpleNamespace(pid=4321, returncode=None if mode == 'timeout' else 0)
                process.poll = lambda: process.returncode
                def wait(**kwargs): process.returncode = -9; return -9
                process.wait = wait
                def launch(argv, **kwargs):
                    if mode == 'oversize': kwargs['stdout'].write(b'x'*(512*1024+1))
                    return process
                with patch.object(worker.subprocess, 'Popen', side_effect=launch), \
                        patch.object(worker.os, 'killpg'), \
                        patch.object(worker.time, 'monotonic', side_effect=[0.0, 16.0]), \
                        self.assertRaises(ValueError) as caught:
                    worker.bounded_root_command(['/synthetic/journal'], directory, trace=trace)
                payload = json.loads(encode_failure(trace, caught.exception).removeprefix('CI_ROOT_FAILURE '))
                self.assertEqual(payload, {'phase': 'AUDIT_JOURNAL_WAIT', 'error': expected,
                                           'workerReturnCode': 1, 'commandReturnCode': rc})

    def test_parent_deadline_failure_keeps_transport_phase_and_reaped_result(self):
        with tempfile.TemporaryDirectory() as directory:
            executor = linux.LinuxExecutor(SimpleNamespace(source_sha256='a'*64), Path(directory), 'b'*32, 'c'*64)
            process = SimpleNamespace(pid=4321, returncode=None)
            process.poll = lambda: process.returncode
            def wait(**kwargs): process.returncode = -15; return -15
            process.wait = wait
            with patch.object(linux.subprocess, 'Popen', return_value=process), \
                    patch.object(linux.os, 'killpg'), \
                    patch.object(linux.time, 'monotonic', side_effect=[0.0, 6.0]), self.assertRaises(ValueError) as caught:
                executor.root_action('audit-read', 5.0, '{}')
            self.assertEqual(caught.exception.args, ('CI_ROOT_WORKER_FAILED',
                {'phase': 'TRANSPORT', 'error': 'CI_ROOT_COMMAND_TIMEOUT',
                 'workerReturnCode': -15, 'commandReturnCode': None}))

    def test_parent_reap_failure_does_not_replace_primary_timeout(self):
        with tempfile.TemporaryDirectory() as directory:
            executor = linux.LinuxExecutor(SimpleNamespace(source_sha256='a'*64), Path(directory), 'b'*32, 'c'*64)
            process = SimpleNamespace(pid=4321, returncode=None, poll=lambda: None)
            def wait(**kwargs): raise linux.subprocess.TimeoutExpired('/synthetic', 5)
            process.wait = wait
            with patch.object(linux.subprocess, 'Popen', return_value=process), \
                    patch.object(linux.os, 'killpg'), \
                    patch.object(linux.time, 'monotonic', side_effect=[0.0, 6.0]), \
                    self.assertRaises((ValueError, linux.subprocess.TimeoutExpired)) as caught:
                executor.root_action('audit-read', 5.0, '{}')
            self.assertEqual(caught.exception.args, ('CI_ROOT_WORKER_FAILED',
                {'phase': 'TRANSPORT', 'error': 'CI_ROOT_COMMAND_TIMEOUT',
                 'workerReturnCode': None, 'commandReturnCode': None}))

    def test_inner_reap_failure_does_not_replace_primary_timeout(self):
        trace = {'phase': 'ROOT_SCOPE', 'commandReturnCode': None}
        process = SimpleNamespace(pid=4321, returncode=None, poll=lambda: None)
        def wait(**kwargs): raise worker.subprocess.TimeoutExpired('/synthetic', 5)
        process.wait = wait
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(worker.subprocess, 'Popen', return_value=process), \
                patch.object(worker.os, 'killpg'), \
                patch.object(worker.time, 'monotonic', side_effect=[0.0, 16.0]), \
                self.assertRaises((ValueError, worker.subprocess.TimeoutExpired)) as caught:
            worker.bounded_root_command(['/synthetic'], directory, trace=trace)
        self.assertEqual(caught.exception.args, ('CI_ROOT_COMMAND_TIMEOUT',))
        self.assertIsNone(trace['commandReturnCode'])

    def test_parent_completed_output_bound_is_not_a_generic_transport_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            executor = linux.LinuxExecutor(SimpleNamespace(source_sha256='a'*64), Path(directory), 'b'*32, 'c'*64)
            def launch(argv, **kwargs):
                kwargs['stdout'].write(b'x'*(512*1024+1))
                return SimpleNamespace(returncode=0, poll=lambda: 0)
            with patch.object(linux.subprocess, 'Popen', side_effect=launch), self.assertRaises(ValueError) as caught:
                executor.root_action('audit-read', time.monotonic()+5, '{}')
            self.assertEqual(caught.exception.args, ('CI_ROOT_WORKER_FAILED',
                {'phase': 'TRANSPORT', 'error': 'CI_ROOT_COMMAND_OUTPUT_LIMIT',
                 'workerReturnCode': 0, 'commandReturnCode': None}))

    def test_parent_spawn_error_keeps_finite_transport_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            executor = linux.LinuxExecutor(SimpleNamespace(source_sha256='a'*64), Path(directory), 'b'*32, 'c'*64)
            with patch.object(linux.subprocess, 'Popen', side_effect=FileNotFoundError('private')), \
                    self.assertRaises((ValueError, OSError)) as caught:
                executor.root_action('audit-read', time.monotonic()+5, '{}')
            self.assertEqual(caught.exception.args, ('CI_ROOT_WORKER_FAILED',
                {'phase': 'TRANSPORT', 'error': 'OS_ERROR',
                 'workerReturnCode': None, 'commandReturnCode': None}))

    def test_failed_reaping_reaches_public_cli_without_traceback_or_content(self):
        import ci_isolation_bootstrap as bootstrap
        import os
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); report = root/'report.json'; output = io.StringIO()
            executor = linux.LinuxExecutor(SimpleNamespace(source_sha256='a'*64), root, 'b'*32, 'c'*64)
            executor.probe_records = [(1.0, 2.0, (4321,), ())]
            executor.namespace_probe = lambda *args: False
            runtime = SimpleNamespace(receipt=SimpleNamespace(binary_sha256='d'*64))
            process = SimpleNamespace(pid=4321, returncode=None, poll=lambda: None)
            clock = [0.0]
            def launch(*args, **kwargs): clock[0] = 1000.0; return process
            def wait(**kwargs): raise linux.subprocess.TimeoutExpired('/private-command', 5)
            process.wait = wait
            def cleanup(*args, **kwargs): executor.stage = 'CLEANUP_CACHE'; return True
            with patch.dict(os.environ, {'GITHUB_RUN_ID': '1', 'GITHUB_RUN_ATTEMPT': '1', 'GITHUB_SHA': 'a'*40}), \
                    patch.object(bootstrap, '_hosted_environment', return_value=root), \
                    patch.object(bootstrap, '_executor', return_value=executor), \
                    patch.object(bootstrap, 'provision_runtime', return_value=runtime), \
                    patch.object(bootstrap, 'verify_installed_runtime'), \
                    patch.object(bootstrap, '_cleanup', side_effect=cleanup), \
                    patch.object(linux.subprocess, 'Popen', side_effect=launch), \
                    patch.object(linux.os, 'killpg'), \
                    patch.object(linux.time, 'monotonic', side_effect=lambda: clock[0]), \
                    contextlib.redirect_stdout(output):
                self.assertEqual(bootstrap.main(['--prepare', '--manifest', 'tests/ci-runtime-lock.json',
                                                 '--report', str(report)]), 1)
                value = bootstrap._read_report(report)['diagnostics']
            self.assertEqual(value['error'], 'CI_ROOT_WORKER_FAILED')
            self.assertEqual(value['workerFailure'], {'phase': 'TRANSPORT', 'error': 'CI_ROOT_COMMAND_TIMEOUT',
                              'workerReturnCode': None, 'commandReturnCode': None})
            self.assertEqual(value['cleanup'], 'PASSED')  # runtime/cache cleanup, not child-reaping proof
            for forbidden in ('Traceback', 'private-command', directory): self.assertNotIn(forbidden, output.getvalue())

    def test_parent_output_open_failure_is_finite_without_a_process(self):
        with tempfile.TemporaryDirectory() as directory:
            executor = linux.LinuxExecutor(SimpleNamespace(source_sha256='a'*64), Path(directory), 'b'*32, 'c'*64)
            with patch.object(linux.tempfile, 'TemporaryFile', side_effect=PermissionError('private')), \
                    self.assertRaises(ValueError) as caught:
                executor.root_action('audit-read', time.monotonic()+5, '{}')
            self.assertEqual(caught.exception.args, ('CI_ROOT_WORKER_FAILED',
                {'phase': 'TRANSPORT', 'error': 'OS_ERROR', 'workerReturnCode': None, 'commandReturnCode': None}))

    def test_parent_running_output_bound_matches_completed_output_classification(self):
        with tempfile.TemporaryDirectory() as directory:
            executor = linux.LinuxExecutor(SimpleNamespace(source_sha256='a'*64), Path(directory), 'b'*32, 'c'*64)
            process = SimpleNamespace(pid=4321, returncode=None)
            process.poll = lambda: process.returncode
            def wait(**kwargs): process.returncode = -15; return -15
            process.wait = wait
            def launch(argv, **kwargs): kwargs['stdout'].write(b'x'*(512*1024+1)); return process
            with patch.object(linux.subprocess, 'Popen', side_effect=launch), \
                    patch.object(linux.os, 'killpg'), self.assertRaises(ValueError) as caught:
                executor.root_action('audit-read', time.monotonic()+5, '{}')
            self.assertEqual(caught.exception.args, ('CI_ROOT_WORKER_FAILED',
                {'phase': 'TRANSPORT', 'error': 'CI_ROOT_COMMAND_OUTPUT_LIMIT',
                 'workerReturnCode': -15, 'commandReturnCode': None}))


if __name__ == '__main__': unittest.main()
