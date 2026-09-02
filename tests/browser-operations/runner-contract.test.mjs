import assert from 'node:assert/strict';
import { mkdtemp, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import {
  authorizeRunnerStep, executeRunnerStep, parseRunnerArgs,
} from '../../skills/browser-operations/scripts/browser-runner.mjs';
import {
  activateOperation, readActiveOperation,
} from '../../skills/browser-operations/scripts/browser-binding-store.mjs';
import { NOW, capabilityFixture } from './helpers.mjs';
import { evaluateApprovalHook } from '../../skills/command-driven-operations/scripts/record-command-approval.mjs';
import { evaluateHook } from '../../skills/command-driven-operations/scripts/validate-ops-command.mjs';


const OPEN = [
  '--step', 'open', '--operation-id', 'op-runner-001',
  '--session-id', 'session-runner-001', '--role', 'network-edge-operator',
  '--objective-ref', 'change-42', '--target', 'edge-router-1',
  '--environment', 'production', '--service-origin', 'https://router.example.invalid',
  '--auth-origin', 'https://login.example.invalid', '--identity-ref', 'vault:network-admin',
  '--credential-transport', 'vault', '--permission-mode', 'normal',
  '--action', 'inspect', '--action', 'fill', '--action', 'click', '--action', 'validate', '--action', 'close',
  '--effect', 'LOW_RISK_CHANGE', '--risk', 'LOW_RISK_CHANGE',
  '--precondition-ref', 'router-reachable', '--validation-ref', 'interface-state',
  '--compensation-ref', 'restore-interface', '--expires-in-seconds', '600',
];
const RUNNER_PATH = path.resolve('skills/browser-operations/scripts/browser-runner.mjs');


function replaceFlag(argv, flag, value) {
  const copy = [...argv];
  copy[copy.indexOf(flag) + 1] = value;
  return copy;
}


async function stateFixture(run) {
  const directory = await mkdtemp(path.join(os.tmpdir(), 'browser-runner-'));
  const env = {
    ...process.env,
    OPS_BROWSER_STATE_DIR: directory,
    OPS_COMMAND_GUARD_STATE_DIR: path.join(directory, 'command-guard'),
    OPS_COMMAND_GUARD_AUDIT_PATH: path.join(directory, 'command-guard', 'audit.jsonl'),
  };
  try {
    await run(env);
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
}


function proof() {
  return {
    toolUseId: 'tool-runner-open-001', adapterId: 'protected-runner',
    routeClass: 'PROTECTED_RUNNER', settingsFingerprint: 'browser-runner-v1',
    permissionModes: ['normal', 'bypassPermissions'],
    capability: capabilityFixture({
      adapterId: 'protected-runner', routeClass: 'PROTECTED_RUNNER',
      settingsFingerprint: 'browser-runner-v1', descriptorId: 'protected-runner-v1',
      effects: ['PUBLIC_READ', 'SENSITIVE_READ', 'INTERACTIVE_STATE', 'LOW_RISK_CHANGE',
        'DISRUPTIVE_CHANGE', 'DESTRUCTIVE_CHANGE', 'SENSITIVE_ARTIFACT'],
    }),
  };
}


function fakeDependencies(env, overrides = {}) {
  const calls = [];
  let closed = 0;
  return {
    dependencies: {
      env, now: NOW, proof: proof(),
      adapter: {
        async execute(request) {
          calls.push({ step: request.step, credential: request.credential ?? null });
          return { status: 'ok', observation: 'bounded-structural-observation' };
        },
        async close() { closed += 1; },
      },
      credentialResolver: async (reference) => reference === 'vault:field-value'
        ? 'SYNTH_SECRET_RUNNER_VALUE' : null,
      ...overrides,
    },
    calls,
    closed: () => closed,
  };
}


test('closed parser accepts the complete open envelope and freezes it', () => {
  const request = parseRunnerArgs(OPEN, NOW);
  assert.equal(request.step, 'open');
  assert.equal(request.envelope.operationId, 'op-runner-001');
  assert.deepEqual(request.envelope.serviceOrigins, ['https://router.example.invalid:443']);
  assert.equal(request.envelope.expiresAt, NOW + 600_000);
  assert.equal(Object.isFrozen(request), true);
  assert.equal(Object.isFrozen(request.envelope), true);
});


test('open accepts an exact enabled artifact policy without file paths', () => {
  const argv = replaceFlag([...OPEN,
    '--action', 'screenshot', '--action', 'trace',
    '--artifact-type', 'screenshot', '--artifact-type', 'trace',
    '--artifact-purpose-ref', 'change-evidence',
    '--artifact-source-class', 'browser-viewport',
    '--artifact-source-class', 'browser-trace',
    '--artifact-destination-class', 'operation-temp',
    '--artifact-max-items', '2', '--artifact-max-bytes', '4096',
    '--artifact-redaction', 'required', '--artifact-retention-seconds', '60',
  ], '--effect', 'SENSITIVE_ARTIFACT');
  const request = parseRunnerArgs(argv, NOW);
  assert.equal(request.envelope.artifactPolicy.enabled, true);
  assert.deepEqual(request.envelope.artifactPolicy.types, ['screenshot', 'trace']);
  assert.equal(request.envelope.artifactPolicy.maxBytes, 4096);
});


test('closed parser accepts every semantic step with only its bounded grammar', () => {
  const cases = [
    ['inspect', ['--origin', 'https://router.example.invalid', '--locator-role', 'status', '--expect-ref', 'status-readable']],
    ['navigate', ['--origin', 'https://router.example.invalid']],
    ['fill', ['--origin', 'https://router.example.invalid', '--locator-role', 'textbox', '--value-ref', 'vault:field-value']],
    ['select', ['--origin', 'https://router.example.invalid', '--locator-role', 'combobox', '--value-ref', 'vault:field-value']],
    ['click', ['--origin', 'https://router.example.invalid', '--locator-role', 'button', '--effect', 'LOW_RISK_CHANGE']],
    ['submit', ['--origin', 'https://router.example.invalid', '--locator-role', 'form', '--effect', 'LOW_RISK_CHANGE']],
    ['upload', ['--origin', 'https://router.example.invalid', '--artifact-ref', 'operation-artifact-1']],
    ['download', ['--origin', 'https://router.example.invalid', '--artifact-ref', 'operation-artifact-1']],
    ['screenshot', ['--origin', 'https://router.example.invalid', '--artifact-ref', 'operation-artifact-1']],
    ['trace', ['--origin', 'https://router.example.invalid', '--artifact-ref', 'operation-artifact-1']],
    ['validate', ['--expect-ref', 'interface-state']],
    ['close', []],
  ];
  for (const [step, extra] of cases) {
    const request = parseRunnerArgs(['--operation-id', 'op-runner-001', '--step', step, ...extra], NOW);
    assert.equal(request.step, step);
  }
});


test('parser rejects executable escape hatches secrets URLs and duplicate or unknown flags', () => {
  const rejected = [
    [...OPEN, '--unknown', 'x'],
    [...OPEN, '--operation-id', 'duplicate'],
    ['--operation-id', 'op-runner-001', '--step', 'inspect', '--url', 'javascript:alert(1)'],
    ['--operation-id', 'op-runner-001', '--step', 'navigate', '--origin', 'data:text/plain,bad'],
    ['--operation-id', 'op-runner-001', '--step', 'fill', '--origin', 'https://user:pass@router.example.invalid', '--value', 'literal'],
    ['--operation-id', 'op-runner-001', '--step', 'inspect', '--cdp-endpoint', 'http://localhost:9222'],
    ['--operation-id', 'op-runner-001', '--step', 'inspect', '--profile-path', '/tmp/profile'],
    ['--operation-id', 'op-runner-001', '--step', 'inspect', '--install-browser', 'true'],
  ];
  for (const argv of rejected) assert.throws(() => parseRunnerArgs(argv, NOW), /BROWSER_RUNNER_/u);
});


test('runner open rejects review roles and mutable audit envelopes', () => {
  assert.throws(
    () => parseRunnerArgs(replaceFlag(OPEN, '--role', 'change-manager'), NOW),
    /BROWSER_RUNNER_ROLE_NOT_EXECUTOR/u,
  );
  assert.throws(
    () => parseRunnerArgs(replaceFlag(OPEN, '--role', 'audit-evidence-collector'), NOW),
    /BROWSER_RUNNER_ROLE_NOT_EXECUTOR/u,
  );
});


test('authorization never lets validate bypass expiry or audit mutate', () => {
  const envelope = parseRunnerArgs(OPEN, NOW).envelope;
  const capability = proof().capability;
  const validate = parseRunnerArgs([
    '--operation-id', envelope.operationId, '--step', 'validate',
    '--expect-ref', envelope.validationRef,
  ], NOW);
  assert.equal(authorizeRunnerStep(validate, envelope, capability, envelope.expiresAt).reasonCode, 'OPERATION_EXPIRED');

  const auditEnvelope = Object.freeze({
    ...envelope, role: 'audit-evidence-collector', expectedEffect: 'LOW_RISK_CHANGE',
  });
  const click = parseRunnerArgs([
    '--operation-id', envelope.operationId, '--step', 'click',
    '--origin', 'https://router.example.invalid', '--locator-role', 'button',
    '--effect', 'LOW_RISK_CHANGE',
  ], NOW);
  assert.equal(authorizeRunnerStep(click, auditEnvelope, capability, NOW).reasonCode, 'ROLE_NOT_EXECUTOR');
});


test('open writes pending only and exact successful correlation activates it', async () => {
  await stateFixture(async (env) => {
    const request = parseRunnerArgs(OPEN, NOW);
    const fixture = fakeDependencies(env);
    const pending = await executeRunnerStep(request, fixture.dependencies);
    assert.equal(pending.status, 'pending');
    assert.equal(pending.reasonCode, 'PENDING_NATIVE_APPROVAL');
    assert.equal(readActiveOperation('session-runner-001', 'op-runner-001', env, NOW + 1), null);
    assert.equal(activateOperation({
      sessionId: 'session-runner-001', operationId: 'op-runner-001',
      toolUseId: 'wrong-tool',
    }, env, NOW + 1), false);
    assert.equal(activateOperation({
      sessionId: 'session-runner-001', operationId: 'op-runner-001',
      toolUseId: proof().toolUseId,
    }, env, NOW + 2), true);
    assert.equal(readActiveOperation('session-runner-001', 'op-runner-001', env, NOW + 3).outcome, 'READY');
    assert.equal(fixture.calls.length, 0);
  });
});


test('native PostToolUse activates only a matching operation staged by PreToolUse', async () => {
  await stateFixture(async (env) => {
    const request = parseRunnerArgs(OPEN, NOW);
    const command = ['node', JSON.stringify(RUNNER_PATH), ...OPEN].join(' ');
    const missing = await executeRunnerStep(request, { env, now: NOW });
    assert.equal(missing.reasonCode, 'PENDING_APPROVAL_MISSING');
    const post = {
      session_id: 'session-runner-001', tool_use_id: 'tool-runner-post-001',
      hook_event_name: 'PostToolUse', tool_name: 'Bash', permission_mode: 'normal',
      tool_input: { command },
    };
    assert.equal(evaluateApprovalHook(JSON.stringify(post), env, NOW + 1), false);
    assert.equal(readActiveOperation('session-runner-001', 'op-runner-001', env, NOW + 1), null);

    const decision = evaluateHook(JSON.stringify({
      session_id: 'session-runner-001', tool_use_id: 'tool-runner-post-001',
      hook_event_name: 'PreToolUse', tool_name: 'Bash', permission_mode: 'normal',
      tool_input: { command },
    }), env, NOW + 2);
    assert.equal(decision.hookSpecificOutput.permissionDecision, 'ask');
    assert.equal((await executeRunnerStep(request, { env, now: NOW + 2 })).status, 'pending');
    assert.equal(evaluateApprovalHook(JSON.stringify(post), env, NOW + 3), true);
    const active = readActiveOperation('session-runner-001', 'op-runner-001', env, NOW + 3);
    assert.equal(active.outcome, 'READY');
    assert.deepEqual(active.capability.effects, ['PUBLIC_READ', 'SENSITIVE_READ']);
    const click = parseRunnerArgs([
      '--operation-id', 'op-runner-001', '--step', 'click',
      '--origin', 'https://router.example.invalid', '--locator-role', 'button',
      '--effect', 'LOW_RISK_CHANGE',
    ], NOW + 4);
    assert.equal(authorizeRunnerStep(click, active.envelope, active.capability, NOW + 4).reasonCode,
      'CAPABILITY_EFFECT_UNAVAILABLE');
  });
});


test('active steps resolve protected values without returning them and require validation', async () => {
  await stateFixture(async (env) => {
    const fixture = fakeDependencies(env);
    await executeRunnerStep(parseRunnerArgs(OPEN, NOW), fixture.dependencies);
    activateOperation({ sessionId: 'session-runner-001', operationId: 'op-runner-001', toolUseId: proof().toolUseId }, env, NOW + 1);
    const fill = parseRunnerArgs([
      '--operation-id', 'op-runner-001', '--step', 'fill',
      '--origin', 'https://router.example.invalid', '--locator-role', 'textbox',
      '--value-ref', 'vault:field-value',
    ], NOW + 2);
    const result = await executeRunnerStep(fill, { ...fixture.dependencies, now: NOW + 2, sessionId: 'session-runner-001' });
    assert.equal(result.status, 'ok');
    assert.equal(result.validationRequired, true);
    assert.doesNotMatch(JSON.stringify(result), /SYNTH_SECRET_RUNNER_VALUE/u);
    assert.equal(fixture.calls[0].credential, 'SYNTH_SECRET_RUNNER_VALUE');
    assert.equal(fixture.closed(), 1);
  });
});


test('maximum-length operation ids retain a bounded internal call correlation', async () => {
  await stateFixture(async (env) => {
    const operationId = `o${'x'.repeat(255)}`;
    const open = replaceFlag(OPEN, '--operation-id', operationId);
    const fixture = fakeDependencies(env);
    await executeRunnerStep(parseRunnerArgs(open, NOW), fixture.dependencies);
    activateOperation({
      sessionId: 'session-runner-001', operationId, toolUseId: proof().toolUseId,
    }, env, NOW + 1);
    const inspect = parseRunnerArgs([
      '--operation-id', operationId, '--step', 'inspect',
      '--origin', 'https://router.example.invalid', '--locator-role', 'status',
      '--expect-ref', 'status-readable',
    ], NOW + 2);
    const result = await executeRunnerStep(inspect, {
      ...fixture.dependencies, now: NOW + 2, sessionId: 'session-runner-001',
    });
    assert.equal(result.status, 'ok');
  });
});


test('runner invokes the detected common adapter API and closes it in finally', async () => {
  await stateFixture(async (env) => {
    const opening = fakeDependencies(env);
    await executeRunnerStep(parseRunnerArgs(OPEN, NOW), opening.dependencies);
    activateOperation({
      sessionId: 'session-runner-001', operationId: 'op-runner-001',
      toolUseId: proof().toolUseId,
    }, env, NOW + 1);
    const calls = [];
    const adapter = {
      async open() { calls.push('open'); },
      async inspect() { calls.push('inspect'); return { status: 'ok', observation: 'structural' }; },
      async close() { calls.push('close'); },
    };
    const inspect = parseRunnerArgs([
      '--operation-id', 'op-runner-001', '--step', 'inspect',
      '--origin', 'https://router.example.invalid', '--locator-role', 'status',
      '--expect-ref', 'status-readable',
    ], NOW + 2);
    const result = await executeRunnerStep(inspect, {
      env, now: NOW + 2, sessionId: 'session-runner-001',
      adapterFactory: async () => ({ state: 'ACTIVE', adapter }),
    });
    assert.equal(result.status, 'ok');
    assert.deepEqual(calls, ['open', 'inspect', 'close']);
  });
});


test('runner reports unavailable detection without attempting a step', async () => {
  await stateFixture(async (env) => {
    const opening = fakeDependencies(env);
    await executeRunnerStep(parseRunnerArgs(OPEN, NOW), opening.dependencies);
    activateOperation({
      sessionId: 'session-runner-001', operationId: 'op-runner-001',
      toolUseId: proof().toolUseId,
    }, env, NOW + 1);
    const inspect = parseRunnerArgs([
      '--operation-id', 'op-runner-001', '--step', 'inspect',
      '--origin', 'https://router.example.invalid', '--locator-role', 'status',
      '--expect-ref', 'status-readable',
    ], NOW + 2);
    const result = await executeRunnerStep(inspect, {
      env, now: NOW + 2, sessionId: 'session-runner-001',
      adapterFactory: async () => ({ state: 'UNAVAILABLE', adapter: null }),
    });
    assert.equal(result.reasonCode, 'CAPABILITY_UNAVAILABLE');
  });
});


test('unknown outcome requires an independent exact reconciliation before retry', async () => {
  await stateFixture(async (env) => {
    const opening = fakeDependencies(env);
    await executeRunnerStep(parseRunnerArgs(OPEN, NOW), opening.dependencies);
    activateOperation({ sessionId: 'session-runner-001', operationId: 'op-runner-001', toolUseId: proof().toolUseId }, env, NOW + 1);
    const click = parseRunnerArgs([
      '--operation-id', 'op-runner-001', '--step', 'click',
      '--origin', 'https://router.example.invalid', '--locator-role', 'button',
      '--effect', 'LOW_RISK_CHANGE',
    ], NOW + 2);
    const failing = fakeDependencies(env, { adapter: {
      async execute() { throw new Error('SYNTH_FAILURE_CONTENT'); }, async close() {},
    } });
    const failed = await executeRunnerStep(click, { ...failing.dependencies, now: NOW + 2, sessionId: 'session-runner-001' });
    assert.equal(failed.status, 'outcome-unknown');
    assert.doesNotMatch(JSON.stringify(failed), /SYNTH_FAILURE_CONTENT/u);
    const blocked = await executeRunnerStep(click, { ...opening.dependencies, now: NOW + 3, sessionId: 'session-runner-001' });
    assert.equal(blocked.reasonCode, 'OUTCOME_UNKNOWN');

    const validate = parseRunnerArgs([
      '--operation-id', 'op-runner-001', '--step', 'validate', '--expect-ref', 'interface-state',
    ], NOW + 4);
    assert.equal((await executeRunnerStep(validate, {
      ...opening.dependencies, now: NOW + 4, sessionId: 'session-runner-001',
    })).reasonCode, 'INDEPENDENT_VALIDATOR_UNAVAILABLE');
    assert.equal((await executeRunnerStep(validate, {
      ...opening.dependencies, now: NOW + 4, sessionId: 'session-runner-001',
      postconditionValidator: async () => ({
        status: 'met', validationRef: 'wrong-reference', outcome: 'not-applied',
      }),
    })).reasonCode, 'VALIDATION_FAILED');
    assert.equal((await executeRunnerStep(validate, {
      ...opening.dependencies, now: NOW + 4, sessionId: 'session-runner-001',
      postconditionValidator: async () => ({
        status: 'met', validationRef: 'interface-state', outcome: 'not-applied',
      }),
    })).reasonCode, 'RECONCILED_NOT_APPLIED');
    assert.equal((await executeRunnerStep(click, {
      ...opening.dependencies, now: NOW + 4, sessionId: 'session-runner-001',
    })).reasonCode, 'STEP_COMPLETED');
    const close = parseRunnerArgs(['--operation-id', 'op-runner-001', '--step', 'close'], NOW + 5);
    assert.equal((await executeRunnerStep(close, {
      ...opening.dependencies, now: NOW + 5, sessionId: 'session-runner-001',
    })).reasonCode, 'OPERATION_CLOSED');
    assert.equal(readActiveOperation('session-runner-001', 'op-runner-001', env, NOW + 6), null);
  });
});


test('confirmed applied unknown outcome cannot repeat the mutation', async () => {
  await stateFixture(async (env) => {
    const opening = fakeDependencies(env);
    await executeRunnerStep(parseRunnerArgs(OPEN, NOW), opening.dependencies);
    activateOperation({ sessionId: 'session-runner-001', operationId: 'op-runner-001', toolUseId: proof().toolUseId }, env, NOW + 1);
    const click = parseRunnerArgs([
      '--operation-id', 'op-runner-001', '--step', 'click',
      '--origin', 'https://router.example.invalid', '--locator-role', 'button',
      '--effect', 'LOW_RISK_CHANGE',
    ], NOW + 2);
    await executeRunnerStep(click, {
      ...opening.dependencies, now: NOW + 2, sessionId: 'session-runner-001',
      adapter: { async execute() { throw new Error('ambiguous'); }, async close() {} },
    });
    const validate = parseRunnerArgs([
      '--operation-id', 'op-runner-001', '--step', 'validate', '--expect-ref', 'interface-state',
    ], NOW + 3);
    assert.equal((await executeRunnerStep(validate, {
      ...opening.dependencies, now: NOW + 3, sessionId: 'session-runner-001',
      postconditionValidator: async () => ({
        status: 'met', validationRef: 'interface-state', outcome: 'applied',
      }),
    })).reasonCode, 'RECONCILED_APPLIED');
    assert.equal((await executeRunnerStep(click, {
      ...opening.dependencies, now: NOW + 4, sessionId: 'session-runner-001',
    })).reasonCode, 'OPERATION_COMPLETE');
  });
});
