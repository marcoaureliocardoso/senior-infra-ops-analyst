import { createHash, randomBytes } from 'node:crypto';
import {
  chmodSync, existsSync, lstatSync, mkdirSync, readFileSync, renameSync, rmdirSync,
  writeFileSync,
} from 'node:fs';
import os from 'node:os';
import path from 'node:path';

import { operationFingerprint, parseOperationEnvelope } from './browser-contract.mjs';


const VERSION = 1;
const MAX_ENTRIES = 16;
const MAX_STATE_BYTES = 128 * 1024;
const LOCK_ATTEMPTS = 400;
const LOCK_WAIT_MS = 5;
const IDENTIFIER = /^[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}$/u;


function bounded(value, code) {
  if (typeof value !== 'string' || !IDENTIFIER.test(value)) throw new Error(code);
  return value;
}


function stateDirectory(env) {
  return path.resolve(env.OPS_BROWSER_STATE_DIR ?? path.join(
    os.homedir(), '.claude', 'senior-infra-ops-analyst', 'browser-operation-state',
  ));
}


export function resolveBrowserStateDirectory(env = process.env) {
  return stateDirectory(env);
}


function statePath(sessionId, env) {
  const name = createHash('sha256').update(bounded(sessionId, 'INVALID_SESSION'), 'utf8').digest('hex');
  return path.join(stateDirectory(env), `${name}.json`);
}


function emptyState() {
  return { version: VERSION, pending: [], active: [], calls: [] };
}


function clone(value) {
  return structuredClone(value);
}


function validateStateEntry(entry, kind) {
  if (!entry || typeof entry !== 'object' || Array.isArray(entry)) throw new Error('INVALID_BROWSER_STATE');
  bounded(entry.sessionId, 'INVALID_BROWSER_STATE');
  bounded(entry.operationId, 'INVALID_BROWSER_STATE');
  if (!Number.isSafeInteger(entry.expiresAt) || entry.expiresAt <= 0) throw new Error('INVALID_BROWSER_STATE');
  if (kind === 'call') bounded(entry.toolUseId, 'INVALID_BROWSER_STATE');
  return entry;
}


function readState(sessionId, env, now) {
  const target = statePath(sessionId, env);
  if (!existsSync(target)) return emptyState();
  const info = lstatSync(target);
  if (!info.isFile() || info.isSymbolicLink() || info.size > MAX_STATE_BYTES) {
    throw new Error('UNSAFE_STATE_FILE');
  }
  const parsed = JSON.parse(readFileSync(target, 'utf8'));
  if (parsed?.version !== VERSION || !Array.isArray(parsed.pending)
      || !Array.isArray(parsed.active) || !Array.isArray(parsed.calls)
      || parsed.pending.length > MAX_ENTRIES || parsed.active.length > MAX_ENTRIES
      || parsed.calls.length > MAX_ENTRIES) throw new Error('INVALID_BROWSER_STATE');
  return {
    version: VERSION,
    pending: parsed.pending.map((entry) => validateStateEntry(entry, 'operation'))
      .filter(({ expiresAt }) => expiresAt > now),
    active: parsed.active.map((entry) => validateStateEntry(entry, 'operation'))
      .filter(({ expiresAt }) => expiresAt > now),
    calls: parsed.calls.map((entry) => validateStateEntry(entry, 'call'))
      .filter(({ expiresAt }) => expiresAt > now),
  };
}


function atomicWrite(target, state) {
  const serialized = `${JSON.stringify(state)}\n`;
  if (Buffer.byteLength(serialized, 'utf8') > MAX_STATE_BYTES) throw new Error('BROWSER_STATE_TOO_LARGE');
  const temporary = `${target}.${process.pid}.${randomBytes(8).toString('hex')}.tmp`;
  writeFileSync(temporary, serialized, { encoding: 'utf8', mode: 0o600, flag: 'wx' });
  chmodSync(temporary, 0o600);
  renameSync(temporary, target);
}


function waitForLock() {
  Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, LOCK_WAIT_MS);
}


function withLock(sessionId, env, operation) {
  const directory = stateDirectory(env);
  if (!existsSync(directory)) mkdirSync(directory, { recursive: true, mode: 0o700 });
  const info = lstatSync(directory);
  if (!info.isDirectory() || info.isSymbolicLink()) throw new Error('UNSAFE_STATE_DIRECTORY');
  chmodSync(directory, 0o700);
  const target = statePath(sessionId, env);
  const lock = `${target}.lock`;
  let acquired = false;
  for (let attempt = 0; attempt < LOCK_ATTEMPTS; attempt += 1) {
    try {
      mkdirSync(lock, { mode: 0o700 });
      acquired = true;
      break;
    } catch (error) {
      /* node:coverage disable */
      if (error?.code !== 'EEXIST') throw error;
      /* node:coverage enable */
      waitForLock();
    }
  }
  if (!acquired) throw new Error('BROWSER_STATE_LOCK_UNAVAILABLE');
  try {
    return operation(target);
  } finally {
    rmdirSync(lock);
  }
}


