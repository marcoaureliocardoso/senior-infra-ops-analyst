import assert from 'node:assert/strict';
import test from 'node:test';

import { executeBrowserWorkflow, executeRunnerStep, parseRunnerArgs } from '../../skills/browser-operations/scripts/browser-runner.mjs';
import { consumeOwnedOperation, readActiveOperation, readPendingOperation } from '../../skills/browser-operations/scripts/browser-binding-store.mjs';
import { createOperationClock, createOperationLifetime } from '../../skills/browser-operations/scripts/browser-operation-lifetime.mjs';
import { bindLifetimeAdapter, EXPIRES, OPERATION, ORIGIN, SESSION, stageLifetimeApproval,
  T0, withLifetimeState, workflowLifetimeFixture } from './lifetime-helpers.mjs';
import { replaceWorkflowApproval } from './lifetime-helpers.mjs';


for (const [point, forbidden, status] of [
  ['execution:discovery', 'execution:open', 'denied'],
  ['execution:open', 'execution:navigate', 'denied'],
  ['execution:value-resolve', 'execution:fill', 'denied'],
  ['execution:fill', 'execution:submit', 'outcome-unknown'],
  ['execution:submit', 'validation:discovery', 'outcome-unknown'],
  ['execution:close', 'validation:discovery', 'outcome-unknown'],
  ['validation:discovery', 'validation:open', 'outcome-unknown'],
  ['validation:open', 'validation:navigate', 'outcome-unknown'],
  ['validation:value-resolve', 'validation:fill', 'outcome-unknown'],
  ['expected:resolve', 'validation:verify', 'outcome-unknown'],
  ['validation:verify', null, 'outcome-unknown'],
]) {
  test(`original approval expiry at ${point} fences the next consumer and consumes owned state`, async () => {
    await withLifetimeState(async (env) => {
      const request = stageLifetimeApproval(env);
      assert.equal(request.envelope.expiresAt, EXPIRES + 500);
      const fixture = workflowLifetimeFixture(env, point);
      const result = await executeBrowserWorkflow(request, fixture.dependencies);
      if (forbidden !== null) assert.equal(fixture.calls.includes(forbidden), false);
      assert.equal(result.reasonCode, 'OPERATION_EXPIRED');
      assert.equal(result.status, status);
      assert.equal(result.validationRequired, status === 'outcome-unknown');
      assert.equal(fixture.calls.includes('execution:close'), true);
      assert.equal(readPendingOperation(SESSION, OPERATION, env, T0), null);
      assert.equal(readActiveOperation(SESSION, OPERATION, env, T0), null);
    });
  });
}


test('cleanup failure overrides an early legacy call-binding denial', async () => {
  await withLifetimeState(async (env) => {
    stageLifetimeApproval(env, false);
    const request = parseRunnerArgs(['--step', 'inspect', '--operation-id', OPERATION,
      '--origin', ORIGIN, '--locator-role', 'status', '--expect-ref', 'fixture-state'], T0 + 500);
    const result = await executeRunnerStep(request, {
      env, sessionId: SESSION, now: T0 + 900,
      async adapterFactory({ options }) {
        const active = readActiveOperation(SESSION, OPERATION, env, T0 + 900);
        assert.equal(consumeOwnedOperation(active, env), true);
        return { state: 'ACTIVE', adapter: bindLifetimeAdapter({
          async close() { throw new Error('fixture close failure'); },
        }, options.operationLifetime) };
      },
    });
    assert.equal(result.status, 'outcome-unknown');
    assert.equal(result.reasonCode, 'WORKFLOW_CLEANUP_FAILED');
  });
});


test('an acquired but unavailable legacy adapter is still closed', async () => {
  await withLifetimeState(async (env) => {
    stageLifetimeApproval(env, false);
    let closed = 0;
    const request = parseRunnerArgs(['--step', 'inspect', '--operation-id', OPERATION,
      '--origin', ORIGIN, '--locator-role', 'status', '--expect-ref', 'fixture-state'], T0 + 500);
    const result = await executeRunnerStep(request, {
      env, sessionId: SESSION, now: T0 + 900,
      async adapterFactory() { return { state: 'UNAVAILABLE', adapter: { async close() { closed += 1; } } }; },
    });
    assert.equal(result.reasonCode, 'CAPABILITY_UNAVAILABLE');
    assert.equal(closed, 1);
  });
});


