"""Canonical workflow contract and no-provider execution of selected real steps."""
from dataclasses import dataclass
import importlib
import contextlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
JOBS = (("ci.yml", "package-validate"), ("release.yml", "validate"),
        ("scheduled-maintenance.yml", "full-validation"))
ORDER = ("isolation_prepare", "terminal_provision", "isolation_verify", "package_gate", "isolation_cleanup")


@dataclass(frozen=True)
class Step:
    name: str
    script: str
    always: bool
    report: str


def full_job(text, name):
    match = re.search(r"^  " + re.escape(name) + r":\n(.*?)(?=^  [a-zA-Z0-9_-]+:|\Z)", text, re.M | re.S)
    if match is None:
        raise ValueError("CI_FULL_JOB_MISSING")
    return match[1]


def validate_job(text, name):
    job = full_job(text, name)
    # This is a closed lifecycle contract, not a general GitHub YAML validator.
    # runner context is unavailable at jobs.<job_id>.env. All lifecycle bindings
    # must instead be explicit step environments, including always-run cleanup.
    if re.search(r"^    env:", job, re.M):
        raise ValueError("CI_FULL_JOB_ENV_SCOPE_INVALID")
    required = ("    runs-on: ubuntu-24.04", "    timeout-minutes: 40",
                "    permissions:\n      contents: read", "          persist-credentials: false")
    if any(job.count(token) != 1 for token in required):
        raise ValueError("CI_FULL_JOB_BOUNDARY_INVALID")
    if ("issues: write" in job or "contents: write" in job or "continue-on-error:" in job
            or re.search(r"\bsudo\b|sysctl|aa-disable|aa-complain", job)):
        raise ValueError("CI_FULL_JOB_AUTHORITY_EXPANDED")
    chunks = re.split(r"^      - ", job, flags=re.M)[1:]
    steps = []
    for chunk in chunks:
        identifier = re.findall(r"^        id: ([a-z_]+)$", chunk, re.M)
        if not identifier:
            continue
        if len(identifier) != 1 or identifier[0] not in ORDER:
            raise ValueError("CI_FULL_JOB_STAGE_INVALID")
        stage = identifier[0]
        environments = re.findall(r"^        env:\n((?:          [^\n]*\n)+)", chunk, re.M)
        reports = re.findall(r"^          CI_ISOLATION_REPORT: (.+)$", chunk, re.M)
        if (len(environments) != 1 or reports != ["${{ runner.temp }}/ci-isolation-report.json"]
                or re.findall(r"^          CI_ISOLATION_REPORT: (.+)$", environments[0], re.M) != reports):
            raise ValueError("CI_FULL_JOB_REPORT_SCOPE_INVALID")
        condition = re.findall(r"^        if: (.+)$", chunk, re.M)
        if condition != (["always()"] if stage == "isolation_cleanup" else []):
            raise ValueError("CI_FULL_JOB_STAGE_CONDITIONAL")
        match = re.search(r"^        run: (.*)$", chunk, re.M)
        if match is None:
            raise ValueError("CI_FULL_JOB_COMMAND_MISSING")
        if match[1] == "|":
            body = chunk[match.end():].splitlines()
            script = "\n".join(line[10:] for line in body if line.startswith("          "))
        else:
            script = match[1]
        if stage.startswith("isolation_"):
            mode = {"isolation_prepare": "prepare", "isolation_verify": "verify", "isolation_cleanup": "cleanup"}[stage]
            expected = f'python3 tests/ci_isolation_bootstrap.py --{mode} --manifest tests/ci-runtime-lock.json --report "$CI_ISOLATION_REPORT"'
            if script != expected:
                raise ValueError("CI_FULL_JOB_BOOTSTRAP_DRIFT")
        elif stage == "package_gate" and script != "bash tests/validate-package.sh":
            raise ValueError("CI_FULL_JOB_GATE_DRIFT")
        elif stage == "terminal_provision" and "python3 tests/provision-terminal-runtime.py" not in script:
            raise ValueError("CI_FULL_JOB_TERMINAL_DRIFT")
        steps.append(Step(stage, script, bool(condition), reports[0]))
    if tuple(step.name for step in steps) != ORDER:
        raise ValueError("CI_FULL_JOB_ORDER_INVALID")
    return steps


def check_workflows(root=ROOT):
    for file, job in JOBS:
        validate_job((root / ".github/workflows" / file).read_text(), job)


