import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { cp, mkdir, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';

import { SECURITY_PREDICATE_IDS } from '../../skills/command-driven-operations/scripts/command-guard/policy.mjs';
import { interpretWitnessResult } from './mutation-protocol.mjs';
import { MUTATIONS } from './mutations.mjs';
import { MUTATION_WITNESSES } from './mutation-witnesses.mjs';

assert.deepEqual(MUTATIONS.map(({ id }) => id).sort(), [...SECURITY_PREDICATE_IDS].sort());
assert.deepEqual(Object.keys(MUTATION_WITNESSES).sort(), [...SECURITY_PREDICATE_IDS].sort());

const sourceScripts = path.resolve('skills/command-driven-operations/scripts');
const witnessRunner = path.resolve('tests/command-guard/run-mutation-witness.mjs');

function runWitness(id, root) {
  return spawnSync(process.execPath, [witnessRunner, id, root], {
    cwd: process.cwd(), encoding: 'utf8', timeout: 30_000,
  });
}

for (const id of Object.keys(MUTATION_WITNESSES)) {
  const result = runWitness(id, sourceScripts);
  interpretWitnessResult(result, id, 'baseline');
}
process.stdout.write(`baseline passed ${Object.keys(MUTATION_WITNESSES).length} witnesses\n`);

let killed = 0;
for (const mutation of MUTATIONS) {
  const temporary = await mkdtemp(path.join(os.tmpdir(), `ops-guard-mutant-${mutation.id.toLowerCase()}-`));
  try {
    const mutantRoot = path.join(temporary, 'scripts');
    await mkdir(mutantRoot, { recursive: true });
    await cp(path.join(sourceScripts, 'command-guard'), path.join(mutantRoot, 'command-guard'), { recursive: true });
    await cp(path.join(sourceScripts, 'validate-ops-command.mjs'), path.join(mutantRoot, 'validate-ops-command.mjs'));
    const target = path.join(mutantRoot, mutation.file);
    const source = await readFile(target, 'utf8');
    const count = source.split(mutation.search).length - 1;
    if (count !== 1) throw new Error(`${mutation.id}: expected one mutation site, observed ${count}`);
    await writeFile(target, source.replace(mutation.search, mutation.replacement), 'utf8');
    const result = runWitness(mutation.id, mutantRoot);
    interpretWitnessResult(result, mutation.id, 'mutant');
    killed += 1;
    process.stdout.write(`killed ${mutation.id}\n`);
  } finally {
    const prefix = path.resolve(os.tmpdir(), 'ops-guard-mutant-');
    if (!path.resolve(temporary).startsWith(prefix)) throw new Error('refusing to remove unverified mutation directory');
    await rm(temporary, { recursive: true, force: true });
  }
}

assert.equal(killed, SECURITY_PREDICATE_IDS.length);
process.stdout.write(`mutation gate passed ${killed}/${SECURITY_PREDICATE_IDS.length}\n`);
