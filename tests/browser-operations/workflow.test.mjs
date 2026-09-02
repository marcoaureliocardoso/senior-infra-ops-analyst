import assert from 'node:assert/strict';
import test from 'node:test';

import {
  BrowserWorkflowError, decodeWorkflowStep, parseWorkflowSteps, workflowFingerprint,
} from '../../skills/browser-operations/scripts/browser-workflow.mjs';


const NAVIGATE = 'eyJzdGVwIjoibmF2aWdhdGUiLCJvcmlnaW4iOiJodHRwOi8vMTI3LjAuMC4xOjQzMTExIn0';
const FILL = 'eyJzdGVwIjoiZmlsbCIsIm9yaWdpbiI6Imh0dHA6Ly8xMjcuMC4wLjE6NDMxMTEiLCJsb2NhdG9yUm9sZSI6InRleHRib3giLCJsb2NhdG9yTmFtZSI6IlBhc3N3b3JkIiwidmFsdWVSZWYiOiJlbnY6T1BTX0JST1dTRVJfVkFMVUVfUEFTU1dPUkQifQ';
const SUBMIT = 'eyJzdGVwIjoic3VibWl0Iiwib3JpZ2luIjoiaHR0cDovLzEyNy4wLjAuMTo0MzExMSIsImxvY2F0b3JSb2xlIjoiYnV0dG9uIiwibG9jYXRvck5hbWUiOiJTYXZlIiwiZWZmZWN0IjoiTE9XX1JJU0tfQ0hBTkdFIn0';
const INSPECT = 'eyJzdGVwIjoiaW5zcGVjdCIsIm9yaWdpbiI6Imh0dHA6Ly8xMjcuMC4wLjE6NDMxMTEiLCJsb2NhdG9yUm9sZSI6InN0YXR1cyIsImxvY2F0b3JOYW1lIjoiU2F2ZWQgc3RhdGUiLCJwcmVkaWNhdGUiOiJ0ZXh0LWVxdWFscyIsImV4cGVjdGVkUmVmIjoiZW52Ok9QU19CUk9XU0VSX1ZBTFVFX0VYUEVDVEVEIiwiZXhwZWN0UmVmIjoiaW50ZXJmYWNlLXN0YXRlIn0';


function token(value) {
  return Buffer.from(JSON.stringify(value), 'utf8').toString('base64url');
}


function expectsWorkflowError(callback, code) {
  assert.throws(callback, (error) => error instanceof BrowserWorkflowError && error.code === code);
}


test('decodes a canonical non-secret step into a frozen null-prototype record', () => {
  const step = decodeWorkflowStep(NAVIGATE);
  assert.equal(Object.getPrototypeOf(step), null);
  assert.deepEqual({ ...step }, {
    step: 'navigate', origin: 'http://127.0.0.1:43111',
  });
  assert.equal(Object.isFrozen(step), true);
});


test('parses bounded ordered execution and validation step sequences', () => {
  const workflow = parseWorkflowSteps([NAVIGATE, FILL, SUBMIT], [INSPECT]);
  assert.deepEqual(workflow.executionSteps.map((step) => step.step), ['navigate', 'fill', 'submit']);
  assert.deepEqual(workflow.validationSteps.map((step) => step.step), ['inspect']);
  assert.equal(Object.isFrozen(workflow), true);
  assert.equal(Object.isFrozen(workflow.executionSteps), true);
  assert.equal(Object.isFrozen(workflow.validationSteps[0]), true);
});


test('rejects non-canonical, oversized, malformed, and duplicate-key encoded records', () => {
  const duplicateStep = Buffer.from('{"step":"navigate","step":"fill","origin":"http://127.0.0.1:43111"}').toString('base64url');
  for (const [value, code] of [
    [`${NAVIGATE}=`, 'NON_CANONICAL_TOKEN'],
    ['not base64url', 'INVALID_TOKEN'],
    ['__8', 'INVALID_UTF8'],
    ['a'.repeat(2049), 'TOKEN_TOO_LARGE'],
    [duplicateStep, 'DUPLICATE_JSON_KEY'],
    [token({ step: 'navigate', origin: 'http://127.0.0.1:43111', nested: { denied: true } }), 'UNKNOWN_STEP_FIELD'],
  ]) expectsWorkflowError(() => decodeWorkflowStep(value), code);
});


