"""Pure context numbers from consumed cells; never freshness or input authority."""
from dataclasses import dataclass
from decimal import Decimal
import re

from terminal_state_adapter import TerminalSnapshot


@dataclass(frozen=True)
class ContextNumbers:
    free: Decimal
    buffer: Decimal | None
    used: int


@dataclass(frozen=True)
class ContextSample:
    numbers: ContextNumbers
    geometry: tuple[str, int, int, tuple[int, ...]]


def parse_context_values(
    text: str, allow_rendered_row_order: bool = False,
) -> ContextNumbers | None:
    if "Context Usage" not in text:
        return None
    folded = bytes(value for value in text.lower().encode("utf-8") if 97 <= value <= 122)
    free_matches = re.findall(
        r"Free space[^\r\n%]{0,160}?(\d{1,3}(?:\.\d+)?)%",
        text,
        flags=re.IGNORECASE,
    )
    buffer_matches = re.findall(
        r"(?<![A-Za-z])(?:Autocompact buffer|Compact buffer)"
        r"[^\r\n%]{0,160}?(\d{1,3}(?:\.\d+)?)%",
        text,
        flags=re.IGNORECASE,
    )
    free_row_matches = [
        value
        for line in text.splitlines() if re.search(r"Free space", line, re.IGNORECASE)
        for value in re.findall(r"(?<!\d)(\d{1,3}(?:\.\d+)?)%", line)
    ]
    buffer_row_matches = [
        value
        for line in text.splitlines()
        if re.search(r"(?<![A-Za-z])(?:Autocompact buffer|Compact buffer)", line, re.IGNORECASE)
        for value in re.findall(r"(?<!\d)(\d{1,3}(?:\.\d+)?)%", line)
    ]
    if allow_rendered_row_order and len(set(free_row_matches)) == 1:
        free_matches = free_row_matches
    if allow_rendered_row_order and len(set(buffer_row_matches)) == 1:
        buffer_matches = buffer_row_matches
    free_values = [float(value) for value in free_matches]
    buffer_values = [float(value) for value in buffer_matches]
    buffer_label_present = b"compactbuffer" in folded
    if (not free_values
            or any(not 0 <= value <= 100 for value in free_values + buffer_values)
            or len(set(free_values)) != 1
            or (buffer_label_present and not buffer_values)
            or len(set(buffer_values)) > 1):
        return None
    # Preserve the legacy float/round result; Decimal is identity, not new rounding.
    used = 100 - free_values[-1] - (buffer_values[-1] if buffer_values else 0)
    if not 0 <= used <= 100:
        return None
    return ContextNumbers(Decimal(free_matches[-1]),
        Decimal(buffer_matches[-1]) if buffer_matches else None, round(used))


def parse_context_percent(text: str, allow_rendered_row_order: bool = False) -> int | None:
    value = parse_context_values(text, allow_rendered_row_order)
    return value.used if value is not None else None


def sample_context(snapshot: TerminalSnapshot) -> ContextSample | None:
    lines = tuple(''.join(cell.text or (' ' if cell.width else '') for cell in row).rstrip()
        for row in snapshot.rows)
    numbers = parse_context_values('\n'.join(lines), True)
    if numbers is None:
        return None
    positions = tuple(index for index, line in enumerate(lines)
        if re.search(r'Context Usage|Free space|(?:Autocompact|Compact) buffer',line,re.IGNORECASE))
    return ContextSample(numbers,(snapshot.active,snapshot.baseY,snapshot.viewportY,positions))


def context_numeric_conflict(snapshot: TerminalSnapshot) -> bool:
    """Pure contradiction check, not a sample, freshness or input authority.

    The legacy parser deliberately collapses incomplete and invalid evidence to
    None. Passive transitions must remember contradictory rendered values even
    while the display is incomplete; it must not reinterpret them as absence.
    """
    lines=tuple(''.join(cell.text or (' ' if cell.width else '') for cell in row)
        for row in snapshot.rows)
    groups=[]
    for label in (r'Free space',r'(?<![A-Za-z])(?:Autocompact|Compact) buffer'):
        # Unlike the legacy display parser, do not discard a sign or truncate
        # an oversized completed value into harmless absence/another number.
        values={Decimal(value) for line in lines if re.search(label,line,re.IGNORECASE)
            for value in re.findall(r'(?<![\d.])([+-]?\d+(?:\.\d+)?)%',line)}
        if len(values)>1 or any(not 0<=value<=100 for value in values): return True
        groups.append(values)
    return bool(all(groups) and next(iter(groups[0]))+next(iter(groups[1]))>100)
