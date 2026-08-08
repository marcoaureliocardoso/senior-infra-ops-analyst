import { createHash, randomBytes } from 'node:crypto';
import {
  chmodSync, existsSync, lstatSync, mkdirSync, readFileSync, readdirSync, renameSync, writeFileSync,
} from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const VERSION = 1;
const TTL_MS = 15 * 60 * 1000;
const MAX_ENTRIES = 16;
const MAX_STATE_BYTES = 32 * 1024;
const BINDING_FIELDS = Object.freeze([
  'sessionId', 'toolUseId', 'domain', 'identity', 'transport', 'family', 'targetClass',
]);
const MATCH_FIELDS = Object.freeze([
  'sessionId', 'domain', 'identity', 'transport', 'family', 'targetClass',
]);

function requiredBounded(value, field) {
  if (typeof value !== 'string' || value.length === 0 || value.length > 512) {
    throw new Error(`invalid binding field:${field}`);
  }
  return value;
}

function normalizeBinding(binding) {
  return Object.fromEntries(BINDING_FIELDS.map((field) => [field, requiredBounded(binding[field], field)]));
}

function stateDirectory(env) {
  return path.resolve(env.OPS_COMMAND_GUARD_STATE_DIR ?? path.join(
    os.homedir(), '.claude', 'senior-infra-ops-analyst', 'command-guard-state',
  ));
}

export function resolveBindingStateDirectory(env = process.env) {
  return stateDirectory(env);
}

function statePath(sessionId, env) {
  const name = createHash('sha256').update(sessionId, 'utf8').digest('hex');
  return path.join(stateDirectory(env), `${name}.json`);
}

function emptyState() {
  return { version: VERSION, pending: [], active: [] };
}

function validateEntry(entry) {
  const normalized = normalizeBinding(entry);
  if (!Number.isSafeInteger(entry.expiresAt) || entry.expiresAt <= 0) throw new Error('invalid binding expiry');
  return { ...normalized, expiresAt: entry.expiresAt };
}

function readState(sessionId, env, now) {
  const target = statePath(sessionId, env);
  if (!existsSync(target)) return emptyState();
  const info = lstatSync(target);
  if (!info.isFile() || info.isSymbolicLink() || info.size > MAX_STATE_BYTES) throw new Error('unsafe binding state file');
  const parsed = JSON.parse(readFileSync(target, 'utf8'));
  if (parsed?.version !== VERSION || !Array.isArray(parsed.pending) || !Array.isArray(parsed.active)) {
    throw new Error('invalid binding state');
  }
  if (parsed.pending.length > MAX_ENTRIES || parsed.active.length > MAX_ENTRIES) throw new Error('binding state entry limit exceeded');
  return {
    version: VERSION,
    pending: parsed.pending.map(validateEntry).filter(({ expiresAt }) => expiresAt > now),
    active: parsed.active.map(validateEntry).filter(({ expiresAt }) => expiresAt > now),
  };
}

function atomicWriteTarget(target, state) {
  const temporary = `${target}.${process.pid}.${randomBytes(8).toString('hex')}.tmp`;
  const serialized = `${JSON.stringify(state)}\n`;
  if (Buffer.byteLength(serialized, 'utf8') > MAX_STATE_BYTES) throw new Error('binding state size exceeded');
  writeFileSync(temporary, serialized, { encoding: 'utf8', mode: 0o600, flag: 'wx' });
  chmodSync(temporary, 0o600);
  renameSync(temporary, target);
}

function writeState(sessionId, state, env) {
  const directory = stateDirectory(env);
  if (!existsSync(directory)) mkdirSync(directory, { recursive: true, mode: 0o700 });
  const directoryInfo = lstatSync(directory);
  if (!directoryInfo.isDirectory()) throw new Error('unsafe binding state directory');
  chmodSync(directory, 0o700);
  atomicWriteTarget(statePath(sessionId, env), state);
}

function sameBinding(left, right, fields = MATCH_FIELDS) {
  return fields.every((field) => left[field] === right[field]);
}

export function writePendingBinding(binding, env = process.env, now = Date.now()) {
  const normalized = normalizeBinding(binding);
  const state = readState(normalized.sessionId, env, now);
  state.pending = state.pending.filter(({ toolUseId }) => toolUseId !== normalized.toolUseId);
  state.pending.push({ ...normalized, expiresAt: now + TTL_MS });
  if (state.pending.length > MAX_ENTRIES) state.pending.shift();
  writeState(normalized.sessionId, state, env);
  return true;
}

export function activatePendingBinding(binding, env = process.env, now = Date.now()) {
  const sessionId = requiredBounded(binding.sessionId, 'sessionId');
  const toolUseId = requiredBounded(binding.toolUseId, 'toolUseId');
  const state = readState(sessionId, env, now);
  const index = state.pending.findIndex((entry) => entry.toolUseId === toolUseId &&
    (!binding.domain || sameBinding(entry, binding)));
  if (index < 0) return false;
  const [pending] = state.pending.splice(index, 1);
  state.active = state.active.filter((entry) => !sameBinding(entry, pending));
  state.active.push({ ...pending, expiresAt: now + TTL_MS });
  if (state.active.length > MAX_ENTRIES) state.active.shift();
  writeState(sessionId, state, env);
  return true;
}

export function hasActiveBinding(binding, env = process.env, now = Date.now()) {
  const normalized = normalizeBinding(binding);
  const state = readState(normalized.sessionId, env, now);
  return state.active.some((entry) => sameBinding(entry, normalized));
}

export function invalidateSessionBindings(sessionId, env = process.env) {
  const bounded = requiredBounded(sessionId, 'sessionId');
  writeState(bounded, emptyState(), env);
  return true;
}

export function invalidateAllBindings(env = process.env) {
  const directory = stateDirectory(env);
  if (!existsSync(directory)) return 0;
  const directoryInfo = lstatSync(directory);
  if (!directoryInfo.isDirectory()) throw new Error('unsafe binding state directory');
  let invalidated = 0;
  for (const name of readdirSync(directory)) {
    if (!/^[a-f0-9]{64}\.json$/u.test(name)) continue;
    const target = path.join(directory, name);
    const info = lstatSync(target);
    if (!info.isFile()) continue;
    atomicWriteTarget(target, emptyState());
    invalidated += 1;
  }
  return invalidated;
}

export function bindingFromResult(result, event) {
  const scope = result.credentialBinding;
  if (!result.credential?.literal || !event.toolUseId || !scope?.domain || !scope.family || !scope.targetClass) return null;
  const assignment = event.command.match(/(?:^|\s)OPS_CREDENTIAL_IDENTITY=([A-Za-z0-9._@-]{1,128})(?:\s|$)/u)?.[1];
  const uriIdentity = event.command.match(/:\/\/([^\s:@/]+)(?::[^\s@/]*)?@/u)?.[1];
  const identity = assignment ?? uriIdentity;
  if (!identity) return null;
  return Object.freeze({
    sessionId: event.sessionId,
    toolUseId: event.toolUseId,
    domain: scope.domain,
    identity,
    transport: result.credential.transport,
    family: scope.family,
    targetClass: scope.targetClass,
  });
}
