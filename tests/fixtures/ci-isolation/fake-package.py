"""Stateful external package fixture with real partial/failure boundaries."""
import json
from pathlib import Path
import sys

path, operation, mode = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
state = json.loads(path.read_text(encoding="ascii"))
state["events"].append(operation)
if operation == "apply" and mode == "partial-failure":
    state["generation"] += 1
    path.write_text(json.dumps(state), encoding="ascii")
    raise SystemExit(2)
if operation == "refresh" and mode == "index-failure":
    path.write_text(json.dumps(state), encoding="ascii")
    raise SystemExit(2)
if operation == "apply":
    state["generation"] += 1
path.write_text(json.dumps(state), encoding="ascii")
if operation == "simulate":
    if mode == "malformed":
        print("unknown resolver operation")
    elif mode == "skip-unsafe":
        print("1 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.")
        print("Inst apparmor [1.0] (1.1 Ubuntu [amd64])")
        print("Conf apparmor (1.1 Ubuntu [amd64])")
    else:
        print("1 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.")
        print("Inst build-demo [1.0] (1.1 Ubuntu [amd64])")
        print("Conf build-demo (1.1 Ubuntu [amd64])")
if operation == "simulate-dependencies":
    print("build-demo is already the newest version (1.1).")
    print(f"0 upgraded, 0 newly installed, 0 to remove and {12 if mode == 'deferred' else 0} not upgraded.")
