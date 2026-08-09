#!/usr/bin/env node

import { randomBytes } from 'node:crypto';
import {
  chmod, lstat, mkdir, readFile, rename, rm, writeFile,
} from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  applyOwnedSettings,
  desiredOwnedSettings,
  discoverSettingScopes,
  emptyOwnership,
  inspectContinuity,
  parseStrictObject,
  probeClaudeCapabilities,
  removeOwnedSettings,
} from './settings.mjs';


const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const SKILL_ROOT = path.dirname(SCRIPT_DIR);


function parseArgs(argv) {
  const options = {
    operation: null,
    scope: null,
    root: process.cwd(),
    claudeConfigDir: process.env.CLAUDE_CONFIG_DIR ?? path.join(os.homedir(), '.claude'),
    managedSettings: null,
    claudeBin: 'claude',
    statusLine: false,
  };
  const operations = new Map([
    ['--check', 'check'],
    ['--apply', 'apply'],
    ['--remove-owned', 'remove-owned'],
  ]);
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    if (operations.has(argument)) {
      if (options.operation) throw new Error('exactly one operation is required');
      options.operation = operations.get(argument);
      continue;
    }
    if (argument === '--status-line') {
      options.statusLine = true;
      continue;
    }
    const fields = new Map([
      ['--scope', 'scope'],
      ['--root', 'root'],
      ['--claude-config-dir', 'claudeConfigDir'],
      ['--managed-settings', 'managedSettings'],
      ['--claude-bin', 'claudeBin'],
    ]);
    if (!fields.has(argument) || index + 1 >= argv.length) throw new Error(`unknown or incomplete argument: ${argument}`);
    options[fields.get(argument)] = argv[index + 1];
    index += 1;
  }
  if (!options.operation || !['project', 'user'].includes(options.scope)) {
    throw new Error('one operation and --scope project|user are required');
  }
  if (options.statusLine && options.operation === 'remove-owned') {
    throw new Error('--status-line is not valid with --remove-owned');
  }
  options.root = path.resolve(options.root);
  options.claudeConfigDir = path.resolve(options.claudeConfigDir);
  if (options.managedSettings) options.managedSettings = path.resolve(options.managedSettings);
  return options;
}


async function pathInfo(target) {
  try {
    return await lstat(target);
  } catch (error) {
    if (error?.code === 'ENOENT') return null;
    throw error;
  }
}


async function rejectSymlinkPath(target) {
  let current = path.resolve(target);
  const root = path.parse(current).root;
  const chain = [];
  while (current !== root) {
    chain.push(current);
    current = path.dirname(current);
  }
  chain.push(root);
  for (const candidate of chain.reverse()) {
    const info = await pathInfo(candidate);
    if (info?.isSymbolicLink()) throw new Error(`refusing symlink path: ${candidate}`);
  }
}


async function readJsonObject(target, absent) {
  await rejectSymlinkPath(target);
  const info = await pathInfo(target);
  if (!info) return structuredClone(absent);
  if (!info.isFile()) throw new Error(`settings path is not a regular file: ${target}`);
  return parseStrictObject(await readFile(target, 'utf8'), target);
}


function serialized(value) {
  return `${JSON.stringify(value, null, 2)}\n`;
}


async function prepareAtomic(target, value) {
  await rejectSymlinkPath(target);
  await mkdir(path.dirname(target), { recursive: true, mode: 0o700 });
  await rejectSymlinkPath(path.dirname(target));
  const temporary = `${target}.${process.pid}.${randomBytes(8).toString('hex')}.tmp`;
  await writeFile(temporary, serialized(value), { encoding: 'utf8', mode: 0o600, flag: 'wx' });
  await chmod(temporary, 0o600);
  return temporary;
}


async function restoreOriginal(target, original) {
  if (original === null) {
    await rm(target, { force: true });
    return;
  }
  const temporary = `${target}.${process.pid}.${randomBytes(8).toString('hex')}.restore`;
  await writeFile(temporary, original, { mode: 0o600, flag: 'wx' });
  await chmod(temporary, 0o600);
  await rename(temporary, target);
}


async function readOriginal(target) {
  const info = await pathInfo(target);
  if (!info) return null;
  if (!info.isFile() || info.isSymbolicLink()) throw new Error(`refusing unsafe target: ${target}`);
  return readFile(target);
}


