"""Cell-based acceptance input policy; observations never authorize an effect."""
import re
import unicodedata
from dataclasses import dataclass
from terminal_state_adapter import TerminalSnapshot


@dataclass(frozen=True)
class InputAnchor:
    buffer: str
    row: int
    cursorX: int
    baseY: int
    viewportY: int
    markerX: int

def parse_context_percent(
    text: str, allow_rendered_row_order: bool = False,
) -> int | None:
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
    used = 100 - free_values[-1] - (buffer_values[-1] if buffer_values else 0)
    if not 0 <= used <= 100:
        return None
    return round(used)


class TerminalInputPolicy:
    def __init__(self):
        self._input_last = None
        self._input_anchor = None
        self._context_barrier = ()
        self._position_barrier = None
        self._fresh_input = False
        self._fresh_context = False
        self._fresh_location = False

    @staticmethod
    def _row_text(row):
        return ''.join(cell.text or (' ' if cell.width else '') for cell in row).rstrip()

    def screen_text(self, snapshot: TerminalSnapshot) -> str:
        return '\n'.join(self._row_text(row) for row in snapshot.rows)

    def _cursor_row(self, snapshot):
        index = snapshot.baseY + snapshot.cursorY - snapshot.viewportY
        return snapshot.rows[index] if 0 <= index < len(snapshot.rows) else None

    def _profile(self, snapshot):
        row = self._cursor_row(snapshot)
        return (snapshot.active, row) if row is not None else None

    def _context_signature(self, snapshot):
        return tuple(self._row_text(row) for row in snapshot.rows
            if re.search(r'Context Usage|Free space|(?:Autocompact|Compact) buffer',
                self._row_text(row), re.IGNORECASE))

    def mark_transition(self, snapshot: TerminalSnapshot) -> None:
        self._input_last = self._profile(snapshot)
        row = self._cursor_row(snapshot)
        self._input_anchor = ((snapshot.active, snapshot.baseY + snapshot.cursorY)
            if row is not None and self._candidate(row) is not None else None)
        self._context_barrier = self._context_signature(snapshot)
        self._position_barrier = (snapshot.active, snapshot.cursorY, snapshot.baseY, snapshot.viewportY)
        self._fresh_input = self._fresh_context = self._fresh_location = False

    def _observe(self, snapshot):
        profile = self._profile(snapshot)
        row = self._cursor_row(snapshot)
        position = (snapshot.active, snapshot.baseY + snapshot.cursorY)
        controlled_echo = (row is not None and
            re.match(r'^\s*❯\s*(?:/(?:context|exit)\b|P0-04B synthetic context measurement\.)', self._row_text(row)))
        relevant = (row is not None and
            (self._candidate(row) is not None or (self._input_anchor is not None and controlled_echo)))
        if relevant and (self._input_anchor is None or position == self._input_anchor):
            if self._input_last is not None and profile != self._input_last:
                self._fresh_input = True
            self._input_last = profile
            if self._input_anchor is None:
                self._input_anchor = position
        if self._context_signature(snapshot) != self._context_barrier:
            self._fresh_context = True
        position = (snapshot.active, snapshot.cursorY, snapshot.baseY, snapshot.viewportY)
        if (self._fresh_context and position != self._position_barrier
                and parse_context_percent(self.screen_text(snapshot), allow_rendered_row_order=True) is not None):
            self._fresh_location = True

    def _auth(self, snapshot):
        folded = re.sub('[^a-z]', '', self.screen_text(snapshot).lower())
        if 'doyouwanttousethisapikey' in folded:
            return 'api_key_approval_required'
        if any(label in folded for label in
            ('selectloginmethod','howwouldyouliketologin','claudecoderequiresauthentication')):
            return 'login_required'
        return None

    def authentication(self, snapshot: TerminalSnapshot) -> str | None:
        self._observe(snapshot)
        return self._auth(snapshot)

    def _candidate(self, row):
        # Inspect raw cells before rstrip so unsupported whitespace cannot vanish.
        raw = ''.join(cell.text or (' ' if cell.width else '') for cell in row)
        if any(unicodedata.category(char)=='Cf' or (char.isspace() and char not in ' \t\u00a0') for char in raw):
            return None
        match = re.fullmatch(r'[ \t]*❯[ \t\u00a0]*(?:ready|Try[ \t]+"[^"\r\n]+")?[ \t\u00a0]*', raw)
        if match is None: return None
        marker = next((index for index,cell in enumerate(row) if cell.text=='❯' and cell.width==1), None)
        if marker is None: return None
        tail = raw.strip(' \t\u00a0').removeprefix('❯').lstrip(' \t\u00a0')
        padding_end = marker+1
        while padding_end < 120 and row[padding_end].width==1 and row[padding_end].text in (' ','\t','\u00a0'):
            padding_end += 1
        text_end = max((index+cell.width for index,cell in enumerate(row) if cell.text not in ('',' ','\t','\u00a0')),default=marker+1)
        return marker, padding_end, text_end, tail

    def ready(self, snapshot: TerminalSnapshot) -> bool:
        self._observe(snapshot)
        return self._readiness(snapshot) == 'READY'

    def empty_input_anchor(self, snapshot: TerminalSnapshot) -> InputAnchor | None:
        """Pure edit eligibility; never observes freshness or authorizes a command."""
        if self._auth(snapshot): return None
        folded=re.sub('[^a-z]','',self.screen_text(snapshot).lower())
        if any(label in folded for label in (
                'choosethetextstylethatlooksbestwithyourterminal','yesitrustthisfolder',
                'pressesctoclose','pressescapetoclose')): return None
        candidates=[]
        for index,row in enumerate(snapshot.rows):
            if not re.match(r'^\s*❯',self._row_text(row)): continue
            candidate=self._candidate(row)
            if candidate is None or candidate[3]: return None
            candidates.append((index,candidate))
        if len(candidates)!=1: return None
        index,(marker,padding_end,_text_end,_tail)=candidates[0]
        if (index!=snapshot.baseY+snapshot.cursorY-snapshot.viewportY
                or not marker<snapshot.cursorX<=padding_end or snapshot.cursorX+16>120): return None
        return InputAnchor(snapshot.active,index,snapshot.cursorX,snapshot.baseY,snapshot.viewportY,marker)

    def _readiness(self, snapshot):
        # Same fail-closed decision tree; diagnostic projection never observes.
        if not (self._fresh_input or self._fresh_location): return 'FRESHNESS_UNPROVEN'
        if self._auth(snapshot): return 'AUTHENTICATION_REQUIRED'
        text = self.screen_text(snapshot)
        folded = re.sub('[^a-z]', '', text.lower())
        if any(label in folded for label in
            ('choosethetextstylethatlooksbestwithyourterminal','yesitrustthisfolder')):
            return 'STARTUP_SELECTION'
        candidates = []
        for index,row in enumerate(snapshot.rows):
            line = self._row_text(row)
            if re.match(r'^\s*❯',line):
                candidate = self._candidate(row)
                if candidate is not None: candidates.append((index,candidate))
                elif not (re.match(r'^\s*❯\s*/(?:context|exit)\b',line) or
                          re.match(r'^\s*❯\s*P0-04B synthetic context measurement\.',line)):
                    return 'UNSUPPORTED_MARKER'
        if len(candidates)!=1: return 'CANDIDATE_COUNT'
        index, (marker,padding_end,text_end,tail) = candidates[0]
        if index != snapshot.baseY+snapshot.cursorY-snapshot.viewportY: return 'CURSOR_ROW_MISMATCH'
        cursor = snapshot.cursorX
        valid = cursor == text_end if tail == 'ready' else marker < cursor <= padding_end
        return 'READY' if valid else 'CURSOR_COLUMN_MISMATCH'

    def diagnostic_state(self, snapshot: TerminalSnapshot) -> dict:
        """Pure structural projection: no cells, hashes, IPC or freshness mutation."""
        auth=self._auth(snapshot)
        return {'buffer':snapshot.active,'cursorX':snapshot.cursorX,'cursorY':snapshot.cursorY,
            'baseY':snapshot.baseY,'viewportY':snapshot.viewportY,
            'candidateCount':sum(self._candidate(row) is not None for row in snapshot.rows),
            'inputFresh':self._fresh_input,'contextFresh':self._fresh_context,
            'locationFresh':self._fresh_location,'authentication':auth.upper() if auth else 'NONE',
            'readiness':self._readiness(snapshot)}

    def context_percent(self, snapshot: TerminalSnapshot) -> int | None:
        self._observe(snapshot)
        if not self._fresh_context or self._auth(snapshot): return None
        return parse_context_percent(self.screen_text(snapshot), allow_rendered_row_order=True)
