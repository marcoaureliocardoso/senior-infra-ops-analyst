import assert from 'node:assert/strict';
import test from 'node:test';

import { parseHookEvent } from '../../skills/command-driven-operations/scripts/command-guard/contract.mjs';
import { analyzeCommand } from '../../skills/command-driven-operations/scripts/command-guard/policy.mjs';
import { redactText } from '../../skills/command-driven-operations/scripts/command-guard/redaction.mjs';
import { createFixtureLedger } from './fixture-ledger.mjs';
import { validEvent } from './helpers.mjs';
import { REVIEW_REGRESSION_FIXTURES } from './review-regression-fixtures.mjs';

function analyze(fixture) {
  return analyzeCommand(parseHookEvent(JSON.stringify(validEvent({
    permission_mode: fixture.permissionMode ?? 'bypassPermissions',
    ...(fixture.cwd ? { cwd: fixture.cwd } : {}),
    tool_input: { command: fixture.command },
  }))), fixture.policyEnv ?? {});
}

test('every independent-review regression fixture executes its assertions', () => {
  const ledger = createFixtureLedger(REVIEW_REGRESSION_FIXTURES.map(({ id }) => id));
  for (const fixture of REVIEW_REGRESSION_FIXTURES) {
    const result = analyze(fixture);
    assert.equal(result.decision, fixture.expectedDecision, fixture.id);
    if (fixture.expectedReasonCode) assert.equal(result.reasonCode, fixture.expectedReasonCode, fixture.id);
    if (fixture.expectedRisk) assert.equal(result.risk, fixture.expectedRisk, fixture.id);
    if (fixture.expectedEnvironment) assert.equal(result.environment, fixture.expectedEnvironment, fixture.id);
    if (fixture.expectedTarget) assert.equal(result.target, fixture.expectedTarget, fixture.id);
    if (fixture.expectedCredentialBinding) assert.deepEqual(result.credentialBinding, fixture.expectedCredentialBinding, fixture.id);
    if (fixture.expectedCredentialTransport) assert.equal(result.credential?.transport, fixture.expectedCredentialTransport, fixture.id);
    if (fixture.expectedModifiers) assert.deepEqual(result.modifiers.toSorted(), fixture.expectedModifiers.toSorted(), fixture.id);
    if (fixture.forbiddenText) {
      assert.doesNotMatch(JSON.stringify(result), new RegExp(fixture.forbiddenText, 'u'), fixture.id);
    }
    if (fixture.redactionForbiddenText) {
      assert.doesNotMatch(redactText(fixture.command), new RegExp(fixture.redactionForbiddenText, 'u'), fixture.id);
    }
    ledger.record(fixture.id);
  }
  assert.equal(ledger.assertComplete(), true);
});

test('fixture ledger rejects missing, undeclared, duplicate declarations and duplicate executions', () => {
  assert.throws(() => createFixtureLedger(['A', 'A']), /fixture-declared-twice:A/u);
  const missing = createFixtureLedger(['A']);
  assert.throws(() => missing.assertComplete(), /fixture-not-executed:A/u);
  assert.throws(() => missing.record('B'), /fixture-not-declared:B/u);
  missing.record('A');
  assert.throws(() => missing.record('A'), /fixture-executed-twice:A/u);
  assert.equal(missing.assertComplete(), true);
});