test('rejects action escape hatches, secret literals, unsafe origins, and unapproved references', () => {
  const rejected = [
    { value: { step: 'validate', expectRef: 'interface-state' }, code: 'INVALID_EXECUTION_STEP' },
    { value: { step: 'close' }, code: 'INVALID_EXECUTION_STEP' },
    { value: { step: 'fill', origin: 'http://127.0.0.1:43111', locatorRole: 'textbox', value: 'not-a-reference' }, code: 'UNKNOWN_STEP_FIELD' },
    { value: { step: 'fill', origin: 'http://127.0.0.1:43111', locatorRole: ['textbox'], valueRef: 'env:OPS_BROWSER_VALUE_PASSWORD' }, code: 'INVALID_STEP_FIELD' },
    { value: { step: 'navigate', origin: 'javascript:alert(1)' }, code: 'INVALID_ORIGIN' },
    { value: { step: 'navigate', origin: 'data:text/plain,nope' }, code: 'INVALID_ORIGIN' },
    { value: { step: 'fill', origin: 'http://127.0.0.1:43111', locatorRole: 'textbox', valueRef: 'env:OTHER_VALUE' }, code: 'INVALID_PROTECTED_REFERENCE' },
    { value: { step: 'inspect', origin: 'http://127.0.0.1:43111', locatorRole: 'status', predicate: 'text-equals', expectedRef: 'env:OTHER_VALUE', expectRef: 'interface-state' }, code: 'INVALID_PROTECTED_REFERENCE' },
  ];
  for (const { value, code } of rejected) expectsWorkflowError(() => parseWorkflowSteps([token(value)], [INSPECT]), code);
});


test('rejects invalid validation actions and requires one final inspect', () => {
  const interactiveClick = token({
    step: 'click', origin: 'http://127.0.0.1:43111', locatorRole: 'button', effect: 'INTERACTIVE_STATE',
  });
  const mutatingClick = token({
    step: 'click', origin: 'http://127.0.0.1:43111', locatorRole: 'button', effect: 'LOW_RISK_CHANGE',
  });
  expectsWorkflowError(() => parseWorkflowSteps([NAVIGATE], [mutatingClick, INSPECT]), 'INVALID_VALIDATION_EFFECT');
  expectsWorkflowError(() => parseWorkflowSteps([NAVIGATE], [SUBMIT, INSPECT]), 'INVALID_VALIDATION_STEP');
  expectsWorkflowError(() => parseWorkflowSteps([NAVIGATE], [INSPECT, interactiveClick]), 'MISSING_FINAL_INSPECT');
  expectsWorkflowError(() => parseWorkflowSteps([NAVIGATE], [INSPECT, INSPECT]), 'INVALID_VALIDATION_INSPECT');
  expectsWorkflowError(() => parseWorkflowSteps([], [INSPECT]), 'INVALID_EXECUTION_COUNT');
  expectsWorkflowError(() => parseWorkflowSteps(Array(17).fill(NAVIGATE), [INSPECT]), 'INVALID_EXECUTION_COUNT');
  expectsWorkflowError(() => parseWorkflowSteps([NAVIGATE], []), 'INVALID_VALIDATION_COUNT');
  expectsWorkflowError(() => parseWorkflowSteps([NAVIGATE], Array(13).fill(INSPECT)), 'INVALID_VALIDATION_COUNT');
});


test('fingerprints the exact normalized envelope and ordered step sequences', () => {
  const request = {
    envelope: { operationId: 'op-1', serviceOrigins: ['http://127.0.0.1:43111'] },
    ...parseWorkflowSteps([NAVIGATE, FILL, SUBMIT], [INSPECT]),
  };
  const stable = workflowFingerprint(request);
  assert.match(stable, /^[a-f0-9]{64}$/u);
  assert.equal(workflowFingerprint({ ...request }), stable);
  assert.notEqual(workflowFingerprint({ ...request, executionSteps: [...request.executionSteps].reverse() }), stable);
  assert.notEqual(workflowFingerprint({
    ...request,
    validationSteps: [{ ...request.validationSteps[0], expectRef: 'other-interface-state' }],
  }), stable);
});
