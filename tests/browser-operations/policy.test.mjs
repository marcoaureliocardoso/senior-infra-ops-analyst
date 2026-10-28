import assert from 'node:assert/strict';
import test from 'node:test';

import { operationFingerprint, parseOperationEnvelope } from '../../skills/browser-operations/scripts/browser-contract.mjs';
import { BROWSER_REASON_CODES, evaluateBrowserCall } from '../../skills/browser-operations/scripts/browser-policy.mjs';
import { bindingFixture, browserEnvelope, capabilityFixture, NOW } from './helpers.mjs';


function inputs(overrides = {}) {
  const envelope = parseOperationEnvelope(browserEnvelope(), NOW);
  return {
    event: {
      sessionId: envelope.sessionId,
      toolUseId: 'tool-browser-001',
      role: 'main',
      permissionMode: 'normal',
    },
    envelope,
    capability: capabilityFixture(),
    binding: bindingFixture({ operationFingerprint: operationFingerprint(envelope) }),
    call: {
      action: 'inspect', effect: 'SENSITIVE_READ',
      destinationOrigin: 'https://router.example.invalid:443', sensitiveInputKeys: [],
    },
    now: NOW + 1,
    ...overrides,
  };
}


test('exports stable browser policy reason codes', () => {
  for (const code of [
    'ALLOW_PUBLIC_READ', 'ALLOW_BOUND_OPERATION', 'ASK_SENSITIVE_READ',
    'ASK_INTERACTIVE_STATE', 'ASK_CHANGE', 'ASK_DESTRUCTIVE',
    'ASK_SENSITIVE_ARTIFACT', 'DENY_UNKNOWN_CAPABILITY',
    'DENY_GUARD_UNPROVEN', 'DENY_OPERATION_MISMATCH',
    'DENY_ORIGIN_ESCAPE', 'DENY_SECRET_DESTINATION', 'DENY_ROLE',
    'DENY_EXPIRED', 'DENY_OUTCOME_UNKNOWN', 'PROMPT_INJECTION_ATTEMPT',
  ]) assert.equal(BROWSER_REASON_CODES.includes(code), true, code);
  assert.equal(Object.isFrozen(BROWSER_REASON_CODES), true);
});


test('effect decisions are identical in normal and bypass modes', () => {
  const matrix = new Map([
    ['PUBLIC_READ', ['allow', 'ALLOW_PUBLIC_READ']],
    ['SENSITIVE_READ', ['ask', 'ASK_SENSITIVE_READ']],
    ['INTERACTIVE_STATE', ['ask', 'ASK_INTERACTIVE_STATE']],
    ['LOW_RISK_CHANGE', ['ask', 'ASK_CHANGE']],
    ['DISRUPTIVE_CHANGE', ['ask', 'ASK_CHANGE']],
    ['DESTRUCTIVE_CHANGE', ['ask', 'ASK_DESTRUCTIVE']],
    ['SENSITIVE_ARTIFACT', ['ask', 'ASK_SENSITIVE_ARTIFACT']],
    ['UNKNOWN', ['deny', 'DENY_UNKNOWN_CAPABILITY']],
  ]);
  for (const permissionMode of ['normal', 'bypassPermissions']) {
    for (const [effect, [decision, reasonCode]] of matrix) {
      const base = inputs();
      const envelope = parseOperationEnvelope(browserEnvelope({
        expectedEffect: effect === 'UNKNOWN' ? 'LOW_RISK_CHANGE' : effect,
        risk: effect === 'DESTRUCTIVE_CHANGE' ? 'DESTRUCTIVE' : 'LOW_RISK_CHANGE',
        artifactPolicy: effect === 'SENSITIVE_ARTIFACT' ? {
          enabled: true, types: ['screenshot'], purposeRef: 'bounded-evidence',
          sourceClasses: ['browser-viewport'], destinationClasses: ['operation-temp'],
          maxItems: 1, maxBytes: 100_000, redaction: 'required', retentionSeconds: 60,
        } : browserEnvelope().artifactPolicy,
      }), NOW);
      const result = evaluateBrowserCall(inputs({
        envelope,
        binding: bindingFixture({ operationFingerprint: operationFingerprint(envelope) }),
        event: { ...base.event, permissionMode },
        call: { ...base.call, effect },
      }));
      assert.equal(result.decision, decision, `${permissionMode}:${effect}`);
      assert.equal(result.reasonCode, reasonCode, `${permissionMode}:${effect}`);
    }
  }
});


test('unknown and inactive capabilities fail closed', () => {
  for (const [state, reasonCode] of [
    ['AVAILABLE_UNRECOGNIZED', 'DENY_UNKNOWN_CAPABILITY'],
    ['UNAVAILABLE', 'DENY_UNKNOWN_CAPABILITY'],
    ['CONFLICT', 'DENY_UNKNOWN_CAPABILITY'],
    ['AVAILABLE_RECOGNIZED', 'DENY_GUARD_UNPROVEN'],
  ]) {
    const result = evaluateBrowserCall(inputs({ capability: capabilityFixture({ state }) }));
    assert.equal(result.decision, 'deny');
    assert.equal(result.reasonCode, reasonCode);
  }
});