async function commitPair(settingsPath, settings, ownershipPath, ownership) {
  const originalOwnership = await readOriginal(ownershipPath);
  const settingsTemporary = await prepareAtomic(settingsPath, settings);
  let ownershipTemporary;
  try {
    ownershipTemporary = await prepareAtomic(ownershipPath, ownership);
    await rename(ownershipTemporary, ownershipPath);
    if (process.env.CONTEXT_CONTINUITY_TEST_CRASH_AFTER_OWNERSHIP === '1') process.exit(86);
    try {
      await rename(settingsTemporary, settingsPath);
    } catch (error) {
      await restoreOriginal(ownershipPath, originalOwnership);
      throw error;
    }
  } finally {
    await rm(settingsTemporary, { force: true });
    if (ownershipTemporary) await rm(ownershipTemporary, { force: true });
  }
}


function publicReport({ operation, scope, settingsPath, inspection, capabilities, conflicts = [] }) {
  return {
    schemaVersion: 1,
    operation,
    scope,
    settingsPath,
    autoCompactEnabled: inspection.effective.autoCompactEnabled,
    autoCompactPercent: inspection.effective.autoCompactPercent,
    desired: inspection.desired,
    configured: inspection.configured,
    owned: inspection.owned,
    hooks: inspection.hooks,
    statusLine: {
      requested: inspection.statusLine.requested,
      owned: inspection.statusLine.owned,
      matches: inspection.statusLine.matches,
      conflict: inspection.statusLine.conflict || conflicts.includes('statusLine'),
    },
    capabilities,
    blockers: inspection.blockers.map(({ code, scope: blockerScope }) => ({ code, scope: blockerScope })),
    actions: inspection.actions.map(({ code, scope: actionScope }) => ({ code, scope: actionScope })),
    conflicts,
  };
}


async function execute(options) {
  const scopes = discoverSettingScopes({
    repoRoot: options.root,
    claudeConfigDir: options.claudeConfigDir,
    managedPath: options.managedSettings,
  });
  for (const scope of scopes) scope.settings = await readJsonObject(scope.path, {});
  const target = scopes.find(({ name }) => name === (options.scope === 'project' ? 'local' : 'user'));
  const ownershipPath = path.join(path.dirname(target.path), '.context-continuity-owned.json');
  const ownership = await readJsonObject(ownershipPath, emptyOwnership(options.scope));
  const desired = desiredOwnedSettings({ skillRoot: SKILL_ROOT, includeStatusLine: options.statusLine });
  let inspection = inspectContinuity({ scopes, desired, ownership, processEnv: process.env });
  const capabilities = probeClaudeCapabilities({ claudeBin: options.claudeBin });
  if (options.operation === 'check') {
    return { exitCode: inspection.blockers.length || inspection.actions.length ? 2 : 0, report: publicReport({ operation: options.operation, scope: options.scope, settingsPath: target.path, inspection, capabilities }) };
  }
  if (options.operation === 'apply') {
    if (inspection.blockers.length) return { exitCode: 2, report: publicReport({ operation: options.operation, scope: options.scope, settingsPath: target.path, inspection, capabilities }) };
    const applied = applyOwnedSettings({
      current: target.settings,
      ownership,
      desired,
      effectivePercent: inspection.effective.autoCompactPercent,
    });
    await commitPair(target.path, applied.settings, ownershipPath, applied.ownership);
    target.settings = applied.settings;
    inspection = inspectContinuity({ scopes, desired, ownership: applied.ownership, processEnv: process.env });
    return { exitCode: 0, report: publicReport({ operation: options.operation, scope: options.scope, settingsPath: target.path, inspection, capabilities }) };
  }
  const removed = removeOwnedSettings({ current: target.settings, ownership });
  await commitPair(target.path, removed.settings, ownershipPath, removed.ownership);
  target.settings = removed.settings;
  inspection = inspectContinuity({ scopes, desired: desiredOwnedSettings({ skillRoot: SKILL_ROOT }), ownership: removed.ownership, processEnv: process.env });
  return { exitCode: removed.conflicts.length ? 2 : 0, report: publicReport({ operation: options.operation, scope: options.scope, settingsPath: target.path, inspection, capabilities, conflicts: removed.conflicts }) };
}


export async function main({ argv = process.argv.slice(2), output = process.stdout, error = process.stderr } = {}) {
  try {
    const result = await execute(parseArgs(argv));
    output.write(`${JSON.stringify(result.report)}\n`);
    return result.exitCode;
  } catch (caught) {
    error.write(`Context continuity configuration failed: ${caught instanceof Error ? caught.message : 'unknown error'}\n`);
    return 1;
  }
}


if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  process.exitCode = await main();
}