function pushBounded(entries, entry) {
  entries.push(entry);
  if (entries.length > MAX_ENTRIES) entries.shift();
}


function normalizedProof(proof) {
  const permissionModes = Array.isArray(proof?.permissionModes)
    ? [...new Set(proof.permissionModes)] : [];
  if (permissionModes.length < 1 || permissionModes.length > 6
      || permissionModes.some((mode) => typeof mode !== 'string' || mode.length > 64)) {
    throw new Error('INVALID_BROWSER_PROOF');
  }
  if (!proof.capability || typeof proof.capability !== 'object' || Array.isArray(proof.capability)) {
    throw new Error('INVALID_BROWSER_PROOF');
  }
  return {
    toolUseId: bounded(proof.toolUseId, 'INVALID_BROWSER_PROOF'),
    adapterId: bounded(proof.adapterId, 'INVALID_BROWSER_PROOF'),
    routeClass: bounded(proof.routeClass, 'INVALID_BROWSER_PROOF'),
    settingsFingerprint: bounded(proof.settingsFingerprint, 'INVALID_BROWSER_PROOF'),
    permissionModes,
    capability: clone(proof.capability),
  };
}


export function writePendingOperation(envelopeValue, proofValue, env = process.env, now = Date.now()) {
  const envelope = parseOperationEnvelope(envelopeValue, now);
  const proof = normalizedProof(proofValue);
  return withLock(envelope.sessionId, env, (target) => {
    const state = readState(envelope.sessionId, env, now);
    state.pending = state.pending.filter(({ operationId, toolUseId }) =>
      operationId !== envelope.operationId && toolUseId !== proof.toolUseId);
    pushBounded(state.pending, {
      sessionId: envelope.sessionId,
      operationId: envelope.operationId,
      role: envelope.role,
      envelope: clone(envelope),
      operationFingerprint: operationFingerprint(envelope),
      ...proof,
      expiresAt: envelope.expiresAt,
    });
    atomicWrite(target, state);
    return true;
  });
}


export function activateOperation(correlation, env = process.env, now = Date.now()) {
  const sessionId = bounded(correlation?.sessionId, 'INVALID_BROWSER_CORRELATION');
  const operationId = bounded(correlation?.operationId, 'INVALID_BROWSER_CORRELATION');
  const toolUseId = bounded(correlation?.toolUseId, 'INVALID_BROWSER_CORRELATION');
  return withLock(sessionId, env, (target) => {
    const state = readState(sessionId, env, now);
    const index = state.pending.findIndex((entry) =>
      entry.operationId === operationId && entry.toolUseId === toolUseId);
    if (index < 0) return false;
    const [pending] = state.pending.splice(index, 1);
    state.active = state.active.filter((entry) => entry.operationId !== operationId);
    pushBounded(state.active, {
      ...pending,
      active: true,
      outcome: 'READY',
      validationRequired: false,
    });
    atomicWrite(target, state);
    return true;
  });
}


export function readActiveOperation(sessionId, operationId, env = process.env, now = Date.now()) {
  const boundedSession = bounded(sessionId, 'INVALID_SESSION');
  const boundedOperation = bounded(operationId, 'INVALID_OPERATION');
  const state = readState(boundedSession, env, now);
  const entry = state.active.find((candidate) => candidate.operationId === boundedOperation);
  return entry ? Object.freeze(clone(entry)) : null;
}


export function readSingleActiveOperation(sessionId, env = process.env, now = Date.now()) {
  const boundedSession = bounded(sessionId, 'INVALID_SESSION');
  const state = readState(boundedSession, env, now);
  if (state.active.length !== 1) return null;
  return Object.freeze(clone(state.active[0]));
}


export function stageBrowserCall(sessionId, operationId, call, env = process.env, now = Date.now()) {
  const boundedSession = bounded(sessionId, 'INVALID_SESSION');
  const boundedOperation = bounded(operationId, 'INVALID_OPERATION');
  const toolUseId = bounded(call?.toolUseId, 'INVALID_BROWSER_CALL');
  const action = bounded(call?.action, 'INVALID_BROWSER_CALL');
  const effect = bounded(call?.effect, 'INVALID_BROWSER_CALL');
  return withLock(boundedSession, env, (target) => {
    const state = readState(boundedSession, env, now);
    const operation = state.active.find((entry) => entry.operationId === boundedOperation);
    if (!operation || operation.outcome !== 'READY') return false;
    state.calls = state.calls.filter((entry) => entry.toolUseId !== toolUseId);
    pushBounded(state.calls, {
      sessionId: boundedSession,
      operationId: boundedOperation,
      toolUseId,
      action,
      effect,
      expiresAt: operation.expiresAt,
    });
    atomicWrite(target, state);
    return true;
  });
}


