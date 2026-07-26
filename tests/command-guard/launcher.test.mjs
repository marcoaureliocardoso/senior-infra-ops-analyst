import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { copyFile, mkdtemp, mkdir, rm, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

const SOURCE = path.resolve('skills/command-driven-operations/scripts/command-guard-launcher.sh');
const BASH = process.env.BASH_PATH ?? (process.platform === 'win32' ? 'C:/Program Files/Git/bin/bash.exe' : 'bash');

async function fixture(entrypoint, postEntrypoint = null) {
  const root = await mkdtemp(path.join(os.tmpdir(), 'guard-launcher-'));
  const scripts = path.join(root, 'scripts');
  await mkdir(path.join(scripts, 'command-guard'), { recursive: true });
  await copyFile(SOURCE, path.join(scripts, 'command-guard-launcher.sh'));
  if (entrypoint) await writeFile(path.join(scripts, 'validate-ops-command.mjs'), entrypoint, 'utf8');
  if (postEntrypoint) await writeFile(path.join(scripts, 'record-command-approval.mjs'), postEntrypoint, 'utf8');
  return { root, launcher: path.join(scripts, 'command-guard-launcher.sh') };
}

function run(launcher, mode = 'pre', extraEnv = {}) {
  return spawnSync(BASH, [launcher, mode], {
    input: '{}', encoding: 'utf8', timeout: 10_000,
    env: { ...process.env, PATH: process.env.PATH, ...extraEnv },
  });
}

test('launcher forwards exactly one valid PreToolUse decision', async () => {
  const item = await fixture("process.stdout.write(JSON.stringify({hookSpecificOutput:{hookEventName:'PreToolUse',permissionDecision:'deny',permissionDecisionReason:'synthetic'}})+'\\n');\n");
  try {
    const result = run(item.launcher);
    assert.equal(result.status, 0);
    assert.equal(result.stderr, '');
    assert.equal(result.stdout.trim().split(/\r?\n/u).length, 1);
    assert.equal(JSON.parse(result.stdout).hookSpecificOutput.permissionDecision, 'deny');
  } finally { await rm(item.root, { recursive: true, force: true }); }
});

test('launcher accepts a silent successful PostToolUse recorder', async () => {
  const item = await fixture("process.stdout.write('{}\\n');\n", 'process.exitCode = 0;\n');
  try {
    const result = run(item.launcher, 'post');
    assert.equal(result.status, 0);
    assert.equal(result.stdout, '');
    assert.equal(result.stderr, '');
  } finally { await rm(item.root, { recursive: true, force: true }); }
});

test('launcher blocks an unavailable Node runtime and its internal deadline', async () => {
  const unavailable = await fixture("process.stdout.write('{}\\n');\n");
  try {
    const result = run(unavailable.launcher, 'pre', { PATH: '' });
    assert.equal(result.status, 2);
    assert.match(result.stderr, /launcher failed/u);
  } finally { await rm(unavailable.root, { recursive: true, force: true }); }

  const hanging = await fixture('setInterval(() => {}, 60_000);\n');
  try {
    const started = Date.now();
    const result = run(hanging.launcher);
    assert.equal(result.status, 2);
    assert.ok(Date.now() - started >= 4_500);
    assert.ok(Date.now() - started < 8_000);
  } finally { await rm(hanging.root, { recursive: true, force: true }); }
});

test('launcher blocks invalid mode missing entrypoint crash and polluted output', async () => {
  const cases = [
    { mode: 'invalid', source: "process.stdout.write('{}\\n');\n" },
    { mode: 'pre', source: null },
    { mode: 'pre', source: "throw new Error('synthetic crash');\n" },
    { mode: 'pre', source: "process.stdout.write('{}\\n{}\\n');\n" },
  ];
  for (const itemCase of cases) {
    const item = await fixture(itemCase.source);
    try {
      const result = run(item.launcher, itemCase.mode);
      assert.equal(result.status, 2, itemCase.mode);
      assert.match(result.stderr, /launcher failed/u);
      assert.doesNotMatch(result.stdout, /permissionDecision.*allow/u);
    } finally { await rm(item.root, { recursive: true, force: true }); }
  }
});
