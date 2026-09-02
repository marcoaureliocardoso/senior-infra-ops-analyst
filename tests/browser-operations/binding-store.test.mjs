import assert from 'node:assert/strict';
import { lstat, mkdtemp, readFile, readdir, rm, symlink } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import { parseOperationEnvelope } from '../../skills/browser-operations/scripts/browser-contract.mjs';
import {
  activatePendingWorkflow,
  activateOperation,
  reconcileOutcomeUnknown,
  completeBrowserCall,
  invalidateOperation,
  readActiveOperation,
  recordOutcomeUnknown,
  resolveBrowserStateDirectory,
  stageBrowserCall,
  writePendingOperation,
} from '../../skills/browser-operations/scripts/browser-binding-store.mjs';
import { browserEnvelope, capabilityFixture, NOW } from './helpers.mjs';


async function withState(run) {
  const directory = await mkdtemp(path.join(os.tmpdir(), 'browser-binding-'));
  try {
    await run({ OPS_BROWSER_STATE_DIR: directory });
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
}


function proof(overrides = {}) {
  return {
    toolUseId: 'tool-open-001',
    adapterId: 'fixture-browser',
    routeClass: 'CONTROLLED_BROWSER_MCP',
    settingsFingerprint: 'settings-browser-a',
    permissionModes: ['normal', 'bypassPermissions'],
    capability: capabilityFixture(),
    ...overrides,
  };
}


test('pending operation activates only after exact successful correlation', async () => {
  await withState(async (env) => {
    const envelope = parseOperationEnvelope(browserEnvelope(), NOW);
    assert.equal(writePendingOperation(envelope, proof(), env, NOW), true);
    assert.equal(readActiveOperation(envelope.sessionId, envelope.operationId, env, NOW + 1), null);
    assert.equal(activateOperation({
      sessionId: envelope.sessionId, operationId: envelope.operationId,
      toolUseId: 'different-tool',
    }, env, NOW + 1), false);
    assert.equal(activateOperation({
      sessionId: envelope.sessionId, operationId: envelope.operationId,
      toolUseId: proof().toolUseId,
    }, env, NOW + 2), true);
    const active = readActiveOperation(envelope.sessionId, envelope.operationId, env, NOW + 3);
    assert.equal(active.active, true);
    assert.equal(active.outcome, 'READY');
    assert.equal(active.envelope.target, 'edge-router-1');
  });
});


test('workflow activation consumes only the exact approved invocation fingerprint', async () => {
  await withState(async (env) => {
    const envelope = parseOperationEnvelope(browserEnvelope(), NOW);
    const fingerprint = 'a'.repeat(64);
    writePendingOperation(envelope, proof({
      invocationFingerprint: fingerprint,
      permissionModes: ['bypassPermissions'],
    }), env, NOW);
    assert.equal(activatePendingWorkflow({
      sessionId: envelope.sessionId,
      operationId: envelope.operationId,
      invocationFingerprint: fingerprint,
    }, env, NOW), false);
    writePendingOperation(envelope, proof({
      invocationFingerprint: fingerprint,
      permissionModes: ['normal'],
    }), env, NOW);

    for (const invocationFingerprint of [
      'b'.repeat(64),
      `${fingerprint.slice(0, -1)}b`,
    ]) {
      assert.equal(activatePendingWorkflow({
        sessionId: envelope.sessionId,
        operationId: envelope.operationId,
        invocationFingerprint,
      }, env, NOW + 1), false);
      assert.equal(readActiveOperation(envelope.sessionId, envelope.operationId, env, NOW + 1), null);
    }

    assert.equal(activatePendingWorkflow({
      sessionId: envelope.sessionId,
      operationId: envelope.operationId,
      invocationFingerprint: fingerprint,
    }, env, NOW + 2), true);
    const active = readActiveOperation(envelope.sessionId, envelope.operationId, env, NOW + 3);
    assert.equal(active.invocationFingerprint, fingerprint);
    assert.equal(activatePendingWorkflow({
      sessionId: envelope.sessionId,
      operationId: envelope.operationId,
      invocationFingerprint: fingerprint,
    }, env, NOW + 4), false);
  });
});


test('state is bounded owner-only atomic and contains no raw content', async () => {
  await withState(async (env) => {
    const envelope = parseOperationEnvelope(browserEnvelope(), NOW);
    writePendingOperation(envelope, proof(), env, NOW);
    const entries = await readdir(env.OPS_BROWSER_STATE_DIR);
    assert.equal(entries.length, 1);
    const statePath = path.join(env.OPS_BROWSER_STATE_DIR, entries[0]);
    const text = await readFile(statePath, 'utf8');
    assert.doesNotMatch(text, /password|credentialValue|token|secret|prompt|transcript|tool_input|tool_result/iu);
    assert.equal(resolveBrowserStateDirectory(env), path.resolve(env.OPS_BROWSER_STATE_DIR));
    if (process.platform !== 'win32') {
      assert.equal((await lstat(env.OPS_BROWSER_STATE_DIR)).mode & 0o777, 0o700);
      assert.equal((await lstat(statePath)).mode & 0o777, 0o600);
    }
  });
});


test('state directory and file symlinks fail closed', {
  skip: process.platform === 'win32' ? 'Windows symlink privilege is unavailable' : false,
}, async () => {
  const parent = await mkdtemp(path.join(os.tmpdir(), 'browser-binding-link-'));
  try {
    const real = path.join(parent, 'real');
    const linked = path.join(parent, 'linked');
    await import('node:fs/promises').then(({ mkdir }) => mkdir(real));
    await symlink(real, linked, 'dir');
    const envelope = parseOperationEnvelope(browserEnvelope(), NOW);
    assert.throws(() => writePendingOperation(envelope, proof(), { OPS_BROWSER_STATE_DIR: linked }, NOW), /UNSAFE_STATE_DIRECTORY/u);
  } finally {
    await rm(parent, { recursive: true, force: true });
  }
});


test('outcome unknown quarantines the operation until independent validation', async () => {
  await withState(async (env) => {
    const envelope = parseOperationEnvelope(browserEnvelope(), NOW);
    writePendingOperation(envelope, proof(), env, NOW);
    activateOperation({ sessionId: envelope.sessionId, operationId: envelope.operationId, toolUseId: proof().toolUseId }, env, NOW + 1);
    assert.equal(recordOutcomeUnknown(
      envelope.sessionId, envelope.operationId,
      { reasonCode: 'TOOL_TIMEOUT', action: 'click', effect: 'LOW_RISK_CHANGE' },
      env, NOW + 2,
    ), true);
    assert.equal(readActiveOperation(envelope.sessionId, envelope.operationId, env, NOW + 3).outcome, 'OUTCOME_UNKNOWN');
    assert.equal(reconcileOutcomeUnknown(
      envelope.sessionId, envelope.operationId, 'independent-interface-state', 'not-applied', env, NOW + 4,
    ), true);
    assert.equal(readActiveOperation(envelope.sessionId, envelope.operationId, env, NOW + 5).outcome, 'READY');
  });
});


test('browser call correlation marks mutation validation without retaining call input', async () => {
  await withState(async (env) => {
    const envelope = parseOperationEnvelope(browserEnvelope(), NOW);
    writePendingOperation(envelope, proof(), env, NOW);
    activateOperation({ sessionId: envelope.sessionId, operationId: envelope.operationId, toolUseId: proof().toolUseId }, env, NOW + 1);
    assert.equal(stageBrowserCall(envelope.sessionId, envelope.operationId, {
      toolUseId: 'tool-call-001', action: 'click', effect: 'LOW_RISK_CHANGE',
    }, env, NOW + 2), true);
    assert.equal(completeBrowserCall(
      envelope.sessionId, 'tool-call-001', env, NOW + 3,
    ), true);
    const active = readActiveOperation(envelope.sessionId, envelope.operationId, env, NOW + 4);
    assert.equal(active.validationRequired, true);
    const contents = await Promise.all((await readdir(env.OPS_BROWSER_STATE_DIR)).map((name) =>
      readFile(path.join(env.OPS_BROWSER_STATE_DIR, name), 'utf8')));
    assert.doesNotMatch(contents.join(''), /tool_input|tool_result|pageContent/u);
  });
});


test('invalidating one operation removes only its exact binding', async () => {
  await withState(async (env) => {
    for (const [operationId, toolUseId] of [['op-browser-001', 'tool-open-001'], ['op-browser-002', 'tool-open-002']]) {
      const envelope = parseOperationEnvelope(browserEnvelope({ operationId }), NOW);
      writePendingOperation(envelope, proof({ toolUseId }), env, NOW);
      activateOperation({ sessionId: envelope.sessionId, operationId, toolUseId }, env, NOW + 1);
    }
    assert.equal(invalidateOperation('session-browser-001', 'op-browser-001', 'OPERATOR_CLOSED', env, NOW + 2), true);
    assert.equal(readActiveOperation('session-browser-001', 'op-browser-001', env, NOW + 3), null);
    assert.notEqual(readActiveOperation('session-browser-001', 'op-browser-002', env, NOW + 3), null);
  });
});


test('expired operations are removed and entry count remains bounded', async () => {
  await withState(async (env) => {
    for (let index = 0; index < 17; index += 1) {
      const operationId = `op-browser-${String(index).padStart(3, '0')}`;
      const toolUseId = `tool-open-${String(index).padStart(3, '0')}`;
      const envelope = parseOperationEnvelope(browserEnvelope({ operationId }), NOW);
      writePendingOperation(envelope, proof({ toolUseId }), env, NOW);
    }
    const entries = await readdir(env.OPS_BROWSER_STATE_DIR);
    const state = JSON.parse(await readFile(path.join(env.OPS_BROWSER_STATE_DIR, entries[0]), 'utf8'));
    assert.equal(state.pending.length, 16);
    assert.equal(readActiveOperation('session-browser-001', 'op-browser-001', env, NOW + 700_000), null);
  });
});
