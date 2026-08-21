#!/usr/bin/env node

import { randomBytes } from 'node:crypto';
import {
  chmod, lstat, mkdir, open, readFile, rename, rmdir, rm, unlink,
} from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { isDeepStrictEqual } from 'node:util';

import {
  applyOwnedMainSessionHooks,
  desiredMainSessionHooks,
  emptyMainSessionOwnership,
  inspectMainSessionGuard,
  parseStrictSettings,
  removeOwnedMainSessionHooks,
} from './main-session-settings.mjs';


const SCRIPT_PATH = fileURLToPath(import.meta.url);
const SKILL_ROOT = path.dirname(path.dirname(SCRIPT_PATH));
const LOCK_WAIT_MS = 1500;
const LOCK_POLL_MS = 25;
const FILE_MODE = 0o600;
const DIR_MODE = 0o700;
const NAMES = Object.freeze({
  ownership: '.p0-05-native-execution-owned.json',
  transaction: '.p0-05-native-execution.transaction.json',
  lock: '.p0-05-native-execution.lock',
});


function usage() {
  return 'Usage: configure-native-execution-boundary.mjs --check | --apply | --remove-owned [--root PATH]\n';
}


function parseArgs(argv) {
  if (argv.includes('--help')) return { operation: 'help' };
  const options = { operation: null, root: process.cwd(), managedSettings: null };
  const operations = new Map([
    ['--check', 'check'],
    ['--apply', 'apply'],
    ['--remove-owned', 'remove-owned'],
  ]);
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    if (operations.has(argument)) {
      if (options.operation) throw new Error('INVALID_INVOCATION');
      options.operation = operations.get(argument);
      continue;
    }
    if (['--root', '--managed-settings'].includes(argument) && index + 1 < argv.length) {
      const field = argument === '--root' ? 'root' : 'managedSettings';
      options[field] = argv[index + 1];
      index += 1;
      continue;
    }
    throw new Error('INVALID_INVOCATION');
  }
  if (!options.operation) throw new Error('INVALID_INVOCATION');
  options.root = path.resolve(options.root);
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


async function rejectLinkedPath(target) {
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
    if (info?.isSymbolicLink()) throw new Error('UNSAFE_LINKED_PATH');
  }
}


async function readObject(target, absent) {
  await rejectLinkedPath(target);
  const info = await pathInfo(target);
  if (!info) return { value: structuredClone(absent), raw: null };
  if (!info.isFile()) throw new Error('UNSAFE_NON_REGULAR_FILE');
  const raw = await readFile(target);
  return {
    value: parseStrictSettings(raw.toString('utf8'), path.basename(target)),
    raw,
  };
}


function serialized(value) {
  return `${JSON.stringify(value, null, 2)}\n`;
}


async function writeDurableFile(target, value, flag = 'wx') {
  await rejectLinkedPath(target);
  const handle = await open(target, flag, FILE_MODE);
  try {
    await handle.writeFile(serialized(value), 'utf8');
    await handle.sync();
  } finally {
    await handle.close();
  }
  await chmod(target, FILE_MODE);
}


async function atomicReplace(target, value) {
  await mkdir(path.dirname(target), { recursive: true, mode: DIR_MODE });
  await rejectLinkedPath(path.dirname(target));
  const temporary = `${target}.${process.pid}.${randomBytes(8).toString('hex')}.tmp`;
  try {
    await writeDurableFile(temporary, value);
    await rejectLinkedPath(target);
    await rename(temporary, target);
  } finally {
    await rm(temporary, { force: true });
  }
}


function rawEqual(left, right) {
  if (left === null || right === null) return left === right;
  return left.equals(right);
}


async function recheckRaw(target, expected) {
  const current = await readObject(target, {});
  if (!rawEqual(current.raw, expected)) throw new Error('CONCURRENT_TARGET_CHANGE');
}


function processIsAlive(pid) {
  try {
    process.kill(pid, 0);
    return true;
  } catch (error) {
    return error?.code !== 'ESRCH';
  }
}


async function tryRemoveStaleLock(lockPath) {
  const ownerPath = path.join(lockPath, 'owner.json');
  try {
    const owner = (await readObject(ownerPath, null)).value;
    if (!Number.isInteger(owner?.pid) || owner.pid < 1 || processIsAlive(owner.pid)) return false;
    await unlink(ownerPath);
    await rmdir(lockPath);
    return true;
  } catch {
    return false;
  }
}


