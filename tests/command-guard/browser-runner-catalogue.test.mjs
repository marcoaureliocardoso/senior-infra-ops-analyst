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
const WORKFLOW = [
  ...changed(changed(OPEN, '--step', 'workflow'), '--service-origin', 'http://127.0.0.1:43111'),
  '--action', 'navigate', '--action', 'submit',
  '--workflow-step', 'eyJzdGVwIjoibmF2aWdhdGUiLCJvcmlnaW4iOiJodHRwOi8vMTI3LjAuMC4xOjQzMTExIn0',
  '--workflow-step', 'eyJzdGVwIjoic3VibWl0Iiwib3JpZ2luIjoiaHR0cDovLzEyNy4wLjAuMTo0MzExMSIsImxvY2F0b3JSb2xlIjoiYnV0dG9uIiwiZWZmZWN0IjoiRElTUlVQVElWRV9DSEFOR0UifQ',
  '--validation-step', 'eyJzdGVwIjoiaW5zcGVjdCIsIm9yaWdpbiI6Imh0dHA6Ly8xMjcuMC4wLjE6NDMxMTEiLCJsb2NhdG9yUm9sZSI6InN0YXR1cyIsInByZWRpY2F0ZSI6InByZXNlbnQiLCJleHBlY3RlZFJlZiI6ImVudjpPUFNfQlJPV1NFUl9WQUxVRV9FWFBFQ1RFRCIsImV4cGVjdFJlZiI6ImludGVyZmFjZS1zdGF0ZSJ9',
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


function removedAll(args, flag) {
  const copy = [...args];
  for (let index = copy.lastIndexOf(flag); index >= 0; index = copy.lastIndexOf(flag)) {
    copy.splice(index, 2);
  }
  return copy;
}


function artifactOpen() {
  return changed([...OPEN,
    '--action', 'screenshot', '--action', 'trace',
    '--artifact-type', 'screenshot', '--artifact-type', 'trace',
    '--artifact-purpose-ref', 'change-evidence',
    '--artifact-source-class', 'browser-viewport', '--artifact-source-class', 'browser-trace',
    '--artifact-destination-class', 'operation-temp',
    '--artifact-max-items', '2', '--artifact-max-bytes', '4096',
    '--artifact-redaction', 'required', '--artifact-retention-seconds', '60',
  ], '--effect', 'SENSITIVE_ARTIFACT');
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
  assert.equal(lookup(artifactOpen()).risk, 'LOW_RISK_CHANGE');

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


test('browser runner catalogue decodes a workflow and takes its highest declared step effect', () => {
  const result = lookup(WORKFLOW);
  assert.equal(result.policyId, 'BROWSER_PROTECTED_RUNNER');
  assert.equal(result.risk, 'DISRUPTIVE_CHANGE');
  assert.ok(result.modifiers.includes('ALWAYS_ASK'));
  for (const args of [
    removedAll(WORKFLOW, '--workflow-step'),
    removedAll(WORKFLOW, '--validation-step'),
    [...WORKFLOW, '--unknown', 'x'],
  ]) assert.equal(lookup(args), null);
});


test('browser runner catalogue rejects every closed-grammar branch', () => {
  const oversizedPairs = Array.from({ length: 49 }, (_, index) => [`--x${index}`, 'v']).flat();
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
    ...[
      '--artifact-type', '--artifact-purpose-ref', '--artifact-source-class',
      '--artifact-destination-class', '--artifact-max-items', '--artifact-max-bytes',
      '--artifact-redaction', '--artifact-retention-seconds',
    ].map((flag) => removedAll(artifactOpen(), flag)),
    changed(artifactOpen(), '--effect', 'LOW_RISK_CHANGE'),
    changed(artifactOpen(), '--artifact-type', 'cookie'),
    changed(artifactOpen(), '--artifact-type', 'download'),
    changed(artifactOpen(), '--artifact-source-class', 'Invalid_Class'),
    changed(artifactOpen(), '--artifact-destination-class', 'Invalid_Class'),
    changed(artifactOpen(), '--artifact-purpose-ref', 'bad value'),
    changed(artifactOpen(), '--artifact-max-items', '0'),
    changed(artifactOpen(), '--artifact-max-items', '17'),
    changed(artifactOpen(), '--artifact-max-bytes', '0'),
    changed(artifactOpen(), '--artifact-max-bytes', '50000001'),
    changed(artifactOpen(), '--artifact-redaction', 'none'),
    changed(artifactOpen(), '--artifact-retention-seconds', '0'),
    changed(artifactOpen(), '--artifact-retention-seconds', '3601'),
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
