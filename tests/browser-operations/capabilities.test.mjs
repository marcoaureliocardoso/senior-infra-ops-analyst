import assert from 'node:assert/strict';
import test from 'node:test';

import {
  classifyCapability,
  chooseBrowserRoute,
  summarizeContextDelta,
} from '../../skills/browser-operations/scripts/browser-capabilities.mjs';


const EXECUTOR = 'network-edge-operator';


function descriptor(overrides = {}) {
  return {
    id: 'fixture-runner',
    runtimeIdentity: 'fixture/browser-runtime',
    interfaceRevision: 'semantic-v1',
    routeClass: 'PROTECTED_RUNNER',
    effects: ['PUBLIC_READ', 'SENSITIVE_READ', 'INTERACTIVE_STATE', 'LOW_RISK_CHANGE'],
    enforcement: {
      preCall: true,
      topLevelOrigin: true,
      redirects: true,
      popups: true,
      artifacts: true,
    },
    ...overrides,
  };
}


function observation(overrides = {}) {
  return {
    available: true,
    runtimeIdentity: 'fixture/browser-runtime',
    interfaceRevision: 'semantic-v1',
    routeClass: 'PROTECTED_RUNNER',
    settingsFingerprint: 'settings-a',
    guardProof: {
      active: true,
      settingsFingerprint: 'settings-a',
    },
    ...overrides,
  };
}


test('classifies absent and unavailable candidates without inventing a route', () => {
  assert.deepEqual(classifyCapability(undefined, [descriptor()], EXECUTOR), {
    state: 'UNAVAILABLE', reasonCode: 'CAPABILITY_UNAVAILABLE', routeClass: null, adapterId: null,
  });
  assert.deepEqual(classifyCapability({ available: false }, [descriptor()], EXECUTOR), {
    state: 'UNAVAILABLE', reasonCode: 'CAPABILITY_UNAVAILABLE', routeClass: null, adapterId: null,
  });
});


test('recognition requires one exact package-owned descriptor', () => {
  const unrecognized = classifyCapability(observation({ interfaceRevision: 'changed-v2' }), [descriptor()], EXECUTOR);
  assert.equal(unrecognized.state, 'AVAILABLE_UNRECOGNIZED');
  assert.equal(unrecognized.reasonCode, 'CAPABILITY_UNRECOGNIZED');

  const conflict = classifyCapability(observation(), [descriptor(), descriptor({ id: 'duplicate' })], EXECUTOR);
  assert.equal(conflict.state, 'CONFLICT');
  assert.equal(conflict.reasonCode, 'CAPABILITY_CONFLICT');
});


test('a recognized candidate stays inactive until exact guard proof is current', () => {
  for (const guardProof of [
    undefined,
    { active: false, settingsFingerprint: 'settings-a' },
    { active: true, settingsFingerprint: 'settings-b' },
  ]) {
    const result = classifyCapability(observation({ guardProof }), [descriptor()], EXECUTOR);
    assert.equal(result.state, 'AVAILABLE_RECOGNIZED');
    assert.equal(result.reasonCode, 'GUARD_UNPROVEN');
  }
  const active = classifyCapability(observation(), [descriptor()], EXECUTOR);
  assert.equal(active.state, 'ACTIVE');
  assert.equal(active.reasonCode, 'CAPABILITY_ACTIVE');
  assert.equal(active.adapterId, 'fixture-runner');
});


test('missing origin or popup enforcement prevents mutable activation', () => {
  for (const key of ['preCall', 'topLevelOrigin', 'redirects', 'popups']) {
    const result = classifyCapability(observation(), [descriptor({
      enforcement: { ...descriptor().enforcement, [key]: false },
    })], EXECUTOR);
    assert.equal(result.state, 'AVAILABLE_RECOGNIZED');
    assert.equal(result.reasonCode, 'ENFORCEMENT_INSUFFICIENT');
  }
});


