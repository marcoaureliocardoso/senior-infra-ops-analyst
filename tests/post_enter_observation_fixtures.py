"""Synthetic owned observation fixtures. Never mounted into native runs."""
from dataclasses import replace
from context_display_fixtures import DisplayCase
from resume_history_fixtures import history_snapshot
import terminal_context_echo as echo
import terminal_resume_history as history


class ObservationCase(DisplayCase):
    def __enter__(self):
        f=self.fixture.__enter__()
        try:
            f.complete_initial(); assert f.validate_sdk(f.kind).valid
            f.fresh_terminal()
            self.baseline=self.snapshot()
            self.request=history.offer_post_enter_observation(f.case,state=f.state,
                scope=f.scope,command=f.resume_command)
            offer=history.observation_resume_offer(self.request,state=f.state,
                scope=f.scope,command=f.resume_command)
            f.policy.mark_transition(history_snapshot(((37,'❯ ready'),)))
            self.view=history.try_bind_resume_view(offer,policy=f.policy,
                snapshot=self.baseline,frame=1,native_owner=f.native,
                controller_owner=f.controller,transition_owner=f.transition)
            self.command=echo.begin_context_command(f.scope,f.state,f.native,f.transition,
                f.policy,self.baseline,1,_resume_view=self.view,_controller_owner=f.controller,
                _post_enter_request=self.request)
            # DisplayCase.submit records through the journal as well.
            from terminal_context_diagnostics import _create_context_journal
            self.journal=_create_context_journal(controller_owner=f.controller,
                scope=f.scope,state=f.state,transition_owner=f.transition)
            return self
        except BaseException:
            self.fixture.__exit__(); raise

    def submit(self,*,extra=(),wait_free=None,ack=1):
        assert self.command.type_bytes(self.baseline,1)==b'/context'
        self.command.check_edit(self.baseline,1,8)
        self.preenter=replace(self.snapshot(extra=(*extra,(37,'❯ /context'))),cursorX=10)
        assert self.command.observe(self.preenter,2)=='COMMAND_ECHO_MATCHED'
        self.observer=echo._prepare_post_enter_observation(self.command,self.preenter,2,
            request=self.request,controller_owner=self.fixture.controller)
        assert self.command.submit_bytes(self.preenter,2)==b'\r'
        if wait_free is not None:
            self.preenter=replace(self.snapshot(free=wait_free,extra=(*extra,(37,'❯ /context'))),cursorX=10)
            self.command.observe(self.preenter,3)
        self.command.submission_written(ack)

    def detach(self):
        if hasattr(self,'observer') and not getattr(self,'guard_taken',False):
            from terminal_post_enter_observation import _OBSERVATIONS
            self.guard_taken=True
            return _OBSERVATIONS[self.observer]['guard']
        return history.detach_post_enter_history(self.request,view=self.view,
            command=self.command,snapshot=self.preenter,
            frame=2,controller_owner=self.fixture.controller)

    def __exit__(self,*args):
        if hasattr(self,'observer'): self.observer.close()
        super().__exit__(*args)

    def validate_guard(self,guard,snapshot=None,frame=3,**overrides):
        f=self.fixture
        bindings=dict(policy=f.policy,snapshot=snapshot or self.snapshot(),frame=frame,
            state=f.state,scope=f.scope,native_owner=f.native,
            controller_owner=f.controller,transition_owner=f.transition)
        return history.validate_post_enter_history(guard,**{**bindings,**overrides})
