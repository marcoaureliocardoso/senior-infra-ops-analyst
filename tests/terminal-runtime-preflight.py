#!/usr/bin/env python3
"""Credential-free capability check; never calls Claude or installs packages."""
import argparse
import json
from pathlib import Path
import time

from terminal_state_adapter import TerminalState, TerminalStateError
from terminal_cancellation import TerminalCancellation


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--node',type=Path,required=True)
    parser.add_argument('--module-root',type=Path,required=True)
    args=parser.parse_args(); state=None; ready=False
    cancellation=TerminalCancellation()
    try:
        with cancellation:
            try:
                state=TerminalState(args.node,args.module_root,time.monotonic()+5,cancellation=cancellation)
                state.feed('\x1b[?1049h\x1b[H❯\u00a0'.encode())
                snapshot=state.snapshot()
                ready=(snapshot.active=='alternate' and snapshot.cursorX==2 and snapshot.cursorY==0
                       and snapshot.rows[0][0].text=='❯' and snapshot.rows[0][1].text=='\u00a0')
            except RuntimeError: pass
            finally:
                if state is not None:
                    try: state.close()
                    except RuntimeError: ready=False
    except RuntimeError: ready=False
    if cancellation.requested: ready=False
    print(json.dumps({'reasonCode':'TERMINAL_RUNTIME_READY' if ready else 'TERMINAL_DEPENDENCY_UNAVAILABLE'}))
    return 0 if ready else 2


if __name__=='__main__': raise SystemExit(main())
