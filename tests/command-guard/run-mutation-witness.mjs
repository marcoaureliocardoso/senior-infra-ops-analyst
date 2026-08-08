import assert from 'node:assert/strict';

import { MUTATION_WITNESSES } from './mutation-witnesses.mjs';

const [id, root] = process.argv.slice(2);
const witness = MUTATION_WITNESSES[id];
if (!id || !root || !witness) {
  process.exitCode = 2;
} else {
  try {
    await witness({ root, mutationId: id });
    process.exitCode = 0;
  } catch (error) {
    if (error instanceof assert.AssertionError) {
      process.stderr.write(`WITNESS_ASSERTION:${id}\n`);
      process.exitCode = 42;
    } else {
      process.stderr.write(`WITNESS_INFRASTRUCTURE:${id}:${error?.name ?? 'Error'}\n`);
      process.exitCode = 2;
    }
  }
}
