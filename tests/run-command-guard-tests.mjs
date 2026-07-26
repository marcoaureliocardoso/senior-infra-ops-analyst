import { spawnSync } from 'node:child_process';
import { readdir, readFile, stat } from 'node:fs/promises';
import path from 'node:path';

const REQUIRED_FLAGS = [
  '--experimental-test-coverage', '--test-coverage-lines',
  '--test-coverage-branches', '--test-coverage-functions', '--test-coverage-include',
  '--test-concurrency',
];
const help = spawnSync(process.execPath, ['--help'], { encoding: 'utf8' });
if (help.status !== 0) throw new Error(`Node ${process.version} capability probe failed`);
for (const flag of REQUIRED_FLAGS) {
  if (!help.stdout.includes(flag)) {
    throw new Error(`Node ${process.version} lacks required native coverage capability: ${flag}`);
  }
}

function run(args, label) {
  const result = spawnSync(process.execPath, args, { cwd: process.cwd(), encoding: 'utf8', stdio: 'inherit' });
  if (result.error) throw result.error;
  if (result.status !== 0) throw new Error(`${label} failed with exit ${result.status}`);
}

const testDirectory = path.resolve('tests/command-guard');
const tests = (await readdir(testDirectory))
  .filter((name) => name.endsWith('.test.mjs'))
  .map((name) => path.join(testDirectory, name));

run(['--test', '--test-concurrency=1', ...tests], 'command guard unit/property/finite-matrix tests');

const critical = [
  'contract.mjs', 'redaction.mjs', 'response.mjs', 'bash-lexer.mjs',
  'powershell-lexer.mjs', 'composition.mjs', 'credential-flow.mjs', 'binding-store.mjs',
  'policy.mjs', 'audit.mjs',
].map((name) => `--test-coverage-include=skills/command-driven-operations/scripts/command-guard/${name}`);
critical.push('--test-coverage-include=skills/command-driven-operations/scripts/validate-ops-command.mjs');
critical.push('--test-coverage-include=skills/command-driven-operations/scripts/record-command-approval.mjs');
run([
  '--test', '--test-concurrency=1', '--experimental-test-coverage',
  '--test-coverage-lines=100', '--test-coverage-branches=100', '--test-coverage-functions=100',
  ...critical, ...tests,
], '100% critical coverage gate');

run([path.join(testDirectory, 'run-mutations.mjs')], 'security mutation gate');

async function scan(directory) {
  const info = await stat(directory).catch(() => null);
  if (!info) return;
  for (const name of await readdir(directory)) {
    const target = path.join(directory, name);
    const child = await stat(target);
    if (child.isDirectory()) await scan(target);
    else if ((await readFile(target, 'utf8')).includes('SYNTH_SECRET_')) throw new Error(`synthetic credential retained in runtime artifact: ${target}`);
  }
}

await scan(path.resolve('.command-guard-artifacts'));
await scan(path.resolve('tests/.command-guard-artifacts'));
process.stdout.write(`command guard gate passed on ${process.version}; seeds: 0x04c0ffee, 0x51a7e001, 0x7f00aa55, 0xd15ea5ed\n`);
