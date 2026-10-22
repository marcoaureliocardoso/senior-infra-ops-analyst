"""One exact offline history relocation; synthetic fixtures only."""
import copy
from dataclasses import replace
import unittest
from unittest import mock

import terminal_resume_history as history
import terminal_context_echo as echo
from terminal_cancellation import TerminalCancelled
from terminal_state_adapter import TerminalCell
from resume_history_fixtures import CaseFixture


class SDKRelocationTests(unittest.TestCase):
    def args(self,f,b,**changes):
        args=dict(policy=f.policy,snapshot=b['snapshot'],frame=b['frame']+1,state=f.state,scope=f.scope,
            native_owner=f.native,controller_owner=f.controller,transition_owner=f.transition)
        args.update(changes); return args

    def moved(self,b,destination=6,*,text=None,duplicate=False):
        rows=list(b['snapshot'].rows)
        source=rows[5]; rows[5]=tuple(TerminalCell('',1) for _ in range(120))
        if text is not None:
            source=tuple(TerminalCell(c,1) for c in text)+tuple(TerminalCell('',1) for _ in range(120-len(text)))
        rows[destination]=source
        if duplicate: rows[7]=source
        return replace(b['snapshot'],rows=tuple(rows))

    def prepare(self,f,b,**changes):
        prepare=getattr(history,'_prepare_sdk_relocation',lambda *_a,**_k:None)
        return prepare(b['view'],b['probe'],b['evidence'],b['receipt'],**self.args(f,b,**changes))

    def commit(self,f,b,**changes):
        commit=getattr(history,'_try_commit_sdk_relocation',lambda *_a,**_k:False)
        return commit(b['view'],b['probe'],b['receipt'],**self.args(f,b,**changes))

    def edited(self,snapshot,index,text):
        rows=list(snapshot.rows)
        rows[index]=tuple(TerminalCell(c,1) for c in text)+tuple(TerminalCell('',1) for _ in range(120-len(text)))
        return replace(snapshot,rows=tuple(rows))

    def test_exact_relocation_commits_only_after_complete_same_frame_assessment(self):
        for kind in ('text-turn','skill-turn'):
            with self.subTest(kind=kind),CaseFixture(kind) as f:
                b=f.proven_resume(); record=history._VIEWS[b['view']]; original=b['probe']._proof
                moved=self.moved(b)
                self.assertTrue(self.commit(f,b,snapshot=moved),'complete same-frame transaction must commit')
                self.assertTrue(record['sdk_relocated']); self.assertEqual(record['sdk_position'],6)
                self.assertIn(5,record['retired']); self.assertEqual(set(record['profiles']),{5})
                self.assertIs(b['probe']._proof,original)
                b['probe'].observe(moved,6)
                self.assertTrue(b['probe'].consume_exit(original,moved,6,f.native,f.transition))
                self.assertFalse(b['probe'].consume_exit(original,moved,6,f.native,f.transition))

    def test_same_percentage_changed_sample_rejects_transaction(self):
        for kind in ('text-turn','skill-turn'):
            for change in ('decimal','metric-row','context-row','witness','anchor'):
                with self.subTest(kind=kind,change=change),CaseFixture(kind) as f:
                    b=f.proven_resume(); moved=self.moved(b)
                    if change=='decimal': moved=self.edited(moved,1,'Free space: 81.1%')
                    if change=='metric-row':
                        rows=list(moved.rows); rows[1],rows[3]=rows[3],rows[1]; moved=replace(moved,rows=tuple(rows))
                    if change=='context-row': moved=self.edited(moved,20,'❯\u00a0/context')
                    if change=='witness': echo._DISPLAYS.pop(echo._COMMANDS[b['command']]['display_witness'])
                    if change=='anchor': moved=replace(moved,cursorX=3)
                    with self.assertRaises(RuntimeError): self.commit(f,b,snapshot=moved)
                    self.assertEqual(history.resume_view_decision(b['view']),'REJECTED')

    def test_rejected_composition_never_publishes_candidate_state(self):
        for kind in ('text-turn','skill-turn'):
            for text in ('❯ unknown','Do you want to use this API key?','❯ /exit  Synthetic completion'):
                with self.subTest(kind=kind,row_kind=text.split()[0]),CaseFixture(kind) as f:
                    b=f.proven_resume(); record=history._VIEWS[b['view']]
                    moved=self.edited(self.moved(b),30,text); before=(dict(record['profiles']),set(record['retired']))
                    with self.assertRaises(RuntimeError): self.commit(f,b,snapshot=moved)
                    self.assertEqual((record['profiles'],record['retired']),before)
                    self.assertFalse(record['sdk_relocated']); self.assertEqual(record['sdk_position'],5)
                    self.assertEqual(history.resume_view_decision(b['view']),'REJECTED')

    def test_transaction_lifetime_replay_and_collision_matrix(self):
        for kind in ('text-turn','skill-turn'):
            for destination in (0,1,2,12,16,20,37):
                with self.subTest(kind=kind,destination=destination),CaseFixture(kind) as f:
                    b=f.proven_resume(pinned_exit=True,pre_enter_menu=True)
                    with self.assertRaises(RuntimeError): self.commit(f,b,snapshot=self.moved(b,destination))
                    self.assertEqual(history.resume_view_decision(b['view']),'REJECTED')
            for effect in ('cancel','expiry','advance','reentrant','native-exit','helper-exit'):
                with self.subTest(kind=kind,effect=effect),CaseFixture(kind) as f:
                    b=f.proven_resume(); record=history._VIEWS[b['view']]; moved=self.moved(b)
                    real_compose=echo._compose_input_assessment; real_now=history._now; changed=False
                    def compose(*args,**kwargs):
                        nonlocal changed
                        result=real_compose(*args,**kwargs); changed=True
                        if effect=='advance': record['frame']=7
                        if effect=='native-exit': f.native.returncode=0
                        if effect=='helper-exit': f.state.close()
                        if effect=='reentrant': self.commit(f,b,snapshot=moved)
                        return result
                    def cancelled():
                        if changed and effect=='cancel': raise TerminalCancelled()
                    def now(): return history._CASES[f.case]['deadline'] if changed and effect=='expiry' else real_now()
                    with mock.patch.object(echo,'_compose_input_assessment',side_effect=compose), \
                            mock.patch.object(f.state,'check_cancelled',side_effect=cancelled), \
                            mock.patch.object(history,'_now',side_effect=now), self.assertRaises(RuntimeError):
                        self.commit(f,b,snapshot=moved)
                    self.assertFalse(record['sdk_relocated']); self.assertNotIn(5,record['retired'])
                    self.assertEqual(history.resume_view_decision(b['view']),'REJECTED')

    def test_committed_placement_is_unique_stable_and_monotonic(self):
        for kind in ('text-turn','skill-turn'):
            for effect in ('disappear','second-move','old-return','duplicate','mutation','expiry','cancel'):
                with self.subTest(kind=kind,effect=effect),CaseFixture(kind) as f:
                    b=f.proven_resume(); moved=self.moved(b)
                    self.assertTrue(self.commit(f,b,snapshot=moved),'first exact transaction must commit')
                    invalid=moved
                    if effect=='disappear': invalid=self.edited(moved,6,'')
                    if effect=='second-move': invalid=self.moved(b,7)
                    if effect in ('old-return','duplicate'):
                        rows=list(moved.rows); rows[5 if effect=='old-return' else 7]=rows[6]
                        invalid=replace(moved,rows=tuple(rows))
                    if effect=='mutation':
                        prompt=history.TEXT_PROMPT if kind=='text-turn' else history.SKILL_PROMPT
                        invalid=self.edited(moved,6,'❯\u00a0'+prompt)
                    when=(mock.patch.object(history,'_now',return_value=history._CASES[f.case]['deadline'])
                        if effect=='expiry' else mock.patch.object(f.state,'check_cancelled',side_effect=TerminalCancelled())
                        if effect=='cancel' else mock.patch.dict({},{}))
                    with when, self.assertRaises(RuntimeError):
                        history.validate_resume_view(b['view'],**self.args(f,b,snapshot=invalid,frame=7))
                    self.assertEqual(history.resume_view_decision(b['view']),'REJECTED')

    def test_exact_candidate_is_read_only_and_not_an_exclusion_grant(self):
        for kind in ('text-turn','skill-turn'):
            with self.subTest(kind=kind),CaseFixture(kind) as f:
                b=f.proven_resume(); record=history._VIEWS[b['view']]
                before=(dict(record['profiles']),set(record['retired']),record['frame'],record['snapshot']())
                self.assertIsNone(self.prepare(f,b))
                moved=self.moved(b); candidate=self.prepare(f,b,snapshot=moved)
                self.assertIsNotNone(candidate,'exact baseline correspondence must produce a read-only proposal')
                self.assertEqual((record['profiles'],record['retired'],record['frame'],record['snapshot']()),before)
                self.assertFalse(record['sdk_relocated'])
                indices=history.validate_resume_view(b['view'],**self.args(f,b,snapshot=moved),_history_read=candidate)
                self.assertEqual(indices,frozenset((6,)))
                with self.assertRaises(history.ResumeHistoryError):
                    history.validate_resume_view(b['view'],**self.args(f,b,snapshot=moved))

    def test_retired_source_is_identity_not_authority(self):
        for kind in ('text-turn','skill-turn'):
            with self.subTest(kind=kind),CaseFixture(kind) as f:
                b=f.proven_resume(); rows=list(b['snapshot'].rows); rows[5]=tuple(TerminalCell('',1) for _ in range(120))
                gone=replace(b['snapshot'],rows=tuple(rows))
                history.validate_resume_view(b['view'],**self.args(f,b,snapshot=gone))
                candidate=self.prepare(f,b,snapshot=self.moved(b),frame=7)
                self.assertIsNotNone(candidate,'retired source identity must support only one new exact placement')
                self.assertIn(5,history._VIEWS[b['view']]['retired'])
                with self.assertRaises(history.ResumeHistoryError):
                    history.validate_resume_view(b['view'],**self.args(f,b,snapshot=b['snapshot'],frame=8))

    def test_candidate_identity_collision_and_replay_matrix(self):
        for kind in ('text-turn','skill-turn'):
            for mutation in ('padding','marker','tail','kind','width','duplicate','late','cursor','old-history',
                    'owner','frame','geometry','copy','serialized','replay'):
                with self.subTest(kind=kind,mutation=mutation),CaseFixture(kind) as f:
                    b=f.proven_resume(sdk_history=mutation!='late')
                    prompt=history.TEXT_PROMPT if kind=='text-turn' else history.SKILL_PROMPT
                    text='❯ '+prompt
                    if mutation=='padding': text='❯\u00a0'+prompt
                    if mutation=='marker': text=' ❯ '+prompt
                    if mutation=='tail': text+='\u00a0'
                    if mutation=='kind': text='❯ '+(history.SKILL_PROMPT if kind=='text-turn' else history.TEXT_PROMPT)
                    moved=self.moved(b,text=text,duplicate=mutation=='duplicate')
                    if mutation=='width':
                        rows=list(moved.rows); row=list(rows[6]); row[0]=TerminalCell('❯',2); rows[6]=tuple(row)
                        moved=replace(moved,rows=tuple(rows))
                    if mutation=='cursor': moved=self.moved(b,37)
                    if mutation=='old-history': moved=self.moved(b,5)
                    changes=dict(snapshot=moved)
                    if mutation=='owner': changes['native_owner']=object()
                    if mutation=='frame': changes['frame']=4
                    if mutation=='geometry': changes['snapshot']=replace(moved,baseY=1)
                    if mutation in ('copy','serialized','replay'):
                        candidate=self.prepare(f,b,snapshot=moved)
                        self.assertIsNotNone(candidate,'exact correspondence must produce proposal before replay checks')
                        if mutation=='copy':
                            try: candidate=copy.copy(candidate)
                            except (TypeError,history.ResumeHistoryError): continue
                        if mutation=='serialized': candidate={}
                        if mutation=='replay': changes['snapshot']=replace(moved)
                        with self.assertRaises(RuntimeError):
                            history.validate_resume_view(b['view'],**self.args(f,b,**changes),_history_read=candidate)
                    elif mutation=='old-history': self.assertIsNone(self.prepare(f,b,**changes))
                    else:
                        with self.assertRaises(RuntimeError): self.prepare(f,b,**changes)


if __name__=='__main__': unittest.main()
