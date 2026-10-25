"""Synthetic external builder: creates data, never a namespace or provider."""
from pathlib import Path
import sys

directory = Path(sys.argv[1])
mode = sys.argv[2]
(directory / "build-started").write_text("synthetic", encoding="ascii")
if mode == "build-failure":
    raise SystemExit(1)
binary = directory / "candidate"
if mode == "symlink":
    binary.symlink_to(directory / "foreign")
else:
    binary.write_bytes(b"#!/bin/sh\nprintf 'bubblewrap 0.12.0\\n'\n")
    binary.chmod(0o777 if mode == "writable" else 0o4755 if mode == "setuid" else 0o755)
