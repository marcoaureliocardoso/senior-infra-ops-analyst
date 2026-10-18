"""Content-free fixture classifiers and private resumed-case contracts."""
import copy
import dataclasses
import importlib
from pathlib import Path
import unittest
from unittest import mock

from terminal_state_adapter import TerminalCell
from resume_history_fixtures import history_snapshot, sdk_stream, sdk_events, encode_events, CaseFixture

SESSION = 'synthetic-session'
TEXT = 'P0-04B synthetic text control. Reply P004B_SKILL_OK only.'
SKILL = 'P0-04B synthetic. Invoke Skill(context-continuity) once; reply P004B_SKILL_OK. No browser.'


class ResumeHistoryTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(Path(__file__).with_name('terminal_resume_history.py').is_file(),
                        'resumed-history classifier component missing')
        self.module = importlib.import_module('terminal_resume_history')

    def parse(self, raw, kind='text-turn'):
        return self.module.parse_sdk_sample(raw, expected_session=SESSION, case_kind=kind)

    def test_public_fixture_profiles_are_complete_and_content_free(self):
        for kind, token in (('CONTEXT', '/context'), ('EXIT', '/exit'),
                            ('SDK_TEXT', TEXT), ('SDK_SKILL', SKILL)):
            for gap in (' ', '\u00a0', ' \u00a0'):
                with self.subTest(kind=kind, gap=repr(gap)):
                    row = history_snapshot(((5, '  ❯'+gap+token+'\u00a0'),)).rows[5]
                    profile = self.module.match_history_row(row, kind)
                    self.assertIsNotNone(profile)
                    self.assertEqual(profile.kind, kind)
                    self.assertEqual(profile.marker_x, 2)
                    self.assertEqual(profile.gap, tuple(1 if c=='\u00a0' else 0 for c in gap))
                    self.assertEqual(profile.tail[0], 1)
                    self.assertNotIn(token, repr(profile))
                    with self.assertRaises(dataclasses.FrozenInstanceError):
                        profile.marker_x = 9
        self.assertIsNone(self.module.match_history_row(
            history_snapshot(((5, '❯ /context extra'),)).rows[5], 'CONTEXT'))

    def test_profile_rejects_unsupported_cells_geometry_and_partial_tokens(self):
        row = history_snapshot(((5, '❯ /context'),)).rows[5]
        invalid = [row[:-1], row+(TerminalCell('', 1),), list(row)]
        for index, cell in ((0, TerminalCell('❯', 2)), (1, TerminalCell('', 0)),
                            (3, TerminalCell('context', 1)), (100, TerminalCell('x', 1)),
                            (100, TerminalCell('\t', 1)), (100, TerminalCell('\u200b', 1)),
                            (100, TerminalCell('\x00', 1)), (100, TerminalCell('', True))):
            changed = list(row); changed[index] = cell; invalid.append(tuple(changed))
        for text in ('❯/context', '\u00a0❯ /context', '❯ /context ❯', '❯ /contex',
                     '❯ /context…', '❯\u2003/context', '❯ '+SKILL[:-1]):
            invalid.append(history_snapshot(((5, text),)).rows[5])
        for candidate in invalid:
            with self.subTest(candidate=invalid.index(candidate)):
                self.assertIsNone(self.module.match_history_row(candidate, 'CONTEXT'))
        self.assertIsNone(self.module.match_history_row(row, 'OTHER'))
        for kind, token in (('SDK_TEXT', TEXT), ('SDK_SKILL', SKILL)):
            for text in ('❯ '+token[:-1], '❯ '+token+' extra', '❯ '+token+'\u200b'):
                with self.subTest(kind=kind, text_length=len(text)):
                    self.assertIsNone(self.module.match_history_row(
                        history_snapshot(((5, text),)).rows[5], kind))

    def test_sdk_text_and_skill_require_session_lifecycle_and_exact_calls(self):
        for kind, calls in (('text-turn', 0), ('skill-turn', 1)):
            facts = self.parse(sdk_stream(SESSION, kind), kind)
            self.assertEqual((facts.valid, facts.reason, facts.skill_calls), (True, 'VALID', calls))
            self.assertNotIn(SESSION, repr(facts))
            with self.assertRaises(dataclasses.FrozenInstanceError):
                facts.valid = False

    def test_sdk_rejects_session_lifecycle_and_tool_contract_mutations(self):
        mutations = []
        def add(kind, mutate):
            events = sdk_events(SESSION, kind); mutate(events); mutations.append((kind, events))
        add('text-turn', lambda e: e.pop(0))
        add('text-turn', lambda e: e.pop())
        add('text-turn', lambda e: e.insert(1, copy.deepcopy(e[0])))
        add('text-turn', lambda e: e.append(copy.deepcopy(e[-1])))
        for index in range(3):
            add('text-turn', lambda e, i=index: e[i].update(session_id='wrong-session'))
        add('text-turn', lambda e: e[0].pop('session_id'))
        add('text-turn', lambda e: e[-1].update(is_error=True))
        add('text-turn', lambda e: e[-1].update(subtype='error_max_turns'))
        add('text-turn', lambda e: e[1].update(parent_tool_use_id='nested'))
        add('text-turn', lambda e: e[1]['message']['content'].append(
            {'type':'tool_use','id':'call1','name':'Skill','input':{'skill':'context-continuity'}}))
        add('text-turn', lambda e: e[1]['message'].update(hidden={
            'type':'tool_use','id':'hidden','name':'Skill','input':{}}))
        add('text-turn', lambda e: e.insert(1, {'type':'unknown','session_id':SESSION}))
        add('text-turn', lambda e: e[1]['message'].update(content=[{'type':'unknown'}]))
        add('text-turn', lambda e: e[1]['message'].update(content=[{'type':'text','text':'x'}]*65))
        add('skill-turn', lambda e: e[1]['message']['content'][0].update(name='Bash'))
        add('skill-turn', lambda e: e[1]['message']['content'][0].update(input={'skill':'other'}))
        add('skill-turn', lambda e: e[2]['message']['content'][0].update(tool_use_id='unmatched'))
        add('skill-turn', lambda e: e[2]['message']['content'][0].update(is_error=True))
        add('skill-turn', lambda e: e.pop(2))
        add('skill-turn', lambda e: e.insert(2, copy.deepcopy(e[1])))
        add('skill-turn', lambda e: e.append(copy.deepcopy(e[1])))
        add('skill-turn', lambda e: e[2]['message']['content'][0].update(content=[
            {'type':'tool_use','id':'hidden','name':'Skill','input':{}}]))
        mutations.append(('text-turn', sdk_events(SESSION, 'skill-turn')))
        mutations.append(('skill-turn', sdk_events(SESSION, 'text-turn')))
        for index, (kind, events) in enumerate(mutations):
            with self.subTest(index=index):
                facts = self.parse(encode_events(events), kind)
                self.assertFalse(facts.valid)
                self.assertIn(facts.reason, {'BOUNDS','MALFORMED','SESSION_MISMATCH','LIFECYCLE','TOOL_CONTRACT'})
                self.assertLessEqual(facts.skill_calls, 4)

    def test_sdk_bounds_duplicate_fields_nonfinite_and_untrusted_text(self):
        for raw in (b'', b'{}\n', b'not JSON', b'[]\n', b'{"type":"system","type":"result"}\n',
                    b'{"value":NaN}\n', b'['*100+b'0'+b']'*100, b'x'*5_000_001,
                    encode_events(sdk_events(SESSION, 'text-turn')*1400)):
            with self.subTest(size=len(raw)):
                self.assertFalse(self.parse(raw).valid)
        events = sdk_events(SESSION, 'text-turn')
        events[1]['message']['content'][0]['text'] = 'untrusted prose: {"type":"tool_use"}'
        self.assertTrue(self.parse(encode_events(events)).valid)
        self.assertFalse(self.module.parse_sdk_sample(sdk_stream(SESSION, 'text-turn'),
            expected_session=SESSION, case_kind='other').valid)
        nested = 'synthetic'
        for _ in range(34):
            nested = {'metadata': nested}
        events[1]['metadata'] = nested
        self.assertEqual(self.parse(encode_events(events)).reason, 'BOUNDS')

    def test_classifiers_do_not_open_files_spawn_or_mutate_input(self):
        row = history_snapshot(((5, '❯ /context'),)).rows[5]
        raw = sdk_stream(SESSION, 'text-turn')
        before = (row, raw)
        with mock.patch('builtins.open', side_effect=AssertionError('file IO')), \
             mock.patch('subprocess.Popen', side_effect=AssertionError('spawn')), \
             mock.patch('socket.socket', side_effect=AssertionError('network')):
            self.assertIsNotNone(self.module.match_history_row(row, 'CONTEXT'))
            self.assertTrue(self.parse(raw).valid)
        self.assertEqual((row, raw), before)


