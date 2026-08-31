import assert from 'node:assert/strict';
import path from 'node:path';
import test from 'node:test';

import { lookupFamily } from '../../skills/command-driven-operations/scripts/command-guard/catalogue.mjs';


const runner = path.resolve('skills/browser-operations/scripts/browser-runner.mjs');
const lookup = (args, executable = 'node', runnerPath = runner) =>
  lookupFamily({ argv: [executable, runnerPath, ...args] });
const OPEN = [
  '--step', 'open', '--operation-id', 'op-matrix', '--session-id', 'session-matrix',
  '--role', 'network-edge-operator', '--objective-ref', 'change-42', '--target', 'router-1',
  '--environment', 'production', '--service-origin', 'https://router.example.invalid',
  '--auth-origin', 'http://login.example.invalid:8080', '--identity-ref', 'vault:network-admin',
  '--credential-transport', 'vault', '--permission-mode', 'normal', '--action', 'inspect',
  '--action', 'validate', '--modifier', 'PRIVILEGED', '--effect', 'LOW_RISK_CHANGE',
  '--risk', 'LOW_RISK_CHANGE', '--precondition-ref', 'reachable',
  '--validation-ref', 'interface-state', '--compensation-ref', 'restore-interface',
  '--expires-in-seconds', '600',
];


function changed(args, flag, value) {
  const copy = [...args];
  const index = copy.indexOf(flag);
  if (index < 0) return [...copy, flag, value];
  copy[index + 1] = value;
  return copy;
}


function removed(args, flag) {
  const copy = [...args];
  const index = copy.indexOf(flag);
  if (index >= 0) copy.splice(index, 2);
  return copy;
}


test('browser runner catalogue classifies every effect risk and semantic step', () => {
  for (const [effect, expectedRisk] of [
    ['PUBLIC_READ', 'SAFE_READ_ONLY'], ['SENSITIVE_READ', 'SAFE_READ_ONLY'],
    ['INTERACTIVE_STATE', 'LOW_RISK_CHANGE'], ['LOW_RISK_CHANGE', 'LOW_RISK_CHANGE'],
    ['DISRUPTIVE_CHANGE', 'DISRUPTIVE_CHANGE'], ['DESTRUCTIVE_CHANGE', 'DESTRUCTIVE'],
    ['SENSITIVE_ARTIFACT', 'LOW_RISK_CHANGE'],
  ]) {
    const result = lookup(changed(changed(OPEN, '--effect', effect), '--risk', 'safe'));
    assert.equal(result.risk, expectedRisk, effect);
  }
  for (const [alias, expected] of [
    ['low', 'LOW_RISK_CHANGE'], ['medium', 'DISRUPTIVE_CHANGE'], ['high', 'DESTRUCTIVE'],
  ]) assert.equal(lookup(changed(OPEN, '--risk', alias)).risk, expected, alias);
  const auditOpen = changed(
    changed(changed(OPEN, '--role', 'audit-evidence-collector'), '--effect', 'SENSITIVE_READ'),
    '--risk', 'safe',
  );
  assert.equal(lookup(auditOpen).risk, 'SAFE_READ_ONLY');

  const steps = [
    ['inspect', ['--origin', 'https://router.example.invalid', '--locator-role', 'status', '--locator-name', 'Status', '--expect-ref', 'readable'], 'SAFE_READ_ONLY'],
    ['navigate', ['--origin', 'http://router.example.invalid'], 'LOW_RISK_CHANGE'],
    ['fill', ['--origin', 'https://router.example.invalid', '--locator-role', 'textbox', '--locator-name', 'Name', '--value-ref', 'vault:value'], 'LOW_RISK_CHANGE'],
    ['select', ['--origin', 'https://router.example.invalid', '--locator-role', 'combobox', '--locator-name', 'Mode', '--value-ref', 'vault:value'], 'LOW_RISK_CHANGE'],
    ['click', ['--origin', 'https://router.example.invalid', '--locator-role', 'button', '--locator-name', 'Apply', '--effect', 'DISRUPTIVE_CHANGE'], 'DISRUPTIVE_CHANGE'],
    ['submit', ['--origin', 'https://router.example.invalid', '--locator-role', 'form', '--locator-name', 'Settings', '--effect', 'DESTRUCTIVE_CHANGE'], 'DESTRUCTIVE'],
    ['upload', ['--origin', 'https://router.example.invalid', '--artifact-ref', 'artifact-1'], 'LOW_RISK_CHANGE'],
    ['download', ['--origin', 'https://router.example.invalid', '--artifact-ref', 'artifact-1'], 'LOW_RISK_CHANGE'],
    ['screenshot', ['--origin', 'https://router.example.invalid', '--artifact-ref', 'artifact-1'], 'LOW_RISK_CHANGE'],
    ['trace', ['--origin', 'https://router.example.invalid', '--artifact-ref', 'artifact-1'], 'LOW_RISK_CHANGE'],
    ['validate', ['--expect-ref', 'interface-state'], 'SAFE_READ_ONLY'],
    ['close', [], 'LOW_RISK_CHANGE'],
  ];
  for (const [step, extra, expectedRisk] of steps) {
    const result = lookup(['--operation-id', 'op-matrix', '--step', step, ...extra]);
    assert.equal(result.policyId, 'BROWSER_PROTECTED_RUNNER', step);
    assert.equal(result.risk, expectedRisk, step);
    assert.ok(result.modifiers.includes('ALWAYS_ASK'), step);
  }
});


