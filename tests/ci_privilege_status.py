"""Portable, static capability validation shared by offline isolation audits."""
import re


def validate_privilege_status(text: str) -> None:
    if type(text) is not str or len(text) > 65536 or "\x00" in text:
        raise ValueError("PRIVILEGE_STATUS_UNPROVEN")
    fields = {}
    expected = {"CapInh", "CapPrm", "CapEff", "CapBnd", "CapAmb", "NoNewPrivs"}
    for line in text.splitlines():
        name = line.partition(":")[0]
        if name not in expected:
            continue
        if name in fields:
            raise ValueError("PRIVILEGE_STATUS_UNPROVEN")
        value = line.partition(":")[2].strip()
        if name == "NoNewPrivs":
            if value != "1":
                raise ValueError("PRIVILEGE_STATUS_UNPROVEN")
        elif not re.fullmatch(r"[0-9a-fA-F]{16}", value) or int(value, 16) != 0:
            raise ValueError("PRIVILEGE_STATUS_UNPROVEN")
        fields[name] = value
    if set(fields) != expected:
        raise ValueError("PRIVILEGE_STATUS_UNPROVEN")