async function acquireLock(lockPath) {
  const deadline = Date.now() + LOCK_WAIT_MS;
  while (true) {
    try {
      await rejectLinkedPath(lockPath);
      await mkdir(lockPath, { mode: DIR_MODE });
      try {
        await writeDurableFile(path.join(lockPath, 'owner.json'), {
          version: 1,
          pid: process.pid,
          createdAt: Date.now(),
        });
      } catch (error) {
        await rmdir(lockPath).catch(() => {});
        throw error;
      }
      return async () => {
        await unlink(path.join(lockPath, 'owner.json')).catch(() => {});
        await rmdir(lockPath).catch(() => {});
      };
    } catch (error) {
      if (error?.code !== 'EEXIST') throw error;
      if (await tryRemoveStaleLock(lockPath)) continue;
      if (Date.now() >= deadline) throw new Error('LOCK_CONTENTION');
      await new Promise((resolve) => setTimeout(resolve, LOCK_POLL_MS));
    }
  }
}


function desiredEntriesPresent(settings, ownership) {
  return ownership.entries.every(({ event, group }) =>
    Array.isArray(settings.hooks?.[event]) &&
    settings.hooks[event].some((candidate) => isDeepStrictEqual(candidate, group)));
}


async function cleanupTransaction(transactionPath, ownershipTemporary) {
  await rm(transactionPath, { force: true });
  if (ownershipTemporary) await rm(ownershipTemporary, { force: true });
}


async function recoverTransaction(paths, desired) {
  const transactionInfo = await readObject(paths.transaction, null);
  if (transactionInfo.raw === null) return false;
  const transaction = transactionInfo.value;
  if (transaction?.version !== 1 || !['apply', 'remove-owned'].includes(transaction.operation) ||
      typeof transaction.ownershipTemporary !== 'string' ||
      path.basename(transaction.ownershipTemporary) !== transaction.ownershipTemporary) {
    throw new Error('TRANSACTION_CONFLICT');
  }
  const ownershipTemporary = path.join(paths.directory, transaction.ownershipTemporary);
  const planned = await readObject(ownershipTemporary, null);
  if (planned.raw === null) throw new Error('TRANSACTION_CONFLICT');
  const settings = await readObject(paths.settings, {});
  const ownership = await readObject(paths.ownership, emptyMainSessionOwnership());
  const plannedPresent = planned.value.entries.length > 0
    ? desiredEntriesPresent(settings.value, planned.value)
    : !desired.hooks.some(({ event, group }) =>
      settings.value.hooks?.[event]?.some((candidate) => isDeepStrictEqual(candidate, group)));
  if (plannedPresent) {
    await rename(ownershipTemporary, paths.ownership);
  } else if (planned.value.entries.length > 0) {
    const rolledBack = removeOwnedMainSessionHooks({
      current: settings.value,
      ownership: planned.value,
    });
    if (rolledBack.conflicts.length) throw new Error('TRANSACTION_CONFLICT');
    await atomicReplace(paths.settings, rolledBack.settings);
  } else if (ownership.value.entries.length > 0) {
    const restored = structuredClone(settings.value);
    restored.hooks ??= {};
    for (const entry of ownership.value.entries) {
      restored.hooks[entry.event] ??= [];
      if (!restored.hooks[entry.event].some((group) => isDeepStrictEqual(group, entry.group))) {
        restored.hooks[entry.event].push(structuredClone(entry.group));
      }
    }
    await atomicReplace(paths.settings, restored);
  }
  await cleanupTransaction(paths.transaction, ownershipTemporary);
  return true;
}


async function commitPair(paths, operation, settingsSnapshot, ownershipSnapshot, next) {
  const ownershipTemporary = `${paths.ownership}.${process.pid}.${randomBytes(8).toString('hex')}.next`;
  await writeDurableFile(ownershipTemporary, next.ownership);
  try {
    await atomicReplace(paths.transaction, {
      version: 1,
      operation,
      phase: 'PREPARED',
      ownershipTemporary: path.basename(ownershipTemporary),
    });
    await recheckRaw(paths.settings, settingsSnapshot);
    await recheckRaw(paths.ownership, ownershipSnapshot);
    await atomicReplace(paths.settings, next.settings);
    await atomicReplace(paths.transaction, {
      version: 1,
      operation,
      phase: 'SETTINGS_COMMITTED',
      ownershipTemporary: path.basename(ownershipTemporary),
    });
    if (process.env.P005_TEST_CRASH_AFTER_SETTINGS === '1') process.exit(86);
    await rename(ownershipTemporary, paths.ownership);
    await rm(paths.transaction, { force: true });
  } finally {
    await rm(ownershipTemporary, { force: true });
  }
}


