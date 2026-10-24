#!/usr/bin/env python3
"""Closed, content-free main-stage evidence; no native processes."""
import copy
import unittest

from browser_context_contract import (
    STAGES, finish_stage, offline_usage, project_api_usage, project_context,
    public_main, stage_policy, validate_main,
)


def observation(total=100, usage=None):
    return {"context": {"totalTokens": total, "maxTokens": 10000,
            "rawMaxTokens": 10000, "percentage": 1, "autoCompactEnabled": True,
            "categoryCount": 0}, "apiUsage": {"state": "NULL", "values": None}
            if usage is None else project_api_usage({"apiUsage": usage})}


def usage(value=1250):
    return dict(input_tokens=value, output_tokens=10,
                cache_creation_input_tokens=0, cache_read_input_tokens=0)


def witness(stage="skill"):
    return dict(latestResponseUsage=usage(), sessionBound=True, policyFixed=True,
                historyLinked="NOT_REQUIRED" if stage == "skill" else "OBSERVED",
                measurementHook="OBSERVED" if stage == "subagent" else "NOT_REQUIRED",
                claimVerified=True, actionCalls=1, toolResultsComplete=True,
                toolSearchAvailable=True, unexpectedCalls=0, fault="NONE")


def report():
    return dict(schema="MAIN_STAGE_CONTEXT_V2", schemaVersion=2, runNonce="run-001",
                sessionId="native-001", stages=[finish_stage(s, observation(),
                    observation(99, usage()), witness(s)) for s in STAGES],
                outcome="MAIN_STAGE_QUALIFIED", reason="NONE", cleanupVerified=True)


