"""Closed structural observation summaries; no native/provider IO."""
import copy
import json
import unittest
import terminal_post_enter_observation as observation
from post_enter_observation_fixtures import ObservationCase
import terminal_resume_history as history


class ObservationSummaryTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(callable(getattr(observation,'valid_observation_summary',None)),
            'closed observation summary validator is absent')

    def test_summary_rejects_unknown_keys_enums_and_wrong_types(self):
        valid={'outcome':'UNSUPPORTED_TRANSITION','stopCategory':'UNKNOWN_ROW','profileObserved':False}
        self.assertTrue(observation.valid_observation_summary(valid))
        for fields in ({'raw':'Synthetic contents'},{'menuState':'new text'},
                {'profileObserved':0},{'outcome':'arbitrary'},{'stopCategory':True},
                {'profileObserved':True}):
            with self.subTest(fields=fields):
                self.assertFalse(observation.valid_observation_summary({**valid,**fields}))

    def test_only_completed_closed_summary_can_be_taken_once(self):
        with ObservationCase() as c:
            c.submit(); self.assertIsNone(history.take_post_enter_result(c.request))
            frame=c.snapshot(commit=20); c.observer.observe(frame,3); c.observer.complete(frame,3)
            c.observer.close(); result=history.take_post_enter_result(c.request)
            self.assertTrue(observation.valid_observation_summary(result))
            result['outcome']='Injected value'
            self.assertEqual(c.observer.summary()['outcome'],'CURRENT_PROFILE_OBSERVED')
            self.assertIsNone(history.take_post_enter_result(c.request))
            rendered=json.dumps(c.observer.summary())
            for forbidden in ('/context','Synthetic','snapshot','deadline','scope','row'):
                self.assertNotIn(forbidden,rendered)
            self.assertEqual(set(observation._OBSERVATIONS[c.observer]),{'phase','closed','summary'})

    def test_positive_summary_requires_complete_coherent_profile(self):
        valid={'outcome':'CURRENT_PROFILE_OBSERVED','stopCategory':'COMPLETE','profileObserved':True,
            'menuState':'DISAPPEARED','inputState':'EMPTY','commitRelation':'NEW_CELL',
            'numericRelation':'BASELINE_EQUIVALENT'}
        self.assertTrue(observation.valid_observation_summary(valid))
        for key,value in (('stopCategory','AUTHENTICATION'),('menuState','EXACT_PRESENT'),
                ('inputState','OWNED_COMMAND_ECHO'),('commitRelation','PREENTER_INVENTORY'),
                ('numericRelation','CONFLICT')):
            with self.subTest(key=key):
                self.assertFalse(observation.valid_observation_summary({**valid,key:value}))
        self.assertFalse(observation.valid_observation_summary({key:value for key,value in valid.items() if key!='inputState'}))

    def test_stop_cannot_fabricate_positive_result_or_restore_failure(self):
        with ObservationCase() as c:
            c.submit()
            with self.assertRaises(RuntimeError): c.observer.stop('CURRENT_PROFILE_OBSERVED','COMPLETE')
            c.observer.stop('DEADLINE','DEADLINE'); original=c.observer.summary()
            c.observer.stop('SAFETY_STOP','OWNER_LOST')
            self.assertEqual(c.observer.summary(),original)


if __name__=='__main__': unittest.main()
