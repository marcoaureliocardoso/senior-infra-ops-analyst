import assert from 'node:assert/strict';
import path from 'node:path';
import test from 'node:test';

import { evaluateHook } from '../../skills/command-driven-operations/scripts/validate-ops-command.mjs';
import { analyzeCommand } from '../../skills/command-driven-operations/scripts/command-guard/policy.mjs';
import { parseHookEvent } from '../../skills/command-driven-operations/scripts/command-guard/contract.mjs';
import { stageBrowserOpenApproval } from '../../skills/command-driven-operations/scripts/record-command-approval.mjs';
import { readPendingOperation } from '../../skills/browser-operations/scripts/browser-binding-store.mjs';
import { executeBrowserWorkflow } from '../../skills/browser-operations/scripts/browser-runner.mjs';
import { parseRunnerArgs } from '../../skills/browser-operations/scripts/browser-runner.mjs';
import {
  APPROVAL, OPERATION, SESSION, T0, lifetimeArgs, stageLifetimeApproval,
  withLifetimeState, workflowLifetimeFixture,
} from '../browser-operations/lifetime-helpers.mjs';

const runner = path.resolve('skills/browser-operations/scripts/browser-runner.mjs');
const command = (args) => ['node', JSON.stringify(runner), ...args].join(' ');
function event(args, role = 'network-edge-operator', session = SESSION) {
  return {
    session_id: session, tool_use_id: APPROVAL, hook_event_name: 'PreToolUse',
    tool_name: 'Bash', permission_mode: 'normal', tool_input: { command: command(args) },
    ...(role === 'main' ? {} : { agent_type: role, agent_id: 'native-fixture-agent' }),
  };
}
function at(now, run) {
  const previous = Date.now;
  try { Date.now = () => now; return run(); } finally { Date.now = previous; }
}

test('native actors cannot stage another role or dispatch its workflow', async () => {
  for (const role of ['audit-evidence-collector', 'main', 'diagnostic-operator']) {
    await withLifetimeState(async (env) => {
      const args = lifetimeArgs();
      const raw = JSON.stringify(event(args, role));
      const result = at(T0, () => evaluateHook(raw, env));
      assert.equal(result.hookSpecificOutput.permissionDecision, 'deny', role);
      assert.equal(readPendingOperation(SESSION, OPERATION, env, T0), null);
      const fixture = workflowLifetimeFixture(env);
      const outcome = await executeBrowserWorkflow(parseRunnerArgs(args, T0 + 500), fixture.dependencies);
      assert.notEqual(outcome.reasonCode, 'WORKFLOW_VALIDATED');
      assert.deepEqual(fixture.calls, []);
      // Defense in depth if a caller tries to stage an otherwise fabricated ask.
      assert.equal(stageBrowserOpenApproval({ policyId: 'BROWSER_PROTECTED_RUNNER',
        decision: 'ask', browserArgs: args }, parseHookEvent(raw), env, T0), false);
    });
  }
});

test('matching native executor and main each ask only for their own envelope', async () => {
  for (const role of ['network-edge-operator', 'main']) {
    await withLifetimeState((env) => {
      const args = lifetimeArgs();
      args[args.indexOf('--role') + 1] = role;
      const result = at(T0, () => evaluateHook(JSON.stringify(event(args, role)), env));
      assert.equal(result.hookSpecificOutput.permissionDecision, 'ask');
      assert.equal(readPendingOperation(SESSION, OPERATION, env, T0).envelope.role, role);
    });
  }
});

test('legacy close and validate resolve only an exact live session/native-role binding', async () => {
  await withLifetimeState((env) => {
    stageLifetimeApproval(env, false);
    for (const step of ['close', 'validate']) {
      const args = ['--operation-id', OPERATION, '--step', step,
        ...(step === 'validate' ? ['--expect-ref', 'fixture-state'] : [])];
      const evaluate = (role, session = SESSION, now = T0 + 500) => at(now, () =>
        analyzeCommand(parseHookEvent(JSON.stringify(event(args, role, session))), env));
      const matching = evaluate('network-edge-operator');
      assert.equal(matching.decision, 'ask', step);
      assert.equal(matching.environment, 'http://127.0.0.1:43111');
      assert.ok(matching.modifiers.includes('ALWAYS_ASK'));
      for (const role of ['audit-evidence-collector', 'main', 'diagnostic-operator']) {
        assert.equal(evaluate(role).decision, 'deny', `${step}/${role}`);
      }
      assert.equal(evaluate('network-edge-operator', 'foreign-session').decision, 'deny');
      assert.equal(evaluate('network-edge-operator', 'invalid session').decision, 'deny');
      const wrongMode = { ...event(args), permission_mode: 'acceptEdits' };
      assert.equal(at(T0 + 500, () => analyzeCommand(parseHookEvent(JSON.stringify(wrongMode)), env)).decision, 'deny');
      assert.equal(evaluate('network-edge-operator', SESSION, T0 + 1000).decision, 'deny');
      const missing = args.map((value) => value === OPERATION ? 'op-missing' : value);
      assert.equal(at(T0 + 500, () => analyzeCommand(
        parseHookEvent(JSON.stringify(event(missing))), env)).decision, 'deny');
    }
  });
});

test('open bindings reject session and permission-mode drift before staging', async () => {
  await withLifetimeState((env) => {
    for (const change of [{ session_id: 'foreign-session' }, { permission_mode: 'acceptEdits' }]) {
      const raw = JSON.stringify({ ...event(lifetimeArgs()), ...change });
      assert.equal(at(T0, () => evaluateHook(raw, env)).hookSpecificOutput.permissionDecision, 'deny');
      assert.equal(readPendingOperation(SESSION, OPERATION, env, T0), null);
    }
  });
});