class ContractTests(unittest.TestCase):
    def test_usage_presence_and_safe_numeric_projection(self):
        self.assertEqual(project_api_usage({}), {"state": "ABSENT", "values": None})
        self.assertEqual(project_api_usage({"apiUsage": None}), {"state": "NULL", "values": None})
        self.assertEqual(project_api_usage({"apiUsage": {**usage(), "secret": "drop"}}),
                         {"state": "VALID", "values": usage()})
        for bad in (True, -1, 2**53, 1.5, float("nan")):
            self.assertEqual(project_api_usage({"apiUsage": usage(bad)})["state"], "INVALID")
        raw = dict(totalTokens=100, maxTokens=10000, rawMaxTokens=10000,
                   percentage=1, isAutoCompactEnabled=True, categories=[{"name": "private"}])
        self.assertEqual(project_context(raw), {**observation()["context"], "categoryCount": 1})
        for key, bad in (("percentage", float("nan")), ("maxTokens", 0),
                         ("totalTokens", True), ("categories", [0]*4097)):
            with self.assertRaises(ValueError):
                project_context({**raw, key: bad})

    def test_zero_negative_delta_and_equal_percentage_can_qualify(self):
        for total in (100, 99):
            result = finish_stage("skill", observation(), observation(total, usage()), witness())
            self.assertEqual(result["outcome"], "QUALIFIED")
            self.assertEqual(result["deltaTokens"], total-100)

    def test_replayed_cumulative_or_nested_usage_cannot_qualify(self):
        for latest in (None, usage(9999)):
            self.assertEqual(finish_stage("skill", observation(), observation(101, usage()),
                {**witness(), "latestResponseUsage": latest})["reason"], "USAGE_PROVENANCE_UNPROVEN")
        self.assertEqual(finish_stage("skill", observation(100, usage()),
            observation(101, usage()), witness())["reason"], "USAGE_PROVENANCE_UNPROVEN")

    def test_denominator_drift_is_non_comparable(self):
        after = observation(99, usage()); after["context"]["rawMaxTokens"] = 9999
        result = finish_stage("skill", observation(), after, witness())
        self.assertEqual((result["reason"], result["deltaTokens"]), ("NON_COMPARABLE", None))

    def test_exact_schema_order_and_cleanup_are_required(self):
        valid = report()
        self.assertEqual(validate_main(valid, "run-001", "native-001"), valid)
        for mutate in (lambda x: x.update(extra="content"), lambda x: x.update(cleanupVerified=False),
                       lambda x: x["stages"].reverse(), lambda x: x.update(schemaVersion=True),
                       lambda x: x["stages"][0].update(deltaTokens=5),
                       lambda x: x["stages"][0]["witness"].update(secret="no")):
            bad=copy.deepcopy(valid); mutate(bad)
            with self.assertRaises(ValueError): validate_main(bad, "run-001", "native-001")
        with self.assertRaises(ValueError): validate_main(valid, "other", "native-001")
        public=public_main(valid)
        self.assertNotIn("runNonce", public); self.assertNotIn("sessionId", public)

    def test_partial_failure_contains_no_invented_samples(self):
        stage=finish_stage("skill", None, None, {**witness(), "fault": "OPERATION_TIMEOUT"})
        self.assertIsNone(stage["before"]); self.assertIsNone(stage["deltaTokens"])
        value={**report(), "stages": [stage], "outcome": "INCONCLUSIVE", "reason": "OPERATION_TIMEOUT"}
        self.assertEqual(validate_main(value, "run-001", "native-001"), value)

    def test_stage_policy_preserves_existing_prompts_and_inputs(self):
        import browser_operations_live as legacy
        for stage in STAGES:
            p=stage_policy(stage, "run-001")
            self.assertEqual(p["stage"], stage)
            self.assertEqual(p["input"], {"skill": "context-continuity"} if stage=="skill" else
                {"description":"P004B_SUBAGENT_ACK","prompt":"P004B_SUBAGENT_ACK","subagent_type":"diagnostic-operator"}
                if stage=="subagent" else {"query":"select:mcp__p004b-context__context_fixture_ping"}
                if stage=="discovery" else {"nonce":"run-001"})
            self.assertTrue(p["prompt"])

    def test_offline_usage_uses_reported_window(self):
        self.assertEqual(offline_usage(observation(), 1), usage(1251))
        for before, ordinal in ((observation(100, usage(1251)), 1), (observation(), 41)):
            with self.assertRaisesRegex(ValueError, "CHALLENGE_UNAVAILABLE"): offline_usage(before, ordinal)
        small=observation(); small["context"].update(maxTokens=20, rawMaxTokens=20)
        with self.assertRaisesRegex(ValueError,"CHALLENGE_UNAVAILABLE"): offline_usage(small,1)

    def test_main_v2_cannot_pass_full_role_validator(self):
        import browser_operations_live as legacy
        with self.assertRaises(ValueError): legacy.validate_trusted_measurement(report(), "run-001", {"native-001"})

    def test_invalid_closed_enums_and_delta_types_raise_value_error(self):
        for change in (lambda x:x.update(reason=[]),
                       lambda x:x["stages"][0]["witness"].update(fault={}),
                       lambda x:x["stages"][0].update(deltaTokens=-1.0)):
            bad=report();change(bad)
            with self.assertRaises(ValueError):validate_main(bad,"run-001","native-001")
        with self.assertRaises(ValueError):public_main(None)

    def test_private_reader_rejects_duplicate_symlink_and_permissions(self):
        import json,os,tempfile
        from pathlib import Path
        from browser_context_contract import load_private
        if os.name!="posix":self.skipTest("POSIX private evidence")
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"report.json";path.write_text(json.dumps(report()));path.chmod(0o600)
            self.assertEqual(load_private(path,"run-001","native-001"),report())
            path.chmod(0o644)
            with self.assertRaises(ValueError):load_private(path,"run-001","native-001")
            path.chmod(0o600);link=Path(d)/"link";link.symlink_to(path)
            with self.assertRaises((ValueError,OSError)):load_private(link,"run-001","native-001")
            path.write_text('{"schema":1,"schema":2}')
            with self.assertRaises(ValueError):load_private(path,"run-001","native-001")


if __name__ == "__main__": unittest.main()
