"""Private offline observation state. Never an input or acceptance capability."""
import copy
from dataclasses import replace
import math
import time
import weakref
import terminal_resume_history as history
from terminal_context_sample import sample_context
from terminal_state_adapter import TerminalSnapshot

_SEAL=object()
_OBSERVATIONS=weakref.WeakKeyDictionary()
_COMMAND_OBSERVERS=weakref.WeakKeyDictionary()
OUTCOMES=frozenset(('CURRENT_PROFILE_OBSERVED','INVENTORIED_CELL_REPLACEMENT',
    'UNSUPPORTED_TRANSITION','DEADLINE','SAFETY_STOP','SETUP_BLOCKED','CLEANUP_FAILED'))
STOP_CATEGORIES=frozenset(('COMPLETE','SETUP','AUTHENTICATION','CANCELLED','DEADLINE',
    'OWNER_LOST','PROCESS_EXIT','GEOMETRY','CAPTURE_PROTOCOL','UNKNOWN_ROW','MENU_CHANGED',
    'INPUT_CHANGED','HISTORY_CONFLICT','NUMERIC_CONFLICT','PROFILE_LOST','WRITE_ATTEMPT','REPORT','CLEANUP'))
_ENUMS={'menuState':frozenset(('NOT_BOUND','EXACT_PRESENT','DISAPPEARED','CHANGED','MOVED','DUPLICATED','REAPPEARED')),
    'inputState':frozenset(('OWNED_COMMAND_ECHO','EMPTY','UNSUPPORTED','UNOBSERVED')),
    'commitRelation':frozenset(('NONE','NEW_CELL','PREENTER_INVENTORY','PINNED','RETIRED','MULTIPLE')),
    'numericRelation':frozenset(('ABSENT','BASELINE_EQUIVALENT','DISTINCT','CONFLICT'))}


def valid_observation_summary(value):
    required={'outcome','stopCategory','profileObserved'}
    if type(value) is not dict or not required<=set(value)<=required|set(_ENUMS): return False
    if (type(value['outcome']) is not str or value['outcome'] not in OUTCOMES
            or type(value['stopCategory']) is not str or value['stopCategory'] not in STOP_CATEGORIES
            or type(value['profileObserved']) is not bool
            or value['profileObserved']!=(value['outcome']=='CURRENT_PROFILE_OBSERVED')): return False
    if value['profileObserved'] and not (value['stopCategory']=='COMPLETE'
            and value.get('menuState') in ('NOT_BOUND','DISAPPEARED')
            and value.get('inputState')=='EMPTY' and value.get('commitRelation')=='NEW_CELL'
            and value.get('numericRelation') in ('BASELINE_EQUIVALENT','DISTINCT')): return False
    return all(type(value[key]) is str and value[key] in choices
        for key,choices in _ENUMS.items() if key in value)


def _owned_echo(record,snapshot):
    anchor=record['anchor']; cursor=snapshot.baseY+snapshot.cursorY-snapshot.viewportY
    if cursor!=anchor.row or snapshot.cursorX!=anchor.cursorX+8: return False
    row=snapshot.rows[cursor]; start=anchor.cursorX
    return (row[:start]==record['row'][:start]
        and all(cell.width==1 and cell.text==char for cell,char in zip(row[start:start+8],'/context'))
        and all(cell.width==1 and cell.text in ('',' ','\t','\u00a0') for cell in row[start+8:]))


