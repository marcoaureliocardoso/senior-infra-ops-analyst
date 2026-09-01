import { createHash } from 'node:crypto';
import path from 'node:path';
import { isDeepStrictEqual } from 'node:util';


const OWNERSHIP_VERSION = 1;
const BROWSER_MCP_MATCHER = 'mcp__playwright__browser_(navigate|snapshot|type|click)';
const EVENTS = Object.freeze([
  ['PreToolUse', 'pre'],
  ['PostToolUse', 'post'],
  ['PostToolUseFailure', 'failure'],
]);


function clone(value) {
  return structuredClone(value);
}


function object(value, code) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error(code);
  return value;
}


function launcherPath(skillRoot, platform) {
  if (!['win32', 'linux', 'darwin'].includes(platform)) throw new Error('UNSUPPORTED_PLATFORM');
  const paths = platform === 'win32' ? path.win32 : path.posix;
  if (typeof skillRoot !== 'string' || skillRoot.length < 1 || skillRoot.length > 4096
      || /[\r\n\0]/u.test(skillRoot) || !paths.isAbsolute(skillRoot)) {
    throw new Error('INVALID_SKILL_ROOT');
  }
  const unsafe = platform === 'win32' ? /["&|<>%^!;]/u : /[';&|<>`$()]/u;
  if (unsafe.test(skillRoot)) throw new Error('UNSAFE_SKILL_ROOT');
  return paths.join(skillRoot, 'scripts', 'browser-hook-launcher.sh');
}


function identity(hooks) {
  return createHash('sha256').update(JSON.stringify({ schemaVersion: 1, hooks }), 'utf8').digest('hex');
}


export function desiredBrowserHooks({ skillRoot, platform = process.platform }) {
  const command = launcherPath(skillRoot, platform);
  const hooks = EVENTS.map(([event, mode]) => Object.freeze({
    event,
    group: Object.freeze({
      matcher: BROWSER_MCP_MATCHER,
      hooks: Object.freeze([Object.freeze({
        type: 'command', command, args: Object.freeze([mode]), timeout: 9,
      })]),
    }),
  }));
  return Object.freeze({
    schemaVersion: 1,
    hooks: Object.freeze(hooks),
    configurationIdentity: identity(hooks),
  });
}


export function emptyBrowserOwnership() {
  return {
    version: OWNERSHIP_VERSION,
    scope: 'local',
    configurationIdentity: null,
    entries: [],
    liveProof: null,
    createdSettingsFile: false,
  };
}


function validateDesired(desired) {
  object(desired, 'INVALID_DESIRED_HOOKS');
  if (desired.schemaVersion !== 1 || !Array.isArray(desired.hooks)
      || desired.hooks.length !== EVENTS.length
      || !/^[a-f0-9]{64}$/u.test(desired.configurationIdentity ?? '')) {
    throw new Error('INVALID_DESIRED_HOOKS');
  }
  for (let index = 0; index < EVENTS.length; index += 1) {
    const [event, mode] = EVENTS[index];
    const item = desired.hooks[index];
    if (item?.event !== event || item?.group?.matcher !== BROWSER_MCP_MATCHER
        || !Array.isArray(item.group.hooks) || item.group.hooks.length !== 1
        || item.group.hooks[0]?.type !== 'command'
        || typeof item.group.hooks[0]?.command !== 'string'
        || !item.group.hooks[0].command.endsWith('browser-hook-launcher.sh')
        || !isDeepStrictEqual(item.group.hooks[0]?.args, [mode])
        || item.group.hooks[0]?.timeout !== 9) throw new Error('INVALID_DESIRED_HOOKS');
  }
  if (identity(desired.hooks) !== desired.configurationIdentity) {
    throw new Error('INVALID_DESIRED_HOOKS');
  }
}


function validateOwnership(ownership) {
  object(ownership, 'OWNERSHIP_CONFLICT');
  if (ownership.version !== OWNERSHIP_VERSION || ownership.scope !== 'local'
      || !Array.isArray(ownership.entries)
      || (ownership.configurationIdentity !== null
        && !/^[a-f0-9]{64}$/u.test(ownership.configurationIdentity ?? ''))
      || (ownership.liveProof !== null
        && (!ownership.liveProof || typeof ownership.liveProof !== 'object'
          || Array.isArray(ownership.liveProof)))
      || typeof ownership.createdSettingsFile !== 'boolean') throw new Error('OWNERSHIP_CONFLICT');
  const seen = new Set();
  for (const entry of ownership.entries) {
    if (!EVENTS.some(([event]) => event === entry?.event)
        || !entry.group || typeof entry.group !== 'object' || Array.isArray(entry.group)
        || seen.has(entry.event)) throw new Error('OWNERSHIP_CONFLICT');
    seen.add(entry.event);
  }
}


function exactOwned(ownership, desiredHook) {
  return ownership.entries.some((entry) =>
    entry.event === desiredHook.event && isDeepStrictEqual(entry.group, desiredHook.group));
}


export function applyOwnedBrowserHooks({ current, desired, ownership }) {
  object(current, 'INVALID_SETTINGS');
  validateDesired(desired);
  validateOwnership(ownership);
  if (ownership.entries.length > 0
      && ownership.configurationIdentity !== desired.configurationIdentity) {
    throw new Error('OWNERSHIP_DRIFT');
  }
  const settings = clone(current);
  const owned = clone(ownership);
  settings.hooks ??= {};
  object(settings.hooks, 'HOOKS_CONFLICT');
  for (const item of desired.hooks) {
    const groups = settings.hooks[item.event];
    if (groups !== undefined && !Array.isArray(groups)) throw new Error(`HOOKS_CONFLICT:${item.event}`);
    settings.hooks[item.event] ??= [];
    const present = settings.hooks[item.event].some((group) => isDeepStrictEqual(group, item.group));
    const ownedExact = exactOwned(owned, item);
    if (ownedExact && !present) throw new Error(`OWNERSHIP_DRIFT:${item.event}`);
    if (!ownedExact && present) throw new Error(`HOOK_ALREADY_PRESENT_UNOWNED:${item.event}`);
    if (!present) {
      settings.hooks[item.event].push(clone(item.group));
      owned.entries.push({ event: item.event, group: clone(item.group) });
    }
  }
  owned.configurationIdentity = desired.configurationIdentity;
  owned.liveProof ??= null;
  return { settings, ownership: owned };
}


export function removeOwnedBrowserHooks({ current, desired, ownership }) {
  object(current, 'INVALID_SETTINGS');
  validateDesired(desired);
  validateOwnership(ownership);
  if (ownership.entries.length > 0 && (
    ownership.configurationIdentity !== desired.configurationIdentity
      || ownership.entries.some((entry) => !desired.hooks.some((item) =>
        entry.event === item.event && isDeepStrictEqual(entry.group, item.group))))) {
    throw new Error('OWNERSHIP_DRIFT');
  }
  const settings = clone(current);
  const conflicts = [];
  const remaining = [];
  for (const entry of ownership.entries) {
    const groups = settings.hooks?.[entry.event];
    if (!Array.isArray(groups)) {
      conflicts.push(`hooks.${entry.event}`);
      remaining.push(clone(entry));
      continue;
    }
    const index = groups.findIndex((group) => isDeepStrictEqual(group, entry.group));
    if (index < 0) {
      conflicts.push(`hooks.${entry.event}`);
      remaining.push(clone(entry));
      continue;
    }
    groups.splice(index, 1);
    if (groups.length === 0) delete settings.hooks[entry.event];
  }
  if (settings.hooks && Object.keys(settings.hooks).length === 0) delete settings.hooks;
  const owned = remaining.length === 0 ? emptyBrowserOwnership() : {
    ...clone(ownership), entries: remaining, liveProof: null,
  };
  return { settings, ownership: owned, conflicts };
}


function exactConfigured(current, desired) {
  return desired.hooks.map((item) =>
    Array.isArray(current.hooks?.[item.event])
    && current.hooks[item.event].some((group) => isDeepStrictEqual(group, item.group)));
}


export function inspectBrowserSettings({ current, desired, ownership }) {
  object(current, 'INVALID_SETTINGS');
  validateDesired(desired);
  validateOwnership(ownership);
  if (current.disableAllHooks === true || current.allowManagedHooksOnly === true) {
    return { state: 'CONFLICT', reasonCode: 'MANAGED_POLICY_BLOCK', hookCount: 0, liveProof: false };
  }
  const configured = exactConfigured(current, desired);
  const hookCount = configured.filter(Boolean).length;
  if (hookCount === 0 && ownership.entries.length === 0) {
    return { state: 'NOT_CONFIGURED', reasonCode: 'MISSING_HOOKS', hookCount, liveProof: false };
  }
  const ownershipExact = ownership.configurationIdentity === desired.configurationIdentity
    && desired.hooks.every((item) => exactOwned(ownership, item));
  if (!configured.every(Boolean) || !ownershipExact) {
    return { state: 'CONFLICT', reasonCode: 'OWNERSHIP_DRIFT', hookCount, liveProof: false };
  }
  const proof = ownership.liveProof;
  const proofExact = proof?.configurationIdentity === desired.configurationIdentity
    && proof?.capabilityState === 'ACTIVE'
    && ['allow', 'ask', 'deny'].includes(proof?.decision)
    && typeof proof?.reasonCode === 'string' && proof.reasonCode.length <= 128;
  if (!proofExact) {
    return { state: 'CONFIGURED_UNPROVEN', reasonCode: 'EXACT_SETTINGS_ONLY', hookCount, liveProof: false };
  }
  return { state: 'ACTIVE', reasonCode: 'EXACT_LIVE_PROOF', hookCount, liveProof: true };
}
