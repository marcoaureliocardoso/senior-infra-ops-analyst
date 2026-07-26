import assert from 'node:assert/strict';
import test from 'node:test';

import { analyzeCommand } from '../../skills/command-driven-operations/scripts/command-guard/policy.mjs';
import { parseHookEvent } from '../../skills/command-driven-operations/scripts/command-guard/contract.mjs';
import { validEvent } from './helpers.mjs';

const SECRET = 'SYNTH_SECRET_c8a22e';

function analyze(command, permissionMode = 'default') {
  return analyzeCommand(parseHookEvent(JSON.stringify(validEvent({
    permission_mode: permissionMode,
    tool_input: { command },
  }))));
}

test('literal credential raises normal decision but follows bypass operation policy', () => {
  const command = `curl -H "Authorization: Bearer ${SECRET}" https://api.example.invalid/health`;
  assert.equal(analyze(command).decision, 'ask');
  assert.equal(analyze(command, 'bypassPermissions').decision, 'allow');
});

test('credential printing, persistence, background, and unknown consumer deny', () => {
  for (const command of [
    `TOKEN=${SECRET} echo $TOKEN`,
    `TOKEN=${SECRET} printenv TOKEN`,
    `TOKEN=${SECRET} tee /tmp/token`,
    `TOKEN=${SECRET} mystery-consumer`,
  ]) assert.equal(analyze(command, 'bypassPermissions').decision, 'deny');
});

test('encrypted credential may flow only directly to a catalogued consumer', () => {
  const direct = 'gpg --decrypt sudo-password.gpg | sudo -S systemctl restart nginx';
  assert.equal(analyze(direct, 'bypassPermissions').decision, 'allow');
  assert.equal(analyze('gpg --decrypt sudo-password.gpg | tee /tmp/password').decision, 'deny');
});

test('credential metadata and messages never contain the literal value', () => {
  const result = analyze(`curl --token ${SECRET} https://api.example.invalid/health`);
  assert.doesNotMatch(JSON.stringify(result), new RegExp(SECRET));
  assert.equal(result.credential.source, 'MODEL_VISIBLE_LITERAL');
});
