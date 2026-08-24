import { createHash } from 'node:crypto';
import path from 'node:path';
import { isDeepStrictEqual } from 'node:util';


const MAX_JSON_BYTES = 1024 * 1024;
const MAX_JSON_DEPTH = 64;
const MAX_IDENTITY_CHARS = 256;
const MAX_PATH_CHARS = 4096;
const OWNERSHIP_VERSION = 1;
const PROBE_COMMAND = 'printf P005_GUARD_PROBE';
const PROBE_REASON = 'DENY_UNKNOWN_COMMAND';


function strictScan(text, source) {
  let index = 0;
  const fail = (message) => {
    throw new Error(`${source}: ${message} at byte ${index}`);
  };
  const skipWhitespace = () => {
    while (/\s/u.test(text[index] ?? '')) index += 1;
  };
  const scanString = () => {
    const start = index;
    if (text[index] !== '"') fail('expected JSON string');
    index += 1;
    while (index < text.length) {
      const character = text[index];
      if (character === '"') {
        index += 1;
        try {
          return JSON.parse(text.slice(start, index));
        } catch {
          fail('invalid JSON string');
        }
      }
      if (character === '\\') {
        index += 1;
        if (text[index] === 'u') {
          if (!/^[0-9a-fA-F]{4}$/u.test(text.slice(index + 1, index + 5))) {
            fail('invalid Unicode escape');
          }
          index += 5;
          continue;
        }
        if (!/["\\/bfnrt]/u.test(text[index] ?? '')) fail('invalid JSON escape');
        index += 1;
        continue;
      }
      if (character.codePointAt(0) < 0x20) fail('control character in JSON string');
      index += 1;
    }
    fail('unterminated JSON string');
  };
  const scanLiteral = (literal) => {
    if (text.slice(index, index + literal.length) !== literal) fail('invalid JSON value');
    index += literal.length;
  };
  const scanNumber = () => {
    const match = text.slice(index).match(/^-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?/u);
    if (!match) fail('invalid JSON number');
    index += match[0].length;
  };
  const scanValue = (depth) => {
    if (depth > MAX_JSON_DEPTH) fail('JSON nesting exceeds limit');
    skipWhitespace();
    switch (text[index]) {
      case '{': scanObject(depth + 1); return;
      case '[': scanArray(depth + 1); return;
      case '"': scanString(); return;
      case 't': scanLiteral('true'); return;
      case 'f': scanLiteral('false'); return;
      case 'n': scanLiteral('null'); return;
      default: scanNumber();
    }
  };
  const scanObject = (depth) => {
    const keys = new Set();
    index += 1;
    skipWhitespace();
    if (text[index] === '}') { index += 1; return; }
    while (index < text.length) {
      skipWhitespace();
      const key = scanString();
      if (keys.has(key)) fail(`duplicate JSON key ${JSON.stringify(key)}`);
      keys.add(key);
      skipWhitespace();
      if (text[index] !== ':') fail('expected colon after object key');
      index += 1;
      scanValue(depth);
      skipWhitespace();
      if (text[index] === '}') { index += 1; return; }
      if (text[index] !== ',') fail('expected comma between object members');
      index += 1;
    }
    fail('unterminated JSON object');
  };
  const scanArray = (depth) => {
    index += 1;
    skipWhitespace();
    if (text[index] === ']') { index += 1; return; }
    while (index < text.length) {
      scanValue(depth);
      skipWhitespace();
      if (text[index] === ']') { index += 1; return; }
      if (text[index] !== ',') fail('expected comma between array items');
      index += 1;
    }
    fail('unterminated JSON array');
  };

  scanValue(0);
  skipWhitespace();
  if (index !== text.length) fail('unexpected trailing JSON data');
}


export function parseStrictSettings(text, source = 'settings JSON') {
  if (typeof text !== 'string' || Buffer.byteLength(text, 'utf8') > MAX_JSON_BYTES) {
    throw new Error(`${source}: JSON input exceeds limit`);
  }
  strictScan(text, source);
  const parsed = JSON.parse(text);
  if (parsed === null || Array.isArray(parsed) || typeof parsed !== 'object') {
    throw new Error(`${source}: JSON root must be an object`);
  }
  return parsed;
}


function boundedIdentity(value, label) {
  if (typeof value !== 'string' || value.length === 0 ||
      value.length > MAX_IDENTITY_CHARS || /[\r\n\0]/u.test(value)) {
    throw new Error(`${label} must be a non-empty bounded string`);
  }
  return value;
}


function launcherPath(skillRoot, platform) {
  if (!['win32', 'linux', 'darwin'].includes(platform)) {
    throw new Error('unsupported platform');
  }
  const paths = platform === 'win32' ? path.win32 : path.posix;
  if (typeof skillRoot !== 'string' || skillRoot.length === 0 ||
      skillRoot.length > MAX_PATH_CHARS || /[\r\n\0]/u.test(skillRoot)) {
    throw new Error('skillRoot must be a bounded path');
  }
  const root = skillRoot;
  if (!paths.isAbsolute(root)) throw new Error('skillRoot must be absolute');
  const unsafe = platform === 'win32' ? /["&|<>%^!;]/u : /[';&|<>`$()]/u;
  if (unsafe.test(root)) throw new Error('skillRoot contains shell control characters');
  return paths.join(root, 'scripts', 'command-guard-launcher.sh');
}


function desiredIdentity(hooks, runtimeIdentity) {
  const structure = JSON.stringify({
    schemaVersion: 1,
    runtimeIdentity: boundedIdentity(runtimeIdentity, 'runtimeIdentity'),
    hooks,
  });
  return createHash('sha256').update(structure).digest('hex');
}


export function desiredMainSessionHooks({
  skillRoot,
  platform = process.platform,
  runtimeIdentity = 'runtime-unobserved',
}) {
  const command = launcherPath(skillRoot, platform);
  const hooks = ['PreToolUse', 'PostToolUse'].map((event, index) => ({
    event,
    matcher: 'Bash',
    group: {
      matcher: 'Bash',
      hooks: [{
        type: 'command',
        command,
        args: [index === 0 ? 'pre' : 'post'],
        timeout: 7,
      }],
    },
  }));
  return Object.freeze({
    schemaVersion: 1,
    runtimeIdentity,
    hooks: Object.freeze(hooks),
    configurationIdentity: desiredIdentity(hooks, runtimeIdentity),
  });
}


export function emptyMainSessionOwnership() {
  return { version: OWNERSHIP_VERSION, scope: 'local', configurationIdentity: null, entries: [] };
}


function assertObject(value, label) {
  if (value === null || Array.isArray(value) || typeof value !== 'object') {
    throw new Error(`${label} must be an object`);
  }
}


function validateDesired(desired) {
  assertObject(desired, 'desired hooks');
  const runtimeIdentity = boundedIdentity(desired.runtimeIdentity, 'runtimeIdentity');
  if (desired.schemaVersion !== 1 || typeof desired.configurationIdentity !== 'string' ||
      !/^[a-f0-9]{64}$/u.test(desired.configurationIdentity) || !Array.isArray(desired.hooks)) {
    throw new Error('DESIRED_HOOKS_INCOMPLETE');
  }
  const identities = desired.hooks.map(({ event, matcher }) => `${event}:${matcher}`);
  if (!isDeepStrictEqual(identities, ['PreToolUse:Bash', 'PostToolUse:Bash'])) {
    throw new Error('DESIRED_HOOKS_INCOMPLETE');
  }
  for (const item of desired.hooks) {
    if (!isDeepStrictEqual(item.group?.matcher, 'Bash') ||
        !Array.isArray(item.group?.hooks) || item.group.hooks.length !== 1 ||
        item.group.hooks[0]?.type !== 'command' ||
        item.group.hooks[0]?.timeout !== 7 ||
        !isDeepStrictEqual(item.group.hooks[0]?.args, [item.event === 'PreToolUse' ? 'pre' : 'post'])) {
      throw new Error('DESIRED_HOOKS_INCOMPLETE');
    }
  }
  if (desiredIdentity(desired.hooks, runtimeIdentity) !== desired.configurationIdentity) {
    throw new Error('DESIRED_HOOKS_INCOMPLETE');
  }
}


function validateOwnership(ownership) {
  assertObject(ownership, 'ownership');
  if (ownership.version !== OWNERSHIP_VERSION || ownership.scope !== 'local' ||
      !Array.isArray(ownership.entries) ||
      (ownership.configurationIdentity !== null &&
       (typeof ownership.configurationIdentity !== 'string' ||
        !/^[a-f0-9]{64}$/u.test(ownership.configurationIdentity)))) {
    throw new Error('OWNERSHIP_CONFLICT');
  }
  const seen = new Set();
  for (const entry of ownership.entries) {
    if (!['PreToolUse', 'PostToolUse'].includes(entry?.event) ||
        entry?.group === null || typeof entry?.group !== 'object' || Array.isArray(entry?.group)) {
      throw new Error('OWNERSHIP_CONFLICT');
    }
    if (seen.has(entry.event)) throw new Error('OWNERSHIP_CONFLICT');
    seen.add(entry.event);
  }
}


function clone(value) {
  return structuredClone(value);
}


function exactEntry(ownership, desiredHook) {
  return ownership.entries.find(({ event, group }) =>
    event === desiredHook.event && isDeepStrictEqual(group, desiredHook.group));
}


export function applyOwnedMainSessionHooks({ current, desired, ownership }) {
  assertObject(current, 'settings root');
  validateDesired(desired);
  validateOwnership(ownership);
  if (ownership.entries.length > 0 &&
      ownership.configurationIdentity !== desired.configurationIdentity) {
    throw new Error('OWNERSHIP_DRIFT');
  }
  const settings = clone(current);
  const owned = clone(ownership);
  settings.hooks ??= {};
  assertObject(settings.hooks, 'settings hooks');

  for (const desiredHook of desired.hooks) {
    const configured = settings.hooks[desiredHook.event];
    if (configured !== undefined && !Array.isArray(configured)) {
      throw new Error(`HOOKS_CONFLICT:${desiredHook.event}`);
    }
    settings.hooks[desiredHook.event] ??= [];
    const present = settings.hooks[desiredHook.event].some((group) =>
      isDeepStrictEqual(group, desiredHook.group));
    const ownedEntry = exactEntry(owned, desiredHook);
    if (ownedEntry && !present) throw new Error(`OWNERSHIP_DRIFT:${desiredHook.event}`);
    if (!ownedEntry && present) {
      throw new Error(`HOOK_ALREADY_PRESENT_UNOWNED:${desiredHook.event}`);
    }
    if (!present) {
      settings.hooks[desiredHook.event].push(clone(desiredHook.group));
      owned.entries.push({ event: desiredHook.event, group: clone(desiredHook.group) });
    }
  }
  owned.configurationIdentity = desired.configurationIdentity;
  return { settings, ownership: owned };
}


export function removeOwnedMainSessionHooks({ current, ownership }) {
  assertObject(current, 'settings root');
  validateOwnership(ownership);
  const settings = clone(current);
  const owned = clone(ownership);
  const conflicts = [];
  const remaining = [];
  for (const entry of owned.entries) {
    const groups = settings.hooks?.[entry.event];
    if (groups === undefined) continue;
    if (!Array.isArray(groups)) {
      conflicts.push(`hooks.${entry.event}`);
      remaining.push(entry);
      continue;
    }
    const index = groups.findIndex((group) => isDeepStrictEqual(group, entry.group));
    if (index < 0) {
      conflicts.push(`hooks.${entry.event}`);
      remaining.push(entry);
      continue;
    }
    groups.splice(index, 1);
    if (groups.length === 0) delete settings.hooks[entry.event];
  }
  if (settings.hooks && Object.keys(settings.hooks).length === 0) delete settings.hooks;
  owned.entries = remaining;
  if (remaining.length === 0) owned.configurationIdentity = null;
  return { settings, ownership: owned, conflicts };
}


function hookPresent(scopes, desiredHook) {
  return scopes.some((scope) =>
    Array.isArray(scope?.settings?.hooks?.[desiredHook.event]) &&
    scope.settings.hooks[desiredHook.event].some((group) =>
      isDeepStrictEqual(group, desiredHook.group)));
}


function effectiveScalar(scopes, key) {
  let value;
  for (const scope of [...scopes].sort((left, right) => left.precedence - right.precedence)) {
    if (scope?.settings && Object.hasOwn(scope.settings, key)) value = scope.settings[key];
  }
  return value;
}


function inspection(state, reasonCode, preHookExact, postHookExact, liveProof) {
  return { state, reasonCode, preHookExact, postHookExact, liveProof };
}


export function inspectMainSessionGuard({
  scopes,
  desired,
  ownership,
  capabilities,
  liveProof,
}) {
  if (!Array.isArray(scopes)) throw new Error('scopes must be an array');
  validateDesired(desired);
  validateOwnership(ownership);
  const preHookExact = hookPresent(scopes, desired.hooks[0]);
  const postHookExact = hookPresent(scopes, desired.hooks[1]);
  if (capabilities?.hooks !== true) {
    return inspection('UNSUPPORTED', 'CAPABILITY_UNAVAILABLE', preHookExact, postHookExact, false);
  }
  if (effectiveScalar(scopes, 'allowManagedHooksOnly') === true ||
      effectiveScalar(scopes, 'disableAllHooks') === true) {
    return inspection('CONFLICT', 'MANAGED_POLICY_BLOCK', preHookExact, postHookExact, false);
  }
  const ownershipExact = ownership.configurationIdentity === desired.configurationIdentity &&
    desired.hooks.every((item) => Boolean(exactEntry(ownership, item)));
  if (!preHookExact || !postHookExact) {
    if (ownership.entries.length > 0) {
      return inspection('CONFLICT', 'OWNERSHIP_DRIFT', preHookExact, postHookExact, false);
    }
    return inspection('ABSENT', 'MISSING_HOOKS', preHookExact, postHookExact, false);
  }
  if (!ownershipExact) {
    return inspection('CONFLICT', 'OWNERSHIP_DRIFT', preHookExact, postHookExact, false);
  }
  const proofExact = liveProof?.command === PROBE_COMMAND &&
    liveProof?.decision === 'deny' && liveProof?.reasonCode === PROBE_REASON &&
    liveProof?.configurationIdentity === desired.configurationIdentity;
  if (!proofExact) {
    return inspection(
      'CONFIGURED_UNPROVEN', 'EXACT_SETTINGS_ONLY', preHookExact, postHookExact, false,
    );
  }
  return inspection('ACTIVE', 'EXACT_LIVE_PROOF', preHookExact, postHookExact, true);
}
