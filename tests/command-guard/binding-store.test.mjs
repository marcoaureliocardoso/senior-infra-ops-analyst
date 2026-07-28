import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdir, mkdtemp, readFile, readdir, rm, stat, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { Readable, Writable } from 'node:stream';
import test from 'node:test';

import {
  activatePendingBinding,
  bindingFromResult,
  hasActiveBinding,
  resolveBindingStateDirectory,
  writePendingBinding,
} from '../../skills/command-driven-operations/scripts/command-guard/binding-store.mjs';
import { evaluateApprovalHook, main as approvalMain } from '../../skills/command-driven-operations/scripts/record-command-approval.mjs';
import { evaluateHook } from '../../skills/command-driven-operations/scripts/validate-ops-command.mjs';
import { validEvent } from './helpers.mjs';

const NOW = 1_800_000_000_000;
const binding = Object.freeze({
  sessionId: 'session-binding-1',
  toolUseId: 'tool-use-1',
  domain: 'https://api.example.invalid',
  identity: 'deployment-operator',
  transport: 'AUTHORIZATION',
  family: 'HTTP',
  targetClass: 'HTTP',
});

async function withState(run) {
  const directory = await mkdtemp(path.join(os.tmpdir(), 'ops-binding-'));
  try {
    await run({ OPS_COMMAND_GUARD_STATE_DIR: directory });
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
}

test('pending binding activates only after a matching successful post event', async () => {
  await withState(async (env) => {
    assert.equal(writePendingBinding(binding, env, NOW), true);
    assert.equal(hasActiveBinding(binding, env, NOW), false);
    assert.equal(activatePendingBinding(binding, env, NOW + 1), true);
    assert.equal(hasActiveBinding(binding, env, NOW + 2), true);
    assert.equal(activatePendingBinding(binding, env, NOW + 3), false);
  });
});

test('binding rejects changed domain identity transport session and expiry', async () => {
  await withState(async (env) => {
    writePendingBinding(binding, env, NOW);
    activatePendingBinding(binding, env, NOW + 1);
    for (const changed of [
      { ...binding, sessionId: 'other-session' },
      { ...binding, domain: 'https://other.example.invalid' },
      { ...binding, identity: 'other-operator' },
      { ...binding, transport: 'COOKIE' },
    ]) assert.equal(hasActiveBinding(changed, env, NOW + 2), false);
    assert.equal(hasActiveBinding(binding, env, NOW + 900_001), false);
  });
});

test('state is owner-only bounded atomic and contains no command or secret', async () => {
  await withState(async (env) => {
    writePendingBinding(binding, env, NOW);
    const entries = await import('node:fs/promises').then(({ readdir }) => readdir(env.OPS_COMMAND_GUARD_STATE_DIR));
    assert.equal(entries.length, 1);
    const statePath = path.join(env.OPS_COMMAND_GUARD_STATE_DIR, entries[0]);
    const contents = await readFile(statePath, 'utf8');
    assert.doesNotMatch(contents, /"(?:command|password|secret|token|authorization)"\s*:/iu);
    if (process.platform !== 'win32') {
      assert.equal((await stat(env.OPS_COMMAND_GUARD_STATE_DIR)).mode & 0o777, 0o700);
      assert.equal((await stat(statePath)).mode & 0o777, 0o600);
    }
  });
});

test('PostToolUse entrypoint activates only exact Bash success metadata', async () => {
  await withState(async (env) => {
    writePendingBinding(binding, env, NOW);
    const raw = JSON.stringify({
      session_id: binding.sessionId,
      tool_use_id: binding.toolUseId,
      hook_event_name: 'PostToolUse',
      tool_name: 'Bash',
    });
    assert.equal(evaluateApprovalHook(raw, env, NOW + 1), true);
    assert.equal(hasActiveBinding(binding, env, NOW + 2), true);
    for (const changed of [
      { ...JSON.parse(raw), hook_event_name: 'PostToolUseFailure' },
      { ...JSON.parse(raw), tool_name: 'Read' },
    ]) assert.throws(() => evaluateApprovalHook(JSON.stringify(changed), env, NOW + 3));
    assert.equal(evaluateApprovalHook(JSON.stringify({ ...JSON.parse(raw), tool_use_id: 'other' }), env, NOW + 3), false);
  });
});

test('PostToolUse is a silent no-op when a successful Bash call has no pending binding', async () => {
  await withState(async (env) => {
    const raw = JSON.stringify({
      session_id: 'ordinary-session', tool_use_id: 'ordinary-tool',
      hook_event_name: 'PostToolUse', tool_name: 'Bash',
    });
    assert.equal(evaluateApprovalHook(raw, env, NOW), false);
    let errorText = '';
    const error = new Writable({ write(chunk, encoding, callback) { errorText += chunk.toString(); callback(); } });
    assert.equal(await approvalMain({ input: Readable.from([raw]), error, env }), 0);
    assert.equal(errorText, '');
  });
});

test('PreToolUse asks first then reuses only the approved non-secret binding', async () => {
  await withState(async (env) => {
    const auditPath = path.join(env.OPS_COMMAND_GUARD_STATE_DIR, 'audit.jsonl');
    const command = 'OPS_CREDENTIAL_IDENTITY=deployment-operator curl -H "Authorization: Bearer SYNTH_SECRET_binding_a" https://api.example.invalid/health';
    const first = validEvent({
      tool_use_id: 'tool-first', permission_mode: 'bypassPermissions', tool_input: { command },
    });
    const firstResponse = evaluateHook(JSON.stringify(first), { ...env, OPS_COMMAND_GUARD_AUDIT_PATH: auditPath });
    assert.equal(firstResponse.hookSpecificOutput.permissionDecision, 'ask');
    assert.equal(evaluateApprovalHook(JSON.stringify({
      session_id: first.session_id, tool_use_id: first.tool_use_id,
      hook_event_name: 'PostToolUse', tool_name: 'Bash',
    }), env), true);

    const second = validEvent({
      tool_use_id: 'tool-second', permission_mode: 'bypassPermissions',
      tool_input: { command: command.replace('binding_a', 'binding_b') },
    });
    const secondResponse = evaluateHook(JSON.stringify(second), { ...env, OPS_COMMAND_GUARD_AUDIT_PATH: auditPath });
    assert.equal(secondResponse.hookSpecificOutput.permissionDecision, 'allow');

    const changed = validEvent({
      tool_use_id: 'tool-third', permission_mode: 'bypassPermissions',
      tool_input: { command: command.replace('api.example.invalid', 'other.example.invalid') },
    });
    const changedResponse = evaluateHook(JSON.stringify(changed), { ...env, OPS_COMMAND_GUARD_AUDIT_PATH: auditPath });
    assert.equal(changedResponse.hookSpecificOutput.permissionDecision, 'ask');
  });
});

test('approved Authorization binding cannot be reused as another credential transport', async () => {
  await withState(async (env) => {
    const auditPath = path.join(env.OPS_COMMAND_GUARD_STATE_DIR, 'audit.jsonl');
    const first = validEvent({
      tool_use_id: 'tool-authorization', permission_mode: 'bypassPermissions',
      tool_input: {
        command: 'OPS_CREDENTIAL_IDENTITY=deployment-operator curl -H "Authorization: Bearer SYNTH_SECRET_auth" https://api.example.invalid/health',
      },
    });
    const firstResponse = evaluateHook(JSON.stringify(first), { ...env, OPS_COMMAND_GUARD_AUDIT_PATH: auditPath });
    assert.equal(firstResponse.hookSpecificOutput.permissionDecision, 'ask');
    assert.equal(evaluateApprovalHook(JSON.stringify({
      session_id: first.session_id, tool_use_id: first.tool_use_id,
      hook_event_name: 'PostToolUse', tool_name: 'Bash',
    }), env), true);

    for (const [toolUseId, command] of [
      ['tool-cookie', 'OPS_CREDENTIAL_IDENTITY=deployment-operator curl -H "Cookie: session=SYNTH_SECRET_cookie" https://api.example.invalid/health'],
      ['tool-basic', 'OPS_CREDENTIAL_IDENTITY=deployment-operator curl -u user:SYNTH_SECRET_basic https://api.example.invalid/health'],
    ]) {
      const changed = validEvent({
        tool_use_id: toolUseId, permission_mode: 'bypassPermissions', tool_input: { command },
      });
      const response = evaluateHook(JSON.stringify(changed), { ...env, OPS_COMMAND_GUARD_AUDIT_PATH: auditPath });
      assert.equal(response.hookSpecificOutput.permissionDecision, 'ask', command);
    }
  });
});

test('binding input state and storage bounds fail closed', async () => {
  assert.match(resolveBindingStateDirectory({}), /command-guard-state/u);
  for (const value of [undefined, '', 'x'.repeat(513)]) {
    assert.throws(() => writePendingBinding({ ...binding, identity: value }, {}, NOW), /invalid binding field/u);
  }
  await withState(async (env) => {
    writePendingBinding(binding, env, NOW);
    const [name] = await readdir(env.OPS_COMMAND_GUARD_STATE_DIR);
    const statePath = path.join(env.OPS_COMMAND_GUARD_STATE_DIR, name);
    for (const invalid of [
      '{}',
      '{"version":1,"pending":{},"active":[]}',
      JSON.stringify({ version: 1, pending: [{ ...binding, expiresAt: 0 }], active: [] }),
      JSON.stringify({ version: 1, pending: Array(17).fill({ ...binding, expiresAt: NOW + 1 }), active: [] }),
    ]) {
      await writeFile(statePath, invalid, 'utf8');
      assert.throws(() => hasActiveBinding(binding, env, NOW), /binding/u);
    }
    await rm(statePath, { force: true });
    await mkdir(statePath);
    assert.throws(() => hasActiveBinding(binding, env, NOW), /unsafe binding state file/u);
    await rm(statePath, { recursive: true, force: true });
    await writeFile(statePath, 'x'.repeat(33 * 1024), 'utf8');
    assert.throws(() => hasActiveBinding(binding, env, NOW), /unsafe binding state file/u);
  });
  const parent = await mkdtemp(path.join(os.tmpdir(), 'ops-binding-notdir-'));
  try {
    const notDirectory = path.join(parent, 'file');
    await writeFile(notDirectory, 'x', 'utf8');
    assert.equal(hasActiveBinding(binding, { OPS_COMMAND_GUARD_STATE_DIR: notDirectory }, NOW), false);
  } finally { await rm(parent, { recursive: true, force: true }); }
});

test('binding store bounds pending and active entries', async () => {
  await withState(async (env) => {
    for (let index = 0; index < 17; index += 1) {
      writePendingBinding({ ...binding, toolUseId: `pending-${index}`, identity: `pending-${index}` }, env, NOW + index);
    }
    writePendingBinding({ ...binding, toolUseId: 'pending-16', identity: 'pending-16' }, env, NOW + 20);
    for (let index = 0; index < 17; index += 1) {
      const item = { ...binding, toolUseId: `tool-${index}`, identity: `identity-${index}` };
      writePendingBinding(item, env, NOW + index);
      activatePendingBinding(item, env, NOW + index + 1);
    }
    assert.equal(hasActiveBinding({ ...binding, toolUseId: 'new', identity: 'identity-0' }, env, NOW + 100), false);
    assert.equal(hasActiveBinding({ ...binding, toolUseId: 'new', identity: 'identity-16' }, env, NOW + 100), true);
  });
});

test('binding serialized byte limit blocks oversized non-secret state', async () => {
  await withState(async (env) => {
    const large = 'x'.repeat(500);
    let blocked = false;
    for (let index = 0; index < 16; index += 1) {
      try {
        writePendingBinding({
          sessionId: large, toolUseId: `${index}-${large}`, domain: large,
          identity: `${index}-${large}`, transport: large, family: large, targetClass: large,
        }, env, NOW + index);
      } catch (error) {
        assert.match(error.message, /state size exceeded/u);
        blocked = true;
        break;
      }
    }
    assert.equal(blocked, true);
  });
});

test('binding derivation requires literal tool identity domain family and explicit principal', () => {
  const result = {
    credential: { literal: true, transport: 'AUTHORIZATION' },
    environment: 'https://api.example.invalid', policyId: 'HTTP',
  };
  const event = {
    sessionId: 's', toolUseId: 't',
    command: 'OPS_CREDENTIAL_IDENTITY=operator curl https://api.example.invalid',
  };
  assert.equal(bindingFromResult({ ...result, credential: null }, event), null);
  assert.equal(bindingFromResult(result, { ...event, toolUseId: null }), null);
  assert.equal(bindingFromResult({ ...result, environment: null }, event), null);
  assert.equal(bindingFromResult({ ...result, policyId: null }, event), null);
  assert.equal(bindingFromResult(result, { ...event, command: 'curl https://api.example.invalid' }), null);
  assert.equal(bindingFromResult(result, event).identity, 'operator');
  assert.equal(bindingFromResult(result, { ...event, command: 'curl https://user:synthetic@api.example.invalid' }).identity, 'user');
});

test('PostToolUse stream main handles chunking invalid input and size limits', async () => {
  await withState(async (env) => {
    writePendingBinding(binding, env, NOW);
    const raw = JSON.stringify({
      session_id: binding.sessionId, tool_use_id: binding.toolUseId,
      hook_event_name: 'PostToolUse', tool_name: 'Bash',
    });
    let errorText = '';
    const error = new Writable({ write(chunk, encoding, callback) { errorText += chunk.toString(); callback(); } });
    assert.equal(await approvalMain({ input: Readable.from([raw.slice(0, 5), Buffer.from(raw.slice(5))]), error, env }), 0);
    assert.equal(errorText, '');
    assert.equal(await approvalMain({ input: Readable.from(['{']), error, env }), 2);
    assert.match(errorText, /did not activate/u);
    assert.equal(await approvalMain({ input: Readable.from(['x'.repeat(2_000_000)]), error, env }), 2);
  });
});

test('PostToolUse executable entrypoint fails closed on invalid input', () => {
  const entrypoint = path.resolve('skills/command-driven-operations/scripts/record-command-approval.mjs');
  const result = spawnSync(process.execPath, [entrypoint], { input: '{', encoding: 'utf8' });
  assert.equal(result.status, 2);
  assert.equal(result.stdout, '');
  assert.match(result.stderr, /did not activate/u);
});

test('PostToolUse contract rejects malformed scalar and missing identifiers', () => {
  for (const value of [
    null, [], 'text',
    { hook_event_name: 'PostToolUse', tool_name: 'Bash', session_id: '', tool_use_id: 't' },
    { hook_event_name: 'PostToolUse', tool_name: 'Bash', session_id: 's', tool_use_id: '' },
  ]) assert.throws(() => evaluateApprovalHook(JSON.stringify(value), {}, NOW));
  assert.throws(() => evaluateApprovalHook(null, {}, NOW), /input exceeds/u);
  assert.throws(() => evaluateApprovalHook('x'.repeat(2_000_000), {}, NOW), /input exceeds/u);
});
