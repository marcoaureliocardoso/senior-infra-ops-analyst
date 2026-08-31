#!/usr/bin/env node

import { randomBytes } from 'node:crypto';
import {
  chmod, lstat, mkdir, open, readFile, rename, rmdir, rm, unlink,
} from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { parseStrictSettings } from '../../command-driven-operations/scripts/main-session-settings.mjs';
import {
  applyOwnedBrowserHooks,
  desiredBrowserHooks,
  emptyBrowserOwnership,
  inspectBrowserSettings,
  removeOwnedBrowserHooks,
} from './browser-main-session-settings.mjs';


const SCRIPT = fileURLToPath(import.meta.url);
const SKILL_ROOT = path.dirname(path.dirname(SCRIPT));
const MODE_FILE = 0o600;
const MODE_DIRECTORY = 0o700;
const LOCK_WAIT_MS = 1500;
const LOCK_POLL_MS = 25;
const NAMES = Object.freeze({
  ownership: '.p0-04b-browser-operations-owned.json',
  transaction: '.p0-04b-browser-operations.transaction.json',
  lock: '.p0-04b-browser-operations.lock',
});


function usage() {
  return 'Usage: configure-browser-operations.mjs --check | --apply | --remove-owned [--root PATH]\n';
}


function parseArgs(argv) {
  if (argv.length === 1 && argv[0] === '--help') return { operation: 'help' };
  const result = { operation: null, root: process.cwd() };
  const operations = new Map([
    ['--check', 'check'], ['--apply', 'apply'], ['--remove-owned', 'remove-owned'],
  ]);
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    if (operations.has(argument)) {
      if (result.operation) throw new Error('INVALID_INVOCATION');
      result.operation = operations.get(argument);
    } else if (argument === '--root' && index + 1 < argv.length) {
      result.root = argv[index + 1];
      index += 1;
    } else throw new Error('INVALID_INVOCATION');
  }
  if (!result.operation) throw new Error('INVALID_INVOCATION');
  result.root = path.resolve(result.root);
  return result;
}


async function info(target) {
  try {
    return await lstat(target);
  } catch (error) {
    if (error?.code === 'ENOENT') return null;
    throw error;
  }
}


async function rejectLinks(target) {
  let current = path.resolve(target);
  const root = path.parse(current).root;
  const chain = [];
  while (current !== root) {
    chain.push(current);
    current = path.dirname(current);
  }
  chain.push(root);
  for (const candidate of chain.reverse()) {
    const state = await info(candidate);
    if (state?.isSymbolicLink()) throw new Error('UNSAFE_LINKED_PATH');
  }
}


async function readObject(target, absent) {
  await rejectLinks(target);
  const state = await info(target);
  if (!state) return { value: structuredClone(absent), raw: null };
  if (!state.isFile() || state.isSymbolicLink()) throw new Error('UNSAFE_NON_REGULAR_FILE');
  const raw = await readFile(target);
  return {
    value: parseStrictSettings(raw.toString('utf8'), path.basename(target)), raw,
  };
}


function serialized(value) {
  return `${JSON.stringify(value, null, 2)}\n`;
}


async function atomicReplace(target, value) {
  const directory = path.dirname(target);
  await rejectLinks(directory);
  await mkdir(directory, { recursive: true, mode: MODE_DIRECTORY });
  await chmod(directory, MODE_DIRECTORY);
  await rejectLinks(target);
  const temporary = `${target}.${process.pid}.${randomBytes(8).toString('hex')}.tmp`;
  const handle = await open(temporary, 'wx', MODE_FILE);
  try {
    await handle.writeFile(serialized(value), 'utf8');
    await handle.sync();
  } finally {
    await handle.close();
  }
  await chmod(temporary, MODE_FILE);
  try {
    await rename(temporary, target);
  } finally {
    await rm(temporary, { force: true });
  }
}


function alive(pid) {
  try {
    process.kill(pid, 0);
    return true;
  } catch (error) {
    return error?.code !== 'ESRCH';
  }
}


async function removeStaleLock(lock) {
  try {
    const owner = (await readObject(path.join(lock, 'owner.json'), null)).value;
    if (!Number.isSafeInteger(owner?.pid) || owner.pid < 1 || alive(owner.pid)) return false;
    await unlink(path.join(lock, 'owner.json'));
    await rmdir(lock);
    return true;
  } catch {
    return false;
  }
}


async function acquireLock(lock) {
  const deadline = Date.now() + LOCK_WAIT_MS;
  while (true) {
    try {
      await rejectLinks(lock);
      await mkdir(lock, { mode: MODE_DIRECTORY });
      await atomicReplace(path.join(lock, 'owner.json'), {
        version: 1, pid: process.pid, createdAt: Date.now(),
      });
      return async () => {
        await unlink(path.join(lock, 'owner.json')).catch(() => {});
        await rmdir(lock).catch(() => {});
      };
    } catch (error) {
      if (error?.code !== 'EEXIST') throw error;
      if (await removeStaleLock(lock)) continue;
      if (Date.now() >= deadline) throw new Error('LOCK_UNAVAILABLE');
      await new Promise((resolve) => setTimeout(resolve, LOCK_POLL_MS));
    }
  }
}


function sameRaw(left, right) {
  if (left === null || right === null) return left === right;
  return left.equals(right);
}


async function assertUnchanged(target, raw) {
  const current = await readObject(target, {});
  if (!sameRaw(current.raw, raw)) throw new Error('CONCURRENT_TARGET_CHANGE');
}


