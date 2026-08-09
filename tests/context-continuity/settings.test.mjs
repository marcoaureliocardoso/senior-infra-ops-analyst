import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { lstatSync, readFileSync } from 'node:fs';
import { mkdir, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import {
  applyOwnedSettings,
  desiredOwnedSettings,
  discoverSettingScopes,
  emptyOwnership,
  inspectContinuity,
  parseStrictObject,
  probeClaudeCapabilities,
  quoteStatusCommand,
  removeOwnedSettings,
} from '../../skills/context-continuity/scripts/settings.mjs';


test('strict settings parser accepts one JSON object', () => {
  assert.deepEqual(
    parseStrictObject('{"env":{"A":"1"},"hooks":{}}', 'fixture'),
    { env: { A: '1' }, hooks: {} },
  );
});

test('strict settings parser rejects duplicate keys at every object depth', () => {
  for (const raw of [
    '{"env":{},"env":{}}',
    '{"env":{"A":"1","A":"2"}}',
    '{"hooks":{"PreCompact":[],"PreCompact":[]}}',
    '{"array":[{"key":1,"key":2}]}',
  ]) {
    assert.throws(
      () => parseStrictObject(raw, 'fixture'),
      /duplicate JSON key/u,
      raw,
    );
  }
});

test('strict settings parser rejects non-object and invalid roots', () => {
  for (const raw of ['null', '[]', '"text"', '{', '{"a":NaN}']) {
    assert.throws(() => parseStrictObject(raw, 'fixture'), /fixture/u, raw);
  }
});

const skillRoot = '/installed/context-continuity';

function desired(includeStatusLine = false) {
  return desiredOwnedSettings({
    skillRoot,
    includeStatusLine,
    nodeBin: '/usr/bin/node',
    platform: 'linux',
  });
}

test('desired project settings use percentage compaction and native hooks only', () => {
  const value = desired();
  assert.deepEqual(value.env, { CLAUDE_AUTOCOMPACT_PCT_OVERRIDE: '72' });
  assert.equal('CLAUDE_CODE_AUTO_COMPACT_WINDOW' in value.env, false);
  assert.equal(value.hooks.PreCompact[0].hooks[0].args[0], 'pre');
  assert.equal(value.hooks.PostCompact[0].hooks[0].args[0], 'post');
  assert.equal(value.hooks.PreCompact[0].hooks[0].timeout, 5);
  assert.equal('statusLine' in value, false);
});

test('apply preserves unrelated settings and appends owned hooks once', () => {
  const stop = [{ hooks: [{ type: 'command', command: '/operator/stop' }] }];
  const operatorPre = { matcher: 'manual', hooks: [{ type: 'command', command: '/operator/pre' }] };
  const current = {
    model: 'operator-model',
    env: { OTHER: 'keep' },
    hooks: { Stop: stop, PreCompact: [operatorPre] },
  };
  const first = applyOwnedSettings({ current, ownership: emptyOwnership('project'), desired: desired() });
  const second = applyOwnedSettings({ current: first.settings, ownership: first.ownership, desired: desired() });
  assert.equal(first.settings.model, 'operator-model');
  assert.equal(first.settings.env.OTHER, 'keep');
  assert.equal(first.settings.env.CLAUDE_AUTOCOMPACT_PCT_OVERRIDE, '72');
  assert.deepEqual(first.settings.hooks.Stop, stop);
  assert.deepEqual(first.settings.hooks.PreCompact[0], operatorPre);
  assert.equal(first.settings.hooks.PreCompact.length, 2);
  assert.deepEqual(second, first);
});

test('apply preserves an operator percentage from 70 through 75', () => {
  for (const percent of ['70', '71', '72', '73', '74', '75']) {
    const result = applyOwnedSettings({
      current: { env: { CLAUDE_AUTOCOMPACT_PCT_OVERRIDE: percent } },
      ownership: emptyOwnership('project'),
      desired: desired(),
    });
    assert.equal(result.settings.env.CLAUDE_AUTOCOMPACT_PCT_OVERRIDE, percent);
    assert.equal('env.CLAUDE_AUTOCOMPACT_PCT_OVERRIDE' in result.ownership.values, false);
  }
});

test('apply does not shadow an allowed effective percentage from another scope', () => {
  const result = applyOwnedSettings({
    current: {},
    ownership: emptyOwnership('project'),
    desired: desired(),
    effectivePercent: '70',
  });
  assert.equal('CLAUDE_AUTOCOMPACT_PCT_OVERRIDE' in (result.settings.env ?? {}), false);
  assert.equal('env.CLAUDE_AUTOCOMPACT_PCT_OVERRIDE' in result.ownership.values, false);
});

test('apply rejects disabled or conflicting auto compaction', () => {
  for (const current of [
    { autoCompactEnabled: false },
    { env: { DISABLE_AUTO_COMPACT: '1' } },
    { env: { DISABLE_COMPACT: 'true' } },
    { env: { CLAUDE_AUTOCOMPACT_PCT_OVERRIDE: '69' } },
    { env: { CLAUDE_AUTOCOMPACT_PCT_OVERRIDE: '76' } },
    { env: { CLAUDE_AUTOCOMPACT_PCT_OVERRIDE: 'text' } },
  ]) {
    assert.throws(
      () => applyOwnedSettings({ current, ownership: emptyOwnership('project'), desired: desired() }),
      /AUTO_COMPACT_DISABLED|AUTOCOMPACT_PERCENT_CONFLICT/u,
      JSON.stringify(current),
    );
  }
});

test('owned removal preserves operator changes and reports exact conflicts', () => {
  const applied = applyOwnedSettings({ current: { model: 'keep' }, ownership: emptyOwnership('project'), desired: desired(true) });
  const changed = structuredClone(applied.settings);
  changed.statusLine = { type: 'command', command: '/operator/status' };
  changed.hooks.PreCompact.unshift({ hooks: [{ type: 'command', command: '/operator/pre' }] });
  const removed = removeOwnedSettings({ current: changed, ownership: applied.ownership });
  assert.equal(removed.settings.model, 'keep');
  assert.equal('CLAUDE_AUTOCOMPACT_PCT_OVERRIDE' in (removed.settings.env ?? {}), false);
  assert.deepEqual(removed.settings.statusLine, changed.statusLine);
  assert.equal(removed.settings.hooks.PreCompact.length, 1);
  assert.deepEqual(removed.conflicts, ['statusLine']);
});

test('inspection respects managed local project user and process blockers', () => {
  const scopes = [
    { name: 'user', precedence: 1, settings: { env: { CLAUDE_AUTOCOMPACT_PCT_OVERRIDE: '70' } } },
    { name: 'project', precedence: 2, settings: { env: { CLAUDE_AUTOCOMPACT_PCT_OVERRIDE: '71' } } },
    { name: 'local', precedence: 3, settings: { env: { CLAUDE_AUTOCOMPACT_PCT_OVERRIDE: '74' } } },
    { name: 'managed', precedence: 5, settings: { autoCompactEnabled: true } },
  ];
  const report = inspectContinuity({ scopes, desired: desired(), ownership: emptyOwnership('project'), processEnv: {} });
  assert.equal(report.effective.autoCompactEnabled, true);
  assert.equal(report.effective.autoCompactPercent, 74);
  assert.deepEqual(report.blockers, []);
  const blocked = inspectContinuity({ scopes, desired: desired(), ownership: emptyOwnership('project'), processEnv: { DISABLE_COMPACT: '1' } });
  assert.equal(blocked.blockers[0].code, 'AUTO_COMPACT_DISABLED');
  assert.equal('value' in blocked.blockers[0], false);
});

test('inspection distinguishes missing configuration from desired defaults', () => {
  const report = inspectContinuity({
    scopes: [{ name: 'local', precedence: 3, settings: {} }],
    desired: desired(),
    ownership: emptyOwnership('project'),
    processEnv: {},
  });
  assert.equal(report.effective.autoCompactPercent, null);
  assert.equal(report.desired.autoCompactPercent, 72);
  assert.deepEqual(report.hooks, { preCompact: false, postCompact: false });
  assert.deepEqual(report.actions.map(({ code }) => code), [
    'AUTOCOMPACT_PERCENT_MISSING',
    'PRECOMPACT_HOOK_MISSING',
    'POSTCOMPACT_HOOK_MISSING',
  ]);
});

test('inspection refuses to shadow an inherited operator status line', () => {
  const report = inspectContinuity({
    scopes: [{ name: 'user', precedence: 1, settings: {
      statusLine: { type: 'command', command: '/operator/status' },
      env: { CLAUDE_AUTOCOMPACT_PCT_OVERRIDE: '72' },
      hooks: desired().hooks,
    } }],
    desired: desired(true), ownership: emptyOwnership('project'), processEnv: {},
  });
  assert.equal(report.configured.statusLine, false);
  assert.deepEqual(report.statusLine, {
    requested: true, owned: false, matches: false, conflict: true,
  });
  assert.deepEqual(report.blockers, [{ code: 'STATUS_LINE_CONFLICT', scope: 'effective' }]);
});

test('scope discovery uses current documented platform paths', () => {
  const windows = discoverSettingScopes({ repoRoot: 'C:\\repo', claudeConfigDir: 'C:\\home\\.claude', platform: 'win32' });
  assert.equal(windows.find(({ name }) => name === 'managed').path, 'C:\\Program Files\\ClaudeCode\\managed-settings.json');
  assert.equal(windows.find(({ name }) => name === 'local').path, 'C:\\repo\\.claude\\settings.local.json');
  const linux = discoverSettingScopes({ repoRoot: '/repo', claudeConfigDir: '/home/operator/.claude', platform: 'linux' });
  assert.equal(linux.find(({ name }) => name === 'managed').path, '/etc/claude-code/managed-settings.json');
  assert.equal(linux.find(({ name }) => name === 'user').path, '/home/operator/.claude/settings.json');
});

test('status command quotes exactly node and script paths', () => {
  assert.equal(quoteStatusCommand('/usr/bin/node', '/path with space/status.mjs', 'linux'), "'/usr/bin/node' '/path with space/status.mjs'");
  assert.equal(quoteStatusCommand('C:\\Program Files\\node.exe', 'C:\\skill root\\status.mjs', 'win32'), '"C:\\Program Files\\node.exe" "C:\\skill root\\status.mjs"');
  assert.throws(() => quoteStatusCommand('/node;bad', '/status', 'linux'), /unsafe command path/u);
});

test('capability probe reports local help features without a model request', () => {
  const calls = [];
  const run = (binary, args) => {
    calls.push([binary, args]);
    if (args[0] === '--version') return { status: 0, stdout: '2.1.218 (Claude Code)\n', stderr: '' };
    if (args[0] === 'mcp') return { status: 0, stdout: 'Usage: claude mcp list get add remove\n', stderr: '' };
    return { status: 0, stdout: 'Usage: claude --resume --agent --output-format stream-json --verbose\n', stderr: '' };
  };
  const report = probeClaudeCapabilities({ claudeBin: '/usr/bin/claude', run });
  assert.deepEqual(report, {
    available: true,
    observedVersion: '2.1.218',
    resume: true,
    agent: true,
    mcp: true,
    printStreamJson: true,
    rewind: false,
    taskTools: 'unknown',
    toolSearch: 'unknown',
    reasonCode: 'CAPABILITIES_OBSERVED',
  });
  assert.deepEqual(calls.map(([, args]) => args), [['--help'], ['mcp', '--help'], ['--version']]);
});

test('capability probe reports missing or timed-out CLI conservatively', () => {
  for (const result of [
    { status: null, error: new Error('missing'), stdout: '', stderr: '' },
    { status: 124, stdout: '', stderr: 'timeout' },
  ]) {
    const report = probeClaudeCapabilities({ claudeBin: '/missing/claude', run: () => result });
    assert.equal(report.available, false);
    assert.equal(report.taskTools, 'unknown');
    assert.equal(report.toolSearch, 'unknown');
    assert.equal(report.reasonCode, 'CLAUDE_CLI_UNAVAILABLE');
    assert.equal(JSON.stringify(report).includes('missing'), false);
    assert.equal(JSON.stringify(report).includes('timeout'), false);
  }
});

const cli = path.resolve('skills/context-continuity/scripts/configure-context-continuity.mjs');

function cleanProcessEnv() {
  const env = { ...process.env };
  for (const name of [
    'DISABLE_AUTO_COMPACT',
    'DISABLE_COMPACT',
    'CLAUDE_AUTOCOMPACT_PCT_OVERRIDE',
    'CLAUDE_CODE_AUTO_COMPACT_WINDOW',
  ]) delete env[name];
  return env;
}

async function withCliFixture(run) {
  const directory = await mkdtemp(path.join(os.tmpdir(), 'context-settings-'));
  const repoRoot = path.join(directory, 'repo');
  const claudeConfigDir = path.join(directory, 'home', '.claude');
  const managedPath = path.join(directory, 'managed-settings.json');
  await mkdir(path.join(repoRoot, '.claude'), { recursive: true });
  await mkdir(claudeConfigDir, { recursive: true });
  try {
    await run({ directory, repoRoot, claudeConfigDir, managedPath });
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
}

function runCli(args, extraEnv = {}) {
  return spawnSync(process.execPath, [cli, ...args], {
    encoding: 'utf8',
    env: { ...cleanProcessEnv(), ...extraEnv },
  });
}

test('CLI project apply preserves an allowed user-scope percentage', async () => {
  await withCliFixture(async ({ repoRoot, claudeConfigDir, managedPath }) => {
    await writeFile(
      path.join(claudeConfigDir, 'settings.json'),
      '{"env":{"CLAUDE_AUTOCOMPACT_PCT_OVERRIDE":"70"}}\n',
      'utf8',
    );
    const common = ['--scope', 'project', '--root', repoRoot, '--claude-config-dir', claudeConfigDir, '--managed-settings', managedPath, '--claude-bin', '/missing/claude'];
    const before = runCli(['--check', ...common]);
    assert.equal(before.status, 2);
    assert.equal(JSON.parse(before.stdout).autoCompactPercent, 70);
    const applied = runCli(['--apply', ...common]);
    assert.equal(applied.status, 0, applied.stdout + applied.stderr);
    const local = JSON.parse(await readFile(path.join(repoRoot, '.claude', 'settings.local.json'), 'utf8'));
    assert.equal('CLAUDE_AUTOCOMPACT_PCT_OVERRIDE' in (local.env ?? {}), false);
    assert.equal(JSON.parse(applied.stdout).autoCompactPercent, 70);
  });
});

test('CLI check reports an empty scope as requiring configuration', async () => {
  await withCliFixture(async ({ repoRoot, claudeConfigDir, managedPath }) => {
    const result = runCli([
      '--check', '--scope', 'project', '--root', repoRoot,
      '--claude-config-dir', claudeConfigDir, '--managed-settings', managedPath,
      '--claude-bin', '/missing/claude',
    ]);
    assert.equal(result.status, 2);
    const report = JSON.parse(result.stdout);
    assert.equal(report.autoCompactPercent, null);
    assert.deepEqual(report.hooks, { preCompact: false, postCompact: false });
    assert.equal(report.desired.autoCompactPercent, 72);
    assert.equal(report.configured.autoCompactPercent, false);
    assert.equal(report.owned.autoCompactPercent, false);
    assert.equal(report.actions.length, 3);
  });
});

test('CLI recovers an interruption after ownership commits but before settings', async () => {
  await withCliFixture(async ({ repoRoot, claudeConfigDir, managedPath }) => {
    const common = ['--scope', 'project', '--root', repoRoot, '--claude-config-dir', claudeConfigDir, '--managed-settings', managedPath, '--claude-bin', '/missing/claude'];
    const interrupted = runCli(['--apply', ...common], {
      CONTEXT_CONTINUITY_TEST_CRASH_AFTER_OWNERSHIP: '1',
    });
    assert.equal(interrupted.status, 86);
    const settingsPath = path.join(repoRoot, '.claude', 'settings.local.json');
    const ownershipPath = path.join(repoRoot, '.claude', '.context-continuity-owned.json');
    assert.equal(await readFile(settingsPath, 'utf8').catch(() => null), null);
    assert.ok(JSON.parse(await readFile(ownershipPath, 'utf8')).values);
    const recovered = runCli(['--apply', ...common]);
    assert.equal(recovered.status, 0, recovered.stdout + recovered.stderr);
    const removed = runCli(['--remove-owned', ...common]);
    assert.equal(removed.status, 0, removed.stdout + removed.stderr);
    const finalSettings = JSON.parse(await readFile(settingsPath, 'utf8'));
    assert.equal('CLAUDE_AUTOCOMPACT_PCT_OVERRIDE' in (finalSettings.env ?? {}), false);
    assert.equal('PreCompact' in (finalSettings.hooks ?? {}), false);
  });
});

test('CLI apply check and remove preserve unrelated project-local settings', async () => {
  await withCliFixture(async ({ repoRoot, claudeConfigDir, managedPath }) => {
    const settingsPath = path.join(repoRoot, '.claude', 'settings.local.json');
    const ownershipPath = path.join(repoRoot, '.claude', '.context-continuity-owned.json');
    await writeFile(settingsPath, `${JSON.stringify({
      model: 'operator-model',
      env: { OTHER: 'SYNTH_SECRET_must_not_be_reported' },
      hooks: { Stop: [{ hooks: [{ type: 'command', command: '/operator/stop' }] }] },
    }, null, 2)}\n`, 'utf8');
    const common = ['--scope', 'project', '--root', repoRoot, '--claude-config-dir', claudeConfigDir, '--managed-settings', managedPath, '--claude-bin', '/missing/claude'];
    const applied = runCli(['--apply', ...common]);
    assert.equal(applied.status, 0, applied.stdout + applied.stderr);
    assert.doesNotMatch(applied.stdout + applied.stderr, /SYNTH_SECRET|operator-model|OTHER/u);
    const settings = JSON.parse(await readFile(settingsPath, 'utf8'));
    assert.equal(settings.model, 'operator-model');
    assert.equal(settings.env.OTHER, 'SYNTH_SECRET_must_not_be_reported');
    assert.equal(settings.env.CLAUDE_AUTOCOMPACT_PCT_OVERRIDE, '72');
    assert.equal(settings.hooks.Stop.length, 1);
    assert.equal(settings.hooks.PreCompact.length, 1);
    assert.equal(settings.hooks.PostCompact.length, 1);
    assert.equal(lstatSync(settingsPath).isSymbolicLink(), false);
    assert.equal(lstatSync(ownershipPath).isSymbolicLink(), false);
    const checked = runCli(['--check', ...common]);
    assert.equal(checked.status, 0, checked.stdout + checked.stderr);
    assert.equal(JSON.parse(checked.stdout).autoCompactPercent, 72);
    const removed = runCli(['--remove-owned', ...common]);
    assert.equal(removed.status, 0, removed.stdout + removed.stderr);
    const after = JSON.parse(await readFile(settingsPath, 'utf8'));
    assert.equal(after.model, 'operator-model');
    assert.equal(after.env.OTHER, 'SYNTH_SECRET_must_not_be_reported');
    assert.equal('CLAUDE_AUTOCOMPACT_PCT_OVERRIDE' in after.env, false);
    assert.equal('PreCompact' in after.hooks, false);
    assert.equal('PostCompact' in after.hooks, false);
    assert.equal(after.hooks.Stop.length, 1);
  });
});

test('CLI aborts invalid or duplicate JSON without changing the file', async () => {
  await withCliFixture(async ({ repoRoot, claudeConfigDir, managedPath }) => {
    const settingsPath = path.join(repoRoot, '.claude', 'settings.local.json');
    const raw = '{"env":{"A":"1","A":"2"}}\n';
    await writeFile(settingsPath, raw, 'utf8');
    const result = runCli(['--apply', '--scope', 'project', '--root', repoRoot, '--claude-config-dir', claudeConfigDir, '--managed-settings', managedPath]);
    assert.equal(result.status, 1, result.stdout + result.stderr);
    assert.match(result.stderr, /duplicate JSON key/u);
    assert.equal(readFileSync(settingsPath, 'utf8'), raw);
  });
});

test('CLI refuses a symlink settings target before writing', { skip: process.platform === 'win32' }, async () => {
  await withCliFixture(async ({ directory, repoRoot, claudeConfigDir, managedPath }) => {
    const target = path.join(directory, 'operator-settings.json');
    const settingsPath = path.join(repoRoot, '.claude', 'settings.local.json');
    await writeFile(target, '{"model":"keep"}\n', 'utf8');
    await import('node:fs/promises').then(({ symlink }) => symlink(target, settingsPath));
    const result = runCli(['--apply', '--scope', 'project', '--root', repoRoot, '--claude-config-dir', claudeConfigDir, '--managed-settings', managedPath]);
    assert.equal(result.status, 1);
    assert.match(result.stderr, /symlink/u);
    assert.equal(await readFile(target, 'utf8'), '{"model":"keep"}\n');
  });
});
