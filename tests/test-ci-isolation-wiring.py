"""Canonical workflow contract and no-provider execution of selected real steps."""
from dataclasses import dataclass
import importlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
JOBS = (("ci.yml", "package-validate"), ("release.yml", "validate"),
        ("scheduled-maintenance.yml", "full-validation"))
ORDER = ("isolation_prepare", "terminal_provision", "isolation_verify", "package_gate", "isolation_cleanup")


@dataclass(frozen=True)
class Step:
    name: str
    script: str
    always: bool


def full_job(text, name):
    match = re.search(r"^  " + re.escape(name) + r":\n(.*?)(?=^  [a-zA-Z0-9_-]+:|\Z)", text, re.M | re.S)
    if match is None:
        raise ValueError("CI_FULL_JOB_MISSING")
    return match[1]


def validate_job(text, name):
    job = full_job(text, name)
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
        steps.append(Step(stage, script, bool(condition)))
    if tuple(step.name for step in steps) != ORDER:
        raise ValueError("CI_FULL_JOB_ORDER_INVALID")
    return steps


def check_workflows(root=ROOT):
    for file, job in JOBS:
        validate_job((root / ".github/workflows" / file).read_text(), job)


class WiringTests(unittest.TestCase):
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
                           "GITHUB_PATH": str(root / "path"), "CI_ISOLATION_REPORT": str(root / "report"),
                           "FIXTURE_EVENTS": str(events), "FIXTURE_PREPARE_FAIL": str(int(fail))}
            status = 0
            for step in steps:
                if status and not step.always:
                    continue
                result = subprocess.run(["/bin/bash", "-e", "-o", "pipefail", "-c", step.script],
                                        cwd=ROOT, env=environment, capture_output=True, timeout=5)
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