function exactHookPresence(settings, desired) {
  return desired.hooks.map((item) =>
    Array.isArray(settings.hooks?.[item.event])
    && settings.hooks[item.event].some((group) =>
      JSON.stringify(group) === JSON.stringify(item.group)));
}


async function recoverTransaction(paths, desired) {
  const transaction = await readObject(paths.transaction, null);
  if (transaction.raw === null) return;
  const value = transaction.value;
  if (value?.version !== 1 || !['apply', 'remove-owned'].includes(value.operation)
      || value.configurationIdentity !== desired.configurationIdentity
      || !value.nextOwnership || typeof value.nextOwnership !== 'object') {
    throw new Error('TRANSACTION_CONFLICT');
  }
  const settings = (await readObject(paths.settings, {})).value;
  const present = exactHookPresence(settings, desired);
  if (value.operation === 'apply' && present.every(Boolean)) {
    await atomicReplace(paths.ownership, value.nextOwnership);
  } else if (value.operation === 'remove-owned' && present.every((item) => !item)) {
    await unlink(paths.ownership).catch((error) => {
      if (error?.code !== 'ENOENT') throw error;
    });
  }
  await unlink(paths.transaction);
}


function pathsFor(root) {
  const claude = path.join(root, '.claude');
  return {
    claude,
    settings: path.join(claude, 'settings.local.json'),
    ownership: path.join(claude, NAMES.ownership),
    transaction: path.join(claude, NAMES.transaction),
    lock: path.join(claude, NAMES.lock),
  };
}


function publicReport(inspection, changed) {
  return {
    state: inspection.state,
    reasonCode: inspection.reasonCode,
    hookCount: inspection.hookCount,
    liveProof: inspection.liveProof,
    changed,
  };
}


async function inspect(paths, desired) {
  const settings = await readObject(paths.settings, {});
  const ownership = await readObject(paths.ownership, emptyBrowserOwnership());
  return {
    settings,
    ownership,
    inspection: inspectBrowserSettings({
      current: settings.value, desired, ownership: ownership.value,
    }),
  };
}


async function run(options) {
  const paths = pathsFor(options.root);
  const desired = desiredBrowserHooks({ skillRoot: SKILL_ROOT, platform: process.platform });
  if (options.operation === 'check') {
    const current = await inspect(paths, desired);
    return { report: publicReport(current.inspection, false), status: current.inspection.state === 'ACTIVE' ? 0 : 2 };
  }

  await rejectLinks(options.root);
  await mkdir(paths.claude, { recursive: true, mode: MODE_DIRECTORY });
  const release = await acquireLock(paths.lock);
  try {
    await recoverTransaction(paths, desired);
    const current = await inspect(paths, desired);
    const operation = options.operation;
    const changedValues = operation === 'apply'
      ? applyOwnedBrowserHooks({
        current: current.settings.value, desired, ownership: current.ownership.value,
      })
      : removeOwnedBrowserHooks({
        current: current.settings.value, ownership: current.ownership.value,
      });
    if (operation === 'apply' && current.settings.raw === null) {
      changedValues.ownership.createdSettingsFile = true;
    }
    if (operation === 'remove-owned' && changedValues.conflicts.length > 0) {
      throw new Error('OWNERSHIP_DRIFT');
    }
    const settingsChanged = JSON.stringify(changedValues.settings) !== JSON.stringify(current.settings.value);
    const ownershipChanged = JSON.stringify(changedValues.ownership) !== JSON.stringify(current.ownership.value);
    const changed = settingsChanged || ownershipChanged;
    if (changed) {
      await atomicReplace(paths.transaction, {
        version: 1,
        operation,
        configurationIdentity: desired.configurationIdentity,
        nextOwnership: changedValues.ownership,
      });
      await assertUnchanged(paths.settings, current.settings.raw);
      await assertUnchanged(paths.ownership, current.ownership.raw);
      if (process.env.P004B_TEST_FAIL_BEFORE_REPLACE === '1') throw new Error('INJECTED_FAILURE');
      const removeCreatedSettings = operation === 'remove-owned'
        && current.ownership.value.createdSettingsFile === true
        && Object.keys(changedValues.settings).length === 0;
      if (removeCreatedSettings) {
        await unlink(paths.settings).catch((error) => {
          if (error?.code !== 'ENOENT') throw error;
        });
      } else if (settingsChanged) await atomicReplace(paths.settings, changedValues.settings);
      if (process.env.P004B_TEST_CRASH_AFTER_SETTINGS === '1') process.exit(86);
      if (operation === 'remove-owned' && changedValues.ownership.entries.length === 0) {
        await unlink(paths.ownership).catch((error) => {
          if (error?.code !== 'ENOENT') throw error;
        });
      } else if (ownershipChanged) await atomicReplace(paths.ownership, changedValues.ownership);
      await unlink(paths.transaction);
    }
    const final = await inspect(paths, desired);
    const status = operation === 'remove-owned' ? 0 : final.inspection.state === 'ACTIVE' ? 0 : 2;
    return { report: publicReport(final.inspection, changed), status };
  } finally {
    await release();
  }
}


async function main() {
  let options;
  try {
    options = parseArgs(process.argv.slice(2));
  } catch {
    process.stderr.write(usage());
    return 64;
  }
  if (options.operation === 'help') {
    process.stdout.write(usage());
    return 0;
  }
  try {
    const result = await run(options);
    process.stdout.write(`${JSON.stringify(result.report)}\n`);
    return result.status;
  } catch {
    process.stderr.write('Browser operation configuration failed closed.\n');
    return 3;
  }
}


process.exitCode = await main();
