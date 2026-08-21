import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';
import { mkdir, mkdtemp, readFile, rm, symlink, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { spawn, spawnSync } from 'node:child_process';
import test from 'node:test';


const cli = path.resolve(
  'skills/command-driven-operations/scripts/configure-native-execution-boundary.mjs',
);

async function fixture(run) {
  const directory = await mkdtemp(path.join(os.tmpdir(), 'p005-settings-'));
  const root = path.join(directory, 'project');
  await mkdir(root, { recursive: true });
  try {
    await run({ directory, root, claude: path.join(root, '.claude') });
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
}

function runCli(args, env = {}) {
  return spawnSync(process.execPath, [cli, ...args], {
    encoding: 'utf8',
    env: { ...process.env, ...env },
  });
}

function report(result) {
  return JSON.parse(result.stdout);
}

async function waitForPath(target, timeoutMs = 1000) {
  const deadline = Date.now() + timeoutMs;
  while (!existsSync(target) && Date.now() < deadline) {
    await new Promise((resolve) => setTimeout(resolve, 10));
  }
  assert.equal(existsSync(target), true, `timed out waiting for ${path.basename(target)}`);
}

test('help is side-effect free and invalid invocations return 64', async () => {
  await fixture(async ({ root, claude }) => {
    const help = runCli(['--help', '--root', root]);
    assert.equal(help.status, 0, help.stderr);
    assert.match(help.stdout, /--check.*--apply.*--remove-owned/su);
    assert.equal(existsSync(claude), false);
    for (const args of [[], ['--unknown'], ['--check', '--apply'], ['--root']]) {
      const invalid = runCli(args);
      assert.equal(invalid.status, 64, `${args}: ${invalid.stdout}${invalid.stderr}`);
    }
  });
});

test('check apply idempotent apply and owned removal expose honest states', async () => {
  await fixture(async ({ root, claude }) => {
    const before = runCli(['--check', '--root', root]);
    assert.equal(before.status, 2, before.stderr);
    assert.equal(report(before).state, 'ABSENT');
    assert.equal(report(before).changed, false);
    assert.equal(existsSync(claude), false, '--check must not create the settings directory');

    const first = runCli(['--apply', '--root', root]);
    assert.equal(first.status, 2, first.stderr);
    assert.equal(report(first).state, 'CONFIGURED_UNPROVEN');
    assert.equal(report(first).changed, true);
    const second = runCli(['--apply', '--root', root]);
    assert.equal(second.status, 2, second.stderr);
    assert.equal(report(second).changed, false);

    const settings = JSON.parse(await readFile(path.join(claude, 'settings.local.json'), 'utf8'));
    assert.equal(settings.hooks.PreToolUse.length, 1);
    assert.equal(settings.hooks.PostToolUse.length, 1);
    const removed = runCli(['--remove-owned', '--root', root]);
    assert.equal(removed.status, 0, removed.stderr);
    assert.equal(report(removed).state, 'ABSENT');
    assert.equal(report(removed).changed, true);
  });
});

test('apply and removal preserve unrelated operator settings without reporting values', async () => {
  await fixture(async ({ root, claude }) => {
    await mkdir(claude, { recursive: true });
    const settingsPath = path.join(claude, 'settings.local.json');
    const original = {
      model: 'operator-model',
      env: { OPERATOR_TOKEN: 'SYNTH_SECRET_never_report' },
      hooks: {
        Stop: [{ hooks: [{ type: 'command', command: '/operator/stop' }] }],
        PreToolUse: [{ matcher: 'Read', hooks: [{ type: 'command', command: '/operator/read' }] }],
      },
    };
    await writeFile(settingsPath, `${JSON.stringify(original, null, 2)}\n`, 'utf8');
    const applied = runCli(['--apply', '--root', root]);
    assert.equal(applied.status, 2, applied.stderr);
    assert.doesNotMatch(applied.stdout + applied.stderr, /SYNTH_SECRET|operator-model|OPERATOR_TOKEN/u);
    const changed = JSON.parse(await readFile(settingsPath, 'utf8'));
    assert.equal(changed.env.OPERATOR_TOKEN, 'SYNTH_SECRET_never_report');
    assert.equal(changed.hooks.Stop.length, 1);
    assert.equal(changed.hooks.PreToolUse.length, 2);
    const removed = runCli(['--remove-owned', '--root', root]);
    assert.equal(removed.status, 0, removed.stderr);
    assert.deepEqual(JSON.parse(await readFile(settingsPath, 'utf8')), original);
  });
});

test('malformed duplicate and non-object settings fail without mutation', async () => {
  await fixture(async ({ root, claude }) => {
    await mkdir(claude, { recursive: true });
    const settingsPath = path.join(claude, 'settings.local.json');
    for (const raw of ['{"hooks":{},"hooks":{}}\n', '[]\n']) {
      await writeFile(settingsPath, raw, 'utf8');
      const result = runCli(['--apply', '--root', root]);
      assert.equal(result.status, 3, result.stdout + result.stderr);
      assert.equal(await readFile(settingsPath, 'utf8'), raw);
      assert.doesNotMatch(result.stdout + result.stderr, /\[\]|\{"hooks/u);
    }
  });
});

test('linked settings and linked ancestors are rejected without touching targets', {
  skip: process.platform === 'win32',
}, async () => {
  await fixture(async ({ directory, root, claude }) => {
    const target = path.join(directory, 'operator-settings.json');
    await writeFile(target, '{"model":"keep"}\n', 'utf8');
    await mkdir(claude, { recursive: true });
    await symlink(target, path.join(claude, 'settings.local.json'));
    const linkedFile = runCli(['--apply', '--root', root]);
    assert.equal(linkedFile.status, 3);
    assert.equal(await readFile(target, 'utf8'), '{"model":"keep"}\n');
  });
});

test('an interrupted settings-first commit recovers without whole-file restoration', async () => {
  await fixture(async ({ root, claude }) => {
    const interrupted = runCli(['--apply', '--root', root], {
      P005_TEST_CRASH_AFTER_SETTINGS: '1',
    });
    assert.equal(interrupted.status, 86, interrupted.stdout + interrupted.stderr);
    const recovered = runCli(['--apply', '--root', root]);
    assert.equal(recovered.status, 2, recovered.stdout + recovered.stderr);
    assert.equal(report(recovered).state, 'CONFIGURED_UNPROVEN');
    const settings = JSON.parse(await readFile(path.join(claude, 'settings.local.json'), 'utf8'));
    assert.equal(settings.hooks.PreToolUse.length, 1);
    assert.equal(settings.hooks.PostToolUse.length, 1);
    assert.equal(existsSync(path.join(claude, '.p0-05-native-execution.transaction.json')), false);
  });
});

test('a target changed before the guarded recheck is refused and preserved', async () => {
  await fixture(async ({ root, claude }) => {
    await mkdir(claude, { recursive: true });
    const settingsPath = path.join(claude, 'settings.local.json');
    const transactionPath = path.join(claude, '.p0-05-native-execution.transaction.json');
    await writeFile(settingsPath, '{"model":"initial"}\n', 'utf8');
    const child = spawn(process.execPath, [cli, '--apply', '--root', root], {
      encoding: 'utf8',
      env: {
        ...process.env,
        P005_TEST_PAUSE_BEFORE_RECHECK_MS: '500',
      },
    });
    let stdout = '';
    let stderr = '';
    child.stdout.setEncoding('utf8');
    child.stderr.setEncoding('utf8');
    child.stdout.on('data', (chunk) => { stdout += chunk; });
    child.stderr.on('data', (chunk) => { stderr += chunk; });
    await waitForPath(transactionPath);
    const operatorChange = '{"model":"operator-concurrent-change"}\n';
    await writeFile(settingsPath, operatorChange, 'utf8');
    const status = await new Promise((resolve) => child.once('close', resolve));
    assert.equal(status, 3, stdout + stderr);
    assert.equal(await readFile(settingsPath, 'utf8'), operatorChange);
  });
});

test('lock contention fails within a bounded interval and preserves settings', async () => {
  await fixture(async ({ root, claude }) => {
    await mkdir(claude, { recursive: true });
    const settingsPath = path.join(claude, 'settings.local.json');
    await writeFile(settingsPath, '{"model":"keep"}\n', 'utf8');
    await mkdir(path.join(claude, '.p0-05-native-execution.lock'));
    const started = Date.now();
    const result = runCli(['--apply', '--root', root]);
    assert.equal(result.status, 3);
    assert.ok(Date.now() - started < 4000, `lock wait was ${Date.now() - started}ms`);
    assert.equal(await readFile(settingsPath, 'utf8'), '{"model":"keep"}\n');
  });
});