test('a lost completion binding cannot turn verified adapter output into workflow success', async () => {
  await withLifetimeState(async (env) => {
    const request = stageLifetimeApproval(env);
    const fixture = workflowLifetimeFixture(env);
    const factory = fixture.dependencies.adapterFactory;
    fixture.dependencies.adapterFactory = async (options) => {
      const detected = await factory(options);
      const adapter = detected.adapter;
      return { state: 'ACTIVE', adapter: Object.freeze({
        ...adapter,
        async verify(...args) {
          const value = await adapter.verify(...args);
          const active = readActiveOperation(SESSION, OPERATION, env, T0 + 900);
          assert.equal(consumeOwnedOperation(active, env), true);
          return value;
        },
      }) };
    };
    const result = await executeBrowserWorkflow(request, fixture.dependencies);
    assert.equal(result.status, 'outcome-unknown');
    assert.equal(result.reasonCode, 'WORKFLOW_COMPLETION_FAILED');
    assert.equal(result.validationRequired, true);
  });
});


for (const sample of [NaN, T0 + 899]) {
  test(`unproven clock during protected reference resolution blocks its consumer (${Number.isNaN(sample) ? 'invalid' : 'backward'})`, async () => {
    await withLifetimeState(async (env) => {
      const request = stageLifetimeApproval(env);
      const fixture = workflowLifetimeFixture(env);
      const read = Object.getOwnPropertyDescriptor(env, 'OPS_BROWSER_VALUE_FIELD').get;
      let invalid = false;
      Object.defineProperty(env, 'OPS_BROWSER_VALUE_FIELD', { configurable: true, get() {
        invalid = true; return read.call(env);
      } });
      const result = await executeBrowserWorkflow(request, { ...fixture.dependencies, now: () => invalid ? sample : T0 + 900 });
      assert.equal(result.reasonCode, 'OPERATION_CLOCK_UNPROVEN');
      assert.equal(result.status, 'denied');
      assert.equal(fixture.calls.includes('execution:fill'), false);
      assert.equal(readActiveOperation(SESSION, OPERATION, env, T0), null);
    });
  });
}


test('a live numeric workflow control validates and consumes the original one-shot grant', async () => {
  await withLifetimeState(async (env) => {
    const request = stageLifetimeApproval(env);
    const fixture = workflowLifetimeFixture(env);
    const result = await executeBrowserWorkflow(request, { ...fixture.dependencies, now: T0 + 900 });
    assert.equal(result.status, 'ok');
    assert.equal(result.reasonCode, 'WORKFLOW_VALIDATED');
    assert.equal(fixture.calls.includes('execution:submit'), true);
    assert.equal(fixture.calls.includes('validation:verify'), true);
    assert.equal(fixture.calls.includes('validation:close'), true);
    assert.equal(readActiveOperation(SESSION, OPERATION, env, T0), null);
  });
});


test('the default invocation clock remains fresh after reference resolution', async () => {
  await withLifetimeState(async (env) => {
    const request = stageLifetimeApproval(env);
    const fixture = workflowLifetimeFixture(env, 'execution:value-resolve');
    const previous = Date.now;
    try {
      Date.now = fixture.now;
      const { now: _injected, ...dependencies } = fixture.dependencies;
      const result = await executeBrowserWorkflow(request, dependencies);
      assert.equal(result.reasonCode, 'OPERATION_EXPIRED');
      assert.equal(fixture.calls.includes('execution:fill'), false);
    } finally { Date.now = previous; }
  });
});


test('select reference resolution observes the same pre-consumer expiry boundary', async () => {
  await withLifetimeState(async (env) => {
    const request = stageLifetimeApproval(env, true, 'select');
    const fixture = workflowLifetimeFixture(env, 'execution:value-resolve');
    const result = await executeBrowserWorkflow(request, fixture.dependencies);
    assert.equal(fixture.calls.includes('execution:select'), false);
    assert.equal(result.reasonCode, 'OPERATION_EXPIRED');
    assert.equal(result.status, 'denied');
  });
});


test('ACTIVE discovery without exact installed lifetime cannot open or mutate', async () => {
  for (const fake of [{ expiresAt: EXPIRES, assertLive: () => T0 + 900 },
    createOperationLifetime({ expiresAt: EXPIRES }, createOperationClock(T0 + 900))]) {
    await withLifetimeState(async (env) => {
      const request = stageLifetimeApproval(env);
      const calls = [];
      const result = await executeBrowserWorkflow(request, {
        env, now: T0 + 900,
        async adapterFactory() { return { state: 'ACTIVE', adapter: Object.freeze({
          operationLifetime: fake, capabilities: { operationLifetime: true, preCall: true, topLevelOrigin: true, redirects: true, popups: true },
          async open() { calls.push('open'); }, async submit() { calls.push('submit'); },
          async close() { calls.push('close'); },
        }) }; },
      });
      assert.equal(result.reasonCode, 'OPERATION_LIFETIME_UNPROVEN');
      assert.equal(result.status, 'denied');
      assert.deepEqual(calls, ['close']);
      assert.equal(readPendingOperation(SESSION, OPERATION, env, T0), null);
    });
  }
});


