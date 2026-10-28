import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import { lstat, mkdir, mkdtemp, readFile, rm, symlink, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import {
  applyOwnedBrowserHooks,
  desiredBrowserHooks,
  emptyBrowserOwnership,
  inspectBrowserSettings,
  removeOwnedBrowserHooks,
} from '../../skills/browser-operations/scripts/browser-main-session-settings.mjs';


const CLI = path.resolve('skills/browser-operations/scripts/configure-browser-operations.mjs');
const SKILL_ROOT = path.resolve('skills/browser-operations');
const BROWSER_MCP_MATCHER = 'mcp__playwright__browser_(navigate|snapshot|type|click)';


async function fixture(run) {
  const directory = await mkdtemp(path.join(os.tmpdir(), 'browser-settings-'));
  const root = path.join(directory, 'project');
  try {
    await mkdir(root);
    await run({ directory, root, claude: path.join(root, '.claude') });
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
}


function runCli(args, env = {}) {
  return spawnSync(process.execPath, [CLI, ...args], {
    encoding: 'utf8', env: { ...process.env, ...env },
  });
}


function report(result) {
  return JSON.parse(result.stdout);
}


test('desired hooks are exact bounded browser MCP lifecycle entries', () => {
  const desired = desiredBrowserHooks({ skillRoot: SKILL_ROOT, platform: process.platform });
  assert.deepEqual(desired.hooks.map(({ event, group }) => [
    event, group.matcher, group.hooks[0].args[0], group.hooks[0].timeout,
  ]), [
    ['PreToolUse', BROWSER_MCP_MATCHER, 'pre', 9],
    ['PostToolUse', BROWSER_MCP_MATCHER, 'post', 9],
    ['PostToolUseFailure', BROWSER_MCP_MATCHER, 'failure', 9],
  ]);
  assert.equal(desired.hooks.every(({ group }) =>
    group.hooks[0].command.endsWith('browser-hook-launcher.sh')), true);
});


test('merge and removal preserve all operator settings and hook order', () => {
  const operatorBefore = { matcher: 'Read', hooks: [{ type: 'command', command: '/operator/before' }] };
  const operatorAfter = { matcher: 'Write', hooks: [{ type: 'command', command: '/operator/after' }] };
  const current = {
    statusLine: { type: 'command', command: '/operator/status' },
    permissions: { deny: ['Read(.env)'] },
    mcpServers: { operator: { command: '/operator/mcp' } },
    env: { OPERATOR_VALUE: 'keep' },
    unknownSetting: { nested: true },
    hooks: { PreToolUse: [operatorBefore], Stop: [operatorAfter] },
  };
  const desired = desiredBrowserHooks({ skillRoot: SKILL_ROOT, platform: process.platform });
  const applied = applyOwnedBrowserHooks({ current, desired, ownership: emptyBrowserOwnership() });
  assert.deepEqual(applied.settings.hooks.PreToolUse[0], operatorBefore);
  assert.deepEqual(applied.settings.hooks.Stop, [operatorAfter]);
  assert.deepEqual(Object.fromEntries(Object.entries(applied.settings).filter(([key]) => key !== 'hooks')),
    Object.fromEntries(Object.entries(current).filter(([key]) => key !== 'hooks')));
  const repeated = applyOwnedBrowserHooks({
    current: applied.settings, desired, ownership: applied.ownership,
  });
  assert.deepEqual(repeated, applied);
  const removed = removeOwnedBrowserHooks({
    current: repeated.settings, desired, ownership: repeated.ownership,
  });
  assert.deepEqual(removed.settings, current);
  assert.deepEqual(removed.ownership, emptyBrowserOwnership());
  assert.deepEqual(removed.conflicts, []);
});


test('inspection never treats persisted proof structure as current runtime evidence', () => {
  const desired = desiredBrowserHooks({ skillRoot: SKILL_ROOT, platform: process.platform });
  const empty = emptyBrowserOwnership();
  assert.equal(inspectBrowserSettings({ current: {}, desired, ownership: empty }).state, 'NOT_CONFIGURED');
  const applied = applyOwnedBrowserHooks({ current: {}, desired, ownership: empty });
  assert.equal(inspectBrowserSettings({
    current: applied.settings, desired, ownership: applied.ownership,
  }).state, 'CONFIGURED_UNPROVEN');
  const drifted = structuredClone(applied.settings);
  drifted.hooks.PreToolUse.at(-1).hooks[0].timeout = 30;
  assert.equal(inspectBrowserSettings({
    current: drifted, desired, ownership: applied.ownership,
  }).state, 'CONFLICT');
  const proved = structuredClone(applied.ownership);
  proved.liveProof = {
    configurationIdentity: desired.configurationIdentity,
    capabilityState: 'ACTIVE', decision: 'deny', reasonCode: 'DENY_ORIGIN_ESCAPE',
  };
  assert.throws(() => inspectBrowserSettings({
    current: applied.settings, desired, ownership: proved,
  }), /OWNERSHIP_CONFLICT/u);
});


test('unowned duplicates and ownership drift fail without widening hooks', () => {
  const desired = desiredBrowserHooks({ skillRoot: SKILL_ROOT, platform: process.platform });
  const current = { hooks: { PreToolUse: [structuredClone(desired.hooks[0].group)] } };
  assert.throws(() => applyOwnedBrowserHooks({
    current, desired, ownership: emptyBrowserOwnership(),
  }), /HOOK_ALREADY_PRESENT_UNOWNED/u);
  const applied = applyOwnedBrowserHooks({ current: {}, desired, ownership: emptyBrowserOwnership() });
  const changed = structuredClone(applied.ownership);
  changed.configurationIdentity = '0'.repeat(64);
  assert.throws(() => applyOwnedBrowserHooks({
    current: applied.settings, desired, ownership: changed,
  }), /OWNERSHIP_DRIFT/u);
});


test('owned removal rejects a forged record naming an operator hook', () => {
  const desired = desiredBrowserHooks({ skillRoot: SKILL_ROOT, platform: process.platform });
  const operatorGroup = {
    matcher: 'Read', hooks: [{ type: 'command', command: '/operator/hook' }],
  };
  const ownership = {
    ...emptyBrowserOwnership(),
    configurationIdentity: desired.configurationIdentity,
    entries: [{ event: 'PreToolUse', group: structuredClone(operatorGroup) }],
  };
  assert.throws(() => removeOwnedBrowserHooks({
    current: { hooks: { PreToolUse: [operatorGroup] } }, desired, ownership,
  }), /OWNERSHIP_DRIFT/u);
});


test('CLI check is read-only and apply/remove are idempotent and structural', async () => {
  await fixture(async ({ root, claude }) => {
    const before = runCli(['--check', '--root', root]);
    assert.equal(before.status, 2, before.stderr);
    assert.equal(report(before).state, 'NOT_CONFIGURED');
    assert.equal(report(before).changed, false);
    assert.equal(existsSync(claude), false);

    const applied = runCli(['--apply', '--root', root]);
    assert.equal(applied.status, 2, applied.stderr);
    assert.equal(report(applied).state, 'CONFIGURED_UNPROVEN');
    assert.equal(report(applied).changed, true);
    assert.equal(existsSync(path.join(root, '.mcp.json')), false);
    const repeated = runCli(['--apply', '--root', root]);
    assert.equal(repeated.status, 2, repeated.stderr);
    assert.equal(report(repeated).changed, false);

    const settings = JSON.parse(await readFile(path.join(claude, 'settings.local.json'), 'utf8'));
    for (const event of ['PreToolUse', 'PostToolUse', 'PostToolUseFailure']) {
      assert.equal(settings.hooks[event].length, 1);
      assert.equal(settings.hooks[event][0].matcher, BROWSER_MCP_MATCHER);
    }
    const removed = runCli(['--remove-owned', '--root', root]);
    assert.equal(removed.status, 0, removed.stderr);
    assert.equal(report(removed).state, 'NOT_CONFIGURED');
    assert.equal(runCli(['--remove-owned', '--root', root]).status, 0);
  });
});


test('CLI preserves seeded operator settings and never reports their values', async () => {
  await fixture(async ({ root, claude }) => {
    await mkdir(claude);
    const settingsPath = path.join(claude, 'settings.local.json');
    const original = {
      model: 'operator-model', env: { OPERATOR_TOKEN: 'SYNTH_BROWSER_SECRET' },
      hooks: { PreToolUse: [{ matcher: 'Read', hooks: [{ type: 'command', command: '/keep' }] }] },
      mcpServers: { operator: { command: '/keep-mcp' } },
    };
    await writeFile(settingsPath, `${JSON.stringify(original, null, 2)}\n`);
    const applied = runCli(['--apply', '--root', root]);
    assert.equal(applied.status, 2, applied.stderr);
    assert.doesNotMatch(applied.stdout + applied.stderr, /SYNTH_BROWSER_SECRET|operator-model|OPERATOR_TOKEN/u);
    const removed = runCli(['--remove-owned', '--root', root]);
    assert.equal(removed.status, 0, removed.stderr);
    assert.deepEqual(JSON.parse(await readFile(settingsPath, 'utf8')), original);
  });
});


test('conflict and injected interruption preserve original settings', async () => {
  await fixture(async ({ root, claude }) => {
    await mkdir(claude);
    const settingsPath = path.join(claude, 'settings.local.json');
    const original = '{"hooks":{"PreToolUse":"operator-owned"}}\n';
    await writeFile(settingsPath, original);
    const conflict = runCli(['--apply', '--root', root]);
    assert.equal(conflict.status, 3);
    assert.equal(await readFile(settingsPath, 'utf8'), original);

    const safeOriginal = '{"model":"keep"}\n';
    await writeFile(settingsPath, safeOriginal);
    const interrupted = runCli(['--apply', '--root', root], { P004B_TEST_FAIL_BEFORE_REPLACE: '1' });
    assert.equal(interrupted.status, 3);
    assert.equal(await readFile(settingsPath, 'utf8'), safeOriginal);
  });
});


test('a settings-first process crash is recovered transactionally', async () => {
  await fixture(async ({ root, claude }) => {
    const crashed = runCli(['--apply', '--root', root], { P004B_TEST_CRASH_AFTER_SETTINGS: '1' });
    assert.equal(crashed.status, 86, crashed.stdout + crashed.stderr);
    assert.equal(existsSync(path.join(claude, 'settings.local.json')), true);
    assert.equal(existsSync(path.join(claude, '.p0-04b-browser-operations.transaction.json')), true);
    const recovered = runCli(['--apply', '--root', root]);
    assert.equal(recovered.status, 2, recovered.stdout + recovered.stderr);
    assert.equal(report(recovered).state, 'CONFIGURED_UNPROVEN');
    assert.equal(existsSync(path.join(claude, '.p0-04b-browser-operations-owned.json')), true);
    assert.equal(existsSync(path.join(claude, '.p0-04b-browser-operations.transaction.json')), false);
  });
});


test('symlinked settings and ownership fail closed', { skip: process.platform === 'win32' }, async () => {
  await fixture(async ({ directory, root, claude }) => {
    await mkdir(claude);
    const target = path.join(directory, 'operator.json');
    await writeFile(target, '{"model":"keep"}\n');
    await symlink(target, path.join(claude, 'settings.local.json'));
    assert.equal(runCli(['--apply', '--root', root]).status, 3);
    assert.equal((await lstat(path.join(claude, 'settings.local.json'))).isSymbolicLink(), true);
    assert.equal(await readFile(target, 'utf8'), '{"model":"keep"}\n');

    await rm(path.join(claude, 'settings.local.json'));
    await writeFile(path.join(claude, 'settings.local.json'), '{}\n');
    const ownedTarget = path.join(directory, 'operator-owned.json');
    await writeFile(ownedTarget, '{}\n');
    await symlink(ownedTarget, path.join(claude, '.p0-04b-browser-operations-owned.json'));
    assert.equal(runCli(['--apply', '--root', root]).status, 3);
    assert.equal(await readFile(ownedTarget, 'utf8'), '{}\n');
  });
});
