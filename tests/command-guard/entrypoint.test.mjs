import assert from 'node:assert/strict';
import path from 'node:path';
import test from 'node:test';
import { spawn } from 'node:child_process';

import { temporaryAudit, validEvent } from './helpers.mjs';

const ENTRYPOINT = path.resolve('skills/command-driven-operations/scripts/validate-ops-command.mjs');

function runGuard(input, auditPath) {
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [ENTRYPOINT], {
      env: { ...process.env, OPS_COMMAND_GUARD_AUDIT_PATH: auditPath },
      stdio: ['pipe', 'pipe', 'pipe'],
    });
    let stdout = '';
    let stderr = '';
    child.stdout.setEncoding('utf8').on('data', (chunk) => { stdout += chunk; });
    child.stderr.setEncoding('utf8').on('data', (chunk) => { stderr += chunk; });
    child.on('error', reject);
    child.on('close', (code) => resolve({ code, stdout, stderr }));
    child.stdin.end(input);
  });
}

test('entrypoint emits exactly one native allow response and one audit record', async () => {
  const temporary = await temporaryAudit();
  try {
    const result = await runGuard(JSON.stringify(validEvent()), temporary.auditPath);
    assert.equal(result.code, 0);
    assert.equal(result.stderr, '');
    assert.equal(result.stdout.trim().split('\n').length, 1);
    const response = JSON.parse(result.stdout);
    assert.equal(response.hookSpecificOutput.hookEventName, 'PreToolUse');
    assert.equal(response.hookSpecificOutput.permissionDecision, 'allow');
    assert.equal((await temporary.read()).trim().split('\n').length, 1);
  } finally {
    await temporary.cleanup();
  }
});

test('entrypoint fails closed for malformed input and audit write failure', async () => {
  const temporary = await temporaryAudit();
  try {
    const malformed = await runGuard('{', temporary.auditPath);
    assert.equal(malformed.code, 2);
    assert.equal(malformed.stdout, '');
    assert.match(malformed.stderr, /denied/i);

    const auditFailure = await runGuard(JSON.stringify(validEvent()), path.dirname(temporary.auditPath));
    assert.equal(auditFailure.code, 2);
    assert.equal(auditFailure.stdout, '');
    assert.match(auditFailure.stderr, /denied/i);
  } finally {
    await temporary.cleanup();
  }
});

test('entrypoint never emits or audits a model-visible credential', async () => {
  const temporary = await temporaryAudit();
  const secret = 'SYNTH_SECRET_entrypoint_901a';
  try {
    const event = validEvent({
      permission_mode: 'bypassPermissions',
      tool_input: { command: `curl -H "Authorization: Bearer ${secret}" https://api.example.invalid/health` },
    });
    const result = await runGuard(JSON.stringify(event), temporary.auditPath);
    assert.equal(result.code, 0);
    assert.doesNotMatch(`${result.stdout}${result.stderr}${await temporary.read()}`, new RegExp(secret));
  } finally {
    await temporary.cleanup();
  }
});
