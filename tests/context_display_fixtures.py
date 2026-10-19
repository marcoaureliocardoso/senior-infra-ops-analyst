"""Test-only owned resumed-display fixture; never mounted into native runs."""
from dataclasses import replace
from resume_history_fixtures import CaseFixture, history_snapshot
import terminal_context_echo as echo
import terminal_resume_history as history
from terminal_context_diagnostics import _create_context_journal

TEXT = 'P0-04B synthetic text control. Reply P004B_SKILL_OK only.'


class DisplayCase:
    def __init__(self, *, history_rows=None, baseline_free='81', baseline_buffer='3'):
        self.fixture = CaseFixture()
        self.history = tuple(history_rows if history_rows is not None else ((5,'❯ '+TEXT),))
        self.free = baseline_free
        self.buffer = baseline_buffer

    def snapshot(self, *, free=None, buffer=None, commit=None, extra=(), numeric=True):
        rows = self.history
        if numeric:
            rows += ((0,'Context Usage'),(1,f'Free space: {free or self.free}%'),
                (2,f'Autocompact buffer: {buffer or self.buffer}%'))
        if commit is not None: rows += ((commit,'❯ /context'),)
        return history_snapshot((*rows,*extra))

    def __enter__(self):
        f = self.fixture.__enter__()
        try:
            f.complete_initial()
            assert f.validate_sdk(f.kind).valid
            f.fresh_terminal()
            self.baseline = self.snapshot()
            f.policy.mark_transition(history_snapshot(((37,'❯ ready'),)))
            self.view = history.try_bind_resume_view(f.offer(),policy=f.policy,
                snapshot=self.baseline,frame=1,native_owner=f.native,
                controller_owner=f.controller,transition_owner=f.transition)
            assert self.view is not None
            self.bindings = dict(controller_owner=f.controller,scope=f.scope,state=f.state,
                transition_owner=f.transition)
            self.journal = _create_context_journal(**self.bindings)
            self.command = echo.begin_context_command(f.scope,f.state,f.native,f.transition,
                f.policy,self.baseline,1,_resume_view=self.view,_controller_owner=f.controller,
                _diagnostic_journal=self.journal)
            return self
        except BaseException:
            self.fixture.__exit__(); raise

    def submit(self, *, extra=()):
        assert self.command.type_bytes(self.baseline,1)==b'/context'
        self.command.check_edit(self.baseline,1,8)
        self.journal.acknowledge(8,submission=False,remaining=8)
        current = replace(self.snapshot(extra=(*extra,(37,'❯ /context'))),cursorX=10)
        assert self.command.observe(current,2)=='COMMAND_ECHO_MATCHED'
        assert self.command.submit_bytes(current,2)==b'\r'
        self.journal.acknowledge(1,submission=True,remaining=1)
        self.command.submission_written(1)

    def observe(self, snapshot, frame):
        self.command.observe(snapshot,frame)
        return self.command.context_display_percent(snapshot,frame)

    def __exit__(self, *args):
        self.command.invalidate('INPUT_PROBE_REVOKED')
        self.journal.finish()
        self.fixture.__exit__(*args)