class WiringTests(unittest.TestCase):
    def test_namespace_audit_failure_survives_prepare_cleanup_report_and_stdout(self):
        import ci_isolation_bootstrap as bootstrap
        cases = ((ValueError('CI_COMMAND_FAILED'), 'CI_COMMAND_FAILED'),
                 (ValueError('CI_ROOT_WORKER_FAILED', {'phase': 'AUDIT_JOURNAL_WAIT',
                   'error': 'CI_ROOT_COMMAND_FAILED', 'workerReturnCode': 1, 'commandReturnCode': 7}), 'CI_ROOT_WORKER_FAILED'),
                 (ValueError('CI_POLICY_EVIDENCE_MISSING'), 'CI_POLICY_EVIDENCE_MISSING'),
                 (ValueError('CI_POLICY_EVIDENCE_REJECTED'), 'CI_POLICY_EVIDENCE_REJECTED'),
                 (OSError('private transport details'), 'OS_ERROR'),
                 (ValueError('private received content'), 'UNKNOWN_ERROR'),
                 (type('UntrustedError', (ValueError,), {})('CI_COMMAND_FAILED'), 'UNKNOWN_ERROR'))
        for error, expected in cases:
            for cleaned in (True, False):
                with self.subTest(code=expected, cleaned=cleaned), tempfile.TemporaryDirectory() as directory:
                    root = Path(directory); report = root/'report.json'; output = io.StringIO()
                    executor = SimpleNamespace(stage='NAMESPACE_FULL', spec=object(), primary_failure=None)
                    executor.namespace_probe = lambda *args: False
                    def audit(*args):
                        executor.stage = 'POLICY_AUDIT'
                        raise error
                    executor.denial_evidence = audit
                    def snapshot(*args): self.fail('audit failure reached the policy snapshot')
                    executor.snapshot_policy = snapshot
                    def cleanup(*args, **kwargs):
                        executor.stage = 'CLEANUP_CACHE'
                        return cleaned
                    with patch.dict(os.environ, {'GITHUB_RUN_ID': '1', 'GITHUB_RUN_ATTEMPT': '1',
                                                 'GITHUB_SHA': 'a'*40}), \
                            patch.object(bootstrap, '_hosted_environment', return_value=root), \
                            patch.object(bootstrap, '_executor', return_value=executor), \
                            patch.object(bootstrap, 'provision_runtime', return_value=object()), \
                            patch.object(bootstrap, 'verify_installed_runtime'), \
                            patch.object(bootstrap, '_cleanup', side_effect=cleanup), contextlib.redirect_stdout(output):
                        self.assertEqual(bootstrap.main(['--prepare', '--manifest', 'tests/ci-runtime-lock.json',
                                                         '--report', str(report)]), 1)
                        if cleaned:
                            bootstrap.cleanup_cli(report, root)
                        else:
                            with self.assertRaises(ValueError): bootstrap.cleanup_cli(report, root)
                        record = bootstrap._read_report(report)
                    projection = json.loads(output.getvalue().splitlines()[0].removeprefix('CI_BOOTSTRAP_DIAGNOSTICS '))
                    for diag in (record['diagnostics'], projection):
                        self.assertEqual((diag['phase'], diag['stage'], diag['error']),
                                         ('PREPARE', 'POLICY_AUDIT', expected))
                        self.assertEqual(diag['cleanup'], 'PASSED' if cleaned else 'FAILED')
                        if expected == 'CI_ROOT_WORKER_FAILED':
                            self.assertEqual(diag.get('workerFailure'), error.args[1])
                    for forbidden in ('private', directory, 'UntrustedError'):
                        self.assertNotIn(forbidden, output.getvalue() + report.read_text())

    def test_first_apt_rejection_survives_prepare_cleanup_and_stdout_without_content(self):
        import ci_isolation_bootstrap as bootstrap
        from ci_image_upgrade import parse_apt_simulation
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); report = root / 'report.json'; output = io.StringIO()
            executor = SimpleNamespace(stage='PACKAGE_UPGRADE_SIMULATE', spec=object())
            def reject(*args, **kwargs): parse_apt_simulation('\nN: demo\nW: later\n')
            def cleanup(*args, **kwargs):
                executor.stage = 'CLEANUP_CACHE'
                return True
            with patch.dict(os.environ, {'GITHUB_RUN_ID': '1', 'GITHUB_RUN_ATTEMPT': '1', 'GITHUB_SHA': 'a'*40}), \
                    patch.object(bootstrap, '_hosted_environment', return_value=root), \
                    patch.object(bootstrap, '_executor', return_value=executor), \
                    patch.object(bootstrap, 'provision_runtime', side_effect=reject), \
                    patch.object(bootstrap, '_cleanup', side_effect=cleanup), contextlib.redirect_stdout(output):
                self.assertEqual(bootstrap.main(['--prepare', '--manifest', 'tests/ci-runtime-lock.json',
                                                 '--report', str(report)]), 1)
                bootstrap.cleanup_cli(report, root)
                record = bootstrap._read_report(report)
            self.assertEqual(record['schemaVersion'], 4)
            projection = json.loads(output.getvalue().splitlines()[0].removeprefix('CI_BOOTSTRAP_DIAGNOSTICS '))
            for diag in (record['diagnostics'], projection):
                self.assertEqual(diag['aptRejection'], dict(kind='NOTICE', line=2, length=7))
                self.assertEqual((diag['stage'], diag['error'], diag['cleanup']),
                                 ('PACKAGE_UPGRADE_SIMULATE', 'APT_SIMULATION_UNRECOGNIZED', 'PASSED'))
            for text in (report.read_text(), output.getvalue()):
                for forbidden in ('N: demo', 'W: later', directory): self.assertNotIn(forbidden, text)

    def test_rejection_projection_rejects_content_and_invalid_scalar_contracts(self):
        import ci_diagnostics as diagnostics
        valid = {**diagnostics.empty_diagnostics(), 'phase': 'PREPARE', 'stage': 'PACKAGE_UPGRADE_SIMULATE',
                 'error': 'APT_SIMULATION_UNRECOGNIZED', 'aptRejection': dict(kind='NOTICE', line=2, length=7)}
        try: validated = diagnostics.validate_diagnostics(valid)
        except ValueError: validated = None
        self.assertEqual(validated, valid, 'bounded rejection projection must be accepted')
        for detail in ({'kind': 'untrusted', 'line': 2, 'length': 7},
                       {'kind': 'NOTICE', 'line': True, 'length': 7},
                       {'kind': 'NOTICE', 'line': 4097, 'length': 7},
                       {'kind': 'NOTICE', 'line': 2, 'length': 524289},
                       {'kind': 'NOTICE', 'line': 0, 'length': 7},
                       {'kind': 'NOTICE', 'line': 2, 'length': 0},
                       {'kind': 'NOTICE', 'line': 2, 'length': True},
                       {'kind': 'NOTICE', 'line': 2, 'length': 7, 'text': 'not-exported'}):
            with self.subTest(keys=sorted(detail)), self.assertRaises(ValueError):
                diagnostics.validate_diagnostics({**valid, 'aptRejection': detail})
        with self.assertRaises(ValueError):
            diagnostics.validate_diagnostics({**valid, 'error': 'CI_COMMAND_FAILED'})
        self.assertIsNone(diagnostics.empty_diagnostics()['aptRejection'])
        for error in (ValueError('APT_SIMULATION_UNRECOGNIZED', 'NOTICE', True, 7),
                      ValueError('APT_SIMULATION_UNRECOGNIZED', 'private-text', 2, 7),
                      type('UntrustedError', (ValueError,), {})('APT_SIMULATION_UNRECOGNIZED', 'NOTICE', 2, 7)):
            self.assertEqual(diagnostics.error_code(error), 'UNKNOWN_ERROR')

    def test_primary_apt_rejection_survives_failed_cleanup_and_later_errors(self):
        from ci_diagnostics import empty_diagnostics, record_cleanup, record_failure, remember_failure
        executor = SimpleNamespace(stage='PACKAGE_UPGRADE_SIMULATE')
        remember_failure(executor, 'PREPARE', ValueError('APT_SIMULATION_UNRECOGNIZED', 'NOTICE', 2, 7))
        executor.stage = 'CLEANUP_CACHE'
        record = dict(diagnostics=empty_diagnostics())
        record_failure(record, 'PREPARE', ValueError('CI_COMMAND_FAILED'), executor)
        record_cleanup(record, False, executor)
        record_failure(record, 'CLEANUP', ValueError('CLEANUP_UNPROVEN'), executor)
        self.assertEqual(record['diagnostics'].get('aptRejection'), dict(kind='NOTICE', line=2, length=7))
        self.assertEqual(record['diagnostics']['error'], 'APT_SIMULATION_UNRECOGNIZED')
        self.assertEqual(record['diagnostics']['cleanupError'], 'CLEANUP_UNPROVEN')

    def test_real_apt_parser_codes_survive_prepare_cleanup_and_stdout(self):
        import ci_isolation_bootstrap as bootstrap
        from ci_image_upgrade import parse_apt_simulation
        cases = [('', 'APT_SIMULATION_INVALID'),
                 ('0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.\nUnmodelled notice\n',
                  'APT_SIMULATION_UNRECOGNIZED'),
                 ('1 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.\n',
                  'APT_SIMULATION_DRIFT'),
                 ('0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.\n' * 2,
                  'APT_SIMULATION_AMBIGUOUS')]
        for sample, expected in cases:
            with self.subTest(code=expected), tempfile.TemporaryDirectory() as directory:
                root = Path(directory); report = root/'report.json'; output = io.StringIO()
                executor = SimpleNamespace(stage='PACKAGE_UPGRADE_SIMULATE', spec=object())
                def fail_parser(*args, **kwargs): parse_apt_simulation(sample)
                def cleanup(*args, **kwargs):
                    executor.stage = 'CLEANUP_CACHE'
                    return True
                with patch.dict(os.environ, {'GITHUB_RUN_ID': '1', 'GITHUB_RUN_ATTEMPT': '1', 'GITHUB_SHA': 'a'*40}), \
                        patch.object(bootstrap, '_hosted_environment', return_value=root), \
                        patch.object(bootstrap, '_executor', return_value=executor), \
                        patch.object(bootstrap, 'provision_runtime', side_effect=fail_parser), \
                        patch.object(bootstrap, '_cleanup', side_effect=cleanup), contextlib.redirect_stdout(output):
                    self.assertEqual(bootstrap.main(['--prepare', '--manifest', 'tests/ci-runtime-lock.json',
                                                     '--report', str(report)]), 1)
                    record = bootstrap._read_report(report)
                    self.assertEqual(record['diagnostics']['error'], expected)
                    self.assertEqual(record['diagnostics']['stage'], 'PACKAGE_UPGRADE_SIMULATE')
                    self.assertEqual(record['diagnostics']['cleanup'], 'PASSED')
                    bootstrap.cleanup_cli(report, root)
                    self.assertEqual(bootstrap._read_report(report)['diagnostics']['error'], expected)
                projection = json.loads(output.getvalue().splitlines()[0].removeprefix('CI_BOOTSTRAP_DIAGNOSTICS '))
                self.assertEqual(projection['error'], expected)
                self.assertNotIn('Unmodelled', output.getvalue())
                self.assertNotIn(directory, output.getvalue())
        from ci_diagnostics import error_code
        self.assertEqual(error_code(ValueError('APT_SIMULATION_UNREVIEWED')), 'UNKNOWN_ERROR')
        self.assertEqual(error_code(ValueError('untrusted message')), 'UNKNOWN_ERROR')

    def test_prepare_reports_closed_primary_failure_before_cleanup_overwrites_stage(self):
        import ci_isolation_bootstrap as bootstrap
        for error, expected in ((ValueError('PACKAGE_STATE_UNPROVEN'), 'PACKAGE_STATE_UNPROVEN'),
                                (ValueError('untrusted path/URL/secret text'), 'UNKNOWN_ERROR')):
            for cleanup_success in (True, False):
                with self.subTest(code=expected, cleanup=cleanup_success), tempfile.TemporaryDirectory() as directory:
                    root = Path(directory); report = root / 'report.json'
                    executor = SimpleNamespace(stage='PACKAGE_SNAPSHOT', spec=object())
                    def cleanup(*args, **kwargs):
                        executor.stage = 'CLEANUP_CACHE'
                        return cleanup_success
                    with patch.dict(os.environ, {'GITHUB_RUN_ID': '1', 'GITHUB_RUN_ATTEMPT': '1',
                                                 'GITHUB_SHA': 'a'*40}), \
                            patch.object(bootstrap, '_executor', return_value=executor), \
                            patch.object(bootstrap, 'provision_runtime', side_effect=error), \
                            patch.object(bootstrap, '_cleanup', side_effect=cleanup):
                        with self.assertRaises(ValueError): bootstrap.prepare_cli(report, root)
                        record = bootstrap._read_report(report)
                        self.assertIn('diagnostics', record)
                        diag = record['diagnostics']
                        self.assertEqual((diag['phase'], diag['stage'], diag['error']),
                                         ('PREPARE', 'PACKAGE_SNAPSHOT', expected))
                        self.assertEqual(diag['cleanup'], 'PASSED' if cleanup_success else 'FAILED')
                        # An always-run cleanup cannot erase the original failure.
                        if not cleanup_success:
                            with self.assertRaises(ValueError): bootstrap.cleanup_cli(report, root)
                        else:
                            bootstrap.cleanup_cli(report, root)
                        self.assertEqual(bootstrap._read_report(report)['diagnostics']['error'], expected)
                        projection = bootstrap.diagnostic_summary(record)
                        self.assertLess(len(projection), 1024)
                        for forbidden in ('untrusted', directory, 'nonce', 'workspaceIdentity', 'runId', 'githubSha'):
                            self.assertNotIn(forbidden, projection)
                        self.assertTrue(projection.startswith('CI_BOOTSTRAP_DIAGNOSTICS '))

    def test_diagnostic_contract_rejects_unknown_fields_codes_and_untrusted_stage(self):
        import ci_diagnostics as diagnostics
        valid = diagnostics.empty_diagnostics()
        self.assertEqual(diagnostics.failure_stage(SimpleNamespace(stage='untrusted secret')), 'UNKNOWN_STAGE')
        for changed in ({**valid, 'error': 'UNREVIEWED'}, {**valid, 'stage': '../private'},
                        {**valid, 'extra': 'content'}, {**valid, 'cleanup': True}):
            with self.assertRaises(ValueError): diagnostics.validate_diagnostics(changed)

    def test_hosted_failure_emits_only_structural_whitelist_and_rejects_old_report_schema(self):
        import ci_isolation_bootstrap as bootstrap
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); report = root / 'report.json'
            executor = SimpleNamespace(stage='PACKAGE_REFRESH', spec=object())
            output = io.StringIO()
            with patch.dict(os.environ, {'GITHUB_RUN_ID': '1', 'GITHUB_RUN_ATTEMPT': '1', 'GITHUB_SHA': 'a'*40}), \
                    patch.object(bootstrap, '_hosted_environment', return_value=root), \
                    patch.object(bootstrap, '_executor', return_value=executor), \
                    patch.object(bootstrap, 'provision_runtime', side_effect=ValueError('CI_COMMAND_FAILED')), \
                    patch.object(bootstrap, '_cleanup', return_value=True), contextlib.redirect_stdout(output):
                status = bootstrap.main(['--prepare', '--manifest', 'tests/ci-runtime-lock.json', '--report', str(report)])
                self.assertEqual(status, 1)
                lines = output.getvalue().splitlines()
                self.assertEqual(len(lines), 2)
                self.assertEqual(lines[-1], 'CI_BOOTSTRAP_BLOCKED')
                data = json.loads(lines[0].removeprefix('CI_BOOTSTRAP_DIAGNOSTICS '))
                self.assertEqual(set(data), {'phase', 'stage', 'error', 'cleanup', 'cleanupStage', 'cleanupError', 'aptRejection', 'workerFailure'})
                self.assertIsNone(data['aptRejection'])
                self.assertEqual((data['stage'], data['error']), ('PACKAGE_REFRESH', 'CI_COMMAND_FAILED'))
                record = json.loads(report.read_text())
                for old in (1, 2, 3):
                    record['schemaVersion'] = old
                    report.write_text(json.dumps(record))
                    with self.assertRaisesRegex(ValueError, 'CI_REPORT_INVALID'): bootstrap._read_report(report)

    def test_internal_cleanup_does_not_replace_primary_failure_stage_or_code(self):
        from ci_diagnostics import empty_diagnostics, record_failure, remember_failure
        executor = SimpleNamespace(stage='RUNTIME_PUBLISH')
        remember_failure(executor, 'PREPARE', ValueError('RUNTIME_BINARY_CHANGED'))
        executor.stage = 'CLEANUP_RUNTIME'
        record = dict(diagnostics=empty_diagnostics())
        record_failure(record, 'PREPARE', ValueError('CI_POLICY_CLEANUP_FAILED'), executor)
        self.assertEqual((record['diagnostics']['stage'], record['diagnostics']['error']),
                         ('RUNTIME_PUBLISH', 'RUNTIME_BINARY_CHANGED'))
        record_failure(record, 'CLEANUP', ValueError('CLEANUP_UNPROVEN'), executor)
        self.assertEqual(record['diagnostics']['error'], 'RUNTIME_BINARY_CHANGED')

    def test_each_stage_rejects_missing_duplicate_or_foreign_report_binding(self):
        binding = "          CI_ISOLATION_REPORT: ${{ runner.temp }}/ci-isolation-report.json\n"
        for file, job in JOBS:
            source = (ROOT / ".github/workflows" / file).read_text()
            for stage in ORDER:
                start = source.index("        id: " + stage + "\n")
                end = source.find("      - ", start)
                end = len(source) if end == -1 else end
                chunk = source[start:end]
                for replacement in ("", binding + binding,
                                    binding.replace("runner.temp", "github.workspace"),
                                    binding.replace("/ci-isolation-report.json", "/../foreign.json")):
                    mutated = source[:start] + chunk.replace(binding, replacement, 1) + source[end:]
                    with self.subTest(file=file, stage=stage, replacement=replacement), \
                            self.assertRaisesRegex(ValueError, "CI_FULL_JOB_REPORT_SCOPE_INVALID"):
                        validate_job(mutated, job)

    def test_runner_context_in_job_environment_is_rejected_before_dispatch(self):
        source = (ROOT / ".github/workflows/ci.yml").read_text()
        # Reproduce GitHub's rejected scope even once the real job is repaired.
        job_env = "    env:\n      CI_ISOLATION_REPORT: ${{ runner.temp }}/ci-isolation-report.json\n"
        if job_env not in source:
            source = source.replace("  package-validate:\n", "  package-validate:\n" + job_env, 1)
        with self.assertRaisesRegex(ValueError, "CI_FULL_JOB_ENV_SCOPE_INVALID"):
            validate_job(source, "package-validate")

    def test_full_jobs_execute_the_same_bootstrap_order(self):
        for file, job in JOBS:
            with self.subTest(file=file):
                result, events = self.execute(file, job)
                self.assertEqual(result, 0)
                self.assertEqual(events, ["prepare", "terminal-provision", "verify", "package-gate", "cleanup"])

    def test_prepare_failure_runs_only_cleanup(self):
        for file, job in JOBS:
            with self.subTest(file=file):
                result, events = self.execute(file, job, fail=True)
                self.assertNotEqual(result, 0)
                self.assertEqual(events, ["prepare", "cleanup"])
                self.assertFalse(set(events) & {"package-gate", "release", "issue"})

    def execute(self, file, job, fail=False):
        steps = validate_job((ROOT / ".github/workflows" / file).read_text(), job)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bin_directory = root / "bin"
            bin_directory.mkdir()
            tool = ROOT / "tests/fixtures/ci-isolation/fake-workflow-tool.py"
            for name in ("python3", "bash"):
                path = bin_directory / name
                path.write_text("#!/usr/bin/python3\nexec(compile(open(" + repr(str(tool)) + ").read()," + repr(str(tool)) + ",'exec'))\n")
                path.chmod(0o755)
            for name in ("node", "npm"):
                (bin_directory / name).symlink_to("/usr/bin/true")
            events = root / "events.json"
            events.write_text("[]")
            environment = {"PATH": str(bin_directory) + ":/usr/bin:/bin", "HOME": str(root),
                           "RUNNER_TEMP": str(root), "GITHUB_ENV": str(root / "environment"),
                           "GITHUB_PATH": str(root / "path"),
                           "FIXTURE_EVENTS": str(events), "FIXTURE_PREPARE_FAIL": str(int(fail))}
            status = 0
            for step in steps:
                if status and not step.always:
                    continue
                step_environment = {**environment,
                    "CI_ISOLATION_REPORT": step.report.replace("${{ runner.temp }}", str(root))}
                result = subprocess.run(["/bin/bash", "-e", "-o", "pipefail", "-c", step.script],
                                        cwd=ROOT, env=step_environment, capture_output=True, timeout=5)
                status = status or result.returncode
            return status, json.loads(events.read_text())

    def test_wrong_order_missing_proof_and_elevation_reject(self):
        source = (ROOT / ".github/workflows/ci.yml").read_text()
        validate_job(source, "package-validate")
        for mutated in (source.replace("id: isolation_verify", "id: isolation_cleanup", 1),
                        source.replace("if: always()", "if: success()", 1),
                        source.replace("contents: read", "contents: write"),
                        source.replace("bash tests/validate-package.sh", "sudo bash tests/validate-package.sh"),
                        source.replace("persist-credentials: false", "persist-credentials: true", 1)):
            with self.assertRaises(ValueError):
                validate_job(mutated, "package-validate")

    def test_cli_refuses_operator_host_before_any_provisioning(self):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "report.json"
            result = subprocess.run(["/usr/bin/python3", str(ROOT / "tests/ci_isolation_bootstrap.py"),
                                     "--prepare", "--manifest", "tests/ci-runtime-lock.json", "--report", str(report)],
                                    cwd=ROOT, env={"PATH": "/usr/bin:/bin", "HOME": directory},
                                    capture_output=True, timeout=5)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout.strip(), b"CI_BOOTSTRAP_BLOCKED")
            self.assertFalse(report.exists())

    def test_manifest_and_report_paths_are_closed(self):
        module = importlib.import_module("ci_isolation_bootstrap")
        self.assertTrue(hasattr(module, "validate_manifest_argument"), "fixed CLI manifest gate absent")
        self.assertEqual(module.validate_manifest_argument("tests/ci-runtime-lock.json"), ROOT / "tests/ci-runtime-lock.json")
        for value in ("tests/../tests/ci-runtime-lock.json", "/tmp/alternate-lock.json"):
            with self.assertRaises(ValueError):
                module.validate_manifest_argument(value)
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            self.assertEqual(module.validate_report_path(root / "report.json", root), root / "report.json")
            alias = root / "alias"
            alias.symlink_to(outside)
            for path in (root / "../escape.json", alias / "report.json"):
                with self.assertRaises(ValueError):
                    module.validate_report_path(path, root)
            leaf = root / "leaf.json"
            leaf.symlink_to(Path(outside) / "foreign.json")
            with self.assertRaises(ValueError):
                module.validate_report_path(leaf, root)

    def test_required_new_suites_and_version_contracts_precede_long_terminal_suites(self):
        source = (ROOT / "tests/validate-package.sh").read_text()
        boundary = source.index("node --test tests/terminal-state-adapter.test.mjs")
        for name in ("test-ci-image-upgrade.py", "test-ci-isolation-runtime.py", "test-ci-isolation-bootstrap.py",
                     "test-ci-isolation-probe.py", "test-ci-isolation-wiring.py", "test-nori-package-contract.py",
                     "test-browser-operation-policy.py"):
            self.assertLess(source.index("python3 tests/" + name), boundary)
        self.assertIn("require_frozen_ci_runtime()", source)
        self.assertIn("tests/offline-terminal-resume-probe.py --audit-isolation", source)
        self.assertIn("node --test tests/browser-operations/puppeteer-api.test.mjs", source)
        for name in ('redirect-protocol.test.mjs', 'redirect-feasibility.test.mjs'):
            self.assertTrue('node --test tests/browser-operations/' + name in source, 'required F0 suite missing')

    def test_cli_and_transport_share_one_typed_module_identity(self):
        script = ("import runpy,sys; from pathlib import Path; "
                  "sys.path.insert(0,str(Path('tests').resolve())); "
                  "sys.argv=['ci','--prepare','--manifest','tests/ci-runtime-lock.json','--report','/tmp/unused.json']; "
                  "\ntry: runpy.run_path('tests/ci_isolation_bootstrap.py',run_name='__main__')"
                  "\nexcept SystemExit: pass"
                  "\nmodule=sys.modules.get('ci_isolation_bootstrap'); "
                  "assert module is not None and module.PolicySnapshot.__module__=='__main__'; print('CANONICAL')")
        result = subprocess.run(["/usr/bin/python3", "-I", "-B", "-c", script], cwd=ROOT,
                                env={"PATH": "/usr/bin:/bin", "HOME": "/tmp"},
                                capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0, "CLI loaded a duplicate typed bootstrap module")
        self.assertEqual(result.stdout.splitlines(), [b"CI_BOOTSTRAP_BLOCKED", b"CANONICAL"])


if __name__ == "__main__":
    if sys.argv[1:] == ["--check-only"]:
        try:
            check_workflows()
            print("CI isolation wiring passed")
        except (OSError, ValueError):
            print("CI isolation wiring blocked")
            raise SystemExit(1) from None
    else:
        unittest.main()
