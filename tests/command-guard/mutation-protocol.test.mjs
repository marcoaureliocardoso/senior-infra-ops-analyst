import assert from 'node:assert/strict';
import test from 'node:test';

import { interpretWitnessResult } from './mutation-protocol.mjs';

test('pristine witnesses must succeed', () => {
  assert.equal(interpretWitnessResult({ status: 0, stderr: '' }, 'X', 'baseline'), 'passed');
  for (const result of [
    { status: 1, stderr: '' },
    { status: 42, stderr: 'WITNESS_ASSERTION:X' },
    { status: 2, stderr: 'import failed' },
  ]) assert.throws(() => interpretWitnessResult(result, 'X', 'baseline'));
});

test('only the matching semantic assertion kills a mutant', () => {
  assert.equal(interpretWitnessResult({ status: 42, stderr: 'WITNESS_ASSERTION:X\n' }, 'X', 'mutant'), 'killed');
  for (const result of [
    { status: 0, stderr: '' },
    { status: 1, stderr: 'WITNESS_ASSERTION:X' },
    { status: 42, stderr: 'WITNESS_ASSERTION:Y' },
    { status: 2, stderr: 'SyntaxError' },
  ]) assert.throws(() => interpretWitnessResult(result, 'X', 'mutant'));
});

test('protocol rejects unknown phases and ambiguous assertion output', () => {
  assert.throws(() => interpretWitnessResult({ status: 0, stderr: '' }, 'X', 'other'));
  assert.throws(() => interpretWitnessResult({ status: 42, stderr: 'prefix WITNESS_ASSERTION:X suffix' }, 'X', 'mutant'));
  assert.throws(() => interpretWitnessResult({ status: null, stderr: 'timeout' }, 'X', 'mutant'));
});
