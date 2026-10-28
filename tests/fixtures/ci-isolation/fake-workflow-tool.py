"""Real child-process stand-in for selected workflow run commands only."""
import json
import os
from pathlib import Path
import sys

arguments = sys.argv[1:]
if not arguments:
    raise SystemExit(2)
target = arguments[0]
if target == "tests/ci_isolation_bootstrap.py":
    phase = {"--prepare": "prepare", "--verify": "verify", "--cleanup": "cleanup"}.get(arguments[1])
elif target == "tests/provision-terminal-runtime.py":
    phase = "terminal-provision"
elif target == "tests/validate-package.sh":
    phase = "package-gate"
else:
    raise SystemExit(2)
expected_report = str(Path(os.environ["RUNNER_TEMP"]) / "ci-isolation-report.json")
if os.environ.get("CI_ISOLATION_REPORT") != expected_report:
    raise SystemExit(4)
if target == "tests/ci_isolation_bootstrap.py":
    if arguments.count("--report") != 1 or arguments[arguments.index("--report") + 1:] != [expected_report]:
        raise SystemExit(4)
path = Path(os.environ["FIXTURE_EVENTS"])
events = json.loads(path.read_text())
if phase == "package-gate" and "verify" not in events:
    raise SystemExit(3)
events.append(phase)
path.write_text(json.dumps(events))
if phase == "prepare" and os.environ.get("FIXTURE_PREPARE_FAIL") == "1":
    raise SystemExit(7)
