import assert from 'node:assert/strict';
import test from 'node:test';

import { analyzeCommand } from '../../skills/command-driven-operations/scripts/command-guard/policy.mjs';
import { parseHookEvent } from '../../skills/command-driven-operations/scripts/command-guard/contract.mjs';
import { validEvent } from './helpers.mjs';

function analyze(command, permissionMode = 'default') {
  return analyzeCommand(parseHookEvent(JSON.stringify(validEvent({
    permission_mode: permissionMode,
    tool_input: { command },
  }))));
}

test('narrow read and bounded read pipeline allow in normal mode', () => {
  assert.equal(analyze('uname -a').decision, 'allow');
  assert.equal(analyze('journalctl -u nginx -n 20 | grep error | head -n 5').decision, 'allow');
});

test('catalogued change asks normally and allows in bypassPermissions', () => {
  assert.equal(analyze('systemctl restart nginx').decision, 'ask');
  assert.equal(analyze('systemctl restart nginx', 'bypassPermissions').decision, 'allow');
});

test('destructive action asks in every permission mode', () => {
  const command = 'kubectl --context lab --namespace demo delete pod demo-0';
  assert.equal(analyze(command).decision, 'ask');
  assert.equal(analyze(command, 'bypassPermissions').decision, 'ask');
});

test('unknown, unsupported, and ambiguous mutations deny', () => {
  assert.equal(analyze('mysteryctl deploy production').decision, 'deny');
  assert.equal(analyze('kubectl scale deployment api --replicas 0').reasonCode, 'DENY_AMBIGUOUS_TARGET');
  assert.equal(analyze('echo ok > /tmp/result').decision, 'deny');
});

test('unknown future mode uses conservative normal semantics', () => {
  const result = analyze('systemctl restart nginx', 'futureAutonomy');
  assert.equal(result.decision, 'ask');
  assert.ok(result.modifiers.includes('UNKNOWN_MODE_CONSERVATIVE'));
});

test('explicit literal PowerShell read pipeline is analyzed separately', () => {
  const command = `pwsh -NoProfile -Command "Get-Service | Where-Object Status -eq 'Running'"`;
  assert.equal(analyze(command).decision, 'allow');
});