class PostEnterObservation:
    __slots__=('__weakref__',)
    def __new__(cls,seal=None):
        if seal is not _SEAL: raise RuntimeError('OBSERVATION_UNPROVEN')
        return super().__new__(cls)

    def __repr__(self): return '<PostEnterObservation>'

    @property
    def phase(self): return _OBSERVATIONS[self]['phase']

    @property
    def candidate_ready(self): return self.phase=='CANDIDATE'

    def stop(self,outcome,stop_category):
        if (type(outcome) is not str or outcome not in OUTCOMES or outcome=='CURRENT_PROFILE_OBSERVED'
                or type(stop_category) is not str or stop_category not in STOP_CATEGORIES):
            raise RuntimeError('OBSERVATION_UNPROVEN')
        self._finish(outcome,stop_category)

    def _finish(self,outcome,category):
        record=_OBSERVATIONS[self]
        if record['phase']=='FINISHED': return
        detail={key:record[key] for key in _ENUMS if key in record}
        record['summary']={**detail,'outcome':outcome,'stopCategory':category,
            'profileObserved':outcome=='CURRENT_PROFILE_OBSERVED'}
        record['phase']='FINISHED'

    def observe(self,snapshot,frame):
        record=_OBSERVATIONS[self]
        if record['phase']=='FINISHED': return
        if record['phase'] not in ('AWAIT_DISPLAY','CANDIDATE'):
            self.stop('SETUP_BLOCKED','SETUP'); return
        now=time.monotonic()
        if type(now) not in (int,float) or not math.isfinite(now) or now<record['time']:
            self.stop('SAFETY_STOP','OWNER_LOST'); return
        if now>=record['deadline']:
            self.stop('DEADLINE','DEADLINE'); return
        record['time']=now
        if (type(snapshot) is not TerminalSnapshot or type(frame) is not int
                or frame<=record['submit_frame']):
            self.stop('SAFETY_STOP','CAPTURE_PROTOCOL'); return
        policy=record['policy']
        if policy.active_input_forbidden(snapshot):
            self.stop('SAFETY_STOP','AUTHENTICATION'); return
        if (snapshot.active,snapshot.baseY,snapshot.viewportY)!=record['geometry']:
            self.stop('SAFETY_STOP','GEOMETRY'); return
        try:
            old=history.validate_post_enter_history(record['guard'],policy=policy,
                snapshot=snapshot,frame=frame,state=record['state'],scope=record['scope'],
                native_owner=record['native'],controller_owner=record['controller'],
                transition_owner=record['transition'])
        except history.ResumeHistoryError as error:
            # Case failure may already have invalidated/closed this observer.
            if self.phase!='FINISHED':
                if error.reason=='RESUME_HISTORY_LAYOUT_REJECTED': self.stop('UNSUPPORTED_TRANSITION','HISTORY_CONFLICT')
                else: self.stop('SAFETY_STOP','OWNER_LOST')
            return
        except (RuntimeError,TypeError,ValueError):
            if self.phase!='FINISHED': self.stop('SAFETY_STOP','CAPTURE_PROTOCOL')
            return
        # The observation profile supports width-one marker rows only. The
        # ordinary empty-input assessor may tolerate blank wide cells; that
        # does not make them part of this separately reviewed profile.
        if any(any(cell.width!=1 for cell in row) for row in snapshot.rows
                if any(cell.text=='❯' for cell in row)):
            self.stop('UNSUPPORTED_TRANSITION','UNKNOWN_ROW'); return
        sample=sample_context(snapshot)
        record['numericRelation']=('ABSENT' if sample is None else
            'BASELINE_EQUIVALENT' if sample.numbers==record['baseline'] else 'DISTINCT')
        if sample is not None:
            if record.get('distinct') is not None and sample.numbers!=record['distinct']:
                record['numericRelation']='CONFLICT'; self.stop('UNSUPPORTED_TRANSITION','NUMERIC_CONFLICT'); return
            if sample.numbers!=record['baseline']: record['distinct']=sample.numbers
        from terminal_context_echo import _history_rows
        matches=_history_rows(policy,snapshot,_excluded_rows=old)
        record['commitRelation']='NONE' if not matches else 'NEW_CELL' if len(matches)==1 else 'MULTIPLE'
        if len(matches)>1:
            self.stop('UNSUPPORTED_TRANSITION','HISTORY_CONFLICT'); return
        if matches and matches[0] in record['inventory']:
            record['commitRelation']='PREENTER_INVENTORY'
            self.stop('INVENTORIED_CELL_REPLACEMENT','HISTORY_CONFLICT'); return
        menu=record['menu_index']
        completion=[index for index,row in enumerate(snapshot.rows) if policy._context_completion_row(row)]
        record['menuState']='NOT_BOUND' if menu is None else 'DISAPPEARED'
        if completion:
            if menu is None:
                self.stop('UNSUPPORTED_TRANSITION','UNKNOWN_ROW'); return
            if len(completion)>1: record['menuState']='DUPLICATED'
            elif completion!=[menu]: record['menuState']='MOVED'
            elif record.get('menu_retired'): record['menuState']='REAPPEARED'
            elif snapshot.rows[menu]!=record['menu_row']: record['menuState']='CHANGED'
            else: record['menuState']='EXACT_PRESENT'
            if record['menuState']!='EXACT_PRESENT':
                self.stop('UNSUPPORTED_TRANSITION','MENU_CHANGED'); return
        else: record['menu_retired']=True
        own=_owned_echo(record,snapshot)
        if own and record.get('input_retired'):
            record['inputState']='UNSUPPORTED'; self.stop('UNSUPPORTED_TRANSITION','INPUT_CHANGED'); return
        if not own: record['input_retired']=True
        observed=snapshot
        if own:
            anchor=record['anchor']; rows=list(snapshot.rows); rows[anchor.row]=record['row']
            observed=replace(snapshot,cursorX=anchor.cursorX,rows=tuple(rows))
        excluded=old|frozenset(matches)|frozenset(completion)
        assessment,_=policy._empty_input_assessment(observed,_excluded_rows=excluded)
        record['inputState']='OWNED_COMMAND_ECHO' if own else 'EMPTY' if assessment.anchor is not None else 'UNSUPPORTED'
        if assessment.anchor is None:
            self.stop('UNSUPPORTED_TRANSITION','UNKNOWN_ROW'); return
        full=not own and not completion and bool(matches) and sample is not None
        candidate=(matches[0],snapshot.rows[matches[0]],sample,assessment.anchor) if full else None
        if record['phase']=='CANDIDATE':
            if candidate!=record['candidate']: self.stop('UNSUPPORTED_TRANSITION','PROFILE_LOST')
        elif candidate is not None:
            record.update(phase='CANDIDATE',candidate=candidate)

    def complete(self,snapshot,frame):
        if not self.candidate_ready: return
        self.observe(snapshot,frame)
        if self.candidate_ready: self._finish('CURRENT_PROFILE_OBSERVED','COMPLETE')

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
    current.update(guard=guard,phase='AWAIT_DISPLAY',submit_frame=record['submit_frame'],
        geometry=(current['snapshot'].active,current['snapshot'].baseY,current['snapshot'].viewportY))
