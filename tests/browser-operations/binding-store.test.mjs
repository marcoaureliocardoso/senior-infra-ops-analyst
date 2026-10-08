import assert from 'node:assert/strict';
import { lstat, mkdtemp, readFile, readdir, rm, symlink, writeFile } from 'node:fs/promises';
import fs from 'node:fs';
import { syncBuiltinESMExports } from 'node:module';
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
  readPendingOperation,
  recordOutcomeUnknown,
  resolveBrowserStateDirectory,
  stageBrowserCall,
  writePendingOperation,
} from '../../skills/browser-operations/scripts/browser-binding-store.mjs';
import { authorizeRunnerStep, parseRunnerArgs } from '../../skills/browser-operations/scripts/browser-runner.mjs';
import { browserEnvelope, capabilityFixture, NOW } from './helpers.mjs';
import * as bindingStore from '../../skills/browser-operations/scripts/browser-binding-store.mjs';


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


function workflowApprovalProof(overrides = {}) {
  return proof({
    adapterId: 'protected-runner',
    routeClass: 'PROTECTED_RUNNER',
    settingsFingerprint: 'browser-runner-v1',
    permissionModes: ['normal'],
    invocationFingerprint: 'a'.repeat(64),
    capability: { state: 'PENDING_NATIVE_APPROVAL' },
    ...overrides,
  });
}