class ResumeCaseTests(unittest.TestCase):
    def setUp(self):
        self.m = importlib.import_module('terminal_resume_history')
        self.assertTrue(hasattr(self.m,'create_offline_case'), 'case witness issuer missing')

    def test_case_cannot_advance_from_events_exit_flags_or_sdkfacts(self):
        with CaseFixture() as f:
            with self.assertRaises(self.m.ResumeHistoryError):
                f.offer()
            self.assertFalse(hasattr(self.m.SDKFacts(True,'VALID',0),'offer_resume'))
        for name in ('OfflineCase','InitialCompletionSink','PendingInitialCompletion',
                     'SDKLaunch','ResumeOffer','ResumedHistoryView'):
            with self.subTest(name=name), self.assertRaises(self.m.ResumeHistoryError):
                getattr(self.m,name)()

    def test_foreign_replayed_and_serialized_bindings_reject(self):
        with CaseFixture() as f:
            with self.assertRaises(self.m.ResumeHistoryError):
                self.m.validate_initial_sink({'valid':True},state=f.state,scope=f.scope,command=f.initial_command)
        for replacement in ('state','scope','command'):
            with CaseFixture() as f:
                args = dict(state=f.state,scope=f.scope,command=f.initial_command)
                args[replacement] = object()
                with self.assertRaises(self.m.ResumeHistoryError):
                    self.m.validate_initial_sink(f.sink,**args)
                with self.assertRaises(self.m.ResumeHistoryError):
                    self.m.validate_initial_sink(f.sink,state=f.state,scope=f.scope,command=f.initial_command)

    def test_initial_completion_requires_consumed_proof_exact_exit_and_cleanup(self):
        for field, value in (('exit_written',5),('frame',True),('controller_owner',object()),('probe',object())):
            with self.subTest(field=field), CaseFixture() as f:
                f.initial_protocol()
                with self.assertRaises(self.m.ResumeHistoryError):
                    f.capture(**{field:value})
        for native, helper in (('CLEANUP_FAILED','CLEANUP_COMPLETED'),
                               ('CLEANUP_COMPLETED','TERMINAL_DEADLINE_EXCEEDED')):
            with CaseFixture() as f:
                f.initial_protocol(); pending=f.capture(); f.state.close()
                with self.assertRaises(self.m.ResumeHistoryError):
                    self.m.finish_initial_completion(pending,result=0,native_cleanup=native,helper_cleanup=helper)
        with CaseFixture() as f:
            f.complete_initial()
            self.assertTrue(f.validate_sdk('text-turn').valid)
            f.fresh_terminal(); offer=f.offer()
            self.assertEqual(repr(offer),'<ResumeOffer>')
            with self.assertRaises(self.m.ResumeHistoryError):
                f.offer()

    def bind(self, f, snapshot=None):
        f.complete_initial(); self.assertTrue(f.validate_sdk(f.kind).valid); f.fresh_terminal()
        offer=f.offer()
        # Freshness is observed from a real different public cell frame.
        f.policy.mark_transition(history_snapshot(((37,'❯ ready'),)))
        self.args = dict(policy=f.policy,snapshot=snapshot or history_snapshot(((5,'❯ '+TEXT),)),
            frame=1,native_owner=f.native,controller_owner=f.controller,transition_owner=f.transition)
        view=self.m.try_bind_resume_view(offer,**self.args)
        self.assertIsNotNone(view)
        return view

    def validate(self, f, view, **changes):
        args=dict(self.args,state=f.state,scope=f.scope); args.update(changes)
        return self.m.validate_resume_view(view,**args)

    def test_history_profiles_pin_once_before_submission(self):
        for changed in (history_snapshot(),history_snapshot(((6,'❯ '+TEXT),)),
                        history_snapshot(((5,'❯ '+TEXT),(6,'❯ /exit'))),
                        history_snapshot(((5,'❯ private-draft'),))):
            with CaseFixture() as f:
                view=self.bind(f)
                self.assertEqual(self.validate(f,view),frozenset({5}))
                with self.assertRaises(self.m.ResumeHistoryError):
                    self.validate(f,view,snapshot=changed,frame=2)
                with self.assertRaises(self.m.ResumeHistoryError):
                    self.validate(f,view,frame=3)

    def test_empty_view_is_branded_and_rejects_new_history_or_same_frame_copy(self):
        for change in ('new-history','same-frame-copy','foreign-owner','root-rename'):
            with self.subTest(change=change), CaseFixture() as f:
                view=self.bind(f,history_snapshot())
                self.assertEqual(self.validate(f,view),frozenset())
                args={}
                if change=='new-history': args=dict(snapshot=history_snapshot(((5,'❯ /exit'),)),frame=2)
                elif change=='same-frame-copy': args=dict(snapshot=dataclasses.replace(self.args['snapshot']))
                elif change=='foreign-owner': args=dict(native_owner=object())
                else: (f.root/'project').rename(f.root/'moved-project')
                with self.assertRaises(self.m.ResumeHistoryError): self.validate(f,view,**args)
                self.assertEqual(self.m.resume_view_decision(view),'REJECTED')

    def test_pending_view_waits_for_raw_freshness_without_fallback(self):
        with CaseFixture() as f:
            f.complete_initial(); f.validate_sdk(f.kind); f.fresh_terminal(); offer=f.offer()
            current=history_snapshot(((5,'❯ '+TEXT),))
            f.policy.mark_transition(current)
            args=dict(policy=f.policy,snapshot=current,frame=1,native_owner=f.native,
                controller_owner=f.controller,transition_owner=f.transition)
            self.assertIsNone(self.m.try_bind_resume_view(offer,**args))
            self.assertIsNone(f.policy.empty_input_anchor(current))
            args.update(snapshot=history_snapshot(((5,'❯ '+TEXT),(37,'❯\u00a0'))),frame=2)
            view=self.m.try_bind_resume_view(offer,**args)
            self.assertIsNotNone(view)
            with self.assertRaises(self.m.ResumeHistoryError):
                self.m.try_bind_resume_view(offer,**args)

    def test_public_consumed_phase_alone_cannot_make_initial_nonce_fact(self):
        import terminal_input_challenge as challenge
        with CaseFixture() as f:
            probe=challenge.NonceInputChallenge(f.scope,f.native,f.transition,f.policy,history_snapshot(),1)
            probe.phase='CONSUMED'
            self.assertFalse(challenge._initial_nonce_completed(probe,state=f.state,scope=f.scope,
                native_owner=f.native,transition_owner=f.transition))

    def test_revoked_consumed_nonce_cannot_restore_fact_by_public_phase(self):
        import terminal_input_challenge as challenge
        with CaseFixture() as f:
            f.initial_protocol(); f.probe.invalidate('INPUT_PROBE_REVOKED')
            f.probe.phase='CONSUMED'
            self.assertFalse(challenge._initial_nonce_completed(f.probe,state=f.state,scope=f.scope,
                native_owner=f.native,transition_owner=f.transition))

    def test_sdk_witness_expires_with_its_own_25_second_budget(self):
        from resume_history_fixtures import NativeFixture
        with CaseFixture() as f:
            f.complete_initial()
            with (f.root/'sdk.stream').open('w+b') as stream:
                import os
                os.chmod(stream.name,0o600); stream.write(sdk_stream(SESSION,f.kind)); stream.flush()
                child=NativeFixture(f.sdk_command)
                launch=self.m.sdk_started(f.case,child=child,command=f.sdk_command,stream=stream)
                child.returncode=0
                now=self.m._now()
                with mock.patch.object(self.m,'_now',return_value=now+26):
                    with self.assertRaises(self.m.ResumeHistoryError): self.m.sdk_finished(launch)

    def test_initial_completion_rejects_out_of_transport_frame_bounds(self):
        with CaseFixture() as f:
            f.initial_protocol()
            with self.assertRaises(self.m.ResumeHistoryError): f.capture(frame=8_388_609)

    def test_view_does_not_extend_raw_snapshot_lifetime(self):
        import gc
        import weakref
        with CaseFixture() as f:
            view=self.bind(f)
            reference=weakref.ref(self.args.pop('snapshot'))
            gc.collect()
            self.assertTrue(reference() is None,'view extended raw fixture snapshot lifetime')
            self.assertEqual(self.m.resume_view_decision(view),'VALID')


