import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

import { verifyPermissionRequest } from './browser-permission-verifier.mjs';


const NOW = 1_800_000_000_000;
const RUNNER = path.resolve('skills/browser-operations/scripts/browser-runner.mjs');
const ORIGIN = 'http://127.0.0.1:43111';
const NONCE = 'p004b-run-001';
const ALLOW_SESSION = '11111111-1111-4111-8111-111111111111';
const DENY_SESSION = '22222222-2222-4222-8222-222222222222';
const VERIFIER = fileURLToPath(new URL('./browser-permission-verifier.mjs', import.meta.url));


function token(value) {
  return Buffer.from(JSON.stringify(value), 'utf8').toString('base64url');
}


function quote(value) {
  return `'${value.replaceAll("'", "'\\\"'\\\"'")}'`;
}


function authenticationSteps() {
  return [
    { step: 'navigate', origin: ORIGIN },
    {
      step: 'click', origin: ORIGIN, locatorRole: 'link', locatorName: 'Login',
      effect: 'INTERACTIVE_STATE',
    },
    {
      step: 'fill', origin: ORIGIN, locatorRole: 'textbox', locatorName: 'Password',
      valueRef: 'env:OPS_BROWSER_VALUE_PASSWORD', valueClass: 'credential',
    },
    {
      step: 'click', origin: ORIGIN, locatorRole: 'button', locatorName: 'Continue',
      effect: 'INTERACTIVE_STATE',
    },
    {
      step: 'fill', origin: ORIGIN, locatorRole: 'textbox', locatorName: 'Code',
      valueRef: 'env:OPS_BROWSER_VALUE_TOTP', valueClass: 'credential',
    },
    {
      step: 'click', origin: ORIGIN, locatorRole: 'button', locatorName: 'Verify',
      effect: 'INTERACTIVE_STATE',
    },
  ];
}


function workflowCommand(phase, overrides = {}) {
  const allow = phase === 'allow';
  const sessionId = overrides.sessionId ?? (allow ? ALLOW_SESSION : DENY_SESSION);
  const operationId = overrides.operationId ?? (allow ? 'p004b-allow-operation' : 'p004b-deny-operation');
  const origin = overrides.origin ?? ORIGIN;
  const authentication = authenticationSteps().map((step) => ({ ...step, origin }));
  const execution = allow ? [...authentication, {
    step: 'select', origin, locatorRole: 'combobox', locatorName: 'WAN enabled',
    valueRef: overrides.valueRef ?? 'env:OPS_BROWSER_VALUE_DISABLED', valueClass: 'configuration',
  }, {
    step: 'click', origin, locatorRole: 'button', locatorName: 'Save',
    effect: 'LOW_RISK_CHANGE',
  }] : [...authentication, {
    step: 'click', origin, locatorRole: 'button', locatorName: 'Rollback',
    effect: 'LOW_RISK_CHANGE',
  }];
  const validation = [...authentication, {
    step: 'inspect', origin, locatorRole: 'status', locatorName: 'Saved state',
    predicate: 'text-equals',
    expectedRef: overrides.expectedRef ?? (allow
      ? 'env:OPS_BROWSER_VALUE_EXPECTED_FALSE'
      : 'env:OPS_BROWSER_VALUE_EXPECTED_TRUE'),
    expectRef: 'interface-state',
  }];
  const actions = allow
    ? ['navigate', 'fill', 'select', 'click', 'inspect']
    : ['navigate', 'fill', 'click', 'inspect'];
  const args = [
    '--step', 'workflow', '--operation-id', operationId,
    '--session-id', sessionId, '--role', overrides.role ?? 'network-edge-operator',
    '--objective-ref', overrides.nonce ?? NONCE, '--target', overrides.target ?? 'loopback-router',
    '--environment', overrides.environment ?? 'test', '--service-origin', origin, '--auth-origin', origin,
    '--identity-ref', overrides.identityRef ?? 'vault:network-admin',
    '--credential-transport', overrides.transport ?? 'vault',
    '--permission-mode', 'normal',
    ...(overrides.actions ?? actions).flatMap((action) => ['--action', action]),
    '--effect', overrides.effect ?? 'LOW_RISK_CHANGE', '--risk', 'LOW_RISK_CHANGE',
    '--precondition-ref', 'fixture-ready', '--validation-ref', 'interface-state',
    '--compensation-ref', 'fixture-rollback', '--expires-in-seconds', overrides.expiry ?? '600',
    ...(overrides.execution ?? execution).flatMap((step) => ['--workflow-step', token(step)]),
    ...(overrides.validation ?? validation).flatMap((step) => ['--validation-step', token(step)]),
  ];
  const runner = overrides.runner ?? RUNNER;
  return `node ${quote(runner.replaceAll('\\', '/'))} ${args.map(quote).join(' ')}`;
}


function expected(phase, overrides = {}) {
  return {
    phase,
    decision: phase,
    runnerPath: overrides.runnerPath ?? RUNNER,
    operationId: overrides.operationId ?? (phase === 'allow'
      ? 'p004b-allow-operation'
      : 'p004b-deny-operation'),
    sessionId: overrides.sessionId ?? (phase === 'allow' ? ALLOW_SESSION : DENY_SESSION),
    runNonce: overrides.runNonce ?? NONCE,
    origin: overrides.origin ?? ORIGIN,
  };
}


function request(phase, overrides = {}) {
  return {
    tool_name: overrides.toolName ?? 'Bash',
    input: overrides.input ?? { command: workflowCommand(phase, overrides) },
  };
}


