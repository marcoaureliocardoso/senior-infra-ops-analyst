"""Private offline observation state. Never an input or acceptance capability."""
import copy
import weakref
import terminal_resume_history as history

_SEAL=object()
_OBSERVATIONS=weakref.WeakKeyDictionary()
_COMMAND_OBSERVERS=weakref.WeakKeyDictionary()


class PostEnterObservation:
    __slots__=('__weakref__',)
    def __new__(cls,seal=None):
        if seal is not _SEAL: raise RuntimeError('OBSERVATION_UNPROVEN')
        return super().__new__(cls)

    def __repr__(self): return '<PostEnterObservation>'

    @property
    def phase(self): return _OBSERVATIONS[self]['phase']

    def invalidate(self,_reason): self.close()

    def close(self):
        record=_OBSERVATIONS.get(self)
        if record is None or record.get('closed'): return
        summary=record.get('summary',{'outcome':'SAFETY_STOP',
            'stopCategory':'OWNER_LOST','profileObserved':False})
        history.close_post_enter_history(record.get('guard'))
        record.clear(); record.update(phase='FINISHED',closed=True,summary=summary)

    def summary(self):
        record=_OBSERVATIONS[self]
        if record['phase']!='FINISHED': raise RuntimeError('OBSERVATION_PENDING')
        return copy.deepcopy(record['summary'])


def _create(command,record,request,snapshot,frame):
    from terminal_context_echo import _COMMANDS
    if _COMMANDS.get(command) is not record or command in _COMMAND_OBSERVERS:
        raise RuntimeError('OBSERVATION_UNPROVEN')
    pending=history._registered(request,history._OBS_REQUESTS,history.PostEnterObservationRequest)
    if pending['phase']!='OFFERED' or pending.get('observer') is not None:
        raise RuntimeError('OBSERVATION_UNPROVEN')
    observer=PostEnterObservation(_SEAL)
    _OBSERVATIONS[observer]={'phase':'PREPARED','closed':False,
        'command':weakref.ref(command),'request':request}
    _COMMAND_OBSERVERS[command]=observer
    pending['observer']=observer
    pending['dependents']=[weakref.ref(observer)]
    _refresh(observer,command,record,snapshot,frame)
    return observer


def _refresh(observer,command,record,snapshot,frame):
    from terminal_context_echo import _COMMANDS,_DISPLAY_TRACKERS,_MENU_BINDINGS
    current=_OBSERVATIONS.get(observer)
    if (current is None or current['phase']!='PREPARED' or current['command']() is not command
            or _COMMANDS.get(command) is not record): raise RuntimeError('OBSERVATION_UNPROVEN')
    tracker=_DISPLAY_TRACKERS[command]
    origin,selection=_MENU_BINDINGS[command]
    current.update({key:record[key] for key in ('scope','state','native','transition',
        'policy','run','deadline','controller','anchor','row','time')})
    current.update(snapshot=snapshot,frame=frame,baseline=tracker['baseline'],
        inventory=set(tracker['inventory']),menu_index=selection[0] if selection else None,
        menu_row=selection[1] if selection else None,origin=origin)


def _activate(observer,command,record):
    current=_OBSERVATIONS[observer]
    if (current['phase']!='PREPARED' or current['command']() is not command
            or current['frame']!=record['submit_frame']): raise RuntimeError('OBSERVATION_UNPROVEN')
    guard=history.detach_post_enter_history(current['request'],view=record['resume_view'],
        command=command,snapshot=current['snapshot'],frame=current['frame'],
        controller_owner=current['controller'])
    current.update(guard=guard,phase='AWAIT_DISPLAY',submit_frame=record['submit_frame'])