test('browser runner catalogue rejects every closed-grammar branch', () => {
  const oversizedPairs = Array.from({ length: 33 }, (_, index) => [`--x${index}`, 'v']).flat();
  const invalidGeneric = [
    { args: ['--operation-id', 'op'], executable: 'nodejs' },
    { args: ['--operation-id', 'op'], runnerPath: 'relative/browser-runner.mjs' },
    { args: ['--operation-id', 'op'], runnerPath: `${runner}.copy` },
    { args: [] },
    { args: ['--step'] },
    { args: oversizedPairs },
    { args: [7, 'x', '--step', 'close'] },
    { args: ['step', 'close', '--operation-id', 'op'] },
    { args: ['--operation-id', '$OP', '--step', 'close'] },
    { args: ['--operation-id', 'x'.repeat(2049), '--step', 'close'] },
    { args: ['--operation-id', 'op', '--operation-id', 'op2', '--step', 'close'] },
    { args: ['--step', 'close'] },
    { args: ['--operation-id', 'bad value', '--step', 'close'] },
  ];
  for (const item of invalidGeneric) {
    assert.equal(lookup(item.args, item.executable, item.runnerPath), null);
  }

  const invalidOpen = [
    [...OPEN, '--unknown', 'x'],
    ...[
      '--session-id', '--role', '--objective-ref', '--target', '--environment',
      '--identity-ref', '--credential-transport', '--permission-mode', '--effect', '--risk',
      '--precondition-ref', '--validation-ref', '--compensation-ref', '--expires-in-seconds',
    ].map((flag) => removed(OPEN, flag)),
    removed(OPEN, '--service-origin'),
    removed(removed(OPEN, '--action'), '--action'),
    changed(OPEN, '--service-origin', 'https://*.example.invalid'),
    changed(OPEN, '--service-origin', 'https://routér.example.invalid'),
    changed(OPEN, '--service-origin', 'ftp://router.example.invalid'),
    changed(OPEN, '--service-origin', 'https://user:pass@router.example.invalid'),
    changed(OPEN, '--service-origin', 'https://'),
    changed(OPEN, '--service-origin', 'https://xn--ruter-qua.example.invalid'),
    changed(OPEN, '--action', 'Invalid_Action'),
    changed(OPEN, '--modifier', 'invalid'),
    changed(OPEN, '--expires-in-seconds', '0'),
    changed(OPEN, '--expires-in-seconds', '99999'),
    changed(OPEN, '--effect', 'UNKNOWN'),
    changed(OPEN, '--risk', 'unknown'),
    changed(OPEN, '--role', 'change-manager'),
    changed(OPEN, '--role', 'audit-evidence-collector'),
  ];
  for (const args of invalidOpen) assert.equal(lookup(args), null);

  const invalidSteps = [
    ['--operation-id', 'op', '--step', 'unknown'],
    ['--operation-id', 'op', '--step', 'close', '--unknown', 'x'],
    ['--operation-id', 'op', '--step', 'inspect', '--origin', 'https://router.example.invalid', '--locator-role', 'status'],
    ['--operation-id', 'op', '--step', 'close', '--origin', 'https://router.example.invalid'],
    ['--operation-id', 'op', '--step', 'navigate', '--origin', 'https://'],
    ['--operation-id', 'op', '--step', 'click', '--origin', 'https://router.example.invalid', '--locator-role', 'button', '--effect', 'UNKNOWN'],
  ];
  for (const args of invalidSteps) assert.equal(lookup(args), null);
});
