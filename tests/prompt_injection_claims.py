#!/usr/bin/env python3
"""Validate bounded, honest P0-06 claims in exact deliverables."""
from __future__ import annotations

import argparse
import re
from pathlib import Path


MAX_DELIVERABLE_BYTES = 1_048_576
NORMATIVE = (
    "docs/superpowers/specs/2026-08-25-p0-06-global-prompt-injection-defense-design.md",
    "docs/superpowers/specs/2026-08-26-p0-06-guarantee-separation-design.md",
    "docs/architecture/ADR-009-global-prompt-injection-defense.md",
)
OPERATOR = ("README.md", "docs.md")
EVIDENCE = ("CHANGELOG.md", "tests/validation-notes.md")
TAXONOMY = (
    "DG-POLICY",
    "DG-AUTHZ",
    "DG-EFFECT",
    "DG-EVIDENCE",
    "RC-AUTHORITY",
    "RC-TOOL-PROPOSAL",
    "RC-OUTPUT",
)
OPERATOR_MARKERS = (
    "deterministic package guarantees",
    "runtime compatibility",
    "RC-OUTPUT=FAIL",
    "does not guarantee output confidentiality",
    "not required for deterministic P0-06 merge acceptance",
)
EVIDENCE_MARKERS = (
    "65fd95da1c4890741180f2e2c9c80820d8421a4d",
    "574c41379d90359ff06db03aad36ed758fa03736",
    "`incident-commander`",
    "`audit-evidence-collector`",
    "`CANARY_EXPOSED`",
    "zero tool-call attempts",
    "`RC-OUTPUT=FAIL`",
    "deterministic acceptance is separate",
)
FORBIDDEN = {
    "universal confidentiality claim": re.compile(
        r"(?:"
        r"(?:guarantees?|ensures?) (?:that )?(?:protected values|model output) "
        r"(?:are |is )?never (?:emitted|exposed|repeated)"
        r"|protected values[^\n.;]{0,240} (?:are |is )never "
        r"(?:emitted|exposed|repeated|transformed)"
        r"|model output (?:are |is )never "
        r"(?:emitted|exposed|repeated|transformed)"
        r"|(?:the package|model output) cannot ever "
        r"(?:emit|expose|repeat)(?: protected values)?"
        r"|the package always prevents protected-value disclosure"
        r")",
        re.IGNORECASE,
    ),
    "prompt injection elimination claim": re.compile(
        r"(?:eliminates?|prevents? all) prompt injection",
        re.IGNORECASE,
    ),
    "monolithic active merge gate": re.compile(
        r"active-model matrix must pass before P0-06 can merge",
        re.IGNORECASE,
    ),
}
TAXONOMY_SECTION = re.compile(
    r"^## Guarantee [Tt]axonomy[^\n]*\n(?P<body>.*?)(?=^## |\Z)",
    re.MULTILINE | re.DOTALL,
)


def fail(label: str) -> int:
    """Emit one fixed diagnostic label without document content or paths."""
    print(f"prompt injection claims invalid: {label}")
    return 1


def read_allowlisted(root: Path, relative: str) -> str | None:
    """Read one bounded regular UTF-8 file with no linked path component."""
    current = root
    for part in Path(relative).parts:
        current = current / part
        if current.is_symlink():
            return None
    try:
        if not current.is_file() or current.stat().st_size > MAX_DELIVERABLE_BYTES:
            return None
        return current.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def validate(root: Path) -> int:
    if root.is_symlink() or not root.is_dir():
        return fail("invalid claims root")

    texts: dict[str, str] = {}
    for relative in (*NORMATIVE, *OPERATOR, *EVIDENCE):
        text = read_allowlisted(root, relative)
        if text is None:
            return fail("invalid allowlisted deliverable")
        texts[relative] = text

    for relative in NORMATIVE:
        section = TAXONOMY_SECTION.search(texts[relative])
        if section is None or any(
            marker not in section.group("body") for marker in TAXONOMY
        ):
            return fail("missing guarantee taxonomy")

    for relative in OPERATOR:
        if any(marker not in texts[relative] for marker in OPERATOR_MARKERS):
            return fail("current compatibility disclosure")

    for relative in EVIDENCE:
        if any(marker not in texts[relative] for marker in EVIDENCE_MARKERS):
            return fail("historical compatibility evidence")

    for text in texts.values():
        for label, pattern in FORBIDDEN.items():
            if pattern.search(text):
                return fail(label)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    arguments = parser.parse_args()
    return validate(Path(arguments.root))


if __name__ == "__main__":
    raise SystemExit(main())
