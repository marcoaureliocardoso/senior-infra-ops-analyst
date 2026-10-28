import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { copyFile, mkdtemp, mkdir, readFile, readdir, rm, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { Readable, Writable } from 'node:stream';
import test from 'node:test';

import { parseOperationEnvelope } from '../../skills/browser-operations/scripts/browser-contract.mjs';
import {
  activateOperation, readActiveOperation, writePendingOperation,
} from '../../skills/browser-operations/scripts/browser-binding-store.mjs';
import { evaluateHookEvent, main } from '../../skills/browser-operations/scripts/browser-hook.mjs';
import { browserEnvelope, capabilityFixture, NOW } from './helpers.mjs';


const BASH = process.env.BASH_PATH ?? (process.platform === 'win32' ? 'C:/Program Files/Git/bin/bash.exe' : 'bash');
const LAUNCHER = path.resolve('skills/browser-operations/scripts/browser-hook-launcher.sh');


async function seededState(run) {
  const directory = await mkdtemp(path.join(os.tmpdir(), 'browser-hook-'));
  const env = { ...process.env, OPS_BROWSER_STATE_DIR: directory };
  try {
    const envelope = parseOperationEnvelope(browserEnvelope(), NOW);
    const proof = {
      toolUseId: 'tool-open-001', adapterId: 'fixture-browser',
      routeClass: 'CONTROLLED_BROWSER_MCP', settingsFingerprint: 'settings-browser-a',
      permissionModes: ['normal', 'bypassPermissions'], capability: capabilityFixture(),
    };
    writePendingOperation(envelope, proof, env, NOW);
    activateOperation({ sessionId: envelope.sessionId, operationId: envelope.operationId, toolUseId: proof.toolUseId }, env, NOW + 1);
    await run({ env, envelope });
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
}


function hookEvent(overrides = {}) {
  return {
    session_id: 'session-browser-001',
    hook_event_name: 'PreToolUse',
    permission_mode: 'normal',
    tool_name: 'mcp__playwright__browser_snapshot',
    tool_input: {},
    tool_use_id: 'tool-browser-001',
    ...overrides,
  };
}


test('PreToolUse maps an exact call, returns one native decision, and stages correlation', async () => {
  await seededState(async ({ env, envelope }) => {
    const response = evaluateHookEvent(JSON.stringify(hookEvent()), 'pre', env, NOW + 2);
    assert.equal(response.hookSpecificOutput.hookEventName, 'PreToolUse');
    assert.equal(response.hookSpecificOutput.permissionDecision, 'ask');
    assert.match(response.hookSpecificOutput.permissionDecisionReason, /^ASK_SENSITIVE_READ$/u);
    const state = JSON.parse(await readFile((await readdir(env.OPS_BROWSER_STATE_DIR)).map((name) =>
      path.join(env.OPS_BROWSER_STATE_DIR, name))[0], 'utf8'));
    assert.equal(state.calls[0].operationId, envelope.operationId);
    assert.equal(state.calls[0].toolUseId, 'tool-browser-001');
  });
});


test('PostToolUse and PostToolUseFailure correlate exact calls without output content', async () => {
  await seededState(async ({ env, envelope }) => {
    evaluateHookEvent(JSON.stringify(hookEvent({
      tool_name: 'mcp__playwright__browser_navigate',
      tool_input: { url: 'https://router.example.invalid/status' },
    })), 'pre', env, NOW + 2);
    assert.equal(evaluateHookEvent(JSON.stringify(hookEvent({
      hook_event_name: 'PostToolUse',
      tool_name: 'mcp__playwright__browser_navigate',
      tool_input: { url: 'https://router.example.invalid/status' },
    })), 'post', env, NOW + 3), null);
    assert.equal(readActiveOperation(envelope.sessionId, envelope.operationId, env, NOW + 4).validationRequired, true);

    evaluateHookEvent(JSON.stringify(hookEvent({
      tool_use_id: 'tool-browser-002',
      tool_name: 'mcp__playwright__browser_navigate',
      tool_input: { url: 'https://router.example.invalid/status' },
    })), 'pre', env, NOW + 5);
    assert.equal(evaluateHookEvent(JSON.stringify(hookEvent({
      hook_event_name: 'PostToolUseFailure', tool_use_id: 'tool-browser-002',
      tool_name: 'mcp__playwright__browser_navigate',
      tool_input: { url: 'https://router.example.invalid/status' },
      error: 'DO_NOT_RETAIN_FAILURE_CANARY',
    })), 'failure', env, NOW + 6), null);
    assert.equal(readActiveOperation(envelope.sessionId, envelope.operationId, env, NOW + 7).outcome, 'OUTCOME_UNKNOWN');
    const contents = await Promise.all((await readdir(env.OPS_BROWSER_STATE_DIR)).map((name) =>
      readFile(path.join(env.OPS_BROWSER_STATE_DIR, name), 'utf8')));
    assert.doesNotMatch(contents.join(''), /DO_NOT_RETAIN_FAILURE_CANARY/u);
  });
});


test('unrecognized MCP tools, origin escape, malformed JSON, and oversized input fail closed', async () => {
  await seededState(async ({ env }) => {
    assert.equal(evaluateHookEvent(JSON.stringify(hookEvent({
      tool_name: 'mcp__other__browser_snapshot',
    })), 'pre', env, NOW + 2).hookSpecificOutput.permissionDecision, 'deny');
    assert.equal(evaluateHookEvent(JSON.stringify(hookEvent({
      tool_name: 'mcp__playwright__browser_navigate',
      tool_input: { url: 'https://other.example.invalid/' },
    })), 'pre', env, NOW + 2).hookSpecificOutput.permissionDecision, 'deny');
    assert.throws(() => evaluateHookEvent('{', 'pre', env, NOW + 2));
    assert.throws(() => evaluateHookEvent('x'.repeat(1_048_577), 'pre', env, NOW + 2));
  });
});


test('entrypoint emits no secret canary and failure modes are generic', async () => {
  await seededState(async ({ env }) => {
    let outputText = '';
    let errorText = '';
    const output = new Writable({ write(chunk, encoding, callback) { outputText += chunk.toString(); callback(); } });
    const error = new Writable({ write(chunk, encoding, callback) { errorText += chunk.toString(); callback(); } });
    const canary = 'DO_NOT_ECHO_BROWSER_HOOK_CANARY';
    const raw = JSON.stringify(hookEvent({
      tool_name: 'mcp__playwright__browser_type',
      tool_input: { element: 'Password', target: 'e7', text: canary, submit: false },
    }));
    assert.equal(await main({ mode: 'pre', input: Readable.from([raw]), output, error, env, now: NOW + 2 }), 0);
    assert.doesNotMatch(`${outputText}\n${errorText}`, new RegExp(canary, 'u'));

    outputText = '';
    errorText = '';
    assert.equal(await main({ mode: 'pre', input: Readable.from(['{']), output, error, env, now: NOW + 3 }), 2);
    assert.equal(outputText, '');
    assert.equal(errorText, 'Browser guard denied execution because validation failed.\n');
  });
});


test('launcher handles pre post and failure modes from a path with spaces', async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'browser launcher '));
  try {
    const scripts = path.join(root, 'scripts');
    await mkdir(scripts, { recursive: true });
    const launcher = path.join(scripts, 'browser-hook-launcher.sh');
    await copyFile(LAUNCHER, launcher);
    await writeFile(path.join(scripts, 'browser-hook.mjs'), `
const mode = process.argv[2];
if (mode === 'pre') process.stdout.write(JSON.stringify({hookSpecificOutput:{hookEventName:'PreToolUse',permissionDecision:'deny',permissionDecisionReason:'SYNTHETIC_DENY'}})+'\\n');
else if (mode !== 'post' && mode !== 'failure') process.exitCode = 2;
`, 'utf8');
    for (const mode of ['pre', 'post', 'failure']) {
      const result = spawnSync(BASH, [launcher, mode], {
        input: '{}', encoding: 'utf8', timeout: 10_000,
        env: { ...process.env, PATH: process.env.PATH },
      });
      assert.equal(result.status, 0, `${mode}:${result.stderr}`);
      if (mode === 'pre') assert.equal(JSON.parse(result.stdout).hookSpecificOutput.permissionDecision, 'deny');
      else assert.equal(result.stdout, '');
      assert.equal(result.stderr, '');
    }
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});