test('every changed authorization binding is denied', () => {
  for (const binding of [
    bindingFixture({ active: false }),
    bindingFixture({ operationId: 'other-operation' }),
    bindingFixture({ sessionId: 'other-session' }),
    bindingFixture({ role: 'network-edge-operator' }),
    bindingFixture({ operationFingerprint: 'b'.repeat(64) }),
    bindingFixture({ adapterId: 'other-adapter' }),
    bindingFixture({ routeClass: 'PROTECTED_RUNNER' }),
    bindingFixture({ settingsFingerprint: 'other-settings' }),
    bindingFixture({ permissionModes: ['normal'] }),
  ]) {
    const base = inputs();
    const event = binding.permissionModes.includes('bypassPermissions')
      ? base.event : { ...base.event, permissionMode: 'bypassPermissions' };
    const result = evaluateBrowserCall(inputs({ binding, event }));
    assert.equal(result.decision, 'deny');
    assert.equal(result.reasonCode, 'DENY_OPERATION_MISMATCH');
  }
});


test('expired and outcome-unknown bindings deny before effect evaluation', () => {
  assert.equal(evaluateBrowserCall(inputs({
    binding: bindingFixture({ expiresAt: NOW }),
  })).reasonCode, 'DENY_EXPIRED');
  assert.equal(evaluateBrowserCall(inputs({
    binding: bindingFixture({ outcome: 'OUTCOME_UNKNOWN' }),
  })).reasonCode, 'DENY_OUTCOME_UNKNOWN');
});


test('role and action boundaries cannot be expanded by a call', () => {
  assert.equal(evaluateBrowserCall(inputs({
    event: { ...inputs().event, role: 'change-manager' },
  })).reasonCode, 'DENY_ROLE');
  assert.equal(evaluateBrowserCall(inputs({
    call: { ...inputs().call, action: 'delete-router' },
  })).reasonCode, 'DENY_OPERATION_MISMATCH');

  const auditEnvelope = parseOperationEnvelope(browserEnvelope({
    role: 'audit-evidence-collector', expectedEffect: 'SENSITIVE_READ', risk: 'SAFE_READ_ONLY',
  }), NOW);
  const audit = inputs({
    envelope: auditEnvelope,
    event: { ...inputs().event, role: 'audit-evidence-collector' },
    binding: bindingFixture({
      role: 'audit-evidence-collector', operationFingerprint: operationFingerprint(auditEnvelope),
    }),
    call: { ...inputs().call, action: 'click', effect: 'LOW_RISK_CHANGE' },
  });
  assert.equal(evaluateBrowserCall(audit).reasonCode, 'DENY_ROLE');
});


test('destination origin must remain in the bound service or auth set', () => {
  assert.equal(evaluateBrowserCall(inputs({
    call: { ...inputs().call, destinationOrigin: 'https://other.example.invalid:443' },
  })).reasonCode, 'DENY_ORIGIN_ESCAPE');
  assert.equal(evaluateBrowserCall(inputs({
    call: { ...inputs().call, destinationOrigin: 'https://login.example.invalid:443' },
  })).reasonCode, 'ASK_SENSITIVE_READ');
});


test('credential-bearing fill is limited to bound authentication actions and origins', () => {
  const base = inputs();
  const allowed = evaluateBrowserCall(inputs({
    call: {
      action: 'authenticate', effect: 'INTERACTIVE_STATE',
      destinationOrigin: 'https://login.example.invalid:443', sensitiveInputKeys: ['text'],
    },
  }));
  assert.equal(allowed.reasonCode, 'ASK_INTERACTIVE_STATE');

  for (const call of [
    { action: 'fill', effect: 'INTERACTIVE_STATE', destinationOrigin: 'https://router.example.invalid:443', sensitiveInputKeys: ['text'] },
    { action: 'authenticate', effect: 'INTERACTIVE_STATE', destinationOrigin: 'https://other.example.invalid:443', sensitiveInputKeys: ['text'] },
  ]) {
    const result = evaluateBrowserCall(inputs({ ...base, call }));
    assert.equal(result.decision, 'deny');
    assert.equal(result.reasonCode, 'DENY_SECRET_DESTINATION');
  }
});


test('autosaving form state is never downgraded to a read', () => {
  const result = evaluateBrowserCall(inputs({
    call: {
      action: 'fill', effect: 'INTERACTIVE_STATE', destinationOrigin: null,
      sensitiveInputKeys: [], autosavePossible: true,
    },
  }));
  assert.equal(result.decision, 'ask');
  assert.equal(result.reasonCode, 'ASK_INTERACTIVE_STATE');
});


test('policy output is bounded structural data without tool values', () => {
  const canary = 'DO_NOT_RETAIN_BROWSER_POLICY_CANARY';
  const result = evaluateBrowserCall(inputs({
    call: { ...inputs().call, untrustedValue: canary },
  }));
  assert.deepEqual(Object.keys(result).sort(), [
    'decision', 'effect', 'modifiers', 'operationId', 'reasonCode', 'risk',
  ]);
  assert.doesNotMatch(JSON.stringify(result), new RegExp(canary, 'u'));
});
