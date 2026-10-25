"""Synthetic policy lifecycle, never invokes an AppArmor parser."""
import json
from pathlib import Path
import sys

path, action, mode = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
state = json.loads(path.read_text())
state["events"].append(action)
if action == "policy-load":
    state["policy"] = True
elif action == "policy-remove":
    state["policy"] = False
path.write_text(json.dumps(state))
if mode == "load-failure" and action == "policy-load":
    raise SystemExit(1)
if mode == "cleanup-failure" and action == "policy-remove":
    raise SystemExit(1)
