import assert from 'node:assert/strict';
import test from 'node:test';

import {
  CAPABILITY_STATES,
  EFFECT_CLASSES,
  ROUTE_CLASSES,
  normalizeOrigin,
  operationFingerprint,
  parseOperationEnvelope,
} from '../../skills/browser-operations/scripts/browser-contract.mjs';


const NOW = Date.parse('2026-08-31T12:00:00Z');


function validEnvelope(overrides = {}) {
  return {
    version: 1,
    operationId: 'op-20260831-001',
    sessionId: 'session-001',
    role: 'network-edge-operator',
    objectiveRef: 'change-42-router-description',
    target: 'edge-router-1',
    environment: 'production',
    serviceOrigins: ['HTTPS://Router.Example.Invalid/status?view=all#top'],
    authOrigins: ['https://login.example.invalid/auth'],
    identityRef: 'vault:network-admin',
    credentialTransport: 'vault',
    permissionModeAtApproval: 'normal',
    actions: ['inspect-status', 'update-interface-description'],
    expectedEffect: 'LOW_RISK_CHANGE',
    risk: 'LOW_RISK_CHANGE',
    modifiers: ['PRIVILEGED'],
    preconditionRef: 'interface-exists',
    validationRef: 'interface-description-and-link-state',
    compensationRef: 'restore-interface-description',
    artifactPolicy: {
      enabled: false,
      types: [],
      purposeRef: 'none',
      sourceClasses: [],
      destinationClasses: [],
      maxItems: 0,
      maxBytes: 0,
      redaction: 'none',
      retentionSeconds: 0,
    },
    expiresAt: NOW + 600_000,
    ...overrides,
  };
}


test('accepts the main session as an operation role', () => {
  assert.equal(parseOperationEnvelope(validEnvelope({ role: 'main' }), NOW).role, 'main');
});


function expectCode(code, operation) {
  assert.throws(operation, (error) => {
    assert.equal(error?.code, code);
    assert.equal(error?.message, code);
    return true;
  });
}


test('exports the complete immutable browser taxonomies', () => {
  assert.deepEqual(CAPABILITY_STATES, [
    'AVAILABLE_RECOGNIZED', 'AVAILABLE_UNRECOGNIZED', 'UNAVAILABLE',
    'CONFLICT', 'ACTIVE',
  ]);
  assert.deepEqual(EFFECT_CLASSES, [
    'PUBLIC_READ', 'SENSITIVE_READ', 'INTERACTIVE_STATE',
    'LOW_RISK_CHANGE', 'DISRUPTIVE_CHANGE', 'DESTRUCTIVE_CHANGE',
    'SENSITIVE_ARTIFACT', 'UNKNOWN',
  ]);
  assert.deepEqual(ROUTE_CLASSES, [
    'TYPED_API_MCP', 'NATIVE_BROWSER', 'CONTROLLED_BROWSER_MCP',
    'PROTECTED_RUNNER', 'PUBLIC_FETCH', 'COMPUTER_USE',
  ]);
  assert.equal(Object.isFrozen(CAPABILITY_STATES), true);
  assert.equal(Object.isFrozen(EFFECT_CLASSES), true);
  assert.equal(Object.isFrozen(ROUTE_CLASSES), true);
});


test('normalizes HTTP origins to explicit effective ports', () => {
  assert.equal(
    normalizeOrigin('HTTPS://Router.Example.Invalid/status?view=all#top'),
    'https://router.example.invalid:443',
  );
  assert.equal(normalizeOrigin('http://EXAMPLE.invalid:8080/path'), 'http://example.invalid:8080');
  assert.equal(normalizeOrigin('http://127.0.0.1/'), 'http://127.0.0.1:80');
  assert.equal(normalizeOrigin('https://[::1]/login'), 'https://[::1]:443');
});


test('rejects ambiguous or credential-bearing origins', () => {
  for (const [value, code] of [
    ['ftp://router.example.invalid', 'INVALID_ORIGIN_SCHEME'],
    ['https://user:pass@router.example.invalid', 'ORIGIN_CREDENTIALS_FORBIDDEN'],
    ['https://*.example.invalid', 'ORIGIN_WILDCARD_FORBIDDEN'],
    ['https://münich.example.invalid', 'ORIGIN_IDN_FORBIDDEN'],
    ['https://xn--mnich-kva.example.invalid', 'ORIGIN_IDN_FORBIDDEN'],
    ['not a url', 'INVALID_ORIGIN'],
  ]) {
    expectCode(code, () => normalizeOrigin(value));
  }
});


test('parses and freezes one complete version-one envelope', () => {
  const parsed = parseOperationEnvelope(validEnvelope(), NOW);
  assert.equal(Object.isFrozen(parsed), true);
  assert.equal(Object.isFrozen(parsed.serviceOrigins), true);
  assert.equal(Object.isFrozen(parsed.artifactPolicy), true);
  assert.deepEqual(parsed.serviceOrigins, ['https://router.example.invalid:443']);
  assert.deepEqual(parsed.authOrigins, ['https://login.example.invalid:443']);
  assert.deepEqual(parsed.actions, ['inspect-status', 'update-interface-description']);
  assert.equal(parsed.expiresAt, NOW + 600_000);
});


