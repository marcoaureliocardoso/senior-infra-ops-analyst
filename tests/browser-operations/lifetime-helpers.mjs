import assert from 'node:assert/strict';
import { mkdtemp, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';

import { isOperationLifetime } from '../../skills/browser-operations/scripts/browser-operation-lifetime.mjs';
import { parseRunnerArgs } from '../../skills/browser-operations/scripts/browser-runner.mjs';
import { evaluateHook } from '../../skills/command-driven-operations/scripts/validate-ops-command.mjs';
import { evaluateApprovalHook } from '../../skills/command-driven-operations/scripts/record-command-approval.mjs';
import { readPendingOperation, readActiveOperation } from '../../skills/browser-operations/scripts/browser-binding-store.mjs';
import { activatePendingWorkflow, recordOutcomeUnknown } from '../../skills/browser-operations/scripts/browser-binding-store.mjs';


export const T0 = 1_000_000;
export const EXPIRES = T0 + 1000;
export const SESSION = 'session-lifetime-001';
export const OPERATION = 'op-lifetime-001';
export const ORIGIN = 'http://127.0.0.1:43111';
export const APPROVAL = 'tool-lifetime-001';


export async function withLifetimeState(run) {
  const root = await mkdtemp(path.join(os.tmpdir(), 'browser-lifetime-'));
  const env = {
    OPS_BROWSER_STATE_DIR: root,
    OPS_COMMAND_GUARD_STATE_DIR: path.join(root, 'guard'),
    OPS_COMMAND_GUARD_AUDIT_PATH: path.join(root, 'guard', 'audit.jsonl'),
  };
  try { return await run(env); } finally { await rm(root, { recursive: true, force: true }); }
}


export function lifetimeArgs(workflow = true, valueStep = 'fill') {
  const args = [
    '--step', workflow ? 'workflow' : 'open', '--operation-id', OPERATION,
    '--session-id', SESSION, '--role', 'network-edge-operator',
    '--objective-ref', 'fixture-change', '--target', 'fixture-router',
    '--environment', 'test', '--service-origin', ORIGIN, '--auth-origin', ORIGIN,
    '--identity-ref', 'vault:fixture-identity', '--credential-transport', 'vault',
    '--permission-mode', 'normal', '--action', 'navigate', '--action', valueStep,
    '--action', 'submit', '--action', 'inspect', '--action', 'validate', '--action', 'close',
    '--effect', 'LOW_RISK_CHANGE', '--risk', 'LOW_RISK_CHANGE',
    '--precondition-ref', 'fixture-reachable', '--validation-ref', 'fixture-state',
    '--compensation-ref', 'fixture-restore', '--expires-in-seconds', '1',
  ];
  if (workflow) {
    const token = (step) => Buffer.from(JSON.stringify(step)).toString('base64url');
    const fill = { step: valueStep, origin: ORIGIN, locatorRole: valueStep === 'select' ? 'combobox' : 'textbox',
      locatorName: 'Fixture field', valueRef: 'env:OPS_BROWSER_VALUE_FIELD', valueClass: 'credential' };
    for (const step of [{ step: 'navigate', origin: ORIGIN }, fill,
      { step: 'submit', origin: ORIGIN, locatorRole: 'button', locatorName: 'Save', effect: 'LOW_RISK_CHANGE' }]) {
      args.push('--workflow-step', token(step));
    }
    for (const step of [{ step: 'navigate', origin: ORIGIN }, fill,
      { step: 'inspect', origin: ORIGIN, locatorRole: 'status', locatorName: 'Saved',
        predicate: 'text-equals', expectedRef: 'env:OPS_BROWSER_VALUE_EXPECTED', expectRef: 'fixture-state' }]) {
      args.push('--validation-step', token(step));
    }
  }
  return args;
}


export function stageLifetimeApproval(env, workflow = true, valueStep = 'fill') {
  const args = lifetimeArgs(workflow, valueStep);
  parseRunnerArgs(args, T0);
  const event = {
    session_id: SESSION, tool_use_id: APPROVAL, hook_event_name: 'PreToolUse',
    tool_name: 'Bash', permission_mode: 'normal',
    agent_type: 'network-edge-operator', agent_id: 'native-fixture-agent',
    tool_input: { command: ['node', JSON.stringify(path.resolve('skills/browser-operations/scripts/browser-runner.mjs')), ...args].join(' ') },
  };
  const previous = Date.now;
  let decision;
  try {
    Date.now = () => T0;
    decision = evaluateHook(JSON.stringify(event), env);
  } finally { Date.now = previous; }
  assert.equal(decision.hookSpecificOutput.permissionDecision, 'ask', decision.hookSpecificOutput.permissionDecisionReason);
  assert.equal(readPendingOperation(SESSION, OPERATION, env, T0).expiresAt, EXPIRES);
  if (!workflow) assert.equal(evaluateApprovalHook(JSON.stringify({ ...event, hook_event_name: 'PostToolUse' }), env, T0 + 1), true);
  if (!workflow) assert.equal(readActiveOperation(SESSION, OPERATION, env, T0 + 1).expiresAt, EXPIRES);
  return parseRunnerArgs(args, T0 + 500);
}


export function bindLifetimeAdapter(adapter, lifetime, onAttempt = () => {}) {
  assert.equal(isOperationLifetime(lifetime), true, 'factory must receive the genuine invocation lifetime');
  const result = {
    ...adapter, operationLifetime: lifetime,
    capabilities: Object.freeze({ ...adapter.capabilities, operationLifetime: true }),
  };
  for (const [name, method] of Object.entries(adapter)) {
    if (typeof method !== 'function' || name === 'close') continue;
    result[name] = async (...args) => {
      onAttempt(name);
      lifetime.assertLive();
      const value = await method.apply(adapter, args);
      lifetime.assertLive();
      return value;
    };
  }
  return Object.freeze(result);
}


export function lifetimeFixtureDependencies(request, dependencies = {}) {
  if (request.step === 'open' || request.step === 'close') return dependencies;
  const original = dependencies.adapterFactory;
  if (!original && !dependencies.adapter) return dependencies;
  const { adapter: direct, ...rest } = dependencies;
  return {
    ...rest,
    async adapterFactory(options) {
      const detected = original ? await original(options) : { state: 'ACTIVE', adapter: direct };
      if (!detected?.adapter) return detected;
      return { ...detected, adapter: bindLifetimeAdapter(detected.adapter, options.options.operationLifetime) };
    },
  };
}


export function workflowLifetimeFixture(env, expireAt = null) {
  let now = T0 + 900;
  let discovery = 0;
  let resolutions = 0;
  const calls = [];
  const point = (label) => { if (label === expireAt) now = EXPIRES; };
  Object.defineProperties(env, {
    OPS_BROWSER_VALUE_FIELD: { configurable: true, get() {
      const label = resolutions++ === 0 ? 'execution:value-resolve' : 'validation:value-resolve';
      calls.push(label); point(label); return 'fixture-value';
    } },
    OPS_BROWSER_VALUE_EXPECTED: { configurable: true, get() {
      calls.push('expected:resolve'); point('expected:resolve'); return 'fixture-value';
    } },
  });
  const dependencies = {
    env, now: () => now,
    async referenceResolver() { assert.fail('closed env reference must use the bounded fixture env'); },
    async adapterFactory({ options }) {
      const phase = discovery++ === 0 ? 'execution' : 'validation';
      calls.push(`${phase}:discovery`); point(`${phase}:discovery`);
      assert.deepEqual(options.allowedOrigins, [ORIGIN]);
      const method = (name) => async (request) => {
        if (request) assert.equal(request.origin, ORIGIN);
        point(`${phase}:${name}`);
        return name === 'verify' ? { status: 'met', expectRef: 'fixture-state' }
          : { status: 'ok', observation: 'structural' };
      };
      const adapter = {
        capabilities: { preCall: true, topLevelOrigin: true, redirects: true, popups: true },
        open: method('open'), navigate: method('navigate'), fill: method('fill'),
        select: method('select'),
        submit: method('submit'), verify: method('verify'),
        async close() { calls.push(`${phase}:close`); point(`${phase}:close`); },
      };
      return { state: 'ACTIVE', adapter: bindLifetimeAdapter(adapter, options.operationLifetime,
        (name) => calls.push(`${phase}:${name}`)) };
    },
  };
  return { dependencies, calls, now: () => now, expire: () => { now = EXPIRES; } };
}


export function replaceWorkflowApproval(env, capability, unknown = true, differentTarget = true, activate = true) {
  const args = lifetimeArgs();
  if (differentTarget) args[args.indexOf('--target') + 1] = 'replacement-router';
  const previous = Date.now;
  let decision;
  try {
    Date.now = () => T0 + 500;
    decision = evaluateHook(JSON.stringify({
      session_id: SESSION, tool_use_id: 'tool-replacement-001', hook_event_name: 'PreToolUse',
      tool_name: 'Bash', permission_mode: 'normal',
      agent_type: 'network-edge-operator', agent_id: 'native-fixture-agent',
      tool_input: { command: ['node', JSON.stringify(path.resolve('skills/browser-operations/scripts/browser-runner.mjs')), ...args].join(' ') },
    }), env);
  } finally { Date.now = previous; }
  assert.equal(decision.hookSpecificOutput.permissionDecision, 'ask');
  const pending = readPendingOperation(SESSION, OPERATION, env, T0 + 900);
  assert.equal(pending.toolUseId, 'tool-replacement-001');
  if (!activate) return pending;
  assert.equal(activatePendingWorkflow({
    sessionId: SESSION, operationId: OPERATION, invocationFingerprint: pending.invocationFingerprint,
    effectiveCapability: capability,
  }, env, T0 + 900), true);
  if (unknown) assert.equal(recordOutcomeUnknown(SESSION, OPERATION, {
    reasonCode: 'TOOL_FAILURE', action: 'submit', effect: 'LOW_RISK_CHANGE',
  }, env, T0 + 900), true);
  return readActiveOperation(SESSION, OPERATION, env, T0 + 900);
}