test('route selection preserves precedence and detects same-rank conflict', () => {
  const candidates = [
    { ...classifyCapability(observation(), [descriptor()], EXECUTOR), effects: descriptor().effects },
    {
      state: 'ACTIVE', reasonCode: 'CAPABILITY_ACTIVE', adapterId: 'typed-api',
      routeClass: 'TYPED_API_MCP', effects: ['PUBLIC_READ', 'LOW_RISK_CHANGE'],
      enforcement: descriptor().enforcement,
    },
  ];
  assert.equal(chooseBrowserRoute('LOW_RISK_CHANGE', candidates, EXECUTOR).adapterId, 'typed-api');

  const conflict = chooseBrowserRoute('PUBLIC_READ', [
    candidates[1], { ...candidates[1], adapterId: 'typed-api-2' },
  ], EXECUTOR);
  assert.equal(conflict.reasonCode, 'CAPABILITY_CONFLICT');
  assert.equal(conflict.route, null);
});


test('role limits preserve executor, evidence, and review boundaries', () => {
  const active = {
    state: 'ACTIVE', adapterId: 'runner', routeClass: 'PROTECTED_RUNNER',
    effects: ['PUBLIC_READ', 'SENSITIVE_READ', 'LOW_RISK_CHANGE'],
    enforcement: descriptor().enforcement,
  };
  assert.equal(chooseBrowserRoute('LOW_RISK_CHANGE', [active], EXECUTOR).adapterId, 'runner');
  assert.equal(
    chooseBrowserRoute('SENSITIVE_READ', [active], 'audit-evidence-collector').adapterId,
    'runner',
  );
  assert.equal(
    chooseBrowserRoute('LOW_RISK_CHANGE', [active], 'audit-evidence-collector').reasonCode,
    'ROLE_NOT_EXECUTOR',
  );
  assert.equal(
    chooseBrowserRoute('PUBLIC_READ', [active], 'change-manager').reasonCode,
    'ROLE_NOT_EXECUTOR',
  );
});


test('unknown effects and insufficient active routes fail closed', () => {
  assert.equal(chooseBrowserRoute('UNKNOWN', [], EXECUTOR).reasonCode, 'NO_ENFORCEABLE_ROUTE');
  assert.equal(chooseBrowserRoute('DESTRUCTIVE_CHANGE', [{
    state: 'AVAILABLE_RECOGNIZED', adapterId: 'runner', routeClass: 'PROTECTED_RUNNER',
    effects: ['DESTRUCTIVE_CHANGE'], enforcement: descriptor().enforcement,
  }], EXECUTOR).reasonCode, 'NO_ENFORCEABLE_ROUTE');
});


test('context deltas retain only bounded structural measurements', () => {
  const report = summarizeContextDelta(
    {
      usedPercent: 12, skillCount: 25, subagentCount: 12, schemaCount: 0,
      toolCount: 18, toolSearchMode: 'unavailable', prompt: 'SECRET_BEFORE',
    },
    {
      usedPercent: 19, skillCount: 26, subagentCount: 12, schemaCount: 4,
      toolCount: 22, toolSearchMode: 'available-used', content: 'SECRET_AFTER',
    },
  );
  assert.deepEqual(report, {
    usedBefore: 12,
    usedAfter: 19,
    delta: 7,
    skillCountBefore: 25,
    skillCountAfter: 26,
    subagentCountBefore: 12,
    subagentCountAfter: 12,
    schemaCountBefore: 0,
    schemaCountAfter: 4,
    toolCountBefore: 18,
    toolCountAfter: 22,
    toolSearchMode: 'available-used',
  });
  assert.doesNotMatch(JSON.stringify(report), /SECRET|prompt|content/u);
});


test('context accounting rejects invalid percentages, counts, and modes', () => {
  const before = {
    usedPercent: 12, skillCount: 25, subagentCount: 12, schemaCount: 0,
    toolCount: 18, toolSearchMode: 'unavailable',
  };
  assert.throws(() => summarizeContextDelta({ ...before, usedPercent: 101 }, before), /INVALID_CONTEXT_PERCENT/u);
  assert.throws(() => summarizeContextDelta(before, { ...before, toolCount: -1 }), /INVALID_CONTEXT_COUNT/u);
  assert.throws(() => summarizeContextDelta(before, { ...before, toolSearchMode: 'assumed' }), /INVALID_TOOL_SEARCH_MODE/u);
});