class ResumeCompositionTests(unittest.TestCase):
    bind=ResumeCaseTests.bind
    validate=ResumeCaseTests.validate

    def setUp(self):
        self.m=importlib.import_module('terminal_resume_history')
        self.echo=importlib.import_module('terminal_context_echo')
        self.assertTrue(hasattr(self.echo,'_compose_input_assessment'),'composed input assessment missing')

    def begin(self,f,view,baseline):
        return self.echo.begin_context_command(f.scope,f.state,f.native,f.transition,f.policy,baseline,1,
            _resume_view=view,_controller_owner=f.controller)

    def submit(self,f,view,baseline,history):
        command=self.begin(f,view,baseline)
        self.assertEqual(command.type_bytes(baseline,1),b'/context')
        command.check_edit(baseline,1,8)
        echoed=dataclasses.replace(history_snapshot((*history,(37,'❯ /context'))),cursorX=10)
        command.observe(echoed,2)
        self.assertEqual(command.submit_bytes(echoed,2),b'\r')
        command.submission_written(1)
        return command

    def test_history_menu_and_unknown_row_use_one_ordered_assessment(self):
        import terminal_input_challenge as challenge
        with CaseFixture() as f:
            view=self.bind(f); baseline=self.args['snapshot']; command=self.begin(f,view,baseline)
            command.type_bytes(baseline,1); command.check_edit(baseline,1,8)
            menu=((5,'❯ '+TEXT),(8,'❯ /context  Synthetic menu'))
            echoed=dataclasses.replace(history_snapshot((*menu,(37,'❯ /context'))),cursorX=10)
            command.observe(echoed,2)
            bad=dataclasses.replace(history_snapshot((*menu,(37,'❯ /context'),(39,'❯ synthetic unknown'))),cursorX=10)
            with mock.patch.object(f.policy,'_empty_input_assessment',wraps=f.policy._empty_input_assessment) as assess:
                with self.assertRaises(challenge.InputProofError): command.observe(bad,3)
                self.assertEqual(assess.call_count,1)
            self.assertEqual(command.phase,'REVOKED')
            self.assertEqual(self.m.resume_view_decision(view),'REJECTED')
            self.assertIsNone(f.policy.empty_input_anchor(bad))

    def test_debug_keeps_actual_rejection_after_view_revocation(self):
        import terminal_input_challenge as challenge
        with CaseFixture() as f:
            view=self.bind(f); baseline=self.args['snapshot']; command=self.begin(f,view,baseline)
            command.type_bytes(baseline,1); command.check_edit(baseline,1,8)
            menu=((5,'❯ '+TEXT),(8,'❯ /context  Synthetic menu'))
            echoed=dataclasses.replace(history_snapshot((*menu,(37,'❯ /context'))),cursorX=10)
            command.observe(echoed,2)
            bad=dataclasses.replace(history_snapshot((*menu,(37,'❯ /context'),(39,'❯ synthetic unknown'))),cursorX=10)
            normalized=history_snapshot((*menu,(39,'❯ synthetic unknown')))
            assessment,index,observation=self.echo._compose_input_assessment(f.policy,bad,frame=3,state=f.state,
                scope=f.scope,native_owner=f.native,controller_owner=f.controller,transition_owner=f.transition,
                resume_view=view,context_command=command,normalized_snapshot=normalized)
            self.assertEqual((assessment.reason,assessment.rowRelation,assessment.rowCause,index),
                ('UNSUPPORTED_ROW','OTHER_CAPTURED_ROW','UNRECOGNIZED_SHAPE',39))
            error=challenge.InputProofError('INPUT_PROBE_INELIGIBLE',assessment.reason,
                input_row_relation=assessment.rowRelation,input_row_cause=assessment.rowCause)
            self.echo.attach_context_rejection(error,observation)
            self.assertEqual(self.m.resume_view_decision(view),'REJECTED')
            with mock.patch.object(self.m,'validate_resume_view',side_effect=AssertionError('live proof queried')):
                self.assertEqual(self.echo.context_rejection_projection(error,bad,f.policy),(True,39))

    def test_retired_baseline_row_cannot_be_promoted_to_new_history(self):
        with CaseFixture() as f:
            history=((5,'❯ '+TEXT),(10,'❯ /context'),(12,'❯ /exit'))
            baseline=history_snapshot(history); view=self.bind(f,baseline)
            command=self.submit(f,view,baseline,history)
            numeric=history_snapshot(((0,'Context Usage'),(1,'Free space: 81%'),
                (2,'Autocompact buffer: 3%'),(10,'❯ /context'),(12,'❯ /exit'),(20,'❯ /context')))
            receipt=command.bind_history(numeric,3)
            self.assertEqual(self.echo._RECEIPTS[receipt][1],20)
            assessment,_=self.echo.assess_context_input(f.policy,numeric,receipt=receipt,state=f.state,
                scope=f.scope,native_owner=f.native,transition_owner=f.transition,frame=3,
                _resume_view=view,_controller_owner=f.controller)
            self.assertEqual(assessment.reason,'ELIGIBLE')
            restored=history_snapshot(((0,'Context Usage'),(1,'Free space: 81%'),
                (2,'Autocompact buffer: 3%'),*history,(20,'❯ /context')))
            with self.assertRaises(self.m.ResumeHistoryError):
                self.validate(f,view,snapshot=restored,frame=4)
            self.assertEqual(command.phase,'REVOKED')

    def test_retirement_and_exclusion_cannot_refresh_old_numeric_grid(self):
        import terminal_input_challenge as challenge
        with CaseFixture() as f:
            history=((0,'Context Usage'),(1,'Free space: 81%'),(2,'Autocompact buffer: 3%'),(5,'❯ '+TEXT))
            baseline=history_snapshot(history); view=self.bind(f,baseline)
            command=self.submit(f,view,baseline,history)
            unchanged=history_snapshot(history[:3])
            with self.assertRaises(challenge.InputProofError): command.bind_history(unchanged,3)
            self.assertEqual(self.m.resume_view_decision(view),'REJECTED')

    def test_unowned_normalization_cannot_hide_current_draft(self):
        with CaseFixture() as f:
            view=self.bind(f)
            draft=history_snapshot(((5,'❯ '+TEXT),(37,'❯ synthetic draft')))
            with self.assertRaises(self.m.ResumeHistoryError):
                self.echo._compose_input_assessment(f.policy,draft,frame=2,state=f.state,scope=f.scope,
                    native_owner=f.native,controller_owner=f.controller,transition_owner=f.transition,
                    resume_view=view,normalized_snapshot=history_snapshot(((5,'❯ '+TEXT),)))

    def test_current_nonce_echo_clear_and_consumption_keep_same_view(self):
        import terminal_input_challenge as challenge
        for has_receipt in (False,True):
            with self.subTest(receipt=has_receipt), CaseFixture() as f:
                view=self.bind(f); baseline=self.args['snapshot']; history=((5,'❯ '+TEXT),)
                command=self.submit(f,view,baseline,history)
                rows=((0,'Context Usage'),(1,'Free space: 81%'),(2,'Autocompact buffer: 3%'),*history)
                if has_receipt: rows=(*rows,(20,'❯ /context'))
                numeric=history_snapshot(rows); receipt=command.bind_history(numeric,3)
                self.assertEqual(receipt is not None,has_receipt)
                probe=challenge.NonceInputChallenge(f.scope,f.native,f.transition,f.policy,numeric,3,
                    context_receipt=receipt,_resume_view=view,_controller_owner=f.controller)
                marker=probe.type_bytes(numeric,3)
                self.assertEqual(len(marker),16)
                echoed=dataclasses.replace(history_snapshot((*rows,(37,'❯ '+marker.decode()))),cursorX=18)
                self.assertEqual(probe.observe(echoed,4),'ECHO_MATCHED')
                self.assertEqual(probe.clear_bytes(echoed,4),b'\x15')
                self.assertEqual(probe.observe(numeric,5),'PROVEN')
                self.assertTrue(probe.consume_exit(probe.ownership_proof(),numeric,5,f.native,f.transition))
                auth=history_snapshot((*rows,(7,'Do you want to use this API key?')))
                with self.assertRaises(RuntimeError): probe.observe(auth,6)
                self.assertEqual((probe.phase,command.phase),('REVOKED','REVOKED'))
                self.assertIsNone(probe._marker)
                self.assertEqual(self.m.resume_view_decision(view),'REJECTED')

    def test_nonce_without_receipt_keeps_actual_other_row_rejection(self):
        import terminal_input_challenge as challenge
        with CaseFixture() as f:
            view=self.bind(f); baseline=self.args['snapshot']; history=((5,'❯ '+TEXT),)
            command=self.submit(f,view,baseline,history)
            rows=((0,'Context Usage'),(1,'Free space: 81%'),(2,'Autocompact buffer: 3%'),*history)
            numeric=history_snapshot(rows)
            self.assertIsNone(command.bind_history(numeric,3))
            probe=challenge.NonceInputChallenge(f.scope,f.native,f.transition,f.policy,numeric,3,
                _resume_view=view,_controller_owner=f.controller)
            marker=probe.type_bytes(numeric,3)
            actual=dataclasses.replace(history_snapshot((*rows,(37,'❯ '+marker.decode()),
                (39,'❯ synthetic other row'))),cursorX=18)
            with self.assertRaises(challenge.InputProofError) as caught: probe.observe(actual,4)
            self.assertEqual(caught.exception.reason,'INPUT_PROBE_INELIGIBLE')
            self.assertEqual((caught.exception.input_row_relation,caught.exception.input_row_cause),
                ('OTHER_CAPTURED_ROW','UNRECOGNIZED_SHAPE'))
            self.assertEqual(self.echo.context_rejection_projection(caught.exception,actual,f.policy),(True,39))


if __name__ == '__main__':
    unittest.main()
