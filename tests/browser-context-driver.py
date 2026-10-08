#!/usr/bin/env python3
"""Acceptance-only, single-use startup decision; never a production entrypoint."""
import argparse
import importlib.util
import os
from pathlib import Path
import re
import subprocess
import sys
import time

from browser_startup_approval import load_approval
from terminal_state_adapter import TerminalState, TerminalStateError


def source_head(root):
    """Read a clean immutable source via native Git or the installed WSL bridge."""
    root = Path(root).resolve(strict=True)
    git = "git"
    location = str(root)
    marker = root / ".git"
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": os.environ.get("HOME", "/tmp"),
           "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull}
    if (os.name == "posix" and marker.is_file() and marker.stat().st_size <= 4096
            and re.match(r"gitdir: [A-Za-z]:[/\\]", marker.read_text(encoding="utf-8"))):
        # Windows linked worktrees contain a Windows gitdir, not a Linux path.
        git = "/mnt/c/Program Files/Git/cmd/git.exe"
        if not Path(git).is_file():
            raise ValueError("source bridge unavailable")
        converted = subprocess.run(["wslpath", "-w", location], env=env,
                                   capture_output=True, timeout=10, check=True)
        location = converted.stdout.decode("utf-8").strip().replace("\\", "/")
        env["GIT_CONFIG_GLOBAL"] = "NUL"
        env["WSLENV"] = "GIT_CONFIG_NOSYSTEM:GIT_CONFIG_GLOBAL"
    def read(*args):
        result = subprocess.run([git, "--no-optional-locks", "--no-pager", "-c", "core.fsmonitor=false",
                                 "-c", f"safe.directory={location}", "-C", location, *args],
                                env=env, capture_output=True, timeout=10, check=True)
        return result.stdout.decode("utf-8").strip()
    head = read("rev-parse", "HEAD")
    if not re.fullmatch(r"[0-9a-f]{40}", head) or read("status", "--porcelain", "--untracked-files=all"):
        raise ValueError("source is not clean and immutable")
    return head


def prepare_approval(claim, commit, nonce, source_root, command, *, cancellation=None):
    if (Path(source_root).resolve(strict=True) != Path(__file__).resolve().parents[1]
            or len(command) != 6 or command[1] != "--session-id"
            or command[3:5] != ["--strict-mcp-config", "--mcp-config"]
            or not Path(command[0]).is_absolute() or not Path(command[0]).is_file()
            or str(Path(command[0]).resolve(strict=True)) != command[0]
            or source_head(source_root) != commit):
        raise ValueError("invalid startup invocation")
    root = Path(claim).parent.parent
    mcp = Path(command[5])
    if (not mcp.is_absolute() or mcp.resolve() != mcp or not mcp.is_relative_to(root)
            or not mcp.is_file()):
        raise ValueError("invalid startup MCP location")
    binding = {"commit": commit, "runNonce": nonce, "sessionId": command[2],
               "endpoint": os.environ.get("ANTHROPIC_BASE_URL", ""),
               "configDir": os.environ.get("CLAUDE_CONFIG_DIR", ""),
               "executable": command[0], "probe": "main-before"}
    if cancellation is not None: cancellation.check()
    return load_approval(claim, binding)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--claim", required=True, type=Path)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--run-nonce", required=True)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--capture", required=True, type=Path)
    parser.add_argument("--events", required=True, type=Path)
    parser.add_argument("--dialogue", choices=("context",), required=True)
    parser.add_argument("--timeout", type=int, required=True)
    parser.add_argument("--terminal-engine", choices=("legacy", "headless"), default="legacy")
    parser.add_argument("--terminal-node", type=Path)
    parser.add_argument("--terminal-module-root", type=Path)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if args.terminal_engine == "headless":
        from terminal_cancellation import TerminalCancellation
        cancellation = TerminalCancellation()
        try:
            with cancellation:
                result = _run_selected_args(args, command, cancellation)
            return 2 if cancellation.requested else result
        except RuntimeError:
            print("BLOCKED: test terminal runtime unavailable", file=sys.stderr)
            return 2
    return _run_selected_args(args, command)


def _run_selected_args(args, command, cancellation=None):
    terminal = None
    if args.terminal_engine == "headless":
        try:
            terminal = TerminalState(args.terminal_node, args.terminal_module_root, time.monotonic() + args.timeout,
                                     cancellation=cancellation)
        except TerminalStateError:
            print("BLOCKED: test terminal runtime unavailable", file=sys.stderr)
            return 2
    elif args.terminal_node is not None or args.terminal_module_root is not None:
        print("BLOCKED: test terminal runtime unavailable", file=sys.stderr)
        return 2
    try:
        if cancellation is not None:
            cancellation.check()
            approval = prepare_approval(args.claim, args.commit, args.run_nonce, args.source_root, command,
                                        cancellation=cancellation)
        else:
            approval = prepare_approval(args.claim, args.commit, args.run_nonce, args.source_root, command)
        root = args.claim.parent.parent
        if any(not path.is_absolute() or path.resolve() != path or not path.is_relative_to(root)
               for path in (args.capture, args.events)):
            raise ValueError("invalid startup output location")
    except (OSError, ValueError, UnicodeError, subprocess.SubprocessError):
        if terminal is not None:
            try: terminal.close()
            except TerminalStateError: pass
        print("BLOCKED: startup approval scope rejected", file=sys.stderr)
        return 2
    spec = importlib.util.spec_from_file_location("acceptance_pty", Path(__file__).with_name("claude-pty-driver.py"))
    driver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(driver)
    try:
        result = driver.drive(command, args.capture, args.timeout, args.events,
                              dialogue="context", startup_approval=approval, terminal_state=terminal)
    finally:
        if terminal is not None:
            try: terminal.close()
            except TerminalStateError:
                result = 2
    if result:
        print("Claude PTY dialogue did not complete.", file=sys.stderr)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