test('allow phase accepts only the exact synthetic change workflow', () => {
  const result = verifyPermissionRequest(request('allow'), expected('allow'), NOW);
  assert.deepEqual({
    verified: result.verified,
    reasonCode: result.reasonCode,
    phase: result.phase,
    decision: result.decision,
    operationId: result.operationId,
    expectedEffect: result.expectedEffect,
    executionSteps: result.executionSteps,
    validationSteps: result.validationSteps,
  }, {
    verified: true,
    reasonCode: 'P004B_PERMISSION_EXACT',
    phase: 'allow',
    decision: 'allow',
    operationId: 'p004b-allow-operation',
    expectedEffect: 'LOW_RISK_CHANGE',
    executionSteps: 8,
    validationSteps: 7,
  });
  assert.match(result.invocationFingerprint, /^[0-9a-f]{64}$/u);
  assert.equal(Object.isFrozen(result), true);
});


test('deny phase accepts only the exact synthetic rollback request', () => {
  const result = verifyPermissionRequest(request('deny'), expected('deny'), NOW);
  assert.equal(result.verified, true);
  assert.equal(result.phase, 'deny');
  assert.equal(result.decision, 'deny');
  assert.equal(result.operationId, 'p004b-deny-operation');
  assert.equal(result.executionSteps, 7);
  assert.equal(result.validationSteps, 7);
  assert.match(result.invocationFingerprint, /^[0-9a-f]{64}$/u);
});


test('all mismatches return one content-free closed record', () => {
  const cases = [
    [request('allow', { toolName: 'Read' }), 'allow'],
    [request('allow', { input: { command: workflowCommand('allow'), extra: true } }), 'allow'],
    [request('allow', { input: { command: `${workflowCommand('allow')} | tee output` } }), 'allow'],
    [request('allow', { input: { command: `${workflowCommand('allow')} > output` } }), 'allow'],
    [request('allow', { input: { command: `${workflowCommand('allow')}\nprintf nope` } }), 'allow'],
    [request('allow', { input: { command: `VALUE=x ${workflowCommand('allow')}` } }), 'allow'],
    [request('allow', { input: { command: workflowCommand('allow').replace(/^node/u, 'env node') } }), 'allow'],
    [request('allow', { runner: `${RUNNER}.other` }), 'allow'],
    [request('allow', { operationId: 'p004b-other-operation' }), 'allow'],
    [request('allow', { sessionId: DENY_SESSION }), 'allow'],
    [request('allow', { nonce: 'p004b-other-run' }), 'allow'],
    [request('allow', { origin: 'http://127.0.0.1:43112' }), 'allow'],
    [request('allow', { role: 'diagnostic-operator' }), 'allow'],
    [request('allow', { target: 'other-router' }), 'allow'],
    [request('allow', { environment: 'production' }), 'allow'],
    [request('allow', { identityRef: 'vault:other-admin' }), 'allow'],
    [request('allow', { transport: 'profile', identityRef: 'profile:other-admin' }), 'allow'],
    [request('allow', { effect: 'DISRUPTIVE_CHANGE' }), 'allow'],
    [request('allow', { actions: ['navigate', 'fill', 'click', 'inspect'] }), 'allow'],
    [request('allow', { valueRef: 'env:OPS_BROWSER_VALUE_ENABLED' }), 'allow'],
    [request('allow', { expectedRef: 'env:OPS_BROWSER_VALUE_EXPECTED_TRUE' }), 'allow'],
    [request('allow', { expiry: '601' }), 'allow'],
    [request('allow', { execution: [...authenticationSteps()].reverse() }), 'allow'],
    [request('allow', { validation: [...authenticationSteps(), {
      step: 'inspect', origin: ORIGIN, locatorRole: 'status', locatorName: 'Saved state',
      predicate: 'text-equals', expectedRef: 'env:OPS_BROWSER_VALUE_EXPECTED_TRUE',
      expectRef: 'interface-state',
    }] }), 'allow'],
    [request('deny', { input: { command: workflowCommand('allow') } }), 'deny'],
  ];
  for (const [value, phase] of cases) {
    assert.deepEqual(verifyPermissionRequest(value, expected(phase), NOW), {
      verified: false,
      reasonCode: 'P004B_PERMISSION_MISMATCH',
      phase: null,
      decision: null,
      invocationFingerprint: null,
      operationId: null,
      expectedEffect: null,
      executionSteps: 0,
      validationSteps: 0,
    });
  }
});


test('invalid expectations and clocks fail closed without throwing', () => {
  assert.equal(verifyPermissionRequest(request('allow'), { ...expected('allow'), phase: 'other' }, NOW).verified, false);
  assert.equal(verifyPermissionRequest(request('allow'), expected('allow'), -1).verified, false);
  assert.equal(verifyPermissionRequest(null, expected('allow'), NOW).verified, false);
});


test('CLI emits exactly one structural JSON line', () => {
  const input = JSON.stringify(request('allow'));
  const result = spawnSync(process.execPath, [
    VERIFIER, 'allow', RUNNER, 'p004b-allow-operation', ALLOW_SESSION,
    NONCE, ORIGIN, 'allow',
  ], { input, encoding: 'utf8' });
  assert.equal(result.status, 0, result.stderr);
  assert.equal(result.stderr, '');
  assert.equal(result.stdout.split('\n').filter(Boolean).length, 1);
  assert.equal(JSON.parse(result.stdout).verified, true);
});
