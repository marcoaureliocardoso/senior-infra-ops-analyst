"""Synthetic env_reset transport: never elevates or reads operator state."""
import os
import sys

if sys.argv[1] != "-n":
    raise SystemExit(2)
os.execve(sys.argv[2], sys.argv[2:], {"PATH": "/usr/bin:/bin", "SUDO_UID": str(os.getuid())})
