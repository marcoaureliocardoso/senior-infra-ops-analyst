"""One exact offline history relocation; synthetic fixtures only."""
import copy
from dataclasses import replace
import unittest

import terminal_resume_history as history
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