function publicReport(operation, inspection, changed, conflicts = []) {
  return {
    schemaVersion: 1,
    operation,
    state: inspection.state,
    reasonCode: inspection.reasonCode,
    preHookExact: inspection.preHookExact,
    postHookExact: inspection.postHookExact,
    liveProof: false,
    changed,
    conflicts,
  };
}


function exitFor(operation, inspection, conflicts = []) {
  if (conflicts.length || ['CONFLICT', 'UNSUPPORTED'].includes(inspection.state)) return 3;
  if (operation === 'remove-owned' && inspection.state === 'ABSENT') return 0;
  if (inspection.state === 'ACTIVE') return 0;
  return 2;
}


async function execute(options) {
  const directory = path.join(options.root, '.claude');
  const paths = {
    directory,
    settings: path.join(directory, 'settings.local.json'),
    ownership: path.join(directory, NAMES.ownership),
    transaction: path.join(directory, NAMES.transaction),
    lock: path.join(directory, NAMES.lock),
  };
  const desired = desiredMainSessionHooks({
    skillRoot: SKILL_ROOT,
    runtimeIdentity: 'runtime-capability-detected',
  });
  await rejectLinkedPath(options.root);
  if (options.operation === 'check') {
    const directoryInfo = await pathInfo(directory);
    if (directoryInfo && !directoryInfo.isDirectory()) {
      throw new Error('UNSAFE_NON_REGULAR_FILE');
    }
    if (directoryInfo) await rejectLinkedPath(directory);
    const settings = directoryInfo
      ? await readObject(paths.settings, {})
      : { value: {}, raw: null };
    const ownership = directoryInfo
      ? await readObject(paths.ownership, emptyMainSessionOwnership())
      : { value: emptyMainSessionOwnership(), raw: null };
    const scopes = [{ name: 'local', precedence: 3, settings: settings.value }];
    if (options.managedSettings) {
      scopes.push({
        name: 'managed', precedence: 5,
        settings: (await readObject(options.managedSettings, {})).value,
      });
    }
    const inspection = inspectMainSessionGuard({
      scopes, desired, ownership: ownership.value, capabilities: { hooks: true },
    });
    return {
      code: exitFor(options.operation, inspection),
      report: publicReport(options.operation, inspection, false),
    };
  }
  await mkdir(directory, { recursive: true, mode: DIR_MODE });
  await rejectLinkedPath(directory);
  const release = await acquireLock(paths.lock);
  try {
    await recoverTransaction(paths, desired);
    const settings = await readObject(paths.settings, {});
    const ownership = await readObject(paths.ownership, emptyMainSessionOwnership());
    const scopes = [{ name: 'local', precedence: 3, settings: settings.value }];
    if (options.managedSettings) {
      scopes.push({
        name: 'managed', precedence: 5,
        settings: (await readObject(options.managedSettings, {})).value,
      });
    }
    let inspection = inspectMainSessionGuard({
      scopes, desired, ownership: ownership.value, capabilities: { hooks: true },
    });
    const next = options.operation === 'apply'
      ? applyOwnedMainSessionHooks({ current: settings.value, desired, ownership: ownership.value })
      : removeOwnedMainSessionHooks({ current: settings.value, ownership: ownership.value });
    const conflicts = next.conflicts ?? [];
    const changed = !isDeepStrictEqual(next.settings, settings.value) ||
      !isDeepStrictEqual(next.ownership, ownership.value);
    if (changed) {
      await commitPair(paths, options.operation, settings.raw, ownership.raw, next);
    }
    scopes[0].settings = next.settings;
    inspection = inspectMainSessionGuard({
      scopes, desired, ownership: next.ownership, capabilities: { hooks: true },
    });
    return {
      code: exitFor(options.operation, inspection, conflicts),
      report: publicReport(options.operation, inspection, changed, conflicts),
    };
  } finally {
    await release();
  }
}


export async function main({ argv = process.argv.slice(2), output = process.stdout, error = process.stderr } = {}) {
  let options;
  try {
    options = parseArgs(argv);
  } catch {
    error.write(usage());
    return 64;
  }
  if (options.operation === 'help') {
    output.write(usage());
    return 0;
  }
  try {
    const result = await execute(options);
    output.write(`${JSON.stringify(result.report)}\n`);
    return result.code;
  } catch (caught) {
    const code = caught instanceof Error ? caught.message.split(':', 1)[0] : 'UNKNOWN_ERROR';
    error.write(`Native execution boundary configuration failed: ${code}\n`);
    return 3;
  }
}


if (process.argv[1] && path.resolve(process.argv[1]) === SCRIPT_PATH) {
  process.exitCode = await main();
}
