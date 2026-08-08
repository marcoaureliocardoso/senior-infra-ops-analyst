import path from 'node:path';
import test from 'node:test';

import { MUTATION_WITNESSES } from './mutation-witnesses.mjs';

const root = path.resolve('skills/command-driven-operations/scripts');

for (const [mutationId, witness] of Object.entries(MUTATION_WITNESSES)) {
  test(`pristine witness passes: ${mutationId}`, async () => {
    await witness({ root, mutationId });
  });
}