test('accepts only protected credential references and transports', () => {
  for (const [identityRef, credentialTransport] of [
    ['profile:router-admin', 'profile'],
    ['vault:network-admin', 'vault'],
    ['keychain:router-admin', 'keychain'],
    ['helper:network-admin', 'helper'],
    ['secret-manager:network-admin', 'secret-manager'],
    ['fd:3', 'fd'],
    ['direct-protected-reference:router-admin', 'direct-protected-reference'],
    ['operator-provided-protected-channel:current', 'operator-provided-protected-channel'],
  ]) {
    const parsed = parseOperationEnvelope(validEnvelope({ identityRef, credentialTransport }), NOW);
    assert.equal(parsed.identityRef, identityRef);
    assert.equal(parsed.credentialTransport, credentialTransport);
  }
  expectCode('CREDENTIAL_REFERENCE_REQUIRED', () => parseOperationEnvelope(
    validEnvelope({ identityRef: 'router-admin', credentialTransport: 'literal' }), NOW,
  ));
});


test('rejects unknown, secret-bearing, missing, and expired envelope fields', () => {
  expectCode('INVALID_ENVELOPE_FIELD', () => parseOperationEnvelope({
    ...validEnvelope(), password: 'DO_NOT_ECHO_THIS_VALUE',
  }, NOW));
  expectCode('INVALID_ARTIFACT_FIELD', () => parseOperationEnvelope(validEnvelope({
    artifactPolicy: { ...validEnvelope().artifactPolicy, rawPage: true },
  }), NOW));
  const missing = validEnvelope();
  delete missing.validationRef;
  expectCode('MISSING_ENVELOPE_FIELD', () => parseOperationEnvelope(missing, NOW));
  expectCode('ENVELOPE_EXPIRED', () => parseOperationEnvelope(validEnvelope({ expiresAt: NOW }), NOW));
});


test('rejects duplicates, unbounded values, and invalid taxonomy members', () => {
  expectCode('DUPLICATE_ORIGIN', () => parseOperationEnvelope(validEnvelope({
    serviceOrigins: ['https://router.example.invalid', 'https://ROUTER.example.invalid/path'],
  }), NOW));
  expectCode('DUPLICATE_ACTION', () => parseOperationEnvelope(validEnvelope({
    actions: ['inspect-status', 'inspect-status'],
  }), NOW));
  expectCode('INVALID_BOUNDED_STRING', () => parseOperationEnvelope(validEnvelope({
    objectiveRef: 'x'.repeat(257),
  }), NOW));
  expectCode('INVALID_EFFECT', () => parseOperationEnvelope(validEnvelope({
    expectedEffect: 'STATE_CHANGING',
  }), NOW));
  expectCode('INVALID_RISK', () => parseOperationEnvelope(validEnvelope({
    risk: 'UNKNOWN',
  }), NOW));
});


test('requires disabled artifacts to carry zero-retention defaults', () => {
  expectCode('INVALID_DISABLED_ARTIFACT_POLICY', () => parseOperationEnvelope(validEnvelope({
    artifactPolicy: { ...validEnvelope().artifactPolicy, maxItems: 1 },
  }), NOW));
  const enabled = parseOperationEnvelope(validEnvelope({
    expectedEffect: 'SENSITIVE_ARTIFACT',
    risk: 'SAFE_READ_ONLY',
    modifiers: ['SENSITIVE_OUTPUT'],
    artifactPolicy: {
      enabled: true,
      types: ['screenshot'],
      purposeRef: 'interface-state-evidence',
      sourceClasses: ['browser-viewport'],
      destinationClasses: ['operation-temp'],
      maxItems: 1,
      maxBytes: 1_000_000,
      redaction: 'required',
      retentionSeconds: 300,
    },
  }), NOW);
  assert.equal(enabled.artifactPolicy.enabled, true);
});


test('fingerprints canonical non-secret authorization bindings', () => {
  const first = parseOperationEnvelope(validEnvelope(), NOW);
  const same = parseOperationEnvelope({
    ...validEnvelope(),
    serviceOrigins: ['https://router.example.invalid:443/another/path'],
  }, NOW);
  const changed = parseOperationEnvelope(validEnvelope({ target: 'edge-router-2' }), NOW);
  assert.match(operationFingerprint(first), /^[a-f0-9]{64}$/u);
  assert.equal(operationFingerprint(first), operationFingerprint(same));
  assert.notEqual(operationFingerprint(first), operationFingerprint(changed));
});


test('coded errors never echo rejected input', () => {
  const canary = 'DO_NOT_ECHO_BROWSER_SECRET_CANARY';
  try {
    parseOperationEnvelope(validEnvelope({ objectiveRef: canary.repeat(20) }), NOW);
    assert.fail('expected bounded-string rejection');
  } catch (error) {
    assert.equal(error.code, 'INVALID_BOUNDED_STRING');
    assert.doesNotMatch(`${error.message}\n${error.stack}`, new RegExp(canary, 'u'));
  }
});
