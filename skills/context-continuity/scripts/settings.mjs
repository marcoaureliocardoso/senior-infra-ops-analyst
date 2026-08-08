import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { isDeepStrictEqual } from 'node:util';


const MAX_JSON_BYTES = 1024 * 1024;
const MAX_JSON_DEPTH = 64;
export const OWNERSHIP_VERSION = 1;
export const DEFAULT_PERCENT = '72';
export const ALLOWED_PERCENT = Object.freeze(new Set(['70', '71', '72', '73', '74', '75']));


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


export function parseStrictObject(text, source = 'JSON') {
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


function platformPath(platform) {
  return platform === 'win32' ? path.win32 : path.posix;
}


function managedSettingsPath(platform) {
  if (platform === 'win32') return 'C:\\Program Files\\ClaudeCode\\managed-settings.json';
  if (platform === 'darwin') return '/Library/Application Support/ClaudeCode/managed-settings.json';
  return '/etc/claude-code/managed-settings.json';
}


export function discoverSettingScopes({
  repoRoot,
  claudeConfigDir,
  platform = process.platform,
  managedPath,
}) {
  const paths = platformPath(platform);
  return Object.freeze([
    { name: 'user', path: paths.join(claudeConfigDir, 'settings.json'), precedence: 1, writable: true },
    { name: 'project', path: paths.join(repoRoot, '.claude', 'settings.json'), precedence: 2, writable: true },
    { name: 'local', path: paths.join(repoRoot, '.claude', 'settings.local.json'), precedence: 3, writable: true },
    { name: 'managed', path: managedPath ?? managedSettingsPath(platform), precedence: 5, writable: false },
  ]);
}


function validateCommandPath(value, platform) {
  if (typeof value !== 'string' || value.length === 0 || value.length > 4096 || /[\r\n\0]/u.test(value)) {
    throw new Error('unsafe command path');
  }
  const unsafe = platform === 'win32' ? /["&|<>%^!]/u : /[';&|<>`$()]/u;
  if (unsafe.test(value)) throw new Error('unsafe command path');
  return value;
}


export function quoteStatusCommand(nodeBin, scriptPath, platform = process.platform) {
  const node = validateCommandPath(nodeBin, platform);
  const script = validateCommandPath(scriptPath, platform);
  if (platform === 'win32') return `"${node}" "${script}"`;
  return `'${node}' '${script}'`;
}


export function desiredOwnedSettings({
  skillRoot,
  includeStatusLine = false,
  nodeBin = process.execPath,
  platform = process.platform,
}) {
  const paths = platformPath(platform);
  const launcher = paths.join(skillRoot, 'scripts', 'compact-hook-launcher.sh');
  const desired = {
    env: { CLAUDE_AUTOCOMPACT_PCT_OVERRIDE: DEFAULT_PERCENT },
    hooks: {
      PreCompact: [{
        hooks: [{ type: 'command', command: launcher, args: ['pre'], timeout: 5 }],
      }],
      PostCompact: [{
        hooks: [{ type: 'command', command: launcher, args: ['post'], timeout: 5 }],
      }],
    },
  };
  if (includeStatusLine) {
    desired.statusLine = {
      type: 'command',
      command: quoteStatusCommand(
        nodeBin,
        paths.join(skillRoot, 'scripts', 'context-statusline.mjs'),
        platform,
      ),
    };
  }
  return desired;
}


export function emptyOwnership(scope) {
  return { version: OWNERSHIP_VERSION, scope, values: {} };
}


function cloneObject(value) {
  return value === undefined ? undefined : structuredClone(value);
}


function assertSettingsObject(value) {
  if (value === null || Array.isArray(value) || typeof value !== 'object') {
    throw new Error('settings root must be an object');
  }
}


function disableValue(value) {
  return value !== undefined && value !== null && !['', '0', 'false'].includes(String(value).toLowerCase());
}


function assertAutoCompact(settings) {
  if (settings.autoCompactEnabled === false || disableValue(settings.env?.DISABLE_AUTO_COMPACT) || disableValue(settings.env?.DISABLE_COMPACT)) {
    throw new Error('AUTO_COMPACT_DISABLED');
  }
  const percent = settings.env?.CLAUDE_AUTOCOMPACT_PCT_OVERRIDE;
  if (percent !== undefined && !ALLOWED_PERCENT.has(String(percent))) {
    throw new Error('AUTOCOMPACT_PERCENT_CONFLICT');
  }
}


function addOwnedHook(settings, ownership, event, group) {
  settings.hooks ??= {};
  const current = settings.hooks[event];
  if (current !== undefined && !Array.isArray(current)) throw new Error(`HOOKS_CONFLICT:${event}`);
  settings.hooks[event] ??= [];
  const exists = settings.hooks[event].some((item) => isDeepStrictEqual(item, group));
  const ownedPath = `hooks.${event}`;
  const alreadyOwned = Array.isArray(ownership.values[ownedPath]) &&
    ownership.values[ownedPath].some((item) => isDeepStrictEqual(item, group));
  if (!exists) {
    settings.hooks[event].push(cloneObject(group));
    ownership.values[ownedPath] ??= [];
    ownership.values[ownedPath].push(cloneObject(group));
  } else if (alreadyOwned) {
    ownership.values[ownedPath] = ownership.values[ownedPath].filter((item) =>
      isDeepStrictEqual(item, group));
  }
}


export function applyOwnedSettings({ current, ownership, desired }) {
  assertSettingsObject(current);
  assertSettingsObject(desired);
  assertAutoCompact(current);
  const settings = cloneObject(current);
  const owned = cloneObject(ownership ?? emptyOwnership('project'));
  if (owned.version !== OWNERSHIP_VERSION || typeof owned.values !== 'object' || owned.values === null || Array.isArray(owned.values)) {
    throw new Error('OWNERSHIP_CONFLICT');
  }

  settings.env ??= {};
  if (settings.env === null || Array.isArray(settings.env) || typeof settings.env !== 'object') throw new Error('ENV_CONFLICT');
  const existingPercent = settings.env.CLAUDE_AUTOCOMPACT_PCT_OVERRIDE;
  if (existingPercent === undefined) {
    settings.env.CLAUDE_AUTOCOMPACT_PCT_OVERRIDE = desired.env.CLAUDE_AUTOCOMPACT_PCT_OVERRIDE;
    owned.values['env.CLAUDE_AUTOCOMPACT_PCT_OVERRIDE'] = desired.env.CLAUDE_AUTOCOMPACT_PCT_OVERRIDE;
  }

  for (const [event, groups] of Object.entries(desired.hooks ?? {})) {
    for (const group of groups) addOwnedHook(settings, owned, event, group);
  }

  if (desired.statusLine !== undefined) {
    if (settings.statusLine === undefined) {
      settings.statusLine = cloneObject(desired.statusLine);
      owned.values.statusLine = cloneObject(desired.statusLine);
    } else if (!isDeepStrictEqual(settings.statusLine, desired.statusLine)) {
      throw new Error('STATUS_LINE_CONFLICT');
    }
  }

  return { settings, ownership: owned };
}


function removeOwnedScalar(settings, ownership, propertyPath, container, key, conflicts) {
  if (!(propertyPath in ownership.values)) return;
  if (isDeepStrictEqual(container?.[key], ownership.values[propertyPath])) {
    delete container[key];
    delete ownership.values[propertyPath];
  } else if (container?.[key] === undefined) {
    delete ownership.values[propertyPath];
  } else {
    conflicts.push(propertyPath);
  }
}


export function removeOwnedSettings({ current, ownership }) {
  assertSettingsObject(current);
  const settings = cloneObject(current);
  const owned = cloneObject(ownership ?? emptyOwnership('project'));
  const conflicts = [];
  removeOwnedScalar(
    settings,
    owned,
    'env.CLAUDE_AUTOCOMPACT_PCT_OVERRIDE',
    settings.env,
    'CLAUDE_AUTOCOMPACT_PCT_OVERRIDE',
    conflicts,
  );
  for (const event of ['PreCompact', 'PostCompact']) {
    const propertyPath = `hooks.${event}`;
    const ownedGroups = owned.values[propertyPath];
    if (!Array.isArray(ownedGroups)) continue;
    if (Array.isArray(settings.hooks?.[event])) {
      settings.hooks[event] = settings.hooks[event].filter((group) =>
        !ownedGroups.some((ownedGroup) => isDeepStrictEqual(ownedGroup, group)));
      if (settings.hooks[event].length === 0) delete settings.hooks[event];
    }
    delete owned.values[propertyPath];
  }
  removeOwnedScalar(settings, owned, 'statusLine', settings, 'statusLine', conflicts);
  if (settings.env && Object.keys(settings.env).length === 0) delete settings.env;
  if (settings.hooks && Object.keys(settings.hooks).length === 0) delete settings.hooks;
  return { settings, ownership: owned, conflicts };
}


function effectiveEnvironment(scopes) {
  const effective = {};
  for (const scope of [...scopes].sort((left, right) => left.precedence - right.precedence)) {
    if (scope.settings?.env && typeof scope.settings.env === 'object' && !Array.isArray(scope.settings.env)) {
      Object.assign(effective, scope.settings.env);
    }
  }
  return effective;
}


function effectiveScalar(scopes, key, fallback) {
  let value = fallback;
  for (const scope of [...scopes].sort((left, right) => left.precedence - right.precedence)) {
    if (scope.settings && key in scope.settings) value = scope.settings[key];
  }
  return value;
}


export function inspectContinuity({ scopes, desired, ownership, processEnv = process.env }) {
  const environment = effectiveEnvironment(scopes);
  const blockers = [];
  const disabled = effectiveScalar(scopes, 'autoCompactEnabled', true) === false ||
    disableValue(environment.DISABLE_AUTO_COMPACT) ||
    disableValue(environment.DISABLE_COMPACT) ||
    disableValue(processEnv.DISABLE_AUTO_COMPACT) ||
    disableValue(processEnv.DISABLE_COMPACT);
  const rawPercent = processEnv.CLAUDE_AUTOCOMPACT_PCT_OVERRIDE ?? environment.CLAUDE_AUTOCOMPACT_PCT_OVERRIDE;
  if (disabled) blockers.push({ code: 'AUTO_COMPACT_DISABLED', scope: 'effective' });
  if (rawPercent !== undefined && !ALLOWED_PERCENT.has(String(rawPercent))) {
    blockers.push({ code: 'AUTOCOMPACT_PERCENT_CONFLICT', scope: 'effective' });
  }
  if (processEnv.CLAUDE_CODE_AUTO_COMPACT_WINDOW ?? environment.CLAUDE_CODE_AUTO_COMPACT_WINDOW) {
    blockers.push({ code: 'ABSOLUTE_WINDOW_REQUIRES_EVIDENCE', scope: 'effective' });
  }
  return {
    schemaVersion: 1,
    effective: {
      autoCompactEnabled: !disabled,
      autoCompactPercent: rawPercent === undefined ? Number(DEFAULT_PERCENT) : Number(rawPercent),
    },
    hooks: {
      preCompact: Boolean(desired?.hooks?.PreCompact),
      postCompact: Boolean(desired?.hooks?.PostCompact),
    },
    statusLine: {
      requested: desired?.statusLine !== undefined,
      owned: Boolean(ownership?.values?.statusLine),
    },
    blockers,
  };
}


function defaultCapabilityRun(binary, args) {
  return spawnSync(binary, args, {
    encoding: 'utf8',
    timeout: 2000,
    maxBuffer: 128 * 1024,
    windowsHide: true,
    env: {
      PATH: process.env.PATH,
      PATHEXT: process.env.PATHEXT,
      SystemRoot: process.env.SystemRoot,
    },
  });
}


export function probeClaudeCapabilities({ claudeBin = 'claude', run = defaultCapabilityRun } = {}) {
  const unavailable = () => ({
    available: false,
    observedVersion: null,
    resume: false,
    agent: false,
    mcp: false,
    printStreamJson: false,
    rewind: false,
    taskTools: 'unknown',
    toolSearch: 'unknown',
    reasonCode: 'CLAUDE_CLI_UNAVAILABLE',
  });
  const help = run(claudeBin, ['--help']);
  if (help?.status !== 0 || typeof help.stdout !== 'string') return unavailable();
  const mcp = run(claudeBin, ['mcp', '--help']);
  const version = run(claudeBin, ['--version']);
  if (version?.status !== 0 || typeof version.stdout !== 'string') return unavailable();
  const observedVersion = version.stdout.match(/\b\d+(?:\.\d+){1,3}\b/u)?.[0] ?? null;
  return {
    available: true,
    observedVersion,
    resume: /(?:^|\s)--resume(?:\s|,|$)/u.test(help.stdout),
    agent: /(?:^|\s)--agent(?:\s|,|$)/u.test(help.stdout),
    mcp: mcp?.status === 0 && /\bmcp\b/u.test(mcp.stdout ?? ''),
    printStreamJson: /--output-format\b/u.test(help.stdout) && /\bstream-json\b/u.test(help.stdout),
    rewind: /(?:^|\s)--rewind(?:\s|,|$)/u.test(help.stdout),
    taskTools: 'unknown',
    toolSearch: 'unknown',
    reasonCode: 'CAPABILITIES_OBSERVED',
  };
}