function effectiveWorkflowCapability(overrides = {}) {
  return {
    state: 'ACTIVE',
    reasonCode: 'CAPABILITY_ACTIVE',
    adapterId: 'protected-runner',
    routeClass: 'PROTECTED_RUNNER',
    settingsFingerprint: 'browser-runner-v1',
    descriptorId: 'protected-runner-v1',
    serverName: null,
    toolPrefix: null,
    effects: ['SENSITIVE_READ', 'INTERACTIVE_STATE', 'LOW_RISK_CHANGE'],
    enforcement: {
      preCall: true,
      topLevelOrigin: true,
      redirects: true,
      popups: true,
      artifacts: false,
    },
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
    writePendingOperation(envelope, workflowApprovalProof({
      invocationFingerprint: fingerprint,
      permissionModes: ['bypassPermissions'],
    }), env, NOW);
    assert.equal(activatePendingWorkflow({
      sessionId: envelope.sessionId,
      operationId: envelope.operationId,
      invocationFingerprint: fingerprint,
    }, env, NOW), false);
    writePendingOperation(envelope, workflowApprovalProof({
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
      effectiveCapability: effectiveWorkflowCapability(),
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


test('workflow activation replaces the approval marker with a sufficient effective capability', async () => {
  await withState(async (env) => {
    const envelope = parseOperationEnvelope(browserEnvelope({
      actions: ['navigate', 'fill', 'submit', 'inspect'],
    }), NOW);
    const fingerprint = 'a'.repeat(64);
    assert.throws(() => writePendingOperation(envelope, workflowApprovalProof({
      invocationFingerprint: fingerprint,
      capability: effectiveWorkflowCapability(),
    }), env, NOW), /INVALID_BROWSER_PROOF/u);
    writePendingOperation(envelope, workflowApprovalProof({ invocationFingerprint: fingerprint }), env, NOW);

    assert.equal(activatePendingWorkflow({
      sessionId: envelope.sessionId,
      operationId: envelope.operationId,
      invocationFingerprint: fingerprint,
      effectiveCapability: effectiveWorkflowCapability(),
    }, env, NOW + 1), true);
    const active = readActiveOperation(envelope.sessionId, envelope.operationId, env, NOW + 2);
    assert.deepEqual(active.capability, effectiveWorkflowCapability());
    assert.equal(readPendingOperation(envelope.sessionId, envelope.operationId, env, NOW + 2), null);

    const fill = parseRunnerArgs([
      '--operation-id', envelope.operationId, '--step', 'fill',
      '--origin', 'https://router.example.invalid', '--locator-role', 'textbox',
      '--value-ref', 'vault:field-value',
    ], NOW);
    assert.equal(authorizeRunnerStep(fill, active.envelope, active.capability, NOW + 2).allowed, true);
  });
});


test('workflow activation rejects insufficient runtime capabilities without consuming approval', async () => {
  await withState(async (env) => {
    const envelope = parseOperationEnvelope(browserEnvelope({
      actions: ['navigate', 'fill', 'submit', 'inspect'],
    }), NOW);
    const fingerprint = 'a'.repeat(64);
    writePendingOperation(envelope, workflowApprovalProof({ invocationFingerprint: fingerprint }), env, NOW);

    const insufficient = [
      undefined,
      effectiveWorkflowCapability({ effects: ['PUBLIC_READ', 'SENSITIVE_READ'] }),
      effectiveWorkflowCapability({ effects: ['SENSITIVE_READ', 'INTERACTIVE_STATE'] }),
      effectiveWorkflowCapability({ state: 'AVAILABLE_UNRECOGNIZED', reasonCode: 'CAPABILITY_UNRECOGNIZED' }),
      effectiveWorkflowCapability({ state: 'CONFLICT', reasonCode: 'CAPABILITY_CONFLICT' }),
      effectiveWorkflowCapability({ routeClass: 'CONTROLLED_BROWSER_MCP' }),
      effectiveWorkflowCapability({ adapterId: 'other-adapter' }),
      effectiveWorkflowCapability({ settingsFingerprint: 'other-settings' }),
      effectiveWorkflowCapability({ descriptorId: 'unrecognized-runner' }),
      { ...effectiveWorkflowCapability(), untrustedExtra: true },
      effectiveWorkflowCapability({ enforcement: { ...effectiveWorkflowCapability().enforcement, topLevelOrigin: false } }),
      effectiveWorkflowCapability({ enforcement: { ...effectiveWorkflowCapability().enforcement, redirects: false } }),
      effectiveWorkflowCapability({ enforcement: { ...effectiveWorkflowCapability().enforcement, popups: false } }),
    ];
    for (const effectiveCapability of insufficient) {
      assert.equal(activatePendingWorkflow({
        sessionId: envelope.sessionId,
        operationId: envelope.operationId,
        invocationFingerprint: fingerprint,
        effectiveCapability,
      }, env, NOW + 1), false);
      assert.notEqual(readPendingOperation(envelope.sessionId, envelope.operationId, env, NOW + 1), null);
    }

    const artifactEnvelope = parseOperationEnvelope(browserEnvelope({
      operationId: 'op-browser-artifact-001',
      actions: ['screenshot', 'inspect'],
      expectedEffect: 'SENSITIVE_ARTIFACT',
      artifactPolicy: {
        enabled: true,
        types: ['screenshot'],
        purposeRef: 'change-evidence',
        sourceClasses: ['browser-viewport'],
        destinationClasses: ['operation-temp'],
        maxItems: 1,
        maxBytes: 4096,
        redaction: 'required',
        retentionSeconds: 60,
      },
    }), NOW);
    writePendingOperation(artifactEnvelope, workflowApprovalProof({
      toolUseId: 'tool-artifact-001',
      invocationFingerprint: 'b'.repeat(64),
    }), env, NOW);
    assert.equal(activatePendingWorkflow({
      sessionId: artifactEnvelope.sessionId,
      operationId: artifactEnvelope.operationId,
      invocationFingerprint: 'b'.repeat(64),
      effectiveCapability: effectiveWorkflowCapability({
        effects: ['SENSITIVE_READ', 'SENSITIVE_ARTIFACT'],
        enforcement: { ...effectiveWorkflowCapability().enforcement, artifacts: false },
      }),
    }, env, NOW + 1), false);
    assert.notEqual(readPendingOperation(
      artifactEnvelope.sessionId, artifactEnvelope.operationId, env, NOW + 1,
    ), null);
    assert.equal(activatePendingWorkflow({
      sessionId: artifactEnvelope.sessionId,
      operationId: artifactEnvelope.operationId,
      invocationFingerprint: 'b'.repeat(64),
      effectiveCapability: effectiveWorkflowCapability({
        effects: ['SENSITIVE_READ'],
        enforcement: { ...effectiveWorkflowCapability().enforcement, artifacts: true },
      }),
    }, env, NOW + 1), false);
    assert.notEqual(readPendingOperation(
      artifactEnvelope.sessionId, artifactEnvelope.operationId, env, NOW + 1,
    ), null);
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


function ownedCorrelation(envelope, grant = proof()) {
  return {
    sessionId: envelope.sessionId, operationId: envelope.operationId,
    toolUseId: grant.toolUseId, invocationFingerprint: grant.invocationFingerprint ?? null,
    expiresAt: envelope.expiresAt,
  };
}


async function rawState(env) {
  const name = (await readdir(env.OPS_BROWSER_STATE_DIR)).find((entry) => entry.endsWith('.json'));
  const target = path.join(env.OPS_BROWSER_STATE_DIR, name);
  return { target, state: JSON.parse(await readFile(target, 'utf8')) };
}


test('owned cleanup physically consumes expired active calls and is idempotent', async () => {
  await withState(async (env) => {
    const envelope = parseOperationEnvelope(browserEnvelope({ expiresAt: NOW + 1000 }), NOW);
    writePendingOperation(envelope, proof(), env, NOW);
    activateOperation(ownedCorrelation(envelope), env, NOW + 1);
    stageBrowserCall(envelope.sessionId, envelope.operationId, {
      toolUseId: 'call-old', action: 'inspect', effect: 'SENSITIVE_READ',
    }, env, NOW + 2);
    assert.equal(readActiveOperation(envelope.sessionId, envelope.operationId, env, NOW + 1000), null);
    assert.equal(bindingStore.consumeOwnedOperation(ownedCorrelation(envelope), env), true);
    assert.equal(readActiveOperation(envelope.sessionId, envelope.operationId, env, NOW + 2), null);
    assert.equal(readPendingOperation(envelope.sessionId, envelope.operationId, env, NOW + 2), null);
    assert.deepEqual((await rawState(env)).state.calls, []);
    assert.equal(bindingStore.consumeOwnedOperation(ownedCorrelation(envelope), env), true);
  });
});


test('owned cleanup removes an expired pending grant without authorizing it', async () => {
  await withState(async (env) => {
    const envelope = parseOperationEnvelope(browserEnvelope({ expiresAt: NOW + 1000 }), NOW);
    writePendingOperation(envelope, proof(), env, NOW);
    assert.equal(readPendingOperation(envelope.sessionId, envelope.operationId, env, NOW + 1000), null);
    assert.equal(bindingStore.consumeOwnedOperation(ownedCorrelation(envelope), env), true);
    assert.equal(readPendingOperation(envelope.sessionId, envelope.operationId, env, NOW), null);
  });
});


test('old cleanup preserves a later grant and its calls sharing the operation ID', async () => {
  await withState(async (env) => {
    const old = parseOperationEnvelope(browserEnvelope({ expiresAt: NOW + 1000 }), NOW);
    const fresh = parseOperationEnvelope(browserEnvelope({ expiresAt: NOW + 2000 }), NOW + 10);
    writePendingOperation(old, proof(), env, NOW);
    activateOperation(ownedCorrelation(old), env, NOW + 1);
    stageBrowserCall(old.sessionId, old.operationId, {
      toolUseId: 'call-old', action: 'inspect', effect: 'SENSITIVE_READ',
    }, env, NOW + 2);
    const newer = proof({ toolUseId: 'tool-new' });
    writePendingOperation(fresh, newer, env, NOW + 10);
    assert.equal(bindingStore.consumeOwnedOperation(ownedCorrelation(old), env), true);
    assert.equal(readPendingOperation(fresh.sessionId, fresh.operationId, env, NOW + 11).toolUseId, 'tool-new');
    activateOperation(ownedCorrelation(fresh, newer), env, NOW + 12);
    stageBrowserCall(fresh.sessionId, fresh.operationId, {
      toolUseId: 'call-new', action: 'inspect', effect: 'SENSITIVE_READ',
    }, env, NOW + 13);
    assert.equal(bindingStore.consumeOwnedOperation(ownedCorrelation(old), env), true);
    const state = (await rawState(env)).state;
    assert.equal(state.active[0].toolUseId, 'tool-new');
    assert.deepEqual(state.calls.map((entry) => entry.toolUseId), ['call-new']);
    assert.equal(state.calls[0].approvalToolUseId, 'tool-new');
  });
});


test('different workflow fingerprints cannot be consumed through another correlation', async () => {
  await withState(async (env) => {
    const envelope = parseOperationEnvelope(browserEnvelope(), NOW);
    const grant = workflowApprovalProof();
    writePendingOperation(envelope, grant, env, NOW);
    assert.equal(bindingStore.consumeOwnedOperation({
      ...ownedCorrelation(envelope, grant), invocationFingerprint: 'b'.repeat(64),
    }, env), false);
    assert.notEqual(readPendingOperation(envelope.sessionId, envelope.operationId, env, NOW), null);
    assert.equal(bindingStore.consumeOwnedOperation(ownedCorrelation(envelope, grant), env), true);
  });
});


test('inconsistent expiry copies are rejected even in expired state', async () => {
  await withState(async (env) => {
    const envelope = parseOperationEnvelope(browserEnvelope(), NOW);
    writePendingOperation(envelope, proof(), env, NOW);
    const { target, state } = await rawState(env);
    state.pending[0].expiresAt += 1;
    await writeFile(target, JSON.stringify(state));
    assert.throws(() => readPendingOperation(envelope.sessionId, envelope.operationId, env, NOW),
      /INVALID_BROWSER_STATE/u);
    assert.throws(() => bindingStore.consumeOwnedOperation(ownedCorrelation(envelope), env),
      /APPROVAL_BINDING_INVALID/u);
  });
});


test('untagged legacy calls prevent a falsely complete cleanup or deletion of newer authority', async () => {
  await withState(async (env) => {
    const envelope = parseOperationEnvelope(browserEnvelope(), NOW);
    writePendingOperation(envelope, proof(), env, NOW);
    activateOperation(ownedCorrelation(envelope), env, NOW + 1);
    stageBrowserCall(envelope.sessionId, envelope.operationId, {
      toolUseId: 'call-legacy', action: 'inspect', effect: 'SENSITIVE_READ',
    }, env, NOW + 2);
    const { target, state } = await rawState(env);
    delete state.calls[0].approvalToolUseId;
    await writeFile(target, JSON.stringify(state));
    writePendingOperation(envelope, proof({ toolUseId: 'tool-new' }), env, NOW + 3);
    assert.equal(bindingStore.consumeOwnedOperation(ownedCorrelation(envelope), env), false);
    assert.equal(readPendingOperation(envelope.sessionId, envelope.operationId, env, NOW + 4).toolUseId, 'tool-new');
    assert.equal((await rawState(env)).state.calls.length, 1);
  });
});


test('malformed or linked cleanup state cannot consume protected targets', async () => {
  await withState(async (env) => {
    const envelope = parseOperationEnvelope(browserEnvelope(), NOW);
    writePendingOperation(envelope, proof(), env, NOW);
    const { target } = await rawState(env);
    await writeFile(target, '{');
    assert.throws(() => bindingStore.consumeOwnedOperation(ownedCorrelation(envelope), env), /APPROVAL_BINDING_INVALID/u);
    if (process.platform !== 'win32') {
      const protectedTarget = path.join(env.OPS_BROWSER_STATE_DIR, 'protected');
      await writeFile(protectedTarget, 'unchanged');
      await rm(target);
      await symlink(protectedTarget, target);
      assert.throws(() => bindingStore.consumeOwnedOperation(ownedCorrelation(envelope), env), /APPROVAL_BINDING_INVALID/u);
      assert.equal(await readFile(protectedTarget, 'utf8'), 'unchanged');
    }
  });
});


test('a call with the same approval ID but a different deadline prevents idempotent success', async () => {
  await withState(async (env) => {
    const envelope = parseOperationEnvelope(browserEnvelope(), NOW);
    writePendingOperation(envelope, proof(), env, NOW);
    activateOperation(ownedCorrelation(envelope), env, NOW + 1);
    stageBrowserCall(envelope.sessionId, envelope.operationId, {
      toolUseId: 'call-ambiguous', action: 'inspect', effect: 'SENSITIVE_READ',
    }, env, NOW + 2);
    const { target, state } = await rawState(env);
    state.active = [];
    state.calls[0].expiresAt += 1;
    await writeFile(target, JSON.stringify(state));
    assert.equal(bindingStore.consumeOwnedOperation(ownedCorrelation(envelope), env), false);
    assert.equal((await rawState(env)).state.calls.length, 1);
  });
});


test('malformed cleanup correlations fail closed without changing the grant', async () => {
  await withState(async (env) => {
    const envelope = parseOperationEnvelope(browserEnvelope(), NOW);
    writePendingOperation(envelope, proof(), env, NOW);
    for (const changes of [{ toolUseId: null }, { expiresAt: '1000' },
      { invocationFingerprint: undefined }, { invocationFingerprint: 'invalid' }]) {
      assert.throws(() => bindingStore.consumeOwnedOperation({
        ...ownedCorrelation(envelope), ...changes,
      }, env), /APPROVAL_BINDING_INVALID/u);
      assert.notEqual(readPendingOperation(envelope.sessionId, envelope.operationId, env, NOW), null);
    }
  });
});


test('failed atomic cleanup writes cannot report consumption or reveal the thrown detail', async (context) => {
  await withState(async (env) => {
    const envelope = parseOperationEnvelope(browserEnvelope(), NOW);
    writePendingOperation(envelope, proof(), env, NOW);
    const rename = context.mock.method(fs, 'renameSync', () => { throw new Error('private filesystem detail'); });
    syncBuiltinESMExports();
    try {
      assert.throws(() => bindingStore.consumeOwnedOperation(ownedCorrelation(envelope), env),
        (error) => error.message === 'APPROVAL_BINDING_INVALID');
    } finally {
      rename.mock.restore();
      syncBuiltinESMExports();
    }
    assert.notEqual(readPendingOperation(envelope.sessionId, envelope.operationId, env, NOW), null);
  });
});