for (const ambiguous of [false, true]) {
  test(`older ${ambiguous ? 'ambiguous' : 'successful'} workflow cannot validate a replacement grant`, async () => {
    await withLifetimeState(async (env) => {
      const request = stageLifetimeApproval(env);
      const fixture = workflowLifetimeFixture(env);
      const factory = fixture.dependencies.adapterFactory;
      let phase = 0;
      fixture.dependencies.adapterFactory = async (options) => {
        const detected = await factory(options);
        const adapter = detected.adapter;
        const execution = phase++ === 0;
        return { ...detected, adapter: Object.freeze({
          ...adapter,
          async submit(...args) {
            const value = await adapter.submit(...args);
            if (ambiguous && execution) throw new Error('fixture ambiguous submission');
            return value;
          },
          async verify(...args) {
            const value = await adapter.verify(...args);
            const old = readActiveOperation(SESSION, OPERATION, env, T0 + 900);
            const replacement = replaceWorkflowApproval(env, old.capability, ambiguous);
            if (!ambiguous) {
              assert.equal(replacement.outcome, 'READY');
              // A real native call tag marks replacement validation as required.
              const store = await import('../../skills/browser-operations/scripts/browser-binding-store.mjs');
              assert.equal(store.stageBrowserCall(SESSION, OPERATION, {
                toolUseId: 'replacement-call', action: 'submit', effect: 'LOW_RISK_CHANGE',
              }, env, T0 + 900), true);
              assert.equal(store.completeBrowserCall(SESSION, 'replacement-call', env, T0 + 900), true);
            }
            return value;
          },
        }) };
      };
      const result = await executeBrowserWorkflow(request, fixture.dependencies);
      assert.equal(result.status, 'outcome-unknown');
      assert.equal(result.reasonCode, 'WORKFLOW_COMPLETION_FAILED');
      const replacement = readActiveOperation(SESSION, OPERATION, env, T0 + 900);
      assert.equal(replacement.toolUseId, 'tool-replacement-001');
      assert.equal(replacement.envelope.target, 'replacement-router');
      assert.equal(replacement.outcome, ambiguous ? 'OUTCOME_UNKNOWN' : 'READY');
      assert.equal(replacement.validationRequired, true);
    });
  });
}


test('older discovery cannot activate a later identical invocation approval', async () => {
  await withLifetimeState(async (env) => {
    const request = stageLifetimeApproval(env);
    const fixture = workflowLifetimeFixture(env);
    const factory = fixture.dependencies.adapterFactory;
    fixture.dependencies.adapterFactory = async (options) => {
      replaceWorkflowApproval(env, null, false, false, false);
      return factory(options);
    };
    const result = await executeBrowserWorkflow(request, fixture.dependencies);
    assert.equal(result.status, 'denied');
    assert.equal(fixture.calls.includes('execution:open'), false);
    assert.equal(readPendingOperation(SESSION, OPERATION, env, T0 + 900).toolUseId, 'tool-replacement-001');
    assert.equal(readActiveOperation(SESSION, OPERATION, env, T0 + 900), null);
  });
});


for (const point of ['discovery', 'open', 'inspect', 'validator']) {
  test(`legacy read-only expiry during ${point} cannot complete successfully`, async () => {
    await withLifetimeState(async (env) => {
      stageLifetimeApproval(env, false);
      let now = T0 + 900;
      const calls = [];
      const late = (name) => { calls.push(name); if (name === point) now = EXPIRES; };
      const step = parseRunnerArgs(['--step', point === 'validator' ? 'validate' : 'inspect',
        '--operation-id', OPERATION, ...(point === 'validator' ? ['--expect-ref', 'fixture-state']
          : ['--origin', ORIGIN, '--locator-role', 'status', '--expect-ref', 'fixture-state'])], T0 + 500);
      const result = await executeRunnerStep(step, {
        env, sessionId: SESSION, now: () => now,
        async postconditionValidator() { late('validator'); return { status: 'met', validationRef: 'fixture-state' }; },
        async adapterFactory({ options }) {
          late('discovery');
          return { state: 'ACTIVE', adapter: bindLifetimeAdapter({
            async open() { late('open'); },
            async inspect() { late('inspect'); return { status: 'ok' }; },
            async close() { calls.push('close'); },
          }, options.operationLifetime) };
        },
      });
      assert.equal(result.reasonCode, 'OPERATION_EXPIRED');
      assert.notEqual(result.status, 'ok');
      if (point === 'discovery' || point === 'open') assert.equal(calls.includes('inspect'), false);
      if (point !== 'validator') assert.equal(calls.includes('close'), true);
      assert.equal(readActiveOperation(SESSION, OPERATION, env, T0), null);
    });
  });
}
