"""Isolated-scope and pinned echo/clear proof tests; no Claude or provider."""
import copy
from dataclasses import replace
import importlib.util
import os
from pathlib import Path
import sys
import time
import unittest
from unittest import mock

from terminal_input_policy import TerminalInputPolicy
from terminal_state_adapter import TerminalCell, TerminalSnapshot, TerminalState


def snapshot(text='❯\u00a0',*,x=2,y=37,active='alternate',extra=()):
    lines={y:text,**dict(extra)}
    rows=[]
    for index in range(40):
        row=[TerminalCell(char,1) for char in lines.get(index,'')]
        row.extend(TerminalCell('',1) for _ in range(120-len(row)))
        rows.append(tuple(row))
    return TerminalSnapshot(active,x,y,0,0,tuple(rows),
        {key:0 for key in ('primaryAttributes','secondaryAttributes','cursorPosition','status','other')})


class InputChallengeTests(unittest.TestCase):
    def setUp(self):
        path=Path(__file__).with_name('terminal_input_challenge.py')
        self.assertTrue(path.is_file(),'private input protocol missing')
        # Keep one module/brand across cases; no caller data can recreate it.
        if 'terminal_input_challenge' not in sys.modules:
            spec=importlib.util.spec_from_file_location('terminal_input_challenge',path)
            module=importlib.util.module_from_spec(spec); sys.modules[spec.name]=module
            spec.loader.exec_module(module)
        self.m=sys.modules['terminal_input_challenge']
        self.terminal=TerminalState(Path(os.environ['P004B_TERMINAL_NODE']),
            Path(os.environ['P004B_TERMINAL_MODULE_ROOT']),time.monotonic()+20)
        self.addCleanup(self.terminal.close)

    def scope(self,terminal=None,issuer=None):
        with mock.patch.object(self.m,'audit_offline_namespace',return_value={
                'networkIsolated':True,'operatorStateHidden':True,'capabilitiesDropped':True}):
            issuer=issuer or self.m.create_offline_probe_issuer()
            return issuer.issue_scope(terminal or self.terminal,object()),issuer

    def fixture_challenge(self,initial=None):
        self.terminal=TerminalState(Path(os.environ['P004B_TERMINAL_NODE']),
            Path(os.environ['P004B_TERMINAL_MODULE_ROOT']),time.monotonic()+20)
        self.addCleanup(self.terminal.close)
        scope,_issuer=self.scope(); owner=object(); transition=object()
        empty=initial or snapshot()
        return self.m.NonceInputChallenge(scope,owner,transition,TerminalInputPolicy(),empty,1),owner,transition,empty

    def echo_frame(self,marker,**kwargs):
        return snapshot('❯\u00a0'+marker.decode('ascii'),x=2+len(marker),**kwargs)

    def proven(self):
        challenge,owner,transition,empty=self.fixture_challenge()
        marker=challenge.type_bytes(empty,1)
        challenge.observe(self.echo_frame(marker),2)
        challenge.clear_bytes(self.echo_frame(marker),2)
        challenge.observe(empty,3)
        return challenge,challenge.ownership_proof(),owner,transition,empty

    def assert_reason(self,reason,call):
        with self.assertRaises(self.m.InputProofError) as caught: call()
        self.assertEqual(caught.exception.reason,reason)
        self.assertEqual(str(caught.exception),reason)

    def test_exact_echo_clear_mints_one_exit_proof(self):
        c,owner,transition,empty=self.fixture_challenge()
        marker=c.type_bytes(empty,1)
        self.assertEqual(len(marker),16); self.assertRegex(marker.decode(),r'^[0-9a-f]{16}$')
        self.assertEqual(c.observe(self.echo_frame(marker),2),'ECHO_MATCHED')
        self.assertEqual(c.clear_bytes(self.echo_frame(marker),2),b'\x15')
        self.assertEqual(c.observe(empty,3),'PROVEN')
        proof=c.ownership_proof()
        self.assertTrue(c.consume_exit(proof,empty,3,owner,transition))
        self.assertFalse(c.consume_exit(proof,empty,3,owner,transition))
        self.assertNotIn(marker.decode(),repr(c)+repr(proof))

    def test_partial_echo_is_pending_but_no_clear_or_proof(self):
        c,_owner,_transition,empty=self.fixture_challenge(); marker=c.type_bytes(empty,1)
        self.assertEqual(c.observe(self.echo_frame(marker[:4]),2),'ECHO_PENDING')
        self.assert_reason('INPUT_PROBE_STATE_REJECTED',c.ownership_proof)

    def test_missing_echo_cannot_mint_proof(self):
        c,_,_,empty=self.fixture_challenge(); c.type_bytes(empty,1)
        self.assertEqual(c.observe(empty,2),'ECHO_PENDING')
        self.assert_reason('INPUT_PROBE_STATE_REJECTED',c.ownership_proof)

    def test_postwrite_generation_is_required(self):
        c,_,_,empty=self.fixture_challenge(); marker=c.type_bytes(empty,1)
        self.assert_reason('INPUT_PROBE_STATE_REJECTED',lambda:c.observe(self.echo_frame(marker),1))

    def test_partial_then_full_echo_is_correlated(self):
        c,_,_,empty=self.fixture_challenge(); marker=c.type_bytes(empty,1)
        c.observe(self.echo_frame(marker[:4]),2)
        self.assertEqual(c.observe(self.echo_frame(marker),3),'ECHO_MATCHED')
        self.assertEqual(c.clear_bytes(self.echo_frame(marker),3),b'\x15')

    def test_ascii_marker_must_occupy_exact_cells_not_one_string_cell(self):
        c,_,_,empty=self.fixture_challenge(); marker=c.type_bytes(empty,1)
        rows=list(empty.rows); row=list(rows[37]); row[2]=TerminalCell(marker.decode(),1)
        rows[37]=tuple(row)
        forged=replace(empty,rows=tuple(rows),cursorX=18)
        self.assert_reason('INPUT_PROBE_ECHO_REJECTED',lambda:c.observe(forged,2))

    def test_wrong_echo_location_buffer_and_extra_text_revoke(self):
        for kind in ('wrong','row','buffer','extra','history'):
            # Each case owns a new terminal scope; failure must be terminal.
            terminal=TerminalState(Path(os.environ['P004B_TERMINAL_NODE']),
                Path(os.environ['P004B_TERMINAL_MODULE_ROOT']),time.monotonic()+20)
            self.addCleanup(terminal.close)
            scope,_=self.scope(terminal)
            c=self.m.NonceInputChallenge(scope,object(),object(),TerminalInputPolicy(),snapshot(),1)
            marker=c.type_bytes(snapshot(),1)
            states={'wrong':snapshot('❯\u00a0wrong',x=7),
                'row':self.echo_frame(marker,y=36),'buffer':self.echo_frame(marker,active='normal'),
                'extra':snapshot('❯\u00a0'+marker.decode()+'x',x=19),
                'history':snapshot(extra=((1,'❯\u00a0'+marker.decode()),))}
            self.assert_reason('INPUT_PROBE_ECHO_REJECTED',lambda:c.observe(states[kind],2))
            self.assert_reason('INPUT_PROBE_REVOKED',lambda:c.clear_bytes(self.echo_frame(marker),3))

    def test_auth_and_menu_revocation_latches(self):
        for heading in ('Do you want to use this API key?','Yes, I trust this folder','Press Esc to close'):
            terminal=TerminalState(Path(os.environ['P004B_TERMINAL_NODE']),
                Path(os.environ['P004B_TERMINAL_MODULE_ROOT']),time.monotonic()+20)
            self.addCleanup(terminal.close); scope,_=self.scope(terminal)
            c=self.m.NonceInputChallenge(scope,object(),object(),TerminalInputPolicy(),snapshot(),1)
            marker=c.type_bytes(snapshot(),1)
            self.assert_reason('INPUT_PROBE_REVOKED',lambda:c.observe(self.echo_frame(marker,extra=((1,heading),)),2))
            self.assert_reason('INPUT_PROBE_REVOKED',lambda:c.observe(self.echo_frame(marker),3))

    def test_clear_cannot_use_stale_empty_frame(self):
        c,_,_,empty=self.fixture_challenge(); marker=c.type_bytes(empty,1)
        c.observe(self.echo_frame(marker),2); c.clear_bytes(self.echo_frame(marker),2)
        self.assert_reason('INPUT_PROBE_STATE_REJECTED',lambda:c.observe(empty,2))

    def test_clear_must_restore_exact_owned_empty_anchor(self):
        c,_,_,empty=self.fixture_challenge(); marker=c.type_bytes(empty,1)
        c.observe(self.echo_frame(marker),2); c.clear_bytes(self.echo_frame(marker),2)
        self.assert_reason('INPUT_PROBE_CLEAR_REJECTED',lambda:c.observe(snapshot('❯\u00a0other',x=7),3))

    def test_instance_transition_and_reconstructed_proof_are_rejected(self):
        for which in ('owner','transition','dict','clone'):
            c,proof,owner,transition,empty=self.proven()
            token=proof if which in ('owner','transition') else (
                {} if which=='dict' else object.__new__(self.m.InputOwnershipProof))
            self.assertFalse(c.consume_exit(token,empty,3,object() if which=='owner' else owner,
                object() if which=='transition' else transition))
            self.assertFalse(c.consume_exit(proof,empty,3,owner,transition))

    def test_deadline_fences_each_next_action(self):
        for phase in ('type','echo','clear','proof','exit'):
            c,owner,transition,empty=self.fixture_challenge()
            marker=None
            if phase!='type': marker=c.type_bytes(empty,1)
            if phase in ('clear','proof','exit'): c.observe(self.echo_frame(marker),2)
            if phase in ('proof','exit'):
                c.clear_bytes(self.echo_frame(marker),2); c.observe(empty,3)
            proof=c.ownership_proof() if phase=='exit' else None
            with mock.patch.object(self.m,'_now',return_value=self.terminal.operation_deadline+1):
                if phase=='exit': self.assertFalse(c.consume_exit(proof,empty,3,owner,transition))
                else:
                    call={'type':lambda:c.type_bytes(empty,1),'echo':lambda:c.observe(self.echo_frame(marker),2),
                        'clear':lambda:c.clear_bytes(self.echo_frame(marker),2),'proof':c.ownership_proof}[phase]
                    self.assert_reason('INPUT_PROBE_DEADLINE',call)

    def test_scope_is_one_shot_and_not_json_or_public_constructor(self):
        scope,issuer=self.scope()
        self.m.NonceInputChallenge(scope,object(),object(),TerminalInputPolicy(),snapshot(),1)
        self.assert_reason('INPUT_PROBE_SCOPE_REJECTED',lambda:
            self.m.NonceInputChallenge(scope,object(),object(),TerminalInputPolicy(),snapshot(),1))
        self.assert_reason('INPUT_PROBE_SCOPE_REJECTED',lambda:
            self.m.NonceInputChallenge({},object(),object(),TerminalInputPolicy(),snapshot(),1))
        with mock.patch.object(self.m,'audit_offline_namespace',return_value={
                'networkIsolated':True,'operatorStateHidden':True,'capabilitiesDropped':True}):
            self.assert_reason('INPUT_PROBE_SCOPE_REJECTED',lambda:issuer.issue_scope(self.terminal,object()))
        self.assert_reason('INPUT_PROBE_SCOPE_REJECTED',self.m.OfflineProbeScope)

    def test_real_host_namespace_cannot_issue_authority(self):
        self.assert_reason('INPUT_PROBE_SCOPE_REJECTED',self.m.create_offline_probe_issuer)

    def test_scope_requires_all_actual_audit_facts(self):
        for bad in ({},{'networkIsolated':True,'operatorStateHidden':True,'capabilitiesDropped':False}):
            with mock.patch.object(self.m,'audit_offline_namespace',return_value=bad):
                self.assert_reason('INPUT_PROBE_SCOPE_REJECTED',self.m.create_offline_probe_issuer)

    def test_clear_only_once_and_observation_cannot_retry(self):
        c,_,_,empty=self.fixture_challenge(); marker=c.type_bytes(empty,1)
        c.observe(self.echo_frame(marker),2); c.clear_bytes(self.echo_frame(marker),2)
        self.assert_reason('INPUT_PROBE_STATE_REJECTED',lambda:c.clear_bytes(self.echo_frame(marker),2))
        self.assert_reason('INPUT_PROBE_REVOKED',lambda:c.type_bytes(empty,3))


if __name__=='__main__': unittest.main()
