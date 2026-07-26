import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { cp, mkdir, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';

import { SECURITY_PREDICATE_IDS } from '../../skills/command-driven-operations/scripts/command-guard/policy.mjs';
import { MUTATIONS } from './mutations.mjs';

assert.deepEqual(MUTATIONS.map(({ id }) => id).sort(), [...SECURITY_PREDICATE_IDS].sort());
const sourceScripts = path.resolve('skills/command-driven-operations/scripts');
const invariantTest = path.resolve('tests/command-guard/mutation-invariant.test.mjs');

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
    const result = spawnSync(process.execPath, ['--test', invariantTest], {
      cwd: process.cwd(), encoding: 'utf8',
      env: { ...process.env, COMMAND_GUARD_MUTANT_ROOT: mutantRoot, COMMAND_GUARD_MUTATION_ID: mutation.id },
    });
    if (result.status === 0) throw new Error(`${mutation.id}: mutation survived\n${result.stdout}${result.stderr}`);
    process.stdout.write(`killed ${mutation.id}\n`);
  } finally {
    const prefix = path.join(os.tmpdir(), 'ops-guard-mutant-');
    if (!path.resolve(temporary).startsWith(path.resolve(prefix))) throw new Error('refusing to remove unverified mutation directory');
    await rm(temporary, { recursive: true, force: true });
  }
}
