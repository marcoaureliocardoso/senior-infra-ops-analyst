import assert from 'node:assert/strict';
import { mkdtemp, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import {
  authorizeRunnerStep, executeBrowserWorkflow as realExecuteBrowserWorkflow,
  executeRunnerStep as realExecuteRunnerStep, parseRunnerArgs,
} from '../../skills/browser-operations/scripts/browser-runner.mjs';
import {
  activateOperation, activatePendingWorkflow, readActiveOperation, readPendingOperation,
} from '../../skills/browser-operations/scripts/browser-binding-store.mjs';
import { NOW, capabilityFixture } from './helpers.mjs';
import { evaluateApprovalHook } from '../../skills/command-driven-operations/scripts/record-command-approval.mjs';
import { evaluateHook } from '../../skills/command-driven-operations/scripts/validate-ops-command.mjs';
import { lifetimeFixtureDependencies } from './lifetime-helpers.mjs';


function executeBrowserWorkflow(request, dependencies) {
  return realExecuteBrowserWorkflow(request, lifetimeFixtureDependencies(request, dependencies));
}


function executeRunnerStep(request, dependencies) {
  return realExecuteRunnerStep(request, lifetimeFixtureDependencies(request, dependencies));
}


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
const WORKFLOW = [
  '--step', 'workflow', '--operation-id', 'op-workflow-001',
  '--session-id', 'session-runner-001', '--role', 'network-edge-operator',
  '--objective-ref', 'change-42', '--target', 'edge-router-1',
  '--environment', 'production', '--service-origin', 'http://127.0.0.1:43111',
  '--auth-origin', 'http://127.0.0.1:43111',
  '--identity-ref', 'vault:network-admin', '--credential-transport', 'vault',
  '--permission-mode', 'normal', '--action', 'navigate', '--action', 'fill',
  '--action', 'submit', '--action', 'inspect', '--effect', 'LOW_RISK_CHANGE',
  '--risk', 'LOW_RISK_CHANGE', '--precondition-ref', 'router-reachable',
  '--validation-ref', 'interface-state', '--compensation-ref', 'restore-interface',
  '--expires-in-seconds', '600',
  '--workflow-step', 'eyJzdGVwIjoibmF2aWdhdGUiLCJvcmlnaW4iOiJodHRwOi8vMTI3LjAuMC4xOjQzMTExIn0',
  '--workflow-step', 'eyJzdGVwIjoiZmlsbCIsIm9yaWdpbiI6Imh0dHA6Ly8xMjcuMC4wLjE6NDMxMTEiLCJsb2NhdG9yUm9sZSI6InRleHRib3giLCJsb2NhdG9yTmFtZSI6IlBhc3N3b3JkIiwidmFsdWVSZWYiOiJlbnY6T1BTX0JST1dTRVJfVkFMVUVfUEFTU1dPUkQiLCJ2YWx1ZUNsYXNzIjoiY3JlZGVudGlhbCJ9',
  '--workflow-step', 'eyJzdGVwIjoic3VibWl0Iiwib3JpZ2luIjoiaHR0cDovLzEyNy4wLjAuMTo0MzExMSIsImxvY2F0b3JSb2xlIjoiYnV0dG9uIiwibG9jYXRvck5hbWUiOiJTYXZlIiwiZWZmZWN0IjoiTE9XX1JJU0tfQ0hBTkdFIn0',
  '--validation-step', 'eyJzdGVwIjoiaW5zcGVjdCIsIm9yaWdpbiI6Imh0dHA6Ly8xMjcuMC4wLjE6NDMxMTEiLCJsb2NhdG9yUm9sZSI6InN0YXR1cyIsImxvY2F0b3JOYW1lIjoiU2F2ZWQgc3RhdGUiLCJwcmVkaWNhdGUiOiJ0ZXh0LWVxdWFscyIsImV4cGVjdGVkUmVmIjoiZW52Ok9QU19CUk9XU0VSX1ZBTFVFX0VYUEVDVEVEIiwiZXhwZWN0UmVmIjoiaW50ZXJmYWNlLXN0YXRlIn0',
];
const RUNNER_PATH = path.resolve('skills/browser-operations/scripts/browser-runner.mjs');


function replaceFlag(argv, flag, value) {
  const copy = [...argv];
  copy[copy.indexOf(flag) + 1] = value;
  return copy;
}


function workflowToken(value) {
  return Buffer.from(JSON.stringify(value), 'utf8').toString('base64url');
}


function workflowArgs(overrides = {}) {
  const executionSteps = overrides.executionSteps ?? [
    { step: 'navigate', origin: 'http://127.0.0.1:43111' },
    {
      step: 'fill', origin: 'http://127.0.0.1:43111', locatorRole: 'textbox',
      locatorName: 'Password', valueRef: 'env:OPS_BROWSER_VALUE_PASSWORD',
      valueClass: 'credential',
    },
    {
      step: 'submit', origin: 'http://127.0.0.1:43111', locatorRole: 'button',
      locatorName: 'Save', effect: 'LOW_RISK_CHANGE',
    },
  ];
  const validationSteps = overrides.validationSteps ?? [
    { step: 'navigate', origin: 'http://127.0.0.1:43111' },
    {
      step: 'fill', origin: 'http://127.0.0.1:43111', locatorRole: 'textbox',
      locatorName: 'Password', valueRef: 'env:OPS_BROWSER_VALUE_PASSWORD',
      valueClass: 'credential',
    },
    {
      step: 'inspect', origin: 'http://127.0.0.1:43111', locatorRole: 'status',
      locatorName: 'Saved state', predicate: 'text-equals',
      expectedRef: 'env:OPS_BROWSER_VALUE_EXPECTED', expectRef: 'interface-state',
    },
  ];
  const args = [
    '--step', 'workflow', '--operation-id', overrides.operationId ?? 'op-workflow-001',
    '--session-id', overrides.sessionId ?? 'session-runner-001',
    '--role', 'network-edge-operator', '--objective-ref', 'change-42',
    '--target', 'edge-router-1', '--environment', 'production',
    '--service-origin', 'http://127.0.0.1:43111', '--identity-ref', 'vault:network-admin',
    '--credential-transport', 'vault', '--permission-mode', overrides.permissionMode ?? 'normal',
    '--effect', overrides.effect ?? 'LOW_RISK_CHANGE', '--risk', overrides.risk ?? 'LOW_RISK_CHANGE',
    '--precondition-ref', 'router-reachable', '--validation-ref', 'interface-state',
    '--compensation-ref', 'restore-interface', '--expires-in-seconds', '600',
  ];
  for (const authOrigin of overrides.authOrigins ?? ['http://127.0.0.1:43111']) {
    args.push('--auth-origin', authOrigin);
  }
  for (const action of overrides.actions ?? ['navigate', 'fill', 'submit', 'inspect']) {
    args.push('--action', action);
  }
  for (const step of executionSteps) args.push('--workflow-step', workflowToken(step));
  for (const step of validationSteps) args.push('--validation-step', workflowToken(step));
  return args;
}


function workflowCommand(args = workflowArgs()) {
  return ['node', JSON.stringify(RUNNER_PATH), ...args].join(' ');
}


async function stageWorkflowApproval(env, args, now = NOW) {
  const decision = evaluateHook(JSON.stringify({
    session_id: 'session-runner-001',
    tool_use_id: 'tool-workflow-open-001',
    hook_event_name: 'PreToolUse',
    tool_name: 'Bash',
    permission_mode: 'normal',
    tool_input: { command: workflowCommand(args) },
  }), env, now);
  assert.equal(decision.hookSpecificOutput.permissionDecision, 'ask');
  return parseRunnerArgs(args, now);
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


test('workflow parser binds exact envelope actions origins validation and fingerprint', () => {
  const request = parseRunnerArgs(WORKFLOW, NOW);
  assert.equal(request.step, 'workflow');
  assert.equal(request.executionSteps.length, 3);
  assert.equal(request.validationSteps.length, 1);
  assert.match(request.invocationFingerprint, /^[a-f0-9]{64}$/u);
  assert.equal(Object.isFrozen(request), true);
  assert.throws(() => parseRunnerArgs(replaceFlag(WORKFLOW, '--validation-ref', 'other-interface-state'), NOW), /BROWSER_RUNNER_WORKFLOW_VALIDATION_REFERENCE/u);
  assert.throws(() => parseRunnerArgs(replaceFlag(WORKFLOW, '--action', 'inspect-only'), NOW), /BROWSER_RUNNER_WORKFLOW_ACTION_NOT_BOUND/u);
});


test('workflow fingerprint binds the CLI expiry duration without binding parser clock time', () => {
  const first = parseRunnerArgs(WORKFLOW, NOW);
  const later = parseRunnerArgs(WORKFLOW, NOW + 45_000);
  const longer = parseRunnerArgs(replaceFlag(WORKFLOW, '--expires-in-seconds', '601'), NOW);
  assert.equal(first.envelope.expiresAt, NOW + 600_000);
  assert.equal(later.envelope.expiresAt, NOW + 645_000);
  assert.equal(first.invocationFingerprint, later.invocationFingerprint);
  assert.notEqual(first.invocationFingerprint, longer.invocationFingerprint);
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


test('one-shot workflow returns outcome unknown when validation adapter is unavailable and leaves no reusable binding', async () => {
  await stateFixture(async (env) => {
    const args = workflowArgs();
    const request = await stageWorkflowApproval(env, args, NOW);
    const calls = [];
    const result = await executeBrowserWorkflow(request, {
      env: {
        ...env,
        OPS_BROWSER_SESSION_ID: 'session-runner-001',
        OPS_BROWSER_VALUE_PASSWORD: 'SYNTH_SECRET_WORKFLOW_PASSWORD',
        OPS_BROWSER_VALUE_EXPECTED: 'saved-state-enabled',
      },
      now: NOW + 1,
      adapterFactory: async () => {
        if (calls.length === 0) {
          return {
            state: 'ACTIVE',
            adapter: {
              capabilities: {
                preCall: true, topLevelOrigin: true, redirects: true, popups: true, artifacts: false,
              },
              async open() { calls.push('execution:open'); },
              async navigate() { calls.push('execution:navigate'); return { status: 'ok', observation: 'execution-navigation' }; },
              async fill(step) { calls.push(`execution:fill:${step.credential}`); return { status: 'ok', observation: 'execution-fill' }; },
              async submit() { calls.push('execution:submit'); return { status: 'ok', observation: 'execution-submit' }; },
              async close() { calls.push('execution:close'); },
            },
          };
        }
        calls.push('validation:unavailable');
        return { state: 'UNAVAILABLE', adapter: null };
      },
    });
    assert.equal(result.status, 'outcome-unknown');
    assert.equal(result.reasonCode, 'OUTCOME_UNKNOWN');
    assert.equal(result.validationRequired, true);
    assert.deepEqual(calls, [
      'execution:open',
      'execution:navigate',
      'execution:fill:SYNTH_SECRET_WORKFLOW_PASSWORD',
      'execution:submit',
      'execution:close',
      'validation:unavailable',
    ]);
    assert.equal(readActiveOperation('session-runner-001', request.operationId, env, NOW + 2), null);
    const retry = parseRunnerArgs([
      '--operation-id', request.operationId, '--step', 'submit',
      '--origin', 'http://127.0.0.1:43111', '--locator-role', 'button',
      '--locator-name', 'Save', '--effect', 'LOW_RISK_CHANGE',
    ], NOW + 3);
    assert.equal((await executeRunnerStep(retry, {
      env: { ...env, OPS_BROWSER_SESSION_ID: 'session-runner-001' },
      now: NOW + 3,
      sessionId: 'session-runner-001',
    })).reasonCode, 'OPERATION_NOT_ACTIVE');
  });
});


test('native guard rejects validation configuration before staging authority or dispatch', async () => {
  await stateFixture(async (env) => {
    const inspect = { step: 'inspect', origin: 'http://127.0.0.1:43111', locatorRole: 'status',
      predicate: 'text-equals', expectedRef: 'env:OPS_BROWSER_VALUE_EXPECTED', expectRef: 'interface-state' };
    for (const step of ['fill', 'select']) {
      const args = workflowArgs({ actions: ['navigate', 'fill', 'select', 'submit', 'inspect'],
        validationSteps: [{ step, origin: 'http://127.0.0.1:43111',
          locatorRole: step === 'select' ? 'combobox' : 'textbox',
          locatorName: 'Autosave', valueRef: 'env:OPS_BROWSER_VALUE_FIELD', valueClass: 'configuration' }, inspect] });
      const decision = evaluateHook(JSON.stringify({
        session_id: 'session-runner-001', tool_use_id: `invalid-validation-${step}`,
        hook_event_name: 'PreToolUse', tool_name: 'Bash', permission_mode: 'normal',
        tool_input: { command: workflowCommand(args) },
      }), env, NOW);
      assert.equal(decision.hookSpecificOutput.permissionDecision, 'deny');
      assert.equal(readPendingOperation('session-runner-001', 'op-workflow-001', env, NOW), null);
      assert.throws(() => parseRunnerArgs(args, NOW), { code: 'BROWSER_RUNNER_INVALID_VALIDATION_VALUE_CLASS' });
    }
  });
});

test('validation interactive preparation requires an explicit authentication origin', () => {
  const validationSteps = [
    { step: 'click', origin: 'http://127.0.0.1:43111', locatorRole: 'button',
      locatorName: 'Sign in', effect: 'INTERACTIVE_STATE' },
    { step: 'inspect', origin: 'http://127.0.0.1:43111', locatorRole: 'status',
      predicate: 'present', expectedRef: 'env:OPS_BROWSER_VALUE_EXPECTED', expectRef: 'interface-state' },
  ];
  const common = { actions: ['navigate', 'fill', 'click', 'submit', 'inspect'], validationSteps };
  assert.throws(() => parseRunnerArgs(workflowArgs({ ...common,
    executionSteps: [{ step: 'navigate', origin: 'http://127.0.0.1:43111' }],
    authOrigins: ['https://login.example.invalid'],
  }), NOW), { code: 'BROWSER_RUNNER_WORKFLOW_VALIDATION_AUTH_ORIGIN_NOT_BOUND' });
  assert.equal(parseRunnerArgs(workflowArgs(common), NOW).validationSteps[0].step, 'click');
});

test('one-shot workflow retains unknown for not-met validation after ambiguous failure on the later mutable step', async () => {
  await stateFixture(async (env) => {
    const args = workflowArgs({
      effect: 'LOW_RISK_CHANGE',
      actions: ['navigate', 'click', 'inspect'],
      executionSteps: [
        { step: 'navigate', origin: 'http://127.0.0.1:43111' },
        {
          step: 'click', origin: 'http://127.0.0.1:43111', locatorRole: 'button',
          locatorName: 'Continue', effect: 'INTERACTIVE_STATE',
        },
        {
          step: 'click', origin: 'http://127.0.0.1:43111', locatorRole: 'button',
          locatorName: 'Apply', effect: 'LOW_RISK_CHANGE',
        },
        {
          step: 'click', origin: 'http://127.0.0.1:43111', locatorRole: 'button',
          locatorName: 'Never run', effect: 'LOW_RISK_CHANGE',
        },
      ],
      validationSteps: [
        { step: 'navigate', origin: 'http://127.0.0.1:43111' },
        {
          step: 'inspect', origin: 'http://127.0.0.1:43111', locatorRole: 'status',
          locatorName: 'Saved state', predicate: 'text-equals',
          expectedRef: 'env:OPS_BROWSER_VALUE_EXPECTED', expectRef: 'interface-state',
        },
      ],
    });
    const request = await stageWorkflowApproval(env, args, NOW);
    const calls = [];
    const adapters = [
      {
        capabilities: {
          preCall: true, topLevelOrigin: true, redirects: true, popups: true, artifacts: false,
        },
        async open() { calls.push('execution:open'); },
        async navigate() { calls.push('execution:navigate'); return { status: 'ok', observation: 'execution-navigation' }; },
        async click(step) {
          calls.push(`execution:click:${step.locatorName}:${step.effect}`);
          if (step.locatorName === 'Apply') throw new Error('SYNTH_MUTATION_TIMEOUT');
          return { status: 'ok', observation: 'execution-click' };
        },
        async close() { calls.push('execution:close'); },
      },
      {
        capabilities: {
          preCall: true, topLevelOrigin: true, redirects: true, popups: true, artifacts: false,
        },
        async open() { calls.push('validation:open'); },
        async navigate() { calls.push('validation:navigate'); return { status: 'ok', observation: 'validation-navigation' }; },
        async verify() { calls.push('validation:verify'); return { status: 'not-met', expectRef: 'interface-state' }; },
        async close() { calls.push('validation:close'); },
      },
    ];
    const result = await executeBrowserWorkflow(request, {
      env: {
        ...env,
        OPS_BROWSER_SESSION_ID: 'session-runner-001',
        OPS_BROWSER_VALUE_EXPECTED: 'saved-state-disabled',
      },
      now: NOW + 1,
      adapterFactory: async () => ({ state: 'ACTIVE', adapter: adapters.shift() }),
    });
    assert.equal(result.status, 'outcome-unknown');
    assert.equal(result.reasonCode, 'POSTCONDITION_NOT_MET');
    assert.equal(result.validationRequired, true);
    assert.deepEqual(calls, [
      'execution:open',
      'execution:navigate',
      'execution:click:Continue:INTERACTIVE_STATE',
      'execution:click:Apply:LOW_RISK_CHANGE',
      'execution:close',
      'validation:open',
      'validation:navigate',
      'validation:verify',
      'validation:close',
    ]);
    assert.equal(readActiveOperation('session-runner-001', request.operationId, env, NOW + 2), null);
  });
});


test('one-shot workflow validates after a later non-mutable failure once a mutation already ran', async () => {
  await stateFixture(async (env) => {
    const syntheticExpected = 'SYNTH_SECRET_WORKFLOW_EXPECTED';
    const args = workflowArgs({
      actions: ['navigate', 'submit', 'inspect'],
      executionSteps: [
        { step: 'navigate', origin: 'http://127.0.0.1:43111' },
        {
          step: 'submit', origin: 'http://127.0.0.1:43111', locatorRole: 'button',
          locatorName: 'Save', effect: 'LOW_RISK_CHANGE',
        },
        { step: 'navigate', origin: 'http://127.0.0.1:43111' },
      ],
      validationSteps: [
        { step: 'navigate', origin: 'http://127.0.0.1:43111' },
        {
          step: 'inspect', origin: 'http://127.0.0.1:43111', locatorRole: 'status',
          locatorName: 'Saved state', predicate: 'text-equals',
          expectedRef: 'env:OPS_BROWSER_VALUE_EXPECTED', expectRef: 'interface-state',
        },
      ],
    });
    const request = await stageWorkflowApproval(env, args, NOW);
    const calls = [];
    let observedDuringValidation = null;
    const adapters = [
      {
        capabilities: {
          preCall: true, topLevelOrigin: true, redirects: true, popups: true, artifacts: false,
        },
        async open() { calls.push('execution:open'); },
        async navigate() {
          calls.push('execution:navigate');
          if (calls.filter((entry) => entry === 'execution:navigate').length > 1) {
            throw new Error(syntheticExpected);
          }
          return { status: 'ok', observation: 'execution-navigation' };
        },
        async submit() { calls.push('execution:submit'); return { status: 'ok', observation: 'execution-submit' }; },
        async close() { calls.push('execution:close'); },
      },
      {
        capabilities: {
          preCall: true, topLevelOrigin: true, redirects: true, popups: true, artifacts: false,
        },
        async open() {
          calls.push('validation:open');
          observedDuringValidation = readActiveOperation('session-runner-001', request.operationId, env, NOW + 1);
        },
        async navigate() { calls.push('validation:navigate'); return { status: 'ok', observation: 'validation-navigation' }; },
        async verify() { calls.push('validation:verify'); return { status: 'not-met', expectRef: 'interface-state' }; },
        async close() { calls.push('validation:close'); },
      },
    ];
    const result = await executeBrowserWorkflow(request, {
      env: {
        ...env,
        OPS_BROWSER_SESSION_ID: 'session-runner-001',
        OPS_BROWSER_VALUE_EXPECTED: syntheticExpected,
      },
      now: NOW + 1,
      adapterFactory: async () => ({ state: 'ACTIVE', adapter: adapters.shift() }),
    });
    assert.equal(result.status, 'outcome-unknown');
    assert.equal(result.reasonCode, 'POSTCONDITION_NOT_MET');
    assert.equal(result.validationRequired, true);
    assert.doesNotMatch(JSON.stringify(result), /SYNTH_SECRET_WORKFLOW_EXPECTED/u);
    assert.equal(observedDuringValidation?.outcome, 'OUTCOME_UNKNOWN');
    assert.deepEqual(observedDuringValidation?.outcomeObservation, {
      reasonCode: 'ADAPTER_FAILURE',
      action: 'submit',
      effect: 'LOW_RISK_CHANGE',
      observedAt: NOW + 1,
    });
    assert.doesNotMatch(JSON.stringify(observedDuringValidation), /SYNTH_SECRET_WORKFLOW_EXPECTED/u);
    assert.deepEqual(calls, [
      'execution:open',
      'execution:navigate',
      'execution:submit',
      'execution:navigate',
      'execution:close',
      'validation:open',
      'validation:navigate',
      'validation:verify',
      'validation:close',
    ]);
    assert.equal(readActiveOperation('session-runner-001', request.operationId, env, NOW + 2), null);
  });
});


test('one-shot workflow denies a destructive execution step before adapter dispatch when envelope effect is only interactive', async () => {
  await stateFixture(async (env) => {
    const args = workflowArgs({
      effect: 'INTERACTIVE_STATE',
      risk: 'LOW_RISK_CHANGE',
      actions: ['navigate', 'click', 'inspect'],
      executionSteps: [
        { step: 'navigate', origin: 'http://127.0.0.1:43111' },
        {
          step: 'click', origin: 'http://127.0.0.1:43111', locatorRole: 'button',
          locatorName: 'Destroy', effect: 'DESTRUCTIVE_CHANGE',
        },
      ],
      validationSteps: [
        {
          step: 'inspect', origin: 'http://127.0.0.1:43111', locatorRole: 'status',
          locatorName: 'Saved state', predicate: 'present',
          expectedRef: 'env:OPS_BROWSER_VALUE_EXPECTED', expectRef: 'interface-state',
        },
      ],
    });
    const request = await stageWorkflowApproval(env, args, NOW);
    const calls = [];
    const result = await executeBrowserWorkflow(request, {
      env: {
        ...env,
        OPS_BROWSER_SESSION_ID: 'session-runner-001',
        OPS_BROWSER_VALUE_EXPECTED: 'ignored',
      },
      now: NOW + 1,
      adapterFactory: async () => ({
        state: 'ACTIVE',
        adapter: {
          capabilities: {
            preCall: true, topLevelOrigin: true, redirects: true, popups: true, artifacts: false,
          },
          async open() { calls.push('execution:open'); },
          async navigate() { calls.push('execution:navigate'); return { status: 'ok', observation: 'execution-navigation' }; },
          async click() { calls.push('execution:click'); return { status: 'ok', observation: 'execution-click' }; },
          async close() { calls.push('execution:close'); },
        },
      }),
    });
    assert.equal(result.status, 'denied');
    assert.ok(new Set(['CAPABILITY_EFFECT_UNAVAILABLE', 'EFFECT_NOT_BOUND']).has(result.reasonCode));
    assert.deepEqual(calls, ['execution:open', 'execution:navigate', 'execution:close']);
    assert.equal(readActiveOperation('session-runner-001', request.operationId, env, NOW + 2), null);
  });
});


test('one-shot workflow returns outcome unknown when validation expectation cannot be resolved and leaves no reusable binding', async () => {
  await stateFixture(async (env) => {
    const args = workflowArgs();
    const request = await stageWorkflowApproval(env, args, NOW);
    const calls = [];
    const adapters = [
      {
        capabilities: {
          preCall: true, topLevelOrigin: true, redirects: true, popups: true, artifacts: false,
        },
        async open() { calls.push('execution:open'); },
        async navigate() { calls.push('execution:navigate'); return { status: 'ok', observation: 'execution-navigation' }; },
        async fill(step) { calls.push(`execution:fill:${step.credential}`); return { status: 'ok', observation: 'execution-fill' }; },
        async submit() { calls.push('execution:submit'); return { status: 'ok', observation: 'execution-submit' }; },
        async close() { calls.push('execution:close'); },
      },
      {
        capabilities: {
          preCall: true, topLevelOrigin: true, redirects: true, popups: true, artifacts: false,
        },
        async open() { calls.push('validation:open'); },
        async navigate() { calls.push('validation:navigate'); return { status: 'ok', observation: 'validation-navigation' }; },
        async fill(step) { calls.push(`validation:fill:${step.credential}`); return { status: 'ok', observation: 'validation-fill' }; },
        async verify() { calls.push('validation:verify'); return { status: 'met', expectRef: 'interface-state' }; },
        async close() { calls.push('validation:close'); },
      },
    ];
    const result = await executeBrowserWorkflow(request, {
      env: {
        ...env,
        OPS_BROWSER_SESSION_ID: 'session-runner-001',
        OPS_BROWSER_VALUE_PASSWORD: 'SYNTH_SECRET_WORKFLOW_PASSWORD',
      },
      now: NOW + 1,
      adapterFactory: async () => ({ state: 'ACTIVE', adapter: adapters.shift() }),
    });
    assert.equal(result.status, 'outcome-unknown');
    assert.equal(result.reasonCode, 'VALIDATION_REFERENCE_UNRESOLVED');
    assert.equal(result.validationRequired, true);
    assert.deepEqual(calls, [
      'execution:open',
      'execution:navigate',
      'execution:fill:SYNTH_SECRET_WORKFLOW_PASSWORD',
      'execution:submit',
      'execution:close',
      'validation:open',
      'validation:navigate',
      'validation:fill:SYNTH_SECRET_WORKFLOW_PASSWORD',
      'validation:close',
    ]);
    assert.equal(readActiveOperation('session-runner-001', request.operationId, env, NOW + 2), null);
  });
});


test('one-shot workflow activates before browser effects, uses a fresh validation adapter, and keeps secrets bounded', async () => {
  await stateFixture(async (envBase) => {
    const args = workflowArgs();
    const request = await stageWorkflowApproval(envBase, args, NOW);
    const events = [];
    const env = new Proxy({
      ...envBase,
      OPS_BROWSER_SESSION_ID: 'session-runner-001',
      OPS_BROWSER_VALUE_PASSWORD: 'SYNTH_SECRET_WORKFLOW_PASSWORD',
      OPS_BROWSER_VALUE_EXPECTED: 'saved-state-enabled',
    }, {
      get(target, property, receiver) {
        if (typeof property === 'string' && property.startsWith('OPS_BROWSER_VALUE_')) {
          events.push(`env:${property}`);
        }
        return Reflect.get(target, property, receiver);
      },
    });
    let validationOpenedAfterExecutionClosed = false;
    let executionClosed = false;
    const adapters = [
      {
        capabilities: {
          preCall: true, topLevelOrigin: true, redirects: true, popups: true, artifacts: false,
        },
        async open() {
          const active = readActiveOperation('session-runner-001', request.operationId, env, NOW + 1);
          assert.notEqual(active, null);
          assert.equal(readPendingOperation('session-runner-001', request.operationId, env, NOW + 1), null);
          events.push('execution:open');
        },
        async navigate(step) { events.push(`execution:${step.step}`); return { status: 'ok', observation: 'execution-navigation' }; },
        async fill(step) { events.push(`execution:${step.step}:${step.credential}`); return { status: 'ok', observation: 'execution-fill' }; },
        async submit(step) { events.push(`execution:${step.step}`); return { status: 'ok', observation: 'execution-submit' }; },
        async close() { executionClosed = true; events.push('execution:close'); },
      },
      {
        capabilities: {
          preCall: true, topLevelOrigin: true, redirects: true, popups: true, artifacts: false,
        },
        async open() {
          validationOpenedAfterExecutionClosed = executionClosed;
          events.push('validation:open');
        },
        async navigate(step) { events.push(`validation:${step.step}`); return { status: 'ok', observation: 'validation-navigation' }; },
        async fill(step) { events.push(`validation:${step.step}:${step.credential}`); return { status: 'ok', observation: 'validation-fill' }; },
        async verify(step) {
          events.push(`validation:verify:${step.expected}`);
          return { status: 'met', expectRef: step.expectRef };
        },
        async close() { events.push('validation:close'); },
      },
    ];
    const result = await executeBrowserWorkflow(request, {
      env,
      now: NOW + 1,
      adapterFactory: async () => ({ state: 'ACTIVE', adapter: adapters.shift() }),
    });
    assert.equal(result.reasonCode, 'WORKFLOW_VALIDATED');
    assert.equal(validationOpenedAfterExecutionClosed, true);
    assert.deepEqual(events, [
      'execution:open',
      'execution:navigate',
      'env:OPS_BROWSER_VALUE_PASSWORD',
      'execution:fill:SYNTH_SECRET_WORKFLOW_PASSWORD',
      'execution:submit',
      'execution:close',
      'validation:open',
      'validation:navigate',
      'env:OPS_BROWSER_VALUE_PASSWORD',
      'validation:fill:SYNTH_SECRET_WORKFLOW_PASSWORD',
      'env:OPS_BROWSER_VALUE_EXPECTED',
      'validation:verify:saved-state-enabled',
      'validation:close',
    ]);
    assert.doesNotMatch(JSON.stringify(result), /SYNTH_SECRET_WORKFLOW_PASSWORD|saved-state-enabled/u);
    assert.equal(readActiveOperation('session-runner-001', request.operationId, env, NOW + 2), null);
  });
});


test('one-shot workflow rejects mutable execution before open when runtime popup containment is absent', async () => {
  await stateFixture(async (env) => {
    const args = workflowArgs();
    const request = await stageWorkflowApproval(env, args, NOW);
    let opened = false;
    const result = await executeBrowserWorkflow(request, {
      env: {
        ...env,
        OPS_BROWSER_SESSION_ID: 'session-runner-001',
        OPS_BROWSER_VALUE_PASSWORD: 'SYNTH_SECRET_WORKFLOW_PASSWORD',
        OPS_BROWSER_VALUE_EXPECTED: 'saved-state-enabled',
      },
      now: NOW + 1,
      adapterFactory: async () => ({
        state: 'ACTIVE',
        adapter: {
          capabilities: {
            preCall: true, topLevelOrigin: true, redirects: true, popups: false, artifacts: false,
          },
          async open() { opened = true; },
          async close() {},
        },
      }),
    });
    assert.equal(result.reasonCode, 'CAPABILITY_UNAVAILABLE');
    assert.equal(opened, false);
    assert.equal(readActiveOperation('session-runner-001', request.operationId, env, NOW + 2), null);
    assert.equal(readPendingOperation('session-runner-001', request.operationId, env, NOW + 2), null);
  });
});


test('workflow binds credential values only to explicit authentication origins', () => {
  const accepted = parseRunnerArgs(workflowArgs({
    authOrigins: ['https://login.example.invalid'],
    executionSteps: [
      { step: 'navigate', origin: 'https://login.example.invalid' },
      {
        step: 'fill', origin: 'https://login.example.invalid', locatorRole: 'textbox',
        valueRef: 'env:OPS_BROWSER_VALUE_PASSWORD', valueClass: 'credential',
      },
    ],
    validationSteps: [{
      step: 'inspect', origin: 'http://127.0.0.1:43111', locatorRole: 'status',
      predicate: 'present', expectedRef: 'env:OPS_BROWSER_VALUE_EXPECTED',
      expectRef: 'interface-state',
    }],
    actions: ['navigate', 'fill', 'inspect'],
  }), NOW);
  assert.equal(accepted.executionSteps[1].valueClass, 'credential');
  assert.throws(() => parseRunnerArgs(workflowArgs({
    authOrigins: ['https://login.example.invalid'],
    executionSteps: [
      { step: 'navigate', origin: 'http://127.0.0.1:43111' },
      {
        step: 'fill', origin: 'http://127.0.0.1:43111', locatorRole: 'textbox',
        valueRef: 'env:OPS_BROWSER_VALUE_PASSWORD', valueClass: 'credential',
      },
    ],
    validationSteps: [{
      step: 'inspect', origin: 'http://127.0.0.1:43111', locatorRole: 'status',
      predicate: 'present', expectedRef: 'env:OPS_BROWSER_VALUE_EXPECTED',
      expectRef: 'interface-state',
    }],
    actions: ['navigate', 'fill', 'inspect'],
  }), NOW), /WORKFLOW_CREDENTIAL_ORIGIN_NOT_BOUND/u);
});


test('one-shot workflow validates an ambiguous autosaving fill failure', async () => {
  await stateFixture(async (env) => {
    const args = workflowArgs({
      effect: 'INTERACTIVE_STATE', risk: 'LOW_RISK_CHANGE',
      executionSteps: [
        { step: 'navigate', origin: 'http://127.0.0.1:43111' },
        {
          step: 'fill', origin: 'http://127.0.0.1:43111', locatorRole: 'textbox',
          valueRef: 'env:OPS_BROWSER_VALUE_PASSWORD', valueClass: 'credential',
        },
      ],
      validationSteps: [{
        step: 'inspect', origin: 'http://127.0.0.1:43111', locatorRole: 'status',
        predicate: 'text-equals', expectedRef: 'env:OPS_BROWSER_VALUE_EXPECTED',
        expectRef: 'interface-state',
      }],
      actions: ['navigate', 'fill', 'inspect'],
    });
    const request = await stageWorkflowApproval(env, args, NOW);
    const calls = [];
    const adapters = [
      {
        capabilities: {
          preCall: true, topLevelOrigin: true, redirects: true, popups: true, artifacts: false,
        },
        async open() { calls.push('execution:open'); },
        async navigate() { calls.push('execution:navigate'); return { status: 'ok' }; },
        async fill() { calls.push('execution:fill'); throw new Error('SYNTH_AUTOSAVE_TIMEOUT'); },
        async close() { calls.push('execution:close'); },
      },
      {
        capabilities: {
          preCall: true, topLevelOrigin: true, redirects: true, popups: true, artifacts: false,
        },
        async open() { calls.push('validation:open'); },
        async verify() { calls.push('validation:verify'); return { status: 'met', expectRef: 'interface-state' }; },
        async close() { calls.push('validation:close'); },
      },
    ];
    const result = await executeBrowserWorkflow(request, {
      env: {
        ...env, OPS_BROWSER_SESSION_ID: 'session-runner-001',
        OPS_BROWSER_VALUE_PASSWORD: 'SYNTH_SECRET_WORKFLOW_PASSWORD',
        OPS_BROWSER_VALUE_EXPECTED: 'saved-state-enabled',
      },
      now: NOW + 1,
      adapterFactory: async () => ({ state: 'ACTIVE', adapter: adapters.shift() }),
    });
    assert.equal(result.reasonCode, 'WORKFLOW_VALIDATED');
    assert.deepEqual(calls, [
      'execution:open', 'execution:navigate', 'execution:fill', 'execution:close',
      'validation:open', 'validation:verify', 'validation:close',
    ]);
  });
});


test('one-shot workflow retains partial autosaved state as unknown after a later read failure', async () => {
  await stateFixture(async (env) => {
    const persisted = { changed: false };
    const args = workflowArgs({
      effect: 'INTERACTIVE_STATE',
      risk: 'LOW_RISK_CHANGE',
      actions: ['navigate', 'fill', 'inspect'],
      executionSteps: [
        { step: 'navigate', origin: 'http://127.0.0.1:43111' },
        {
          step: 'fill', origin: 'http://127.0.0.1:43111', locatorRole: 'textbox',
          locatorName: 'Hostname', valueRef: 'env:OPS_BROWSER_VALUE_HOSTNAME',
          valueClass: 'configuration',
        },
        {
          step: 'inspect', origin: 'http://127.0.0.1:43111', locatorRole: 'status',
          locatorName: 'Transient status', predicate: 'present',
          expectedRef: 'env:OPS_BROWSER_VALUE_EXPECTED', expectRef: 'interface-state',
        },
      ],
      validationSteps: [
        { step: 'navigate', origin: 'http://127.0.0.1:43111' },
        {
          step: 'inspect', origin: 'http://127.0.0.1:43111', locatorRole: 'status',
          locatorName: 'Saved state', predicate: 'text-equals',
          expectedRef: 'env:OPS_BROWSER_VALUE_EXPECTED', expectRef: 'interface-state',
        },
      ],
    });
    const request = await stageWorkflowApproval(env, args, NOW);
    const calls = [];
    const adapters = [
      {
        capabilities: {
          preCall: true, topLevelOrigin: true, redirects: true, popups: true, artifacts: false,
        },
        async open() { calls.push('execution:open'); },
        async navigate() { calls.push('execution:navigate'); return { status: 'ok' }; },
        async fill(step) { persisted.changed = true; calls.push(`execution:fill:${step.credential}`); return { status: 'ok' }; },
        async inspect() { calls.push('execution:inspect'); throw new Error('SYNTH_READ_FAILURE'); },
        async close() { calls.push('execution:close'); },
      },
      {
        capabilities: {
          preCall: true, topLevelOrigin: true, redirects: true, popups: true, artifacts: false,
        },
        async open() { calls.push('validation:open'); },
        async navigate() { calls.push('validation:navigate'); return { status: 'ok' }; },
        async verify() { calls.push('validation:verify'); return { status: 'not-met', expectRef: 'interface-state' }; },
        async close() { calls.push('validation:close'); },
      },
    ];
    const result = await executeBrowserWorkflow(request, {
      env: {
        ...env,
        OPS_BROWSER_SESSION_ID: 'session-runner-001',
        OPS_BROWSER_VALUE_HOSTNAME: 'synthetic-hostname',
        OPS_BROWSER_VALUE_EXPECTED: 'saved-state-enabled',
      },
      now: NOW + 1,
      adapterFactory: async () => ({ state: 'ACTIVE', adapter: adapters.shift() }),
    });
    assert.equal(persisted.changed, true);
    assert.equal(result.status, 'outcome-unknown');
    assert.equal(result.reasonCode, 'POSTCONDITION_NOT_MET');
    assert.equal(result.validationRequired, true);
    assert.deepEqual(calls, [
      'execution:open', 'execution:navigate', 'execution:fill:synthetic-hostname',
      'execution:inspect', 'execution:close', 'validation:open', 'validation:navigate',
      'validation:verify', 'validation:close',
    ]);
    assert.equal(readActiveOperation('session-runner-001', request.operationId, env, NOW + 2), null);
  });
});


test('one-shot workflow does not treat successful navigation alone as persisted state', async () => {
  await stateFixture(async (env) => {
    const args = workflowArgs({
      effect: 'INTERACTIVE_STATE',
      risk: 'LOW_RISK_CHANGE',
      actions: ['navigate', 'inspect'],
      executionSteps: [
        { step: 'navigate', origin: 'http://127.0.0.1:43111' },
        {
          step: 'inspect', origin: 'http://127.0.0.1:43111', locatorRole: 'status',
          locatorName: 'Transient status', predicate: 'present',
          expectedRef: 'env:OPS_BROWSER_VALUE_EXPECTED', expectRef: 'interface-state',
        },
      ],
      validationSteps: [
        {
          step: 'inspect', origin: 'http://127.0.0.1:43111', locatorRole: 'status',
          locatorName: 'Saved state', predicate: 'present',
          expectedRef: 'env:OPS_BROWSER_VALUE_EXPECTED', expectRef: 'interface-state',
        },
      ],
    });
    const request = await stageWorkflowApproval(env, args, NOW);
    const calls = [];
    let resolutions = 0;
    const result = await executeBrowserWorkflow(request, {
      env: {
        ...env,
        OPS_BROWSER_SESSION_ID: 'session-runner-001',
        OPS_BROWSER_VALUE_EXPECTED: 'saved-state-enabled',
      },
      now: NOW + 1,
      adapterFactory: async () => {
        resolutions += 1;
        return {
          state: 'ACTIVE',
          adapter: {
            capabilities: {
              preCall: true, topLevelOrigin: true, redirects: true, popups: true, artifacts: false,
            },
            async open() { calls.push('execution:open'); },
            async navigate() { calls.push('execution:navigate'); return { status: 'ok' }; },
            async inspect() { calls.push('execution:inspect'); throw new Error('SYNTH_READ_FAILURE'); },
            async close() { calls.push('execution:close'); },
          },
        };
      },
    });
    assert.equal(result.status, 'denied');
    assert.equal(result.reasonCode, 'WORKFLOW_NOT_APPLIED');
    assert.equal(result.validationRequired, false);
    assert.equal(resolutions, 1);
    assert.deepEqual(calls, [
      'execution:open', 'execution:navigate', 'execution:inspect', 'execution:close',
    ]);
    assert.equal(readActiveOperation('session-runner-001', request.operationId, env, NOW + 2), null);
  });
});


test('legacy steps quarantine an interrupted active one-shot workflow binding', async () => {
  await stateFixture(async (env) => {
    const args = workflowArgs();
    const request = await stageWorkflowApproval(env, args, NOW);
    const pending = readPendingOperation('session-runner-001', request.operationId, env, NOW);
    assert.equal(activatePendingWorkflow({
      sessionId: 'session-runner-001',
      operationId: request.operationId,
      invocationFingerprint: request.invocationFingerprint,
      effectiveCapability: {
        state: 'ACTIVE', reasonCode: 'CAPABILITY_ACTIVE',
        adapterId: pending.adapterId, routeClass: 'PROTECTED_RUNNER',
        settingsFingerprint: pending.settingsFingerprint,
        descriptorId: 'protected-runner-v1', serverName: null, toolPrefix: null,
        effects: ['SENSITIVE_READ', 'INTERACTIVE_STATE', 'LOW_RISK_CHANGE'],
        enforcement: {
          preCall: true, topLevelOrigin: true, redirects: true, popups: true, artifacts: false,
        },
      },
    }, env, NOW + 1), true);

    let dispatched = false;
    const submit = parseRunnerArgs([
      '--operation-id', request.operationId, '--step', 'submit',
      '--origin', 'http://127.0.0.1:43111', '--locator-role', 'button',
      '--locator-name', 'Save', '--effect', 'LOW_RISK_CHANGE',
    ], NOW + 2);
    const result = await executeRunnerStep(submit, {
      env, now: NOW + 2, sessionId: 'session-runner-001',
      adapter: {
        async execute() { dispatched = true; return { status: 'ok' }; },
        async close() {},
      },
    });
    assert.equal(result.status, 'denied');
    assert.equal(result.reasonCode, 'WORKFLOW_BINDING_QUARANTINED');
    assert.equal(dispatched, false);
    assert.equal(readActiveOperation('session-runner-001', request.operationId, env, NOW + 3), null);
  });
});


test('workflow closes its injected artifact manager and reports the requested effect', async () => {
  await stateFixture(async (env) => {
    const request = await stageWorkflowApproval(env, workflowArgs(), NOW);
    let artifactCloses = 0;
    const adapters = [
      {
        capabilities: {
          preCall: true, topLevelOrigin: true, redirects: true, popups: true, artifacts: false,
        },
        async open() {}, async navigate() { return { status: 'ok' }; },
        async fill() { return { status: 'ok' }; }, async submit() { return { status: 'ok' }; },
        async close() {},
      },
      {
        capabilities: {
          preCall: true, topLevelOrigin: true, redirects: true, popups: true, artifacts: false,
        },
        async open() {}, async navigate() { return { status: 'ok' }; },
        async fill() { return { status: 'ok' }; },
        async verify() { return { status: 'met', expectRef: 'interface-state' }; },
        async close() {},
      },
    ];
    const result = await executeBrowserWorkflow(request, {
      env: {
        ...env, OPS_BROWSER_SESSION_ID: 'session-runner-001',
        OPS_BROWSER_VALUE_PASSWORD: 'SYNTH_SECRET_WORKFLOW_PASSWORD',
        OPS_BROWSER_VALUE_EXPECTED: 'saved-state-enabled',
      },
      now: NOW + 1,
      artifactManager: { async close() { artifactCloses += 1; } },
      adapterFactory: async () => ({ state: 'ACTIVE', adapter: adapters.shift() }),
    });
    assert.equal(result.effect, 'LOW_RISK_CHANGE');
    assert.equal(artifactCloses, 1);
  });
});


test('one-shot workflow stops after the first ambiguous mutation failure, never retries, and still validates in a fresh context', async () => {
  await stateFixture(async (env) => {
    const args = workflowArgs({
      executionSteps: [
        { step: 'navigate', origin: 'http://127.0.0.1:43111' },
        {
          step: 'submit', origin: 'http://127.0.0.1:43111', locatorRole: 'button',
          locatorName: 'Save', effect: 'LOW_RISK_CHANGE',
        },
        {
          step: 'click', origin: 'http://127.0.0.1:43111', locatorRole: 'button',
          locatorName: 'Never run', effect: 'LOW_RISK_CHANGE',
        },
      ],
      actions: ['navigate', 'fill', 'submit', 'click', 'inspect'],
    });
    const request = await stageWorkflowApproval(env, args, NOW);
    const calls = [];
    const adapters = [
      {
        capabilities: {
          preCall: true, topLevelOrigin: true, redirects: true, popups: true, artifacts: false,
        },
        async open() { calls.push('execution:open'); },
        async navigate() { calls.push('execution:navigate'); return { status: 'ok', observation: 'execution-navigation' }; },
        async submit() { calls.push('execution:submit'); throw new Error('SYNTH_AMBIGUOUS_MUTATION'); },
        async click() { calls.push('execution:click'); return { status: 'ok', observation: 'should-not-run' }; },
        async close() { calls.push('execution:close'); },
      },
      {
        capabilities: {
          preCall: true, topLevelOrigin: true, redirects: true, popups: true, artifacts: false,
        },
        async open() { calls.push('validation:open'); },
        async navigate() { calls.push('validation:navigate'); return { status: 'ok', observation: 'validation-navigation' }; },
        async fill(step) { calls.push(`validation:fill:${step.credential}`); return { status: 'ok', observation: 'validation-fill' }; },
        async verify() { calls.push('validation:verify'); return { status: 'met', expectRef: 'interface-state' }; },
        async close() { calls.push('validation:close'); },
      },
    ];
    const result = await executeBrowserWorkflow(request, {
      env: {
        ...env,
        OPS_BROWSER_SESSION_ID: 'session-runner-001',
        OPS_BROWSER_VALUE_PASSWORD: 'SYNTH_SECRET_WORKFLOW_PASSWORD',
        OPS_BROWSER_VALUE_EXPECTED: 'saved-state-enabled',
      },
      now: NOW + 1,
      adapterFactory: async () => ({ state: 'ACTIVE', adapter: adapters.shift() }),
    });
    assert.equal(result.reasonCode, 'WORKFLOW_VALIDATED');
    assert.deepEqual(calls, [
      'execution:open',
      'execution:navigate',
      'execution:submit',
      'execution:close',
      'validation:open',
      'validation:navigate',
      'validation:fill:SYNTH_SECRET_WORKFLOW_PASSWORD',
      'validation:verify',
      'validation:close',
    ]);
    assert.equal(readActiveOperation('session-runner-001', request.operationId, env, NOW + 2), null);
  });
});


test('one-shot workflow invalidates the activation even when execution adapter open fails', async () => {
  await stateFixture(async (env) => {
    const args = workflowArgs();
    const request = await stageWorkflowApproval(env, args, NOW);
    let closed = 0;
    const result = await executeBrowserWorkflow(request, {
      env: {
        ...env,
        OPS_BROWSER_SESSION_ID: 'session-runner-001',
        OPS_BROWSER_VALUE_PASSWORD: 'SYNTH_SECRET_WORKFLOW_PASSWORD',
        OPS_BROWSER_VALUE_EXPECTED: 'saved-state-enabled',
      },
      now: NOW + 1,
      adapterFactory: async () => ({
        state: 'ACTIVE',
        adapter: {
          capabilities: {
            preCall: true, topLevelOrigin: true, redirects: true, popups: true, artifacts: false,
          },
          async open() { throw new Error('SYNTH_OPEN_FAILURE'); },
          async close() { closed += 1; },
        },
      }),
    });
    assert.equal(result.status, 'denied');
    assert.equal(result.reasonCode, 'WORKFLOW_NOT_APPLIED');
    assert.equal(closed, 1);
    assert.equal(readActiveOperation('session-runner-001', request.operationId, env, NOW + 2), null);
  });
});


test('one-shot workflow lets execution close failure take precedence over execution open failure', async () => {
  await stateFixture(async (env) => {
    const args = workflowArgs();
    const request = await stageWorkflowApproval(env, args, NOW);
    const calls = [];
    const syntheticPassword = 'SYNTH_SECRET_WORKFLOW_PASSWORD';
    const result = await executeBrowserWorkflow(request, {
      env: {
        ...env,
        OPS_BROWSER_SESSION_ID: 'session-runner-001',
        OPS_BROWSER_VALUE_PASSWORD: syntheticPassword,
        OPS_BROWSER_VALUE_EXPECTED: 'saved-state-enabled',
      },
      now: NOW + 1,
      adapterFactory: async () => ({
        state: 'ACTIVE',
        adapter: {
          capabilities: {
            preCall: true, topLevelOrigin: true, redirects: true, popups: true, artifacts: false,
          },
          async open() { calls.push('execution:open'); throw new Error('SYNTH_OPEN_FAILURE'); },
          async close() {
            calls.push('execution:close');
            const error = new Error(syntheticPassword);
            error.code = syntheticPassword;
            throw error;
          },
        },
      }),
    });
    assert.equal(result.status, 'outcome-unknown');
    assert.equal(result.reasonCode, 'ADAPTER_CLOSE_FAILED');
    assert.equal(result.validationRequired, true);
    assert.doesNotMatch(JSON.stringify(result), /SYNTH_SECRET_WORKFLOW_PASSWORD/u);
    assert.deepEqual(calls, ['execution:open', 'execution:close']);
    assert.equal(readActiveOperation('session-runner-001', request.operationId, env, NOW + 2), null);
  });
});


test('one-shot workflow derives fresh validation capability before opening the validation adapter', async () => {
  await stateFixture(async (env) => {
    const args = workflowArgs();
    const request = await stageWorkflowApproval(env, args, NOW);
    const calls = [];
    const adapters = [
      {
        capabilities: {
          preCall: true, topLevelOrigin: true, redirects: true, popups: true, artifacts: false,
        },
        async open() { calls.push('execution:open'); },
        async navigate() { calls.push('execution:navigate'); return { status: 'ok', observation: 'execution-navigation' }; },
        async fill(step) { calls.push(`execution:fill:${step.credential}`); return { status: 'ok', observation: 'execution-fill' }; },
        async submit() { calls.push('execution:submit'); return { status: 'ok', observation: 'execution-submit' }; },
        async close() { calls.push('execution:close'); },
      },
      {
        capabilities: {
          preCall: false, topLevelOrigin: false, redirects: false, popups: false, artifacts: false,
        },
        async open() { calls.push('validation:open'); },
        async close() { calls.push('validation:close'); },
      },
    ];
    const result = await executeBrowserWorkflow(request, {
      env: {
        ...env,
        OPS_BROWSER_SESSION_ID: 'session-runner-001',
        OPS_BROWSER_VALUE_PASSWORD: 'SYNTH_SECRET_WORKFLOW_PASSWORD',
        OPS_BROWSER_VALUE_EXPECTED: 'saved-state-enabled',
      },
      now: NOW + 1,
      adapterFactory: async () => ({ state: 'ACTIVE', adapter: adapters.shift() }),
    });
    assert.equal(result.status, 'outcome-unknown');
    assert.equal(result.reasonCode, 'OUTCOME_UNKNOWN');
    assert.equal(result.validationRequired, true);
    assert.deepEqual(calls, [
      'execution:open',
      'execution:navigate',
      'execution:fill:SYNTH_SECRET_WORKFLOW_PASSWORD',
      'execution:submit',
      'execution:close',
      'validation:close',
    ]);
    assert.equal(readActiveOperation('session-runner-001', request.operationId, env, NOW + 2), null);
  });
});


test('one-shot workflow lets execution close failure take precedence over a denied execution path', async () => {
  await stateFixture(async (env) => {
    const args = workflowArgs({
      effect: 'INTERACTIVE_STATE',
      risk: 'LOW_RISK_CHANGE',
      actions: ['navigate', 'click', 'inspect'],
      executionSteps: [
        { step: 'navigate', origin: 'http://127.0.0.1:43111' },
        {
          step: 'click', origin: 'http://127.0.0.1:43111', locatorRole: 'button',
          locatorName: 'Destroy', effect: 'DESTRUCTIVE_CHANGE',
        },
      ],
      validationSteps: [
        {
          step: 'inspect', origin: 'http://127.0.0.1:43111', locatorRole: 'status',
          locatorName: 'Saved state', predicate: 'present',
          expectedRef: 'env:OPS_BROWSER_VALUE_EXPECTED', expectRef: 'interface-state',
        },
      ],
    });
    const request = await stageWorkflowApproval(env, args, NOW);
    const calls = [];
    const syntheticExpected = 'SYNTH_SECRET_WORKFLOW_EXPECTED';
    const result = await executeBrowserWorkflow(request, {
      env: {
        ...env,
        OPS_BROWSER_SESSION_ID: 'session-runner-001',
        OPS_BROWSER_VALUE_EXPECTED: syntheticExpected,
      },
      now: NOW + 1,
      adapterFactory: async () => ({
        state: 'ACTIVE',
        adapter: {
          capabilities: {
            preCall: true, topLevelOrigin: true, redirects: true, popups: true, artifacts: false,
          },
          async open() { calls.push('execution:open'); },
          async navigate() { calls.push('execution:navigate'); return { status: 'ok', observation: 'execution-navigation' }; },
          async close() {
            calls.push('execution:close');
            const error = new Error(syntheticExpected);
            error.code = syntheticExpected;
            throw error;
          },
        },
      }),
    });
    assert.equal(result.status, 'outcome-unknown');
    assert.equal(result.reasonCode, 'ADAPTER_CLOSE_FAILED');
    assert.equal(result.validationRequired, true);
    assert.doesNotMatch(JSON.stringify(result), /SYNTH_SECRET_WORKFLOW_EXPECTED/u);
    assert.deepEqual(calls, ['execution:open', 'execution:navigate', 'execution:close']);
    assert.equal(readActiveOperation('session-runner-001', request.operationId, env, NOW + 2), null);
  });
});


test('one-shot workflow returns outcome unknown when execution close fails after a mutation and skips validation', async () => {
  await stateFixture(async (env) => {
    const args = workflowArgs();
    const request = await stageWorkflowApproval(env, args, NOW);
    const calls = [];
    const syntheticPassword = 'SYNTH_SECRET_WORKFLOW_PASSWORD';
    const adapters = [
      {
        capabilities: {
          preCall: true, topLevelOrigin: true, redirects: true, popups: true, artifacts: false,
        },
        async open() { calls.push('execution:open'); },
        async navigate() { calls.push('execution:navigate'); return { status: 'ok', observation: 'execution-navigation' }; },
        async fill(step) { calls.push(`execution:fill:${step.credential}`); return { status: 'ok', observation: 'execution-fill' }; },
        async submit() { calls.push('execution:submit'); return { status: 'ok', observation: 'execution-submit' }; },
        async close() {
          calls.push('execution:close');
          const error = new Error(syntheticPassword);
          error.code = syntheticPassword;
          throw error;
        },
      },
      {
        capabilities: {
          preCall: true, topLevelOrigin: true, redirects: true, popups: true, artifacts: false,
        },
        async open() { calls.push('validation:open'); },
        async close() { calls.push('validation:close'); },
      },
    ];
    const result = await executeBrowserWorkflow(request, {
      env: {
        ...env,
        OPS_BROWSER_SESSION_ID: 'session-runner-001',
        OPS_BROWSER_VALUE_PASSWORD: syntheticPassword,
        OPS_BROWSER_VALUE_EXPECTED: 'saved-state-enabled',
      },
      now: NOW + 1,
      adapterFactory: async () => ({ state: 'ACTIVE', adapter: adapters.shift() }),
    });
    assert.equal(result.status, 'outcome-unknown');
    assert.equal(result.reasonCode, 'ADAPTER_CLOSE_FAILED');
    assert.equal(result.validationRequired, true);
    assert.doesNotMatch(JSON.stringify(result), /SYNTH_SECRET_WORKFLOW_PASSWORD/u);
    assert.deepEqual(calls, [
      'execution:open',
      'execution:navigate',
      'execution:fill:SYNTH_SECRET_WORKFLOW_PASSWORD',
      'execution:submit',
      'execution:close',
    ]);
    assert.equal(readActiveOperation('session-runner-001', request.operationId, env, NOW + 2), null);
  });
});


test('one-shot workflow lets validation close failure take precedence over validation open failure', async () => {
  await stateFixture(async (env) => {
    const args = workflowArgs();
    const request = await stageWorkflowApproval(env, args, NOW);
    const calls = [];
    const syntheticPassword = 'SYNTH_SECRET_WORKFLOW_PASSWORD';
    const adapters = [
      {
        capabilities: {
          preCall: true, topLevelOrigin: true, redirects: true, popups: true, artifacts: false,
        },
        async open() { calls.push('execution:open'); },
        async navigate() { calls.push('execution:navigate'); return { status: 'ok', observation: 'execution-navigation' }; },
        async fill(step) { calls.push(`execution:fill:${step.credential}`); return { status: 'ok', observation: 'execution-fill' }; },
        async submit() { calls.push('execution:submit'); return { status: 'ok', observation: 'execution-submit' }; },
        async close() { calls.push('execution:close'); },
      },
      {
        capabilities: {
          preCall: true, topLevelOrigin: true, redirects: true, popups: true, artifacts: false,
        },
        async open() { calls.push('validation:open'); throw new Error('SYNTH_VALIDATION_OPEN_FAILURE'); },
        async close() {
          calls.push('validation:close');
          const error = new Error(syntheticPassword);
          error.code = syntheticPassword;
          throw error;
        },
      },
    ];
    const result = await executeBrowserWorkflow(request, {
      env: {
        ...env,
        OPS_BROWSER_SESSION_ID: 'session-runner-001',
        OPS_BROWSER_VALUE_PASSWORD: syntheticPassword,
        OPS_BROWSER_VALUE_EXPECTED: 'saved-state-enabled',
      },
      now: NOW + 1,
      adapterFactory: async () => ({ state: 'ACTIVE', adapter: adapters.shift() }),
    });
    assert.equal(result.status, 'outcome-unknown');
    assert.equal(result.reasonCode, 'ADAPTER_CLOSE_FAILED');
    assert.equal(result.validationRequired, true);
    assert.doesNotMatch(JSON.stringify(result), /SYNTH_SECRET_WORKFLOW_PASSWORD/u);
    assert.deepEqual(calls, [
      'execution:open',
      'execution:navigate',
      'execution:fill:SYNTH_SECRET_WORKFLOW_PASSWORD',
      'execution:submit',
      'execution:close',
      'validation:open',
      'validation:close',
    ]);
    assert.equal(readActiveOperation('session-runner-001', request.operationId, env, NOW + 2), null);
  });
});


test('one-shot workflow returns outcome unknown when validation close fails before reconciliation completes', async () => {
  await stateFixture(async (env) => {
    const args = workflowArgs({
      actions: ['navigate', 'submit', 'inspect'],
      executionSteps: [
        { step: 'navigate', origin: 'http://127.0.0.1:43111' },
        {
          step: 'submit', origin: 'http://127.0.0.1:43111', locatorRole: 'button',
          locatorName: 'Save', effect: 'LOW_RISK_CHANGE',
        },
      ],
      validationSteps: [
        { step: 'navigate', origin: 'http://127.0.0.1:43111' },
        {
          step: 'inspect', origin: 'http://127.0.0.1:43111', locatorRole: 'status',
          locatorName: 'Saved state', predicate: 'text-equals',
          expectedRef: 'env:OPS_BROWSER_VALUE_EXPECTED', expectRef: 'interface-state',
        },
      ],
    });
    const request = await stageWorkflowApproval(env, args, NOW);
    const calls = [];
    let activeDuringValidationClose = null;
    const adapters = [
      {
        capabilities: {
          preCall: true, topLevelOrigin: true, redirects: true, popups: true, artifacts: false,
        },
        async open() { calls.push('execution:open'); },
        async navigate() { calls.push('execution:navigate'); return { status: 'ok', observation: 'execution-navigation' }; },
        async submit() { calls.push('execution:submit'); throw new Error('SYNTH_AMBIGUOUS_MUTATION'); },
        async close() { calls.push('execution:close'); },
      },
      {
        capabilities: {
          preCall: true, topLevelOrigin: true, redirects: true, popups: true, artifacts: false,
        },
        async open() { calls.push('validation:open'); },
        async navigate() { calls.push('validation:navigate'); return { status: 'ok', observation: 'validation-navigation' }; },
        async verify() { calls.push('validation:verify'); return { status: 'met', expectRef: 'interface-state' }; },
        async close() {
          calls.push('validation:close');
          activeDuringValidationClose = readActiveOperation('session-runner-001', request.operationId, env, NOW + 1);
          const error = new Error('ADAPTER_CLOSE_FAILED');
          error.code = 'ADAPTER_CLOSE_FAILED';
          throw error;
        },
      },
    ];
    const result = await executeBrowserWorkflow(request, {
      env: {
        ...env,
        OPS_BROWSER_SESSION_ID: 'session-runner-001',
        OPS_BROWSER_VALUE_EXPECTED: 'saved-state-enabled',
      },
      now: NOW + 1,
      adapterFactory: async () => ({ state: 'ACTIVE', adapter: adapters.shift() }),
    });
    assert.equal(result.status, 'outcome-unknown');
    assert.equal(result.reasonCode, 'ADAPTER_CLOSE_FAILED');
    assert.equal(activeDuringValidationClose?.outcome, 'OUTCOME_UNKNOWN');
    assert.deepEqual(activeDuringValidationClose?.outcomeObservation, {
      reasonCode: 'ADAPTER_FAILURE',
      action: 'submit',
      effect: 'LOW_RISK_CHANGE',
      observedAt: NOW + 1,
    });
    assert.deepEqual(calls, [
      'execution:open',
      'execution:navigate',
      'execution:submit',
      'execution:close',
      'validation:open',
      'validation:navigate',
      'validation:verify',
      'validation:close',
    ]);
    assert.equal(readActiveOperation('session-runner-001', request.operationId, env, NOW + 2), null);
  });
});
