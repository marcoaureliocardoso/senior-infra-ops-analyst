import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import test from 'node:test';

import { SECURITY_PREDICATE_IDS } from '../../skills/command-driven-operations/scripts/command-guard/policy.mjs';
import { MUTATIONS } from './mutations.mjs';
import { MUTATION_WITNESSES } from './mutation-witnesses.mjs';

test('every exported security predicate has one exact one-site mutation', async () => {
  assert.deepEqual(MUTATIONS.map(({ id }) => id).sort(), [...SECURITY_PREDICATE_IDS].sort());
  assert.deepEqual(Object.keys(MUTATION_WITNESSES).sort(), [...SECURITY_PREDICATE_IDS].sort());
  for (const mutation of MUTATIONS) {
    const source = await readFile(path.resolve('skills/command-driven-operations/scripts', mutation.file), 'utf8');
    assert.equal(source.split(mutation.search).length - 1, 1, mutation.id);
  }
});
