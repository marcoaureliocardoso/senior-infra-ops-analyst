#!/usr/bin/env python3
"""Test-only bookkeeping for a separately operator-authorized native decision.

A claim is not evidence of human consent. Its trusted creating launcher must
first verify the fresh grant and immutable source commit. No credential enters
this module. Public production/PTY entrypoints do not create claims.
"""
import json
import os
from pathlib import Path
import re
import stat
import time
from urllib.parse import urlsplit
import uuid

FIELDS = {"commit", "runNonce", "sessionId", "endpoint", "configDir", "executable", "probe"}


class StartupApproval:
    def __init__(self, expires, clock):
        self.expires = expires
        self.clock = clock
        self.used = False

    def revoke(self):
        self.used = True

    def selection(self, screen):
        if self.used or self.clock() >= self.expires:
            return None
        self.used = True  # An unknown dialogue consumes the decision too.
        heading = "Do you want to use this API key?"
        folded = re.sub(r"[^a-z]", "", screen.lower())
        if screen.count(heading) != 1 or any(label in folded for label in (
                "selectloginmethod", "howwouldyouliketologin", "claudecoderequiresauthentication")):
            return None
        lines = screen.split(heading, 1)[1].splitlines()
        options = []
        for line in lines:
            if not line.strip():
                if options:
                    break  # The exact selector block, not stale prior screens below it.
                continue
            match = re.fullmatch(r"\s*(❯)?\s*(?:([12])\.\s*)?(Yes|No)(?:\s*\(recommended\))?\s*", line)
            if match is not None:
                options.append(match.groups())
            elif options or re.match(r"\s*(?:❯\s*)?\d+\.", line):
                return None
        if (len(options) != 2 or [label for _, _, label in options] != ["Yes", "No"]
                or [n for _, n, _ in options] not in [["1", "2"], [None, None]]):
            return None
        selected = [label for marker, _, label in options if marker]
        if selected == ["No"]:
            return b"\x1b[A"
        if selected == ["Yes"]:
            return b""
        return None


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("invalid startup claim")
        result[key] = value
    return result


def load_approval(path, binding, *, clock=time.time):
    """Consume one private POSIX claim before any child or selector input."""
    if (os.name != "posix" or not isinstance(binding, dict) or set(binding) != FIELDS
            or any(type(value) is not str for value in binding.values())
            or binding["probe"] != "main-before"):
        raise ValueError("invalid startup scope")
    if (not re.fullmatch(r"[0-9a-f]{40}", binding["commit"])
            or not re.fullmatch(r"p004b-[0-9a-f]{32}", binding["runNonce"])):
        raise ValueError("invalid startup scope")
    try:
        if str(uuid.UUID(binding["sessionId"])) != binding["sessionId"]:
            raise ValueError
        endpoint = urlsplit(binding["endpoint"])
        if (endpoint.scheme != "https" or not endpoint.hostname or endpoint.username
                or endpoint.password or endpoint.query or endpoint.fragment
                or len(binding["endpoint"]) > 512 or re.search(r"\s", binding["endpoint"])):
            raise ValueError
        endpoint.port
    except (ValueError, TypeError, AttributeError):
        raise ValueError("invalid startup scope") from None
    path = Path(path)
    parent = path.parent
    root = parent.parent
    config = Path(binding["configDir"])
    executable = Path(binding["executable"])
    if (not path.is_absolute() or parent.resolve() != parent or root.resolve() != root
            or not config.is_absolute() or config.resolve() != config
            or not config.is_relative_to(root) or not config.is_dir()
            or not executable.is_absolute()):
        raise ValueError("invalid startup location")
    for directory in (root, parent, config):
        info = directory.lstat()
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid()
                or info.st_mode & 0o077):
            raise ValueError("unsafe startup directory")
    directory_fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        descriptor = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory_fd)
        try:
            before = os.fstat(descriptor)
            if (not stat.S_ISREG(before.st_mode) or before.st_uid != os.getuid()
                    or before.st_mode & 0o077 or before.st_nlink != 1 or not 0 < before.st_size <= 4096):
                raise ValueError("unsafe startup claim")
            data = os.read(descriptor, 4097)
            after = os.fstat(descriptor)
            identity_fields = ("st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink",
                               "st_size", "st_mtime_ns", "st_ctime_ns")
            if (any(getattr(before, field) != getattr(after, field) for field in identity_fields)
                    or len(data) != before.st_size):
                raise ValueError("changed startup claim")
            claim = json.loads(data, object_pairs_hook=_pairs)
        finally:
            os.close(descriptor)
        if (not isinstance(claim, dict) or set(claim) != FIELDS | {"issuedAt", "expiresAt"}
                or any(claim[key] != binding[key] for key in FIELDS)):
            raise ValueError("startup binding mismatch")
        issued, expires = claim["issuedAt"], claim["expiresAt"]
        if (type(issued) is not int or type(expires) is not int
                or not issued <= clock() < expires <= issued + 120):
            raise ValueError("expired startup claim")
        spent = os.open("spent", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                        0o600, dir_fd=directory_fd)
        os.close(spent)
        identity = os.stat(path.name, dir_fd=directory_fd, follow_symlinks=False)
        if (identity.st_dev, identity.st_ino) != (before.st_dev, before.st_ino):
            raise ValueError("changed startup claim")
        os.unlink(path.name, dir_fd=directory_fd)
        return StartupApproval(expires, clock)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("startup claim rejected") from None
    finally:
        os.close(directory_fd)