export function completeBrowserCall(sessionId, toolUseId, env = process.env, now = Date.now()) {
  const boundedSession = bounded(sessionId, 'INVALID_SESSION');
  const boundedToolUse = bounded(toolUseId, 'INVALID_BROWSER_CALL');
  return withLock(boundedSession, env, (target) => {
    const state = readState(boundedSession, env, now);
    const index = state.calls.findIndex((entry) => entry.toolUseId === boundedToolUse);
    if (index < 0) return false;
    const [call] = state.calls.splice(index, 1);
    const operation = state.active.find((entry) => entry.operationId === call.operationId);
    if (!operation) return false;
    if (!['PUBLIC_READ', 'SENSITIVE_READ'].includes(call.effect)) operation.validationRequired = true;
    atomicWrite(target, state);
    return true;
  });
}


export function recordOutcomeUnknown(sessionId, operationId, observation, env = process.env, now = Date.now()) {
  const boundedSession = bounded(sessionId, 'INVALID_SESSION');
  const boundedOperation = bounded(operationId, 'INVALID_OPERATION');
  const reasonCode = bounded(observation?.reasonCode, 'INVALID_OUTCOME');
  const action = bounded(observation?.action, 'INVALID_OUTCOME');
  const effect = bounded(observation?.effect, 'INVALID_OUTCOME');
  return withLock(boundedSession, env, (target) => {
    const state = readState(boundedSession, env, now);
    const operation = state.active.find((entry) => entry.operationId === boundedOperation);
    if (!operation) return false;
    operation.outcome = 'OUTCOME_UNKNOWN';
    operation.outcomeObservation = { reasonCode, action, effect, observedAt: now };
    operation.validationRequired = true;
    state.calls = state.calls.filter((entry) => entry.operationId !== boundedOperation);
    atomicWrite(target, state);
    return true;
  });
}


export function failBrowserCall(sessionId, toolUseId, reasonCode, env = process.env, now = Date.now()) {
  const boundedSession = bounded(sessionId, 'INVALID_SESSION');
  const boundedToolUse = bounded(toolUseId, 'INVALID_BROWSER_CALL');
  const boundedReason = bounded(reasonCode, 'INVALID_OUTCOME');
  return withLock(boundedSession, env, (target) => {
    const state = readState(boundedSession, env, now);
    const index = state.calls.findIndex((entry) => entry.toolUseId === boundedToolUse);
    if (index < 0) return false;
    const [call] = state.calls.splice(index, 1);
    const operation = state.active.find((entry) => entry.operationId === call.operationId);
    if (!operation) return false;
    operation.outcome = 'OUTCOME_UNKNOWN';
    operation.outcomeObservation = {
      reasonCode: boundedReason, action: call.action, effect: call.effect, observedAt: now,
    };
    operation.validationRequired = true;
    atomicWrite(target, state);
    return true;
  });
}


export function clearOutcomeUnknown(sessionId, operationId, validationRef, env = process.env, now = Date.now()) {
  const boundedSession = bounded(sessionId, 'INVALID_SESSION');
  const boundedOperation = bounded(operationId, 'INVALID_OPERATION');
  const boundedValidation = bounded(validationRef, 'INVALID_VALIDATION');
  return withLock(boundedSession, env, (target) => {
    const state = readState(boundedSession, env, now);
    const operation = state.active.find((entry) => entry.operationId === boundedOperation);
    if (!operation || operation.outcome !== 'OUTCOME_UNKNOWN'
        || operation.envelope.validationRef !== boundedValidation) return false;
    operation.outcome = 'READY';
    operation.validationRequired = false;
    delete operation.outcomeObservation;
    atomicWrite(target, state);
    return true;
  });
}


export function invalidateOperation(sessionId, operationId, reasonCode, env = process.env, now = Date.now()) {
  const boundedSession = bounded(sessionId, 'INVALID_SESSION');
  const boundedOperation = bounded(operationId, 'INVALID_OPERATION');
  bounded(reasonCode, 'INVALID_REASON');
  return withLock(boundedSession, env, (target) => {
    const state = readState(boundedSession, env, now);
    const prior = state.active.length + state.pending.length;
    state.pending = state.pending.filter((entry) => entry.operationId !== boundedOperation);
    state.active = state.active.filter((entry) => entry.operationId !== boundedOperation);
    state.calls = state.calls.filter((entry) => entry.operationId !== boundedOperation);
    if (prior === state.active.length + state.pending.length) return false;
    atomicWrite(target, state);
    return true;
  });
}
